"""Provedor de demonstração: roda o pipeline inteiro sem modelo de linguagem nenhum.

Extrai itens de linhas no formato "4x switch 24p" e escolhe o candidato de maior
similaridade. É uma regra simples, só para o `docker compose up` mostrar a tela
funcionando sem chave de API; ativa-se com `LLM_API_URL=demo`.
"""

from __future__ import annotations

import json
import re

from app.extracao.extrator import SYSTEM_EXTRACAO
from app.matching.scorer import similaridade

_LINHA = re.compile(r"^\s*(?:[-*]\s*)?(\d+(?:[.,]\d+)?)\s*(x|un|pc|cx|m)?\.?\s+(.+?)\s*$", re.I)
_CAND = re.compile(r"^\s*\[(\d+)\]\s*[^|]*\|\s*(.+)$")
_ITEM = re.compile(r"^--- Item (\d+) \((.*)\) ---$")


class ProvedorDemo:
    def completar(self, system: str, user: str, *, max_tokens: int = 4000) -> str:
        if system == SYSTEM_EXTRACAO:
            return json.dumps(self._extrair(user), ensure_ascii=False)
        return json.dumps(self._escolher(user), ensure_ascii=False)

    def _extrair(self, texto: str) -> dict:
        itens = []
        for linha in texto.splitlines():
            m = _LINHA.match(linha)
            if not m:
                continue
            qtd, un, desc = m.groups()
            itens.append(
                {
                    "descricao_original": desc,
                    "quantidade": float(qtd.replace(",", ".")),
                    "unidade": (un or "UN").upper().replace("X", "UN"),
                }
            )
        return {"itens": itens}

    def _escolher(self, prompt: str) -> dict:
        matches, atual, melhor = [], None, None
        pedidos = dict(re.findall(r"Item (\d+)\n  DESCRIÇÃO: (.+)", prompt))
        for linha in [*prompt.splitlines(), "--- Item 99999999 () ---"]:
            cab = _ITEM.match(linha)
            if cab:
                if atual is not None and melhor and melhor[0] >= 0.3:
                    conf = "alta" if melhor[0] >= 0.6 else "media"
                    matches.append({"indice": atual, "candidato": melhor[1], "confianca": conf,
                                    "motivo": "maior similaridade textual (provedor de demonstração)"})  # fmt: skip
                atual, melhor = int(cab.group(1)), None
                continue
            c = _CAND.match(linha)
            if c and atual is not None:
                s = similaridade(pedidos.get(str(atual), ""), c.group(2))
                if melhor is None or s > melhor[0]:
                    melhor = (s, int(c.group(1)))
        return {"matches": matches}
