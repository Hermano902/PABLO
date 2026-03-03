"""
Activation Cloud — per-token context structure assembled before specialist call.

The activation cloud gathers everything PABLO already knows that is relevant
to a single token and its current utterance/narrative context. It is built
once per token, passed to the LLM specialist as rich context, then discarded.

The cloud is NOT stored. It is transient — exists for one token's grounding cycle.

Phase 1: cognitive layer only.
Phase 2+: affective, motivational, relational layers activate.

See docs/ACTIVATION_CLOUD/activation_cloud_concept.md for the concept.
See docs/ACTIVATION_CLOUD/activation_cloud_architecture.md for the spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.compound import Compound


# ══════════════════════════════════════════════════════════════════════════════
# Activation Weight Constants
# ══════════════════════════════════════════════════════════════════════════════

WEIGHT_EXACT_MATCH        = 1.0   # token already exists in KNOW
WEIGHT_FAMILY_ROOT        = 0.9   # root compound of an inflected form
WEIGHT_DEFINITION         = 0.6   # primes from definition compounds
WEIGHT_UTTERANCE          = 0.5   # primes from already-resolved sibling tokens
WEIGHT_NARRATIVE          = 0.3   # primes from recent narrative context

FAST_PATH_EXACT_THRESHOLD = 0.8   # exact_match.confidence >= this → skip LLM call


# ══════════════════════════════════════════════════════════════════════════════
# ActivationCloud Dataclass
# ══════════════════════════════════════════════════════════════════════════════

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

    # ── Identity ──────────────────────────────────────────────────────────
    token:    str           # surface form being resolved
    position: int           # 0-based index in the utterance
    lemma:    Optional[str] # spaCy lemma (if available)
    pos:      Optional[str] # spaCy POS tag ("NOUN", "VERB", "ADJ", etc.)

    # ── Cognitive layer (Phase 1 — active) ────────────────────────────────
    exact_match:          Optional[Compound]    = None
    # The existing compound for this exact surface form, if in KNOW.
    # None: token not yet known to PABLO → specialist must create it.
    # Polysemy is not PABLO's concern. PABLO reasons in prime-space.
    # Two senses of "bank" are TWO compounds with different primebits,
    # naturally disambiguated by prime_candidates + narrative context.

    family_root:          Optional[Compound]    = None
    definition_compounds: List[Compound]        = field(default_factory=list)
    utterance_context:    List[Compound]        = field(default_factory=list)
    narrative_context:    List[Compound]        = field(default_factory=list)

    prime_candidates:     Dict[str, float]      = field(default_factory=dict)
    # prime_candidates maps prime_name → activation weight (0.0–1.0).
    # Aggregated from all compounds in the cloud. Max-wins semantics.

    fast_path:            bool                  = False
    # True if exact_match.confidence >= FAST_PATH_EXACT_THRESHOLD.
    # When True: router can skip the LLM specialist call for this token.

    # ── Affective layer (Phase 2 — dormant) ───────────────────────────────
    affective_valence:   Optional[float] = None   # FEEL: -1.0 bad ↔ 1.0 good
    affective_intensity: Optional[float] = None   # FEEL: 0.0 calm ↔ 1.0 strong

    # ── Motivational layer (Phase 3 — dormant) ────────────────────────────
    goal_relevance:      Optional[float] = None   # WANT: 0.0 irrelevant ↔ 1.0 central
    need_pressure:       Optional[float] = None   # NEED: 0.0 none ↔ 1.0 urgent

    # ── Relational layer (Phase 4 — dormant) ──────────────────────────────
    source_salience:     Optional[float] = None   # SELF: relationship history weight
    narrative_status:    Optional[str]   = None   # SELF: "continuing"|"new"|"closing"


# ══════════════════════════════════════════════════════════════════════════════
# Cloud Assembly
# ══════════════════════════════════════════════════════════════════════════════

def build_activation_cloud(
    token:             str,
    position:          int,
    lemma:             Optional[str],
    pos:               Optional[str],
    utterance_so_far:  List[Compound],
    active_narrative:  Optional[List[Compound]] = None,
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
    from primes.KNOW import know  # lazy import to avoid circular dependency

    cloud = ActivationCloud(
        token=token,
        position=position,
        lemma=lemma,
        pos=pos,
    )

    # ── 1. Exact match (single compound for this symbol) ───────────────────
    cloud.exact_match = know.by_symbol(token)
    if cloud.exact_match is None and token != token.lower():
        cloud.exact_match = know.by_symbol(token.lower())

    # ── 1b. Fast path check ────────────────────────────────────────────────
    if (cloud.exact_match is not None
            and cloud.exact_match.confidence >= FAST_PATH_EXACT_THRESHOLD):
        cloud.fast_path = True

    # ── 2. Family root (if inflected) ─────────────────────────────────────
    if lemma and lemma.lower() != token.lower():
        cloud.family_root = know.by_symbol(lemma)
        if cloud.family_root is None:
            cloud.family_root = know.by_symbol(lemma.lower())

    # ── 3. Definition compounds ───────────────────────────────────────────
    # Use exact_match (or family_root) to find definition compounds.
    lookup_compound = cloud.exact_match or cloud.family_root
    if lookup_compound is not None and lookup_compound.nested:
        for nested_id in lookup_compound.nested[:10]:   # cap at 10
            nested = know.by_id(nested_id)
            if nested is not None:
                cloud.definition_compounds.append(nested)

    # ── 4. Utterance context ──────────────────────────────────────────────
    cloud.utterance_context = list(utterance_so_far)

    # ── 5. Narrative context ──────────────────────────────────────────────
    if active_narrative:
        cloud.narrative_context = list(active_narrative[-5:])   # last 5

    # ── 6. Assemble prime_candidates ──────────────────────────────────────
    cloud.prime_candidates = _aggregate_primes(cloud)

    return cloud


# ══════════════════════════════════════════════════════════════════════════════
# Prime Aggregation
# ══════════════════════════════════════════════════════════════════════════════

def _aggregate_primes(cloud: ActivationCloud) -> Dict[str, float]:
    """
    Walk all compounds in the cloud and collect prime activations
    with weight-by-source.

    Returns dict mapping prime_name → max activation weight.
    Max-wins: if the same prime appears from multiple sources,
    the highest weight is kept (no double counting).
    """
    activations: Dict[str, float] = {}

    def _add(compound: Optional[Compound], weight: float) -> None:
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


# ══════════════════════════════════════════════════════════════════════════════
# Cloud Serialisation for LLM Prompt
# ══════════════════════════════════════════════════════════════════════════════

def serialise_cloud(cloud: ActivationCloud) -> str:
    """
    Convert an ActivationCloud to a human-readable string for inclusion
    in the LLM specialist's prompt context.

    Sections with no data are omitted entirely. Phase 2–4 sections only
    appear when their fields are not None.
    """
    lines: List[str] = []

    lines.append(f'Token: "{cloud.token}"')
    lines.append(f"Position: {cloud.position}")
    if cloud.lemma and cloud.lemma.lower() != cloud.token.lower():
        lines.append(f"Lemma: {cloud.lemma}")
    if cloud.pos:
        lines.append(f"POS: {cloud.pos}")
    lines.append("")

    # ── Exact match ────────────────────────────────────────────────────────
    if cloud.exact_match:
        primes = cloud.exact_match.primebit.get_prime_names()
        lines.append("Already known in PABLO:")
        lines.append(f"  {cloud.exact_match.symbol} → {', '.join(primes) or 'ungrounded'}")
        conf_str = f"  confidence: {cloud.exact_match.confidence:.2f}"
        if cloud.fast_path:
            conf_str += "  [FAST PATH — LLM call skipped]"
        lines.append(conf_str)
        lines.append("")
    else:
        lines.append("Already known in PABLO: None")
        lines.append("")

    # ── Family root ────────────────────────────────────────────────────────
    if cloud.family_root:
        primes = cloud.family_root.primebit.get_prime_names()
        lines.append(f"Root form ({cloud.family_root.symbol}):")
        lines.append(f"  primes: {', '.join(primes) or 'ungrounded'}")
        lines.append("")

    # ── Definition context ─────────────────────────────────────────────────
    if cloud.definition_compounds:
        lines.append("Definition context (from PABLO's dictionary):")
        for c in cloud.definition_compounds:
            primes = c.primebit.get_prime_names()
            lines.append(f"  {c.symbol} → {', '.join(primes) or '?'}")
        lines.append("")

    # ── Utterance context ──────────────────────────────────────────────────
    if cloud.utterance_context:
        lines.append("Utterance context (tokens already resolved):")
        for c in cloud.utterance_context:
            primes = c.primebit.get_prime_names()
            lines.append(f'  "{c.symbol}" → {", ".join(primes) or "unresolved"}')
        lines.append("")

    # ── Narrative context ──────────────────────────────────────────────────
    if cloud.narrative_context:
        lines.append("Narrative context (recent compounds):")
        for c in cloud.narrative_context:
            primes = c.primebit.get_prime_names()
            lines.append(f'  "{c.symbol}" → {", ".join(primes) or "?"}')
        lines.append("")

    # ── Prime activation field ─────────────────────────────────────────────
    if cloud.prime_candidates:
        sorted_primes = sorted(
            cloud.prime_candidates.items(), key=lambda x: x[1], reverse=True
        )
        top = sorted_primes[:10]   # show top 10
        lines.append("Primes already activated by context:")
        lines.append("  " + ", ".join(f"{p} ({w:.1f})" for p, w in top))
        lines.append("")

    # ── Phase 2: Affective layer ───────────────────────────────────────────
    if cloud.affective_valence is not None:
        label = (
            "positive" if cloud.affective_valence > 0
            else "negative" if cloud.affective_valence < 0
            else "neutral"
        )
        lines.append(
            f"Affective context: {label} "
            f"(valence={cloud.affective_valence:.2f}, "
            f"intensity={cloud.affective_intensity or 0:.2f})"
        )
        lines.append("")

    # ── Phase 3: Motivational layer ────────────────────────────────────────
    if cloud.goal_relevance is not None:
        lines.append(f"Goal relevance: {cloud.goal_relevance:.2f}")
    if cloud.need_pressure is not None:
        lines.append(f"Need pressure: {cloud.need_pressure:.2f}")
    if cloud.goal_relevance is not None or cloud.need_pressure is not None:
        lines.append("")

    # ── Phase 4: Relational layer ──────────────────────────────────────────
    if cloud.source_salience is not None:
        lines.append(f"Source salience: {cloud.source_salience:.2f}")
    if cloud.narrative_status is not None:
        lines.append(f"Narrative status: {cloud.narrative_status}")
    if cloud.source_salience is not None or cloud.narrative_status is not None:
        lines.append("")

    return "\n".join(lines)
