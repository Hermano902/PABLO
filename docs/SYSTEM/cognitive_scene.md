# CognitiveScene

*PABLO's thinking threads. The shared workspace of experience.*

---

## Concept

When PABLO encounters any input — external (text, voice, image) or internal (a goal
activating, a memory surfacing) — a CognitiveScene is opened.

The scene is not a log or a pipeline step. It is a **live thinking thread**: a shared
workspace where any prime can contribute whenever its conditions are met, independently
of every other prime. No prime calls another. No prime waits for a gate.

Primes watch the SceneStore continuously. When a scene's content satisfies a prime's
entry condition, the prime acts and writes its contribution back to the scene. The order
that emerges is natural — driven by data dependencies, not by imposed sequence.

---

### The scene as transformer analogue

A transformer processes input through layers of attention and produces a weighted
representation across all token positions. The CognitiveScene processes input through
layers of prime attention and produces a weighted representation across all prime
dimensions.

Where a transformer's internal state is a dense matrix of floats opaque to inspection,
the CognitiveScene is a structured symbolic representation: human-readable, traceable
to individual primes, and refinable through the error-correction loop.

---

## Two thread classes

Every scene belongs to one of two thread classes, each with its own lifecycle.

---

### Unconscious threads

Always running. Low cost, high volume. READ, SYMBOL, DATA, and KNOW all operate
primarily here. Unconscious threads process every scene in parallel with no serialisation
constraint.

An unconscious thread ends in one of three ways:

| Outcome | Triggered by | Meaning |
|---------|-------------|---------|
| `promoted` | SELF | Salience threshold crossed — scene enters the conscious layer |
| `archived` | SELF | Processed, nothing notable, kept for session memory |
| `suppressed` | SELF | Competing with a higher-salience thread, parked |

Suppressed scenes are not deleted. If the foreground conscious thread stalls, SELF may
resurface a suppressed scene.

---

### Conscious threads

Expensive. Serialised into a priority queue managed by SELF. THINK and SAY operate here.

The conscious layer has three slots:

| Slot | Description |
|------|-------------|
| **Foreground** | One scene. THINK's full attention. |
| **Background** | Up to 2 scenes. THINK's partial attention — occasional cycles. |
| **Stagnation queue** | Scenes with no recent progress. Heartbeat-checked periodically. |

SELF manages promotions and demotions between slots. If the foreground scene resolves
quickly, a warm background scene is promoted immediately — no cold start.

A conscious thread ends in one of three ways:

| Outcome | Triggered by | Meaning |
|---------|-------------|---------|
| `archived` | SAY | Response emitted. Scene preserved with full contribution record. |
| `failed` | SELF / THINK | Dead end. Scene marked failed. SELF decides: retry, drop, or escalate. |
| `archived` (stagnation) | SELF | No progress after timeout. Scene demoted or archived as low-priority. |

---

## Stagnation detection

Two mechanisms, both always present:

```python
stagnation_timeout:    float        # wall-clock threshold — always active
stagnation_max_cycles: int | None   # THINK sets this for content-based control
last_progress_at:      float        # updated on every prime contribution
think_cycles:          int          # incremented by THINK on each loop
```

Stagnation triggers when **either** condition is met first. THINK can tighten its own
leash by setting `stagnation_max_cycles`. Over time PABLO learns to set this dynamically
based on scene type and past performance.

Default: `stagnation_timeout = 5.0` seconds, `stagnation_max_cycles = None`.

---

## Prime entry conditions

Primes do not wait for a stage gate. Each prime watches the SceneStore and acts when the
scene's content satisfies its entry condition:

