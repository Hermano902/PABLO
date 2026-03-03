# Triples — Architecture & Implementation

This document specifies the implementation contract for triples in PABLO.
The conceptual model — what a triple is, how triples form propositions, and
how propositions anchor to form narratives — lives in triple_concept.md.
Implement triples according to both.

---

## PHASE 1 — Implement Now

---

### 1. Triple Dataclass

```python
# core/triple.py
from dataclasses import dataclass, field
import time

@dataclass
class Triple:
    id:           int           # globally unique, assigned by KNOW
    source_id:    int           # compound ID of the source (compound_A)
    predicate:    str           # prime name — one of the 63 canonical primes
    target_id:    int           # compound ID of the target (compound_B)
                                # OR a prime name as terminal value (see below)
    target_prime: str | None    # set when target is a terminal prime, not a compound
                                # exactly one of target_id / target_prime is used
    confidence:   float = 1.0   # 0.0–1.0; 1.0 for definition triples, lower for inferred
    source:       str  = ""     # "definition" | "utterance" | "inferred" | "specialist"
    created_at:   float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "source_id":    self.source_id,
            "predicate":    self.predicate,
            "target_id":    self.target_id,
            "target_prime": self.target_prime,
            "confidence":   self.confidence,
            "source":       self.source,
            "created_at":   self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Triple":
        return cls(**d)
```

**Rule:** exactly one of `target_id` or `target_prime` is set per triple.
- `target_prime` is used when compound_B is a terminal prime value (e.g. BEFORE, NOW, MANY).
- `target_id` is used when compound_B is a real compound in KNOW.

```python
# Terminal prime examples:
Triple(source_id=RUN_ID,    predicate="WITH", target_id=None,   target_prime="NOW")
Triple(source_id=BITE_ID,   predicate="WITH", target_id=None,   target_prime="BEFORE")

# Compound-to-compound examples:
Triple(source_id=RUN_ID,    predicate="KIND", target_id=MOVE_ID, target_prime=None)
Triple(source_id=DOCTOR_ID, predicate="HAVE", target_id=TIRED_ID, target_prime=None)
```

---

### 2. Triple Storage in KNOW

Triples are stored in KNOW as a flat indexed store alongside compounds.

```python
# primes/KNOW.py — additions

# Triple store — one flat dict, indexed by source_id for fast activation cloud lookup
self._triples:          dict[int, Triple]               = {}   # triple_id → Triple
self._triple_index:     dict[int, list[int]]            = {}   # source_id → [triple_id, ...]
self._tri_lock          = threading.RLock()
self._next_triple_id:   int = 1
```

**Index:** `_triple_index` maps a source compound's ID to all its outgoing triples.
This is the primary access pattern — "give me all triples for compound X" — used by
the activation cloud when assembling definition compound context.

**Persistence:** triples are saved to `storage/triples.json` by the autosave thread.

---

### 3. Triple Store API

```python
def store_triple(
    self,
    source_id:    int,
    predicate:    str,
    target_id:    int | None,
    target_prime: str | None,
    confidence:   float = 1.0,
    source:       str = "definition",
) -> int:
    """
    Store one triple. Assigns permanent ID. Updates triple_index.
    Returns triple_id.
    Validates predicate is in PRIME_SET.
    Validates exactly one of target_id / target_prime is set.
    """
    assert predicate in PRIME_SET, f"Invalid predicate prime: {predicate}"
    assert (target_id is None) != (target_prime is None), \
        "Exactly one of target_id / target_prime must be set"

    with self._tri_lock:
        t = Triple(
            id=self._next_triple_id,
            source_id=source_id,
            predicate=predicate,
            target_id=target_id,
            target_prime=target_prime,
            confidence=confidence,
            source=source,
        )
        self._next_triple_id += 1
        self._triples[t.id] = t
        self._triple_index.setdefault(source_id, []).append(t.id)
    return t.id

def get_triples(self, source_id: int) -> list[Triple]:
    """Return all outgoing triples for a compound. O(1) index lookup."""
    with self._tri_lock:
        ids = self._triple_index.get(source_id, [])
        return [self._triples[i] for i in ids if i in self._triples]

def get_triple(self, triple_id: int) -> Triple | None:
    with self._tri_lock:
        return self._triples.get(triple_id)

def get_triples_by_predicate(self, source_id: int, predicate: str) -> list[Triple]:
    """Filter outgoing triples by predicate. Used in activation cloud."""
    return [t for t in self.get_triples(source_id) if t.predicate == predicate]
```

