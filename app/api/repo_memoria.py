from __future__ import annotations

import threading
from datetime import date

from app.extracao import CacheMemoria
from app.matching import BuscaPura, MemoriaEmMemoria, Produto
from app.matching.normalizacao import normalizar

from .esquemas import ItemOut, PropostaOut


class RepoMemoria:
    def __init__(self, produtos: list[Produto]) -> None:
        self.produtos = list(produtos)
        self.cache = CacheMemoria()
        self.memoria = MemoriaEmMemoria()
        self.busca = BuscaPura(self.produtos)
        self._propostas: dict[int, PropostaOut] = {}
        self._trava = threading.Lock()

    def produtos_por_id(self, ids: list[int]) -> dict[int, Produto]:
        return {p.id: p for p in self.produtos if p.id in set(ids)}

    def listar_produtos(self, q: str, limite: int = 20) -> list[Produto]:
        termos = normalizar(q).split()
        achados = [p for p in self.produtos if all(t in normalizar(f"{p.codigo} {p.descricao}") for t in termos)]
        return achados[:limite]

    def salvar_proposta(self, proposta: PropostaOut) -> PropostaOut:
        with self._trava:
            novo_id = len(self._propostas) + 1
            salva = proposta.model_copy(
                deep=True, update={"id": novo_id, "numero": f"COT-{date.today().year}-{novo_id:05d}"}
            )
            self._propostas[novo_id] = salva
            return salva.model_copy(deep=True)

    def obter_proposta(self, proposta_id: int) -> PropostaOut | None:
        with self._trava:
            p = self._propostas.get(proposta_id)
            return p.model_copy(deep=True) if p else None

    def salvar_item(self, proposta_id: int, item: ItemOut) -> None:
        with self._trava:
            p = self._propostas[proposta_id]
            p.itens = [item.model_copy(deep=True) if i.n == item.n else i for i in p.itens]