| Prime | Entry condition | Writes |
|-------|----------------|--------|
| READ | external signal crosses threshold | opens scene, `raw_input`, `preliminary_tokens` |
| SYMBOL | scene has `raw_input`, no `script` yet | `script`, `language_hint`, `preliminary_tokens` (refined), `modality` |
| KNOW | scene has `script` + `preliminary_tokens`, no `token_resolutions` yet | `token_resolutions`, `prime_field`, `prime_field_bits`, `utterance_id`, `concept_ids`, `known_symbols`, `new_symbols` |
| KNOW | scene has `prime_field_bits > 0`, no `active_narratives` yet | `active_narratives` (cued recall) |
| DATA | scene has `concept_ids`, no `validation_flags` yet | `validation_flags` (graph integrity, advisory) |
| SELF | scene has `concept_ids` | `salience`, `attention_decision`, promotes or archives |
| THINK | scene promoted to conscious foreground | `reasoning_mode`, `intent_id`, `response_text` |
| SAY | scene has `response_text` | `closed_at`, emits response |

These are the Phase 1 defaults. Any prime may define its own entry condition — an actor
steps on when the stage holds what they need, not before. No prime is blocked from
acting on any part of the scene.

---

## Two channels

Each CognitiveScene runs two representations simultaneously.

---

### Channel 1: MetaScene (scaffolded)

Structured fields with explicit human-readable labels. Each prime has an assigned
section. The MetaScene makes the scene inspectable, debuggable, and comparable during
development.

```
IDENTITY
    scene_id               str          uuid4
    opened_at              float        unix timestamp
    source                 str          "keyboard" | "gui" | "internal" | "voice"
    thread_type            str          "unconscious" | "conscious"
    status                 str          "active" | "promoted" | "archived" | "suppressed" | "failed"
    salience               float        SELF updates continuously
    last_progress_at       float        updated on every contribution
    stagnation_timeout     float        default 5.0s
    stagnation_max_cycles  int | None   set by THINK; None = disabled
    think_cycles           int          THINK loop counter

PERCEPTION              [READ writes here]
    raw_input           str         unprocessed input signal
    modality            str         "text" | "voice" | "image" | "audio"
    preliminary_tokens  list[str]   surface tokens before interpretation

SYMBOL                  [SYMBOL writes here]
    script              str         dominant Unicode block: "latin" | "cyrillic" | "cjk" | ...
    language_hint       dict        {ISO-639 code: confidence}  e.g. {"en": 0.92, "de": 0.05}
    modality            str         confirmed: "text" | "image" | "audio"

MEMORY                  [KNOW writes here — resolution pass]
    token_resolutions   list[dict]  per-token: {token, compound_id, symbol, score, method}
    prime_field         dict        {prime_name: max_score} across all resolved Compounds
    prime_field_bits    int         union PrimeBit of all resolved Compounds
    unresolved_tokens   list[str]   tokens with no Compound match

MEMORY                  [DATA + KNOW write here]
    utterance_id        int | None  permanent ID of the utterance Compound
    concept_ids         list[int]   IDs of all concept Compounds in this scene
    known_symbols       list[str]   symbols retrieved from KNOW (recognised)
    new_symbols         list[str]   symbols crystallised new in this scene
    active_narratives   list[int]   narrative IDs surfaced by KNOW
    validation_flags    dict        {compound_id: {valid: bool, orphan_primes: list}}

AFFECTIVE               [FEEL writes here — Phase 4]
    valence             float       -1.0 to +1.0
    intensity           float       0.0 to 1.0
    emotional_tag       str         dominant emotional quality

MOTIVATIONAL            [WANT / NEED write here — Phase 5]
    goal_relevance      float       0.0 to 1.0
    need_pressure       float       0.0 to 1.0
    active_goal         str         current dominant goal label

RELATIONAL              [SELF writes here]
    attention_decision  str         "conscious" | "archived"
    relationship_quality float      -1.0 → +1.0 from Instance Narrative

EXECUTION               [THINK + SAY write here]
    reasoning_mode      str         routing mode selected by THINK
    intent_id           int | None  ID of the Intent Compound created by THINK
    response_text       str         final text to be expressed by SAY

CLOSE
    closed_at           float | None    unix timestamp when scene is archived or failed
```

The MetaScene is **authoritative in Phase 1**. It is the source of truth for the GUI
Scene panel and for evaluating SymbolicScene quality.

---

### Channel 2: SymbolicScene (native)

