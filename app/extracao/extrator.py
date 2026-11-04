"""Documento canônico -> PedidoExtraido, via modelo de linguagem, com cache."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from app.ingestao import Documento

from .modelos import PedidoExtraido
from .provedor import ProvedorLLM, ler_json

SYSTEM_EXTRACAO = """Você lê pedidos de cotação de material de telecom, redes, energia e segurança
eletrônica e devolve os itens pedidos em JSON. Regras:
- "descricao_original" é o texto do cliente EXATAMENTE como ele escreveu, sem corrigir,
  resumir ou traduzir. É a chave do histórico de preços.
- "quantidade" numérica; "unidade" como o cliente escreveu (UN, PC, M, CX...). Se não houver, UN e 1.
- "codigo_cliente" é o código do item no sistema do cliente, se aparecer na linha.
- "atributos" são especificações técnicas que aparecem no texto, em pares curtos:
  tensao, portas, capacidade, categoria, bitola, comprimento, cor, fabricante, modelo.
  Só o que está escrito. Não deduza.
- Linhas iniciadas por [CITAÇÃO] vêm de e-mails anteriores e não são pedido novo.
- Linha idêntica repetida na mesma tabela é um item só com as quantidades somadas.
- Responda apenas com o JSON, sem comentário:
{"cliente": "", "cnpj": "", "destino": "", "referencia": "",
 "itens": [{"descricao_original": "", "quantidade": 1, "unidade": "UN",
            "codigo_cliente": "", "atributos": {}}]}"""


class CacheExtracao(Protocol):
    def obter(self, chave: str) -> dict | None: ...
    def guardar(self, chave: str, valor: dict) -> None: ...


class CacheMemoria:
    def __init__(self) -> None:
        self._dados: dict[str, dict] = {}

    def obter(self, chave: str) -> dict | None:
        return self._dados.get(chave)

    def guardar(self, chave: str, valor: dict) -> None:
        self._dados[chave] = valor


def chave_cache(texto: str, versao_prompt: str = SYSTEM_EXTRACAO) -> str:
    h = hashlib.sha256()
    h.update(versao_prompt.encode())
    h.update(b"\0")
    h.update(texto.encode())
    return h.hexdigest()


class ErroExtracao(RuntimeError):
    pass


@dataclass
class Extrator:
    provedor: ProvedorLLM
    cache: CacheExtracao | None = None

    def extrair(self, documento: Documento, texto_extra: str = "") -> PedidoExtraido:
        texto = documento.render_texto()
        if texto_extra.strip():
            texto += "\n\n[OBSERVAÇÃO DO OPERADOR]\n" + texto_extra.strip()
        if not texto.strip():
            return PedidoExtraido()

        chave = chave_cache(texto)
        if self.cache is not None:
            guardado = self.cache.obter(chave)
            if guardado is not None:
                return PedidoExtraido.model_validate(guardado)

        pedido = self._pedir(texto)
        if self.cache is not None:
            self.cache.guardar(chave, pedido.model_dump())
        return pedido

    def _pedir(self, texto: str) -> PedidoExtraido:
        """Uma chamada; se a resposta não validar, repete uma vez mostrando o erro ao modelo."""
        bruto = self.provedor.completar(SYSTEM_EXTRACAO, texto, max_tokens=8000)
        try:
            return _validar(bruto)
        except ValueError as primeiro_erro:
            pedido_correcao = (
                f"{texto}\n\n[A resposta anterior foi rejeitada: {primeiro_erro}. "
                "Devolva o mesmo conteúdo como JSON válido no formato pedido.]"
            )
            bruto2 = self.provedor.completar(SYSTEM_EXTRACAO, pedido_correcao, max_tokens=8000)
            try:
                return _validar(bruto2)
            except ValueError as e:
                raise ErroExtracao(f"modelo não devolveu JSON válido em duas tentativas: {e}") from e


def _validar(bruto: str) -> PedidoExtraido:
    obj = ler_json(bruto)
    try:
        return PedidoExtraido.model_validate(obj)
    except ValidationError as e:
        raise ValueError(json.dumps(e.errors(include_url=False), ensure_ascii=False)[:500]) from e
