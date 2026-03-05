# DATA — Concept

*PABLO's structuring prime. The crystalliser.*

---

## Nature

DATA is sensitive to **token interpretations present in the scene that need validation
and compound assembly**. When SYMBOL has resolved tokens to primes, DATA takes those
resolutions and crystallises them — creating or retrieving the Compound objects that
will persist in KNOW.

DATA is where transient token resolutions become stable, reusable units of meaning.
It is the moment of crystallisation in the pipeline.

---

## What DATA Does

When the scene reaches `"memory"` stage, DATA:

1. **Reads** `scene.token_resolutions` from the symbol layer
2. **For each resolved token**, checks KNOW for an existing Compound with that symbol:
   - **Found** — reuses the existing Compound (concept recognised)
   - **Not found** — creates a new Compound (concept crystallised for the first time)
3. **Assembles the utterance Compound** — a Layer 1 Compound containing ordered references
   to all token Compounds; PrimeBit is the union of all token primebits
4. **Calls KNOW.store_batch()** — pushes new Compounds (concepts + utterance) to permanent
   storage; existing Compounds are referenced by ID only
5. **Writes the memory layer** of the scene:
   - `scene.utterance_id` — permanent ID of the utterance Compound
   - `scene.concept_ids` — IDs of all concept Compounds
   - `scene.known_symbols` — symbols found in KNOW (recognised)
   - `scene.new_symbols` — symbols crystallised new in this scene
   - `scene.stage = "attention"`
6. **Contributes to the SymbolicScene** — the assembled Compound set; Triples encoding
   positional relationships (AFTER, PART); Narrative fragments from surfaced memories.

---

## Crystallisation

DATA is where the theory becomes concrete. A token resolution from SYMBOL is unstable:
it exists in the scene's symbol layer as a dict — a transient cognitive event. DATA
encodes it in symbolic form (a Compound with a permanent ID, a PrimeBit, relations) and
writes it to KNOW. The thought is now stable, examinable, referenceable without
re-deriving.

When DATA finds the token in KNOW, it is recognising a crystallised thought from a
previous experience. The Compound already exists because this concept was crystallised
before. DATA does not re-crystallise it — it retrieves the stable form.

This is the difference between a mind encountering a concept for the first time and
recognising one it already knows.

---

## What DATA Does NOT Do

DATA does not interpret tokens. That is SYMBOL.
DATA does not decide what the utterance means. That is THINK.
DATA does not gate attention. That is SELF.
DATA does not call any prime directly — it calls KNOW as a storage service.

---

## Phase Scope

| Phase | Capability |
|-------|-----------|
| 1 | Concept Compound creation and reuse |
| 1 | Utterance Compound assembly |
| 1 | KNOW.store_batch() push |
| 1 | Memory layer written to scene |
| 2 | Definition Narrative creation for new concepts |
| 2 | Enrichment queue for unresolved placeholders |

---

*See `docs/SYSTEM/cognitive_scene.md` for the scene layer DATA writes.*
*See `docs/PRIMES/KNOW/know_concept.md` for the storage service DATA calls.*
*See `docs/COMPOUND/compound_concept.md` for the Compound DATA creates.*
