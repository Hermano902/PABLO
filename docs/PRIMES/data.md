# DATA

---

## Concept

DATA is the integrity auditor. It watches the stage for compound resolutions that have
been placed there by KNOW and checks whether they are structurally coherent.

DATA's question is not *what does this mean?* (KNOW) and not *what should I do with it?*
(THINK). DATA's question is:

> *Is every prime in this Compound's definition actually connected to something?*

A prime that appears in a Compound's primebit but has no relation to any other prime
within that definition is an orphan. It was assigned but never grounded. DATA finds
these, flags them, and reports back to the scene — advisory, never blocking. The
performance continues regardless.

DATA never interprets. It never assigns primes. It never calls another prime.
It reads the scene, checks structure, and writes its findings.

---

### The definition graph check

For every new Compound that KNOW has placed in the scene's memory layer, DATA checks:

> *Does every prime in `primebit` have at least one `Relation` pointing to another
> prime or Compound within this definition?*

A Compound is **resolved** when all primes are connected — `grounded = True`.
A Compound is **unresolved** when orphan primes exist — `grounded = False`, stored
with lower confidence, flagged for future enrichment.

This is advisory. Unresolved Compounds are already in KNOW by the time DATA flags them.
DATA does not prevent storage. It annotates quality.

---

### What DATA does not do

DATA does not look up tokens in compound storage. That is KNOW.
DATA does not interpret tokens or assign primes. That is KNOW and SYMBOL.
DATA does not decide what an utterance means. That is THINK.
DATA does not gate attention. That is SELF.
DATA does not call any other prime directly. It writes to the scene only.

---

## Architecture

### When DATA engages

DATA is sensitive to scenes where KNOW has written `token_resolutions` and
`concept_ids` but `validation_flags` is still empty. KNOW steps off the stage;
DATA steps on.

### Validation steps

1. **Read** `scene.concept_ids` — the permanent Compound IDs KNOW resolved
2. **For each new Compound** (those in `scene.new_symbols`):
   - Check that each prime in `primebit` has ≥1 `Relation` in `relations`
   - Collect orphan prime names
   - Write entry to `validation_flags`
3. **Skip existing Compounds** (those in `scene.known_symbols`) — already validated
   in a prior scene; DATA trusts KNOW's index

### Scene writes

```
scene.validation_flags   dict   {compound_id: {valid: bool, orphan_primes: list[str]}}
```

That is DATA's entire contribution to the MetaScene. One field. No storage calls.
No compound creation. No prime assignment.

### SymbolicScene contribution

DATA contributes positional Triples between the resolved concepts — encoding word order
as AFTER relations — and a structural integrity marker:

```
(concept_A) -[AFTER]→ (concept_B)   for each adjacent pair in concept_ids
```

### Validation is advisory

`validation_flags` is written to the scene but does not block any other prime.
SELF, THINK, and KNOW can all read the flags and weight their behaviour — but nothing
stops the scene from progressing. An unresolved Compound is a known gap, not a failure.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Definition graph check (orphan prime detection) |
| 1 | `validation_flags` written to scene (advisory) |
| 2 | Definition Narrative enrichment — logging orphan primes for future resolution |
| 2 | Enrichment queue: unresolved Compounds queued for LLM specialist |

---

*See [cognitive_scene.md](../../SYSTEM/cognitive_scene.md) for the scene layers DATA reads and writes.*
*See [know.md](know.md) for what KNOW produces that DATA validates.*
*See [compound.md](../PLANGUAGE/compound.md) for the Compound graph structure DATA checks.*
