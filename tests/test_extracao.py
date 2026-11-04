import json

import httpx
import pytest

from app.extracao import (
    CacheMemoria,
    ErroExtracao,
    ErroProvedor,
    Extrator,
    ProvedorFake,
    ProvedorHTTP,
    chave_cache,
    ler_json,
)
from app.ingestao import documento_de_texto

RESPOSTA = {
    "cliente": "Horizonte Redes Ltda",
    "cnpj": "12.345.678/0001-95",
    "itens": [
        {"descricao_original": "  Switch 24p GIGABIT  ", "quantidade": "1.200,5", "unidade": "pç",
         "atributos": {"Portas": "24", "cor": ""}},
        {"descricao_original": "Cabo cat6", "quantidade": 0},
    ],
}  # fmt: skip


def doc():
    return documento_de_texto("4x switch 24p")


def test_ler_json_tolera_cerca_texto_solto_e_virgula_sobrando():
    assert ler_json('```json\n{"a": 1,}\n```\nespero que ajude') == {"a": 1}
    assert ler_json('Claro! {"a": [1, 2,]} fim') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        ler_json("sem json nenhum")
    with pytest.raises(ValueError):
        ler_json("[1, 2]")


def test_extrai_e_normaliza_campos():
    ext = Extrator(ProvedorFake(respostas=[json.dumps(RESPOSTA)]))
    pedido = ext.extrair(doc())
    assert pedido.cnpj == "12345678000195"
    a, b = pedido.itens
    assert a.descricao_original == "Switch 24p GIGABIT"  # só apara as pontas, não reescreve
    assert (a.quantidade, a.unidade, a.atributos) == (1200.5, "PÇ", {"portas": "24"})
    assert b.quantidade == 1 and b.unidade == "UN"


def test_resposta_invalida_repete_uma_vez_mostrando_o_erro():
    fake = ProvedorFake(respostas=["não é json", json.dumps(RESPOSTA)])
    pedido = Extrator(fake).extrair(doc())
    assert len(pedido.itens) == 2
    assert len(fake.chamadas) == 2
    assert "foi rejeitada" in fake.chamadas[1][1]


def test_duas_respostas_ruins_viram_erro_claro():
    fake = ProvedorFake(respostas=["x", '{"itens": [{"descricao_original": ""}]}'])
    with pytest.raises(ErroExtracao):
        Extrator(fake).extrair(doc())
    assert len(fake.chamadas) == 2


def test_cache_por_hash_do_conteudo_evita_segunda_chamada():
    fake = ProvedorFake(respostas=[json.dumps(RESPOSTA)])
    ext = Extrator(fake, CacheMemoria())
    primeiro = ext.extrair(doc())
    segundo = ext.extrair(doc())
    assert primeiro == segundo
    assert len(fake.chamadas) == 1
    assert chave_cache("a") != chave_cache("b")
    assert chave_cache("a") != chave_cache("a", versao_prompt="outro prompt")


def test_documento_vazio_nao_chama_o_modelo():
    fake = ProvedorFake()
    assert Extrator(fake).extrair(documento_de_texto("   ")).itens == []
    assert fake.chamadas == []


def test_provedor_http_formato_de_chat_e_contagem_de_tokens(monkeypatch):
    vistos = {}

    def post(url, json, headers, timeout):
        vistos.update(url=url, json=json, headers=headers)
        corpo = {
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        }
        return httpx.Response(200, json=corpo, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    p = ProvedorHTTP("http://llm.local/v1/chat/completions", "segredo", "modelo-x")
    assert p.completar("sys", "oi") == "{}"
    assert vistos["json"]["messages"][0] == {"role": "system", "content": "sys"}
    assert vistos["json"]["model"] == "modelo-x"
    assert vistos["headers"]["Authorization"] == "Bearer segredo"
    assert (p.tokens_entrada, p.tokens_saida) == (10, 3)


def test_provedor_http_erro_de_rede_vira_erro_provedor(monkeypatch):
    def post(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(ErroProvedor):
        ProvedorHTTP("http://x", "k", "m").completar("s", "u")
