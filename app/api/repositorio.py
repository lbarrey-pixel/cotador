"""Porta de persistência da API.

A API só fala com `Repositorio`. `RepoPostgres` é o de verdade; `RepoMemoria`
roda os testes e o modo demo sem banco, com o mesmo contrato.
"""

from __future__ import annotations

from typing import Protocol

from app.extracao import CacheExtracao
from app.matching import BuscaCandidatos, MemoriaMatch, Produto

from .esquemas import ItemOut, PropostaOut


class Repositorio(Protocol):
    cache: CacheExtracao
    memoria: MemoriaMatch
    busca: BuscaCandidatos

    def produtos_por_id(self, ids: list[int]) -> dict[int, Produto]: ...

    def listar_produtos(self, q: str, limite: int = 20) -> list[Produto]: ...

    def salvar_proposta(self, proposta: PropostaOut) -> PropostaOut:
        """Grava com id e número novos e devolve a proposta como ficou."""
        ...

    def obter_proposta(self, proposta_id: int) -> PropostaOut | None: ...

    def salvar_item(self, proposta_id: int, item: ItemOut) -> None: ...
