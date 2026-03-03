# KNOW — Architecture & Implementation

This document describes how KNOW is implemented. The conceptual contract lives
in KNOW_CONCEPT.md; implement KNOW according to both.

It is phase-separated: Phase 1 is the complete implementable target. Phase 2+
sections are preserved for future reference and must not be implemented until
the relevant phase begins.

---

## PHASE 1 — Implement Now

---

### 1. Module and Singleton

KNOW lives in `primes/KNOW.py` and exports a singleton instance:

```python
# primes/KNOW.py
from core.prime_base import Prime

class KNOW(Prime):
    ...

know = KNOW()   # singleton exported at module level
```

All primes import and use this singleton. No prime instantiates KNOW directly.

---

### 2. Storage Structure

Phase 1 uses four in-memory dictionaries with a single RLock for thread safety.
The sharded sub-record architecture is Phase 2 (see D1). Phase 1 is designed
so the interface is identical — callers never touch the store directly, only
through the public API. Sharding can be introduced behind that API in Phase 2
without changing any caller code.

```python
# core compound records
self._compounds:    dict[int, Compound]         = {}
self._symbol_index: dict[str, int]              = {}   # symbol → compound_id, O(1) lookup
self._lock          = threading.RLock()
self._next_id:      int = 200

# definition narratives — one per compound, loaded on demand
self._definitions:  dict[int, DefinitionNarrative] = {}
self._def_lock      = threading.RLock()
self._next_def_id:  int = 1

# instance narratives — episodic and relational
self._narratives:   dict[int, Narrative]        = {}
self._nar_lock      = threading.RLock()
self._next_nar_id:  int = 1

# refinement tracking — usage signals per compound
self._refinement:   dict[int, RefinementRecord] = {}
self._ref_lock      = threading.RLock()

# triple store — all relational triples (definition + utterance)
self._triples:        dict[int, Triple]          = {}   # triple_id → Triple
self._triple_index:   dict[int, list[int]]        = {}   # source_id → [triple_id, ...]
self._tri_lock        = threading.RLock()
self._next_triple_id: int = 1
```

#### RefinementRecord

```python
@dataclass
class RefinementRecord:
    compound_id:  int
    usage_count:  int   = 0
    success_rate: float = 0.0
    query_count:  int   = 0
```

KNOW creates a RefinementRecord for every compound on storage. Updated
automatically on every access and outcome event — no caller needs to manage it.

#### ID Spaces

```
Compound IDs:             0–99 reserved, 100–199 logic, 200+ runtime
Definition Narrative IDs: separate counter, starts at 1
Instance Narrative IDs:   separate counter, starts at 1
```

No ID space overlaps. Counters are loaded from `storage/metadata.json` on startup.

---

### 3. Hot Cache

Phase 1 hot cache is a simple LRU dict over compound core records. Full LRU
eviction policy is Phase 2 (see D2). Phase 1 implements a fixed-size dict that
evicts the oldest entry when full.

```python
from collections import OrderedDict

self._cache: OrderedDict[int, Compound] = OrderedDict()
self._cache_max_size: int = 1000   # configurable

def _cache_get(self, id: int) -> Compound | None:
    if id in self._cache:
        self._cache.move_to_end(id)
        return self._cache[id]
    return None

def _cache_put(self, compound: Compound) -> None:
    self._cache[compound.id] = compound
    self._cache.move_to_end(compound.id)
    if len(self._cache) > self._cache_max_size:
        self._cache.popitem(last=False)
```

Logic compounds (100–199) are always pre-loaded into the cache at startup and
never evicted — they are needed constantly by all primes.

---

### 4. Threading Model

Phase 1 uses a simple threading model. The priority thread pool is Phase 2 (see D3).
Phase 1 threading:

```
Main process
  └── KNOW autosave thread      periodic serialisation to disk
  └── KNOW maintenance thread   background enrichment queue drain
  └── caller threads            all store/retrieve calls — synchronous, any thread
                                protected by appropriate lock per store
```

All public API methods are safe to call from any thread. Locks are per-store
and never held across I/O operations.

---

### 5. Initialization

```python
def _on_initialize(self):
    self._load_logic_compounds()    # populate IDs 100–199, pre-cache all
    self._load_from_disk()          # restore compounds, definitions, narratives
    self._start_autosave_thread()
    self._start_maintenance_thread()
```

