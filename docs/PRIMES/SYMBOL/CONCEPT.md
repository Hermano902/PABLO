```markdown
# Multi-LLM Strategy

Status: draft — tier 2 (soft structurer in ingestion path)

Position in the system
The multi-LLM specialist fleet is the internal engine of the SYMBOL prime. SYMBOL owns interpretation — both the autonomous path (raw observations → near-compound candidates) and the on-demand path (placeholder compounds → grounded compounds). The multi-LLM layer is not a separate pipeline stage; it is how SYMBOL does its job when heuristics are insufficient.

```
Perceptors (Tier 1)
    ↓  raw observation dicts  {timestamp, modality, event_type, data, metadata}
SYMBOL autonomous thread (Tier 2)   ← multi-LLM runs here internally
    ↓  near-compound candidates  {candidate_primes, roles, spans, confidence, provenance}
DATA + KNOW (Tier 3)
    ↓  validates → real compounds with IDs and prime masks
THINK (Tier 4)
      ↓ calls symbol(on-demand) to ground specific placeholders
SYMBOL on-demand
```

Why this tier positioning
Defining a single rigid schema that covers a video frame, a line of text, and an audio event is impossible without losing either richness or simplicity. The multi-LLM layer solves this: specialist models handle the messy, modality-specific interpretation, then hand DATA a near-compound candidate in a shared minimal shape. DATA's job becomes contract enforcement — not parsing.

Two operating modes
1. Ingestion path (synchronous, low-latency)
   - Triggered per observation as it leaves the queue.
   - Router selects a specialist or falls back to heuristics.
   - Specialist produces a near-compound candidate.
   - DATA validates and creates real compounds.
   - Must be fast; prefer cached rules and header-only reads on the hot path.

2. Enrichment path (asynchronous, background)
   - KNOW idle loop enqueues stored compounds for deeper analysis.
   - Specialists propose new rules, refine prime assignments, fill placeholders.
   - Results stored as `rule` compounds; activated after validation and governance checks.
   - Does not block the ingestion path.

Near-compound candidate shape
The shared output contract for all specialists, regardless of modality:

```json
{
  "candidate_primes": [{"prime": "MOVE", "score": 0.91}],
  "roles":            [{"span": [0, 3], "role": "agent", "score": 0.87}],
  "rule_template":    {"pattern": "<agent> <MOVE> <direction>", "slots": ["agent", "direction"]},
  "confidence":       0.89,
  "provenance":       {"model": "text-grounder-v1", "adapter": "motion-detector"},
  "raw_input":        "the cat moved left"
}
```

DATA treats this as a proposal, not ground truth. Unknown primes become placeholder compounds; low-confidence fields are flagged for background enrichment.

Key strategic principles
- Router-first, deterministic preference: use cheap heuristics and `rel_flags` header checks before invoking any model. Models are only called when heuristics cannot produce a confident candidate.
- Specialists as proposal engines: micro-LLMs produce near-compound candidates. They do not write to KNOW directly. DATA and KNOW are the gatekeepers.
- Fail safe: if a specialist fails or times out, fall back to a heuristic candidate. Never block the ingestion pipeline on a model call.
- Conservative governance: shadow-mode, replay sandbox, HITL thresholds, and audit logs before activating high-impact rules.
- PII boundary: raw observations are sanitised before reaching any model.

Bootstrap note
The ingestion path can operate with heuristic-only candidates (no model calls) in Phase 1. Specialists are trained and activated incrementally as data accumulates. This keeps Tier 2 a non-blocking dependency for early development.

See SYMBOL_ARCHITECTURE.md for router internals, model-serving, symbolicifier contract, rule schema, lifecycle, governance, and metrics.
See docs/SYSTEM/CONCEPT.md for the full tier overview.

```
