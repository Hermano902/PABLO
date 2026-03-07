# Storage Sharding — Design Patch

*Status: design only — not yet implemented. Merge into compound.md, know.md, and a new storage.md when ready.*

---

## Motivation

Current storage is flat JSON. Every compound record carries all its fields regardless of
whether reasoning needs them. At 10k+ compounds this means loading definition text,
refinement history, execution slots, and timestamps into memory even when PABLO only
needs to answer "is this the right compound?" — a question answerable from seven fields.

The redesign splits compound data into purpose-built layers. Reasoning never touches
content it doesn't need.

---

## Core principle: hot record = identity + routing signals only

The hot record is what PABLO holds in working memory during a reasoning cycle.
It must answer two questions instantly:

1. Is this the right compound? (primebit match, depth, grounded state)
2. Where is its meaning? (narrative_id pointer)

It never contains lists, nested content, or prose.

```json
{
  "id": 847,
  "symbol": "run/race",
  "primebit": 12345,
  "compound_type": "concept",
  "depth": 3,
  "grounded": true,
  "narrative_id": 847
}
```

Seven fields. Thousands fit in memory with negligible footprint.

---

## Depth

`depth` is a new field computed once at import time. It measures how many grounding
hops separate a compound from pure prime meaning.

- **depth 0** — all triple nodes are primes or slot words (THIS, SOMEONE, SOMETHING,
  SOMEWHERE). Fully grounded. Directly executable.
- **depth 1** — has one unresolved node; that node is depth 0.
- **depth N** — N hops to reach all-prime meaning.

Depth is computed by walking `nested_words` recursively at import time. It never
changes after import unless the compound is re-enriched.

Common words (run, see, feel, want) are typically depth 1-3.
Abstract or rare words tend toward depth 4+.

---

## Consolidated compounds (future)

A compound may eventually accumulate enough relational mass — enough triple coverage,
enough narrative appearances, enough consistent primebit — that it no longer needs
to be decomposed to primes during reasoning. It functions as an atom.

This is consolidation. A consolidated compound is promoted to depth 0* and sits
alongside primes in working memory. It is not a prime — it is a learned primitive
specific to PABLO's experience.

Implementation: `compound_type = "consolidated"`. Promotion trigger TBD (usage count
threshold, connection density, or explicit decision by THINK).

The 63 primes are the universal seed. Consolidated compounds are the personalised,
domain-adapted layer that grows on top through use.

*Not implemented. Architecture must reserve a slot for depth 0* in the hot shard.*

---

## Storage layout

```
storage/
│
├── meta.json                        # global ID counters + shard config
│
├── index/
│   ├── primebit.json                # prime → {depth → [compound_id, ...]}
│   ├── symbol.json                  # symbol string → compound_id
│   └── headword.json                # headword → [compound_id, ...]
│
├── compounds/
│   ├── hot/
│   │   ├── depth_0.json             # primes + consolidated — always in memory
│   │   ├── depth_1.json             # always in memory
│   │   ├── depth_2.json             # always in memory
│   │   ├── depth_3.json             # always in memory
│   │   └── depth_4plus.json         # lazy loaded per scene
│   │
│   ├── definition/
│   │   ├── def_0_999.json           # definition text + relations, sharded by ID
│   │   └── def_1000_1999.json
│   │
│   ├── execution/
│   │   └── exec_all.json            # action/macro only — tiny, loaded on demand
│   │
│   └── refinement/
│       ├── ref_0_999.json           # version, confidence, source, created_at
│       └── ref_1000_1999.json
│
├── triples/
│   ├── tri_0_9999.json              # actual s/p/o content, sharded by ID
│   └── tri_10000_19999.json
│
└── narratives/
    ├── nar_0_999.json               # situational event sequences, sharded by ID
    └── nar_1000_1999.json
```

---

## Compound field assignment

### Hot shard (`compounds/hot/`)

