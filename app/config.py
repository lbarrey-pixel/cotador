"""Configuração por variável de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    database_url: str = ""
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    margem_padrao_pct: int = 30
    cors_origens: tuple[str, ...] = field(default_factory=tuple)
    upload_max_bytes: int = 10 * 1024 * 1024

    @classmethod
    def do_ambiente(cls, env: dict[str, str] | None = None) -> Config:
        e = os.environ if env is None else env
        return cls(
            database_url=e.get("DATABASE_URL", ""),
            llm_api_url=e.get("LLM_API_URL", ""),
            llm_api_key=e.get("LLM_API_KEY", ""),
            llm_model=e.get("LLM_MODEL", ""),
            margem_padrao_pct=int(e.get("MARGEM_PADRAO_PCT", "30")),
            cors_origens=tuple(o.strip() for o in e.get("CORS_ORIGINS", "").split(",") if o.strip()),
        )
