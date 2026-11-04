"""Camada 1: memória de pares (texto do cliente -> produto) confirmados pelo operador.

Regras:
- A chave é a descrição normalizada. O escopo é o cliente (raiz do CNPJ, ou o
  nome normalizado quando não há CNPJ) e, depois, global.
- Cliente vence global. Dentro de um escopo, vale o produto com maior saldo
  (acertos - erros); empate é ambiguidade e o escopo não responde.
- O operador é a hierarquia superior. O que ele confirmou é fato: grava sempre.
  Erro só é contado quando a memória sugeriria OUTRO produto para a mesma
  entrada; aí a sugestão contrariada é rebaixada.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol

from .normalizacao import normalizar
from .tipos import Origem


@dataclass(frozen=True)
class Lembranca:
    produto_id: int
    origem: Origem


class MemoriaMatch(Protocol):
    def consultar(self, entradas: list[str], cliente: str, cnpj: str = "") -> dict[str, Lembranca]: ...

    def aprender(self, pares: list[tuple[str, int]], cliente: str, cnpj: str = "") -> dict[str, int]: ...


def escopo_cliente(cliente: str, cnpj: str = "") -> str:
    """Raiz do CNPJ (8 dígitos) identifica a empresa mesmo quando o nome muda; sem CNPJ, o nome."""
    digitos = re.sub(r"\D", "", cnpj or "")
    if len(digitos) == 14:
        return f"cnpj:{digitos[:8]}"
    nome = normalizar(cliente)
    return f"nome:{nome}" if nome else ""


def _melhor(saldos: dict[int, int]) -> int | None:
    positivos = {pid: s for pid, s in saldos.items() if s > 0}
    if not positivos:
        return None
    topo = max(positivos.values())
    vencedores = [pid for pid, s in positivos.items() if s == topo]
    return vencedores[0] if len(vencedores) == 1 else None


@dataclass
class MemoriaEmMemoria:
    """Implementação em dicionários: testes e modo demo."""

    # (entrada_norm, escopo) -> produto_id -> [acertos, erros]
    _contagens: dict[tuple[str, str], dict[int, list[int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: [0, 0]))
    )

    def _saldos(self, entrada: str, escopo: str) -> dict[int, int]:
        return {pid: a - e for pid, (a, e) in self._contagens.get((entrada, escopo), {}).items()}

    def consultar(self, entradas: list[str], cliente: str, cnpj: str = "") -> dict[str, Lembranca]:
        escopo = escopo_cliente(cliente, cnpj)
        saida: dict[str, Lembranca] = {}
        for texto in entradas:
            chave = normalizar(texto)
            if not chave:
                continue
            pid = _melhor(self._saldos(chave, escopo)) if escopo else None
            if pid is not None:
                saida[chave] = Lembranca(pid, "memoria_cliente")
                continue
            # global: soma de todos os escopos
            total: dict[int, int] = defaultdict(int)
            for (ent, _esc), por_prod in self._contagens.items():
                if ent == chave:
                    for p, (a, e) in por_prod.items():
                        total[p] += a - e
            pid = _melhor(total)
            if pid is not None:
                saida[chave] = Lembranca(pid, "memoria_global")
        return saida

    def aprender(self, pares: list[tuple[str, int]], cliente: str, cnpj: str = "") -> dict[str, int]:
        escopo = escopo_cliente(cliente, cnpj)
        antes = self.consultar([p[0] for p in pares], cliente, cnpj)
        acertos = erros = 0
        for texto, pid in pares:
            chave = normalizar(texto)
            if not chave:
                continue
            self._contagens[(chave, escopo)][pid][0] += 1
            acertos += 1
            sugerido = antes.get(chave)
            if sugerido and sugerido.produto_id != pid:
                for (ent, _esc), por_prod in self._contagens.items():
                    if ent == chave and sugerido.produto_id in por_prod:
                        por_prod[sugerido.produto_id][1] += 1
                erros += 1
        return {"aprendidos": acertos, "rebaixados": erros}


class MemoriaPostgres:
    """Tabela match_memoria; a função SQL memoria_match aplica a mesma precedência."""

    def __init__(self, conectar) -> None:
        self._conectar = conectar

    def consultar(self, entradas: list[str], cliente: str, cnpj: str = "") -> dict[str, Lembranca]:
        if not entradas:
            return {}
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(
                "select entrada_norm, produto_id, origem from memoria_match(%s, %s)",
                ([normalizar(e) for e in entradas], escopo_cliente(cliente, cnpj)),
            )
            return {ent: Lembranca(pid, origem) for ent, pid, origem in cur.fetchall()}

    def aprender(self, pares: list[tuple[str, int]], cliente: str, cnpj: str = "") -> dict[str, int]:
        escopo = escopo_cliente(cliente, cnpj)
        antes = self.consultar([p[0] for p in pares], cliente, cnpj)
        acertos = erros = 0
        with self._conectar() as con, con.cursor() as cur:
            for texto, pid in pares:
                chave = normalizar(texto)
                if not chave:
                    continue
                cur.execute(
                    """insert into match_memoria (entrada_norm, escopo, produto_id, acertos)
                       values (%s, %s, %s, 1)
                       on conflict (entrada_norm, escopo, produto_id)
                       do update set acertos = match_memoria.acertos + 1, ultima_vez = now()""",
                    (chave, escopo, pid),
                )
                acertos += 1
                sugerido = antes.get(chave)
                if sugerido and sugerido.produto_id != pid:
                    cur.execute(
                        """update match_memoria set erros = erros + 1, ultima_vez = now()
                           where entrada_norm = %s and produto_id = %s""",
                        (chave, sugerido.produto_id),
                    )
                    erros += 1
            con.commit()
        return {"aprendidos": acertos, "rebaixados": erros}
