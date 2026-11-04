from .anexos import classificar, decodificar, ler_anexo, ler_csv, ler_pdf, ler_planilha
from .documento import Bloco, Documento, normalizar_texto, texto_para_blocos
from .email import documento_de_arquivo, documento_de_texto, ler_eml, ler_msg
from .html import html_para_blocos

__all__ = [
    "Bloco",
    "Documento",
    "classificar",
    "decodificar",
    "documento_de_arquivo",
    "documento_de_texto",
    "html_para_blocos",
    "ler_anexo",
    "ler_csv",
    "ler_eml",
    "ler_msg",
    "ler_pdf",
    "ler_planilha",
    "normalizar_texto",
    "texto_para_blocos",
]
