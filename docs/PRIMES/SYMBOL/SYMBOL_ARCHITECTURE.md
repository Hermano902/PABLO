# SYMBOL — Architecture & Implementation

This document describes the implementation detail of SYMBOL's multi-LLM layer:
router, model serving, symbolicifier contract, rule store, lifecycle, governance,
and metrics. The conceptual contract — what SYMBOL is, symbol resolution lifecycle,
the two-phase bootstrapping process, and how SYMBOL refines Definition Narratives —
lives in SYMBOL_CONCEPT.md. Implement SYMBOL according to both.

---

# Multi-LLM Architecture and Implementation

This file contains the architecture- and implementation-focused sections for the multi-LLM strategy: router, model serving, symbolicifier, rule store, indexing, lifecycle, background enrichment, governance, metrics and the prioritized roadmap.

## Ingestion Path vs Enrichment Path

The multi-LLM layer operates in two distinct modes that must never be conflated:

Ingestion path (synchronous)
- Triggered per raw observation arriving from the perceptor queue.
- Input: raw observation dict `{timestamp, modality, event_type, data, metadata}`.
- Router selects a specialist based on modality and event_type heuristics.
- Specialist produces a near-compound candidate `{candidate_primes, roles, spans, confidence, provenance}`.
- DATA receives the candidate and creates real compounds (validating primes, creating placeholders for unknowns).
- Latency budget: must not block DATA's queue consumer; prefer cached rules and fast fallback.
- If specialist unavailable or slow: return a minimal heuristic candidate immediately; enqueue for async retry.

Enrichment path (asynchronous)
- Triggered by KNOW's idle background loop for already-stored compounds.
- Input: compound ID + header `{primebit, rel_flags, resolved_prime_mask}`.
- Specialists propose: additional prime assignments, role labels, rule templates, placeholder resolutions.
- Prime and relation proposals are applied via `KNOW.refine_definition()` — the only permitted
  path for updating a stored compound's primebit or relations. Each update is recorded in the
  compound's Definition Narrative thread with full provenance.
- Structural rule templates are stored as `rule` compounds (compound_type="internal", sub-type="rule")
  in KNOW; activated only after validation and governance checks.
- Does not block the ingestion path; bounded queue with drop-on-full and metrics.

---

## Router / Orchestrator (architecture)

- Keep routing overhead negligible (sub‑ms), deterministic and observable. Minimize unnecessary specialist invocations.
- Start deterministic-only: a small rule set of heuristics that select specialists. Fallback to a default specialist when no rule matches.

### Runtime behavior (fallback)
- When no deterministic rule matches, avoid blocking the caller with a long model call. Use prioritized fallback behavior:
  1. Immediately return a cheap default interpretation (heuristic-based) so the caller receives a fast response.
  2. Asynchronously enqueue the observation for specialist processing (background enrichment) so proposals/rules can be generated later.
  3. Optionally (config flag) invoke a very small default specialist synchronously; this mode requires the specialist to respond in <10 ms and should only be enabled if measured fallback×latency stays within SLA.
- Instrumentation: count synchronous fallbacks, async enqueues, and average fallback latency.

### Heuristics
- In ingestion mode the router receives a raw observation dict; dispatch is based on `modality` and `event_type` fields first, then token-level heuristics on the data payload.
- **Surface-form-exact lookup (first check):** before any heuristic or model dispatch,
  the router calls `KNOW.by_symbol(token)` for each token. If the exact surface form
  already exists in KNOW (whether root or family member), the token is resolved
  immediately. No specialist invocation needed. This is the cheapest possible path.
- **Lemmatization pre-router step:** if the exact lookup misses, strip common inflection
  suffixes (-ed, -ing, -s, -es, -er, -est) and check known irregular forms. If a root
  compound is found in KNOW, create a family member compound (KIND relation to root,
  root primebit ∪ grammatical primes) and return it directly. No model call needed.
  See SYMBOL_CONCEPT.md "Lemmatization and Family Member Resolution" for full algorithm.
- In enrichment mode the router receives a compound header `{id, symbol, primebit, rel_flags}`; dispatch uses prime-mask hints and `rel_flags`.
- Token n‑grams and anchored tokens (e.g., "if", "call", punctuation patterns).
- Prime-mask hints: cheap bit tests on `prime_mask` or known prime presence.
- `rel_flags` from `PrimeBit` payload (HAS_CHILDREN, HAS_RESOLVED_MASK, IS_NAMED).
- Simple regex patterns (precompiled) for vocabulary triggers.

### Router implementation notes
- Implement router as a small decision tree or ordered rule-list stored in config, reloadable without restart.
- Expose routing counters via `KNOW.get_router_stats()` or a lightweight `/routing_stats` endpoint.

## Model Fleet & Serving

### Principles
- Prefer a shared base model + LoRA/adapters to host many specialists with low memory overhead. Target small, efficient specialists for proposal tasks.

