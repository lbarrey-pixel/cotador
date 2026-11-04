import csv
import io
from email.message import EmailMessage

import openpyxl

from app.ingestao import (
    decodificar,
    documento_de_arquivo,
    documento_de_texto,
    ler_csv,
    ler_eml,
    ler_pdf,
    ler_planilha,
    texto_para_blocos,
)

HTML = """<html><body>
<p>Boa tarde, preciso de cotação dos itens abaixo.</p>
<table>
  <tr><th>Descrição</th><th>Qtd</th></tr>
  <tr><td>Switch 24p gigabit</td><td>4</td></tr>
  <tr><td>Cabo UTP cat6 cx 305m</td><td>6</td></tr>
</table>
<table><tr><td>Ana Souza - Compras</td></tr></table>
<blockquote><p>De: fulano@example.com Enviada em: segunda</p><p>1 un fonte 12v</p></blockquote>
</body></html>"""


def montar_eml(anexos=()) -> bytes:
    m = EmailMessage()
    m["Subject"] = "Cotação RFQ-0412"
    m["From"] = "compras@example.com"
    m.set_content("versão em texto simples")
    m.add_alternative(HTML, subtype="html")
    for nome, dados, mime in anexos:
        principal, _, sub = mime.partition("/")
        m.add_attachment(dados, maintype=principal, subtype=sub, filename=nome)
    return m.as_bytes()


def csv_bytes(linhas, delim=";") -> bytes:
    s = io.StringIO()
    csv.writer(s, delimiter=delim).writerows(linhas)
    return s.getvalue().encode("utf-8")


def test_texto_colado_vira_paragrafos():
    doc = documento_de_texto("Prezados,\n\n4x switch 24p\n6 cx cabo cat6\n\n\n\nAtt")
    assert [b.tipo for b in doc.blocos] == ["texto", "texto", "texto"]
    assert doc.blocos[1].conteudo == "4x switch 24p\n6 cx cabo cat6"


def test_citacao_marca_o_resto_como_citado():
    blocos = texto_para_blocos("Pedido novo\n\n-----Mensagem original-----\nDe: x\n\n2 un fonte")
    assert [b.citado for b in blocos] == [False, True, True]


def test_eml_html_preserva_ordem_e_tabela():
    doc = ler_eml(montar_eml())
    assert doc.assunto == "Cotação RFQ-0412"
    assert doc.remetente == "compras@example.com"
    tipos = [b.tipo for b in doc.blocos]
    assert tipos[0] == "texto" and "tabela" in tipos
    tabela = next(b for b in doc.blocos if b.tipo == "tabela")
    assert tabela.conteudo.splitlines()[1] == "Switch 24p gigabit | 4"
    # tabela de assinatura (uma célula) não é tabela de dados
    assert not any(b.tipo == "tabela" and "Ana Souza" in b.conteudo for b in doc.blocos)
    assert any("Ana Souza" in b.conteudo for b in doc.blocos)


def test_eml_marca_citacao_no_render():
    doc = ler_eml(montar_eml())
    citados = [b for b in doc.blocos if b.citado]
    assert any("fonte 12v" in b.conteudo for b in citados)
    assert "[CITAÇÃO] 1 un fonte 12v" in doc.render_texto()


def test_eml_anexo_repetido_conta_uma_vez_e_imagem_e_descartada():
    planilha = csv_bytes([["Descrição", "Qtd"], ["Patch panel 24p", "2"], ["Keystone cat6", "48"]])
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    bruto = montar_eml(
        [
            ("itens.csv", planilha, "text/csv"),
            ("itens-reenviado.csv", planilha, "text/csv"),
            ("assinatura.png", png, "image/png"),
        ]
    )
    doc = ler_eml(bruto)
    tabelas = [b for b in doc.blocos if b.tipo == "tabela" and b.origem.endswith(".csv")]
    assert len(tabelas) == 1
    assert not any("assinatura.png" in b.origem for b in doc.blocos)


def test_csv_com_ponto_e_virgula_e_acentos_cp1252():
    dados = csv_bytes([["Descrição", "Qtd"], ["Nobreak 1500VA", "2"]]).decode().encode("cp1252")
    (bloco,) = ler_csv(dados, "pedido.csv")
    assert bloco.tipo == "tabela"
    assert "Descrição | Qtd" in bloco.conteudo


def test_xlsx_com_duas_abas_nomeia_a_origem():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rede"
    ws.append(["Item", "Qtd"])
    ws.append(["Switch 8p", 3.0])
    ws2 = wb.create_sheet("Energia")
    ws2.append(["Item", "Qtd"])
    ws2.append(["Fonte 24V", 2])
    buf = io.BytesIO()
    wb.save(buf)
    blocos = ler_planilha(buf.getvalue(), "lista.xlsx")
    assert [b.origem for b in blocos] == ["lista.xlsx#Rede", "lista.xlsx#Energia"]
    assert "Switch 8p | 3" in blocos[0].conteudo  # 3.0 vira "3"


def pdf_minimo(texto: str) -> bytes:
    """PDF de uma página com uma linha de texto, escrito à mão (sem dependência de geração)."""
    fluxo = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(fluxo) + fluxo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    saida, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offsets.append(len(saida))
        saida += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(saida)
    saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        saida += b"%010d 00000 n \n" % off
    saida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(saida)


def test_pdf_com_texto():
    (bloco,) = ler_pdf(pdf_minimo("4 un Switch 24 portas"), "pedido.pdf")
    assert bloco.tipo == "texto" and "Switch 24 portas" in bloco.conteudo
    assert bloco.origem == "pedido.pdf p.1"


def test_pdf_corrompido_vira_aviso_e_nao_excecao():
    doc = documento_de_arquivo("quebrado.pdf", b"isso nao e um pdf")
    assert doc.blocos[0].tipo == "anexo"


def test_decodificar_nao_perde_acento():
    assert decodificar("Descrição — 2,5mm²".encode("cp1252"), "iso-8859-1") == "Descrição — 2,5mm²"
    assert decodificar("Descrição".encode(), None) == "Descrição"