| Field | Purpose |
|---|---|
| `id` | permanent identity |
| `symbol` | human-language handle |
| `primebit` | fast prime index — bitmask |
| `compound_type` | concept / utterance / intent / action / macro / consolidated |
| `depth` | grounding hops from prime ground |
| `grounded` | True = all nodes bottom out at primes |
| `narrative_id` | pointer to definition shard |

### Definition shard (`compounds/definition/`)

| Field | Purpose |
|---|---|
| `id` | compound ID (join key) |
| `definition` | plain-language definition string |
| `relations` | predicate → target links (Phase 1 bridge to triples) |

### Execution shard (`compounds/execution/`)

| Field | Purpose |
|---|---|
| `id` | compound ID (join key) |
| `executable` | bool |
| `trigger_condition` | primebit pattern that fires this compound |
| `arity` | argument count |
| `slots` | named argument slots |

### Refinement shard (`compounds/refinement/`)

| Field | Purpose |
|---|---|
| `id` | compound ID (join key) |
| `version` | incremented on each update |
| `confidence` | 0.0–1.0 certainty of primebit encoding |
| `source` | which prime/process created this |
| `created_at` | unix timestamp |

---

## Primebit index structure

The index supports both cued recall (which compounds match this prime set?) and
depth-ordered traversal (shallowest match first).

```json
{
  "MOVE": {
    "0": [1, 2, 3],
    "1": [215, 847, 1042],
    "2": [3301, 4421],
    "3": [9002]
  },
  "DO": {
    "0": [4, 5],
    "1": [200, 201, 889]
  }
}
```

Depth is nested inside each prime bucket so intersection at a target depth level is
possible before falling back to deeper candidates.

---

## Memory contract at runtime

| Shard | Loaded at startup | Loaded when |
|---|---|---|
| `hot/depth_0` through `depth_3` | always | startup |
| `hot/depth_4plus` | no | compound referenced in active scene |
| `definition/` | no | THINK needs to reason about a compound's meaning |
| `execution/` | no | compound triggered as action |
| `refinement/` | no | Dev panel / refinement cycle only |
| `index/` | always | startup |
| `triples/` | no | definition or narrative accessed |
| `narratives/` | no | narrative accessed |

PABLO reasons entirely from the hot shard during normal comprehension.

---

## Reasoning path (cued recall)

```
CognitiveScene activates primes [MOVE, DO, BODY]
  → primebit_index: intersect MOVE ∩ DO ∩ BODY, depth 0 first
  → hot shard: candidates ranked by depth ascending
  → pick best match: id=847, symbol="run/race", depth=3
  → need meaning? fetch narrative_id=847 from definition/
  → need triples? fetch triple_ids [1042, 1043, 1044] from triples/
```

Three layers. Each only fetched if the previous wasn't enough to resolve the scene.

---

## meta.json

```json
{
  "next_id": 10590,
  "next_def_id": 10391,
  "next_nar_id": 10391,
  "next_triple_id": 136821,
  "working_memory_depth": 3,
  "shards": {
    "triples_per_file": 10000,
    "defs_per_file": 1000,
    "nars_per_file": 1000,
    "refs_per_file": 1000
  },
  "consolidation_threshold": null
}
```

`working_memory_depth` controls which depth levels are loaded at startup.
Increasing it expands working vocabulary at the cost of memory.
`consolidation_threshold` is reserved for future use.

---

## Files to update when implementing

- `core/compound.py` — add `depth` field, remove fields moved to other shards
- `utils/import_enriched.py` — compute depth, write to sharded files, build indexes
- `primes/KNOW.py` — load sharded hot files at startup, lazy-load others by ID
- `docs/PLANGUAGE/compound.md` — merge hot/definition/execution/refinement split
- `docs/PRIMES/know.md` — merge memory contract and cued recall path
- Create `docs/SYSTEM/storage.md` — canonical storage layout reference

---

*This patch supersedes the flat storage design. Do not implement the flat design.*
