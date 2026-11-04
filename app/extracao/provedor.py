"""Porta para o modelo de linguagem.

O resto do sistema só conhece `ProvedorLLM.completar(system, user) -> str`.
O adaptador HTTP fala o formato de chat JSON que a maioria das APIs aceita
(lista de mensagens com `role`/`content`); o fake serve aos testes e a quem
quer rodar o pipeline sem chave nenhuma.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

import httpx


class ProvedorLLM(Protocol):
    def completar(self, system: str, user: str, *, max_tokens: int = 4000) -> str: ...


class ErroProvedor(RuntimeError):
    pass


@dataclass
class ProvedorHTTP:
    """Chat completions genérico: POST {url} com {model, messages, temperature}."""

    url: str
    chave: str
    modelo: str
    timeout: float = 60.0
    temperatura: float = 0.0
    tokens_entrada: int = 0
    tokens_saida: int = 0

    def completar(self, system: str, user: str, *, max_tokens: int = 4000) -> str:
        corpo = {
            "model": self.modelo,
            "temperature": self.temperatura,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        cabecalhos = {"Authorization": f"Bearer {self.chave}", "Content-Type": "application/json"}
        try:
            r = httpx.post(self.url, json=corpo, headers=cabecalhos, timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ErroProvedor(f"falha ao chamar o modelo: {e}") from e
        dados = r.json()
        uso = dados.get("usage") or {}
        self.tokens_entrada += int(uso.get("prompt_tokens") or 0)
        self.tokens_saida += int(uso.get("completion_tokens") or 0)
        try:
            conteudo = dados["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ErroProvedor("resposta sem choices[0].message.content") from e
        if isinstance(conteudo, list):  # alguns servidores devolvem partes
            conteudo = "".join(p.get("text", "") for p in conteudo if isinstance(p, dict))
        return str(conteudo)


@dataclass
class ProvedorFake:
    """Devolve respostas enfileiradas ou calculadas por função; registra as chamadas."""

    respostas: list[str] = field(default_factory=list)
    funcao: Callable[[str, str], str] | None = None
    chamadas: list[tuple[str, str]] = field(default_factory=list)

    def completar(self, system: str, user: str, *, max_tokens: int = 4000) -> str:
        self.chamadas.append((system, user))
        if self.funcao is not None:
            return self.funcao(system, user)
        if not self.respostas:
            raise ErroProvedor("fake sem resposta enfileirada")
        return self.respostas.pop(0)


def recortar_json(raw: str) -> str:
    """Tira cerca de código e texto antes/depois do primeiro objeto JSON."""
    raw = re.sub(r"^```(?:json)?\s*", "", (raw or "").strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    inicio = raw.find("{")
    if inicio > 0:
        raw = raw[inicio:]
    return raw


def ler_json(raw: str) -> dict:
    """Primeiro objeto JSON da resposta, tolerando texto solto depois dele e vírgula sobrando.

    `json.loads` exige que a string inteira seja um documento; modelos às vezes
    emendam um comentário depois do JSON válido. `raw_decode` lê só o primeiro
    objeto e ignora o resto.
    """
    txt = recortar_json(raw)
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(txt)
    except ValueError:
        try:
            obj, _ = decoder.raw_decode(re.sub(r",\s*([}\]])", r"\1", txt))
        except ValueError as e:
            raise ValueError(f"resposta do modelo não é JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("resposta do modelo não é um objeto JSON")
    return obj
