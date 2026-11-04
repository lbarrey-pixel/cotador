# 0004. O modelo de linguagem fica atrás de uma porta

## Contexto
O pipeline usa o modelo em dois pontos (extração e seleção). Acoplar o código a um fornecedor dificulta
testes, trocas de modelo e uso offline.

## Decisão
O resto do sistema conhece só `ProvedorLLM.completar(system, user, max_tokens) -> str`. Há três adaptadores:
`ProvedorHTTP` (chat JSON compatível com o formato mais comum, configurado por `LLM_API_URL`, `LLM_API_KEY` e
`LLM_MODEL`, com contagem de tokens), `ProvedorFake` (respostas enfileiradas, usado nos testes) e
`ProvedorDemo` (regra simples, ativado com `LLM_API_URL=demo`, para rodar a interface sem chave).
A resposta é tratada como entrada não confiável: JSON lido de forma tolerante, validado com pydantic,
uma nova tentativa mostrando o erro ao modelo, e posição de candidato fora da lista vira `null`.
Lotes de seleção são pequenos e, se um falha, são divididos ao meio até isolar o item problemático.

## Consequências
- Trocar de modelo é configuração. Testes não fazem chamada de rede.
- O formato de chat assumido é uma convenção; um fornecedor com formato diferente precisa de um adaptador novo (poucas linhas).
