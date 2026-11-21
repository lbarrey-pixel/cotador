# 0001. Three layers before calling the language model

## Context
Matching the line "switch 24p giga gerenc." to the right product in a catalog of thousands of items is the
most expensive and most error-prone step in the flow. Sending the whole catalog to the model does not fit in
the context and is expensive; sending only the description and trusting the answer silently swaps the product.

## Decision
Matching happens in three layers, in this order:

1. **Memory.** Pairs (customer text, product) already confirmed by the operator, first by customer
   (the root of the CNPJ, the Brazilian company registration number) and then global. It resolves at no cost
   and with no variation.
2. **Candidates.** Trigrams (`pg_trgm`, GiST index, top 40 per item, one query for all items).
   Without Postgres, a Python scorer (token Jaccard plus a bonus for an identical model code) plays the same role.
3. **Model.** It chooses among the candidates, in small batches, and returns `produto_id` or `null` with
   confidence and a reason. Candidates with a divergent critical attribute (ports, category, voltage, gauge...)
   are removed before the model sees the list.

## Consequences
- Most of the recurring volume never reaches the model.
- The model can only choose what the search found; it does not invent a product code.
- A false negative (an item with no product) is preferable to a false positive: the prompt says to answer `null` when in doubt.
- The quality of the top 40 limits the result. That is why `scripts/avaliar_recall.py` exists.
