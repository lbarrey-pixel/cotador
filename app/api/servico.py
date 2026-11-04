"""Casos de uso da API: extrair e casar, confirmar item, montar o CSV."""

from __future__ import annotations

from app.exportacao import DadosCSV, LinhaCSV, gerar_csv
from app.extracao import Extrator, ProvedorLLM
from app.ingestao import Documento
from app.matching import ItemParaCasar, MotorMatching, Produto, ResultadoMatch, Seletor

from .esquemas import CandidatoOut, CsvIn, ItemIn, ItemOut, PropostaOut
from .repositorio import Repositorio

MAX_CANDIDATOS_NA_TELA = 15


class ErroNegocio(ValueError):
    """Pedido válido no formato, mas que o sistema não consegue atender."""


def preco_de_venda(produto: Produto, margem_pct: int) -> int:
    return produto.preco_custo_centavos * (100 + margem_pct) // 100


def _candidatos_para_tela(r: ResultadoMatch) -> list[CandidatoOut]:
    # escolhido primeiro, depois os viáveis por similaridade, por fim os descartados (com o motivo)
    ordem = sorted(
        r.candidatos,
        key=lambda c: (
            bool(c.descartado_por),
            r.produto is None or c.produto.id != r.produto.id,
            -c.similaridade,
        ),
    )[:MAX_CANDIDATOS_NA_TELA]
    saida = [
        CandidatoOut(
            produto_id=c.produto.id,
            codigo=c.produto.codigo,
            descricao=c.produto.descricao,
            similaridade=round(c.similaridade, 3),
            descartado_por=c.descartado_por,
        )
        for c in ordem
    ]
    if r.produto and all(c.produto_id != r.produto.id for c in saida):  # veio da memória, sem lista
        saida.insert(0, CandidatoOut(produto_id=r.produto.id, codigo=r.produto.codigo,
                                     descricao=r.produto.descricao, similaridade=1.0))  # fmt: skip
    return saida


def extrair_e_casar(repo: Repositorio, provedor: ProvedorLLM, documento: Documento, margem_pct: int,
                    texto_extra: str = "") -> PropostaOut:  # fmt: skip
    pedido = Extrator(provedor, repo.cache).extrair(documento, texto_extra)
    if not pedido.itens:
        raise ErroNegocio("nenhum item encontrado no pedido")

    itens = [ItemParaCasar(i, it.descricao_original, it.atributos) for i, it in enumerate(pedido.itens, 1)]
    motor = MotorMatching(
        memoria=repo.memoria,
        busca=repo.busca,
        buscar_produtos=repo.produtos_por_id,
        seletor=Seletor(provedor),
    )
    resultados = motor.casar(itens, pedido.cliente, pedido.cnpj)

    saida = []
    for it, r in zip(pedido.itens, resultados, strict=True):
        saida.append(
            ItemOut(
                n=r.indice,
                descricao_original=it.descricao_original,
                quantidade=it.quantidade,
                unidade=it.unidade,
                atributos=it.atributos,
                produto_id=r.produto.id if r.produto else None,
                produto_codigo=r.produto.codigo if r.produto else "",
                produto_descricao=r.produto.descricao if r.produto else "",
                confianca=r.confianca,
                origem=r.origem,
                motivo=r.motivo,
                preco_un_centavos=preco_de_venda(r.produto, margem_pct) if r.produto else 0,
                candidatos=_candidatos_para_tela(r),
            )
        )
    proposta = PropostaOut(
        referencia=pedido.referencia,
        cliente=pedido.cliente,
        cnpj=pedido.cnpj,
        destino=pedido.destino,
        avisos=motor.avisos,
        itens=saida,
    )
    return repo.salvar_proposta(proposta)


def atualizar_item(repo: Repositorio, proposta_id: int, n: int, corpo: ItemIn, margem_pct: int) -> ItemOut:
    proposta = repo.obter_proposta(proposta_id)
    if proposta is None:
        raise LookupError("proposta não encontrada")
    item = next((i for i in proposta.itens if i.n == n), None)
    if item is None:
        raise LookupError("item não encontrado")

    enviados = corpo.model_fields_set
    if "produto_id" in enviados:
        if corpo.produto_id is None:
            item.produto_id, item.produto_codigo, item.produto_descricao = None, "", ""
            item.confianca, item.origem, item.motivo, item.preco_un_centavos = "nenhuma", "operador", "", 0
        else:
            produto = repo.produtos_por_id([corpo.produto_id]).get(corpo.produto_id)
            if produto is None:
                raise ErroNegocio("produto inexistente")
            item.produto_id, item.produto_codigo, item.produto_descricao = produto.id, produto.codigo, produto.descricao
            item.confianca, item.origem, item.motivo = "alta", "operador", "confirmado pelo operador"
            item.preco_un_centavos = preco_de_venda(produto, margem_pct)
            # a confirmação do operador é o que alimenta a camada 1 nas próximas cotações
            repo.memoria.aprender([(item.descricao_original, produto.id)], proposta.cliente, proposta.cnpj)
    if corpo.quantidade is not None:
        item.quantidade = corpo.quantidade
    if corpo.preco_un_centavos is not None:
        item.preco_un_centavos = corpo.preco_un_centavos
    repo.salvar_item(proposta_id, item)
    return item


def montar_csv(repo: Repositorio, proposta_id: int, corpo: CsvIn) -> tuple[str, bytes]:
    proposta = repo.obter_proposta(proposta_id)
    if proposta is None:
        raise LookupError("proposta não encontrada")
    linhas = [
        LinhaCSV(
            descricao=i.produto_descricao or i.descricao_original,
            quantidade=i.quantidade,
            unidade=i.unidade,
            preco_un_centavos=i.preco_un_centavos,
            # item sem produto sai com o texto do cliente e fica marcado para o vendedor
            complemento=i.descricao_original if i.produto_id else "SEM PRODUTO NO CATÁLOGO: conferir",
        )
        for i in proposta.itens
    ]
    dados = DadosCSV(
        numero_proposta=proposta.numero,
        cliente=proposta.cliente,
        cnpj=proposta.cnpj,
        itens=linhas,
        frete_centavos=corpo.frete_centavos,
        prazo_entrega=corpo.prazo_entrega,
        observacoes=corpo.observacoes or proposta.observacoes,
    )
    return f"{proposta.numero}.csv", gerar_csv(dados)