### Serving patterns
- Low-latency GPU path: resident base model + adapters served in-process or via a local model server; prefer adapter switching over full model loads.
- CPU/batch offline path: export specialists to ONNX Runtime (ORT) or similar and run large batched jobs for background enrichment.
- Adapter switching: light, but the forward pass still goes through the base model—measure end-to-end latency.

### Memory guidance
- Example: base model quantized = ~2GB, 10 adapters @ 20MB each = 200MB → keep base + 10 adapters resident (~2.2GB).

## Symbolicifier & Specialist Output Contract

The symbolicifier is the bridge between raw model output and the symbolic layer. It operates in both modes:

Ingestion mode (raw → near-compound)
- Input: raw observation dict from the perceptor queue.
- The specialist receives the raw `data` payload (text, frame description, audio event) and produces a near-compound candidate.
- Minimal output schema:

```json
{
  "candidate_primes": [{"prime": "MOVE", "score": 0.91}],
  "roles":            [{"span": [0, 3], "role": "agent", "score": 0.87}],
  "rule_template":    {"pattern": "<agent> <MOVE>", "slots": ["agent"]},
  "confidence":       0.89,
  "provenance":       {"model": "text-grounder-v1", "adapter": "motion-detector"},
  "raw_input":        "the cat moved left"
}
```

- DATA treats this as a proposal: validates primes against the canonical 63, creates placeholder compounds for unknowns, records provenance.

Enrichment mode (compound → rule proposal)
- Input: compound header `{id, primebit, rel_flags, symbol, resolved_prime_mask}`.
- Specialists produce constrained structured output (JSON-like). The symbolicifier parses and validates this into rule candidates.
- Minimal output schema (same shape as above, with compound_id added to provenance).

Shared validation rules (both modes)
- Enforce required keys, types, ranges, span sanity.
- Reject malformed outputs and surface sampled traces for debugging.

### Calibration
- Calibrate raw model scores (Platt scaling / isotonic regression) and persist calibration parameters per adapter in `KNOW` (fields: `calibration_version`, `calibration_params`). Apply calibration at inference time.

## Rule Representation, Storage & Indexing

- Store rules as compounds (`compound_type="internal"`, `sub_type="rule"`) in KNOW with
  provenance, versioning and metrics. The `"rule"` sub-type is not in TYPE_TO_LAYER —
  rule compounds are internal system records, not semantic concept compounds.
- Minimal rule fields: id, pattern, preconditions (prime_mask_mask, rel_flags_mask), action, priority, base_confidence, success_rate, validation metrics, provenance, version, last_validated.

### Indexing
- Precompute masked keys and maintain an inverted index mapping masked-key → list(rule_ids).
- Use `rel_flags` bitset for additional indexing.
- Keep an in-memory hot LRU cache keyed by `(prime_mask_mask, rel_flags)` for fast lookups.

### Precondition matching (implementation)
- Match predicate:

```
match = ((C_primes & R_primes_mask) == R_primes_mask) \
  and ((C_rel_flags & R_rel_flags_mask) == R_rel_flags_mask)
```

- AND semantics by default. Add absent masks for negative preconditions in future revisions.

## Rule Lifecycle & Distillation

- Proposal: specialists propose via the symbolicifier.
- Validation: run against historical corpus/held-out set to compute precision/recall/F1 and coverage.
- Distillation: convert passing candidates into deterministic artifacts (regex, decision-tree) and persist alongside the `rule` compound.
- Activation: versioned activation with optional shadow-mode. Deactivation records reason and supports rollback on regressions.

### E2E test requirement
- After implementing rule storage & indexing, include an E2E test that inserts a `rule` compound, simulates a header, verifies lookup/application, and supports shadow-mode.

## Credit Assignment & Telemetry

- THINK emits `rule_usage` and later `rule_outcome` events. Decision compounds store `applied_rule_ids`.

### Fractional credit formula (implementation)
- For `applied_rule_ids = [r1..rN]` and `outcome_value` ∈ {0,1}:

```
delta = outcome_value * (learning_rate / N)
success_rate := success_rate * (1 - α) + α * outcome_value
```

- Configure `α` (start 0.05) and `learning_rate` conservatively.

## Conflict Resolution & Specificity

- Apply rules in order: `priority` → `specificity` (condition count) → `validation_f1` → `recency`.
- Compatibility: rules with disjoint targets (different slots, non-overlapping spans, disjoint primes) are compatible and may be merged.
- Incompatible: conflicting assignments to same target or contradictory primes/relations. Default: pick top-priority rule and log conflicts; enable composition later after study.

## Decay, TTL & Revalidation

- Active confidence decay:

```
active_confidence = base_confidence * (0.5)^(days_since_last_success / half_life)
```

- Default half_life: semantic rules 30 days, syntactic rules 7 days.
- Keep `last_success` (from credit updates) and `last_validated` (from validation runs) distinct.
- Background revalidation refreshes `last_validated` and demotes failing rules.