An unstructured collection of PLanguage contributions from each prime — Compounds,
Triples, and Narrative fragments in PABLO's own language.

No field labels. No assigned structure. Each prime contributes what it has learned to
contribute. The SymbolicScene is what PABLO will eventually think in.

```python
@dataclass
class SceneContribution:
    prime:              str
    compounds:          list[Compound]
    triples:            list[Triple]
    narrative_fragment: str | None

@dataclass
class SymbolicScene:
    contributions:      list[SceneContribution]
    narrative_thread:   list[int]       # ordered Compound IDs — the scene's story
```

Initially, primes write little or nothing to the SymbolicScene. Over time, as they learn
what is meaningful to contribute, the SymbolicScene grows richer.

---

### The retirement process

The MetaScene and SymbolicScene are compared continuously. For each MetaScene field:
*does the SymbolicScene contain enough information to reconstruct this?*

When yes, that MetaScene field is **retired**:
- Still present in the dataclass but no longer written to
- SymbolicScene contribution becomes authoritative
- GUI Scene panel shows the symbolic form instead

When all MetaScene fields have retired, PABLO thinks entirely in PLanguage. The
MetaScene becomes a debug window rather than the substance of thought.

Phase 1 comparison metric: visual inspection in GUI (coverage, fidelity, expressiveness).

---

## Architecture

### SceneStore

```python
class SceneStore:
    MAX_SCENES = 200    # last 200 scenes kept in memory

    def open(self, source: str, thread_type: str = "unconscious", **kwargs) -> CognitiveScene
    def get(self, scene_id: str) -> CognitiveScene | None
    def recent(self, n: int = 5) -> list[CognitiveScene]
    def by_status(self, status: str) -> list[CognitiveScene]
    def active_unconscious(self) -> list[CognitiveScene]
    def conscious_queue(self) -> list[CognitiveScene]   # foreground first

scene_store = SceneStore()   # module-level singleton
```

Scenes are never deleted during a session. They move from `active` to `archived` or
`failed`. Closed scenes are preserved for session inspection. They are not persisted to
disk — scenes are ephemeral. Compounds and Narratives are what persist.

---

### What each prime writes

#### READ
**MetaScene:** `raw_input`, `preliminary_tokens` (naive whitespace split)
**SymbolicScene:** One observation Compound (the raw experience, no primebit yet).

#### SYMBOL
**MetaScene:** `script`, `language_hint`, `modality`, `preliminary_tokens` (refined segmentation)
**SymbolicScene:** One signal-classification Compound encoding script + dominant language.

#### KNOW
**MetaScene (resolution):** `token_resolutions`, `prime_field`, `prime_field_bits`,
`unresolved_tokens`, `utterance_id`, `concept_ids`, `known_symbols`, `new_symbols`
**MetaScene (cued recall):** `active_narratives`
**SymbolicScene:** Resolved Compounds per token; Narrative fragments from surfaced memories.

#### DATA
**MetaScene:** `validation_flags` (orphan prime flags, advisory only)
**SymbolicScene:** Positional Triples between concepts (AFTER relations encoding word order).

#### SELF
**MetaScene:** `salience`, `attention_decision`, `relationship_quality`; promotes or archives scene
**SymbolicScene:** `(source) -[SELF]→ (salience_compound)`.

#### THINK
**MetaScene:** `reasoning_mode`, `intent_id`, `response_text`; increments `think_cycles`
**SymbolicScene:** Reasoning Triple chain; Intent Compound; Narrative fragment.

#### SAY
**MetaScene:** `closed_at`; sets `status → "archived"`
**SymbolicScene:** Final Narrative fragment — the expressed response as a Compound
sequence, written to KNOW as a new Narrative entry.

---

*See [system.md](system.md) for the theoretical context.*
*See [primes.md](../PRIMES/primes.md) for what each prime is.*
*See [planguage.md](../PLANGUAGE/planguage.md) for the PLanguage units that fill the SymbolicScene.*
*See [narratives.md](../PLANGUAGE/narratives.md) for how scenes accumulate into Narrative threads.*