Logic compounds are always loaded first. Disk load follows. If disk is empty or
persistence is disabled, KNOW starts with only logic compounds in the store.

```python
def _load_logic_compounds(self):
    with open("core/logic_compounds.json") as f:
        entries = json.load(f)
    for entry in entries:
        c = Compound.from_dict(entry)
        self._compounds[c.id] = c
        self._cache_put(c)   # pre-cache all logic compounds — never evicted
```

---

### 6. Compound Store API

#### store_batch

Primary write path. DATA calls this after resolving temp IDs within a batch.

```python
def store_batch(self, compounds: list[Compound]) -> dict[int, int]:
    """
    Assign permanent IDs to all compounds in batch order.
    Update all nested and relation target_ids from temp to permanent.
    Create a DefinitionNarrative for each new concept compound.
    Set definition_narrative_id on each compound before persisting.
    Return {temp_id: permanent_id} map.
    """
    id_map: dict[int, int] = {}

    with self._lock:
        for compound in compounds:
            temp_id = compound.id
            compound.id = self._next_id
            self._next_id += 1
            id_map[temp_id] = compound.id

        # sweep: replace all remaining temp ID references
        for compound in compounds:
            compound.nested = [
                id_map.get(nid, nid) for nid in compound.nested
            ]
            for relation in compound.relations:
                if relation.target_id in id_map:
                    relation.target_id = id_map[relation.target_id]

        for compound in compounds:
            self._compounds[compound.id] = compound
            self._symbol_index[compound.symbol] = compound.id   # O(1) index
            self._cache_put(compound)
            self._refinement[compound.id] = RefinementRecord(compound_id=compound.id)

    # create definition narratives outside compound lock
    for compound in compounds:
        if compound.compound_type == "concept":
            def_id = self._create_definition_narrative(compound.id, compound.symbol)
            with self._lock:
                self._compounds[compound.id].definition_narrative_id = def_id

    # emit Layer 1 commit event if utterance compound in batch
    for compound in compounds:
        if compound.compound_type == "utterance":
            self._emit_layer1_event(compound.id, compound.symbol)

    return id_map
```

#### store (single compound)

Used by THINK for intent, action, macro compounds:

```python
def store(self, compound: Compound) -> int:
    """Assign permanent ID, store, return assigned ID."""
    with self._lock:
        compound.id = self._next_id
        self._next_id += 1
        self._compounds[compound.id] = compound
        self._cache_put(compound)
        self._refinement[compound.id] = RefinementRecord(compound_id=compound.id)
    if compound.compound_type == "utterance":
        self._emit_layer1_event(compound.id, compound.symbol)
    return compound.id
```

---

### 7. Compound Retrieval API

All retrieval methods update the refinement `query_count` automatically.

```python
def by_id(self, id: int) -> Compound | None:
    cached = self._cache_get(id)
    if cached:
        self._increment_query_count(id)
        return cached
    with self._lock:
        compound = self._compounds.get(id)
        if compound:
            self._cache_put(compound)
            self._increment_query_count(id)
        return compound

def by_ids(self, ids: list[int]) -> list[Compound]:
    return [c for c in (self.by_id(i) for i in ids) if c is not None]

def by_symbol(self, symbol: str) -> Compound | None:
    """Find existing concept compound by exact surface form string.
    Exact match — "ran" finds "ran", not "run".
    Used by DATA to check if a surface form is already known before creating new compound.
    Used by SYMBOL for exact lookup before attempting lemmatization.
    O(1) index lookup — symbol_index maintained by store_batch and _load_from_disk.
    """
    with self._lock:
        compound_id = self._symbol_index.get(symbol)
        if compound_id is None:
            return None
        compound = self._compounds.get(compound_id)
        if compound:
            self._increment_query_count(compound_id)
        return compound

def by_relation(self, predicate: str, target_id: int) -> list[Compound]:
    """Return all compounds that have a relation with the given predicate
    pointing to target_id. Used to find compound family members:
      by_relation("KIND", root_id) → all inflected forms of root.
    Also used for any relation-based graph traversal.
    Phase 1: linear scan over all compounds. Phase 2: relation index.
    """
    with self._lock:
        return [c for c in self._compounds.values()
                for r in c.relations
                if r.predicate == predicate and r.target_id == target_id]

def by_prime(self, prime_name: str) -> list[Compound]:
    """Return all compounds that include prime_name in their primebit."""
    with self._lock:
        return [c for c in self._compounds.values()
                if c.primebit.has(prime_name)]

def by_type(self, compound_type: str) -> list[Compound]:
    with self._lock:
        return [c for c in self._compounds.values()
                if _compound_type(c) == compound_type]

def by_trigger(self, primebit) -> list[Compound]:
    """Return action/macro compounds whose trigger_condition matches primebit."""
    with self._lock:
        return [c for c in self._compounds.values()
                if c.executable
                and c.trigger_condition is not None
                and c.trigger_condition & primebit == c.trigger_condition]

def search(self, query: dict) -> list[Compound]:
    """Return compounds matching all field conditions in query dict."""
    with self._lock:
        results = list(self._compounds.values())
        for field, value in query.items():
            results = [c for c in results if getattr(c, field, None) == value]
        return results

def _compound_type(self, compound: Compound) -> str:
    """Derive compound_type from compound structure since it is not stored."""
    if compound.executable:
        return "macro" if compound.id >= 200 else "action"
    if compound.id >= 100 and compound.id <= 199:
        return "logic"
    if compound.nested and not compound.relations:
        return "utterance"
    return "concept"
```

