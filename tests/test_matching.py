import json

from app.extracao import ProvedorFake
from app.matching import (
    BuscaPura,
    Candidato,
    ItemParaCasar,
    MemoriaEmMemoria,
    MotorMatching,
    Seletor,
    atributos_do_item,
    candidatos_puros,
    divergencia_critica,
    escopo_cliente,
    extrair_atributos,
    ler_escolhas,
    montar_prompt,
    produtos_por_id,
    similaridade,
)
from app.matching.normalizacao import codigos, normalizar

# --- camada 2: scorer puro -----------------------------------------------------------------


def test_normalizar_tira_acento_caixa_e_pontuacao():
    assert normalizar("  Cabo FLEXÍVEL 2,5mm² / 750V ") == "cabo flexivel 2 5mm 750v"


def test_codigos_reconhece_modelo_e_ignora_palavra_comum():
    assert codigos("Switch NX-SW24G 24 portas") == {"nxsw24g"}
    assert codigos("cabo de rede") == set()


def test_codigo_de_modelo_igual_pesa_mais_que_palavras():
    a = similaridade("switch NX-SW24G", "Switch gerenciável 24 portas NODAL NX-SW24G")
    b = similaridade("switch gerenciável", "Switch gerenciável 24 portas NODAL NX-SW24G")
    assert a > b


def test_candidatos_puros_ordena_e_corta_no_top_n(catalogo):
    r = candidatos_puros("switch 24 portas gigabit", catalogo, n=2)
    assert [c.produto.id for c in r][0] == 1
    assert len(r) == 2
    assert r[0].similaridade >= r[1].similaridade


def test_candidato_sem_nenhum_token_em_comum_nao_entra(catalogo):
    assert candidatos_puros("martelo de borracha", catalogo) == []


# --- exclusão por atributo crítico ---------------------------------------------------------


def test_extrai_atributos_da_descricao():
    a = extrair_atributos("Switch 24p gigabit PoE 220V")
    assert a["portas"] == "24" and a["tensao"] == "220"
    assert extrair_atributos("cabo UTP Cat6A")["categoria"] == "6a"
    assert extrair_atributos("cabo 2,5mm² flexível")["bitola"] == "2.5"
    assert extrair_atributos("HD 4TB")["capacidade"] == "4tb"


def test_24p_em_disjuntor_e_polos_e_em_switch_e_portas():
    assert "polos" not in extrair_atributos("switch 3p gigabit")  # 3p em switch: portas
    assert "portas" not in extrair_atributos("disjuntor 3p 32A")


def test_divergencia_exclui_e_ausencia_nao():
    assert divergencia_critica({"portas": "24"}, {"portas": "48"}) == "portas"
    assert divergencia_critica({"categoria": "6"}, {"categoria": "5e"}) == "categoria"
    assert divergencia_critica({"tensao": "12"}, {}) is None  # cliente não disse / catálogo não diz
    assert divergencia_critica({"tensao": "12"}, {"tensao": "12"}) is None


def test_atributo_declarado_na_extracao_vence_o_lido_por_regex():
    assert atributos_do_item("fonte 12v", {"tensao": "24 "})["tensao"] == "24"
    assert "cor" not in atributos_do_item("fonte", {"cor": "preto"})  # só os críticos entram


# --- camada 3: prompt, parse, lotes --------------------------------------------------------


def cands(catalogo, ids):
    return [Candidato(p, 0.5) for p in catalogo if p.id in ids]


def test_prompt_numera_candidatos_e_omite_descartados(catalogo):
    item = ItemParaCasar(7, "switch 24 portas", {"portas": "24"})
    lista = cands(catalogo, {1, 2})
    lista[1].descartado_por = "portas"
    prompt = montar_prompt([item], {7: lista})
    assert "Item 7" in prompt and "ATRIBUTOS: portas=24" in prompt
    assert "[0] SW24" in prompt
    assert "SW48" not in prompt


def test_parse_da_resposta_valida_e_defensivo():
    bruto = json.dumps(
        {"matches": [
            {"indice": 1, "candidato": 0, "confianca": "alta", "motivo": "mesma especificação"},
            {"indice": 2, "candidato": 9, "confianca": "alta", "motivo": "posição fora da lista"},
            {"indice": 3, "candidato": 0, "confianca": "certeza", "motivo": "confiança inventada"},
            {"indice": 99, "candidato": 0, "confianca": "alta", "motivo": "item que não existe"},
            {"indice": 4, "candidato": None, "confianca": "baixa", "motivo": "nenhum serve"},
        ]}
    )  # fmt: skip
    r = ler_escolhas(bruto, {1: 2, 2: 2, 3: 2, 4: 2})
    assert r[1].posicao == 0 and r[1].confianca == "alta"
    assert r[2].posicao is None  # índice fora da faixa não vira produto errado
    assert r[3].posicao is None and r[3].confianca == "nenhuma"
    assert 99 not in r
    assert r[4].posicao is None


def test_lotes_pequenos_e_falha_de_um_nao_derruba_os_outros(catalogo):
    itens = [ItemParaCasar(i, f"switch 24 portas {i}") for i in range(1, 7)]
    candidatos = {i: cands(catalogo, {1, 2}) for i in range(1, 7)}

    def modelo(system, user):
        if "switch 24 portas 5" in user and user.count("Item ") < 8:  # o lote que contém o item 5 falha
            raise RuntimeError("estourou o teto de saída")
        ids = [int(x.split()[1]) for x in user.splitlines() if x.startswith("Item ")]
        return json.dumps(
            {"matches": [{"indice": i, "candidato": 0, "confianca": "alta", "motivo": "ok"} for i in ids]}
        )

    seletor = Seletor(ProvedorFake(funcao=modelo), tamanho_lote=3, paralelismo=1)
    escolhas, falhas = seletor.escolher(itens, candidatos)
    assert set(escolhas) == {1, 2, 3, 4, 6}  # só o item 5 ficou sem decisão
    assert len(falhas) == 1 and "1 item(ns)" in falhas[0]


