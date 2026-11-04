import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.repo_memoria import RepoMemoria
from app.config import Config
from app.demo import ProvedorDemo
from app.exportacao import cnpj_valido
from app.main import _catalogo_demo, criar_app

RAIZ = Path(__file__).resolve().parent.parent


def test_seed_esta_em_dia_com_o_catalogo():
    r = subprocess.run([sys.executable, "scripts/gerar_seed.py", "--check"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_catalogo_sintetico_e_coerente():
    produtos = _catalogo_demo()
    assert 35 <= len(produtos) <= 60
    assert len({p.codigo for p in produtos}) == len(produtos)
    sql = (RAIZ / "db" / "seed.sql").read_text(encoding="utf-8")
    import re

    for cnpj in re.findall(r"'(\d{14})'", sql):
        assert cnpj_valido(cnpj)
    assert "@" not in sql


def test_pipeline_completo_com_o_provedor_de_demonstracao():
    client = TestClient(criar_app(RepoMemoria(_catalogo_demo()), ProvedorDemo(), Config()))
    texto = "Prezados\n\n4x switch 24 portas gigabit gerenciavel\n6 cx cabo utp cat6 azul 305m\n2 un fonte 12v 10a"
    r = client.post("/propostas/extrair", data={"texto": texto})
    assert r.status_code == 201
    codigos = [i["produto_codigo"] for i in r.json()["itens"]]
    assert codigos == ["NX-SW24G", "VX-C6-305", "PL-FT12-10"]
