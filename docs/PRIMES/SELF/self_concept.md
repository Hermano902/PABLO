SELF – Concept


Overview
SELF is PABLO's meta-cognitive prime. It is not a perceptor, not a reasoner, and not a
memory store. SELF is the conductor of conscious experience: the component that decides
what is worth thinking about, when to focus, and where to direct PABLO's cognitive
resources.

SELF holds three sub-primes:
  THINK  — reasoning engine, activated by SELF when salience is sufficient
  FEEL   — affective state (GOOD, BAD valence), contributes salience weight
  WANT   — motivational state (NEED, CAN), provides goal-relevance scoring

SELF's one continuous job: evaluate incoming signals against current goals and affective
state, then decide whether to wake THINK.

This is the biological equivalent of the reticular activating system — but with motivational
and affective weighting. A pure attention filter would always wake THINK for keyboard input
(user typed → always respond). SELF can do more: it can suppress, delay, or redirect
attention based on whether PABLO has a pressing goal (WANT) or is in an affective state
(FEEL) that alters priorities.


Where SELF Sits in the Architecture

SELF does not sit inside the data pipeline. It sits beside it, observing in parallel.

  READ → observation_queue ─────────────────────── SYMBOL → DATA → KNOW
                            │                                         │
                            └── SELF (parallel tap)          SELF (Layer 1 notify)
                                   ↓ early alert: "input type=KEYBOARD incoming"
                                   ↓
                            SELF scores salience (WANT + FEEL)
                                   ↓
                            salience ≥ threshold? → queue early preparation signal to THINK
                                                     THINK begins pre-loading context from KNOW
                                   ↓ (pipeline completes separately)
                            KNOW emits Layer 1 commit event
                                   ↓
                            SELF receives utterance_compound_id + source metadata
                                   ↓
                            SELF pushes to think_queue → THINK executes reasoning cycle

SELF interacts at two points:
  1. observation_queue tap   — early warning: source type detected immediately
  2. KNOW Layer 1 notify     — delivery: utterance compound ID available for reasoning

This two-phase approach means THINK gets a heads-up while the pipeline is still running,
then receives the processed compound the moment it is ready. PABLO doesn't wait at a gate
for the pipeline to finish — it prepares in parallel.


Salience Scoring

SELF scores every incoming signal on two axes:

  WANT axis (goal-relevance)
    PABLO always holds a set of active goals (e.g. "respond to user", "monitor environment").
    A signal scores high if it is directly relevant to an active goal.
    source=KEYBOARD always scores maximum on this axis when "respond to user" is active —
    which it is by default unless a higher-priority goal has displaced it.

  FEEL axis (affective weight)
    Signals are weighted by PABLO's current affective state.
    If FEEL is currently in a GOOD valence: novel or pleasant signals score higher.
    If FEEL is currently in a BAD valence: threat-related or urgent signals score higher.

Combined score = WANT_score × FEEL_multiplier

If combined score ≥ SELF.attention_threshold → SELF wakes THINK.
If combined score < SELF.attention_threshold → signal is noted but THINK is not activated.


Narrative-Aware Salience

SELF does not score salience in a vacuum. For any signal originating from a known entity
(e.g. keyboard input from THIS_USER), SELF reads the active Relational Narrative binding
before computing the final score.

For keyboard input:
  base_salience    = 1.0 (source=KEYBOARD, always starts at maximum)
  want_modifier    = THIS_USER.current["relationship_quality"]   # -1.0 → +1.0
  feel_multiplier  = FEEL.current_valence_toward(THIS_USER)       # 0.0 → 1.5
  final_salience   = base_salience × (1.0 + want_modifier) × feel_multiplier

