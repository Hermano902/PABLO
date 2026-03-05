# SYMBOL — Concept

*PABLO's interpretive prime. The bridge between raw language and prime-space.*

---

## Nature

SYMBOL is sensitive to **uninterpreted tokens in the perception layer** of the scene.
When READ has written preliminary tokens but no prime assignments exist yet, SYMBOL
emerges to bridge the gap — matching surface language to PABLO's native prime vocabulary.

SYMBOL does not create Compounds or store anything. It interprets. Its output is a set
of token resolutions: for each token, a proposed prime (or a flag that no prime was found).

---

## What SYMBOL Does

When the scene reaches `"symbol"` stage, SYMBOL:

1. **Reads** `scene.preliminary_tokens` and `scene.raw_input`
2. **For each token**, runs the resolution cascade:
   - **Exact match** — is the token a prime name? Direct assignment.
   - **Lemma match** — spaCy lemmatises the token; does the lemma match a prime name?
   - **Heuristic** — does the token belong to a known family of a prime? (e.g. "moved" → MOVE)
   - **Specialist** — LLM specialist called for ambiguous tokens (Phase 2+)
   - **Unresolved** — no match found; token flagged for placeholder Compound creation
3. **Writes the symbol layer** of the scene:
   - `scene.token_resolutions` — per-token dict with `{token, lemma, prime, score, method, pos}`
   - `scene.prime_field` — `{prime_name: max_score}` across all tokens
   - `scene.prime_field_bits` — union PrimeBit of all resolved primes
   - `scene.unresolved_tokens` — tokens with no prime match
   - `scene.stage = "memory"`
4. **Contributes to the SymbolicScene** — one Compound per resolved token (prime-grounded),
   Triples linking tokens to their resolved primes.

---

## The Resolution Cascade

```
token
  ├── exact match to prime name → score 1.0, method "exact"
  ├── lemma matches prime name  → score 0.9, method "lemma"
  ├── heuristic family match    → score 0.7, method "heuristic"
  ├── specialist (Phase 2+)     → score 0.5–0.9, method "specialist"
  └── unresolved               → score 0.0, method "none"
```

Phase 1 uses exact match, lemma match, and heuristic only. The specialist fleet is
SYMBOL's future engine — activated incrementally as more training data accumulates.

---

## What SYMBOL Does NOT Do

SYMBOL does not create or store Compounds. That is DATA + KNOW.
SYMBOL does not decide what the utterance *means*. That is THINK.
SYMBOL does not know whether the input will be processed consciously. That is SELF.
SYMBOL does not know about Narratives. It sees tokens and primes, nothing more.

---

## Phase Scope

| Phase | Capability |
|-------|-----------|
| 1 | Exact, lemma, and heuristic resolution |
| 2 | LLM specialist fleet for ambiguous tokens |
| 2 | On-demand grounding of placeholder Compounds (called by KNOW enrichment) |

---

*See `docs/SYSTEM/cognitive_scene.md` for the scene layer SYMBOL writes.*
*See `docs/PRIMES/DATA/data_concept.md` for what DATA does with SYMBOL's resolutions.*
