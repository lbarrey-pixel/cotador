"""Camadas 1 e 2 contra Postgres de verdade (pg_trgm, GiST, funções SQL). Pulam sem TEST_DATABASE_URL."""

from fastapi.testclient import TestClient

from app.api.repo_postgres import RepoPostgres
from app.config import Config
from app.extracao import ProvedorFake
from app.main import criar_app
from app.matching import MemoriaEmMemoria, MemoriaPostgres
from tests.test_api import modelo


def test_indice_gist_trigrama_existe(conectar):
    with conectar() as con:
        (definicao,) = con.execute(
            "select indexdef from pg_indexes "
            "where indexname = 'produtos_descricao_trgm' and schemaname = current_schema()"
        ).fetchone()
    assert "gist" in definicao and "gist_trgm_ops" in definicao


def test_busca_trigrama_devolve_top_n_ordenado_por_similaridade(conectar):
    repo = RepoPostgres(conectar)
    (lista,) = repo.busca.buscar(["switch 24 portas gigabit gerenciavel"], n=5)
    assert len(lista) == 5
    assert lista[0].produto.codigo == "NX-SW24G"
    sims = [c.similaridade for c in lista]
    assert sims == sorted(sims, reverse=True)


def test_busca_em_lote_mantem_a_ordem_dos_itens(conectar):
    repo = RepoPostgres(conectar)
    a, b = repo.busca.buscar(["nobreak 1500va", "camera ip 4mp bullet"], n=3)
    assert a[0].produto.codigo == "PL-NB1500"
    assert b[0].produto.codigo == "AL-CAM4B"


def test_memoria_postgres_segue_a_mesma_precedencia_da_memoria_em_python(conectar):
    pg, py = MemoriaPostgres(conectar), MemoriaEmMemoria()
    passos = [
        ([("fonte 12v", 25)], "A", "11.222.333/0001-81"),
        ([("fonte 12v", 26)], "B", ""),
        ([("fonte 12v", 26)], "C", ""),
        ([("fonte 12v", 27)], "A", "11.222.333/0001-81"),  # operador corrige a sugestão
    ]
    for pares, cliente, cnpj in passos:
        assert pg.aprender(pares, cliente, cnpj) == py.aprender(pares, cliente, cnpj)
    for cliente, cnpj in [("A", "11.222.333/0001-81"), ("B", ""), ("Novo", "")]:
        assert pg.consultar(["Fonte 12V", "outra coisa"], cliente, cnpj) == py.consultar(
            ["Fonte 12V", "outra coisa"], cliente, cnpj
        )


def test_seed_traz_memoria_do_cliente_e_global(conectar):
    mem = MemoriaPostgres(conectar)
    r = mem.consultar(["Patch panel 24 portas"], "Horizonte Redes Ltda", "12.345.678/0001-95")
    assert r["patch panel 24 portas"].origem == "memoria_cliente"
    assert mem.consultar(["Fonte 12V 5A"], "Qualquer")["fonte 12v 5a"].origem == "memoria_global"


def test_repo_guarda_proposta_e_cache(conectar):
    repo = RepoPostgres(conectar)
    p = repo.obter_proposta(1)
    assert p.numero == "COT-2026-00001" and len(p.itens) == 4
    assert p.itens[0].produto_codigo == "NX-SW24G"
    assert repo.cache.obter("k") is None
    repo.cache.guardar("k", {"a": 1})
    assert repo.cache.obter("k") == {"a": 1}
    assert [x.codigo for x in repo.listar_produtos("sw24p")] == ["NX-SW24P"]
    assert repo.listar_produtos("100%") == []  # % e _ são literais na busca


def test_api_fim_a_fim_no_postgres(conectar):
    client = TestClient(criar_app(RepoPostgres(conectar), ProvedorFake(funcao=modelo), Config()))
    r = client.post("/propostas/extrair", data={"texto": "4x switch 24p\n2 cx cabo cat6"})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["id"] == 3 and p["itens"][0]["produto_codigo"] == "NX-SW24G"
    assert client.get(f"/propostas/{p['id']}").json() == p
    (fonte,) = client.get("/produtos", params={"q": "PL-FT12-5"}).json()
    r = client.put(f"/propostas/{p['id']}/itens/3", json={"produto_id": fonte["id"]})
    assert r.json()["produto_codigo"] == "PL-FT12-5"
    assert client.get(f"/propostas/{p['id']}").json()["itens"][2]["origem"] == "operador"
    csv_ = client.post(f"/propostas/{p['id']}/csv")
    assert csv_.status_code == 200 and p["numero"].encode() in csv_.content
