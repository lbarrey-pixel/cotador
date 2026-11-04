"""Esquema do que o modelo extrai de um pedido de cotação."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


class ItemExtraido(BaseModel):
    descricao_original: str = Field(min_length=1)
    quantidade: float = 1
    unidade: str = "UN"
    codigo_cliente: str = ""
    atributos: dict[str, str] = Field(default_factory=dict)

    @field_validator("descricao_original")
    @classmethod
    def _apara(cls, v: str) -> str:
        # só espaço nas pontas: o texto do cliente é preservado como ele escreveu
        return v.strip()

    @field_validator("quantidade", mode="before")
    @classmethod
    def _quantidade(cls, v):
        if isinstance(v, str):
            s = v.strip().replace(".", "").replace(",", ".")
            try:
                v = float(s)
            except ValueError:
                v = 1
        return v if v and v > 0 else 1

    @field_validator("unidade", mode="before")
    @classmethod
    def _unidade(cls, v):
        return (str(v or "UN").strip().upper() or "UN")[:10]

    @field_validator("atributos", mode="before")
    @classmethod
    def _atributos(cls, v):
        if not isinstance(v, dict):
            return {}
        return {str(k).strip().lower(): str(val).strip() for k, val in v.items() if val not in (None, "")}


class PedidoExtraido(BaseModel):
    cliente: str = ""
    cnpj: str = ""
    destino: str = ""
    referencia: str = ""
    itens: list[ItemExtraido] = Field(default_factory=list)

    @field_validator("cnpj", mode="before")
    @classmethod
    def _cnpj(cls, v):
        return re.sub(r"\D", "", str(v or ""))

    @field_validator("cliente", "destino", "referencia", mode="before")
    @classmethod
    def _texto(cls, v):
        return str(v or "").strip()
