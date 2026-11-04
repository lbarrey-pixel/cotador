"""Camada 2: candidatos do catálogo inteiro para cada item.

Com Postgres, a busca é por similaridade de trigramas sobre índice GiST
(`candidatos_trgm_lote`): uma ida ao banco para todos os itens, top-N por
item. Sem banco, o scorer puro percorre a lista de produtos em memória.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .scorer import candidatos_puros
from .tipos import Candidato, Produto

TOP_N = 40


class BuscaCandidatos(Protocol):
    def buscar(self, descricoes: list[str], n: int = TOP_N) -> list[list[Candidato]]: ...


class BuscaPura:
    def __init__(self, produtos: Iterable[Produto]) -> None:
        self.produtos = list(produtos)

    def buscar(self, descricoes: list[str], n: int = TOP_N) -> list[list[Candidato]]:
        return [candidatos_puros(d, self.produtos, n) for d in descricoes]


def produto_de_linha(linha: tuple) -> Produto:
    pid, codigo, descricao, atributos, preco, ncm = linha
    return Produto(
        id=pid,
        codigo=codigo or "",
        descricao=descricao or "",
        atributos=dict(atributos or {}),
        preco_custo_centavos=int(preco or 0),
        ncm=ncm or "",
    )


class BuscaTrigrama:
    def __init__(self, conectar) -> None:
        self._conectar = conectar

    def buscar(self, descricoes: list[str], n: int = TOP_N) -> list[list[Candidato]]:
        saida: list[list[Candidato]] = [[] for _ in descricoes]
        if not descricoes:
            return saida
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(
                """select idx, id, codigo, descricao, atributos, preco_custo_centavos, ncm, sim
                   from candidatos_trgm_lote(%s, %s)""",
                (descricoes, n),
            )
            for idx, *linha, sim in cur.fetchall():
                saida[idx - 1].append(Candidato(produto_de_linha(tuple(linha)), float(sim)))
        return saida
