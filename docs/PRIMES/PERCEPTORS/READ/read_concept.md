# READ — Concept

*PABLO's linguistic perceptor. The first prime to touch the world.*

---

## Nature

READ is sensitive to **unprocessed external input**. When text appears in PABLO's
environment — typed by a user, spoken aloud, visible on screen, present in a file —
READ is the first prime to respond.

READ does not interpret what language means. It detects that language has appeared,
brings it into the system, and opens the CognitiveScene where all other primes will
contribute their perception of it.

READ is the threshold between world and mind.

---

## What READ Does

When input arrives, READ:

1. **Opens a CognitiveScene** — the shared workspace for this experience
2. **Writes the perception layer** of the scene:
   - `raw_input` — the unprocessed text, exactly as received
   - `modality` — how it arrived (`"text"`, `"voice"`, `"image"`)
   - `preliminary_tokens` — surface tokenisation (split on whitespace/punctuation)
   - `source` — where it came from (`"keyboard"`, `"gui"`, `"file"`, `"voice"`)
3. **Advances the scene stage** to `"symbol"` — signalling SYMBOL to contribute
4. **Contributes to the SymbolicScene** — a single Compound representing the raw
   experience before any interpretation. Type: `observation`. No PrimeBit assigned yet.

READ then steps back. The scene is now SYMBOL's to perceive.

---

## What READ Senses

**KEYBOARD / GUI** — text typed by the user and submitted via the interface.
This is the only active source in Phase 1.

**VOICE** — spoken input, transcribed to text before READ receives it. Phase 6.

**SCREEN** — text visible in a monitored screen region. Dormant until Phase 6.

**FILE** — new content appended to a watched file. Dormant until Phase 6.

All sources share the same scene contribution: READ writes the same perception layer
fields regardless of modality. Downstream primes do not need to know where input came from —
they read the scene.

---

## Change Detection

READ is a **change detector**, not a line reader. It emits a scene only when something
meaningfully new has appeared:

- KEYBOARD: a new non-empty submission. Empty presses and duplicate submissions within
  the cooldown window are suppressed.
- VOICE: a complete utterance (silence-delimited). Background noise does not trigger.
- FILE: new bytes appended beyond the last-known position.

A static world produces zero scenes. READ is silent when nothing changes.

---

## The Scene READ Opens

```
scene.raw_input          = "the cat moved left"
scene.modality           = "text"
scene.preliminary_tokens = ["the", "cat", "moved", "left"]
scene.source             = "keyboard"
scene.stage              = "symbol"

scene.symbolic.contributions += SceneContribution(
    prime    = "READ",
    compounds = [Compound(type="observation", symbol="the cat moved left")],
    triples   = [],
    fragment  = None
)
```

This is all READ writes. It does not interpret tokens. It does not know what primes
are in the input. It does not know SYMBOL exists.

---

## What READ Does NOT Do

READ does not interpret meaning. That is SYMBOL.
READ does not create concept Compounds. That is DATA.
READ does not store anything in KNOW.
READ does not know whether THINK will be activated. That is SELF's decision.
READ does not know what other primes will do with the scene it opened.

READ's contract is simple: when the world speaks, READ listens and opens the door.

---

## Phase Scope

| Phase | Capability |
|-------|-----------|
| 1 | KEYBOARD / GUI text input → scene perception layer |
| 6 | VOICE, SCREEN, FILE sources |

Phase 1 READ is minimal and correct: it handles the one active source, opens the scene,
writes the perception layer, and yields to SYMBOL.

---

*See `docs/SYSTEM/cognitive_scene.md` for the scene READ opens.*
*See `docs/PRIMES/SYMBOL/symbol_concept.md` for what SYMBOL does next.*
