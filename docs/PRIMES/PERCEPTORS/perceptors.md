# Perceptors

---

## Concept

Perceptors are PABLO's sensory entry points. They are the primes that face the world
directly — detecting meaningful change in the environment and opening a CognitiveScene
for each new experience.

Three perceptors exist:

| Prime | Modality | Phase |
|-------|----------|-------|
| READ | Text and linguistic input | 1 (active) |
| SEE | Visual input | 6 |
| HEAR | Auditory input | 6 |

In Phase 1, only READ is active. SEE and HEAR are dormant stubs.

---

### Change detection, not continuous ingestion

Perceptors are change detectors. They emit a scene only when something meaningfully new
has appeared in their modality. A static environment produces zero scenes.

This mirrors biological perception: the visual system responds to motion and change, not
to static fields. The auditory system responds to sound events, not to silence.

The principle prevents PABLO from being overwhelmed by redundant observations. Only
semantically relevant transitions enter the system.

---

### Perceptors are the threshold between world and mind

A perceptor's job ends the moment it opens a scene. It writes the perception layer —
raw signal, modality, surface tokens, source — then yields. Everything after that is
SYMBOL's work: finding out what the signal means.

Perceptors do not interpret. They detect and deliver.

---

### What perceptors do not do

Perceptors do not assign primes to what they detect. That is SYMBOL.
Perceptors do not create concept Compounds. That is DATA.
Perceptors do not store anything in KNOW.
Perceptors do not know what SELF will decide about the scene they opened.
Perceptors do not call each other or any other prime.

---

## Architecture

### Autonomous mode vs consultation mode

**Autonomous** — perceptors run continuously in the background, sampling their modality
and emitting a scene whenever a meaningful change is detected. This is the normal mode.

**Consultation** — a prime (typically THINK) invokes a perceptor directly to request
a focused perception of the current environment. The perceptor returns a scene
contribution immediately, bypassing change detection.

### Change detection by modality

**READ** — a new non-empty user submission. Duplicate submissions within a cooldown
window are suppressed.

**SEE** *(Phase 6)* — tracks a lightweight model of the visual scene. Emits an event
when an object appears, disappears, or changes semantic state (stationary → moving).
A static scene produces no observations.

**HEAR** *(Phase 6)* — listens for sound events (voice onset, distinct sound). Emits
an event when such an event occurs. Continuous silence produces no observations.

### Flood protection

Perceptors track recently emitted events and suppress near-duplicates within a short
time window. This prevents a burst of identical observations from flooding the pipeline
when the environment changes rapidly but redundantly.

### Scene contribution format

All perceptors write the same perception layer structure regardless of modality:

```
scene.raw_input             str         unprocessed signal as received
scene.modality              str         "text" | "voice" | "image" | "audio"
scene.preliminary_tokens    list[str]   surface decomposition before interpretation
scene.source                str         "keyboard" | "gui" | "voice" | "screen" | "file"
scene.stage                 →  "symbol"
```

Downstream primes read the scene; they do not need to know which perceptor opened it.

---

*See [read.md](read.md) for the Phase 1 active perceptor.*
*See [symbol.md](../symbol.md) for what SYMBOL does with the perception layer.*
*See [cognitive_scene.md](../../SYSTEM/cognitive_scene.md) for the full scene lifecycle.*
