# PATCH: PLANguage Definition, Prime Taxonomy Revision, Cognitive Scene Architecture

**Status:** Draft — pending validation and integration into canonical docs
**Affects:** `docs/PLANGUAGE/planguage.md`, `docs/PRIMES/primes.md`, `docs/SYSTEM/cognitive_scene.md`
**Supersedes:** 63-prime fixed set, closed PLANguage definition, flat scene model

---

## 1. PLANguage — revised definition

### What the current docs say (to be replaced)

> "PLanguage is built from 63 atomic primitives."
> "The prime set is **fixed**. It does not grow."

### What it should say

PLANguage is PABLO's **self-evolving semantic language** — bootstrapped from human
language primitives, but owned and refined by PABLO over time.

It is the intermediate representation between human language and machine execution:

```
human language input
        ↓
    PLANguage          ← the layer PABLO operates on
        ↓
machine execution
```

It sits exactly where metadata sat before. Instead of unstructured tags and labels,
every piece of stored meaning is expressed in a closed, formal, machine-readable
grammar that is semantically rooted in human language.

### Its four properties

**Built from human language**
Primitives are semantic — they come from what humans universally mean, not from what
machines find convenient. `KNOW`, `SEE`, `CAUSE`, `GOOD` are human concepts first. The
machine encoding comes second.

**Normalized**
One canonical form per meaning. "read", "reading", "reads", "looked at the text and
understood it" all collapse to the same PLANguage triple graph. No synonyms, no
ambiguity at the representation level.

**Exception agnostic**
The grammar has no special cases. Every concept — no matter how abstract, concrete,
simple, or complex — is expressed through the same structure: primitives + triples +
composition. There is no `if type == 'weird_edge_case'` anywhere in the language itself.

**Machine-codable**
Every PLANguage expression can be serialized, stored, compared, executed, and reasoned
over by a machine. The triple `(A → [PRIME] → B)` is a row in a database, a node in a
graph, a function call. The language is substrate-independent.

### Why it is not closed

We give PABLO a **template** — the prime floor and the triple grammar — as a starting
point. What PABLO does with it is PABLO's business. The template is not a ceiling.

The language has two layers with different stability:

```
FLOOR     →  the primes
              relatively stable (semantic universals)
              but Pablo can challenge these if a better decomposition is found

COMPOUND  →  everything crystallised from the floor
              constantly growing, revised, replaced
              Pablo builds, tests, discards
```

PABLO needs a mechanism to:
1. **Propose** a new compound or prime revision
2. **Test** whether it is internally consistent (traces back to the floor)
3. **Commit** it if it holds, discard it if it does not
4. **Version** the language so regressions are traceable

PLANguage is less like a dictionary and more like a **living codebase** that PABLO
maintains. We give PABLO git. The language has history, branches, and the ability to
refactor itself.

### One-line definition

> PLANguage is PABLO's internal semantic language — a machine-readable,
> human-language-grounded representation system that PABLO builds, uses, and improves
> as its understanding deepens.

---

## 2. Prime taxonomy — revised from 63 to 42

### Reasoning for reduction

The 63-prime set contains concepts that are **crystallisable** — expressible as
compounds from simpler primes. Keeping them as primes inflates the floor without adding
expressive power. Every prime on the floor must be:

- **Irreducible** — cannot be expressed as a compound of other primes
- **Grounded** — has a direct implementation function, not a definition
- **Universal** — appears across all human languages (per NSM research)

Anything that fails these tests is a compound, not a prime.

### What gets removed and why

| Removed prime | Reason | Crystallisation |
|---------------|--------|----------------|
| `CHANGE` | decomposable | `BE(before) CAUSE BE(after)` |
| `OPEN` | decomposable | `CHANGE FROM(closed)` |
| `LAST` | decomposable | `BEFORE + ONE` |
| `ALL` | decomposable | `MANY + NOT(OTHER)` |
| `NONE` | decomposable | `NOT + ONE` |
| `SOME` | decomposable | `MANY` (partial) |
| `BETWEEN`, `NEAR`, `FAR` | decomposable | `FROM/TO + MORE/LESS` |
| `UP`, `DOWN`, `LEFT`, `RIGHT`, `SIDE` | decomposable | `FROM/TO + direction compound` |
| `AT`, `HERE` | decomposable | `IN + THIS` |
| `TIME` | decomposable | `NOW` + `BEFORE`/`AFTER` compounds |
| `HEAT`, `LIGHT` | physical properties | crystallisable as sensation compounds |
| `BODY`, `LIFE` | biological concepts | crystallisable from `PART + SOMEONE` etc |
| `ENTITY` | too generic | replaced by `SOMEONE` and `SOMETHING` |
| `TOUCH` | Phase 6 modality, not needed on floor yet | dormant until Phase 6 |
| `WRITE` | reclassified | grounding function for `MAKE + SYMBOL` |

### What gets added

