import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.api.repo_memoria import RepoMemoria
from app.config import Config
from app.extracao import ProvedorFake
from app.extracao.extrator import SYSTEM_EXTRACAO
from app.main import criar_app

EXTRACAO = {
    "cliente": "Horizonte Redes Ltda",
    "cnpj": "12.345.678/0001-95",
    "itens": [
        {"descricao_original": "Switch 24p gigabit gerenciavel", "quantidade": 4, "unidade": "UN"},
        {"descricao_original": "Cabo UTP cat6 cx 305m", "quantidade": 2, "unidade": "CX"},
        {"descricao_original": "martelo de borracha", "quantidade": 1, "unidade": "UN"},
    ],
}


def modelo(system, user):
    if system == SYSTEM_EXTRACAO:
        return json.dumps(EXTRACAO)
    ids = [int(x.split()[1]) for x in user.splitlines() if x.startswith("Item ")]
    return json.dumps(
        {"matches": [{"indice": i, "candidato": 0, "confianca": "alta", "motivo": "teste"} for i in sorted(set(ids))]}
    )


@pytest.fixture
def ctx(catalogo):
    repo = RepoMemoria(catalogo)
    fake = ProvedorFake(funcao=modelo)
    return TestClient(criar_app(repo, fake, Config())), repo, fake


def extrair(client):
    r = client.post("/propostas/extrair", data={"texto": "4x switch 24p\n2 cx cabo cat6"})
    assert r.status_code == 201, r.text
    return r.json()


def test_extrair_casa_itens_e_calcula_preco_com_margem(ctx):
    client, _, _ = ctx
    p = extrair(client)
    assert p["numero"].startswith("COT-") and p["cliente"] == "Horizonte Redes Ltda"
    sw, cabo, martelo = p["itens"]
    assert sw["produto_codigo"] == "SW24" and sw["origem"] == "modelo"
    assert sw["preco_un_centavos"] == 129000 * 130 // 100
    assert cabo["produto_codigo"] == "C6"
    assert martelo["produto_id"] is None and martelo["confianca"] == "nenhuma"


def test_extrair_aceita_arquivo_csv(ctx):
    client, _, fake = ctx
    arq = ("pedido.csv", "Descrição;Qtd\nSwitch 24p;4\nCabo cat6;2\n".encode(), "text/csv")
    r = client.post("/propostas/extrair", files={"arquivo": arq})
    assert r.status_code == 201
    assert "[TABELA]" in fake.chamadas[0][1]


def test_extrair_sem_entrada_e_422_e_modelo_fora_e_502(catalogo):
    client = TestClient(criar_app(RepoMemoria(catalogo), ProvedorFake(respostas=["x", "y"]), Config()))
    assert client.post("/propostas/extrair", data={"texto": " "}).status_code == 422
    r = client.post("/propostas/extrair", data={"texto": "4x switch"})
    assert r.status_code == 502 and "modelo" in r.json()["detail"]


def test_arquivo_acima_do_limite_e_413(catalogo):
    cfg = Config(upload_max_bytes=10)
    client = TestClient(criar_app(RepoMemoria(catalogo), ProvedorFake(funcao=modelo), cfg))
    r = client.post("/propostas/extrair", files={"arquivo": ("a.txt", b"x" * 50, "text/plain")})
    assert r.status_code == 413


def test_get_proposta(ctx):
    client, _, _ = ctx
    p = extrair(client)
    assert client.get(f"/propostas/{p['id']}").json() == p
    assert client.get("/propostas/999").status_code == 404


def test_confirmar_item_grava_na_memoria_e_a_proxima_cotacao_nao_chama_o_modelo(ctx):
    client, repo, fake = ctx
    p = extrair(client)
    r = client.put(f"/propostas/{p['id']}/itens/3", json={"produto_id": 5})  # martelo -> fonte 12V, só para o teste
    assert r.status_code == 200
    item = r.json()
    assert (item["produto_codigo"], item["origem"], item["confianca"]) == ("F12", "operador", "alta")
    assert item["preco_un_centavos"] == 4900 * 130 // 100
    fake.chamadas.clear()
    p2 = extrair(client)
    assert p2["itens"][2]["origem"] == "memoria_cliente"
    assert p2["itens"][2]["produto_id"] == 5


def test_put_altera_so_o_que_foi_enviado_e_valida(ctx):
    client, _, _ = ctx
    p = extrair(client)
    url = f"/propostas/{p['id']}/itens/1"
    r = client.put(url, json={"quantidade": 10, "preco_un_centavos": 1})
    assert r.status_code == 200 and r.json()["produto_codigo"] == "SW24"  # produto intocado
    assert (r.json()["quantidade"], r.json()["preco_un_centavos"]) == (10, 1)
    assert client.put(url, json={"produto_id": 4242}).status_code == 422
    assert client.put(url, json={"quantidade": 0}).status_code == 422
    assert client.put(f"/propostas/{p['id']}/itens/99", json={}).status_code == 404
    desfeito = client.put(url, json={"produto_id": None}).json()
    assert desfeito["produto_id"] is None and desfeito["preco_un_centavos"] == 0


def test_csv_da_proposta(ctx):
    client, _, _ = ctx
    p = extrair(client)
    r = client.post(f"/propostas/{p['id']}/csv", json={"frete_centavos": 2500, "prazo_entrega": "5 dias"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert p["numero"] in r.headers["content-disposition"]
    assert r.content.startswith(b"\xef\xbb\xbf")
    linhas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"), newline=""), delimiter=","))
    assert len(linhas) == 3 and {x["Número da proposta"] for x in linhas} == {p["numero"]}
    assert linhas[0]["Frete"] == "25,00" and linhas[0]["Valor unitário"] == "1.677,000"
    assert linhas[2]["Descrição"] == "martelo de borracha"
    assert "SEM PRODUTO" in linhas[2]["Descrição complementar"]
    assert client.post("/propostas/999/csv").status_code == 404


def test_produtos_busca_por_texto_e_codigo(ctx):
    client, _, _ = ctx
    assert {p["codigo"] for p in client.get("/produtos", params={"q": "cat6"}).json()} == {"C6"}
    assert [p["codigo"] for p in client.get("/produtos", params={"q": "f24"}).json()] == ["F24"]
    assert len(client.get("/produtos", params={"limite": 2}).json()) == 2


def test_saude(ctx):
    assert ctx[0].get("/saude").json()["status"] == "ok"
