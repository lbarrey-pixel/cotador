from __future__ import annotations

from collections.abc import Callable
from datetime import date

import psycopg
from psycopg.types.json import Jsonb

from app.matching import BuscaTrigrama, MemoriaPostgres, Produto
from app.matching.candidatos import produto_de_linha

from .esquemas import CandidatoOut, ItemOut, PropostaOut

Conectar = Callable[[], psycopg.Connection]


def conectar_com(url: str) -> Conectar:
    return lambda: psycopg.connect(url)


class CachePostgres:
    def __init__(self, conectar: Conectar) -> None:
        self._conectar = conectar

    def obter(self, chave: str) -> dict | None:
        with self._conectar() as con, con.cursor() as cur:
            cur.execute("select valor from extracao_cache where chave = %s", (chave,))
            linha = cur.fetchone()
            return linha[0] if linha else None

    def guardar(self, chave: str, valor: dict) -> None:
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(
                "insert into extracao_cache (chave, valor) values (%s, %s) on conflict (chave) do nothing",
                (chave, Jsonb(valor)),
            )
            con.commit()


_COLUNAS_PRODUTO = "id, codigo, descricao, atributos, preco_custo_centavos, ncm"


class RepoPostgres:
    def __init__(self, conectar: Conectar) -> None:
        self._conectar = conectar
        self.cache = CachePostgres(conectar)
        self.memoria = MemoriaPostgres(conectar)
        self.busca = BuscaTrigrama(conectar)

    def produtos_por_id(self, ids: list[int]) -> dict[int, Produto]:
        if not ids:
            return {}
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(f"select {_COLUNAS_PRODUTO} from produtos where id = any(%s)", (ids,))
            return {r[0]: produto_de_linha(r) for r in cur.fetchall()}

    def listar_produtos(self, q: str, limite: int = 20) -> list[Produto]:
        padrao = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(
                f"""select {_COLUNAS_PRODUTO} from produtos
                    where descricao ilike %(p)s or codigo ilike %(p)s
                    order by similarity(descricao, %(q)s) desc, id
                    limit %(n)s""",
                {"p": padrao, "q": q, "n": limite},
            )
            return [produto_de_linha(r) for r in cur.fetchall()]

    def salvar_proposta(self, proposta: PropostaOut) -> PropostaOut:
        with self._conectar() as con, con.cursor() as cur:
            cur.execute("select nextval(pg_get_serial_sequence('propostas', 'id'))")
            novo_id = cur.fetchone()[0]
            numero = f"COT-{date.today().year}-{novo_id:05d}"
            cur.execute(
                """insert into propostas (id, numero, referencia, cliente, cnpj, destino, frete_centavos,
                                          prazo_entrega, observacoes, avisos)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (novo_id, numero, proposta.referencia, proposta.cliente, proposta.cnpj, proposta.destino,
                 proposta.frete_centavos, proposta.prazo_entrega, proposta.observacoes, Jsonb(proposta.avisos)),
            )  # fmt: skip
            for it in proposta.itens:
                self._gravar_item(cur, novo_id, it)
            con.commit()
        salva = self.obter_proposta(novo_id)
        assert salva is not None
        return salva

    def obter_proposta(self, proposta_id: int) -> PropostaOut | None:
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(
                """select id, numero, referencia, cliente, cnpj, destino, frete_centavos, prazo_entrega,
                          observacoes, avisos from propostas where id = %s""",
                (proposta_id,),
            )
            cab = cur.fetchone()
            if cab is None:
                return None
            cur.execute(
                """select i.n, i.descricao_original, i.quantidade, i.unidade, i.atributos, i.produto_id,
                          coalesce(p.codigo, ''), coalesce(p.descricao, ''), i.confianca, i.origem, i.motivo,
                          i.preco_un_centavos, i.candidatos
                   from itens_proposta i left join produtos p on p.id = i.produto_id
                   where i.proposta_id = %s order by i.n""",
                (proposta_id,),
            )
            itens = [
                ItemOut(
                    n=r[0], descricao_original=r[1], quantidade=float(r[2]), unidade=r[3], atributos=r[4],
                    produto_id=r[5], produto_codigo=r[6], produto_descricao=r[7], confianca=r[8], origem=r[9],
                    motivo=r[10], preco_un_centavos=r[11],
                    candidatos=[CandidatoOut.model_validate(c) for c in r[12]],
                )
                for r in cur.fetchall()
            ]  # fmt: skip
        return PropostaOut(
            id=cab[0], numero=cab[1], referencia=cab[2], cliente=cab[3], cnpj=cab[4], destino=cab[5],
            frete_centavos=cab[6], prazo_entrega=cab[7], observacoes=cab[8], avisos=cab[9], itens=itens,
        )  # fmt: skip

    def salvar_item(self, proposta_id: int, item: ItemOut) -> None:
        with self._conectar() as con, con.cursor() as cur:
            self._gravar_item(cur, proposta_id, item)
            con.commit()

    @staticmethod
    def _gravar_item(cur, proposta_id: int, it: ItemOut) -> None:
        cur.execute(
            """insert into itens_proposta (proposta_id, n, descricao_original, quantidade, unidade, atributos,
                                           produto_id, confianca, origem, motivo, preco_un_centavos, candidatos)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (proposta_id, n) do update set
                 quantidade = excluded.quantidade, produto_id = excluded.produto_id,
                 confianca = excluded.confianca, origem = excluded.origem, motivo = excluded.motivo,
                 preco_un_centavos = excluded.preco_un_centavos""",
            (proposta_id, it.n, it.descricao_original, it.quantidade, it.unidade, Jsonb(it.atributos),
             it.produto_id, it.confianca, it.origem, it.motivo, it.preco_un_centavos,
             Jsonb([c.model_dump() for c in it.candidatos])),
        )  # fmt: skip
