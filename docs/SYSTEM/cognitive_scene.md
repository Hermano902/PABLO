# CognitiveScene — Specification

*PABLO's inner voice. The shared workspace of experience.*

---

## What a CognitiveScene Is

When PABLO encounters any input — external (text, voice, image) or internal (a goal activating,
a memory surfacing) — a CognitiveScene is opened.

The scene is PABLO's representation of that experience as it unfolds. It is not a log or a
record after the fact. It is the live workspace where primes contribute their perception of
the input, where meaning is assembled, where attention is decided, and where response is formed.

Think of it as PABLO's inner voice for a single experience: the continuous, integrating
representation that bridges raw sensation and formed thought. When the experience is complete
— when SAY has expressed what THINK formed, or when SELF has decided the scene does not
warrant conscious attention — the scene closes and is preserved in the SceneStore.

A scene maps to one utterance or one internal event. It is the atomic unit of experience.

---

## Two Channels

Each CognitiveScene runs two representations simultaneously:

---

### Channel 1: MetaScene (Scaffolded)

Structured fields with explicit human-readable labels. Each prime is assigned a section.
The MetaScene makes the scene inspectable, debuggable, and comparable during development.

```
IDENTITY
    scene_id        str         uuid4
    opened_at       float       unix timestamp
    source          str         "keyboard" | "gui" | "internal" | "voice"
    stage           str         current pipeline stage

PERCEPTION          [READ writes here]
    raw_input       str         unprocessed input text
    modality        str         "text" | "voice" | "image"
    preliminary_tokens  list[str]   surface tokens before interpretation

SYMBOL              [SYMBOL writes here]
    token_resolutions   list[dict]  per-token: {token, lemma, prime, score, method, pos}
    prime_field         dict        {prime_name: max_score} across all tokens
    prime_field_bits    int         union PrimeBit value
    unresolved_tokens   list[str]   tokens with no prime match

MEMORY              [DATA + KNOW write here]
    utterance_id        int | None  permanent ID of the utterance Compound
    concept_ids         list[int]   IDs of all concept Compounds in this scene
    known_symbols       list[str]   symbols found in KNOW (existing)
    new_symbols         list[str]   symbols created new in this scene
    active_narratives   list[int]   narrative IDs surfaced from KNOW

AFFECTIVE           [FEEL writes here — Phase 4]
    valence         float       -1.0 to +1.0
    intensity       float       0.0 to 1.0
    emotional_tag   str         dominant emotional quality

MOTIVATIONAL        [WANT / NEED write here — Phase 5]
    goal_relevance  float       0.0 to 1.0
    need_pressure   float       0.0 to 1.0
    active_goal     str         current dominant goal label

RELATIONAL          [SELF writes here]
    salience            float       computed attention score
    attention_decision  str         "conscious" | "archived" | "pending"
    relationship_quality str        "neutral" | "familiar" | "trusted" | "strained"

EXECUTION           [THINK + SAY write here]
    reasoning_mode  str         routing mode selected by THINK
    intent_id       int | None  ID of the intent Compound created by THINK
    response_text   str         final text to be expressed by SAY

CLOSE
    closed_at       float | None    unix timestamp when SAY closes the scene
```

The MetaScene is **authoritative during Phase 1**. Primes write to it directly. It is the
source of truth for the GUI Scene panel and for evaluating SymbolicScene quality.

---

### Channel 2: SymbolicScene (Native)

An unstructured collection of Compounds, Triples, and Narrative fragments contributed by
each prime — expressed in PABLO's own language.

No field labels. No assigned structure. Each prime contributes what it has learned to
contribute, and nothing more. The SymbolicScene is how PABLO will eventually think.

```python
@dataclass
class SceneContribution:
    prime:              str             # which prime contributed this
    compounds:          list[Compound]  # crystallised observations
    triples:            list[Triple]    # relational assertions
    narrative_fragment: str | None      # a fragment of inner voice, if formed

@dataclass
class SymbolicScene:
    contributions:      list[SceneContribution]
    narrative_thread:   list[int]       # ordered Compound IDs forming the scene's story
```

Initially, primes write nothing (or very little) to the SymbolicScene. Over time, as they
learn what is meaningful to contribute, the SymbolicScene grows richer.

---

## The Retirement Process

The MetaScene and SymbolicScene are compared continuously. For each MetaScene field, the
question is: *does the SymbolicScene contain enough information to reconstruct this?*

When the answer is yes for a given field, that MetaScene field is **retired**:
- The field remains in the dataclass (for backward compat) but is no longer written
- The SymbolicScene contribution is treated as authoritative
- The GUI Scene panel shows the symbolic contribution instead

When all MetaScene fields have been retired, PABLO thinks entirely in its own language.

This process is not designed. It emerges from the primes learning what to contribute and
from explicit evaluation sessions where the two channels are compared.

The comparison metric (Phase 1: visual inspection in GUI):
- Coverage: does the SymbolicScene contain representations of all MetaScene fields?
- Fidelity: do the symbolic representations match the MetaScene values?
- Expressiveness: does the SymbolicScene contain information not in MetaScene?

---

## Scene Lifecycle

