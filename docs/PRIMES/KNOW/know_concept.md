# KNOW — Concept

*PABLO's memory. The persistent store of crystallised thought.*

---

## Nature

KNOW is sensitive to **Compounds ready to be stored** and to **scene contexts that
could be enriched by surfacing related memories**. It is not a pipeline stage — it is
a service that the rest of the system reads from and writes to.

KNOW is where crystallisation becomes permanent. Everything DATA crystallises, KNOW
preserves. Everything THINK reasons about, KNOW supplies. Everything SAY expresses,
KNOW records (via Narrative update).

---

## What KNOW Stores

**Compounds** — the primary store. Every crystallised thought has a permanent ID,
a PrimeBit encoding, and lives in KNOW. Indexed by ID, symbol, and PrimeBit for
fast retrieval.

**Definition Narratives** — one per Compound. The accumulating record of how PABLO
has understood this concept across all scenes. Updated by DATA on first creation and
enriched over time.

**Instance Narratives** — contextual memory threads. A Narrative for THIS_USER tracks
the relationship history with the user. A Narrative for a topic tracks how PABLO's
understanding of that topic has evolved. These are what SELF reads for salience
computation and THINK walks for reasoning.

**Triples** — relational assertions between Compounds. `(subject) -[predicate]→ (object)`.
The relational fabric of PABLO's knowledge. Phase 4+.

**Refinement records** — per-Compound metadata tracking how many times it has been
accessed, updated, and confirmed.

---

## How KNOW Is Accessed

**store_batch(compounds)** — DATA's primary write path. Assigns permanent IDs,
indexes by symbol and PrimeBit, creates Definition Narratives for new concepts.

**by_id(id)** — fetch any Compound by its permanent ID.

**by_symbol(symbol)** — O(1) lookup for Compounds by their surface symbol.
Only concept-type Compounds are in the symbol index (utterances are not).

**by_prime(prime_name)** — all Compounds whose PrimeBit includes a given prime.

**by_primebit_intersection(bits)** — cued recall by prime resonance. Returns Compounds
whose PrimeBit overlaps with the query bits. This is how KNOW surfaces related memories:
not full-text search, but resonance between prime patterns.

**narrative_by_source(source)** — the active Narrative for a given source entity.
SELF reads this for salience computation.

---

## KNOW and the Scene

In the current architecture, KNOW's role in the scene is indirect:
- DATA calls `store_batch()` and writes the results to the scene's memory layer
- SELF reads Narratives from KNOW to compute salience
- THINK reads Compounds from KNOW to reason

In future phases, KNOW will contribute directly to the scene's memory layer —
surfacing active narratives, priming the scene with related concepts before SELF
even evaluates salience. This is cued recall: the scene activates KNOW's memory,
and KNOW responds with what it finds resonant.

---

## Memory Tiers

KNOW provides three memory tiers, accessible within a scene:

| Tier | Content | Access |
|------|---------|--------|
| Working | scene.concept_ids — Compounds in this utterance | scene.memory layer |
| Short-term | Recently active Narratives (last N scenes) | KNOW in-memory cache |
| Long-term | All Compounds + Definition Narratives on disk | KNOW full store |

---

## Persistence

KNOW loads from disk once at startup and saves periodically. The storage format is JSON
(compounds.json, definitions.json, narratives.json, triples.json, metadata.json).

KNOW's in-memory LRU cache (max 1000 entries) provides fast access for recently used
Compounds without full store traversal.

---

## What KNOW Does NOT Do

KNOW does not interpret input. That is SYMBOL.
KNOW does not create utterance Compounds. That is DATA.
KNOW does not gate attention. That is SELF.
KNOW does not form responses. That is THINK.
KNOW does not know about the CognitiveScene — it is a storage service, not a scene
participant. Primes that use KNOW read the scene; KNOW does not.

---

*See `docs/COMPOUND/compound_concept.md` for what KNOW stores.*
*See `docs/NARRATIVES/narratives_concept.md` for Narrative structure.*
*See `docs/TRIPLES/triple_concept.md` for relational storage.*
