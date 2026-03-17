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
2. THINK reads the neighborhood graph — proposition networks assembled concurrently
   by SYMBOL for every resolved token
3. THINK forms an Intent Compound — crystallising its understanding into prime-space
4. THINK forms a response — externalising the crystallised thought as language
5. SAY expresses the response — the externalised form enters the world
6. Future scenes can compare against the stored Intent and refine

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

## What THINK reads

When THINK engages, the scene contains:

```
scene.concept_ids           list[int]       resolved Compounds for each token
scene.prime_field           dict            {prime_name: max_score} — dominant primes
scene.prime_field_bits      int             union PrimeBit of all resolved Compounds
scene.neighborhoods         dict            cid → {compounds, triples, terminals}
scene.active_narratives     list[int]       Narratives surfaced by cued recall
scene.relationship_quality  float | None    relational state from THIS_USER Narrative
```

The neighborhoods field is THINK's primary input for meaning. Each entry is a
subgraph centered on one resolved token, produced by SYMBOL's concurrent BFS over
the triple index. The subgraph contains:

```python
{
    "root_id":   int,                  # compound for this token
    "compounds": dict[int, dict],      # all compounds reached by BFS, keyed by ID
    "triples":   dict[int, list],      # triples for each compound: (subj, pred, target, type)
    "terminals": set[str],             # prime names where BFS stopped
}
```

This is the proposition network for each word in the utterance — not a flat list of
facts, but a graph of how concepts relate to each other down to prime level.

---

## Three prime families

THINK organises the 63 primes into three families. Each family requires different
reasoning treatment.

---

### Family 1 — Structural primes

`KIND`, `PART`, `BE`, `WITH`, `HAVE`, `FROM`, `TO`, `AT`, `IN`, `BETWEEN`, `SIDE`,
`NEAR`, `FAR`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `HERE`, `THIS`, `OTHER`, `ENTITY`, `BODY`

**Nature:** Definitional. These primes express what something *is* — its category
membership, composition, properties, and spatial/relational facts.

**In the triple graph:** structural primes appear as predicates in definition triples.
`bank KIND place`, `bank PART building`, `river BE water`. These are facts about
the ontology, not events.

**How THINK reads them:** As a classification hierarchy and property bundle. When a
token resolves to a compound whose neighborhood contains structural predicates, THINK
extracts:
- Category path (KIND chain): what family of thing this is
- Composition (PART): what it is made of or contains
- Properties (BE + adjective): what it is described as
- Spatial relations (AT/IN/FROM/TO): where/how it is located

THINK does not need to "understand" structural primes. It reads them as axiomatic.
`bank KIND financial_institution` is a fact: this meaning of "bank" belongs to the
financial-institution category. THINK reads that classification and uses it to select
reasoning mode and prune irrelevant propositions.

---

### Family 2 — Action primes

`DO`, `MOVE`, `MAKE`, `CHANGE`, `USE`, `CAUSE`, `OPEN`, `WRITE`, `BECAUSE`

**Nature:** Operational. These primes express what *happens* — events, transformations,
and causal chains.

**In the triple graph:** action primes appear as predicates in event triples.
`deposit DO transfer_money`, `erosion CAUSE change_shape`. These are event patterns —
schemas for what kinds of things happen and what they produce.

**How THINK reads them:** As candidate event frames. A compound with action-prime
triples in its neighborhood is a potential *event participant*: it can be an agent,
patient, instrument, or result of an action.

When the scene's prime field contains action primes, THINK asks:
- What action is being described or requested?
- Who/what is the agent? Who/what is the patient?
- Is this describing a past event, requesting a future one, or asking about a
  possible one?

Action primes drive THINK toward the `action_request` and `knowledge_query` reasoning
modes. The triple graph provides the event schema; the utterance provides the slot fillers.

**Causal chains:** `CAUSE` and `BECAUSE` triples link events. THINK follows causal
chains in both directions:
- Forward (CAUSE): if X happens, what follows?
- Backward (BECAUSE): what produced this outcome?

