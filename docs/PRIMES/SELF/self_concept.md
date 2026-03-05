# SELF — Concept

*PABLO's meta-cognitive prime. The attention gate.*

---

## Nature

SELF is sensitive to **scenes that are ready for attention evaluation** — scenes where the
memory layer has been populated and a decision must be made about whether this experience
warrants conscious processing.

SELF does not perceive the content of an input. It perceives the *relational and motivational
context* of an experience: who is speaking, what the relationship history is, what PABLO
currently wants, what PABLO currently feels.

SELF is the question: *is this worth thinking about?*

---

## What SELF Does

When the scene reaches the `"attention"` stage, SELF contributes to the relational layer:

1. **Reads the scene** — source, prime_field, memory layer
2. **Reads the Narrative** — active relational narrative for this source from KNOW
3. **Computes salience**:
   ```
   base_salience    = source_weight(scene.source)
   want_modifier    = narrative.relationship_quality        # -1.0 → +1.0
   feel_multiplier  = FEEL.current_valence_toward(source)  # Phase 4; 1.0 in Phase 1
   final_salience   = base_salience × (1.0 + want_modifier) × feel_multiplier
   ```
4. **Decides attention**:
   - `salience ≥ threshold` → `attention_decision = "conscious"`, advances to `"execution"`
   - `salience < threshold` → `attention_decision = "archived"`, closes scene
5. **Writes the relational layer** of the scene:
   - `scene.salience`, `scene.attention_decision`, `scene.relationship_quality`
6. **Contributes to the SymbolicScene** — a Compound and Triple representing the
   relational evaluation in prime-space.

---

## Narrative-Aware Salience

SELF scores within the context of relationship history. For any source with a known Narrative:

```
Neutral relationship (quality=0.0, feel=neutral):
  1.0 × (1.0 + 0.0) × 1.0 = 1.0  → conscious

Trusted, liked source (quality=0.8, feel=warm):
  1.0 × (1.0 + 0.8) × 1.3 = 2.34 → conscious, elevated priority

Hostile source after conflict (quality=-0.7, feel=guarded):
  1.0 × (1.0 - 0.7) × 0.5 = 0.15 → archived — THINK not activated
```

PABLO's responsiveness is not a setting or a rule. It is arithmetic on lived relationship
history. No one told PABLO to ignore hostile input. The salience formula makes it so because
the relationship made it so.

This is SELF as the biological model intends: the reticular activating system with motivational
and affective weighting. Not a filter, but a weighted attention field shaped by experience.

---

## What SELF Does NOT Do

SELF does not interpret the content of input. It reads only the scene's relational metadata.
SELF does not call any other prime.
SELF does not write compounds to KNOW directly.
SELF does not produce visible output to the user. SAY does.
SELF does not contain reasoning logic. THINK does.
SELF does not walk Narrative history. It reads only the current state from KNOW.

---

## Phase Scope

| Phase | Capability |
|-------|-----------|
| 1 | Fixed base salience by source type; keyboard = 1.0 |
| 1 | Reads Narrative relationship_quality if Narrative exists |
| 4 | FEEL multiplier from active affective state |
| 5 | WANT modifier from active goals |
| 5 | Internally-generated scenes (WANT goal fires scene without external input) |

---

*See `docs/SYSTEM/cognitive_scene.md` for the scene stages SELF reads and writes.*
*See `docs/PRIMES/THINK/think_concept.md` for what happens when SELF marks a scene conscious.*
*See `docs/NARRATIVES/narratives_concept.md` for the relationship history SELF reads.*