```
INPUT ARRIVES
    ↓
READ opens scene → writes PERCEPTION layer
    ↓
SYMBOL contributes → writes SYMBOL layer
    ↓
DATA + KNOW contribute → write MEMORY layer
    ↓
SELF contributes → writes RELATIONAL layer
    ├── attention_decision = "archived" → scene closes (SceneStore preserves it)
    └── attention_decision = "conscious"
            ↓
        [FEEL contributes → AFFECTIVE layer]     ← Phase 4
        [WANT contributes → MOTIVATIONAL layer]  ← Phase 5
            ↓
        THINK contributes → writes EXECUTION layer
            ↓
        SAY contributes → writes response_text, closes scene
            ↓
        response emitted to GUI / output
```

The brackets indicate future phases. In Phase 1-3, the scene goes directly from MEMORY
to RELATIONAL to EXECUTION.

---

## Stage Labels

The `stage` field tracks where the scene currently is:

| Stage | Set by | Meaning |
|-------|--------|---------|
| `perception` | READ | raw input received, tokens extracted |
| `symbol` | SYMBOL | token interpretation complete |
| `memory` | DATA/KNOW | compounds stored, memory surfaced |
| `attention` | SELF | salience evaluated |
| `archived` | SELF | below threshold, scene closed without THINK |
| `execution` | THINK | reasoning and response formation |
| `output` | SAY | response ready for expression |
| `closed` | SAY | scene complete |

---

## Prime Contributions: What Each Prime Writes

### READ
**MetaScene:** `raw_input`, `modality`, `preliminary_tokens`, `stage → "symbol"`
**SymbolicScene:** A single Compound representing the raw experience (the utterance before
any interpretation). Compound type: `observation`. No primebit yet assigned.

### SYMBOL
**MetaScene:** `token_resolutions`, `prime_field`, `prime_field_bits`, `unresolved_tokens`,
`stage → "memory"`
**SymbolicScene:** One Compound per resolved token (prime-grounded). Triples linking
tokens to primes: `(token) -[SYMBOL]→ (prime)`. Unresolved tokens become placeholder
Compounds with no primebit.

### DATA + KNOW
**MetaScene:** `utterance_id`, `concept_ids`, `known_symbols`, `new_symbols`,
`active_narratives`, `stage → "attention"`
**SymbolicScene:** The assembled Compound set (concepts + utterance). Triples encoding
positional relationships (AFTER, PART). Narrative fragments from surfaced memories.

### SELF
**MetaScene:** `salience`, `attention_decision`, `relationship_quality`,
`stage → "execution"` or `"archived"`
**SymbolicScene:** A Compound expressing the relational evaluation. For example:
a triple `(source) -[SELF/FEEL]→ (salience_compound)` where the salience compound
encodes the weight. Eventually SELF will express the entire attention decision in
compounds without the MetaScene scaffold.

### THINK
**MetaScene:** `reasoning_mode`, `intent_id`, `response_text`, `stage → "output"`
**SymbolicScene:** A chain of Triples representing the reasoning path. An intent Compound.
A Narrative fragment representing the formed response in compound space — PABLO's
native-language version of what it is about to say.

### SAY
**MetaScene:** closes `closed_at`, `stage → "closed"`
**SymbolicScene:** The final Narrative fragment — the expressed response as a Compound
sequence, preserved in KNOW as a new Narrative entry. This is PABLO's memory of what
it said, in its own language.

---

## SceneStore

The SceneStore holds scenes in memory across the session.

```python
class SceneStore:
    MAX_SCENES = 100    # keep last 100 scenes in memory

    def open(self, source: str, **kwargs) -> CognitiveScene
    def close(self, scene: CognitiveScene) -> None
    def write(self, scene_id: str, **kwargs) -> None   # atomic field update
    def get(self, scene_id: str) -> CognitiveScene | None
    def recent(self, n: int = 5) -> list[CognitiveScene]   # newest first
    def by_stage(self, stage: str) -> list[CognitiveScene]

scene_store = SceneStore()   # module-level singleton
```

Closed scenes are preserved in the SceneStore for session inspection. They are not persisted
to disk (scenes are ephemeral; Compounds and Narratives are what persist).

---

## The Scene as Transformer Analogue

A useful analogy: if a transformer processes input through layers of attention and produces
a weighted representation across all positions, the CognitiveScene processes input through
layers of prime attention and produces a weighted representation across all prime dimensions.

But where a transformer's internal representation is a dense matrix of floating-point weights
opaque to inspection, PABLO's CognitiveScene is a structured symbolic representation:
human-readable, traceable to individual primes, and refinable through the error-correction
loop.

The MetaScene is the inspectable form. The SymbolicScene is the native form. The goal is for
the two to converge — for the SymbolicScene to carry everything the MetaScene does, expressed
in PABLO's own language rather than in human-assigned field labels.

When that convergence happens, PABLO is no longer translating its experience into a format
designed for human inspection. It is thinking in its own language, with the MetaScene reduced
to a viewing window for debugging rather than the substance of thought.

---

*See `system_concept.md` for context.*
*See `docs/PRIMES/PRIMES_CONCEPT.md` for what each prime is.*
*See `docs/COMPOUND/compound_concept.md` for the Compound structure.*
*See `docs/NARRATIVES/narratives_concept.md` for how Narratives form from scene contributions.*
