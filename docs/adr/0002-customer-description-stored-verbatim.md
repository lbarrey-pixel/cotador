# 0002. The customer's description is stored verbatim

## Context
The model tends to "improve" what it reads: it corrects abbreviations, translates, summarizes. But the exact
text the customer wrote is the key to memory (layer 1) and the only audit evidence when an item comes out wrong.

## Decision
`descricao_original` is copied with no rewriting, only with spaces at the ends removed. The extraction prompt
forbids correction, summarization, and translation. Technical attributes the model extracts stay in a separate
field (`atributos`) and never replace the description. The memory key is the description normalized in Python
(no accents, lowercase, no punctuation), computed in a single place.

## Consequences
- Two different spellings of the same item create two memory entries; that is acceptable, and layer 2 covers the difference.
- The extraction cache is keyed by a hash of the document content plus the prompt, so changing the prompt invalidates the cache.
