# Activation Cloud — Architecture & Implementation

This file is the canonical implementation reference for `core/activation.py`.
It is phase-separated: Phase 1 is the complete implementable target. Phase 2+
sections are preserved for future reference and must not be implemented until
the relevant phase begins.

See `activation_cloud_concept.md` for the conceptual contract. Implement against both.

---

## PHASE 1 — Implement Now

---

### 1. Scope & Purpose

The Activation Cloud is a transient context structure assembled once per token
during the router's resolution cascade. It gathers everything PABLO already knows
that is relevant to the current token, and serialises it into a rich prompt for
the LLM specialist.

`core/activation.py` implements:
- `ActivationCloud` dataclass — the cloud structure
- `build_activation_cloud()` — the assembly function
- `serialise_cloud()` — converts the cloud to an LLM prompt section

Phase 1 implements the cognitive layer only. Affective, motivational, and
relational layers are structurally present (dormant None fields) but not populated.

Dependencies:
- `core.compound.Compound` — compound references in the cloud
- `core.primebit.PrimeBit`, `PRIME_INDEX` — prime name resolution
- `core.lemmatizer` — already called by router before cloud assembly
- KNOW singleton (lazy import) — compound lookups

No imports from any prime module except through lazy KNOW access.

---

### 2. ActivationCloud Dataclass

```python
# core/activation.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.compound import Compound


@dataclass
class ActivationCloud:
    """
    Transient pre-activation context for a single token.

    Built by the router before calling the LLM specialist. Contains
    everything PABLO already knows that is relevant to this token
    in its current context. Not stored, not serialised to disk.

    Phase 1: cognitive layer only.
    Phase 2+: affective, motivational, relational layers activate.
    """

    # ── Identity ──────────────────────────────────────────────────────
    token:       str            # surface form being resolved
    position:    int            # 0-based index in the utterance
    lemma:       str | None     # spaCy lemma (if available)
    pos:         str | None     # spaCy POS tag

    # ── Cognitive layer (Phase 1 — active) ────────────────────────────
    exact_match:          Compound | None    = None
    # The existing compound for this exact surface form, if in KNOW.
    # None: token not yet known to PABLO → specialist must create it.
    # Polysemy is not PABLO's concern. PABLO reasons in prime-space.
    # Two senses of "bank" are TWO compounds with different primebits.
    # The activation cloud's prime_candidates + narrative context
    # naturally selects the correct compound without explicit disambiguation.
    family_root:          Compound | None    = None
    definition_compounds: list[Compound]     = field(default_factory=list)
    utterance_context:    list[Compound]     = field(default_factory=list)
    narrative_context:    list[Compound]     = field(default_factory=list)
    prime_candidates:     dict[str, float]   = field(default_factory=dict)
    # prime_candidates maps prime_name → activation weight (0.0–1.0)
    # Aggregated from all compounds in the cloud
    fast_path:            bool               = False
    # True if exact_match.confidence >= FAST_PATH_EXACT_THRESHOLD.
    # When True: router skips LLM specialist call for this token.

    # ── Affective layer (Phase 2 — dormant) ───────────────────────────
    affective_valence:   float | None = None   # FEEL: -1.0 bad ↔ 1.0 good
    affective_intensity: float | None = None   # FEEL: 0.0 calm ↔ 1.0 strong

    # ── Motivational layer (Phase 3 — dormant) ────────────────────────
    goal_relevance:      float | None = None   # WANT: 0.0 irrelevant ↔ 1.0 central
    need_pressure:       float | None = None   # NEED: 0.0 none ↔ 1.0 urgent

    # ── Relational layer (Phase 4 — dormant) ──────────────────────────
    source_salience:     float | None = None   # SELF: relationship history weight
    narrative_status:    str | None   = None   # SELF: "continuing"|"new"|"closing"
```

**Fields deliberately absent:**

- `score` — the cloud is not a resolution result. Score comes from the LLM after
  reading the cloud.
- `method` — same reason. The cloud is input, not output.
- `compound_id` — the cloud does not commit to a single compound. Resolution
  follows after the cloud is consumed.

**exact_match vs None:**

