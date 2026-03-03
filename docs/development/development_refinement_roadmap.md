Refinement Roadmap — PABLO

Overview
This document captures the refinement roadmap derived from the Concept and Architecture
docs. Its goal is to convert the high-level design into prioritized, implementable
component architecture specifications and runnable Phase-1 increments.

Scope
- Produce detailed architecture for each component: API surface, threading model,
  queue boundaries, persistence contracts, failure modes, tests, and Phase-2 notes.
- Iterate with heavy feedback until we reach an agreed refinement percentage per
  component (30/60/85/100 thresholds).

Phased Order (minimize blockers)

Phase 0 — Foundations
- `PRIMEBIT`: 64-bit PrimeBit API, serialization, bit ops, performance constraints.
- `COMPOUND`: full schema, constructors, immutability contract, serialisation helpers.

Phase 0.5 — Triple and Proposition Layer  ← NEW (session 2026-03-03)
- `TRIPLE`: Triple dataclass, triple store in KNOW, store_triple/get_triples API,
  serialization to storage/triples.json, triple_index by source_id.
  Reference: docs/TRIPLES/triple_concept.md, docs/TRIPLES/triple_architecture.md
- `SYMBOL_INDEX`: Move by_symbol() from O(n) linear scan to O(1) index.
  _symbol_index: dict[str, int] maintained in KNOW.store_batch() and _load_from_disk().
  Reference: docs/PRIMES/KNOW/know_architecture.md Section 2, 7.
- `PROPOSITION` (concept + architecture docs only in Phase 0.5 — data structure deferred to Phase 2):
  Reference: docs/PROPOSITIONS/proposition_concept.md, docs/PROPOSITIONS/proposition_architecture.md

Phase 1 — Storage & Indexing
- `KNOW`: in-memory store, RLock model, ID allocation, Layer-1 commit event, simple
  retrieval APIs (by_id, by_type, by_symbol O(1), by_relation — linear scans);
  autosave to `storage/`; triple store + triple_index.

Phase 2 — Ingestion & Grounding
- `PERCEPTORS (READ)`: `GUIInputSource` semantics, tap forwarding, cooldown, simulation.
- `SYMBOL`: heuristic router, near-compound candidate shape, multi-LLM specialist contract,
  on-demand grounding API.

Phase 2.5 — Activation Cloud  ← NEW (session 2026-03-03)
- `ACTIVATION_CLOUD`: CloudBuilder and ActivationCloud dataclass implementation.
  Cognitive layer (Phase 1 scope): exact_match, family_root, definition_compounds,
  utterance_context, narrative_context, prime_candidates, fast_path.
  Integration: Router step 0 (build cloud before specialist call).
  Reference: docs/ACTIVATION_CLOUD/activation_cloud_concept.md,
             docs/ACTIVATION_CLOUD/activation_cloud_architecture.md,
             core/activation_cloud.py (to be created)
- `DEEPSEEK_EXTRACTOR`: Replace TextGrounder prime-bag prompt with triple extraction.
  Input: sentence + activation cloud serialization.
  Output: list of (source, predicate, target) triples.
  Reference: docs/PRIMES/SYMBOL/SYMBOL_ARCHITECTURE.md "DeepSeek Triple Extractor"

Phase 3 — Contract & Validation
- `DATA`: candidate validation (prime-bag AND triple format), token→Compound mapping,
  placeholder lifecycle, consultation API, temp ID semantics.
  Triple validation path: predicates → PRIME_SET, resolve surface forms → compound IDs,
  call know.store_triple() per validated triple.

Phase 4 — Context & Memory
- `NARRATIVES`: bindings, Snaps, constraints, thread; relational vs episodic narratives;
  KNOW integration (live reference), narrative lifecycle.
  Instance propositions (THIS-anchored triples) and Proposition records.

Phase 5 — Attention & Policy
- `SELF`: tap, salience math, narrative-aware modifiers, suppression rules, `think_queue`
  contract.

Phase 6 — Reasoner & Action
- `THINK`: reasoning cycle, routing table, macro/action lifecycle, narrative instance-space
  reasoning, consultation API, promotion rules (Action → Macro).

Phase 7 — Presentation & I/O
- GUI / response pipeline: `response_queue`, routing by `source`, UX hooks and testing.

Cross-cutting & Infrastructure
- Storage & persistence: compaction, archive, backups, migration plan (compounds.json,
  narratives.json, triples.json, metadata.json).
- Indexing: incremental plan for `by_prime` / `by_trigger` indexing (Phase 2/3).
- Testing & CI: unit tests per prime, integration harness (simulation of READ → THINK loop),
  performance smoke tests.

---

Pipeline Retirement Roadmap  ← NEW (session 2026-03-03)

Current pipeline:
  READ → SYMBOL → DATA → KNOW → SELF → THINK

Phase 0.5 with triple store and symbol index:
  READ → SYMBOL → DATA → KNOW (with O(1) index + triple store) → SELF → THINK

Phase 2.5 with activation cloud:
  READ → SYMBOL (cloud-assisted) → DATA → KNOW → SELF → THINK
  (cloud built per token, fast_path short-circuits SYMBOL for known tokens)

Phase 3+ with cloud maturity:
  READ → SYMBOL (thin edge-case only) → DATA → KNOW → SELF → THINK
  (cloud handles most tokens; SYMBOL only invoked for truly unknown symbols)

Phase 4 (final) — SYMBOL and DATA absorbed into cloud:
  READ → activation cloud → THINK
  (DATA logic internalized in cloud assembly; KNOW and SELF remain as separate stores)

Nothing is removed until each retirement phase is validated.
Each transition is isolated and testable independently.

---

Deliverables per component
- Detailed Architecture doc (API, threads, queues, data formats, errors, metrics).
- Reference implementation (core methods) + unit tests.
- Integration tests with upstream/downstream neighbors.
- Phase-2 TODOs with acceptance criteria.

Refinement Targets (per component)
- 30%: architecture doc + API surface
- 60%: reference implementation + unit tests
- 85%: integration tests with adjacent components
-100%: persistence validated, performance checks, Phase-2 hooks documented

Next Steps (post session 2026-03-03)
1. Implement Triple dataclass (core/triple.py) and integrate into KNOW.
2. Implement O(1) symbol index in KNOW.py — fixes compound duplicate bug.
3. Write docs/TRIPLES/triple_architecture.md (DONE) and docs/PROPOSITIONS/ (DONE).
4. Implement core/activation_cloud.py (CloudBuilder + ActivationCloud).
5. Update core/router.py to integrate activation cloud as step 0 in cascade.
6. Update core/specialists.py with DeepSeek triple extractor prompt.
7. Update DATA.py to accept and validate triple output from SYMBOL.

Notes
- Keep changes minimal and backward compatible. Phase-1 increments should be runnable
  with heuristic SYMBOL and READ-only keyboard input.
- Triple store is additive — existing compounds.json and pipeline are untouched.
- Activation cloud is additive — existing cascade steps are unchanged, cloud is step 0.
