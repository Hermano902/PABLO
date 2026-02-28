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

Phase 1 — Storage & Indexing
- `KNOW`: in-memory store, RLock model, ID allocation, Layer-1 commit event, simple
  retrieval APIs (by_id, by_type, by_text, linear scans); autosave to `storage/`.

Phase 2 — Ingestion & Grounding
- `PERCEPTORS (READ)`: `GUIInputSource` semantics, tap forwarding, cooldown, simulation.
- `SYMBOL`: heuristic router, near-compound candidate shape, multi-LLM specialist contract,
  on-demand grounding API.

Phase 3 — Contract & Validation
- `DATA`: candidate validation, token→Compound mapping, placeholder lifecycle,
  consultation API, temp ID semantics.

Phase 4 — Context & Memory
- `NARRATIVES`: bindings, Snaps, constraints, thread; relational vs episodic narratives;
  KNOW integration (live reference), narrative lifecycle.

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
  narratives.json, metadata.json).
- Indexing: incremental plan for `by_prime` / `by_trigger` indexing (Phase 2/3).
- Testing & CI: unit tests per prime, integration harness (simulation of READ → THINK loop),
  performance smoke tests.

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

Next Steps
1. Confirm priority: start `PRIMEBIT` or `COMPOUND` first.
2. For the chosen component: produce a detailed architecture doc (target 30% done),
   then implement reference code and unit tests.
3. Iterate with feedback; mark component refinement progress in the project's TODO list.

Notes
- Keep changes minimal and backward compatible. Phase-1 increments should be runnable
  with heuristic SYMBOL and READ-only keyboard input.
