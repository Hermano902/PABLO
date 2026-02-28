KNOW – Architecture

This document describes how KNOW is implemented. The conceptual contract lives in CONCEPT.md;
implement KNOW according to both.


1. Module and Singleton

KNOW lives in primes/KNOW.py and exports a singleton instance:

```python
# primes/KNOW.py
from core.prime_base import Prime

class KNOW(Prime):
    ...

know = KNOW()   # singleton exported at module level
```


2. Threading Model

KNOW runs two background threads, both started in `_on_initialize()`:

```
Main process
  └── KNOW input thread    (drains KNOW's internal input queue; writes to _store)
  └── KNOW autosave thread (periodic serialisation of _store to disk)
  └── caller threads       (retrieval: by_id, by_prime, etc. — synchronous, any thread)
```

The input thread and autosave thread share _store via a threading.RLock.
Retrieval calls run in the caller's thread and also acquire the lock.

KNOW never holds the lock across I/O. Disk writes operate on a snapshot of the store data
taken while holding the lock, then written after releasing it.


3. The Store

```python
self._store: dict[int, Compound | Narrative] = {}
self._lock = threading.RLock()
self._next_id: int = 200   # runtime IDs start at 200
```

IDs 0–99:    reserved (not populated in Phase 1)
IDs 100–199: logic compounds — loaded from core/logic_compounds.json at startup, read-only
IDs 200+:    runtime compounds assigned sequentially

Logic compounds are loaded in `_on_initialize()` before the input thread starts:

```python
def _load_logic_compounds(self):
    with open("core/logic_compounds.json") as f:
        entries = json.load(f)
    for entry in entries:
        c = Compound.from_dict(entry)
        self._store[c.id] = c   # IDs 100–199 pre-assigned in the JSON
```


4. Input Interface

DATA and THINK push to KNOW via its public store methods (not a queue — direct calls
protected by the lock):

```python
def store(self, compound: Compound) -> int:
    """Assign permanent ID, store, emit commit event. Returns assigned ID."""
    with self._lock:
        compound.id = self._next_id
        self._next_id += 1
        self._store[compound.id] = compound
    self._emit_commit_event(compound)
    return compound.id

def store_many(self, compounds: list[Compound]) -> list[int]:
    """Batch store. Assigns IDs in order. Returns list of assigned IDs."""
    ...
```

Temporary negative IDs from DATA are replaced by the permanent ID assigned here.
The caller's reference updates when KNOW returns the new ID.


5. Layer 1 Commit Event

When KNOW stores a Layer 1 (aggregate) Compound, it fires a commit event. This is the
mechanism by which SELF learns that a new utterance is ready:

```python
def _emit_commit_event(self, compound: Compound):
    if compound.compound_type == "aggregate":   # Layer 1
        for cb in self._layer1_listeners:
            cb(compound.id, compound.provenance.get("source", "unknown"))
```

SELF registers itself as a listener during `_on_initialize()`:

```python
# primes/SELF.py — during initialize
know.register_layer1_listener(self._on_utterance_committed)
```

No other component needs to poll KNOW for new utterances. The event fires once,
synchronously, in KNOW's input thread.


6. Narrative Storage

Narratives are stored in `_store` alongside Compounds under their own ID space:

```python
self._narrative_store: dict[int, Narrative] = {}
self._next_narrative_id: int = 1
```

Narrative IDs are separate from Compound IDs. The two ID spaces never overlap.

```python
def store_narrative(self, narrative: Narrative) -> int:
    with self._lock:
        narrative.id = self._next_narrative_id
        self._next_narrative_id += 1
        self._narrative_store[narrative.id] = narrative
    return narrative.id

def get_narrative(self, id: int) -> Narrative | None: ...
def open_narratives(self) -> list[Narrative]: ...
def narrative_by_source(self, source: str) -> Narrative | None: ...
def close_narrative(self, id: int): ...
def archive_narrative(self, id: int): ...
```


