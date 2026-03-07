# SELF

---

## Concept

SELF is PABLO's attention gate. It is sensitive to scenes where the memory layer has
been populated and a decision must be made about whether this experience warrants
conscious processing.

SELF does not perceive the content of an input. It perceives the *relational context*
of an experience: who is speaking, what the relationship history says, and — in later
phases — what PABLO currently wants and feels.

SELF's question is: *is this worth thinking about?*

---

### Salience is arithmetic on relationship history

SELF computes salience from the source's Instance Narrative in KNOW. This is not a
filter rule or a setting. It is arithmetic on lived relationship history:

```
base_salience   = source_weight(scene.source)        # keyboard = 1.0 in Phase 1
want_modifier   = narrative.relationship_quality     # -1.0 → +1.0
feel_multiplier = FEEL.current_valence(source)       # Phase 4; 1.0 in Phase 1
final_salience  = base_salience × (1.0 + want_modifier) × feel_multiplier
```

Examples:

```
Neutral relationship (quality=0.0):
  1.0 × 1.0 × 1.0 = 1.0  → conscious

Trusted source (quality=0.8, feel=warm):
  1.0 × 1.8 × 1.3 = 2.34 → conscious, elevated priority

Hostile source (quality=-0.7, feel=guarded):
  1.0 × 0.3 × 0.5 = 0.15 → archived — THINK not activated
```

No one told PABLO to ignore hostile input. The formula made it so because the
relationship made it so. This is the reticular activating system with affective
weighting — not a filter, but a weighted attention field shaped by experience.

---

### What SELF does not do

SELF does not interpret the content of input. It reads only relational metadata.
SELF does not call any other prime.
SELF does not write Compounds to KNOW directly.
SELF does not produce visible output. That is SAY.
SELF does not reason about the input. That is THINK.
SELF does not walk Narrative history. It reads only the current relational state.

---

## Architecture

### When SELF engages

SELF is sensitive to the scene reaching `"attention"` stage — meaning the memory
layer (`utterance_id`, `concept_ids`, `active_narratives`) has been written by DATA
and KNOW, but the relational decision has not yet been made.

### Steps

1. Read scene: `source`, `prime_field`, memory layer
2. Read Instance Narrative for this source from KNOW (`narrative_by_source(source)`)
3. Compute salience using the formula above
4. Decide attention:
   - `salience ≥ threshold` → `attention_decision = "conscious"`, advance to `"execution"`
   - `salience < threshold` → `attention_decision = "archived"`, close scene
5. Write relational layer:

```
scene.salience              float   computed attention score
scene.attention_decision    str     "conscious" | "archived"
scene.relationship_quality  float   from narrative (-1.0 → +1.0)
scene.stage                 →  "execution" or "archived"
```

### SymbolicScene contribution

SELF contributes a Compound representing the relational evaluation and a Triple:

```
(source_compound) -[SELF]→ (salience_compound)
```

Over time, SELF will express the full attention decision in PLanguage without the
MetaScene scaffold.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Fixed base salience by source type; keyboard = 1.0 |
| 1 | Reads Narrative `relationship_quality` if Narrative exists |
| 4 | FEEL multiplier from active affective state |
| 5 | WANT modifier from active goals |
| 5 | Internally-generated scenes (WANT goal fires scene without external input) |

---

*See [cognitive_scene.md](../SYSTEM/cognitive_scene.md) for the scene stages SELF reads and writes.*
*See [think.md](think.md) for what happens when SELF marks a scene conscious.*
*See [narratives.md](../PLANGUAGE/narratives.md) for the Instance Narrative SELF reads.*
*See [know.md](know.md) for `narrative_by_source()` — the Narrative access path.*