---

### 8. Definition Narrative API

#### _create_definition_narrative

Called internally by store_batch for each new concept compound.

```python
def _create_definition_narrative(self, compound_id: int, symbol: str) -> int:
    """Create an empty Definition Narrative for a new concept compound."""
    with self._def_lock:
        def_id = self._next_def_id
        self._next_def_id += 1
        self._definitions[def_id] = DefinitionNarrative(
            id=def_id,
            compound_id=compound_id,
            symbol=symbol,
            relations=[],
            thread=[],
            constraints=[],
            created_at=time.time(),
        )
    return def_id

def get_definition(self, compound_id: int) -> DefinitionNarrative | None:
    """Load the Definition Narrative for a compound. On-demand — not cached."""
    compound = self.by_id(compound_id)
    if compound is None or compound.definition_narrative_id is None:
        return None
    with self._def_lock:
        return self._definitions.get(compound.definition_narrative_id)

def refine_definition(
    self,
    compound_id:      int,
    new_relations:    list[Relation] | None = None,
    updated_primebit: PrimeBit | None = None,
    confidence:       float | None = None,
    provenance:       dict | None = None,
) -> bool:
    """
    Update a compound's definition. Called by SYMBOL after enrichment.
    Increments compound version. Appends to Definition Narrative thread.
    Returns True on success, False if compound not found.

    This is the ONLY permitted path for modifying primebit, relations,
    or confidence on a stored compound. No prime may modify these directly.
    """
    compound = self.by_id(compound_id)
    if compound is None:
        return False

    with self._lock:
        if updated_primebit is not None:
            compound.primebit = updated_primebit
        if confidence is not None:
            compound.confidence = confidence
        if new_relations:
            compound.relations.extend(new_relations)
        compound.version += 1

    definition = self.get_definition(compound_id)
    if definition is not None:
        with self._def_lock:
            definition.thread.append({
                "timestamp":   time.time(),
                "type":        "refinement",
                "provenance":  provenance or {},
                "primebit":    updated_primebit.value if updated_primebit else None,
                "relations":   [{"predicate": r.predicate, "target_id": r.target_id}
                                for r in (new_relations or [])],
                "confidence":  confidence,
                "version":     compound.version,
            })

    return True
```

---

### 9. Instance Narrative API

```python
def store_narrative(self, narrative: Narrative) -> int:
    with self._nar_lock:
        narrative.id = self._next_nar_id
        self._next_nar_id += 1
        self._narratives[narrative.id] = narrative
    return narrative.id

def get_narrative(self, id: int) -> Narrative | None:
    with self._nar_lock:
        return self._narratives.get(id)

def open_narratives(self) -> list[Narrative]:
    with self._nar_lock:
        return [n for n in self._narratives.values() if n.status == "open"]

def narrative_by_source(self, source: str) -> Narrative | None:
    with self._nar_lock:
        for n in self._narratives.values():
            if n.status == "open" and n.name.endswith(source):
                return n
    return None

def close_narrative(self, id: int) -> None:
    with self._nar_lock:
        n = self._narratives.get(id)
        if n:
            n.status = "closed"
            n.closed_at = time.time()

def archive_narrative(self, id: int) -> None:
    with self._nar_lock:
        n = self._narratives.get(id)
        if n:
            n.status = "archived"
```

