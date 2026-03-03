# SYMBOL – Concept


## Overview

SYMBOL is PABLO's interpretation prime. Its job is to resolve human-language symbols
into prime-grounded Compounds — to find or build the meaning behind each word.

A symbol is a pointer. "cat" is not a concept — it is a handle that points to a
Compound encoding what a cat actually is: a living entity with a body that can move
and be felt. SYMBOL is the component that performs this resolution. Without SYMBOL,
raw observations are just text. With SYMBOL, they become meaning.

SYMBOL operates in two modes:

  Autonomous      Runs continuously, consuming raw observations from the observation
                  queue and producing near-compound candidates for DATA to validate.

  On-demand       Called directly by THINK or KNOW to ground a specific placeholder
                  compound or enrich an existing definition. Returns a grounded result
                  immediately to the caller.

SYMBOL never writes to KNOW directly. It proposes. DATA and KNOW are the gatekeepers.


## What SYMBOL Does

Given a raw observation or a placeholder compound, SYMBOL:

1. Identifies the symbols (tokens) present
2. For each symbol, checks if a compound with that exact surface form already exists
   in KNOW (via by_symbol — exact string match, not fuzzy)
3. If found: returns the existing compound — no new grounding needed
   (this works for both root compounds and family members — "ran" is found directly)
4. If not found: attempts family member derivation (see Lemmatization below)
5. If family derivation fails: proposes a prime assignment for a new root concept
6. Constructs a near-compound candidate encoding the proposed meaning
7. Passes the candidate to DATA for validation and storage

Over time, as PABLO encounters symbols in more contexts, SYMBOL also:

7. Proposes refinements to existing Definition Narratives — adding or adjusting
   relations, updating primebit confidence, recording co-occurrence patterns
8. Promotes high-confidence candidate interpretations to the active definition
9. Retires low-confidence candidates that have not been reinforced

The goal is for KNOW's compound graph to gradually become the primary grounding
reference — so that new symbols can be interpreted by proximity to existing compounds
without invoking any LLM at all.


## Symbol Resolution — The Two-Phase Lifecycle

**Phase 1 — LLM-bootstrapped (early system)**

When PABLO first encounters a symbol it has never seen, KNOW has no compound for it.
SYMBOL invokes a specialist model to propose a prime assignment. The specialist
produces a near-compound candidate. DATA creates a placeholder compound with
grounded=False. The compound enters KNOW unconfirmed.

Over subsequent encounters, SYMBOL accumulates evidence:
- Which primes co-occur with this symbol
- What structural roles the symbol plays (agent, object, modifier)
- What the symbol's relationships are to already-grounded compounds

As confidence rises above the grounding threshold, SYMBOL marks the compound
grounded=True and begins building its Definition Narrative with confirmed relations.

**Phase 2 — Self-grounded (mature system)**

As KNOW's compound graph grows richer, new symbols can often be interpreted by
finding the nearest existing compound cluster — no LLM needed. "feline" clusters
near "cat". "sprint" clusters near "run" and "MOVE". The graph itself becomes the
dictionary.

Compound Families accelerate this convergence: once a root like "run" is fully
grounded, all its inflected forms ("ran", "running", "runs") can be derived via
morphological analysis + KIND relation, without any LLM call. The family structure
means a single well-grounded root unlocks automatic grounding of every inflection.

LLMs remain available for genuinely novel concepts with no close neighbors in the
graph, but they become the exception rather than the rule.

This transition is gradual and automatic. SYMBOL always tries heuristics and graph
proximity first. LLMs are the fallback, not the default.


## The Reverse Pyramid and Grounding

Every compound SYMBOL produces must eventually resolve to the 63 primes. SYMBOL
enforces this by ensuring that every prime assignment it proposes is one of the
63 canonical primes, and every nested compound reference it creates points to an
existing compound in KNOW.

A compound is grounded when its full resolution terminates at primes — no dangling
references, no unresolved placeholders in its nested graph. SYMBOL is responsible
for driving compounds toward this state through the enrichment path.

Unknown concepts that cannot yet be grounded become placeholder compounds:
- primebit is a best-guess estimate
- grounded = False
- candidate_interpretations holds the alternatives SYMBOL considered
- KNOW queues the compound for background enrichment

Placeholders are first-class citizens — they flow through the pipeline and are
reasoned about by THINK. THINK knows they are uncertain and weights them accordingly.


## How SYMBOL Refines Definition Narratives

When SYMBOL enriches an existing compound, it does not overwrite the definition.
It proposes updates to the Definition Narrative through KNOW's explicit update API:

  KNOW.refine_definition(compound_id, new_relations, updated_primebit, confidence)