Causal reasoning is triggered when the scene contains connected event compounds with
CAUSE/BECAUSE triples between them.

---

### Family 3 — Cognitive primes

`THINK`, `KNOW`, `WANT`, `NEED`, `FEEL`, `CAN`, `SELF`, `YOU`, `LIFE`, `GOOD`, `BAD`,
`MORE`, `LESS`, `LIGHT`, `HEAT`, `ONE`, `MANY`, `ALL`, `SOME`, `NONE`,
`NOW`, `BEFORE`, `AFTER`, `LAST`, `TIME`, `HEAR`, `SEE`, `TOUCH`, `READ`, `SAY`

**Nature:** Intentional and evaluative. These primes express mental states, goals,
quantities, sensory access, and value judgements.

**In the triple graph:** cognitive primes appear as predicates expressing what an
agent believes, wants, or perceives. `user WANT information`, `PABLO KNOW definition`,
`event FEEL bad`.

**How THINK reads them:** As intentional states that drive the scene's purpose.
Cognitive primes reveal *why* the scene is happening:

- WANT + YOU → the user wants something → identify what and provide it
- KNOW + YOU → the user is asserting knowledge → store or verify it
- THINK + SELF → PABLO is being asked to reflect → introspective mode
- NEED + (any) → requirement is expressed → stronger than WANT
- FEEL → affective content → weight the response accordingly

Quantifiers (ONE/MANY/ALL/SOME/NONE) and temporal primes (NOW/BEFORE/AFTER/LAST/TIME)
modify how propositions apply: *all* banks vs *one* bank; what *was* true vs what *is*
true now.

Evaluative primes (GOOD/BAD/MORE/LESS) signal the scene's affective or comparative
dimension, informing tone and the structure of THINK's response.

---

## Reasoning modes

The scene's `prime_field` encodes which primes are dominant. THINK matches this pattern
against a routing table to select its reasoning mode. The mode determines the sequence
of operations THINK runs before forming its Intent Compound.

```
prime_field_bits pattern          → reasoning_mode
─────────────────────────────────────────────────────────────────────
KNOW ∩ BE                        → knowledge_query
SAY ∩ YOU                        → directed_message
DO ∩ (MOVE | MAKE | CHANGE)      → action_request
WANT ∩ (any)                     → preference_expression
NEED ∩ (any)                     → requirement_expression
THINK ∩ SELF                     → introspective_query
(no strong match)                → reflective_acknowledgement
```

---

### knowledge_query

**Trigger:** The scene is asking for factual information. Dominant primes: KNOW + BE.
Pattern: "what is X", "what does X mean", "tell me about X".

**What THINK does:**

1. Identify the query subject: which concept_id is being asked about.
2. Load that compound's full neighborhood from `scene.neighborhoods`.
3. Walk the KIND chain to locate the compound in the ontology — what category family
   it belongs to.
4. Collect definitional propositions: all BE, PART, WITH triples in the neighborhood.
5. Collect action triples (DO/MAKE/MOVE) that list what this entity does or is used for.
6. Collect any active narratives from `scene.active_narratives` relevant to this concept.
7. Rank collected propositions by triple confidence × primebit overlap with the query's
   prime field.
8. Assemble ranked propositions into a proposition set — the core of the answer.
9. Form Intent Compound from proposition set (see below).
10. Generate response_text: structured description from KIND → BE/WITH → DO/USE
    (general to specific, category first).

**Phase 1 response template:**
```
[compound.symbol] is a KIND of [kind_target].
It [BE propositions, comma-joined].
[DO/USE propositions, if any: "It is used to / It does..."]
```

---

### directed_message

**Trigger:** A message directed at PABLO from the user. Dominant primes: SAY + YOU.
Pattern: commands, declarations, greetings, feedback.

**What THINK does:**