---

### 10. Refinement Tracking API

```python
def _increment_query_count(self, compound_id: int) -> None:
    with self._ref_lock:
        rec = self._refinement.get(compound_id)
        if rec:
            rec.query_count += 1

def record_usage(self, compound_id: int) -> None:
    """Called by THINK when a compound is used in reasoning."""
    with self._ref_lock:
        rec = self._refinement.get(compound_id)
        if rec:
            rec.usage_count += 1

def record_outcome(self, compound_id: int, success: bool) -> None:
    """Called by THINK after execution outcome is known."""
    with self._ref_lock:
        rec = self._refinement.get(compound_id)
        if rec and rec.usage_count > 0:
            # rolling average
            rec.success_rate = (
                (rec.success_rate * (rec.usage_count - 1) + (1.0 if success else 0.0))
                / rec.usage_count
            )

def get_refinement(self, compound_id: int) -> RefinementRecord | None:
    with self._ref_lock:
        return self._refinement.get(compound_id)
```

---

### 11. Layer 1 Commit Event

When KNOW stores a Layer 1 utterance compound, it fires a commit event.
This is how SELF learns that a new utterance is ready for salience scoring.

```python
self._layer1_listeners: list[Callable] = []

def register_layer1_listener(self, callback: Callable) -> None:
    self._layer1_listeners.append(callback)

def _emit_layer1_event(self, compound_id: int, source: str) -> None:
    for cb in self._layer1_listeners:
        try:
            cb(compound_id, source)
        except Exception as e:
            self.stats["errors"] += 1
```

SELF registers itself as a listener during its own `_on_initialize()`:

```python
# primes/SELF.py
know.register_layer1_listener(self._on_utterance_committed)
```

---

### 12. Maintenance Thread

The maintenance thread drains a low-priority enrichment queue. In Phase 1 this
queue contains compounds flagged `grounded=False` that need SYMBOL enrichment.

```python
self._enrichment_queue: queue.Queue = queue.Queue()

def enqueue_enrichment(self, compound_id: int) -> None:
    """Called by store_batch for any compound stored with grounded=False."""
    self._enrichment_queue.put(compound_id)

def _maintenance_loop(self) -> None:
    while self._running:
        try:
            compound_id = self._enrichment_queue.get(timeout=1.0)
            self._request_enrichment(compound_id)
        except queue.Empty:
            continue

def _request_enrichment(self, compound_id: int) -> None:
    """Signal SYMBOL to enrich this compound. Phase 1: log only."""
    compound = self.by_id(compound_id)
    if compound and not compound.grounded:
        # Phase 2: call SYMBOL enrichment path
        # Phase 1: log for manual inspection
        self.stats["enrichment_queued"] += 1
```

---

### 13. Persistence

Autosave thread fires every `_autosave_interval` seconds (default 30):

```python
def _autosave_loop(self) -> None:
    while self._running:
        time.sleep(self._autosave_interval)
        self._save_to_disk()

def _save_to_disk(self) -> None:
    # snapshot under locks, write outside locks
    with self._lock:
        compounds_snapshot = {
            k: v.to_dict() for k, v in self._compounds.items()
            if v.id >= 200   # skip logic compounds (100–199)
        }
    with self._def_lock:
        definitions_snapshot = {
            k: v.to_dict() for k, v in self._definitions.items()
        }
    with self._nar_lock:
        narratives_snapshot = {
            k: v.to_dict() for k, v in self._narratives.items()
            if v.status != "archived"   # archived narratives compressed separately
        }
    with self._ref_lock:
        refinement_snapshot = {
            k: v.__dict__ for k, v in self._refinement.items()
        }
    meta = {
        "next_id":         self._next_id,
        "next_def_id":     self._next_def_id,
        "next_nar_id":     self._next_nar_id,
        "saved_at":        time.time(),
    }

    os.makedirs("storage", exist_ok=True)
    with open("storage/compounds.json",   "w") as f: json.dump(compounds_snapshot,   f)
    with open("storage/definitions.json", "w") as f: json.dump(definitions_snapshot, f)
    with open("storage/narratives.json",  "w") as f: json.dump(narratives_snapshot,  f)
    with open("storage/refinement.json",  "w") as f: json.dump(refinement_snapshot,  f)
    with open("storage/metadata.json",    "w") as f: json.dump(meta,                 f)

    self.stats["saves_to_disk"] += 1
```

