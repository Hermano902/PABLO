# Pablo Language Stack — Roadmap (GCP / 8·8·8)

**Status:** Draft v0.1 • **Profile:** Writing (extensible to Math / Code / Geo) • **Last updated:** 2025-08-24

---

## 0) North Star

Human-like text understanding with tight memory: **don’t store instance graphs by default**. Persist only:
- **GCP** (Graph Construction Program: rules + small scorers),
- **Rule Library** (pattern→action, with guards),
- **Tiny retrieval** (64-byte thumbnail per graph),
- **Optional** facts/triples + small exemplar buffer for learning/drift.

Runtime = text → build explicit RAM graph (**8·8·8 schema**) → reason/answer → free; persist only thumbnails/facts/exemplars if flagged.

**Operating principles:** rules as mentors (not cages); anytime planning; provenance everywhere; side-effect-free runtime; append-only persistence.

---

## 1) Primer: Writing as Signal (what Pablo is decoding)

**Writing** transmits thought via **words + punctuation + formatting**.
- **Punctuation** is evidence (e.g., `?` ⇒ interrogative force).  
- **Formatting/orthography** (caps/spacing/paragraphs) are advisory but informative.  
- **Decoding** = reconstruct intent with explicit reasons (which symbols, which conventions).

_This primer sets expectations for tokenization, sentence force, and boundary cues in Milestones M2–M4._

---

## 2) Core Model — 8·8·8 (compact)

### Node(8)
`node_id varint | n_type u8 | sub_type u8 | features_ref varint | span tuple-varint | flags u16 | confidence u8 | label_id varint`

### Edge(8)
`src varint | dst varint | e_type u8 | weight u8 | time varint | flags u16 | confidence u8 | attr_ref varint`

### Graph(8)
`graph_id varint/64-bit | graph_type u8 | num_nodes varint | num_edges varint | g_features [64|128] int8? | source_id varint | version varint | schema_id u8`

**Enums (seed):**  
`n_type`: Token=1, Entity=2, Predicate=3, Event=4, Phrase=5, EDU=6, DiscourseRel=7, Negation=8, Modality=9, Quantifier=10, …  
`e_type`: DEP=1, ROLE=2, COREF=3, DISCOURSE=4, SCOPES_OVER=5, NEXT=9, PUNCT=10, ARG_OF=11, …

_All strings are dictionary-encoded; registries live in a tiny shared file._

---

## 3) Storage & Retrieval

- **Varints** (base-128), zigzag for signed.  
- **`.pgraph` blocks:** header (PGRA, version, count, offsets[]) + per-graph payload (Graph(8) + node/edge tables + adjuncts).  
- **Compression:** zstd at block level.  
- **Trees:** LOUDS (~2·n bits) + dep_label array.  
- **General sparse edges:** CSR (row_ptr, col_idx deltas, etype/attr/flags/weight).  
- **Vocab store:** `vocab.bin/idx` (mmap) for lemmas/forms (O(1) slice).  
- **Retrieval:** 64D (or 128D) int8 thumbnail per graph + ANN (HNSW / IVF-PQ). Retrieve→rank→(optional) read full.

---

## 4) Rule Library & Execution

**Rule =** variables + guards + actions + scores (+ micro tests).
- **Phases (priority):** `syntax → semantics → discourse → scope`.  
- **Actions:** add/remove node/edge, set flags/labels, attach `derived_by: rule_id`.  
- **Scores:** support, precision, coverage, MDL.

**Worked examples (seed rules):**
- **Because → CAUSE (discourse)**
- **Modality “should” → SCOPES_OVER predicate (scope)**
- **DET→NOUN agreement (syntax)**

(Exact JSON sketches included later in §9 “Ready Samples”.)

---

## 5) Runtime Pipeline (writing profile)

1) **Tokenize + Morph** (FST/lexicon): form → lemma + morph bits (16–24).  
2) **Syntax**: DEP edges (arc-eager or MST; `root.is_root=1`). Optional Phrase nodes.  
3) **Semantics (SRL/Frames)**: mark Predicates; `ROLE(pred→ARGk)`.  
4) **Coref & Entities**: NER + pronominal coref; Entity nodes; `MENTIONS`, `COREF`.  
5) **Discourse & Scope**: EDUs; DiscourseRel (CAUSE/CONTRAST/ELAB); Negation/Modality/Quantifier with `SCOPES_OVER`.  
6) **World linking (optional)**: `SAME_AS(entity→KG_Entity)`.  
7) **Readout/Reasoning**: small hetero-GNN scorer (int8); optional planner.  
8) **Persist**: thumbnail (64B); selected facts; exemplars if flagged.

