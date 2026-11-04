"""Normalização de texto para chave de memória e para o scorer puro.

A chave da memória é sempre calculada aqui, em Python, e entregue pronta ao
Postgres: assim existe uma só definição de "mesma descrição" e o banco não
precisa da extensão unaccent.
"""

from __future__ import annotations

import re
import unicodedata

_PALAVRAS_VAZIAS = frozenset(
    [
        "de",
        "da",
        "do",
        "das",
        "dos",
        "para",
        "com",
        "sem",
        "em",
        "e",
        "ou",
        "a",
        "o",
        "as",
        "os",
        "um",
        "uma",
        "un",
        "pc",
        "pcs",
        "unid",
        "unidade",
    ]
)
_CODIGO = re.compile(r"\b(?=[a-z0-9-]*\d)(?=[a-z0-9-]*[a-z])[a-z0-9]+(?:-[a-z0-9]+)*\b|\b\d{4,}\b")


def normalizar(s: str) -> str:
    t = unicodedata.normalize("NFD", s or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def tokens(s: str) -> set[str]:
    return {t for t in normalizar(s).split() if t not in _PALAVRAS_VAZIAS and len(t) > 1}


def codigos(s: str) -> set[str]:
    """Tokens que parecem código de modelo/fabricante: misturam letra e dígito, ou são numéricos longos."""
    t = unicodedata.normalize("NFD", s or "").lower()
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9-]+", " ", t)
    return {c.replace("-", "") for c in _CODIGO.findall(t)}