def test_item_sem_candidato_viavel_nao_gasta_chamada(catalogo):
    lista = cands(catalogo, {1})
    lista[0].descartado_por = "portas"
    fake = ProvedorFake()
    escolhas, falhas = Seletor(fake).escolher([ItemParaCasar(1, "switch 48p")], {1: lista})
    assert escolhas == {} and falhas == [] and fake.chamadas == []


# --- camada 1: memória e precedência -------------------------------------------------------


def test_escopo_usa_raiz_do_cnpj_ou_nome():
    assert escopo_cliente("Qualquer Nome", "12.345.678/0001-95") == "cnpj:12345678"
    assert escopo_cliente("Horizonte  Redes", "") == "nome:horizonte redes"
    assert escopo_cliente("", "123") == ""


def test_memoria_cliente_vence_global():
    m = MemoriaEmMemoria()
    m.aprender([("fonte 12v", 5)], "Outra Empresa")
    m.aprender([("fonte 12v", 6)], "Horizonte", "12.345.678/0001-95")
    r = m.consultar(["Fonte 12V"], "Horizonte", "12.345.678/0001-95")
    assert (r["fonte 12v"].produto_id, r["fonte 12v"].origem) == (6, "memoria_cliente")
    # a confirmação do Horizonte (6) contrariou a sugestão global (5): o 5 foi rebaixado, o global passa a ser 6
    assert m.consultar(["fonte 12v"], "Terceiro")["fonte 12v"].produto_id == 6


def test_empate_no_topo_e_ambiguidade_e_nao_responde():
    m = MemoriaEmMemoria()
    m._contagens[("fonte", "nome:a")][5][0] = 1
    m._contagens[("fonte", "nome:b")][6][0] = 1
    assert m.consultar(["fonte"], "Terceiro") == {}


def test_global_responde_para_cliente_novo_quando_ha_vencedor():
    m = MemoriaEmMemoria()
    m.aprender([("fonte 12v", 5)], "A")
    m.aprender([("fonte 12v", 5)], "B")
    r = m.consultar(["fonte 12v"], "Cliente Novo")
    assert r["fonte 12v"].produto_id == 5 and r["fonte 12v"].origem == "memoria_global"


def test_correcao_do_operador_rebaixa_a_sugestao_contrariada():
    m = MemoriaEmMemoria()
    m.aprender([("fonte", 5)], "A")
    saldo = m.aprender([("fonte", 6)], "A")  # operador trocou 5 por 6
    assert saldo == {"aprendidos": 1, "rebaixados": 1}
    assert m.consultar(["fonte"], "A")["fonte"].produto_id == 6


# --- motor: as três camadas juntas ---------------------------------------------------------


def motor(catalogo, resposta_modelo, memoria=None):
    fake = ProvedorFake(funcao=resposta_modelo)
    return MotorMatching(
        memoria=memoria or MemoriaEmMemoria(),
        busca=BuscaPura(catalogo),
        buscar_produtos=produtos_por_id(catalogo),
        seletor=Seletor(fake),
    ), fake


def sempre_o_primeiro(system, user):
    ids = [int(x.split()[1]) for x in user.splitlines() if x.startswith("Item ")]
    return json.dumps({"matches": [{"indice": i, "candidato": 0, "confianca": "media", "motivo": "x"} for i in ids]})


def test_memoria_resolve_sem_chamar_o_modelo(catalogo):
    mem = MemoriaEmMemoria()
    mem.aprender([("fonte da camera", 6)], "Horizonte")
    m, fake = motor(catalogo, sempre_o_primeiro, mem)
    (r,) = m.casar([ItemParaCasar(1, "Fonte da câmera")], "Horizonte")
    assert (r.produto.id, r.origem, r.confianca) == (6, "memoria_cliente", "alta")
    assert fake.chamadas == []


def test_modelo_nao_pode_escolher_candidato_com_atributo_divergente(catalogo):
    # o item pede 48 portas; o modelo (errado) aponta o primeiro candidato, que seria o de 24
    def modelo(system, user):
        return json.dumps({"matches": [{"indice": 1, "candidato": 0, "confianca": "alta", "motivo": "x"}]})

    m, _ = motor(catalogo, modelo)
    (r,) = m.casar([ItemParaCasar(1, "Switch gerenciável 48 portas gigabit")])
    excluidos = {c.produto.id for c in r.candidatos if c.descartado_por}
    assert 1 in excluidos
    assert r.produto is None or r.produto.id == 2


def test_sem_candidato_parecido_devolve_nenhuma_com_motivo(catalogo):
    m, fake = motor(catalogo, sempre_o_primeiro)
    (r,) = m.casar([ItemParaCasar(1, "martelo de borracha")])
    assert r.produto is None and r.origem == "nenhuma" and "sem candidato" in r.motivo
    assert fake.chamadas == []


def test_falha_da_busca_vira_aviso_e_nao_excecao(catalogo):
    class BuscaQuebrada:
        def buscar(self, descricoes, n=40):
            raise ConnectionError("banco fora do ar")

    m = MotorMatching(MemoriaEmMemoria(), BuscaQuebrada(), produtos_por_id(catalogo), None)
    (r,) = m.casar([ItemParaCasar(1, "switch")])
    assert r.produto is None
    assert "busca de candidatos falhou" in m.avisos[0]
