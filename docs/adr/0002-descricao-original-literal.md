# 0002. A descrição do cliente é guardada literal

## Contexto
O modelo tende a "melhorar" o que lê: corrige abreviações, traduz, resume. Mas o texto exato que o cliente
escreveu é a chave da memória (camada 1) e a única evidência de auditoria quando um item sai errado.

## Decisão
`descricao_original` é copiada sem reescrita, só com espaços das pontas removidos. O prompt de extração
proíbe correção, resumo e tradução. Atributos técnicos que o modelo extrai ficam em campo separado
(`atributos`) e nunca substituem a descrição. A chave da memória é a descrição normalizada em Python
(sem acento, minúscula, sem pontuação), calculada em um único lugar.

## Consequências
- Duas escritas diferentes do mesmo item geram duas entradas de memória; aceitável, e a camada 2 cobre a diferença.
- O cache de extração é por hash do conteúdo do documento mais o prompt, então mudar o prompt invalida o cache.
