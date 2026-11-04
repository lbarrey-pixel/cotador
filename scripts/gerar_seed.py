"""Gera db/seed.sql a partir de db/catalogo.csv (fonte única do catálogo de exemplo).

    python scripts/gerar_seed.py          # reescreve db/seed.sql
    python scripts/gerar_seed.py --check  # falha se o arquivo estiver desatualizado

Os dois CNPJs das propostas de exemplo são calculados aqui com dígito verificador
válido; não pertencem a empresas reais.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.exportacao import cnpj_valido  # noqa: E402


def cnpj_com_dv(base12: str) -> str:
    def dv(b: str, pesos: list[int]) -> str:
        r = sum(int(d) * p for d, p in zip(b, pesos, strict=True)) % 11
        return "0" if r < 2 else str(11 - r)

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = dv(base12, p1)
    d2 = dv(base12 + d1, [6, *p1])
    return base12 + d1 + d2


def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


PROPOSTAS = [
    {
        "numero": "COT-2026-00001",
        "referencia": "RFQ-0412",
        "cliente": "Horizonte Redes Ltda",
        "cnpj": cnpj_com_dv("123456780001"),
        "destino": "Campinas/SP",
        "itens": [
            ("Switch 24p gigabit gerenciavel", 4, "UN", "NX-SW24G", "alta", "modelo"),
            ("Cabo UTP cat6 azul cx 305m", 6, "CX", "VX-C6-305", "alta", "modelo"),
            ("Patch cord cat6 1,5m", 120, "UN", "VX-PC6-15", "media", "modelo"),
            ("Patch panel 24 portas", 4, "UN", "VX-PP24", "alta", "memoria_cliente"),
        ],
    },
    {
        "numero": "COT-2026-00002",
        "referencia": "",
        "cliente": "Condomínio Parque das Acácias",
        "cnpj": cnpj_com_dv("987654320001"),
        "destino": "Belo Horizonte/MG",
        "itens": [
            ("Camera IP 4MP bullet", 8, "UN", "AL-CAM4B", "alta", "modelo"),
            ("NVR 16 canais", 1, "UN", "AL-NVR16", "media", "modelo"),
            ("HD 4TB p/ CFTV", 2, "UN", "AL-HD4T", "alta", "modelo"),
            ("Fonte 12V 10A", 2, "UN", None, "nenhuma", "nenhuma"),
        ],
    },
]

MEMORIA = [
    ("patch panel 24 portas", "cnpj:12345678", "VX-PP24", 2),
    ("fonte 12v 5a", "", "PL-FT12-5", 3),
]


def gerar() -> str:
    with open(RAIZ / "db" / "catalogo.csv", encoding="utf-8", newline="") as f:
        produtos = list(csv.DictReader(f, delimiter=";"))
    ids = {p["codigo"]: i for i, p in enumerate(produtos, 1)}
    out = ["-- Gerado por scripts/gerar_seed.py a partir de db/catalogo.csv. Não edite à mão.", ""]
    out.append("insert into produtos (id, codigo, descricao, atributos, preco_custo_centavos, ncm) values")
    out.append(
        ",\n".join(
            f"  ({ids[p['codigo']]}, {q(p['codigo'])}, {q(p['descricao'])}, {q(p['atributos'])}::jsonb, "
            f"{int(p['preco_custo_centavos'])}, {q(p['ncm'])})"
            for p in produtos
        )
        + "\non conflict (id) do nothing;"
    )
    out.append("")
    for i, pr in enumerate(PROPOSTAS, 1):
        assert cnpj_valido(pr["cnpj"])
        out.append(
            "insert into propostas (id, numero, referencia, cliente, cnpj, destino) values "
            f"({i}, {q(pr['numero'])}, {q(pr['referencia'])}, {q(pr['cliente'])}, {q(pr['cnpj'])}, "
            f"{q(pr['destino'])}) on conflict (id) do nothing;"
        )
        linhas = []
        for n, (desc, qtd, un, cod, conf, orig) in enumerate(pr["itens"], 1):
            pid = str(ids[cod]) if cod else "null"
            custo = int(next(p for p in produtos if p["codigo"] == cod)["preco_custo_centavos"]) if cod else 0
            preco = custo * 130 // 100
            linhas.append(f"  ({i}, {n}, {q(desc)}, {qtd}, {q(un)}, {pid}, {q(conf)}, {q(orig)}, {preco})")
        out.append(
            "insert into itens_proposta (proposta_id, n, descricao_original, quantidade, unidade, "
            "produto_id, confianca, origem, preco_un_centavos) values\n"
            + ",\n".join(linhas)
            + "\non conflict (proposta_id, n) do nothing;"
        )
        out.append("")
    out.append("insert into match_memoria (entrada_norm, escopo, produto_id, acertos) values")
    out.append(
        ",\n".join(f"  ({q(e)}, {q(esc)}, {ids[c]}, {a})" for e, esc, c, a in MEMORIA) + "\non conflict do nothing;"
    )
    out.append("")
    out.append("select setval(pg_get_serial_sequence('produtos', 'id'), (select max(id) from produtos));")
    out.append("select setval(pg_get_serial_sequence('propostas', 'id'), (select max(id) from propostas));")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    destino = RAIZ / "db" / "seed.sql"
    novo = gerar()
    if "--check" in sys.argv:
        if not destino.exists() or destino.read_text(encoding="utf-8") != novo:
            sys.exit("db/seed.sql desatualizado: rode python scripts/gerar_seed.py")
    else:
        destino.write_text(novo, encoding="utf-8")
        print(f"{destino.relative_to(RAIZ)} escrito")