---

### 4. Definition Narratives as Triple Sets

A compound's Definition Narrative IS a set of triples. When a compound is created
by DATA and stored via `store_batch()`, KNOW creates an empty Definition Narrative
and an empty triple set for it. SYMBOL enriches these over time.

**Integration with Definition Narrative:**

The Definition Narrative's `relations` list (list of dicts) is the human-readable
mirror of the triple store. The triple store is the machine-queryable form.
Both are populated together when `refine_definition()` is called:

```python
def refine_definition(
    self,
    compound_id:   int,
    triples:       list[dict] | None = None,   # NEW — list of triple specs
    new_relations: list[Relation] | None = None,
    ...
) -> bool:
    """
    When triples are provided, store each as a Triple record AND
    record in the Definition Narrative thread.

    Triple spec format:
      {"predicate": "KIND", "target_id": 205, "target_prime": null, "confidence": 0.95}
    OR
      {"predicate": "WITH", "target_id": null, "target_prime": "BEFORE", "confidence": 1.0}
    """
    ...
    if triples:
        for spec in triples:
            self.store_triple(
                source_id=compound_id,
                predicate=spec["predicate"],
                target_id=spec.get("target_id"),
                target_prime=spec.get("target_prime"),
                confidence=spec.get("confidence", 1.0),
                source="definition",
            )
```

---

### 5. Utterance Triples

When DATA creates a Layer 1 utterance compound, it also calls KNOW to store the
relational triples extracted from the utterance (once triple extraction from SYMBOL
is implemented). Until then, utterance triples are deferred.

**Phase 1 current behavior:** utterance compounds store ordered `nested` concept IDs
(flat list, no relational structure). Triple extraction from utterances is Phase 1.5
— requires the DeepSeek triple extractor (see specialists.py).

**Phase 1.5 behavior (after DeepSeek extractor):**

```python
# DATA creates utterance compound, then:
for triple_spec in candidate.get("triples", []):
    know.store_triple(
        source_id=resolved_compound_id_for(triple_spec["source"]),
        predicate=triple_spec["predicate"],
        target_id=resolved_compound_id_for(triple_spec["target"]) if triple_spec.get("target_compound") else None,
        target_prime=triple_spec.get("target_prime"),
        confidence=triple_spec.get("confidence", 0.8),
        source="utterance",
    )
```

---

### 6. Serialization

Triples are serialized as a flat list in `storage/triples.json`:

```json
[
  {
    "id": 1,
    "source_id": 205,
    "predicate": "KIND",
    "target_id": 206,
    "target_prime": null,
    "confidence": 1.0,
    "source": "definition",
    "created_at": 1772562097.0
  },
  {
    "id": 2,
    "source_id": 205,
    "predicate": "WITH",
    "target_id": null,
    "target_prime": "BEFORE",
    "confidence": 1.0,
    "source": "definition",
    "created_at": 1772562097.0
  }
]
```

**Load from disk (in `_load_from_disk`):**

```python
if os.path.exists("storage/triples.json"):
    with open("storage/triples.json") as f:
        data = json.load(f)
    for raw in data:
        t = Triple.from_dict(raw)
        self._triples[t.id] = t
        self._triple_index.setdefault(t.source_id, []).append(t.id)
    if data:
        self._next_triple_id = max(t["id"] for t in data) + 1
```