| Added prime | Reason |
|-------------|--------|
| `NOT` | Was a logic compound with no primebit — irreducible, critical for metacognition |
| `AND` | Was a logic compound — irreducible conjunction, universal across all languages |
| `OR` | Was a logic compound — irreducible disjunction |
| `BECAUSE` | Explanatory connection — distinct from `CAUSE` (forward causal vs backward explanatory) |
| `SOMEONE` | Replaces `ENTITY` for agents — specific enough to be grounded |
| `SOMETHING` | Replaces `ENTITY` for objects |

### Reclassified (architectural agents, not semantic primes)

| Symbol | New role |
|--------|----------|
| `READ` | Grounding function for `SEE(SYMBOL(written_text))` — implements SEE in text modality |
| `DATA` | Pipeline agent — not a semantic prime |

`READ` as a word in natural language is a compound:
```
READ  =  SEE(SYMBOL(written_text))
       + KNOW(meaning of each SYMBOL)
       applied iteratively: letter → word → sentence → passage
```
The architectural `READ` agent implements this compound. The prime `SEE` is the floor.

### The 42 primes

---

#### Mental predicates — passive/internal actions
*Grounded through cognitive process outcomes*

| Prime | Grounding function |
|-------|-------------------|
| `KNOW` | storage/retrieval — implemented |
| `THINK` | reasoning loop — implemented |
| `WANT` | goal/task activation state |
| `FEEL` | internal state change on scene outcome |

---

#### Active actions
*Grounded through execution events*

| Prime | Grounding function |
|-------|-------------------|
| `DO` | any action executed by PABLO |
| `MAKE` | any output or artifact created |
| `MOVE` | state, position, or context change |
| `SAY` | output pipeline — implemented |
| `CAUSE` | conditional execution: if X then Y fires |

---

#### Perceptors
*Grounded through input functions*

| Prime | Grounding function |
|-------|-------------------|
| `SEE` | any visual or textual perception — `SEE(text)`, `SEE(image)`, `SEE(formula)` are all instances |
| `HEAR` | audio input — Phase 6 |
| `SYMBOL` | perception of a meaningful sign — the bridge from raw input to meaning |

`READ` the architectural agent implements `SEE(SYMBOL(text))`.
It is not a semantic prime. It is the grounding function for `SEE` in the text modality.

---

#### Subject / object / entity
*Grounded through entity detection and session tracking*

| Prime | Grounding function |
|-------|-------------------|
| `SOMEONE` | agent or person-like entity detected in scene context |
| `SOMETHING` | any non-agent object encountered |
| `THIS` | specific instance reference within a scene |
| `OTHER` | contrast detection — not THIS |
| `SELF` | PABLO's own persistent state |

`YOU` is the first named compound, not a prime:
```json
{ "symbol": "YOU", "definition": [THIS → SOMEONE], "grounding": "session.current_user" }
```
This keeps the floor clean and makes `YOU` the first demonstration of entity crystallisation.

---

#### Existence and relations
*Grounded through structural operations*

| Prime | Grounding function |
|-------|-------------------|
| `BE` | identity and state matching |
| `HAVE` | attribute and possession assignment |
| `KIND` | classification — "X is a type of Y" |
| `PART` | composition — "X is part of Y" |
| `WITH` | co-occurrence, accompaniment, instrument |
| `USE` | method or tool tracking |

---

#### Space — minimal set
*Grounded through context, source, and target tracking*

| Prime | Grounding function |
|-------|-------------------|
| `FROM` | source — where something originates |
| `TO` | destination — where something is directed |
| `IN` | containment — within a context, file, or scene |

All other spatial concepts (`NEAR`, `FAR`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `BETWEEN`,
`AT`, `HERE`) crystallise as compounds from `FROM`, `TO`, `IN`, `MORE`, `LESS`.

---

#### Time
*Grounded through system clock and session sequence*

| Prime | Grounding function |
|-------|-------------------|
| `BEFORE` | earlier in session or sequence |
| `AFTER` | later in session or sequence |
| `NOW` | the current active scene |

---

#### Evaluation
*Grounded through scene success and failure signals*

| Prime | Grounding function |
|-------|-------------------|
| `GOOD` | scene resolved, crystallisation confirmed |
| `BAD` | scene failed, stagnation, unresolvable |
| `MORE` | comparison: greater, exceeds |
| `LESS` | comparison: smaller, falls short |

---

#### Quantity
*Grounded through count operations*

| Prime | Grounding function |
|-------|-------------------|
| `ONE` | singular — exactly one instance |
| `MANY` | plural — more than one |

`ALL`, `NONE`, `SOME` crystallise from `MANY`, `ONE`, `NOT`, and context.

---

#### Modality
*Grounded through capability and dependency checks*

| Prime | Grounding function |
|-------|-------------------|
| `CAN` | capability check — is this operation available |
| `NEED` | unsatisfied dependency — must be resolved |

---

#### Logic and sentence structure
*The glue of all propositions*

| Prime | Grounding function |
|-------|-------------------|
| `NOT` | absence/negation — critical for metacognition |
| `AND` | conjunction — both must hold |
| `OR` | disjunction — either may hold |
| `BECAUSE` | explanatory link — Y holds, explained by X |