## Background Enrichment & DATA–KNOW Integration

- KNOW's maintenance thread enqueues compound IDs (grounded=False or flagged for enrichment)
  to `background_tasks` with priority and TTL. SYMBOL workers consume batches, run specialists,
  propose refinements via `KNOW.refine_definition()`, and persist rule proposals to KNOW.

### Queue constraints
- Bounded queue: when full, apply backpressure or drop lowest-priority tasks and increment drop counters.
- Workers yield after `BATCH_YIELD_SIZE` (default 10).
- PII sanitization required before persisting proposals; use sanitized datasets for validation.

## Governance, Audit & Sandbox

- Store proposer metadata, validator run IDs, activation records, and supersession links in rule compounds.
- Sandbox: use fixed corpus snapshot for deterministic replay runs; record metrics and compare to baseline.
- Human-in-the-loop thresholds default: affect >1% compounds or change >5% decisions require approval.
- Audit logs for every activation/deactivation with reason and metrics.

## Metrics & Dashboards

- Routing fallback rate, model call savings, rule coverage, precision/recall/F1, conflict rate, churn rate, specialist latency (GPU/CPU), rule freshness, downstream effect metrics.
- Expose `rule_conflict_rate`, `rule_freshness_seconds`, `specialist_latency_gpu_p99`, `specialist_latency_cpu_p99`, `rule_churn_per_day`.

## Risks & Mitigations

(See below for full risk table)

---

## Family Member Enrichment Cascade

When a root compound's definition is enriched (new primes, updated confidence, added
relations), all family members must be refreshed to maintain the superset invariant.

**Cascade trigger:** `KNOW.refine_definition(root_id, updated_primebit=...)` detects
that the target compound has family members (compounds with KIND → root_id relations).

**Cascade steps:**
1. KNOW queries all compounds with `Relation(predicate="KIND", target_id=root_id)`
2. For each family member: recompute `member.primebit = new_root_primebit | member_grammatical_primes`
3. Update each member via `refine_definition()` with provenance `{"source": "family_cascade", "root_id": root_id}`
4. Member version is incremented; the cascade is recorded in the member's Definition Narrative thread

**Grammatical prime preservation:** the cascade must not strip the member's grammatical
primes. The member's grammatical primes are determined by its WITH→prime relations in
its Definition Narrative. During cascade, these are read and re-OR'd with the new root
primebit.

**Phase 1:** cascade is logged but not auto-executed (requires KNOW family index).
**Phase 2:** automated cascade via KNOW's maintenance thread at priority 20.

---

- Cold start: bootstrap with hand-crafted rules.
- Rule explosion: quotas, pruning, consolidation jobs.
- Feedback delay: use credit assignment + stored rule_ids.
- Resource constraints: adapters + quantization + CPU batching.
- Drift: TTL, scheduled revalidation, shadow testing, conservative thresholds.
- PII: sanitize and restrict access to raw observations; audit all access.

## Default Thresholds

- Router fallback: 1–5% before adding micro-classifier.
- Rule activation F1 >= 0.85.
- Auto-demote: success_rate < 0.6 after N uses (default N=100).
- HITL: affect >1% compounds or change >5% decisions.

## Prioritized Implementation Roadmap

1. Implement deterministic router + routing counters and expose `get_router_stats()` in `KNOW`.
2. Specify model footprint policy and prototype one specialist.
3. Define symbolicifier JSON schema and schema validator; add calibration plan.
4. Implement `rule` compound schema in `KNOW`, masked-key indexing, and in-memory LRU cache.
4.1 Add E2E rule lookup test (insert rule → simulate header → verify lookup & application; support shadow-mode).
5. Instrument `THINK` to emit `rule_usage` and `rule_outcome`; add fractional credit assignment.
6. Build background enrichment queue and idle-time worker skeleton in `DATA`/`KNOW`.
7. Start collecting metrics and build basic dashboards.
8. Implement sandbox/replay harness and governance for HITL activations.

---

Appendix A — Example symbolicifier output schema

```json
{
  "candidate_primes": [{"prime":"IF","score":0.92}],
  "roles": [{"span":[10,12],"role":"condition","score":0.87}],
  "rule_template": {"pattern":"<if> .* <then>","slots":["condition","action"]},
  "confidence":0.89,
  "provenance":{"model":"grounder-v1","adapter":"if-detector"}
}
```

Appendix B — Example `rule` compound

```json
{
  "id":10001,
  "compound_type":"internal",
  "sub_type":"rule",
  "symbol":"rule_if_then_pattern",
  "pattern":"<if> .* <then>",
  "preconditions":{"prime_mask_mask":255,"rel_flags_mask":3},
  "action":{"create_template":"IF(condition,action)"},
  "priority":100,
  "base_confidence":0.92,
  "validation":{"f1":0.91,"precision":0.93,"recall":0.89},
  "provenance":{"proposed_by":"grounder-v1","proposed_at":"2026-02-18T..."},
  "version":1
}
```