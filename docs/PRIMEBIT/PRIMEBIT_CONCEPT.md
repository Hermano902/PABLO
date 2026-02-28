# PrimeBit — Concept Summary

Purpose
- PrimeBit is the compact, fast encoding that represents PABLO's 63 atomic primes and compound references as a 64‑bit integer. It is the low-latency backing store for retrieval, filtering and fast membership checks.

Core ideas
- 64-bit layout: bits 0–62 map to the canonical 63 primes; bit 63 is the compound flag.
- Two modes: a prime-mask mode (low bits are prime flags) and a compound-payload mode (bit63 set, low bits encode a compact payload referencing compound metadata).
- Semantic role: PrimeBits are descriptors and fast indexes — they do not replace structured DATA, they accelerate header-only decision paths and routing.

Responsibilities
- Fast containment and set ops: O(1) checks for `has`, `has_all`, unions, intersections.
- Header-only reads: allow callers to decide if a full compound load is needed (use `rel_flags` and `resolved_prime_mask` hints).
- Stable canonical mapping: canonical prime→bit assignment (alphabetical) to avoid drift across code.

Design constraints
- Keep the PrimeBit helpers centralized (no scattered inline bit math).
- Preserve backward compatibility: `schema_tag == 0` semantics must be supported during rollout.
- Avoid exposing raw bit encodings in higher-level code — provide helper APIs and doc references.

Why PrimeBit matters
- It enables deterministic, cheap heuristics for router and rule matching.
- It makes large-scale filtering and inverted-index operations efficient.
- It supports a feature-flagged rollout of compact compound payloads that reduce full-load costs.

Risks & mitigations (summary)
- Misinterpretation of legacy data: keep schema-tagging and reader fallbacks.
- Exploded coupling: centralize helpers in `core/primebit.py` and document expected invariants.
- Performance regressions: prefer header-only reads and background enrichment.

See `PRIMEBIT_ARCHITECTURE.md` for implementation details, helper APIs, payload layout, and migration guidance.