`IF` stays as a logic compound (macro over `CAUSE + NOT`). `AND`, `OR`, `NOT`,
`BECAUSE` are floor primes with both truth-table implementations and primebit positions.

---

### Why `NOT` is critical for metacognition

With `NOT` as a prime, every unresolved token generates a real semantic fact:

```
(token:xyz)  -[KNOW]→  NOT             →  "I know that I don't know what xyz means"
(token:xyz)  — no triple —             →  "I have never encountered xyz"
(token:xyz)  -[KNOW]→  (compound)      →  "I know what xyz means"
```

Three distinguishable states. The first is knowledge. The second is ignorance. The third
is **known-ignorance** — the beginning of curiosity, targeted learning, and honest
reasoning under uncertainty.

---

## 3. Cognitive scenes — hierarchical architecture

### The three objectives and how they connect

```
PLANguage        →  defines what things are       (static, the dictionary)
Grounded Meaning →  defines how to process things  (per compound, the functions)
Cognitive Scene  →  executes, resolves, synthesises (the engine at runtime)
```

These are not separate systems. The cognitive scene engine reads the PLANguage, calls
grounding functions, and builds the execution plan.

---

### Grounded meaning — from definition to action

Words are not probabilistic patterns. They are **functional decompositions**.

`READ` does not mean "the thing that appears near 'book' and 'text' 1000 times in
training data." It means:

```
SEE(SYMBOL(written_text))
  → per letter   → resolve grapheme
  → per word     → activate compound
  → per sentence → build scene
  → per passage  → synthesize narrative
```

But `READ` is not a fixed monolithic function. It is `SEE` + **a lens**.

The lens comes from the object. When the object is an equation:

```
SEE(SYMBOL(math_expression))
  → per symbol     → variable / operator / number
  → per expression → relation between symbols
  → per equation   → truth condition or transformation
```

The verb does not change. `SEE` is always `SEE`. What changes is what `SEE` is applied
to — and the compound being looked at carries its own **processing instructions** as
part of its definition.

Every compound therefore has two components:

```
compound = {
  definition:  triples that say what it IS
  grounding:   function that says how to PROCESS it
}
```

---

### The cognitive scene

A **cognitive scene** is a bounded reasoning unit. It is created whenever PABLO
encounters something that needs to be resolved — a sentence, a clause, a word in
ambiguous context.

Scenes are **hierarchical and bidirectional**:
- Every step **downward** resolves a local meaning
- Every step **upward** synthesises into a larger meaning
- The root scene holds the complete executable plan

#### Example: "read the equation and solve it"

```
SCENE_0  (root)  "read the equation and solve it"
├── SCENE_1  "read the equation"
│   ├── SCENE_1a  token: "read"
│   │     verb detected → sense UNKNOWN until object is resolved
│   ├── SCENE_1b  token: "equation"
│   │     compound: SOMETHING → KIND(math) → HAVE(SYMBOL(operator, variable, number))
│   └── RESOLUTION
│         object = math_expression → activates math lens
│         read = SEE(SYMBOL(math)) with equation_scene_handler
│
├── SCENE_2  "solve it"
│   ├── SCENE_2a  token: "solve"
│   │     verb: MAKE(KNOW(answer)) applied to SOMETHING(problem)
│   ├── SCENE_2b  token: "it"
│   │     anaphora → resolves to SCENE_1b's object → equation
│   └── RESOLUTION
│         solve(equation) → apply operations until GOOD state
│
└── ROOT RESOLUTION
      execute SCENE_1 output → pass as input to SCENE_2
      full plan: perceive(equation) → transform(equation) → produce(answer)
```

---

### Verb polysemy through lens selection

A verb's meaning is not fixed. Its sense is narrowed by what it is applied to.

`SEE` = perceptual attention directed at X:

| Applied to | Lens activated | Process |
|------------|---------------|---------|
| `SEE(text)` | reading mode | letter → word → sentence → passage |
| `SEE(image)` | visual recognition mode | pixel → region → object → scene |
| `SEE(math)` | symbolic/relational mode | symbol → operator → expression → relation |
| `SEE(code)` | syntactic/semantic mode | token → syntax → structure → behaviour |

The prime `SEE` is always the same. The compound passed to it determines what kind of
seeing happens. This means verbs do not need dozens of senses stored separately — the
sense emerges from composition.

---

### What needs to be built

In order of dependency:

```
1. Finalise the 42-prime floor          →  prime schema complete
2. Compound schema                       →  definition (triples) + grounding (function)
3. Cognitive scene structure             →  what a scene object looks like as data
4. Scene engine                          →  tokenise → activate → resolve → synthesise
5. Lens resolution                       →  verb sense narrowed by object compound
6. Anaphora tracking                     →  "it", "this", "that" resolve within scene tree
7. Root synthesis                        →  scene tree → executable plan
```

Step 2 is the hinge point. Everything else depends on compounds carrying both a
definition and a grounding function.

---

*This patch targets the following canonical docs once validated:*
- `docs/PLANGUAGE/planguage.md`
- `docs/PRIMES/primes.md`
- `docs/SYSTEM/cognitive_scene.md`