1. Identify addressee from the scene — source is "keyboard" or "gui", confirming
   this is directed at PABLO.
2. Check the Instance Narrative for this source: what is the relational history?
   Load `relationship_quality` from `scene.relationship_quality`.
3. Classify the speech act:
   - Declarative (BE/HAVE + assertion): user is telling PABLO something → store + acknowledge
   - Imperative (DO/MAKE/MOVE + command): user wants PABLO to act → action_request sub-mode
   - Social (greeting, thanks, farewell): relational exchange → minimal, appropriate response
   - Evaluative (GOOD/BAD directed at PABLO): feedback → update relational state
4. For declarative speech acts: write a new Triple from the user's assertion into KNOW
   (source = scene.source, subj = user compound, pred = asserted prime, target = object).
5. For social exchanges: select an appropriate acknowledgement pattern from known Compounds.
   Tone is modulated by `relationship_quality` — warmer with high positive, neutral with new.
6. Form Intent Compound encoding the speech act classification.
7. Generate response_text appropriate to speech act type.

---

### action_request

**Trigger:** The user is requesting that PABLO do something. Dominant primes: DO +
(MOVE | MAKE | CHANGE).

**What THINK does:**

1. Identify the requested action from action-prime triples in the neighborhoods.
2. Check for an Action Compound in KNOW matching this action pattern *(Phase 2+)*.
   In Phase 1: pattern match against known action schemas in the compound store.
3. Identify slots: what are the agent, patient, instrument, result of the requested action?
   Walk neighborhoods for slot-filler candidates.
4. Check CAN: is this action within PABLO's current capability set? If not, form a
   response explaining the limitation honestly.
5. If executable: form an Intent Compound encoding the action plan.
   *(Phase 2+: execute via Action Compound execution model.)*
6. If not executable in Phase 1: acknowledge the request, explain Phase 1 constraints.

**Phase 1 constraint:** PABLO cannot take external actions (file writes, API calls,
system commands) in Phase 1 reasoning. THINK acknowledges action requests but does not
execute them.

---

### preference_expression

**Trigger:** The user is expressing a preference or desire. Dominant primes: WANT.

**What THINK does:**

1. Identify the WANT's object: what does the user want?
2. Walk the neighborhood of the want-object compound to understand its category and
   properties.
3. Check PABLO's goal structures *(Phase 5 — dormant in Phase 1)*. In Phase 1: treat
   the preference as a declarative.
4. Store the preference as a Triple: `(THIS_USER, WANT, want_object_compound)`.
5. Acknowledge the preference. If it is actionable in Phase 1 (e.g. wanting an
   explanation), route to knowledge_query sub-mode.
6. Form Intent Compound encoding WANT recognition.
7. Response: confirm understanding + act on the preference where possible.

---

### requirement_expression

**Trigger:** The user is expressing a requirement or necessity. Dominant primes: NEED.
Stronger signal than WANT — THINK treats NEED with higher priority.

**What THINK does:**

Same as preference_expression, but:
- Store as Triple with NEED predicate instead of WANT.
- Priority weight in any competing scenes is raised.
- Response is more direct — acknowledge urgency, act immediately where possible.

---

### introspective_query

**Trigger:** The user is asking PABLO about PABLO. Dominant primes: THINK + SELF.
Pattern: "what are you", "how do you work", "what do you know about X", "do you
remember Y".

**What THINK does:**

1. Classify the introspective question type:
   - Identity: "what are you" → describe PABLO's nature and prime structure
   - Capability: "can you do X" → check known action compounds for X
   - Memory: "do you know/remember X" → search KNOW for X, report honestly
   - Process: "how do you work" → describe the CognitiveScene pipeline
2. For identity questions: compose from PABLO's concept Compounds (PABLO as ENTITY,
   primes as PART, CognitiveScene as DO structure).
3. For memory questions: call `know.by_symbol(X)` and `know.all_by_symbol(X)`.
   If found: report what PABLO knows and from what source (known_symbols, narrative).
   If not found: report honestly that it is not in memory.