---

## 6) Roadmap (Milestones & Exit Criteria)

### M0 — Foundations & Registries
**Deliver:** enums/flags registry; schema IDs; tiny vocab scaffolding; Writing primer documented.  
**Exit:** registries load via mmap; forward-compat policy written.

### M1 — Graph Library (RAM + Codec)
**Deliver:** `GraphBuilder`, LOUDS/CSR helpers, `encode_pgraph`/`decode_pgraph`.  
**Tests:** golden round-trip (byte-exact), fuzz for varints.  
**Exit:** ≤1.5 KB typical per sentence in RAM; codec passes golden.

### M2 — Tokenization & Signal Cues
**Deliver:** tokenizer with lossless policy; minimal flags (cap/numlike/punct); sentence-force cues (`.?!;` + quotes/paren handling).  
**Tests:** tokenization ≥98% on seed; force heuristics sanity.  
**Exit:** stable token stream + boundary candidates + proofs (what cues fired).

### M3 — Morph & Lemma
**Deliver:** FST/lexicon path; morph bits pack; `label_id` = lemma_id.  
**Tests:** lemma accuracy on seed; morph packing round-trip.  
**Exit:** morph available to rules; OOV heuristics in place.

### M4 — Syntax (DEP)
**Deliver:** transition or MST parser; dep_labels in `attr_ref`; `PUNCT` edges optional.  
**Tests:** UAS/LAS on seed; `explain(head→dep)` returns rules/weights.  
**Exit:** ≥ target accuracy (set internally) with deterministic proofs.

### M5 — Semantics (Predicates & Roles)
**Deliver:** predicate finder; frame table; `ROLE` edges.  
**Tests:** role F1 on seed; justification per role edge.  
**Exit:** basic SRL working with explanations.

### M6 — Coref & Entities
**Deliver:** NER + pronominal coref; Entity nodes; `MENTIONS`/`COREF`.  
**Tests:** MUC/B³/CEAF (seed); entity typing sanity.  
**Exit:** coref graph stable; proofs logged.

### M7 — Discourse & Scope
**Deliver:** EDU splitter; DiscourseRel nodes (CAUSE/CONTRAST/ELAB); Negation/Modality/Quantifier with `SCOPES_OVER`.  
**Tests:** rule micro-suites; curated examples.  
**Exit:** end-to-end explanations show discourse links & scope.

### M8 — Retrieval & Facts
**Deliver:** 64D int8 thumbnails; ANN index; fact extractor (triples 12–24 B ea).  
**Tests:** retrieve-then-read latency; precision@k on recall tasks.  
**Exit:** retrieval online; storage budget respected.

### M9 — Learning Loop (Rule Mining)
**Deliver:** instance buffer; structured miner + neural proposer; verifier; MDL scorer; promotion/pruning; replay buffer.  
**Tests:** offline A/B on held-out; drift detection triggers demotion.  
**Exit:** rule evolution pipeline gated by precision/coverage thresholds.

---

## 7) Engineering Budgets (targets)

- **Latency (CPU):** token+morph 50–200 µs; syntax 0.5–2 ms; SRL 0.5–2 ms; coref/discourse/scope 0.5–3 ms; GNN 0.2–1 ms → **<10 ms/sentence** typical.  
- **RAM per sentence graph:** ~0.5–1.5 KB.  
- **Persisted defaults:** 0 B; +64 B thumbnail; +few triples if chosen.  
- **Rule library:** few MB (thousands of rules).  
- **ANN (millions):** 1–2 GB.  
- **Exemplars cap:** ≤5% stored; ≤ few GB.

---

## 8) APIs (to implement across milestones)

```python
# Graph
class GraphBuilder: ...
def encode_pgraph(g) -> bytes: ...
def decode_pgraph(buf: bytes) -> Graph: ...

# Rules
class RuleEngine:
    def apply(self, g: Graph, phase: str) -> None: ...
    def justify(self, g: Graph, edge_id: int, rule_id: int) -> None: ...

# Pipeline (writing)
def process_sentence(text: str) -> Result: ...