KNOW records the proposal in the Definition Narrative's thread with provenance
(which model, which observation triggered it, what confidence). The compound's
version is incremented. The old definition is never deleted — the thread preserves
the full refinement history.

This means PABLO can always answer "why does it think 'cat' means this?" by
walking the Definition Narrative's thread. Every prime assignment has a traceable
cause.


## Two Operating Modes

### 1. Ingestion Path (synchronous, low-latency)

Triggered per observation as it leaves the queue.

```
Raw observation
    → Router: check heuristics and KNOW graph proximity first
    → If confident: produce heuristic candidate directly
    → If not confident: invoke specialist model
    → Specialist produces near-compound candidate
    → Hand to DATA for validation
```

Must be fast. Prefer cached KNOW lookups and heuristic candidates on the hot path.
Never block the ingestion pipeline on a slow model call — fall back to a minimal
heuristic candidate and enqueue for async enrichment.

### 2. Enrichment Path (asynchronous, background)

Triggered by KNOW's background maintenance loop for stored compounds with
grounded=False or NEEDS_ENRICHMENT flag set.

```
Compound header from KNOW
    → Specialist proposes additional prime assignments, relation links, rule templates
    → Results proposed to KNOW via refine_definition()
    → Activated after validation and confidence thresholds are met
```

Does not block the ingestion path. Runs at low priority in KNOW's task pool.


## Lemmatization and Family Member Resolution

When SYMBOL encounters a token not found in KNOW by exact surface form, it attempts
family member derivation before falling back to LLM grounding. This is a cheap
morphological step that avoids model calls for inflected forms of known roots.

**Resolution order (per token):**

```
1. Exact lookup:    KNOW.by_symbol("ran")  →  found?  →  use it
2. Lemmatize:       "ran" → candidate root "run"
3. Root lookup:     KNOW.by_symbol("run")  →  found?
4. Create member:   new compound "ran" with:
                      primebit  = run.primebit | BEFORE
                      nested    = [run.id]
                      relations = [KIND → run.id]
                      grounded  = run.grounded
5. LLM fallback:    if no root found, invoke specialist for new root creation
```

**Lemmatization rules (Phase 1 — heuristic):**
- Strip common suffixes: -ing, -ed, -s, -es, -er, -est, -ly
- Check known irregular forms from dictionary INFLECTIONS tables
- Return candidate root(s) ordered by likelihood

**Grammatical prime selection:**
When creating a family member, SYMBOL determines which grammatical primes to add
based on the inflection type derived during lemmatization:

  -ed, irregular past     → BEFORE (past tense)
  -ing                    → NOW (progressive)
  -s, -es (noun)          → MANY (plural)
  -s (verb, 3rd person)   → OTHER + ONE (3rd person singular)
  -er (comparative)       → MORE
  -est (superlative)      → MORE + ALL
  will + verb             → AFTER (future)
  has/had + past part     → LAST (perfect)

**Irregular forms:**
Irregular inflections (went→go, better→good, mice→mouse) are resolved using the
dictionary INFLECTIONS tables loaded at startup. "went" is looked up, found as the
past tense of "go", and created as a family member of "go" with BEFORE — structurally
identical to regular forms. Irregularity is purely a surface-form lookup problem.

**Family member creation is idempotent:**
If SYMBOL creates "ran" as a family member of "run", subsequent encounters of "ran"
hit the exact lookup in step 1 and return immediately. No duplicate family members
are ever created.


## Near-Compound Candidate Shape

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

DATA treats this as a proposal, not ground truth. Unknown primes become placeholder
compounds. Low-confidence fields are flagged for background enrichment.


## Key Strategic Principles

- **Heuristic-first, deterministic preference**: use cheap heuristics and KNOW graph
  proximity before invoking any model. Models are only called when the graph cannot
  produce a confident candidate.

- **Specialists as proposal engines**: models produce near-compound candidates. They
  do not write to KNOW directly. DATA and KNOW are the gatekeepers.

- **Fail safe**: if a specialist fails or times out, fall back to a heuristic candidate.
  Never block the ingestion pipeline on a model call.

- **Conservative governance**: shadow-mode, replay sandbox, HITL thresholds, and
  audit logs before activating high-impact definition changes.

- **PII boundary**: raw observations are sanitised before reaching any model.

- **Graph convergence goal**: every specialist invocation should leave KNOW's compound
  graph slightly richer, so that the next similar symbol needs less LLM involvement.
  The long-term goal is a self-sufficient graph that rarely needs external models.


## Position in the System