**Save in `_save_to_disk`:**

```python
with self._tri_lock:
    triples_snapshot = [t.to_dict() for t in self._triples.values()]
with open("storage/triples.json", "w") as f:
    json.dump(triples_snapshot, f)
```

---

### 7. Compute Tier

Triples are Tier 2 (CPU sequential). All operations are dict lookups and list
appends — no bitwise operations, no GPU involvement.

```
TIER 1 — CPU BITWISE   nanoseconds    PrimeBit AND/OR/POPCOUNT
TIER 2 — CPU SEQUENTIAL microseconds  Triple store/retrieve — dict access, list append
TIER 3 — GPU PARALLEL   milliseconds  Compound similarity matrix (Phase 2)
```

Triple operations never touch Tier 1 (no primebit ops on triple storage).
Triple operations never need Tier 3 (no matrix ops on triple records).

---

### 8. ID Space

```
Compound IDs:      0–99 reserved, 100–199 logic, 200+ runtime
Triple IDs:        separate counter, starts at 1
Definition IDs:    separate counter, starts at 1
Narrative IDs:     separate counter, starts at 1
```

Triple IDs have no overlap with any other ID space. The counter is stored
in `storage/metadata.json`:

```json
{
  "next_id":        421,
  "next_def_id":    222,
  "next_nar_id":    5,
  "next_triple_id": 847,
  "saved_at":       1772562097.0
}
```

---

### 9. Statistics Additions

```python
self.stats["triples_stored"]    = 0
self.stats["triples_retrieved"] = 0
```

---

### 10. Phase 1 Scope

```
✅ Triple dataclass (source_id, predicate, target_id | target_prime, confidence, source)
✅ Triple store in KNOW (_triples dict + _triple_index by source_id)
✅ store_triple() — validates predicate, assigns ID, updates index
✅ get_triples(source_id) — O(1) index lookup
✅ get_triples_by_predicate(source_id, predicate) — filtered lookup
✅ Integration with refine_definition() — triples stored alongside narrative thread
✅ Serialization to storage/triples.json
✅ Load from disk on startup
✅ next_triple_id persisted in metadata.json

❌ Utterance triple extraction (Phase 1.5 — requires DeepSeek extractor in specialists.py)
❌ Proposition grouping (Phase 2 — see proposition_architecture.md)
❌ Narrative anchoring triples (THIS + TIME + SPACE) (Phase 2)
❌ Triple-based constraint encoding (Phase 2)
❌ Inferred triples from spreading activation (Phase 3)
❌ Triple index by predicate (Phase 2 — currently filter on source_id results)
❌ Triple index by target (Phase 2 — reverse index for graph traversal)
```

---

## PHASE 2+ — Deferred

### D1. Proposition Store

After triples are stored, group them into Proposition records.
See proposition_architecture.md.

### D2. Predicate + Reverse Indexes

```python
self._pred_index:   dict[str, list[int]]          = {}   # predicate → [triple_id]
self._target_index: dict[int, list[int]]           = {}   # target_id → [triple_id]
```

Enables reverse traversal: "all compounds that DO something" or
"all compounds with a KIND relation to run".

### D3. Triple Confidence Decay

Active confidence decay for inferred triples (source="inferred"):
```
active_confidence = base_confidence * (0.5)^(days_since_reinforcement / half_life)
```
Default half_life for inferred triples: 14 days.
Definition triples never decay — they are universal truths.

### D4. Narrative Anchoring Triples

Triples for instance propositions (narrative events):
```python
Triple(source_id=THIS_DOCTOR_ID, predicate="BE",   target_id=DOCTOR_ID, source="utterance")
Triple(source_id=THIS_DOCTOR_ID, predicate="AT",   target_id=HOSPITAL_ID, source="utterance")
Triple(source_id=THIS_DOCTOR_ID, predicate="WITH", target_prime="BEFORE", source="utterance")
```
These use THIS-anchored compound IDs — narrative-local compound references.
