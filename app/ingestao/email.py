"""E-mail (.eml e .msg) para Documento, pelo mesmo caminho.

`.msg` e `.eml` são o mesmo documento em duas embalagens: só muda quem extrai
corpo e anexos. Imagens embutidas (logo, assinatura, banner) são descartadas
aqui porque este pipeline só lê texto; anexos repetidos pela corrente de
respostas são deduplicados por hash.
"""

from __future__ import annotations

import email
import email.policy
import hashlib
import os
import re
import tempfile
from collections.abc import Iterable

from .anexos import classificar, decodificar, ler_anexo
from .documento import Bloco, Documento, texto_para_blocos
from .html import html_para_blocos


def _montar(
    assunto: str,
    remetente: str,
    html: str,
    texto: str,
    anexos: Iterable[tuple[str, bytes, str]],
    origem: str,
) -> Documento:
    blocos = html_para_blocos(html) if html.strip() else texto_para_blocos(texto)
    vistos: set[str] = set()
    for nome, dados, ctype in anexos:
        if not dados:
            continue
        h = hashlib.sha256(dados).hexdigest()
        if h in vistos:
            continue
        vistos.add(h)
        if classificar(nome, ctype) == "imagem":
            continue
        for b in ler_anexo(nome, dados, ctype):
            b.meta.setdefault("hash", h[:16])
            blocos.append(b)
    return Documento(origem=origem, remetente=remetente, assunto=assunto, blocos=blocos)


def ler_eml(bruto: bytes, origem: str = "mensagem.eml") -> Documento:
    msg = email.message_from_bytes(bruto, policy=email.policy.default)

    def cab(k: str) -> str:
        return re.sub(r"\s+", " ", str(msg.get(k, "") or "")).strip()

    html, texto = "", ""
    anexos: list[tuple[str, bytes, str]] = []
    for parte in msg.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        ctype = (parte.get_content_type() or "").lower()
        nome = parte.get_filename() or ""
        dados = parte.get_payload(decode=True) or b""
        if not dados:
            continue
        disp = (parte.get_content_disposition() or "").lower()
        if ctype == "text/html" and disp != "attachment" and not html:
            html = decodificar(dados, parte.get_content_charset())
        elif ctype == "text/plain" and disp != "attachment" and not nome and not texto:
            texto = decodificar(dados, parte.get_content_charset())
        else:
            anexos.append((nome or f"anexo.{classificar(nome, ctype)}", dados, ctype))
    return _montar(cab("Subject"), cab("From"), html, texto, anexos, origem)


def ler_msg(bruto: bytes, origem: str = "mensagem.msg") -> Documento:
    """Outlook .msg via extract-msg. O arquivo vai para disco porque a lib precisa de acesso aleatório."""
    import extract_msg

    with tempfile.TemporaryDirectory() as tmp:
        caminho = os.path.join(tmp, "entrada.msg")
        with open(caminho, "wb") as f:
            f.write(bruto)
        m = extract_msg.openMsg(caminho)
        try:
            html = _texto(getattr(m, "htmlBody", "") or "")
            corpo = _texto(getattr(m, "body", "") or "")
            anexos = []
            for att in m.attachments or []:
                dados = getattr(att, "data", None)
                if isinstance(dados, (bytes, bytearray)) and dados:
                    nome = getattr(att, "longFilename", None) or getattr(att, "shortFilename", None) or ""
                    anexos.append((nome, bytes(dados), ""))
            return _montar(
                (getattr(m, "subject", "") or "").strip(),
                (getattr(m, "sender", "") or "").strip(),
                html,
                corpo,
                anexos,
                origem,
            )
        finally:
            m.close()


def _texto(v) -> str:
    if isinstance(v, (bytes, bytearray)):
        return decodificar(bytes(v))
    return v or ""


def documento_de_texto(txt: str, origem: str = "texto colado") -> Documento:
    return Documento(origem=origem, blocos=texto_para_blocos(txt))


def documento_de_arquivo(nome: str, dados: bytes, content_type: str = "") -> Documento:
    tipo = classificar(nome, content_type)
    if tipo == "eml":
        return ler_eml(dados, nome)
    if tipo == "msg":
        return ler_msg(dados, nome)
    if tipo == "imagem":
        return Documento(origem=nome, blocos=[Bloco("anexo", "(imagem: sem leitura de texto)", origem=nome)])
    return Documento(origem=nome, blocos=ler_anexo(nome, dados, content_type))