`exact_match` is either the single existing compound for this symbol or None.
There is no multi-sense list. If two English words share a surface form but have
different meanings (e.g. "bank" financial vs geographic), they are stored as two
separate compounds in KNOW with distinct symbols — e.g. `"bank_fin"` and `"bank_geo"`,
or simply distinguished by the compound that arrives first and the second being encoded
differently. Either way, prime-space reasoning naturally selects the right compound
from context. PABLO does not need explicit disambiguation machinery.

**fast_path flag:**

`fast_path = True` when `exact_match.confidence >= FAST_PATH_EXACT_THRESHOLD`.
When the router sees `cloud.fast_path == True`, it skips the LLM specialist call
and resolves directly from `exact_match`. This is the compound deduplication path.

**prime_candidates as weighted dict:**

`prime_candidates` is a `dict[str, float]` rather than a `list[str]` because
different sources contribute different activation weights. An exact match's primes
carry weight 1.0. Utterance context primes carry 0.5. Narrative context primes
carry 0.3. Definition compound primes carry 0.6. When the same prime appears from
multiple sources, the maximum weight is kept.

---

### 3. Activation Weight Constants

```python
# Weights for different activation sources when building prime_candidates
WEIGHT_EXACT_MATCH         = 1.0    # the token already exists in KNOW
WEIGHT_FAMILY_ROOT         = 0.9    # root compound of an inflected form
WEIGHT_DEFINITION          = 0.6    # primes from dictionary definition compounds
WEIGHT_UTTERANCE           = 0.5    # primes from already-resolved sibling tokens
WEIGHT_NARRATIVE           = 0.3    # primes from recent narrative context
FAST_PATH_EXACT_THRESHOLD  = 0.8    # exact_match.confidence >= this → skip LLM call
```

These weights are not confidence scores. They represent how strongly a prime
should "light up" in the activation field based on its source. The LLM sees
the weighted primes and uses the pattern to guide its decision.

---

### 4. Building the Cloud

```python
def build_activation_cloud(
    token:             str,
    position:          int,
    lemma:             str | None,
    pos:               str | None,
    utterance_so_far:  list[Compound],
    active_narrative:  list[Compound] | None = None,
) -> ActivationCloud:
    """
    Assemble an ActivationCloud for a single token.

    Called by the router after spaCy analysis but before the specialist step.
    All KNOW lookups are read-only. This function never writes to KNOW.

    Args:
        token:            surface form of the token
        position:         0-based index in the utterance
        lemma:            spaCy lemma (may equal token for base forms)
        pos:              spaCy POS tag ("NOUN", "VERB", "ADJ", etc.)
        utterance_so_far: compounds already resolved for preceding tokens
        active_narrative: recent compounds from the active narrative thread
                          (None if no narrative is active)

    Returns:
        Populated ActivationCloud (Phase 1 cognitive layer).
    """
```

**Implementation steps:**

```python
    from primes.KNOW import know  # lazy import

    cloud = ActivationCloud(
        token=token,
        position=position,
        lemma=lemma,
        pos=pos,
    )

    # ── 1. Exact match (single compound for this symbol) ───────
    cloud.exact_match = know.by_symbol(token)
    if cloud.exact_match is None and token != token.lower():
        cloud.exact_match = know.by_symbol(token.lower())

    # ── 1b. Fast path check ──────────────────────────────────────
    if (cloud.exact_match is not None
            and cloud.exact_match.confidence >= FAST_PATH_EXACT_THRESHOLD):
        cloud.fast_path = True

    # ── 2. Family root (if inflected) ────────────────────────────────
    if lemma and lemma != token.lower():
        cloud.family_root = know.by_symbol(lemma)

    # ── 3. Definition compounds ──────────────────────────────────────
    # Use exact_match (or family_root) to find definition compounds.
    lookup_compound = cloud.exact_match or cloud.family_root
    if lookup_compound is not None and lookup_compound.nested:
        for nested_id in lookup_compound.nested[:10]:  # cap at 10
            nested = know.by_id(nested_id)
            if nested is not None:
                cloud.definition_compounds.append(nested)

    # ── 4. Utterance context ─────────────────────────────────────────
    cloud.utterance_context = list(utterance_so_far)

    # ── 5. Narrative context ─────────────────────────────────────────
    if active_narrative:
        cloud.narrative_context = list(active_narrative[-5:])  # last 5

    # ── 6. Assemble prime_candidates ─────────────────────────────────
    cloud.prime_candidates = _aggregate_primes(cloud)

    return cloud
```

