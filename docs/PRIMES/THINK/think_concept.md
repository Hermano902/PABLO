# THINK — Concept

*PABLO's conscious reasoning prime. The integrator.*

---

## Nature

THINK is sensitive to **scenes marked conscious by SELF** with an empty execution layer.
It is the only prime that operates with the full scene in view — perception, symbol,
memory, and relational layers all contributed before THINK engages.

THINK is not autonomous. It does not scan the environment or run continuously. THINK
engages when SELF decides an experience is worth conscious attention. Between those
moments, THINK is silent.

This mirrors conscious attention in the biological model: PABLO is not always "thinking
about" every observation. It thinks when the attention gate opens.

---

## What THINK Does

When the scene reaches `"execution"` stage, THINK:

1. **Reads the full scene** — all layers contributed by READ, SYMBOL, DATA/KNOW, SELF
2. **Identifies the Narrative context** — open Narrative for this source from KNOW, or
   creates a new one
3. **Resolves scene compounds to Narrative bindings** — known entities map to existing
   bindings; new entities create new bindings
4. **Analyses the prime field** — which primes dominate this experience, in what combination
5. **Selects a reasoning mode** from the prime field pattern:

   | Prime pattern | Reasoning mode |
   |---------------|----------------|
   | KNOW + BE | `knowledge_query` |
   | SAY + YOU | `directed_message` |
   | DO + (MOVE\|MAKE\|CHANGE) | `action_request` |
   | WANT + (any) | `preference_expression` |
   | NEED + (any) | `requirement_expression` |
   | THINK + SELF | `introspective_query` |
   | (no match) | `reflective_acknowledgement` |

6. **Reasons** within the scene context — queries KNOW for relevant compounds, integrates
   with Narrative history, forms a response
7. **Writes the execution layer** of the scene:
   - `scene.reasoning_mode`
   - `scene.intent_id` — ID of the Intent Compound written to KNOW
   - `scene.response_text` — the formed response
   - `scene.stage = "output"`
8. **Contributes to the SymbolicScene** — a chain of Triples representing the reasoning
   path; an Intent Compound; a Narrative fragment in prime-space representing what PABLO
   understood and intends to say.

---

## What THINK Writes to KNOW

THINK is a KNOW writer as well as a KNOW reader.

**Intent Compound** — one per conscious thought cycle. Records what THINK understood
from this experience. This is PABLO's symbolic record of comprehension.

**Action Compounds** (Phase 2+) — when THINK learns a new executable action pattern.

**Macro Compounds** (Phase 2+) — when an action pattern is executed 3+ times
successfully, bundled into a reusable compound.

The Intent Compound is the crystallised output of the reasoning cycle — a stable,
examinable object that can be retrieved, refined, and built upon in later scenes.

---

## THINK's Reasoning IS the Crystallisation Loop

THINK is where the crystallisation loop from the theory runs most explicitly:

1. THINK receives a scene with all prior contributions (the "pre-linguistic" state,
   already symbolised by SYMBOL and stored by KNOW)
2. THINK forms an Intent Compound — crystallising the understanding
3. THINK forms a response — externalising the crystallised thought
4. SAY expresses the response — the externalised form enters the world
5. Future scenes referencing the same concepts can compare against the stored Intent
6. Refinement happens as THINK's understanding deepens through repeated experience

What distinguishes PABLO from an LLM: THINK forms the Intent Compound from Pablo's
own symbolic representation of the experience — not from pattern-matched text. The
crystallisation substrate is PABLO's prime vocabulary, not token frequencies.

---

## What THINK Does NOT Do

THINK does not receive raw observations. Those are READ → SYMBOL → DATA.
THINK does not call SYMBOL. By the time THINK engages, interpretation is complete.
THINK does not call any other prime directly.
THINK does not call any GUI function. SAY handles output.
THINK does not contain language models for reasoning. Reasoning is symbolic, over
prime-grounded Compounds. LLMs may be consulted for response phrasing (Phase 2+).

---

## Phase Scope

| Phase | Capability |
|-------|-----------|
| 1 | Reads full scene; prime field analysis; 7-mode routing table |
| 1 | Intent Compound written to KNOW each cycle |
| 1 | Response text formed and written to scene execution layer |
| 2 | Action Compound execution |
| 2 | Macro Compound creation (3+ successful executions) |
| 2 | KNOW.by_trigger() lookup for macro matching |
| 3 | LLM-assisted response phrasing |

Phase 1 THINK is a valid and complete implementation of conscious reasoning: it reads
the full scene, understands the prime pattern, forms an intent, and produces a response.
The quality of reasoning grows as KNOW accumulates more compounds and Narratives deepen.

---

*See `docs/SYSTEM/cognitive_scene.md` for the scene THINK reads and writes.*
*See `docs/PRIMES/SELF/self_concept.md` for the attention gate that activates THINK.*
*See `docs/PRIMES/KNOW/know_concept.md` for what THINK reads from and writes to.*
