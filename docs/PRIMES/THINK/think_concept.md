THINK – Concept


Overview
THINK is PABLO's conscious reasoning prime. It is the only prime that fully integrates all
upstream work — perception (READ), interpretation (SYMBOL), structuring (DATA), memory (KNOW)
— and produces a meaningful response to a directed input.

THINK is not autonomous. It does not scan the environment, generate observations, or run
continuously. THINK is event-driven: it is activated by a signal that originates at READ and
arrives via KNOW. Between signals, THINK is silent.

This mirrors human conscious attention: PABLO is not always "thinking about" every observation
that flows through its perceptors. It thinks when specifically directed.


Where THINK sits in the pipeline

  READ (marks obs: source="keyboard")
    → observation_queue
      ├── SYMBOL (interprets tokens)              ← pipeline path
      │     → candidate_queue
      │       → DATA (validates, commits to KNOW)
      │             → KNOW (Layer 1 utterance compound committed)
      │                      ↓
      │             KNOW emits Layer 1 commit event
      │                      ↓
      │             SELF receives compound ID → pushes to think_queue
      │
      └── SELF (parallel tap — reads source metadata only)
            ↓ early alert: source=KEYBOARD, salience=1.0
            ↓ THINK begins pre-loading context from KNOW

  THINK (pulls from think_queue, fetches full compound from KNOW, reasons)
    → response_queue
      → GUI conversation panel

READ is the semantic origin: it sets source="keyboard" so the rest of the system knows
the observation's nature. READ does not know THINK exists.

SELF is the attention gate. It decides whether to dispatch to think_queue.
SELF dispatches after KNOW has committed the utterance — so THINK always has data to fetch.

THINK never touches observation_queue or candidate_queue.
THINK never calls DATA or SYMBOL.
THINK never calls any GUI function directly.


The Attention Handoff – Why SELF Owns the Decision

When a user presses Enter they are directing PABLO's attention. But the decision of whether
to actually focus on that — and how urgently — does not belong to READ, SYMBOL, or DATA.
It belongs to SELF.

READ's responsibility is accurate perception: it records source="keyboard" because that is
factually true about the observation's origin. READ does not know what THINK is, and has no
opinion about whether this observation deserves conscious attention.

SELF is the only prime with the context to make that judgment. SELF holds:
  WANT — which tells it whether "respond to user" is an active goal right now
  FEEL — which tells it the current affective state, affecting urgency

SELF taps observation_queue in parallel (not in series) so it can send an early alert to
THINK while the pipeline is still running. Once KNOW commits the Layer 1 utterance compound,
SELF dispatches the complete context to think_queue. THINK wakes up to a fully processed
compound already in KNOW — it never waits at an empty queue.

The source="keyboard" field is the only coupling between READ and SELF. SELF reads it.
No flag is set, passed through, or acted on by SYMBOL or DATA.


The think_queue

`think_queue` is defined in `core/queues.py` alongside the other queues.

```python
think_queue = queue.Queue(maxsize=1000)
```

Items pushed by SELF:
```python
{
    "utterance_compound_id": int,    # Layer 1 compound ID committed to KNOW
    "timestamp":             float,  # When the observation was originally submitted
    "source":                str,    # "gui" | "stdin" | "file" — for THINK's response routing
    "salience":              float,  # Score SELF computed (1.0 for keyboard in Phase 1)
    "want_context":          str,    # Active WANT goal that matched ("default" in Phase 1)
    "feel_state":            str     # FEEL valence at time of dispatch ("neutral" in Phase 1)
}
```

THINK's background thread drains this queue in order. Each item is one conscious thought cycle.


THINK's Reasoning Cycle

For each item pulled from think_queue, THINK performs these steps:

Step 1 – Fetch the utterance
  KNOW.by_id(utterance_compound_id)
  → Layer 1 (aggregate) compound containing ordered list of Layer 0 token compound IDs.

Step 2 – Identify or create Narrative context
  Check KNOW for an open Narrative associated with this source.
  If found: resume — load existing bindings and constraints.
  If not found: create new Narrative and register it with KNOW.

