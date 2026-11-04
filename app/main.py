"""Fábrica da aplicação FastAPI.

uvicorn app.main:criar_app_do_ambiente --factory
"""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import VERSAO
from app.api.repo_memoria import RepoMemoria
from app.api.repo_postgres import RepoPostgres, conectar_com
from app.api.repositorio import Repositorio
from app.api.rotas import router
from app.config import Config
from app.demo import ProvedorDemo
from app.extracao import ErroProvedor, ProvedorHTTP, ProvedorLLM
from app.matching import Produto

CATALOGO_DEMO = Path(__file__).resolve().parent.parent / "db" / "catalogo.csv"


class ProvedorIndisponivel:
    def completar(self, system: str, user: str, *, max_tokens: int = 4000) -> str:
        raise ErroProvedor("modelo não configurado: defina LLM_API_URL, LLM_API_KEY e LLM_MODEL (ou LLM_API_URL=demo)")


def criar_app(repo: Repositorio, provedor: ProvedorLLM, config: Config | None = None) -> FastAPI:
    config = config or Config()
    app = FastAPI(title="Cotador", version=VERSAO)
    app.state.repo, app.state.provedor, app.state.config = repo, provedor, config
    if config.cors_origens:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origens),
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["*"],
            expose_headers=["Content-Disposition"],
        )
    app.include_router(router)

    @app.get("/saude")
    def saude() -> dict[str, str]:
        return {"status": "ok", "versao": VERSAO}

    return app


def _provedor(cfg: Config) -> ProvedorLLM:
    if cfg.llm_api_url == "demo":
        return ProvedorDemo()
    if cfg.llm_api_url:
        return ProvedorHTTP(cfg.llm_api_url, cfg.llm_api_key, cfg.llm_model)
    return ProvedorIndisponivel()


def _catalogo_demo() -> list[Produto]:
    import json

    with open(CATALOGO_DEMO, encoding="utf-8", newline="") as f:
        return [
            Produto(
                i, r["codigo"], r["descricao"], json.loads(r["atributos"]), int(r["preco_custo_centavos"]), r["ncm"]
            )
            for i, r in enumerate(csv.DictReader(f, delimiter=";"), 1)
        ]


def criar_app_do_ambiente() -> FastAPI:
    cfg = Config.do_ambiente()
    repo: Repositorio = (
        RepoPostgres(conectar_com(cfg.database_url)) if cfg.database_url else RepoMemoria(_catalogo_demo())
    )
    return criar_app(repo, _provedor(cfg), cfg)
