import csv
import io
from datetime import date
from pathlib import Path

import pytest

from app.exportacao import (
    COLUNAS,
    DadosCSV,
    ErroExportacao,
    LinhaCSV,
    cnpj_formatado,
    cnpj_valido,
    fmt_preco,
    fmt_quantidade,
    gerar_csv,
)

GOLDEN = Path(__file__).parent / "golden" / "proposta_exemplo.csv"
HOJE = date(2026, 3, 9)

# lido do arquivo de cabeçalho do ERP; qualquer mudança aqui quebra a importação
CABECALHO_ESPERADO = (
    "ID;Número da proposta;Data;Data proximo contato;ID contato;Nome do contato;Aos cuidados de;"
    "Lista de Preço;Tipo de Pessoa;CPF/CNPJ;RG/IE;CEP;Município;UF;Endereço;Endereço Nro;Complemento;"
    "Bairro;Fone;Celular;E-mail;Desconto;Frete;Observações;Validade;Prazo de Entrega;Situação;"
    "Introdução;ID produto;Descrição;Quantidade;Valor unitário;Descrição complementar;Vendedor;"
    "Destinatário;CPF/CNPJ entrega;CEP entrega;Município entrega;UF entrega;Endereço entrega;"
    "Endereço Nro entrega;Complemento entrega;Bairro entrega;Fone entrega;Inscrição Estadual entrega"
)


def exemplo(**kw) -> DadosCSV:
    base = dict(
        numero_proposta="COT-2026-00007",
        cliente="Horizonte Redes Ltda",
        cnpj="12.345.678/0001-95",
        frete_centavos=15050,
        prazo_entrega="10 dias úteis",
        itens=[
            LinhaCSV("Switch gerenciável 24 portas Gigabit NODAL NX-SW24G", 4, "UN", 167700, "switch 24p"),
            LinhaCSV("Cabo de rede UTP Cat6 4 pares azul caixa 305m VERTEX", 6, "CX", 89050),
            LinhaCSV("Patch cord Cat6 1,5m", 120.5, "UN", 123456789),
        ],
    )
    base.update(kw)
    return DadosCSV(**base)


def linhas(bruto: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(bruto.decode("utf-8-sig"), newline=""), delimiter=","))


def test_quarenta_e_cinco_colunas_com_os_nomes_do_erp():
    assert len(COLUNAS) == 45 == len(set(COLUNAS))
    assert ",".join(COLUNAS) == CABECALHO_ESPERADO.replace(";", ",")


def test_golden_file_byte_a_byte():
    bruto = gerar_csv(exemplo(), hoje=HOJE)
    assert bruto == GOLDEN.read_bytes()


def test_bom_utf8_crlf_e_virgula():
    bruto = gerar_csv(exemplo(), hoje=HOJE)
    assert bruto.startswith(b"\xef\xbb\xbf")
    assert bruto.endswith(b"\r\n")
    assert b"\n" not in bruto.replace(b"\r\n", b"")  # nenhuma quebra de linha solta
    assert bruto.decode("utf-8-sig").splitlines()[0] == CABECALHO_ESPERADO.replace(";", ",")


def test_mesmo_numero_de_proposta_em_todas_as_linhas():
    rs = linhas(gerar_csv(exemplo(), hoje=HOJE))
    assert len(rs) == 3
    assert {r["Número da proposta"] for r in rs} == {"COT-2026-00007"}


def test_numero_vazio_ou_sem_itens_e_erro():
    with pytest.raises(ErroExportacao):
        gerar_csv(exemplo(numero_proposta="  "))
    with pytest.raises(ErroExportacao):
        gerar_csv(exemplo(itens=[]))


def test_fmt_preco_tres_casas_ponto_de_milhar_e_sem_float():
    assert fmt_preco(0) == "0,000"
    assert fmt_preco(5) == "0,050"
    assert fmt_preco(123456) == "1.234,560"
    assert fmt_preco(123456789) == "1.234.567,890"
    assert fmt_preco(10) + fmt_preco(20) == "0,100" + "0,200"
    assert fmt_preco(None) == "0,000" and fmt_preco(-5) == "0,000"


def test_quantidade_e_frete_com_virgula_decimal():
    assert fmt_quantidade(4) == "4,00" and fmt_quantidade(120.5) == "120,50"
    r = linhas(gerar_csv(exemplo(), hoje=HOJE))[0]
    assert r["Frete"] == "150,50" and r["Desconto"] == "0,00"


def test_cnpj_valido_e_formatado():
    assert cnpj_valido("12.345.678/0001-95")
    assert cnpj_valido("12345678000195")
    assert not cnpj_valido("12.345.678/0001-96")
    assert not cnpj_valido("11111111111111")
    assert not cnpj_valido("123")
    assert cnpj_formatado("12345678000195") == "12.345.678/0001-95"
    assert cnpj_formatado("abc") == "abc"


def test_cnpj_invalido_sai_vazio_e_vai_para_observacoes():
    rs = linhas(gerar_csv(exemplo(cnpj="12.345.678/0001-00", observacoes="Urgente"), hoje=HOJE))
    assert rs[0]["CPF/CNPJ"] == ""
    assert rs[0]["Observações"] == "Urgente | CNPJ lido (inválido, conferir): 12.345.678/0001-00"


def test_cnpj_ausente_nao_gera_aviso():
    rs = linhas(gerar_csv(exemplo(cnpj=""), hoje=HOJE))
    assert rs[0]["CPF/CNPJ"] == "" and rs[0]["Observações"] == ""


def test_texto_com_separador_e_aspas_nao_desalinha_colunas():
    d = exemplo(itens=[LinhaCSV('Cabo "especial", 2 vias', 1, "UN", 100)])
    (r,) = linhas(gerar_csv(d, hoje=HOJE))
    assert r["Descrição"] == 'Cabo "especial", 2 vias'
    assert len(r) == 45