Step 3 – Resolve utterance compounds to Narrative bindings
  Each compound in the utterance is matched to a binding local_name.
  Known entity (seen before in this Narrative) → resolve to existing binding.
  New entity (first appearance) → create new binding, add to Narrative.
  All subsequent reasoning uses binding local_names, not raw compound IDs.

  **Family member resolution (KIND chain walking):**
  When a token compound is a family member (has a KIND relation), THINK:
  1. Follows the KIND relation to the root compound
  2. Binds to the root concept (e.g. "ran" → binding for "run")
  3. Records the grammatical primes (BEFORE, NOW, etc.) from the family member's
     primebit in the NarrativeEvent — preserving tense/number/degree context
  This means THINK reasons at the root concept level — "the cat ran" and "the cat
  is running" both resolve to the same CAT and RUN bindings — while the temporal
  context is captured in the event thread for precise response generation.

Step 4 – Fetch the tokens
  KNOW.by_ids(token_ids)
  → Layer 0 (data) compounds, each with a populated primebit.

Step 3 – PrimeBit population analysis
  Merge all token primebits into a single population bitfield.
  This tells THINK which primes dominate this utterance:
  - Heavy READ+SYMBOL → perceptual description ("the cat is here")
  - Heavy SAY+YOU      → directed message ("tell me something")
  - Heavy DO+MOVE      → action request ("move to the left")
  - Heavy KNOW+BE      → knowledge query ("what is the heat")
  - Heavy WANT+NEED    → preference/requirement expression

Step 4 – Macro match (Layer 4 lookup)
  Call KNOW.by_trigger(dominant_primebit).
  If an existing Layer 4 Macro compound matches this pattern:
    → Execute the macro's execution_path with slots filled from utterance tokens.
    → Record as successful execution.
    → Skip to Step 7 (compose response).

Step 5 – Action match (Layer 3 lookup)
  If no Macro found, search KNOW for Layer 3 Action compounds matching this pattern.
  If a matching Action is found:
    → Fill slots from utterance tokens.
    → Execute action (call execution_path).
    → Record execution result.
    → Skip to Step 7.

Step 6 – Intent construction (Layer 2 — always executed if no prior match)
  If no Action or Macro matched, THINK constructs a Layer 2 Intent compound:
  ```python
  {
      "compound_type": "definition",
      "text":          "<natural language summary of what THINK understood>",
      "primebit":      <merged utterance primebit with THINK prime set>,
      "utterance_id":  utterance_compound_id,
      "provenance_data": {
          "method": "primebit_analysis",
          "source": "THINK"
      }
  }
  ```
  This compound is written to KNOW. It is PABLO's record of "what I understood from this input."

Step 7 – Compose response
  Based on reasoning mode:
  - Knowledge query    → Query KNOW for relevant compounds; summarise in plain text.
  - Action completed   → Describe what was executed and the result.
  - Macro executed     → Describe execution as above.
  - No match / unknown → Reflect back what was understood; acknowledge uncertainty.

Step 8 – Push to response_queue
  ```python
  {
      "timestamp":   float,
      "type":        "response",
      "text":        str,
      "compound_id": int | None   # Layer 2 Intent compound ID, if created
  }
  ```
  The GUI timer picks this up on its next tick and displays it.

Step 9 – Macro candidacy check (Layer 4 creation)
  If THINK successfully executed a Layer 3 Action, it records a pattern fingerprint.
  When the same pattern is executed successfully 3 or more times, THINK bundles it
  into a Layer 4 Macro compound and writes it to KNOW:
  ```python
  {
      "compound_type":    "macro",
      "text":             "<descriptive macro name>",
      "primebit":         <trigger primebit>,
      "execution_path":   "<same path as source Action>",
      "trigger_condition": <primebit pattern>,
      "arity":            int,
      "slots":            [...]
  }
  ```
  This Macro is now permanently available to all future THINK cycles via Step 4.
  PABLO gets faster and more capable the more it is used.


PrimeBit Analysis — The Core Symbolic Tool

THINK's reasoning is entirely symbolic. There is no language model, no embedding, no fuzzy
matching. The only input to reasoning is the merged PrimeBit across utterance tokens.

This is intentional. SYMBOL is responsible for converting raw text into PrimeBit-tagged
compounds. By the time THINK receives the utterance, all linguistic ambiguity has already
been resolved into prime assignments. THINK works in prime-space.

Population analysis algorithm (Phase 1):
```python
def analyse_population(token_compounds: list[Compound]) -> dict:
    """Return the dominant prime families from a list of token compounds."""
    counts = {}
    for token in token_compounds:
        for prime_name in token.primebit.active_primes():
            counts[prime_name] = counts.get(prime_name, 0) + 1
    # Sort by frequency; return top families
    return sorted(counts.items(), key=lambda x: -x[1])
```

