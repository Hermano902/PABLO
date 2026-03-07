# THINK

---

## Concept

THINK is PABLO's conscious reasoning prime. It is sensitive to scenes marked conscious
by SELF with an empty execution layer. It is the only prime that operates with the full
scene in view — perception, symbol, memory, and relational layers all contributed before
THINK engages.

THINK is not autonomous. It does not scan the environment or run continuously. It engages
when SELF decides an experience warrants conscious attention. Between those moments, THINK
is silent.

This mirrors conscious attention in the biological model: PABLO is not always "thinking
about" every observation. It thinks when the attention gate opens.

---

### THINK is the crystallisation loop made explicit

THINK is where the crystallisation loop from the theory runs most visibly:

1. THINK receives a scene with all prior contributions — the pre-linguistic state,
   already symbolised by SYMBOL, validated by DATA, stored by KNOW
2. THINK forms an Intent Compound — crystallising the understanding
3. THINK forms a response — externalising the crystallised thought
4. SAY expresses the response — the externalised form enters the world
5. Future scenes can compare against the stored Intent and refine

What distinguishes PABLO from an LLM: THINK forms the Intent Compound from PABLO's
own symbolic representation of the experience — not from pattern-matched text. The
crystallisation substrate is prime-space, not token frequencies.

---

### What THINK does not do

THINK does not receive raw observations. Those go READ → SYMBOL → DATA.
THINK does not call SYMBOL or DATA. Interpretation is complete before THINK engages.
THINK does not call any other prime directly.
THINK does not call GUI functions. SAY handles output.
THINK does not use language models for reasoning. Reasoning is symbolic, over
prime-grounded Compounds. LLMs may assist with response phrasing in Phase 3+.

---

## Architecture

### When THINK engages

THINK is sensitive to `scene.stage == "execution"` with `scene.intent_id == None`.
This condition is set by SELF when it decides the scene is conscious.

### Steps

1. Read the full scene — all layers
2. Load the Instance Narrative for this source from KNOW
3. Resolve scene Compounds to Narrative entity bindings
4. Analyse the prime field — which primes dominate, in what combination
5. Select reasoning mode from prime field pattern:

   | Prime pattern | Reasoning mode |
   |---------------|----------------|
   | KNOW + BE | `knowledge_query` |
   | SAY + YOU | `directed_message` |
   | DO + (MOVE\|MAKE\|CHANGE) | `action_request` |
   | WANT + (any) | `preference_expression` |
   | NEED + (any) | `requirement_expression` |
   | THINK + SELF | `introspective_query` |
   | (no match) | `reflective_acknowledgement` |

6. Reason within scene context — query KNOW for relevant Compounds, integrate
   Narrative history, form response
7. Write execution layer:

```
scene.reasoning_mode    str         selected reasoning mode
scene.intent_id         int         permanent ID of Intent Compound written to KNOW
scene.response_text     str         formed response text
scene.stage             →  "output"
```

### What THINK writes to KNOW

**Intent Compound** — one per conscious thought cycle. Type `"intent"`. Records what
THINK understood from this experience in prime-space. The crystallised output of the
reasoning cycle — stable, retrievable, refinable.

**Action Compounds** *(Phase 2+)* — when THINK learns a new executable action pattern.

**Macro Compounds** *(Phase 2+)* — when an action pattern is executed 3+ times
successfully, bundled into a reusable Compound. The fastest path through THINK.

### SymbolicScene contribution

THINK contributes a chain of Triples representing the reasoning path, the Intent
Compound, and a Narrative fragment — PABLO's native-language record of what it
understood and intends to express.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Full scene read; prime field analysis; 7-mode routing table |
| 1 | Intent Compound written to KNOW each cycle |
| 1 | Response text formed and written to scene execution layer |
| 2 | Action Compound execution via compound execution model |
| 2 | Macro Compound creation (3+ successful executions) |
| 3 | LLM-assisted response phrasing |

---

*See [cognitive_scene.md](../SYSTEM/cognitive_scene.md) for the scene THINK reads and writes.*
*See [self.md](self.md) for the attention gate that activates THINK.*
*See [know.md](know.md) for what THINK reads from and writes to.*
*See [planguage.md](../PLANGUAGE/planguage.md) for compound execution (action/macro Compounds).*
