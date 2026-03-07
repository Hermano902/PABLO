# SYMBOL

---

## Concept

SYMBOL is the signal classifier. It is the first actor to step onto the stage after a
perceptor (READ, SEE, HEAR) has deposited raw signal into the scene.

SYMBOL's question is not *what does this mean?* That is KNOW's job. SYMBOL's question is:

> *What kind of signal is this, and how should it be segmented?*

Text in Latin script, text in Cyrillic, romanised Chinese, an image, a sound file —
each requires a different interpreter downstream. SYMBOL determines which interpreter
is needed by classifying the signal's script, language, and modality. It then segments
the signal into the appropriate surface units (tokens, regions, frames) and places them
on the stage for KNOW to read.

SYMBOL is the bridge between raw sensation and interpretable units. Without SYMBOL,
the scene has signal but no structure.

---

### The script/language split

SYMBOL produces two independent classifications:

**Script** — derived from Unicode block analysis. Exact and deterministic. A string of
Cyrillic characters is unambiguously Cyrillic regardless of meaning.

**Language** — derived from statistical n-gram analysis (Phase 1: `lingua` library;
Phase N: PABLO's own learned model). Probabilistic, not exact. Romanised Chinese
(`nǐ hǎo`) has Latin script but Chinese language distribution. SYMBOL reports a
confidence-weighted language distribution, not a single label.

The downstream implication: KNOW uses `language_hint` to select the right compound
store to search. A Cyrillic token maps to different compounds than a Latin token even
if the romanisation looks the same.

---

### SYMBOL is a tenured actor

SYMBOL is present in every scene without exception. Every perceptor intake passes
through SYMBOL. There is no scene in which signal arrives and classification is not
attempted. SYMBOL always steps onto the stage.

---

### What SYMBOL does not do

SYMBOL does not resolve tokens to meanings. That is KNOW.
SYMBOL does not create Compounds. That is KNOW (and DATA validates them).
SYMBOL does not decide what an utterance means at the level of intent. That is THINK.
SYMBOL does not gate attention. That is SELF.
SYMBOL never calls another prime. It classifies, segments, and steps back.

---

## Architecture

### When SYMBOL engages

SYMBOL is sensitive to scenes with `raw_input` present but no `script` classification
yet. As soon as READ deposits raw signal, SYMBOL's cue is met.

### Classification pipeline (Phase 1 — text)

```
raw_input
  │
  ├─ unicodedata block analysis
  │     → script: "latin" | "cyrillic" | "arabic" | "cjk" | "devanagari" | "mixed" | ...
  │
  ├─ lingua language detector
  │     → language_hint: {"en": 0.92, "de": 0.05, ...}   (top-3 by confidence)
  │
  └─ script-appropriate tokeniser
        latin/cyrillic  → whitespace + punctuation split
        cjk             → character-level segments (Phase 6: jieba)
        arabic          → whitespace split, right-to-left aware
        mixed           → segment by script run, then apply per-run tokeniser
        → surface_tokens: list[str]
```

### Scene writes

```
scene.script           str          dominant Unicode block: "latin", "cyrillic", etc.
scene.language_hint    dict         {ISO-639 code: confidence}  e.g. {"en": 0.92}
scene.preliminary_tokens  list[str] surface tokens, script-appropriate segmentation
scene.modality         str          confirmed or refined: "text" | "image" | "audio"
```

`preliminary_tokens` replaces READ's naive whitespace split when SYMBOL's segmentation
is more appropriate. READ's split is used as a fallback if SYMBOL has not yet acted.

### SymbolicScene contribution

SYMBOL contributes one signal-classification Compound to the SymbolicScene:

```
Compound(type="internal", symbol=script+":"+dominant_language, primebit=SYMBOL bit)
```

This is a thin marker — it records what SYMBOL observed about the signal's nature,
not its meaning.

### Phase scope

| Phase | Capability |
|-------|-----------|
| 1 | Unicode block → script classification |
| 1 | `lingua` → language distribution |
| 1 | Latin/Cyrillic/Arabic/CJK tokenisation routing |
| 6 | Image modality classification (SEE perceptor) |
| 6 | Audio modality classification (HEAR perceptor) |
| N | Self-learned language model replaces `lingua` |

---

*See [cognitive_scene.md](../../SYSTEM/cognitive_scene.md) for the scene layers SYMBOL reads and writes.*
*See [know.md](know.md) for what KNOW does with SYMBOL's surface tokens.*
*See [read.md](PERCEPTORS/read.md) for what READ deposits before SYMBOL acts.*