7. Retrieval Interface

All retrieval methods acquire `_lock` as a read (RLock allows concurrent readers):

```python
def by_id(self, id: int) -> Compound | None:
    with self._lock:
        return self._store.get(id)

def by_ids(self, ids: list[int]) -> list[Compound]:
    with self._lock:
        return [self._store[i] for i in ids if i in self._store]

def by_prime(self, prime_name: str) -> list[Compound]:
    with self._lock:
        return [c for c in self._store.values()
                if hasattr(c, "primebit") and c.primebit.has(prime_name)]

def by_text(self, token: str) -> list[Compound]:
    with self._lock:
        return [c for c in self._store.values() if c.text == token]

def by_type(self, compound_type: str) -> list[Compound]:
    with self._lock:
        return [c for c in self._store.values()
                if c.compound_type == compound_type]

def by_trigger(self, primebit) -> list[Compound]:
    """Return Action/Macro Compounds whose trigger_condition matches primebit."""
    with self._lock:
        return [c for c in self._store.values()
                if c.compound_type in ("action", "macro")
                and c.trigger_condition is not None
                and c.trigger_condition & primebit == c.trigger_condition]

def search(self, query: dict) -> list[Compound]:
    """Return Compounds matching all field conditions in query dict."""
    ...
```


8. Persistence

Autosave thread fires every `_autosave_interval` seconds (default 30):

```python
def _autosave_loop(self):
    while self._running:
        time.sleep(self._autosave_interval)
        self._save_to_disk()

def _save_to_disk(self):
    with self._lock:
        snapshot = {k: v.to_dict() for k, v in self._store.items()
                    if v.id >= 200}   # skip logic compounds (100–199)
        narratives = {k: v.to_dict() for k, v in self._narrative_store.items()}
        meta = {"next_id": self._next_id,
                "next_narrative_id": self._next_narrative_id,
                "saved_at": time.time()}
    # write outside lock
    with open("storage/compounds.json", "w") as f:
        json.dump(snapshot, f)
    with open("storage/narratives.json", "w") as f:
        json.dump(narratives, f)
    with open("storage/metadata.json", "w") as f:
        json.dump(meta, f)
```

On `_on_initialize()`, KNOW loads from disk first:

```python
def _load_from_disk(self):
    if os.path.exists("storage/compounds.json"):
        with open("storage/compounds.json") as f:
            data = json.load(f)
        for raw in data.values():
            c = Compound.from_dict(raw)
            self._store[c.id] = c
    if os.path.exists("storage/metadata.json"):
        with open("storage/metadata.json") as f:
            meta = json.load(f)
        self._next_id = meta.get("next_id", 200)
```

Logic compounds are always re-loaded from core/logic_compounds.json — never from
compounds.json. This prevents ID collision and ensures logic compounds are always correct.


9. Statistics

```python
self.stats = {
    "compounds_stored":     0,
    "compounds_retrieved":  0,
    "queries_processed":    0,
    "errors":               0,
    "loads_from_disk":      0,
    "saves_to_disk":        0,
}
```


10. Phase 1 Scope

  ✅ In-memory _store with RLock thread safety
  ✅ Sequential ID assignment (200+), logic compound loading (100–199)
  ✅ store() and store_many() with ID replacement
  ✅ Layer 1 commit event → SELF listener registration
  ✅ Narrative store with separate ID space
  ✅ Retrieval: by_id, by_ids, by_prime, by_text, by_type, by_trigger, search
  ✅ Autosave to storage/compounds.json + storage/narratives.json every 30s
  ✅ Load from disk on startup
  ✅ Statistics counters
  ❌ Compound indexing for fast by_prime / by_trigger (Phase 2 — Phase 1 uses linear scan)
  ❌ Narrative archiving / compression (Phase 2)
  ❌ Compound retirement / expiry (Phase 3)