On `_on_initialize()`, load from disk before starting background threads:

```python
def _load_from_disk(self) -> None:
    if os.path.exists("storage/metadata.json"):
        with open("storage/metadata.json") as f:
            meta = json.load(f)
        self._next_id     = meta.get("next_id",     200)
        self._next_def_id = meta.get("next_def_id", 1)
        self._next_nar_id = meta.get("next_nar_id", 1)

    if os.path.exists("storage/compounds.json"):
        with open("storage/compounds.json") as f:
            data = json.load(f)
        for raw in data.values():
            c = Compound.from_dict(raw)
            self._compounds[c.id] = c
            self._symbol_index[c.symbol] = c.id   # rebuild O(1) index
            self._cache_put(c)

    if os.path.exists("storage/definitions.json"):
        with open("storage/definitions.json") as f:
            data = json.load(f)
        for raw in data.values():
            d = DefinitionNarrative.from_dict(raw)
            self._definitions[d.id] = d

    if os.path.exists("storage/narratives.json"):
        with open("storage/narratives.json") as f:
            data = json.load(f)
        for raw in data.values():
            n = Narrative.from_dict(raw)
            self._narratives[n.id] = n

    if os.path.exists("storage/refinement.json"):
        with open("storage/refinement.json") as f:
            data = json.load(f)
        for k, v in data.items():
            self._refinement[int(k)] = RefinementRecord(**v)

    self.stats["loads_from_disk"] += 1
```

Persistence can be disabled for testing:

```python
know = KNOW(enable_persistence=False)
```

---

### 14. Statistics

```python
self.stats = {
    "compounds_stored":     0,
    "compounds_retrieved":  0,
    "definitions_loaded":   0,
    "narratives_stored":    0,
    "queries_processed":    0,
    "cache_hits":           0,
    "enrichment_queued":    0,
    "errors":               0,
    "loads_from_disk":      0,
    "saves_to_disk":        0,
}
```

---

### 15. Phase 1 Scope

```
✅ Four in-memory stores (compounds, definitions, narratives, refinement)
✅ Symbol index (_symbol_index: dict[str, int]) — O(1) by_symbol() lookup
✅ Simple LRU cache (OrderedDict, configurable max size)
✅ Sequential ID assignment per store, loaded from metadata on startup
✅ Logic compound loading (100–199), pre-cached at startup, never evicted
✅ store_batch — ID assignment, temp→permanent sweep, definition narrative creation
✅ store — single compound write for THINK
✅ Layer 1 commit event → SELF listener registration
✅ Retrieval: by_id, by_ids, by_symbol (O(1)), by_prime, by_type, by_trigger, by_relation, search
✅ Triple store (_triples + _triple_index) — see Section 16 below
✅ Triple API: store_triple, get_triples(source_id), get_triples_by_predicate
✅ Definition Narrative API: get_definition, refine_definition
✅ Instance Narrative API: store/get/open/close/archive/by_source
✅ Refinement tracking: record_usage, record_outcome, get_refinement
✅ Maintenance thread with enrichment queue (Phase 1: logs only)
✅ Autosave to four storage files every 30s
✅ Load from disk on startup (all four stores + metadata)
✅ Statistics counters
✅ enable_persistence=False for testing

❌ by_prime index (Phase 2 — currently linear scan)
❌ Priority thread pool (Phase 2 — see D3)
❌ Sharded sub-record stores (Phase 2 — see D1)
❌ Full LRU eviction policy (Phase 2 — see D2)
❌ Spreading activation / associative retrieval (Phase 2)
❌ Narrative archiving + compression (Phase 2)
❌ SYMBOL enrichment integration in maintenance thread (Phase 2)
❌ SQLite persistence backend (Phase 2)
```

---

### 16. Triple Store API (Phase 1)

Full API spec in docs/TRIPLES/triple_architecture.md. Summary:

