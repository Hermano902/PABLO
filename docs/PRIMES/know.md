# KNOW

---

## Concept

KNOW is PABLO's memory prime. It owns everything that persists beyond a single scene —
Compounds, Triples, Narratives, Definition Narratives — and it is responsible for
surfacing the right memories into active scenes and for resolving surface tokens into
the Compounds they represent.

KNOW enters the stage when SYMBOL has classified the signal and deposited surface tokens.
It picks up those tokens, searches its compound store, resolves each one to a Compound,
and writes the full semantic picture back to the scene for other primes to use.

KNOW is a full prime — a scene participant with its own sensitivity and contribution.
It is not a passive storage service called by other primes. It perceives scene
conditions and contributes accordingly.

---

### Two entries, one actor

KNOW engages at two distinct moments in a scene:

**1. Semantic resolution** — when SYMBOL has deposited `preliminary_tokens` and script
classification but no `token_resolutions` exist yet. KNOW looks up each token, resolves
it to a Compound (or creates a placeholder), and writes the memory layer.

**2. Cued recall** — once `prime_field_bits` is populated, KNOW searches its store for
Compounds and Narratives whose PrimeBit resonates with the scene's prime field. It
surfaces what is conceptually adjacent to what the scene is already about, enriching
the memory layer with relevant prior knowledge.

Both entries are autonomous — KNOW watches the scene, recognises its cues, acts.

---

### Memory tiers

KNOW manages three tiers of memory, all accessible within a scene:

| Tier | Content | Access pattern |
|------|---------|---------------|
| Working | Compounds in this scene's utterance (`concept_ids`) | Scene memory layer — immediate |
| Short-term | Recently active Narratives (last N scenes) | KNOW in-memory cache — fast |
| Long-term | All Compounds + Definition Narratives on disk | Full store — slower, complete |

The tiers are not isolated. Cued recall draws from all three: working memory has highest
salience, short-term provides recent context, long-term provides the full conceptual store.

---

### What KNOW stores

**Compounds** — the primary store. Every crystallised meaning lives in KNOW with a
permanent ID, indexed by ID, symbol, and PrimeBit for fast retrieval.

**Definition Narratives** — one per Compound. The audit trail of how the Compound's
definition graph became resolved across scenes. Not on the hot path.

**Instance Narratives** — contextual memory threads tied to specific entities and
relationships. `THIS_USER` tracks the relational history with the primary user.
Carry entity bindings, an ordered Triple thread, and relational state. Read by SELF
for salience computation.

**Triples** — relational assertions between Compounds. Written by DATA (structural),
THINK (reasoned), and SAY (expressed).

---

### What KNOW does not do

KNOW does not classify signal script or language. That is SYMBOL.
KNOW does not validate Compound graph structure. That is DATA.
KNOW does not gate attention. That is SELF.
KNOW does not form responses. That is THINK.
KNOW never calls another prime. Its contribution is always to the scene.

---

## Architecture

### When KNOW engages

**Entry condition 1 (resolution):** scene has `preliminary_tokens` set AND
`token_resolutions` is empty.

**Entry condition 2 (cued recall):** scene has `prime_field_bits > 0` AND
`active_narratives` is empty.

### Token resolution (entry 1)

For each token in `scene.preliminary_tokens`:

```
token
  ├── exact symbol match in compound store    → existing Compound, score 1.0
  ├── lemma match (spaCy)                     → existing Compound, score 0.9
  ├── phonetic/variant match (Phase 2)        → existing Compound, score 0.7
  └── no match                               → placeholder Compound, score 0.0
                                               (flagged for enrichment)
```

After resolution, KNOW assembles the utterance Compound (ordered sequence of concept
IDs, union primebit) and stores it.

### Scene writes (resolution)

```
scene.token_resolutions   list[dict]   per-token: {token, compound_id, symbol, score, method}
scene.prime_field         dict         {prime_name: max_score} across all resolved Compounds
scene.prime_field_bits    int          union PrimeBit of all resolved Compounds
scene.unresolved_tokens   list[str]    tokens with no compound match
scene.utterance_id        int | None   permanent ID of the assembled utterance Compound
scene.concept_ids         list[int]    permanent IDs of per-token concept Compounds
scene.known_symbols       list[str]    tokens matched to existing Compounds
scene.new_symbols         list[str]    tokens that required new placeholder Compounds
```

### Cued recall (entry 2)

`by_primebit_intersection(scene.prime_field_bits, top_k=10)` — returns Compounds
whose PrimeBit has the most overlap with the scene's prime field (popcount of
`scene_bits & compound_bits`). KNOW writes matching Narrative IDs to `active_narratives`.

### API

```python
# Write paths
store(compound: Compound) -> int                        # returns permanent ID
store_batch(compounds: list[Compound]) -> list[int]

# Read paths — O(1)
by_id(id: int) -> Compound | None
by_symbol(symbol: str) -> Compound | None               # concept index only

# Read paths — set operations on PrimeBit
by_prime(prime_name: str) -> list[Compound]
by_primebit_intersection(bits: int, top_k: int = 10) -> list[Compound]

# Narrative access
narrative_by_source(source: str) -> Narrative | None
definition_narrative(compound_id: int) -> DefinitionNarrative | None
```

### Persistence

KNOW loads from disk once at startup. Format: JSON files per store.
`reload_from_disk()` saves current state, clears in-memory stores, and reloads —
used after external processes (e.g. dict_parser bootstrapping) have written to storage.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Token → Compound resolution (exact + lemma match) |
| 1 | Utterance Compound assembly + storage |
| 1 | `by_symbol()`, `by_id()`, `by_prime()` |
| 1 | `by_primebit_intersection()` — cued recall |
| 1 | `narrative_by_source()` — Instance Narrative for SELF |
| 2 | Definition Narrative creation and enrichment |
| 2 | Phonetic/variant matching |
| 2 | `reload_from_disk()` |
| N | Dictionary bootstrapping (46k+ entries from data/out/) |

---

*See [compound.md](../PLANGUAGE/compound.md) for what KNOW stores.*
*See [narratives.md](../PLANGUAGE/narratives.md) for Narrative structure.*
*See [triples.md](../PLANGUAGE/triples.md) for relational storage.*
*See [primebit.md](../SYSTEM/primebit.md) for the encoding layer underlying cued recall.*
*See [symbol.md](symbol.md) for what SYMBOL produces before KNOW acts.*
*See [data.md](data.md) for what DATA validates after KNOW acts.*
