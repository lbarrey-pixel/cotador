from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile

from app.exportacao import ErroExportacao
from app.extracao import ErroExtracao, ErroProvedor
from app.ingestao import documento_de_arquivo, documento_de_texto

from . import servico
from .esquemas import CsvIn, ItemIn, ItemOut, ProdutoOut, PropostaOut

router = APIRouter()


def _contexto(request: Request):
    return request.app.state.repo, request.app.state.provedor, request.app.state.config


@router.post("/propostas/extrair", response_model=PropostaOut, status_code=201)
def extrair(
    request: Request,
    texto: str = Form(""),
    arquivo: UploadFile | None = File(None),
) -> PropostaOut:
    repo, provedor, cfg = _contexto(request)
    if arquivo is not None and arquivo.filename:
        dados = arquivo.file.read(cfg.upload_max_bytes + 1)
        if len(dados) > cfg.upload_max_bytes:
            raise HTTPException(413, "arquivo maior que o limite")
        doc = documento_de_arquivo(arquivo.filename, dados, arquivo.content_type or "")
        extra = texto
    elif texto.strip():
        doc, extra = documento_de_texto(texto), ""
    else:
        raise HTTPException(422, "envie texto ou arquivo")
    try:
        return servico.extrair_e_casar(repo, provedor, doc, cfg.margem_padrao_pct, extra)
    except servico.ErroNegocio as e:
        raise HTTPException(422, str(e)) from e
    except (ErroExtracao, ErroProvedor) as e:
        raise HTTPException(502, f"falha ao ler o pedido com o modelo: {e}") from e


@router.get("/propostas/{proposta_id}", response_model=PropostaOut)
def obter(proposta_id: int, request: Request) -> PropostaOut:
    proposta = request.app.state.repo.obter_proposta(proposta_id)
    if proposta is None:
        raise HTTPException(404, "proposta não encontrada")
    return proposta


@router.put("/propostas/{proposta_id}/itens/{n}", response_model=ItemOut)
def atualizar_item(proposta_id: int, n: int, corpo: ItemIn, request: Request) -> ItemOut:
    repo, _, cfg = _contexto(request)
    try:
        return servico.atualizar_item(repo, proposta_id, n, corpo, cfg.margem_padrao_pct)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except servico.ErroNegocio as e:
        raise HTTPException(422, str(e)) from e


@router.post("/propostas/{proposta_id}/csv")
def csv_da_proposta(proposta_id: int, request: Request, corpo: CsvIn | None = None) -> Response:
    try:
        nome, conteudo = servico.montar_csv(request.app.state.repo, proposta_id, corpo or CsvIn())
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ErroExportacao as e:
        raise HTTPException(422, str(e)) from e
    return Response(
        conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/produtos", response_model=list[ProdutoOut])
def produtos(request: Request, q: str = "", limite: int = 20) -> list[ProdutoOut]:
    achados = request.app.state.repo.listar_produtos(q, max(1, min(limite, 50)))
    return [ProdutoOut(id=p.id, codigo=p.codigo, descricao=p.descricao, preco_custo_centavos=p.preco_custo_centavos)
            for p in achados]  # fmt: skip
