DATA – Architecture

This document describes how DATA is implemented. The conceptual contract lives in CONCEPT.md;
implement DATA according to both.


1. Module and Singleton

DATA lives in primes/DATA.py and exports a singleton instance:

```python
# primes/DATA.py
from core.prime_base import Prime

class DATA(Prime):
    ...

data = DATA()   # singleton exported at module level
```

No other prime imports DATA's internals. All cross-prime calls use dynamic import and
call the singleton via `__call__`.


2. Threading Model

DATA runs one daemon thread, started in `_on_initialize()`, that drains candidate_queue:

```
Main process
  └── DATA thread   (loop: pull candidate → validate → build compounds → push to KNOW)
  └── caller thread (consultation mode: __call__ runs synchronously, returns Compound)
```

The candidate_queue thread and consultation mode are independent. Both paths run through
the same internal `_process_candidate()` method to ensure consistent validation logic.

DATA's thread skeleton:

```python
def _candidate_loop(self):
    while self._running:
        try:
            candidate = candidate_queue.get(timeout=0.1)
            self._process_candidate(candidate)
        except queue.Empty:
            continue
        except Exception as e:
            self._log_error(e)   # log and continue — never let the loop die
```


3. Processing Pipeline (per candidate)

`_process_candidate(candidate)` executes these steps in order:

```
1. validate_primes(candidate)
   → check each item in candidate["candidate_primes"] against PRIME_SET (63 names)
   → unknown prime name → mark token as ungrounded (placeholder)
   → confidence < GROUND_THRESHOLD (default 0.6) → mark as placeholder

2. detect_logic_operators(candidate)
   → check each token text against LOGIC_TOKEN_MAP (loaded from core/logic_compounds.json)
   → match found → substitute logic compound ID directly (IDs 100–199)
   → skip SYMBOL grounding for these tokens entirely

3. assign_observation_id(candidate)
   → obs_id = f"obs_{int(time.time() * 1000)}"
   → passed to KNOW for recording in the active Instance Narrative
   → NOT stamped on Compounds — observation context is instance-specific,
     compounds are universal

4. resolve_or_create_concept_compounds(candidate)
   → one Layer 0 Compound per unique surface form — but only if not already in KNOW
   → for each token:
       existing = know.by_symbol(token_text)   # exact surface form match
       if existing: use existing compound — no new compound created
         (works for both roots and family members — "ran" found directly)
       if not found:
           # SYMBOL has already resolved family membership in the candidate
           grounded tokens:   Compound.concept(symbol=token, primebit=..., grounded=True,
                                               nested=kind_chain, relations=kind_relations)
           placeholder tokens: Compound.concept(symbol=token, grounded=False, primebit=empty)
   → family member candidates arrive with nested=[root_id] and relations=[KIND→root_id]
     already set by SYMBOL — DATA validates but does not derive family structure
   → no provenance on the compound — observation context goes to Instance Narrative
   → relations from candidate["roles"] deferred to Phase 2

5. build_utterance_compound(concept_compounds)
   → one Layer 1 Compound for the full observation
   → compound_type="utterance"
   → nested = ordered list of concept compound IDs (temp for new, permanent for existing)
   → symbol = candidate["raw_input"]
   → primebit = union of all concept compound primebits

6. push_to_know(new_concept_compounds + utterance_compound)
   → only NEW concept compounds pushed (existing ones already in KNOW)
   → KNOW.store_batch assigns permanent IDs, creates Definition Narratives for new concepts
   → KNOW emits Layer 1 commit event on utterance compound storage
```


4. Compound Construction

Compounds are built using the Compound class from core/compound.py.
Temporary negative IDs are used until KNOW assigns permanent ones:

```python
def _next_temp_id(self) -> int:
    self._temp_counter -= 1
    return self._temp_counter   # starts at -1, decrements each call
```

KNOW replaces all negative IDs with permanent sequential IDs (200+) before storage.


5. Logic Token Map

On `_on_initialize()`, DATA loads core/logic_compounds.json into a dict:

```python
self._logic_map: dict[str, int] = {}
# {"and": 100, "or": 101, "not": 102, "if": 103, "then": 104, ...}
```

This dict is read-only after loading. Logic operator detection is a simple key lookup:

```python
def _detect_logic(self, token_text: str) -> int | None:
    return self._logic_map.get(token_text.lower())
```


6. Consultation Mode

In consultation mode, DATA is called directly by THINK with a pre-built candidate or
a raw text string. The candidate_queue is bypassed entirely:

```python
def __call__(self, context: dict) -> Compound:
    candidate = context.get("candidate") or self._text_to_candidate(context["symbol"])
    compounds = self._process_candidate(candidate)
    return compounds["utterance"]   # return utterance Compound to caller
```

`_text_to_candidate(text)` builds a minimal candidate using heuristic-only grounding
(same path as Phase 1 autonomous mode). The queue, change detection, and flood
protection are all skipped.


7. Queue Boundaries

```
candidate_queue  →  DATA thread reads
KNOW input       ←  DATA pushes validated Compounds
```

DATA never reads from observation_queue.
DATA never calls SYMBOL or READ.
DATA never writes to think_queue (that is SELF's responsibility).


8. Statistics

DATA maintains thread-safe counters updated in `_process_candidate()`:

```python
self.stats = {
    "observations_processed":  0,
    "concepts_found":          0,   # tokens resolved to existing KNOW compounds
    "concepts_created":        0,   # new concept Compounds created for unknown symbols
    "utterances_assembled":    0,
    "grounded_directly":       0,
    "placeholders_created":    0,
    "logic_operators_found":   0,
    "validation_failures":     0,
}
```

A validation failure increments `validation_failures` and discards the candidate.
The loop continues — one bad candidate never stops DATA.


9. Constants

```python
GROUND_THRESHOLD = 0.6      # Minimum confidence to accept a prime assignment
PRIME_SET = { ... }         # Set of all 63 valid prime name strings
LOGIC_TOKEN_MAP = { ... }   # Loaded from core/logic_compounds.json at startup
```


10. Phase 1 Scope

  ✅ Daemon thread draining candidate_queue
  ✅ Prime validation against PRIME_SET
  ✅ Logic operator detection and substitution
  ✅ KNOW-first lookup — resolve existing concept compounds before creating new ones
  ✅ Layer 0 concept Compound creation (grounded + placeholder) for unknown symbols only
  ✅ Layer 1 utterance Compound assembly (nested, symbol, primebit union)
  ✅ Temporary ID assignment; KNOW.store_batch assigns permanent IDs
  ✅ Observation ID passed to KNOW for Instance Narrative — not stored on Compounds
  ✅ Consultation mode (__call__)
  ✅ Statistics counters (concepts_found, concepts_created)
  ❌ Role-based relation population (Phase 2 — candidate["roles"] parsed but not mapped)
  ❌ Background enrichment queue for placeholder tokens (Phase 2 — KNOW maintenance thread)