---

### 5. Prime Aggregation

```python
def _aggregate_primes(cloud: ActivationCloud) -> dict[str, float]:
    """
    Walk all compounds in the cloud and collect prime activations
    with weight-by-source.

    Returns dict mapping prime_name → max activation weight.
    """
    activations: dict[str, float] = {}

    def _add(compound: Compound | None, weight: float):
        if compound is None:
            return
        for name in compound.primebit.get_prime_names():
            if name not in activations or activations[name] < weight:
                activations[name] = weight

    # Exact match — strongest signal
    _add(cloud.exact_match, WEIGHT_EXACT_MATCH)

    # Family root
    _add(cloud.family_root, WEIGHT_FAMILY_ROOT)

    # Definition compounds
    for c in cloud.definition_compounds:
        _add(c, WEIGHT_DEFINITION)

    # Utterance context
    for c in cloud.utterance_context:
        _add(c, WEIGHT_UTTERANCE)

    # Narrative context
    for c in cloud.narrative_context:
        _add(c, WEIGHT_NARRATIVE)

    return activations
```

Prime aggregation uses max-wins semantics: if "ENTITY" appears in both a
definition compound (weight 0.6) and an exact match (weight 1.0), the
activation is 1.0. This prevents double-counting while preserving the
strongest signal.

---

### 6. Cloud Serialisation for LLM Prompt

The cloud must be converted to a string that the specialist LLM receives
as part of its prompt. This replaces the current bare-token prompt.

```python
def serialise_cloud(cloud: ActivationCloud) -> str:
    """
    Convert an ActivationCloud to a human-readable string for inclusion
    in the LLM specialist's prompt context.

    Sections with no data are omitted entirely. Phase 2–4 sections only
    appear when their fields are not None.
    """
    lines: list[str] = []

    lines.append(f'Token: "{cloud.token}"')
    lines.append(f"Position: {cloud.position}")
    if cloud.lemma and cloud.lemma != cloud.token.lower():
        lines.append(f"Lemma: {cloud.lemma}")
    if cloud.pos:
        lines.append(f"POS: {cloud.pos}")
    lines.append("")

    # ── Exact match ────────────────────────────────────────────
    if cloud.exact_match:
        primes = cloud.exact_match.primebit.get_prime_names()
        lines.append(f"Already known in PABLO:")
        lines.append(f"  {cloud.exact_match.symbol} → {', '.join(primes) or 'ungrounded'}")
        lines.append(f"  confidence: {cloud.exact_match.confidence}"
                     + (" [FAST PATH]" if cloud.fast_path else ""))
        lines.append("")
    else:
        lines.append("Already known in PABLO: None")
        lines.append("")

    # ── Family root ──────────────────────────────────────────────────
    if cloud.family_root:
        primes = cloud.family_root.primebit.get_prime_names()
        lines.append(f"Root form ({cloud.family_root.symbol}):")
        lines.append(f"  primes: {', '.join(primes) or 'ungrounded'}")
        lines.append("")

    # ── Definition context ───────────────────────────────────────────
    if cloud.definition_compounds:
        lines.append("Definition context (from PABLO's dictionary):")
        for c in cloud.definition_compounds:
            primes = c.primebit.get_prime_names()
            lines.append(f"  {c.symbol} → {', '.join(primes) or '?'}")
        lines.append("")

    # ── Utterance context ────────────────────────────────────────────
    if cloud.utterance_context:
        lines.append("Utterance context (tokens already resolved):")
        for c in cloud.utterance_context:
            primes = c.primebit.get_prime_names()
            lines.append(f"  \"{c.symbol}\" → {', '.join(primes) or 'unresolved'}")
        lines.append("")

    # ── Narrative context ────────────────────────────────────────────
    if cloud.narrative_context:
        lines.append("Narrative context (recent compounds):")
        for c in cloud.narrative_context:
            primes = c.primebit.get_prime_names()
            lines.append(f"  \"{c.symbol}\" → {', '.join(primes) or '?'}")
        lines.append("")

    # ── Prime activation field ───────────────────────────────────────
    if cloud.prime_candidates:
        sorted_primes = sorted(cloud.prime_candidates.items(),
                               key=lambda x: x[1], reverse=True)
        top = sorted_primes[:10]  # show top 10
        lines.append("Primes already activated by context:")
        lines.append("  " + ", ".join(f"{p} ({w:.1f})" for p, w in top))
        lines.append("")

    # ── Phase 2: Affective layer ─────────────────────────────────────
    if cloud.affective_valence is not None:
        label = "positive" if cloud.affective_valence > 0 else "negative" if cloud.affective_valence < 0 else "neutral"
        lines.append(f"Affective context: {label} "
                      f"(valence={cloud.affective_valence:.2f}, "
                      f"intensity={cloud.affective_intensity or 0:.2f})")
        lines.append("")

    # ── Phase 3: Motivational layer ──────────────────────────────────
    if cloud.goal_relevance is not None:
        lines.append(f"Goal relevance: {cloud.goal_relevance:.2f}")
    if cloud.need_pressure is not None:
        lines.append(f"Need pressure: {cloud.need_pressure:.2f}")
    if cloud.goal_relevance is not None or cloud.need_pressure is not None:
        lines.append("")

    # ── Phase 4: Relational layer ────────────────────────────────────
    if cloud.source_salience is not None:
        lines.append(f"Source salience: {cloud.source_salience:.2f}")
    if cloud.narrative_status is not None:
        lines.append(f"Narrative status: {cloud.narrative_status}")
    if cloud.source_salience is not None or cloud.narrative_status is not None:
        lines.append("")

    return "\n".join(lines)
```

