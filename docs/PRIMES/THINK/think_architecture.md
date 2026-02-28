THINK – Architecture

This document describes how THINK is implemented. The conceptual contract lives in CONCEPT.md;
implement THINK according to both.


1. Module and Singleton

THINK lives in primes/THINK.py and exports a singleton instance:

```python
# primes/THINK.py
from core.prime_base import Prime

class THINK(Prime):
    ...

think = THINK()   # singleton exported at module level
```


2. Threading Model

THINK runs one daemon thread that drains think_queue:

```
Main process
  └── THINK thread   (loop: pull from think_queue → execute reasoning cycle)
  └── caller thread  (consultation mode: __call__ runs synchronously, returns Compound)
```

THINK's thread and consultation mode are independent. Both paths share the same internal
`_run_cycle()` method to ensure identical reasoning logic.

```python
def _on_initialize(self):
    self._think_thread = threading.Thread(target=self._think_loop, daemon=True)
    self._think_thread.start()

def _think_loop(self):
    while self._running:
        try:
            item = think_queue.get(timeout=0.1)
            self._run_cycle(item)
        except queue.Empty:
            continue
        except Exception as e:
            self._log_error(e)   # log and continue — a crashed cycle must never kill the loop
```


3. Reasoning Cycle

`_run_cycle(item)` executes these steps in order. `item` is the dict pushed by SELF
containing `utterance_compound_id`, `source`, `salience`, `want_context`, `feel_state`.

```
Step 1  — Fetch utterance compound
          know.by_id(utterance_compound_id)
          → Layer 1 aggregate Compound

Step 2  — Identify or create Narrative context
          know.narrative_by_source(source)
          → open Narrative found → resume (load bindings + constraints)
          → not found → know.store_narrative(Narrative(...)) → new episodic frame

Step 3  — Resolve utterance tokens to Narrative bindings
          know.by_ids(utterance.children) → Layer 0 token Compounds
          for each token: match text to existing binding or create new binding
          all further reasoning uses binding local_names, not raw compound IDs

Step 4  — Check active Constraints
          load narrative.constraints where active=True
          if any constraint is violated by the current intent → revise before proceeding

Step 5  — PrimeBit population analysis
          merge all token primebits → dominant_primebit
          determine routing mode from routing table (see section 4)

Step 6  — Macro match (Layer 4 lookup)
          know.by_trigger(dominant_primebit)
          → match found → execute macro.execution_path with slots filled → go to Step 9

Step 7  — Action match (Layer 3 lookup)
          know.by_type("action") filtered by trigger_condition match
          → match found → execute action.execution_path → go to Step 9

Step 8  — Intent construction (Layer 2)
          build Layer 2 Intent Compound (compound_type="definition")
          know.store(intent_compound)
          determine response text from routing mode

Step 9  — Update Narrative
          update binding.current for any entities whose state changed
          append Snap to binding.history with cause + event_ref
          log NarrativeEvent to narrative.thread
          assert new Constraints if warranted
          know.store_narrative (or update in place — KNOW's store handles both)

Step 10 — Compose response
          build response text based on routing mode result

Step 11 — Push to response_queue
          response_queue.put({
              "timestamp":   time.time(),
              "type":        "response",
              "text":        response_text,
              "compound_id": intent_compound.id if created else None,
              "source":      source,
          })
```


4. Routing Table

Population analysis produces a `dominant_primebit`. The routing table maps prime families
to reasoning modes:

```python
ROUTING_TABLE = [
    ({"KNOW", "BE"},           "knowledge_query"),
    ({"SAY", "YOU"},           "directed_message"),
    ({"DO", "MOVE"},           "action_request"),
    ({"DO", "MAKE"},           "action_request"),
    ({"DO", "CHANGE"},         "action_request"),
    ({"WANT"},                 "preference_expression"),
    ({"NEED"},                 "requirement_expression"),
    ({"THINK", "SELF"},        "introspective_query"),
]
DEFAULT_MODE = "reflective_acknowledgement"

def _determine_routing(self, dominant_primebit) -> str:
    for prime_set, mode in ROUTING_TABLE:
        if all(dominant_primebit.has(p) for p in prime_set):
            return mode
    return DEFAULT_MODE
```

Each mode has a corresponding `_respond_<mode>(narrative, utterance, tokens)` method
that produces the response text.


5. PrimeBit Population Analysis

```python
def _analyse_population(self, token_compounds: list) -> dict:
    counts: dict[str, int] = {}
    for token in token_compounds:
        for prime_name in token.primebit.active_primes():
            counts[prime_name] = counts.get(prime_name, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
```

The resulting counts dict is used to build `dominant_primebit` (primes appearing in
more than half the tokens) and to pass context to routing and response methods.


6. Macro Candidacy (Layer 4 Creation)

THINK tracks successful Layer 3 Action executions using a fingerprint counter:

```python
self._action_fingerprints: dict[int, int] = {}   # compound_id → success count

def _record_success(self, action_compound_id: int):
    self._action_fingerprints[action_compound_id] = \
        self._action_fingerprints.get(action_compound_id, 0) + 1
    if self._action_fingerprints[action_compound_id] >= MACRO_THRESHOLD:   # default 3
        self._promote_to_macro(action_compound_id)
```

`_promote_to_macro()` creates a Layer 4 Macro Compound from the Action and calls
`know.store()`. The Macro is then available to all future cycles via Step 6.


7. Consultation Mode

THINK can be called on-demand by any prime:

```python
def __call__(self, context: dict) -> Compound:
    # Build a synthetic think_queue item from context
    item = {
        "utterance_compound_id": context["utterance_id"],
        "source": context.get("source", "internal"),
        "salience": context.get("salience", 1.0),
        "want_context": "consultation",
        "feel_state": "neutral",
    }
    return self._run_cycle(item)
```

Returns the Layer 2 Intent Compound created during the cycle, or the most relevant
Compound THINK found if no Intent was created.


8. Queue Boundaries

```
think_queue      →  THINK thread reads (written by SELF only)
response_queue   ←  THINK writes (read by GUI timer)
KNOW             ←  THINK writes (Layer 2/3/4 compounds, Narrative updates)
KNOW             →  THINK reads (all compound lookups)
```

THINK never writes to observation_queue or candidate_queue.
THINK never calls DATA or SYMBOL.
THINK never calls any GUI function directly.


9. Phase 1 Scope

  ✅ Daemon thread draining think_queue
  ✅ Fetch Layer 1 + Layer 0 compounds from KNOW
  ✅ Narrative identification (new vs resume) via KNOW
  ✅ Compound → Narrative binding resolution
  ✅ PrimeBit population analysis
  ✅ Routing table (8 modes + default)
  ✅ Layer 2 Intent Compound written to KNOW each cycle
  ✅ Narrative binding update + Snap append + NarrativeEvent log
  ✅ Response pushed to response_queue
  ✅ Consultation mode (__call__)
  ❌ Constraint checking (Phase 2 — structures created but not yet enforced)
  ❌ Layer 3 Action execution (Phase 2)
  ❌ Layer 4 Macro creation (Phase 2)
  ❌ KNOW.by_trigger() indexed lookup (Phase 2 — Phase 1 uses linear scan)
  ❌ Early pre-load signal from SELF (Phase 2)