4. For process questions: narrate the pipeline: READ → SYMBOL → KNOW → SELF → THINK → SAY.
5. Form Intent Compound encoding the introspective answer.
6. Response reflects genuine self-knowledge — no confabulation. If PABLO does not know
   something about itself, THINK says so.

---

### reflective_acknowledgement

**Trigger:** Scene has no strong prime field match — ambiguous, noisy, or under-specified
input. Fallback mode.

**What THINK does:**

1. Report what was understood: list `known_symbols` vs `unresolved_tokens`.
2. Note the dominant prime, even if not strong: best guess at the scene's topic.
3. Surface any relevant active narratives for context.
4. Form a minimal Intent Compound: scene processed, no strong classification.
5. Response: brief acknowledgement with a request for clarification if the scene is
   ambiguous enough to warrant it. Never fabricate understanding that is not there.

The reflective_acknowledgement mode is THINK being honest about its own epistemic state.
It is not a failure — it is integrity operating correctly.

---

## How THINK reads the proposition graph

Before routing, THINK runs a **graph reading pass** across all neighborhoods in the
scene. This pass produces the Active Proposition Set that all reasoning modes draw from.

```
for each cid in scene.concept_ids:
    N = scene.neighborhoods[cid]          # {root_id, compounds, triples, terminals}

    for each (subj, pred, target, type) in N.triples[N.root_id]:
        if pred in STRUCTURAL_PRIMES:
            → add to classification_propositions
        elif pred in ACTION_PRIMES:
            → add to event_propositions
        elif pred in COGNITIVE_PRIMES:
            → add to intentional_propositions

        if target resolves to a compound in N.compounds:
            → follow into that compound's triples (depth already pre-fetched)
```

The graph reading pass does not recurse at runtime — the neighborhood BFS was already
run by SYMBOL before THINK engaged. THINK reads the pre-fetched subgraph.

**Proposition weighting:** Each proposition carries an initial weight:

```
weight = compound.confidence × triple_type_weight × primebit_overlap

triple_type_weight:
    "definition" → 1.0   (trusted ontological fact)
    "observed"   → 0.8   (empirical, scene-derived)
    "inferred"   → 0.6   (reasoned conclusion)
    "candidate"  → 0.3   (unverified)

primebit_overlap:
    popcount(scene.prime_field_bits & compound.primebit) / max_possible_overlap
```

Propositions with weight below 0.2 are pruned before routing. What remains is the
Active Proposition Set.

---

## Intent Compound

Every THINK cycle produces exactly one Intent Compound — the crystallised output of the
reasoning cycle. It is written to KNOW and its ID stored in `scene.intent_id`.

```python
Intent Compound shape:
    compound_type:  "intent"
    symbol:         "{reasoning_mode}:{scene_id[:8]}"   # e.g. "knowledge_query:3f2a1b9e"
    primebit:       union of all activated proposition primes
    nested:         [root concept_ids from the scene]
    source:         scene.source
    confidence:     mean weight of propositions in Active Proposition Set
    grounded:       True if all nested compounds are grounded; False if any are placeholders
```

The Intent Compound is not the response. It is what PABLO understood — the crystallised
form of the experience, stored permanently, refinable in future scenes when comparison
reveals mismatch.

**Why this matters:** If a future scene surfaces this Intent Compound through cued recall,
PABLO can compare the new scene's interpretation against what it previously crystallised.
This is the error-correction loop from the theory operating on THINK's own outputs.

---

## Response generation

After forming the Intent Compound, THINK generates `response_text`.

### Phase 1: Template assembly

Propositions from the Active Proposition Set are assembled into a response using
mode-specific templates. The output is grammatical but mechanical — structural
descriptions, honest acknowledgements, classification chains.