```python
def store_triple(self, source_id, predicate, target_id, target_prime,
                 confidence=1.0, source="definition") -> int:
    """Store one triple. Validates predicate in PRIME_SET.
    Adds to _triples dict and _triple_index[source_id] list.
    Returns assigned triple_id."""

def get_triples(self, source_id: int) -> list[Triple]:
    """Return all outgoing triples for a compound. O(1) index lookup."""

def get_triples_by_predicate(self, source_id: int, predicate: str) -> list[Triple]:
    """Filter outgoing triples by predicate."""
```

Triple persistence: saved to `storage/triples.json` by autosave thread.
`next_triple_id` added to `storage/metadata.json`.

---

## PHASE 2+ — Deferred (Do Not Implement Yet)

---

### D1. Sharded Sub-Record Stores

Replace each in-memory dict with a sharded store:
`shard = id % NUM_SHARDS` (recommended: 32 or 64 shards per store type).
Per-shard locks replace the single store-level RLock. Allows concurrent primes
to access different compounds without any lock contention.

Sub-record split for compounds:
- `core` — id, symbol, primebit, grounded, version, confidence, nested_ids
- `execution` — execution_path, trigger_condition, arity, slots
- `refinement` — usage_count, success_rate, query_count (already separate in Phase 1)

Sub-record split for narratives:
- `header` — id, name, status, created_at
- `thread` — NarrativeEvent log
- `bindings` — local_name → Binding map (instance narratives)
- `relations` — predicate → target entries (definition narratives)
- `constraints` — active and inactive Constraint list

---

### D2. Full LRU Cache with TTL

Replace OrderedDict with a proper LRU + TTL cache per sub-record type.
Separate cache tiers for hot (core) and warm (execution, relations) sub-records.
Cache size tuned to available memory. TTL defaults: core 5 min, relations 2 min.

---

### D3. Priority Thread Pool

Replace synchronous caller-thread API with a priority task queue and fixed
worker pool (one thread per CPU core).

Priority levels:
- 100: THINK — conscious reasoning
- 80:  SELF — salience scoring
- 60:  SYMBOL — on-demand grounding
- 40:  DATA — observation storage
- 20:  Background enrichment
- 5:   Maintenance (consolidation, forgetting, index rebuild)

Tasks yield on lock contention — worker moves to next task rather than blocking.
Fixed global lock order prevents deadlock.

---

### D4. Indexes

**Note: `_symbol_index` has been moved to Phase 1 (see Section 2 and 7).**
It is already implemented — O(1) `by_symbol()` lookup via `dict[str, int]`.

Add remaining in-memory indexes for fast retrieval without linear scan:
- `_symbol_index: dict[str, int]` — symbol → compound_id
- `_prime_index: dict[str, set[int]]` — prime_name → set of compound_ids
- `_type_index: dict[str, set[int]]` — compound_type → set of compound_ids
- `_trigger_index: list[tuple[PrimeBit, int]]` — sorted trigger_condition → compound_id
- `_family_index: dict[int, set[int]]` — root_compound_id → set of family member compound_ids
  Built from KIND relations. Updated on store_batch and refine_definition.
  Used by SYMBOL's family enrichment cascade and by THINK for KIND chain traversal.
- `_relation_index: dict[tuple[str, int], set[int]]` — (predicate, target_id) → set of compound_ids
  Generalised relation index backing the by_relation() API.

Indexes rebuilt by maintenance thread on startup and after bulk writes.

---

### D5. Spreading Activation

```python
def associative(
    self,
    cues:        dict,   # {"primes": [...], "symbol": "..."}
    spread_depth: int = 2,
    limit:        int = 10,
) -> list[int]:
    """
    Starting from seed compounds matching cues, traverse relations outward
    accumulating activation scores. Returns ranked compound IDs.
    Used by THINK for analogy and by WANT for goal discovery.
    """
```

---

### D6. Background Consolidation and Forgetting

Full implementation of consolidation thread:
- Strengthen frequently co-occurring relations in Definition Narratives
- Create summary sub-records for deeply nested compound graphs
- Update resolved prime masks

Full implementation of forgetting thread:
- Decrement confidence for compounds not accessed recently
- Prune relations below confidence threshold
- Flag compounds for archiving

---

### D7. SQLite Persistence Backend

Replace JSON files with SQLite (WAL mode) for:
- Atomic writes across all four stores
- Efficient partial updates (no full-file rewrite)
- Query support for cold-path retrieval without loading full store into memory