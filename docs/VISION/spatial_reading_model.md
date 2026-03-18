# Spatial Reading Model — Side Implementation Spec

## Core Idea

PABLO's reading is not text parsing. It is seeing.

The same primal `SEE` function, tuned by context, handles any external data that
has a spatial or sequential form. Text parsing is a degenerate case of this model,
not a separate system.

---

## The Universal Function

```
SEE(input, context)
  → open spatial field
  → sample region → detect script / encoding type
  → set reading parameters {anchor, primary_axis, secondary_axis, resolution}
  → traverse field with perceptual focus
  → at each step: match curves/edges against context glyph library
  → lift matches into scene as symbol candidates
  → compounds activate from symbol sequence
```

The function never changes. Context and field geometry are the only variables.

---

## Reading Parameters by Script

| Script       | Anchor      | Primary Axis | Secondary Axis |
|--------------|-------------|--------------|----------------|
| Latin        | top-left    | LEFT → RIGHT | top → bottom   |
| Arabic       | top-right   | RIGHT → LEFT | top → bottom   |
| Hebrew       | top-right   | RIGHT → LEFT | top → bottom   |
| Traditional Chinese / Japanese | top-right | TOP → BOTTOM | right → left |
| Simplified Chinese / Japanese (modern) | top-left | LEFT → RIGHT | top → bottom |
| Braille      | top-left    | LEFT → RIGHT | top → bottom   |

Reading direction is not hardcoded. It is resolved at runtime from script detection.

---

## Script Detection

Script detection happens before full traversal but requires some visual sampling.

Resolution:
1. Sample a small region of the field (not the full image)
2. Detect curve family from stroke characteristics:
   - Arabic: connected cursive strokes, diacritics above/below baseline
   - Latin: discrete upright strokes, consistent baseline
   - Hanzi: high stroke density, square bounding regions
3. Set reading parameters from detected script
4. Begin full traversal with anchor and direction established

This is not a circular dependency — it is a two-pass approach:
small sample → set direction → full traversal.

---

## Glyph Detection vs. Text Parsing

```
Text parsing:      image → string (by OCR) → parse string
Spatial reading:   image → spatial field → curve/edge detection → glyph candidates
                         → compound activation → meaning
```

In spatial reading, PABLO never receives a string. He detects shapes in space and
activates meaning from those shapes directly, the same way a human reader does.

The text parsing case is what happens when the spatial field is already 1D
(a plain string). The traversal collapses to a linear scan. The underlying
machinery is identical.

---

## MOVE Grounding in This Model

`MOVE` is grounded through translation of the perceptual focus window in 2D space.

```
MOVE(focus, direction, step_size)
  → focus.position += direction * step_size
  → return new field region under focus
```

This is the most concrete grounding of `MOVE` in the architecture. It is literally
moving attention through coordinate space. The same prime grounds metaphorical
movement (traversing memory, shifting reasoning state) but spatial reading is the
base case.

---

## Handwritten Text

Handwriting uses the same function. The only difference is the glyph library:

- Printed: exact curve templates, tight matching threshold
- Handwritten: curve families with tolerance, matched by structural similarity not
  exact shape

Direction, anchor, and traversal are identical to printed script of the same type.
A handwritten Arabic note is read right-to-left with the same traversal as printed
Arabic. The glyph library absorbs the variance; the function does not change.

---

## Input Surface Coverage

| Input Form        | Field Type      | Context Tuning                          |
|-------------------|-----------------|-----------------------------------------|
| Printed text      | 2D image        | script detection → standard glyph set  |
| Handwritten text  | 2D image        | script detection → loose glyph set     |
| Plain string      | 1D sequence     | trivial traversal, no spatial detection |
| Barcode / QR      | 2D image        | binary pattern library, fixed scan     |
| Musical score     | 2D image        | staff-relative spatial, note library   |
| Braille           | 2D tactile grid | L→R traversal, 6-dot cell library      |
| Audio spectrogram | 2D time-freq    | L→R time axis, frequency pattern lib   |

The same primal machinery applies to all of these. Context supplies the vocabulary.
The field supplies the geometry. `SEE` does the rest.

---

## Relation to Core Architecture

This is a side implementation. It does not modify the prime floor or the scene model.

Connection points:
- Uses `SEE` as defined in the core architecture (left general intentionally)
- Uses `MOVE` for perceptual focus traversal
- Outputs symbol sequences that feed into compound activation (standard pipeline)
- The spatial field is a specialization of the scene's spatial layer

When this module is integrated, `SEE` gains a concrete implementation for visual
input. The core architecture requires no changes.

---

## Status

Idea captured. Not yet implemented.
Next step when ready: prototype curve/edge detection against a small glyph library
for Latin printed text, then extend to Arabic as the RTL test case.