```
Perceptors (Tier 1)
    ↓  raw observation dicts  {timestamp, modality, event_type, data, metadata}
SYMBOL autonomous thread (Tier 2)   ← multi-LLM runs here internally
    ↓  near-compound candidates  {candidate_primes, roles, spans, confidence, provenance}
DATA + KNOW (Tier 3)
    ↓  validates → real compounds with IDs and prime masks
THINK (Tier 4)
      ↓ calls SYMBOL on-demand to ground specific placeholders
SYMBOL on-demand
    ↓ refine_definition() → KNOW updates Definition Narrative
```


## Bootstrap Note

The ingestion path can operate with heuristic-only candidates (no model calls) in
Phase 1. Specialists are added incrementally as data accumulates. This keeps SYMBOL
a non-blocking dependency for early development — PABLO can run and learn with
pure heuristic grounding from day one.


## SYMBOL as Scaffolding — Retirement Roadmap

SYMBOL's sequential resolution cascade is a temporary construction. Each step
in the cascade IS an activation cloud assembly step performed manually and
sequentially. As the activation cloud matures, SYMBOL's steps dissolve into
cloud assembly one by one until SYMBOL is no longer needed.

### What SYMBOL does manually today

```
1. KNOW exact lookup       → cloud exact_match layer
2. Lemmatize + root lookup → cloud family_root layer
3. Family member creation  → cloud family_root layer
4. LLM specialist call     → cloud fast_path (if cloud not confident enough)
5. Prime-name heuristic    → cloud prime_candidates layer
6. Placeholder             → cloud unresolved → placeholder compound
```

Every step SYMBOL performs today is a future activation cloud capability.

### Retirement phases

```
Phase 1   SYMBOL does full cascade; activation cloud is built but advisory only.
          Cloud provides context to the LLM specialist (activation cloud as input).
          Cloud does NOT yet decide — SYMBOL decides.

Phase 2   Cloud handles all tokens already in KNOW (exact + family).
          SYMBOL only handles tokens not found in cloud — unknown/ambiguous.
          LLM specialist receives full activation cloud as context (not just token).
          Rule: if cloud fast_path = True → skip SYMBOL entirely for that token.

Phase 3   Cloud handles almost everything. SYMBOL = thin edge-case handler.
          Unknown tokens rare — KNOW graph large enough for most symbols.
          LLM specialist only called when cloud confidence < 0.4.

Phase 4   SYMBOL retired. All cascade logic absorbed into cloud assembly.
          Final pipeline: READ → activation cloud → THINK.
          DATA and KNOW do not disappear — they become internal mechanics of
          cloud assembly, not separate pipeline stages visible from outside.
```

### SYMBOL and DATA absorption

DATA does not disappear in Phase 4. Its validation contract — "every proposal must
meet the Compound contract before entering KNOW" — becomes an internal validation step
inside cloud assembly. SYMBOL and DATA are absorbed, not removed.

The pipeline simplifies externally:
```
Today:   READ → SYMBOL → DATA → KNOW → SELF → THINK
Phase 4: READ → activation cloud → THINK
```
The internal mechanics of the cloud include everything SYMBOL and DATA do today.


## Output Format Evolution

### Phase 1 (current) — candidate_primes bag

```json
{
  "candidate_primes": [{"prime": "MOVE", "score": 0.91}],
  "roles":            [{"span": [0, 3], "role": "agent", "score": 0.87}],
  "confidence":       0.89,
  "provenance":       {"model": "text-grounder-v1"}
}
```

### Phase 2.5 (DeepSeek extractor) — triple output

```json
{
  "triples": [
    {"source": "bite", "predicate": "FROM", "target_compound": "dog",   "confidence": 0.95},
    {"source": "bite", "predicate": "TO",   "target_compound": "man",   "confidence": 0.92},
    {"source": "bite", "predicate": "WITH", "target_prime": "BEFORE",   "confidence": 0.98}
  ],
  "activation_cloud_used": true,
  "confidence":       0.95,
  "provenance":       {"model": "deepseek-r1", "adapter": null}
}
```

The shift from prime bags to triples is the shift from "what primes are present"
to "what is the relationship between the compounds". Triples carry structure;
prime bags carry only a flat set.

DATA validates both formats. Triple output is preferred when available.


See SYMBOL_ARCHITECTURE.md for router internals, model-serving, symbolicifier contract,
rule schema, lifecycle, governance, and metrics.
See docs/TRIPLES/triple_concept.md for the triple concept and the predicate prime table.
See docs/ACTIVATION_CLOUD/activation_cloud_concept.md for the activation cloud.
See docs/PRIMES/COMPOUND/CONCEPT.md for what a Compound is and the reverse pyramid.
See docs/PRIMES/KNOW/CONCEPT.md for Definition Narrative storage and refinement API.
See docs/PRIMES/DATA/CONCEPT.md for how near-compound candidates become real Compounds.
See docs/SYSTEM/CONCEPT.md for the full tier overview.