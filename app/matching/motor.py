"""Orquestra as três camadas: memória -> candidatos -> modelo.

A memória resolve sem chamar o modelo. O que sobra vai ao banco buscar
candidatos; candidatos com atributo crítico divergente são descartados antes
de o modelo ver a lista. A memória vence o modelo: entra por último e sobrescreve.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .atributos import atributos_do_item, divergencia_critica
from .candidatos import BuscaCandidatos
from .memoria import MemoriaMatch
from .normalizacao import normalizar
from .seletor import Seletor
from .tipos import Candidato, ItemParaCasar, Produto, ResultadoMatch


def filtrar_por_atributos(item: ItemParaCasar, candidatos: list[Candidato]) -> list[Candidato]:
    """Marca (não remove) os divergentes; o operador ainda vê por que caíram."""
    atrib_item = atributos_do_item(item.descricao, item.atributos)
    for c in candidatos:
        atrib_prod = atributos_do_item(c.produto.descricao, c.produto.atributos)
        c.descartado_por = divergencia_critica(atrib_item, atrib_prod)
    return candidatos


@dataclass
class MotorMatching:
    memoria: MemoriaMatch
    busca: BuscaCandidatos
    buscar_produtos: Callable[[list[int]], dict[int, Produto]]  # resolve os ids que a memória devolve
    seletor: Seletor | None = None
    avisos: list[str] = field(default_factory=list)

    def casar(self, itens: list[ItemParaCasar], cliente: str = "", cnpj: str = "") -> list[ResultadoMatch]:
        if not itens:
            return []
        resultados: dict[int, ResultadoMatch] = {}

        # [1] memória
        lembradas = self.memoria.consultar([it.descricao for it in itens], cliente, cnpj)
        produtos_mem = self.buscar_produtos(sorted({lem.produto_id for lem in lembradas.values()})) if lembradas else {}
        for it in itens:
            lem = lembradas.get(normalizar(it.descricao))
            if lem and lem.produto_id in produtos_mem:
                resultados[it.indice] = ResultadoMatch(
                    it.indice, produtos_mem[lem.produto_id], "alta", lem.origem, "já confirmado pelo operador"
                )

        # [2] candidatos
        pendentes = [it for it in itens if it.indice not in resultados]
        candidatos: dict[int, list[Candidato]] = {}
        if pendentes:
            try:
                listas = self.busca.buscar([it.descricao for it in pendentes])
            except Exception as e:  # noqa: BLE001 - falha de busca é aviso, não "não achei"
                self.avisos.append(f"busca de candidatos falhou: {type(e).__name__}: {e}"[:300])
                listas = [[] for _ in pendentes]
            for it, lista in zip(pendentes, listas, strict=True):
                candidatos[it.indice] = filtrar_por_atributos(it, lista)

        # [3] modelo
        escolhas = {}
        if pendentes and self.seletor is not None:
            escolhas, falhas = self.seletor.escolher(pendentes, candidatos)
            self.avisos.extend(falhas)

        for it in pendentes:
            lista = candidatos.get(it.indice, [])
            esc = escolhas.get(it.indice)
            if esc and esc.posicao is not None and not lista[esc.posicao].descartado_por:
                resultados[it.indice] = ResultadoMatch(
                    it.indice, lista[esc.posicao].produto, esc.confianca, "modelo", esc.motivo, lista
                )
            else:
                motivo = esc.motivo if esc else ("sem candidato parecido" if not lista else "sem decisão")
                resultados[it.indice] = ResultadoMatch(it.indice, None, "nenhuma", "nenhuma", motivo, lista)

        return [resultados[it.indice] for it in itens]


def produtos_por_id(produtos: list[Produto]):
    indice = {p.id: p for p in produtos}
    return lambda ids: {i: indice[i] for i in ids if i in indice}