Examples:
  Neutral user (relationship_quality=0.0, feel=neutral):
    final_salience = 1.0 × 1.0 × 1.0 = 1.0  → THINK woken normally

  Trusted, liked user (relationship_quality=0.8, feel=warm):
    final_salience = 1.0 × 1.8 × 1.3 = 2.34 → THINK woken with elevated priority
    PABLO is more inclined to engage, may seek to know more

  Hostile user after insult (relationship_quality=-0.7, feel=guarded):
    final_salience = 1.0 × 0.3 × 0.5 = 0.15 → below threshold → THINK not woken
    PABLO does not respond

This means PABLO's responsiveness is not a setting or a rule — it is a direct emergent
consequence of the relationship history stored in the Narrative. No one told PABLO to
ignore hostile users. The arithmetic makes it so because the relationship history made
the relationship_quality low.

SELF reads the Relational Narrative via KNOW.narrative_by_source(source). It reads
only THIS_USER.current — it does not walk history. History is THINK's domain.



The think_queue

SELF is the sole writer to think_queue. No other prime writes to it directly.

Items pushed by SELF:
  {
      "utterance_compound_id": int,    # Layer 1 compound ID committed to KNOW
      "timestamp":             float,  # When the observation was originally submitted
      "source":                str,    # "gui" | "stdin" | "file"
      "salience":              float,  # Score SELF computed (for THINK's context)
      "want_context":          str,    # Which active WANT goal matched (or "default")
      "feel_state":            str     # FEEL valence at time of dispatch ("neutral"|"good"|"bad")
  }

The salience, want_context, and feel_state fields allow THINK to know *why* it was woken,
not just *that* it was woken. A future THINK can use this to weight its response accordingly.


SELF and Suppression

SELF can deliberately not wake THINK even for high-salience input. Conditions:

  THINK is already active (busy with a previous thought cycle)
    → SELF queues the signal in think_queue (THINK will process it next)
    → If think_queue exceeds depth threshold → SELF flags overload state

  A higher-priority internal process is running (Phase 2+)
    → SELF defers the keyboard signal until the process yields

  SELF.suspended = True (explicitly set, e.g. during boot)
    → All signals are discarded until SELF resumes

In Phase 1, suppression logic is minimal: THINK processes think_queue items sequentially
and SELF always enqueues keyboard input.


What SELF Does NOT Do

SELF does not interpret the content of observations. It only sees source and salience cues.
SELF does not call SYMBOL, DATA, or READ.
SELF does not write compounds to KNOW.
SELF does not produce outputs visible to the user. THINK does.
SELF does not contain the reasoning logic. That belongs entirely to THINK.
SELF does not replace KNOW: SELF biases attention; KNOW stores and retrieves knowledge.


Relationship to Other Primes

SELF observes:
  observation_queue  — early parallel tap on READ's output (source metadata only)
  KNOW (Layer 1 notify) — commit events for fully processed utterance compounds

SELF activates:
  think_queue  — SELF is the sole dispatcher

SELF holds:
  THINK  — reasoning sub-prime; woken by SELF
  FEEL   — affective sub-prime; provides FEEL_multiplier to salience
  WANT   — motivational sub-prime; provides WANT_score to salience

SELF does not interact directly with:
  READ, SEE, HEAR  (beyond reading source metadata from observation_queue)
  SYMBOL, DATA     (pipeline internals — SELF is not in the pipeline)
  Any GUI component


Phase 1 Scope

  ✅ Parallel tap on observation_queue (reads source field only)
  ✅ Fixed salience rules (keyboard=1.0, others< threshold)
  ✅ Dispatches to think_queue with full context dict
  ✅ SELF.suspended flag for boot suppression
  ❌ Dynamic WANT-based salience scoring (Phase 2)
  ❌ Dynamic FEEL-based multiplier (Phase 2)
  ❌ Early preparation signal to THINK (Phase 2 — requires THINK's pre-load API)
  ❌ Suppression / overload handling beyond simple queue depth (Phase 2)

Phase 1 SELF is a clean, minimal attention router. It correctly owns the decision of
what THINK focuses on, without hard-coding that decision into READ, DATA, or KNOW.