Template rules:
- Lead with category classification (KIND chain) when answering factual questions.
- Use surface symbols from matched Compounds, not internal IDs.
- State confidence explicitly when it is low: "I have some information about X..."
- State absence honestly: "I don't have X in memory."
- Keep responses minimal — do not over-explain. One proposition per sentence maximum.

### Phase 3: LLM-assisted phrasing

THINK passes the Intent Compound and Active Proposition Set to an LLM phrasing module.
The LLM receives:
- A symbolic description of what THINK understood (the proposition set)
- The Intent Compound's prime-space encoding
- The reasoning mode
- The scene's source and relationship_quality

The LLM produces natural language phrasing consistent with the symbolic content.
THINK validates the output against the proposition set before writing it to response_text.
If the phrasing contradicts a proposition (confabulates), it is rejected and Phase 1
template is used instead.

---

## What THINK writes to the scene

```
scene.reasoning_mode    str         selected reasoning mode (one of 7)
scene.intent_id         int         permanent ID of Intent Compound written to KNOW
scene.response_text     str         formed response
scene.think_cycles      int         incremented each loop
scene.stage             → "output"  signals SAY to engage
```

## What THINK writes to KNOW

**Intent Compound** — one per conscious thought cycle. Type `"intent"`. The crystallised
record of what THINK understood, permanently stored.

**Assertion Triples** — when a directed_message contains a declarative speech act,
THINK writes the asserted Triple to KNOW:
```
Triple(source_id=utterance_id, subject=THIS_USER, predicate=asserted_prime, target=object_symbol)
```

**Action Compounds** *(Phase 2+)* — when THINK identifies a new executable action
pattern. Stored with `executable=True` and `trigger_condition` set.

**Macro Compounds** *(Phase 2+)* — when an action pattern executes successfully 3+
times, bundled into a reusable Compound for fast future access.

## SymbolicScene contribution

THINK contributes to the SymbolicScene with:
- The reasoning Triple chain: `(utterance_compound) -[THINK]→ (intent_compound)`
- The Intent Compound itself
- A Narrative fragment: a concise PLanguage record of what THINK understood and intends
  to express. This becomes a new entry in the Instance Narrative for the scene's source,
  extending the relational memory thread.

---

## Architecture

### When THINK engages

THINK is sensitive to `scene.thread_type == "conscious"` AND `scene.intent_id is None`.
This condition is set by SELF when it promotes a scene to conscious foreground.

### Steps

1. Run graph reading pass → Active Proposition Set
2. Load Instance Narrative for this source from KNOW
3. Resolve scene Compounds to Narrative entity bindings
4. Route: match `scene.prime_field_bits` against routing table → `reasoning_mode`
5. Execute reasoning mode steps (see above)
6. Form Intent Compound from Active Proposition Set + reasoning mode output
7. Write Intent Compound to KNOW → `scene.intent_id`
8. Generate `response_text` (Phase 1 template; Phase 3 LLM-assisted)
9. Write SymbolicScene contribution
10. Write execution layer: `reasoning_mode`, `intent_id`, `response_text`, `stage → "output"`

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Full graph reading pass across pre-fetched neighborhoods |
| 1 | All 7 routing modes with template-based response |
| 1 | Intent Compound written to KNOW each cycle |
| 1 | Assertion Triples from declarative speech acts |
| 2 | Action Compound execution via compound execution model |
| 2 | Macro Compound creation (3+ successful executions) |
| 3 | LLM-assisted response phrasing with proposition validation |
| 4 | FEEL-weighted proposition ranking (affective salience) |
| 5 | WANT/NEED integration — goal-aware routing |

---

*See [cognitive_scene.md](../SYSTEM/cognitive_scene.md) for the scene THINK reads and writes.*
*See [self.md](self.md) for the attention gate that activates THINK.*
*See [know.md](know.md) for what THINK reads from and writes to.*
*See [symbol.md](symbol.md) for neighborhood pre-fetching that THINK depends on.*
*See [theory.md](../SYSTEM/theory.md) for the crystallisation theory underlying Intent Compound formation.*
