# 0004. The language model sits behind a port

## Context
The pipeline uses the model in two places (extraction and selection). Coupling the code to a vendor makes
tests, model swaps, and offline use harder.

## Decision
The rest of the system knows only `ProvedorLLM.completar(system, user, max_tokens) -> str`. There are three adapters:
`ProvedorHTTP` (JSON chat compatible with the most common format, configured by `LLM_API_URL`, `LLM_API_KEY` and
`LLM_MODEL`, with token counting), `ProvedorFake` (queued responses, used in the tests) and
`ProvedorDemo` (a simple rule, activated with `LLM_API_URL=demo`, to run the interface without a key).
The response is treated as untrusted input: JSON is read tolerantly, validated with pydantic,
one retry that shows the error to the model, and a candidate position outside the list becomes `null`.
Selection batches are small and, if one fails, are split in half until the problematic item is isolated.

## Consequences
- Switching models is configuration. Tests make no network calls.
- The assumed chat format is a convention; a vendor with a different format needs a new adapter (a few lines).
