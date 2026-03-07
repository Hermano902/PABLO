# READ

---

## Concept

READ is PABLO's linguistic perceptor. It is sensitive to unprocessed external text input —
typed by a user, spoken aloud, visible on screen, present in a file.

READ does not interpret what language means. It detects that language has appeared,
brings it into the system, and opens the CognitiveScene where all other primes will
contribute their perception of it.

READ is the threshold between world and mind for linguistic input.

---

### READ's job ends when the scene opens

READ writes the perception layer and advances the stage to `"symbol"`. That is the
entirety of its contribution. It does not know what primes will do next. It does not
know whether THINK will be activated. It opens the door and steps back.

---

### What READ does not do

READ does not interpret meaning. That is SYMBOL.
READ does not create concept Compounds. That is DATA.
READ does not store anything in KNOW.
READ does not know what SELF will decide.
READ does not call any other prime.

---

## Architecture

### When READ engages

READ is always monitoring its environment. In Phase 1: keyboard and GUI submissions.
When a non-empty, non-duplicate submission arrives, READ opens a CognitiveScene.

### Scene contribution

```
scene.raw_input             str         unprocessed text, exactly as received
scene.modality              str         "text"
scene.preliminary_tokens    list[str]   surface tokenisation (whitespace/punctuation split)
scene.source                str         "keyboard" | "gui" | "file" | "voice"
scene.stage                 →  "symbol"

SymbolicScene contribution:
  prime     = "READ"
  compounds = [Compound(type="observation", symbol=raw_input)]
  triples   = []
  fragment  = None
```

The observation Compound has no primebit assigned yet — SYMBOL will provide that.

### Change detection

READ is a change detector, not a line reader:

- **KEYBOARD / GUI** — a new non-empty submission. Empty presses and duplicates within
  the cooldown window are suppressed.
- **VOICE** *(Phase 6)* — a complete utterance, silence-delimited. Background noise
  does not trigger.
- **FILE** *(Phase 6)* — new bytes appended beyond the last-known file position.
- **SCREEN** *(Phase 6)* — text content change in a monitored screen region.

A static world produces zero scenes from READ.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | KEYBOARD and GUI text submissions |
| 6 | VOICE, FILE, SCREEN sources |

---

*See [perceptors.md](perceptors.md) for the perceptor family READ belongs to.*
*See [symbol.md](../symbol.md) for what happens next in the scene.*
*See [cognitive_scene.md](../../SYSTEM/cognitive_scene.md) for the full scene lifecycle.*
