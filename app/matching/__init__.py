from .atributos import ATRIBUTOS_CRITICOS, atributos_do_item, divergencia_critica, extrair_atributos
from .candidatos import TOP_N, BuscaCandidatos, BuscaPura, BuscaTrigrama
from .memoria import Lembranca, MemoriaEmMemoria, MemoriaMatch, MemoriaPostgres, escopo_cliente
from .motor import MotorMatching, filtrar_por_atributos, produtos_por_id
from .normalizacao import normalizar
from .scorer import candidatos_puros, similaridade
from .seletor import Escolha, Seletor, ler_escolhas, montar_prompt
from .tipos import Candidato, ItemParaCasar, Produto, ResultadoMatch

__all__ = [
    "ATRIBUTOS_CRITICOS",
    "TOP_N",
    "BuscaCandidatos",
    "BuscaPura",
    "BuscaTrigrama",
    "Candidato",
    "Escolha",
    "ItemParaCasar",
    "Lembranca",
    "MemoriaEmMemoria",
    "MemoriaMatch",
    "MemoriaPostgres",
    "MotorMatching",
    "Produto",
    "ResultadoMatch",
    "Seletor",
    "atributos_do_item",
    "candidatos_puros",
    "divergencia_critica",
    "escopo_cliente",
    "extrair_atributos",
    "filtrar_por_atributos",
    "ler_escolhas",
    "montar_prompt",
    "normalizar",
    "produtos_por_id",
    "similaridade",
]
