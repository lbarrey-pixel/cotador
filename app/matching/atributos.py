"""Atributos técnicos críticos: o que diverge descarta o candidato.

Descrição parecida não basta. Um switch de 24 portas não é um de 48, um cabo
Cat6 não é Cat5e e uma fonte 12V não é 24V, por mais que as palavras batam.
Estes atributos são lidos da descrição por regex e comparados antes do modelo
opinar; se os dois lados declaram valores diferentes, o candidato cai.
"""

from __future__ import annotations

import re

ATRIBUTOS_CRITICOS: tuple[str, ...] = (
    "tensao",
    "portas",
    "capacidade",
    "categoria",
    "bitola",
    "polos",
    "amperagem",
    "fibras",
    "resolucao",
)

_PADROES: dict[str, re.Pattern[str]] = {
    "tensao": re.compile(r"\b(\d{2,3})\s*v(?:ac|dc|olts?)?\b", re.I),
    "portas": re.compile(r"\b(\d{1,2})\s*(?:p|portas?|ports?)\b", re.I),
    "capacidade": re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(tb|gb)\b", re.I),
    "categoria": re.compile(r"\bcat\.?\s*(5e|6a|6|7)\b", re.I),
    "bitola": re.compile(r"\b(\d+(?:[.,]\d+)?)\s*mm[²2]", re.I),
    "polos": re.compile(r"\b([1-4])\s*p(?:olos?)?\b(?!\w)", re.I),
    "amperagem": re.compile(r"\b(\d{1,3})\s*a(?:mp(?:eres?)?)?\b", re.I),
    "fibras": re.compile(r"\b(\d{1,3})\s*(?:fo|fibras?)\b", re.I),
    "resolucao": re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(?:mp|megapixels?)\b", re.I),
}

_PORTAS_VS_POLOS = re.compile(r"\b(\d{1,2})\s*p\b", re.I)


def _canon(nome: str, m: re.Match[str]) -> str:
    v = m.group(1).replace(",", ".").lower()
    if nome == "capacidade":
        v = f"{v}{m.group(2).lower()}"
    if v.replace(".", "", 1).isdigit() and "." in v:
        v = v.rstrip("0").rstrip(".")
    return v


def extrair_atributos(descricao: str) -> dict[str, str]:
    """Primeiro valor de cada atributo encontrado no texto, em forma canônica."""
    texto = descricao or ""
    achados: dict[str, str] = {}
    for nome, padrao in _PADROES.items():
        m = padrao.search(texto)
        if m:
            achados[nome] = _canon(nome, m)
    # "24P" vale como portas em switch e como polos em disjuntor; só um deles por vez
    if "portas" in achados and "polos" in achados and achados["portas"] == achados["polos"]:
        if re.search(r"switch|patch|painel|hub", texto, re.I):
            achados.pop("polos")
        elif re.search(r"disjuntor|contator|chave", texto, re.I):
            achados.pop("portas")
    return achados


def divergencia_critica(pedido: dict[str, str], candidato: dict[str, str]) -> str | None:
    """Nome do primeiro atributo crítico que os dois lados declaram com valores diferentes.

    Atributo ausente de um lado não diverge: o cliente que não disse a tensão
    pode receber qualquer uma, e o modelo decide com o que sobrar.
    """
    for nome in ATRIBUTOS_CRITICOS:
        a, b = pedido.get(nome), candidato.get(nome)
        if a and b and _canon_livre(a) != _canon_livre(b):
            return nome
    return None


def _canon_livre(v: str) -> str:
    return v.strip().lower().replace(",", ".").replace(" ", "")


def atributos_do_item(descricao: str, declarados: dict[str, str] | None = None) -> dict[str, str]:
    """Atributos vindos da extração (quando houver) por cima dos lidos da descrição."""
    base = extrair_atributos(descricao)
    for k, v in (declarados or {}).items():
        if k in ATRIBUTOS_CRITICOS and v:
            base[k] = _canon_livre(str(v))
    return base
