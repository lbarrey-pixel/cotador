# 0001. Três camadas antes de chamar o modelo de linguagem

## Contexto
Casar a linha "switch 24p giga gerenc." com o produto certo de um catálogo de milhares de itens é o passo
mais caro e mais sujeito a erro do fluxo. Mandar o catálogo inteiro ao modelo não cabe no contexto e custa
caro; mandar só a descrição e confiar na resposta troca produto silenciosamente.

## Decisão
O casamento acontece em três camadas, nesta ordem:

1. **Memória.** Pares (texto do cliente, produto) já confirmados pelo operador, primeiro por cliente
   (raiz do CNPJ) e depois globais. Resolve sem custo e sem variação.
2. **Candidatos.** Trigramas (`pg_trgm`, índice GiST, top-40 por item, uma consulta para todos os itens).
   Sem Postgres, um scorer em Python (Jaccard de tokens + bônus para código de modelo igual) faz o mesmo papel.
3. **Modelo.** Escolhe entre os candidatos, em lotes pequenos, e devolve `produto_id` ou `null` com
   confiança e motivo. Candidatos com atributo crítico divergente (portas, categoria, tensão, bitola...)
   são retirados antes do modelo ver a lista.

## Consequências
- A maior parte do volume recorrente nunca chega ao modelo.
- O modelo só pode escolher o que a busca achou; ele não inventa código de produto.
- Falso negativo (item sem produto) é preferível a falso positivo: o prompt manda responder `null` na dúvida.
- A qualidade do top-40 limita o resultado. Por isso existe `scripts/avaliar_recall.py`.
