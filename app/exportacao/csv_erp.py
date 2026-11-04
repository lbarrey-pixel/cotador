"""Arquivo de importação de propostas do ERP.

O ERP aceita só este layout: 45 colunas com os nomes exatos do cabeçalho,
separador `,` (valores com vírgula decimal vão entre aspas), UTF-8 com BOM e CRLF. Cada
item da proposta é uma linha, e todas repetem o "Número da proposta" (é ele
que agrupa as linhas na importação). Nada aqui conhece banco ou API.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date

# fmt: off
COLUNAS: tuple[str, ...] = (
    "ID", "Número da proposta", "Data", "Data proximo contato", "ID contato",
    "Nome do contato", "Aos cuidados de", "Lista de Preço", "Tipo de Pessoa", "CPF/CNPJ",
    "RG/IE", "CEP", "Município", "UF", "Endereço", "Endereço Nro", "Complemento", "Bairro",
    "Fone", "Celular", "E-mail", "Desconto", "Frete", "Observações", "Validade",
    "Prazo de Entrega", "Situação", "Introdução", "ID produto", "Descrição", "Quantidade",
    "Valor unitário", "Descrição complementar", "Vendedor", "Destinatário",
    "CPF/CNPJ entrega", "CEP entrega", "Município entrega", "UF entrega",
    "Endereço entrega", "Endereço Nro entrega", "Complemento entrega", "Bairro entrega",
    "Fone entrega", "Inscrição Estadual entrega",
)
# fmt: on

VALIDADE_DIAS = "5"


class ErroExportacao(ValueError):
    pass


@dataclass
class LinhaCSV:
    descricao: str
    quantidade: float
    unidade: str
    preco_un_centavos: int
    complemento: str = ""


@dataclass
class DadosCSV:
    numero_proposta: str
    cliente: str
    cnpj: str = ""
    itens: list[LinhaCSV] = field(default_factory=list)
    frete_centavos: int = 0
    prazo_entrega: str = ""
    observacoes: str = ""


def fmt_preco(centavos: int) -> str:
    """Valor unitário com 3 casas e ponto de milhar: 123456 -> '1.234,560'.

    O ERP lê o campo com três decimais; centavos inteiros entram sem passar
    por float, então 0,10 + 0,20 nunca vira 0,30000000000000004 no arquivo.
    """
    try:
        c = int(centavos)
    except (TypeError, ValueError):
        return "0,000"
    c = max(c, 0)
    reais, resto = divmod(c, 100)
    return f"{reais:,}".replace(",", ".") + f",{resto * 10:03d}"


def fmt_quantidade(q: float) -> str:
    return f"{float(q):.2f}".replace(".", ",")


def _fmt_moeda(centavos: int) -> str:
    reais, resto = divmod(max(int(centavos), 0), 100)
    return f"{reais},{resto:02d}"


def cnpj_valido(cnpj: str) -> bool:
    n = re.sub(r"\D", "", cnpj or "")
    if len(n) != 14 or n == n[0] * 14:
        return False

    def dv(base: str, pesos: list[int]) -> str:
        r = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) % 11
        return "0" if r < 2 else str(11 - r)

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return n[12] == dv(n[:12], p1) and n[13] == dv(n[:13], [6, *p1])


def cnpj_formatado(cnpj: str) -> str:
    n = re.sub(r"\D", "", cnpj or "")
    if len(n) != 14:
        return cnpj or ""
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def gerar_csv(dados: DadosCSV, hoje: date | None = None) -> bytes:
    """Bytes prontos para download. CNPJ inválido sai vazio e o valor lido vai para as Observações."""
    numero = (dados.numero_proposta or "").strip()
    if not numero:
        raise ErroExportacao("proposta sem número: o ERP agruparia os itens errado")
    if not dados.itens:
        raise ErroExportacao("proposta sem itens")

    cnpj_bruto = (dados.cnpj or "").strip()
    ok = cnpj_valido(cnpj_bruto)
    obs = dados.observacoes.strip()
    if cnpj_bruto and not ok:
        aviso = f"CNPJ lido (inválido, conferir): {cnpj_bruto}"
        obs = f"{obs} | {aviso}" if obs else aviso

    data = (hoje or date.today()).strftime("%d/%m/%Y")
    saida = io.StringIO(newline="")
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS, delimiter=",", lineterminator="\r\n")
    escritor.writeheader()
    for it in dados.itens:
        linha = dict.fromkeys(COLUNAS, "")
        linha.update(
            {
                "Número da proposta": numero,
                "Data": data,
                "Nome do contato": dados.cliente,
                "Tipo de Pessoa": "J",
                "CPF/CNPJ": cnpj_formatado(cnpj_bruto) if ok else "",
                "Desconto": "0,00",
                "Frete": _fmt_moeda(dados.frete_centavos),
                "Observações": obs,
                "Validade": VALIDADE_DIAS,
                "Prazo de Entrega": dados.prazo_entrega,
                "Situação": "Rascunho",
                "ID produto": "0",
                "Descrição": it.descricao,
                "Quantidade": fmt_quantidade(it.quantidade),
                "Valor unitário": fmt_preco(it.preco_un_centavos),
                "Descrição complementar": " | ".join(x for x in (it.unidade, it.complemento[:200]) if x),
            }
        )
        escritor.writerow(linha)
    return b"\xef\xbb\xbf" + saida.getvalue().encode("utf-8")
