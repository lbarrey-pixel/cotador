from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Confianca = Literal["alta", "media", "baixa", "nenhuma"]
Origem = Literal["memoria_cliente", "memoria_global", "modelo", "nenhuma"]


@dataclass(frozen=True)
class Produto:
    id: int
    codigo: str
    descricao: str
    atributos: dict[str, str] = field(default_factory=dict, hash=False, compare=False)
    preco_custo_centavos: int = 0
    ncm: str = ""


@dataclass
class Candidato:
    produto: Produto
    similaridade: float
    descartado_por: str | None = None  # atributo crítico divergente


@dataclass
class ItemParaCasar:
    indice: int
    descricao: str
    atributos: dict[str, str] = field(default_factory=dict)


@dataclass
class ResultadoMatch:
    indice: int
    produto: Produto | None
    confianca: Confianca
    origem: Origem
    motivo: str
    candidatos: list[Candidato] = field(default_factory=list)
