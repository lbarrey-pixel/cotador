"""Documento canônico: blocos em ordem de leitura.

Um pedido de cotação chega de muitas formas (texto colado, e-mail com tabela
HTML, planilha, PDF). Todas viram a mesma coisa aqui: uma lista ordenada de
blocos. A ordem importa porque a tabela do item 3 vem logo depois do parágrafo
que diz "segue abaixo", e achatar tudo em texto corrido perde essa ligação.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

TipoBloco = Literal["texto", "tabela", "anexo"]

TEXTO_MAX_CHARS = 120_000


@dataclass
class Bloco:
    tipo: TipoBloco
    conteudo: str
    origem: str = ""
    citado: bool = False
    meta: dict = field(default_factory=dict)


@dataclass
class Documento:
    origem: str = ""
    remetente: str = ""
    assunto: str = ""
    blocos: list[Bloco] = field(default_factory=list)

    def cabecalho(self) -> str:
        partes = []
        if self.assunto:
            partes.append(f"Assunto: {self.assunto}")
        if self.remetente:
            partes.append(f"De: {self.remetente}")
        return "\n".join(partes)

    def render_texto(self, limite: int = TEXTO_MAX_CHARS) -> str:
        """Documento como texto único, com marcadores de tabela e anexo no lugar."""
        partes = []
        cab = self.cabecalho()
        if cab:
            partes.append(cab)
        for b in self.blocos:
            if not b.conteudo.strip():
                continue
            if b.citado:
                partes.append("[CITAÇÃO] " + b.conteudo.replace("\n", "\n[CITAÇÃO] "))
            elif b.tipo == "tabela":
                partes.append("[TABELA]\n" + b.conteudo)
            elif b.tipo == "anexo":
                partes.append(f"[ANEXO: {b.origem}]\n{b.conteudo}")
            else:
                partes.append(b.conteudo)
        return "\n\n".join(partes)[:limite]


MARCA_CITACAO = re.compile(
    r"-{2,}\s*mensagem\s+original|_{10,}|"
    r"\bDe\s*:\s.{0,120}?\bEnviad[ao]\s+em\s*:|"
    r"\bFrom\s*:\s.{0,120}?\bSent\s*:|\bOn\b.{0,90}\bwrote\s*:",
    re.I | re.S,
)


def normalizar_texto(txt: str) -> str:
    txt = (txt or "").replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"[ \t\f\v]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def texto_para_blocos(txt: str, origem: str = "corpo") -> list[Bloco]:
    """Quebra texto puro em parágrafos; tudo após uma marca de citação é citado."""
    blocos, citado = [], False
    for pedaco in re.split(r"\n\s*\n", normalizar_texto(txt)):
        pedaco = pedaco.strip()
        if not pedaco:
            continue
        if MARCA_CITACAO.search(pedaco):
            citado = True
        blocos.append(Bloco("texto", pedaco, origem=origem, citado=citado))
    return blocos


def tabela_para_texto(linhas: list[list[str]]) -> str:
    return "\n".join(" | ".join(c.strip() for c in ln) for ln in linhas)


def e_tabela_de_dados(linhas: list[list[str]]) -> bool:
    """>=2 linhas e >=2 linhas com pelo menos 2 células preenchidas.

    Clientes de e-mail montam assinatura e layout inteiro com <table>; esse
    critério separa tabela de itens de tabela de enfeite sem olhar o conteúdo.
    """
    uteis = [ln for ln in linhas if any(c.strip() for c in ln)]
    if len(uteis) < 2:
        return False
    cheias = sum(1 for ln in uteis if len([c for c in ln if c.strip()]) >= 2)
    return cheias >= 2
