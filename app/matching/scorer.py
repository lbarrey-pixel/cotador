"""Scorer puro para candidatos, quando não há Postgres com pg_trgm por perto.

Serve ao teste, ao modo demo e à CLI de avaliação. Em produção a camada 2
é o índice GiST de trigramas; este scorer aproxima o mesmo ranking com
Jaccard de tokens mais um bônus para código de modelo igual, que é o sinal
mais forte que uma descrição de produto carrega.
"""

from __future__ import annotations

from collections.abc import Iterable

from .normalizacao import codigos, tokens
from .tipos import Candidato, Produto

PESO_CODIGO = 0.35


def similaridade(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    jaccard = len(ta & tb) / len(ta | tb)
    ca, cb = codigos(a), codigos(b)
    bonus = PESO_CODIGO if ca and cb and (ca & cb) else 0.0
    return min(1.0, jaccard + bonus)


def candidatos_puros(descricao: str, produtos: Iterable[Produto], n: int = 40) -> list[Candidato]:
    pontuados = [Candidato(p, similaridade(descricao, p.descricao)) for p in produtos]
    pontuados = [c for c in pontuados if c.similaridade > 0]
    pontuados.sort(key=lambda c: (-c.similaridade, c.produto.id))
    return pontuados[:n]