Phase 2–4 sections produce no output when their fields are None. They
activate automatically when the layer comes online — no template changes needed.

---

### 7. Router Integration

The cloud is built inside the router's resolution cascade, specifically
at Step 4 (specialist call) — the only step that benefits from rich context.
Steps 1–3 and 5–6 are fast lookups that do not need the cloud.

Currently in `core/router.py`, `_resolve_token()` calls the specialist like this:

```python
# Current (bare token)
specialist_result = self._specialist_fn(surface, {
    "lemma": lemma,
    "pos": pos,
    "grammatical_primes": list(gram_primes),
    "context": "ingestion",
})
```

After integration, this becomes:

```python
# With activation cloud
from core.activation import build_activation_cloud, serialise_cloud

cloud = build_activation_cloud(
    token=surface,
    position=idx,
    lemma=lemma,
    pos=pos,
    utterance_so_far=self._current_utterance_compounds,
    active_narrative=self._get_narrative_context(),
)

specialist_result = self._specialist_fn(surface, {
    "lemma": lemma,
    "pos": pos,
    "grammatical_primes": list(gram_primes),
    "context": "ingestion",
    "activation_cloud": serialise_cloud(cloud),
})
```

The specialist's `_build_prompt()` method is updated to include the serialised
cloud in the user prompt when the `activation_cloud` key is present:

```python
# In TextGrounder._build_prompt():
activation_context = token_data.get("activation_cloud", "")
if activation_context:
    user_prompt = (
        f"Activation context:\n{activation_context}\n\n"
        f"Given this activation context, assign primes to \"{word}\":\n"
    )
else:
    # Fallback: current bare-token prompt
    user_prompt = f'Word: "{word}" (lemma: "{lemma}", POS: {pos})\nDecompose into primes:'
```

When no cloud is available (e.g. tests, fallback modes), the specialist falls
back to the current bare-token prompt. No breaking change.

---

### 8. Utterance Context Tracking in Router

The router needs to track which compounds have been resolved so far within
the current utterance, so that token N can see the context from tokens 0..N-1.

```python
class Router:
    def __init__(self, ...):
        ...
        # Per-observation tracking (reset on each resolve_observation call)
        self._current_utterance_compounds: list[Compound] = []
```

In `resolve_observation()`, reset the tracking list at the start:

```python
def resolve_observation(self, observation):
    ...
    self._current_utterance_compounds = []

    for tok_analysis in spacy_tokens:
        resolution = self._resolve_token(tok_analysis)
        resolutions.append(resolution)

        # Track resolved compound for subsequent tokens' clouds
        if resolution.compound_id is not None:
            compound = know.by_id(resolution.compound_id)
            if compound is not None:
                self._current_utterance_compounds.append(compound)

    return resolutions
```

