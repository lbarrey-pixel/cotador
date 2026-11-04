from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from app.matching import Produto

RAIZ = Path(__file__).resolve().parent.parent


def produto(pid: int, codigo: str, descricao: str, custo: int = 10000, **atributos: str) -> Produto:
    return Produto(id=pid, codigo=codigo, descricao=descricao, atributos=atributos, preco_custo_centavos=custo)


@pytest.fixture
def catalogo() -> list[Produto]:
    return [
        produto(1, "SW24", "Switch gerenciável 24 portas Gigabit NODAL NX-SW24G", 129000, portas="24"),
        produto(2, "SW48", "Switch gerenciável 48 portas Gigabit NODAL NX-SW48G", 289000, portas="48"),
        produto(3, "C5E", "Cabo de rede UTP Cat5e 4 pares caixa 305m VERTEX", 41000, categoria="5e"),
        produto(4, "C6", "Cabo de rede UTP Cat6 4 pares caixa 305m VERTEX", 68500, categoria="6"),
        produto(5, "F12", "Fonte chaveada 12V 5A bivolt PULSO", 4900, tensao="12"),
        produto(6, "F24", "Fonte chaveada 24V 5A bivolt PULSO", 7600, tensao="24"),
    ]


@pytest.fixture(scope="session")
def url_banco():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("defina TEST_DATABASE_URL (Postgres com a extensão pg_trgm) para rodar os testes de banco")
    import psycopg

    try:
        with psycopg.connect(url) as con:
            con.execute("create extension if not exists pg_trgm")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Postgres indisponível ou sem pg_trgm: {e}")
    return url


@pytest.fixture
def conectar(url_banco):
    """Esquema novo por teste, com migração e seed; some no fim."""
    import psycopg

    schema = "t_" + uuid.uuid4().hex[:10]
    with psycopg.connect(url_banco, autocommit=True) as admin:
        admin.execute(f"create schema {schema}")

    def abrir():
        return psycopg.connect(url_banco, options=f"-c search_path={schema},public")

    with abrir() as con:
        con.execute((RAIZ / "db/migrations/0001_schema.sql").read_text(encoding="utf-8"))
        con.execute((RAIZ / "db/seed.sql").read_text(encoding="utf-8"))
    yield abrir
    with psycopg.connect(url_banco, autocommit=True) as admin:
        admin.execute(f"drop schema {schema} cascade")
