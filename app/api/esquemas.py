"""Contratos de entrada e saída da API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProdutoOut(BaseModel):
    id: int
    codigo: str
    descricao: str
    preco_custo_centavos: int = 0


class CandidatoOut(BaseModel):
    produto_id: int
    codigo: str
    descricao: str
    similaridade: float
    descartado_por: str | None = None


class ItemOut(BaseModel):
    n: int
    descricao_original: str
    quantidade: float = 1
    unidade: str = "UN"
    atributos: dict[str, str] = Field(default_factory=dict)
    produto_id: int | None = None
    produto_codigo: str = ""
    produto_descricao: str = ""
    confianca: str = "nenhuma"
    origem: str = "nenhuma"
    motivo: str = ""
    preco_un_centavos: int = 0
    candidatos: list[CandidatoOut] = Field(default_factory=list)


class PropostaOut(BaseModel):
    id: int = 0
    numero: str = ""
    referencia: str = ""
    cliente: str = ""
    cnpj: str = ""
    destino: str = ""
    frete_centavos: int = 0
    prazo_entrega: str = ""
    observacoes: str = ""
    avisos: list[str] = Field(default_factory=list)
    itens: list[ItemOut] = Field(default_factory=list)


class ItemIn(BaseModel):
    """Só os campos enviados mudam; `produto_id: null` desfaz o vínculo."""

    produto_id: int | None = None
    quantidade: float | None = Field(default=None, gt=0)
    preco_un_centavos: int | None = Field(default=None, ge=0)


class CsvIn(BaseModel):
    frete_centavos: int = Field(default=0, ge=0)
    prazo_entrega: str = ""
    observacoes: str = ""
