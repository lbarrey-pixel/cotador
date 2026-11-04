# 0003. Invariantes do CSV do ERP são testados byte a byte

## Contexto
O ERP de destino importa um layout fixo e falha de forma pouco informativa: coluna renomeada, separador
errado ou número de proposta vazio resultam em itens agrupados errado ou importação rejeitada.

## Decisão
O módulo `app.exportacao` não conhece banco nem API e tem testes sobre o que o ERP exige: 45 colunas com
os nomes exatos, UTF-8 com BOM, CRLF, separador `,` (valores com vírgula decimal ficam entre aspas), vírgula decimal, o mesmo "Número da proposta"
(nunca vazio) em todas as linhas, CNPJ validado pelos dígitos (inválido sai vazio e vai para Observações).
Preço trafega em centavos inteiros e `fmt_preco` formata sem passar por `float`. Um arquivo golden
(`tests/golden/proposta_exemplo.csv`) é comparado byte a byte.

## Consequências
- Qualquer mudança no layout exige alterar o golden de propósito, em revisão.
- O CSV é gerado sob demanda a partir da proposta salva, então corrigir um item e gerar de novo é barato.
