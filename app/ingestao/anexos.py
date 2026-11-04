"""Leitura de anexos: planilha, CSV, PDF e texto."""

from __future__ import annotations

import csv
import io

from .documento import Bloco, e_tabela_de_dados, normalizar_texto, tabela_para_texto

_ALIAS_CHARSET = {
    "ansi_x3.4-1968": "cp1252",
    "us-ascii": "cp1252",
    "ascii": "cp1252",
    "iso-8859-1": "cp1252",
    "latin-1": "cp1252",
    "latin1": "cp1252",
}

_EXT_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
_EXT_PLANILHA = (".xlsx", ".xlsm")
_LIMITE_ANEXO = 40_000


def decodificar(dados: bytes, charset: str | None = None) -> str:
    """Decodifica respeitando o charset declarado, com cadeia de fallback.

    iso-8859-1 vira cp1252 de propósito: é superconjunto e cobre aspas curvas e
    travessão do Word, que em latin-1 puro viram caractere de controle. Decodificar
    tudo como utf-8 com `ignore` apagaria os acentos em silêncio.
    """
    if not dados:
        return ""
    cs = (charset or "").strip().lower().strip("\"'")
    cs = _ALIAS_CHARSET.get(cs, cs)
    for enc in [cs, "utf-8", "cp1252", "latin-1"]:
        if not enc:
            continue
        try:
            return dados.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return dados.decode("utf-8", "replace")


def classificar(nome: str, content_type: str = "") -> str:
    n = (nome or "").lower()
    c = (content_type or "").lower()
    if n.endswith(_EXT_IMAGEM) or c.startswith("image/"):
        return "imagem"
    if n.endswith(_EXT_PLANILHA) or "spreadsheet" in c or "excel" in c:
        return "planilha"
    if n.endswith(".csv") or c == "text/csv":
        return "csv"
    if n.endswith(".pdf") or c == "application/pdf":
        return "pdf"
    if n.endswith(".msg") or c == "application/vnd.ms-outlook":
        return "msg"
    if n.endswith(".eml") or c == "message/rfc822":
        return "eml"
    if n.endswith(".txt") or c == "text/plain":
        return "texto"
    return "outro"


def _linhas_para_blocos(linhas: list[list[str]], origem: str) -> list[Bloco]:
    linhas = [[str(c) if c is not None else "" for c in ln] for ln in linhas]
    linhas = [ln for ln in linhas if any(c.strip() for c in ln)]
    if not linhas:
        return []
    if e_tabela_de_dados(linhas):
        return [Bloco("tabela", tabela_para_texto(linhas), origem=origem)]
    return [Bloco("texto", normalizar_texto("\n".join(" ".join(ln) for ln in linhas)), origem=origem)]


def ler_planilha(dados: bytes, origem: str = "planilha.xlsx") -> list[Bloco]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    blocos: list[Bloco] = []
    for ws in wb.worksheets:
        linhas = []
        for row in ws.iter_rows(values_only=True):
            celulas = ["" if v is None else _celula(v) for v in row]
            # corta colunas vazias à direita
            while celulas and not celulas[-1].strip():
                celulas.pop()
            if celulas:
                linhas.append(celulas)
        nome = f"{origem}#{ws.title}" if len(wb.worksheets) > 1 else origem
        blocos.extend(_linhas_para_blocos(linhas, nome))
    wb.close()
    return blocos


def _celula(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def ler_csv(dados: bytes, origem: str = "planilha.csv") -> list[Bloco]:
    txt = decodificar(dados)
    amostra = txt[:4096]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t")
    except csv.Error:
        dialeto = csv.excel
    linhas = list(csv.reader(io.StringIO(txt), dialect=dialeto))
    return _linhas_para_blocos(linhas, origem)


def ler_pdf(dados: bytes, origem: str = "anexo.pdf") -> list[Bloco]:
    """Texto e tabelas página a página. PDF digitalizado (sem texto) vira aviso."""
    import pdfplumber

    blocos: list[Bloco] = []
    with pdfplumber.open(io.BytesIO(dados)) as pdf:
        for n, pagina in enumerate(pdf.pages, 1):
            rotulo = f"{origem} p.{n}"
            for tabela in pagina.extract_tables() or []:
                linhas = [[c or "" for c in ln] for ln in tabela]
                blocos.extend(_linhas_para_blocos(linhas, rotulo))
            texto = normalizar_texto(pagina.extract_text() or "")
            if texto:
                blocos.append(Bloco("texto", texto[:_LIMITE_ANEXO], origem=rotulo))
    if not any(b.conteudo.strip() for b in blocos):
        blocos = [
            Bloco(
                "anexo",
                "(PDF sem camada de texto: provavelmente digitalizado; abrir à mão)",
                origem=origem,
                meta={"sem_texto": True},
            )
        ]
    return blocos


def ler_anexo(nome: str, dados: bytes, content_type: str = "") -> list[Bloco]:
    """Anexo não-imagem para blocos. Falha de leitura vira bloco de aviso, nunca exceção."""
    tipo = classificar(nome, content_type)
    try:
        if tipo == "planilha":
            return ler_planilha(dados, nome)
        if tipo == "csv":
            return ler_csv(dados, nome)
        if tipo == "pdf":
            return ler_pdf(dados, nome)
        if tipo == "texto":
            return [Bloco("texto", normalizar_texto(decodificar(dados))[:_LIMITE_ANEXO], origem=nome)]
    except Exception as e:  # noqa: BLE001 - anexo ruim não derruba a leitura do pedido
        return [Bloco("anexo", f"(não consegui ler este anexo: {type(e).__name__})", origem=nome)]
    return [Bloco("anexo", "(anexo não convertido; abrir à mão)", origem=nome, meta={"tipo": tipo})]
