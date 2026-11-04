"""Camada 3: o modelo escolhe entre os candidatos, em lotes pequenos.

Lote pequeno é deliberado. Um prompt com 40 itens x 40 candidatos passa de
40 mil tokens, estoura o teto de saída e, quando falha, derruba a proposta
inteira. Com lotes de 8, uma falha afeta só aquele lote; a nova tentativa
divide o lote ao meio, então um item problemático acaba isolado.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass

from app.extracao.provedor import ProvedorLLM, ler_json

from .tipos import Candidato, Confianca, ItemParaCasar

TAMANHO_LOTE = 8
PARALELISMO = 4
CONFIANCAS: tuple[Confianca, ...] = ("alta", "media", "baixa")

SYSTEM_SELECAO = """Você é especialista em materiais de telecom, redes, energia e segurança eletrônica.
Para cada item solicitado, decida se algum candidato do catálogo é O MESMO ITEM e explique por quê,
como um colega experiente faria antes de fechar a venda.

Responda APENAS com JSON compacto, numa linha, sem markdown:
{"matches":[{"indice":0,"candidato":0,"confianca":"alta","motivo":"..."}]}

- "candidato" é o número entre colchetes do candidato escolhido, ou null se nenhum serve.
- "confianca": "alta" = mesmo produto, mesma especificação, mesmo fabricante quando citado;
  "media" = mesmo produto e especificação, cliente não citou fabricante;
  "baixa" = parecido, mas com dúvida real; devolva o candidato e diga a dúvida no motivo.
- Fabricante diferente, categoria diferente ou atributo técnico divergente (bitola, tensão,
  portas, polos, categoria de cabo, capacidade) = não é o mesmo item: candidato null.
- Cor não diferencia cabo elétrico nem cabo de rede.
- "motivo": uma frase concreta ("cliente pede 2,5mm², catálogo tem 4mm²"), nunca genérica.
- Falso negativo é melhor que falso positivo: na dúvida, null."""


@dataclass
class Escolha:
    indice: int
    posicao: int | None
    confianca: Confianca | str
    motivo: str


def montar_prompt(itens: list[ItemParaCasar], candidatos: dict[int, list[Candidato]]) -> str:
    partes = ["Itens solicitados:"]
    for it in itens:
        partes.append(f"\nItem {it.indice}\n  DESCRIÇÃO: {it.descricao}")
        if it.atributos:
            specs = ", ".join(f"{k}={v}" for k, v in sorted(it.atributos.items()))
            partes.append(f"  ATRIBUTOS: {specs}")
        else:
            partes.append("  ATRIBUTOS: (não informados)")
    partes.append("\nCandidatos do catálogo:")
    for it in itens:
        partes.append(f"\n--- Item {it.indice} ({it.descricao[:60]}) ---")
        for j, c in enumerate(candidatos.get(it.indice, [])):
            if c.descartado_por:
                continue
            partes.append(f"  [{j}] {c.produto.codigo} | {c.produto.descricao}")
    return "\n".join(partes)


def ler_escolhas(bruto: str, validos: dict[int, int]) -> dict[int, Escolha]:
    """`validos` mapeia índice do item -> quantidade de candidatos; posição fora da faixa vira null."""
    obj = ler_json(bruto)
    saida: dict[int, Escolha] = {}
    for m in obj.get("matches") or []:
        if not isinstance(m, dict):
            continue
        try:
            indice = int(m.get("indice"))
        except (TypeError, ValueError):
            continue
        if indice not in validos:
            continue
        pos = m.get("candidato")
        try:
            pos = int(pos) if pos is not None else None
        except (TypeError, ValueError):
            pos = None
        if pos is not None and not (0 <= pos < validos[indice]):
            pos = None
        conf = str(m.get("confianca") or "").lower()
        if pos is None or conf not in CONFIANCAS:
            pos, conf = None, "nenhuma"
        saida[indice] = Escolha(indice, pos, conf, str(m.get("motivo") or "").strip()[:300])
    return saida


@dataclass
class Seletor:
    provedor: ProvedorLLM
    tamanho_lote: int = TAMANHO_LOTE
    paralelismo: int = PARALELISMO

    def escolher(
        self, itens: list[ItemParaCasar], candidatos: dict[int, list[Candidato]]
    ) -> tuple[dict[int, Escolha], list[str]]:
        """Escolhas por índice de item e avisos de lotes que falharam (estado local: seguro entre requisições)."""
        falhas: list[str] = []
        com_candidatos = [it for it in itens if any(not c.descartado_por for c in candidatos.get(it.indice, []))]
        lotes = [com_candidatos[i : i + self.tamanho_lote] for i in range(0, len(com_candidatos), self.tamanho_lote)]
        escolhas: dict[int, Escolha] = {}
        if len(lotes) <= 1:
            for lote in lotes:
                escolhas.update(self._lote_seguro(lote, candidatos, falhas))
            return escolhas, falhas
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.paralelismo, len(lotes))) as ex:
            for parcial in ex.map(lambda lote: self._lote_seguro(lote, candidatos, falhas), lotes):
                escolhas.update(parcial)
        return escolhas, falhas

    def _lote_seguro(self, lote, candidatos, falhas: list[str]) -> dict[int, Escolha]:
        """Falhou: divide o lote ao meio e tenta cada metade, até isolar o item que quebra."""
        try:
            return self._chamar(lote, candidatos)
        except Exception as e:  # noqa: BLE001 - lote que falha não pode derrubar os outros
            if len(lote) > 1:
                meio = len(lote) // 2
                r = self._lote_seguro(lote[:meio], candidatos, falhas)
                r.update(self._lote_seguro(lote[meio:], candidatos, falhas))
                return r
            falhas.append(f"1 item(ns) sem decisão do modelo: {type(e).__name__}: {e}"[:300])
            return {}

    def _chamar(self, lote, candidatos) -> dict[int, Escolha]:
        validos = {it.indice: len(candidatos.get(it.indice, [])) for it in lote}
        bruto = self.provedor.completar(SYSTEM_SELECAO, montar_prompt(lote, candidatos), max_tokens=4000)
        return ler_escolhas(bruto, validos)