This gives each token's cloud access to its predecessors in the utterance.
The first token gets an empty `utterance_context`. The second token sees the
first. This is how context pre-primes the network.

---

### 9. Narrative Context Retrieval

Narrative context comes from KNOW's active narrative. In Phase 1, this is
a simple read — fetch the last N compounds from the most recent narrative.

```python
def _get_narrative_context(self, n: int = 5) -> list[Compound]:
    """
    Fetch the last n compounds from the active narrative.

    Returns empty list if no narrative is active or if KNOW's narrative
    API is not yet available (Phase 1 stub).
    """
    try:
        know = self._get_know()
        # Phase 1 stub: KNOW.recent_compounds() returns the last n
        # compounds stored (not narrative-aware yet).
        # Phase 2+: replace with narrative-specific retrieval.
        if hasattr(know, 'recent_compounds'):
            return know.recent_compounds(n)
    except Exception:
        pass
    return []
```

KNOW's `recent_compounds()` is a new convenience method that returns the
last N compounds stored (by creation time). This is a rough proxy for
narrative context in Phase 1. Phase 2 replaces it with proper narrative
thread traversal.

---

### 10. New Module: `core/activation.py`

Exports:
- `ActivationCloud` — the dataclass
- `build_activation_cloud()` — assembly function
- `serialise_cloud()` — LLM prompt serialisation
- `_aggregate_primes()` — internal prime collection

Does not export:
- Any modification functions. The cloud is built once and read once.
- Any persistence functions. The cloud is transient.

---

### 11. KNOW Additions

One new method on KNOW for Phase 1:

```python
def recent_compounds(self, n: int = 5) -> list[Compound]:
    """
    Return the last n compounds stored (by ID, descending).

    Phase 1 proxy for narrative context. Returns only concept and utterance
    compounds (not logic or internal). Returns empty list if fewer than n
    compounds exist.
    """
    with self._lock:
        runtime = [
            c for cid, c in sorted(self._compounds.items(), reverse=True)
            if cid >= 200 and c.compound_type in ("concept", "utterance")
        ]
    return runtime[:n]
```

---

### 12. Test Requirements

Test file: `tests/test_activation.py`

#### Unit tests for ActivationCloud:
- `test_cloud_default_fields` — dormant layers are None by default, fast_path=False
- `test_cloud_with_exact_match` — exact_match set, primes aggregated at WEIGHT_EXACT_MATCH
- `test_cloud_exact_match_high_confidence` — confidence >= 0.8 → fast_path=True
- `test_cloud_exact_match_low_confidence` — confidence < 0.8 → fast_path=False
- `test_cloud_with_family_root` — family_root contributes to prime_candidates
- `test_cloud_with_definition_compounds` — nested definition compounds contribute
- `test_cloud_with_utterance_context` — preceding tokens contribute at correct weight
- `test_cloud_with_narrative_context` — narrative compounds contribute at low weight
- `test_cloud_prime_aggregation_max_wins` — same prime from two sources → max weight kept
- `test_cloud_empty` — no matches → empty prime_candidates, no crash

#### Unit tests for serialise_cloud:
- `test_serialise_minimal` — token with no matches → clean output
- `test_serialise_with_exact_match` — exact match section included
- `test_serialise_with_definition` — definition context section included
- `test_serialise_with_utterance_context` — utterance section included
- `test_serialise_phase2_dormant` — affective fields are None → section absent
- `test_serialise_phase2_active` — affective fields set → section present

#### Integration test with router:
- `test_router_builds_cloud_for_specialist` — mock specialist receives cloud in token_data
- `test_utterance_context_accumulates` — second token sees first token's compound
- `test_narrative_context_passed` — narrative context flows into cloud

---

### 13. Phase 1 Scope Summary

✅ `core/activation.py` — ActivationCloud dataclass (exact_match, fast_path, family_root, definition_compounds, utterance_context, narrative_context, prime_candidates), build, serialise
✅ `core/activation.py` — `FAST_PATH_EXACT_THRESHOLD` constant; fast_path set when exact_match.confidence >= threshold
✅ `core/router.py` — utterance tracking, cloud assembly before specialist call, fast_path routing
✅ `core/specialists.py` — TextGrounder prompt includes activation cloud context
✅ `primes/KNOW.py` — `by_symbol()` O(1) via `_symbol_index`; `recent_compounds()`
✅ `tests/test_activation.py` — unit + integration test suite

