# 0003. The ERP CSV invariants are tested byte for byte

## Context
The destination ERP imports a fixed layout and fails in an uninformative way: a renamed column, a wrong
separator, or an empty proposal number results in items grouped incorrectly or a rejected import.

## Decision
The `app.exportacao` module knows neither the database nor the API, and it has tests for what the ERP requires:
45 columns with the exact names, UTF-8 with BOM, CRLF, `,` separator (values with a decimal comma stay inside
quotes), decimal comma, the same "Número da proposta" (proposal number, never empty) on every row, CNPJ
(Brazilian company registration number) validated by its digits (an invalid one comes out empty and goes into
Observações, the Notes column). Price travels as integer cents and `fmt_preco` formats it without going through
`float`. A golden file (`tests/golden/proposta_exemplo.csv`) is compared byte for byte.

## Consequences
- Any change to the layout requires changing the golden file on purpose, in review.
- The CSV is generated on demand from the saved proposal, so correcting an item and generating again is cheap.
