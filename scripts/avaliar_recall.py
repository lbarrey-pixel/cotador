"""Recall do gerador de candidatos (camada 2) sobre o conjunto de exemplo.

    python scripts/avaliar_recall.py                       # scorer puro, sem banco
    DATABASE_URL=postgresql://... python scripts/avaliar_recall.py   # trigramas no Postgres

Cada linha de db/avaliacao.csv é um texto de cliente e o código do produto que
o operador escolheria. O recall@k é a fração de linhas cujo produto aparece
entre os k primeiros candidatos. Os números impressos são os medidos nesta
execução, com o tamanho do catálogo ao lado: com poucas dezenas de produtos o
recall@40 é alto por construção, e só diz algo sobre catálogos grandes se a
avaliação for repetida neles.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.main import _catalogo_demo  # noqa: E402
from app.matching import BuscaPura, BuscaTrigrama  # noqa: E402

CORTES = (1, 5, 10, 40)


def carregar_casos() -> list[tuple[str, str]]:
    with open(RAIZ / "db" / "avaliacao.csv", encoding="utf-8", newline="") as f:
        return [(r["pedido"], r["codigo"]) for r in csv.DictReader(f, delimiter=";")]


def main() -> int:
    casos = carregar_casos()
    url = os.environ.get("DATABASE_URL", "")
    if url:
        import psycopg

        busca = BuscaTrigrama(lambda: psycopg.connect(url))
        with psycopg.connect(url) as con:
            total = con.execute("select count(*) from produtos").fetchone()[0]
        modo = "trigramas no Postgres (pg_trgm, índice GiST)"
    else:
        produtos = _catalogo_demo()
        busca = BuscaPura(produtos)
        total, modo = len(produtos), "scorer puro em Python (Jaccard de tokens + código de modelo)"

    listas = busca.buscar([p for p, _ in casos], max(CORTES))
    posicoes = []
    for (_, codigo), lista in zip(casos, listas, strict=True):
        codigos = [c.produto.codigo for c in lista]
        posicoes.append(codigos.index(codigo) + 1 if codigo in codigos else None)

    print(f"modo: {modo}")
    print(f"catálogo: {total} produtos | casos: {len(casos)}")
    for k in CORTES:
        acertos = sum(1 for p in posicoes if p is not None and p <= k)
        print(f"recall@{k}: {acertos}/{len(casos)} = {acertos / len(casos):.1%}")
    erros = [(p, c) for (p, c), pos in zip(casos, posicoes, strict=True) if pos is None or pos > 10]
    if erros:
        print("fora do top-10:")
        for pedido, codigo in erros:
            print(f"  {codigo}  <-  {pedido!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
