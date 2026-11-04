"""HTML de e-mail para blocos, percorrendo o documento linearmente.

Linear de propósito, não DOM: a ordem de leitura é a informação que o
achatamento em texto destrói. Tabela de dados vira bloco próprio com as
células separadas por ` | `, para quem lê depois saber qual número é quantidade.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from .documento import MARCA_CITACAO, Bloco, e_tabela_de_dados, tabela_para_texto

_FIM_DE_BLOCO = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "blockquote"}


class _Leitor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocos: list[Bloco] = []
        self._buf: list[str] = []
        self._citado = 0
        self._viu_citacao = False
        self._tabelas: list[dict] = []
        self._ignorar = 0

    def _citado_agora(self) -> bool:
        return self._citado > 0 or self._viu_citacao

    def _flush(self) -> None:
        txt = "".join(self._buf).strip()
        self._buf = []
        if not txt:
            return
        if self._tabelas:
            self._tabelas[-1]["celula"].append(txt)
            return
        if MARCA_CITACAO.search(txt):
            self._viu_citacao = True
        self.blocos.append(Bloco("texto", txt, origem="corpo", citado=self._citado_agora()))

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._ignorar += 1
            return
        if self._ignorar:
            return
        if tag == "blockquote":
            self._flush()
            self._citado += 1
        elif tag == "table":
            self._flush()
            self._tabelas.append({"linhas": [], "linha": [], "celula": []})
        elif tag == "tr" and self._tabelas:
            self._flush()
            self._tabelas[-1]["linha"] = []
        elif tag in ("td", "th") and self._tabelas:
            self._flush()
            self._tabelas[-1]["celula"] = []
        elif tag in _FIM_DE_BLOCO:
            self._flush()

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._ignorar = max(0, self._ignorar - 1)
            return
        if self._ignorar:
            return
        if tag == "blockquote":
            self._flush()
            self._citado = max(0, self._citado - 1)
        elif tag in ("td", "th") and self._tabelas:
            self._flush()
            t = self._tabelas[-1]
            t["linha"].append(" ".join(t["celula"]).strip())
            t["celula"] = []
        elif tag == "tr" and self._tabelas:
            self._flush()
            t = self._tabelas[-1]
            if t["celula"]:
                t["linha"].append(" ".join(t["celula"]).strip())
                t["celula"] = []
            t["linhas"].append(list(t["linha"]))
            t["linha"] = []
        elif tag == "table" and self._tabelas:
            self._flush()
            t = self._tabelas.pop()
            if t["linha"]:
                t["linhas"].append(list(t["linha"]))
            self._emitir_tabela(t["linhas"])
        elif tag in _FIM_DE_BLOCO:
            self._flush()

    def handle_data(self, d):
        if self._ignorar:
            return
        if d and d.strip():
            self._buf.append(re.sub(r"[ \t\r\f\v]+", " ", d))
        elif d and self._buf:
            self._buf.append(" ")

    def _emitir_tabela(self, linhas: list[list[str]]) -> None:
        linhas = [ln for ln in linhas if any(c.strip() for c in ln)]
        if not linhas:
            return
        if e_tabela_de_dados(linhas):
            self.blocos.append(
                Bloco(
                    "tabela",
                    tabela_para_texto(linhas),
                    origem="corpo",
                    citado=self._citado_agora(),
                    meta={"linhas": len(linhas), "colunas": max(len(ln) for ln in linhas)},
                )
            )
            return
        # tabela de layout: cada linha vira texto comum
        for ln in linhas:
            t = " ".join(c.strip() for c in ln if c.strip())
            if t:
                if MARCA_CITACAO.search(t):
                    self._viu_citacao = True
                self.blocos.append(Bloco("texto", t, origem="corpo", citado=self._citado_agora()))

    def fechar(self) -> list[Bloco]:
        while self._tabelas:
            t = self._tabelas.pop()
            if t["celula"]:
                t["linha"].append(" ".join(t["celula"]))
            if t["linha"]:
                t["linhas"].append(t["linha"])
            self._emitir_tabela(t["linhas"])
        self._flush()
        return self.blocos


def html_para_blocos(html: str) -> list[Bloco]:
    leitor = _Leitor()
    leitor.feed(html or "")
    return leitor.fechar()