❌ Not Phase 1: FEEL integration (affective layer)
❌ Not Phase 1: WANT/NEED integration (motivational layer)
❌ Not Phase 1: SELF integration (relational layer)
❌ Not Phase 1: narrative-aware context retrieval (Phase 2 KNOW upgrade)
❌ Not Phase 1: definition compound loading from sorted_dictionary files

---

## PHASE 2+ — Deferred (Do Not Implement Yet)

---

### D1. Affective Layer (FEEL)

When FEEL comes online, it contributes two fields to the cloud:

```python
cloud.affective_valence  = feel.query_valence(token)    # -1.0 to 1.0
cloud.affective_intensity = feel.query_intensity(token)  # 0.0 to 1.0
```

The build function adds one call to FEEL after the cognitive layer is assembled.
The serialise function already has the placeholder section that activates when
these fields are not None.

Affective valence influences the LLM's interpretation. "rebel" with positive
valence → hero, freedom fighter. "rebel" with negative valence → troublemaker,
dissident. The LLM receives this signal alongside the cognitive context.

---

### D2. Motivational Layer (WANT/NEED)

WANT and NEED contribute goal-relevance and urgency signals:

```python
cloud.goal_relevance = want.relevance_to_active_goals(cloud.prime_candidates)
cloud.need_pressure  = need.current_pressure(cloud.prime_candidates)
```

Goal relevance is computed from the overlap between the cloud's activated primes
and WANT's current goal primes. If the activated field aligns with active goals,
the token gets a salience boost. The LLM sees this as a directive: "PABLO cares
about this concept right now."

---

### D3. Relational Layer (SELF)

SELF contributes source-awareness and narrative state:

```python
cloud.source_salience  = self.relationship_weight(source)
cloud.narrative_status = self.classify_narrative_state()  # "continuing"|"new"|"closing"
```

Source salience modulates how much PABLO trusts or attends to this input.
A known, trusted source's words activate more strongly than an unknown source's.
Narrative status tells the LLM whether this observation continues an existing
conversation thread or starts something new.

With the relational layer active, SELF is no longer just gating whether THINK
is woken — it actively shapes how every token is grounded. The same word means
different things depending on who said it and what the relational history is.

---

### D4. Narrative-Aware Context Retrieval

Phase 1's `recent_compounds()` is a blunt proxy — it returns the N most recent
compounds regardless of narrative thread. Phase 2 replaces this with:

```python
def narrative_context(self, narrative_id: int, n: int = 5) -> list[Compound]:
    """
    Return the last n compounds from a specific narrative thread.

    Follows the narrative's event chain to find the most recent compound
    references that are contextually relevant to the current conversation.
    """
```

This requires the Narrative data structure to support efficient tail traversal,
which is a KNOW Phase 2 concern.

---

### D5. Definition Compound Loading from Sorted Dictionary

Phase 1 fetches definition compounds from KNOW only — if the token's compound
has nested IDs, those IDs are resolved. But most tokens won't have compounds
in KNOW on first encounter.

Phase 2 adds direct file lookup from `data/sorted_dictionary/`:

```python
def _load_definition_from_dict(token: str) -> list[Compound]:
    """
    Look up token in data/sorted_dictionary/, parse the definition fields,
    and return temporary Compound objects representing the definition words.

    These are not stored in KNOW — they exist only within the cloud for
    this resolution cycle.
    """
```

This bridges the gap between first-encounter tokens (not in KNOW) and the
dictionary's rich definition data. The cloud carries the definition context
even before the token has ever been seen by PABLO.

---

### D6. Cloud Caching

If the same token appears in multiple utterances within a short window, the
cognitive layer of its cloud will be identical (same KNOW state, same definitions).
Phase 2 may introduce a short-lived cache:

```python
_cloud_cache: dict[str, tuple[float, ActivationCloud]] = {}
CACHE_TTL = 5.0  # seconds

def _get_cached_cloud(token: str) -> ActivationCloud | None:
    entry = _cloud_cache.get(token)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None
```

Utterance and narrative context would still be updated on each call — only the
KNOW lookups and definition compounds would be cached. This is a performance
optimisation, not a semantic change.