Routing table (Phase 1):
  Pattern                  → Reasoning mode
  ─────────────────────────────────────────────────────
  KNOW + BE               → knowledge_query
  SAY + YOU               → directed_message
  DO + (MOVE|MAKE|CHANGE) → action_request
  WANT + (X)              → preference_expression
  NEED + (X)              → requirement_expression
  THINK + SELF            → introspective_query
  (none match)            → reflective_acknowledgement


What THINK Writes to KNOW

THINK is a KNOW writer as well as a KNOW reader.

Layer 2 (definition):  One per conscious thought cycle. Records what THINK understood.
Layer 3 (action):      Created when THINK learns a new executable action pattern.
Layer 4 (macro):       Created when a Layer 3 action is executed 3+ times successfully.

Downstream primes (WRITE, SAY) read THINK's output from KNOW to compose their own outputs.
They do not call THINK directly.


What THINK Does NOT Do

THINK does not receive raw observations from observation_queue. That is READ+SYMBOL+DATA.
THINK does not call SYMBOL. THINK reasons entirely from what is already in KNOW.
THINK does not block on a response. If KNOW does not have the data yet it skips and retries.
THINK does not call any GUI function. response_queue is the only coupling to the GUI.
THINK does not contain language models. PrimeBit analysis is purely symbolic.
THINK does not interpret text. SYMBOL already did that before THINK is activated.


Phase 1 Scope

Phase 1 THINK is a valid but limited implementation:

- ✅ Background thread draining think_queue
- ✅ Fetches Layer 1 + Layer 0 compounds from KNOW
- ✅ PrimeBit population analysis (frequency-based)
- ✅ Simple routing table (8 modes)
- ✅ Layer 2 Intent compound written to KNOW each cycle
- ✅ Response pushed to response_queue
- ❌ Layer 3 Action execution (Phase 2)
- ❌ Layer 4 Macro creation (Phase 2)
- ❌ KNOW.by_trigger() lookup (Phase 2 — requires compound indexing by primebit)

Phase 1 THINK produces a human-readable reflection of what PABLO understood and routes
through the simple 8-mode routing table. This is enough to close the full pipeline:
user types → pipeline processes → THINK responds → GUI displays.


Full Pipeline Diagram (THINK's view)

  ┌─────────────────────────────────────────────────────────┐
  │                    CONSCIOUS INPUT CYCLE                │
  │                                                         │
  │  User:  "what is the heat?"  [Enter]                    │
  │                ↓                                        │
  │  READ:  creates observation, source="keyboard"          │
  │                ↓ observation_queue                      │
  │  SELF:  parallel tap — salience=1.0 (keyboard)          │
  │  SYMBOL: tags tokens (KNOW, BE, HEAT, ...)              │
  │                ↓ candidate_queue                        │
  │  DATA:  validates + commits to KNOW                     │
  │         utterance_id=347                                │
  │                ↓ KNOW emits Layer 1 commit event        │
  │  SELF:  receives event → pushes to think_queue          │
  │                ↓ think_queue  {utterance_id: 347}       │
  │  THINK: fetches utterance #347 from KNOW                │
  │         fetches tokens #340–346 from KNOW               │
  │         analyses primebits                              │
  │         routing: KNOW+BE → knowledge_query              │
  │         queries KNOW for HEAT compounds                 │
  │         writes Layer 2 Intent compound #348 to KNOW     │
  │         pushes response to response_queue               │
  │                ↓ response_queue                         │
  │  GUI:   timer tick → drains queue → displays response   │
  └─────────────────────────────────────────────────────────┘


Relationship to Other Primes

THINK reads FROM:
  KNOW   — all compound lookups; the only prime THINK consults

THINK writes TO:
  KNOW          — Layer 2/3/4 compounds
  response_queue — output for GUI (and eventually WRITE/SAY)

THINK is triggered BY:
  think_queue   — dispatched by SELF after salience evaluation

THINK does NOT interact with:
  READ, SEE, HEAR (perceptors — upstream of THINK's activation point)
  SYMBOL, DATA (pre-THINK processing — already complete when THINK wakes)
  Any GUI component (response_queue is the boundary)
