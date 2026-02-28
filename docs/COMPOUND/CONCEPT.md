Compound – Concept


Overview
A Compound is the universal unit of representation in PABLO. Everything PABLO perceives,
understands, remembers, plans, and executes is a Compound. A raw word, a complete utterance,
a detected intent, a task request, an execution plan, a self-created capability — all of
these are Compounds. They differ in layer and type, not in kind.

A Compound is not a passive data record. It is prime-grounded: its meaning derives from
which primes are encoded in its PrimeBit. The text field exists for human readability only.
Semantic content lives in the PrimeBit and in the Compound's relations to other Compounds.

Crucially, Compounds are not limited to describing things. Higher-layer Compounds are
executable — they carry an execution path and can be run by THINK directly. This means
PABLO can create new capabilities at runtime, store them as Compounds, and execute them
later without any change to the prime layer. Behaviour is emergent from Compound composition.


The Layer Model
Compounds exist in five conceptual layers. Each layer builds on the one below it.
The layers are not stored separately — they are all Compounds in KNOW — but they have
different types, different fields populated, and different roles in the pipeline.

Layer 0 — Token
Layer 1 — Utterance
Layer 2 — Intent
Layer 3 — Action
Layer 4 — Macro

────────────────────────────────────────────────────────────────────────────────────────────

Layer 0: Token Compound
The smallest meaningful unit.

Created by:  DATA, one per word/token in a READ observation.
PrimeBit:    Set by SYMBOL. Encodes which primes best represent this token's meaning.
             "cat"     → {SEE, FEEL, MOVE}     (perceived animate mover)
             "left"    → {MOVE, SPACE}
             "fast"    → {MOVE, MORE, TIME, LESS}
compound_type: "data"
executable:  False
Lifecycle:   Created ungrounded → SYMBOL grounds it → KNOW stores it.

Token Compounds are descriptors. They represent what something IS, not what to do about it.

────────────────────────────────────────────────────────────────────────────────────────────

Layer 1: Utterance Compound
A complete unit of input — one full message from the user, structured as an aggregate.

Created by:  DATA, after processing all tokens in a single READ observation.
PrimeBit:    Union of all constituent token primebits — the "flavour" of the whole utterance.
compound_type: "aggregate"
children:    Ordered list of the token Compound IDs that make up the utterance.
relations:   Structural roles — subject, verb, object, modifier — linking children.
executable:  False
Lifecycle:   Assembled after all tokens are grounded.

An Utterance Compound is still a descriptor. It represents what was said, preserving
the full structure. THINK reads Utterance Compounds to understand the complete context
of what arrived before deciding what — if anything — needs to happen.

────────────────────────────────────────────────────────────────────────────────────────────

Layer 2: Intent Compound
THINK's interpretation of what the utterance is asking for or expressing.

Created by:  THINK, after reading the Utterance Compound.
PrimeBit:    The primes that define the intent — and this is where the crucial split happens.

The PrimeBit of an Intent Compound determines whether it is a descriptor or an action trigger:

  Descriptor intent    — primes like SEE, KNOW, HEAR, DATA, FEEL, THINK
                         "tell me about X", "what is X", "I see that X"
                         PABLO should store this, respond informatively, or do nothing.

  Actionable intent    — primes like WANT, NEED, DO, MAKE, FIND, GIVE, MOVE, WRITE, SAY
                         "find me X", "create X", "write a file", "search for X"
                         PABLO needs to execute something.

No separate intent-detection logic is needed. The prime content IS the signal.
THINK checks whether the Intent Compound's primebit contains any action primes,
and routes accordingly — to a response path or an execution path.

compound_type: "definition"   (defines what this utterance means for the system)
relations:    Points back to the Utterance Compound it was derived from.
executable:  False — the intent is still a descriptor of what needs to happen.
              Execution is Layer 3's job.

────────────────────────────────────────────────────────────────────────────────────────────

Layer 3: Action Compound
A Compound that can be executed. Carries an ordered execution path.

Created by:  THINK, when an Intent Compound is actionable and no existing Macro
             Compound matches the trigger. THINK derives the steps from primes.
compound_type: "action"
executable:  True

New fields:
  execution_path      Ordered list of Steps. Each Step is one of:
                        {"type": "prime",    "name": "KNOW"}
                        {"type": "compound", "id": 347}
                        {"type": "branch",   "condition_id": 44,
                                             "true_path": [...], "false_path": [...]}

  trigger_condition   A PrimeBit pattern. If an incoming Intent Compound's primebit
                      matches this pattern, this Action Compound is a candidate to run.
                      None = only run when explicitly called, never auto-triggered.

  arity               Integer. How many argument slots the execution path expects.
                      0 = no arguments (e.g. "show status")
                      1 = one argument (e.g. "find X" — X is the argument)
                      N = N arguments

  slots               List of slot names matching the arity. E.g. ["target", "destination"].

When THINK executes an Action Compound:
1. Bind argument Compounds to the slots.
2. Walk the execution_path step by step.
3. Each prime step: call that prime with the current context.
4. Each compound step: execute that Compound recursively (it must be executable).
5. Collect results.
6. Record success/failure in the Action Compound's refinement.success_rate.

────────────────────────────────────────────────────────────────────────────────────────────

Layer 4: Macro Compound
A named, reusable Action Compound that PABLO created and stored itself.

Created by:  THINK, after successfully executing an Action Compound whose path
             proved useful. THINK bundles the path into a Macro and stores it in KNOW.
compound_type: "macro"
executable:  True

A Macro Compound is structurally identical to an Action Compound but:
- It exists permanently in KNOW with a real assigned ID.
- Its trigger_condition is fully specified — THINK will find it automatically next time.
- It is the result of learning. No human defined it. No prime encodes it.
- Its execution_path may include other Macro Compounds as steps — enabling composition.

The evolutionary progression:

  Stage 1 — Prime-only execution
    THINK derives every execution path from raw primes at runtime.
    Every call to "find X" re-derives the same path from scratch.
    No learning occurs. This is the baseline.

  Stage 2 — THINK bundles successful paths into Macros
    After a successful execution, THINK saves the path as a Macro Compound.
    Next time the same trigger appears, THINK finds the Macro in KNOW and runs it directly.
    Speed improves. Redundant derivation stops.

  Stage 3 — Macros compose other Macros
    A Macro's execution_path can reference other Macros as steps.
    "search and summarise" = [Macro:find_relevant + Macro:summarise_text + Macro:format_response]
    PABLO created all three. No prime defines any of them.
    This is emergent capability: new behaviours composed entirely from prior learned behaviours.

  Stage 4 — Self-optimising graph
    PABLO observes that two Macros share sub-paths.
    It factors out the common sub-path into a new shared Macro.
    refinement.success_rate and refinement.usage_count drive retirement of weak paths.
    The Compound graph compresses and specialises over time without external instruction.

────────────────────────────────────────────────────────────────────────────────────────────


Descriptor vs Actionable — The Full Rule
Every Compound at every layer is either a descriptor or actionable.
The rule is the same at every layer: read the PrimeBit.

  Contains only passive primes    (SEE, KNOW, HEAR, THINK, DATA, FEEL, READ, SPACE, TIME)
  → Descriptor. Store it. Respond if appropriate. Do not execute.

  Contains active primes          (WANT, NEED, DO, MAKE, FIND, GIVE, MOVE, WRITE, SAY, CAN)
  → Actionable. Escalate to Layer 3. Find or derive an Action Compound.

The prime system was always carrying this signal. No separate intent parser is needed.
The vocabulary of what something IS is the same as the vocabulary of what to DO about it.


Full Field Reference

Field               Type              Layers    Description
id                  int               all       Permanent unique ID. Assigned by KNOW.
text                str               all       Human-readable label. Semantic content lives in primebit.
primebit            PrimeBit          all       Prime encoding of this compound's meaning.
compound_type       str               all       See types below.
grounded            bool              all       True once SYMBOL has confirmed the primebit.
version             int               all       Incremented on meaningful update.
relations           [(role, id)]      all       Directed role-labelled links to other compounds.
children            [int]             1,2,3,4   Ordered child compound IDs (members of this aggregate).
executable          bool              3,4       True = this compound has an execution path.
execution_path      [Step]            3,4       Ordered execution steps. See Layer 3 above.
trigger_condition   PrimeBit|None     3,4       Primebit pattern that auto-activates this compound.
arity               int               3,4       Number of argument slots.
slots               [str]             3,4       Named argument slots matching arity.
operation_arity     int               logic     For logic compounds: how many operands.
slot_names          [str]             logic     Operand slot names for logic compounds.

Data Buckets (present on all layers):

core
  token, token_lower     The original token string (Layer 0).
  prime_name             Primary prime name, if single-prime.
  is_known               Whether this compound matched an existing KNOW entry.

provenance
  created_at             ISO timestamp.
  provenance             Ordered list of processing steps.
  source                 Origin: "keyboard", "file", "screen", "think", "macro", etc.
  observation_id         Source READ observation ID.
  raw_observation        Original input string.
  observation_tokens     All tokens from the originating observation.
  sibling_tokens         Co-occurring tokens (context).
  position               Token index in original observation.

refinement
  usage_count            Times this compound has been used.
  success_rate           Fraction of uses with successful outcomes.
  query_count            Times retrieved by KNOW.
  candidate_interpretations   Alternative primebits considered during grounding.
  confidence_score       SYMBOL's grounding confidence (0.0–1.0).


Compound Types

logic      Pre-defined structural operators (AND, OR, NOT, IF, THEN, etc.).
           Loaded from core/logic_compounds.json. IDs 100–199. Read-only.

data       Layer 0 token compound. One per token, from READ observations. IDs 200+.

aggregate  Layer 1 utterance compound. Groups ordered token Compounds.

definition Layer 2 intent compound. THINK's interpretation of an utterance.

action     Layer 3 executable compound. Derived by THINK. Has execution_path.

macro      Layer 4 self-created compound. Stored by THINK after successful execution.
           Permanently available to all future THINK calls via KNOW.

internal   System-use compounds not from external observations.


ID Ranges

Range       Purpose
0–99        Reserved for system bootstrapping.
100–199     Logic compounds (fixed at startup).
200+        All runtime compounds — data, aggregate, definition, action, macro, internal.
            Assigned sequentially by KNOW.


The Full Pipeline

  READ detects input
    → observation_queue
      → SYMBOL interprets observation → near-compound candidates
        → DATA validates candidates → Layer 0 token Compounds + Layer 1 utterance Compound
          → KNOW stores → permanent IDs assigned
            → THINK reads Utterance Compound
              → builds Intent Compound (Layer 2)
                → checks primebit for action primes
                  → [descriptor] → compose response → SAY
                  → [actionable] → find Macro OR derive Action Compound
                                 → execute execution_path
                                 → if successful: bundle as new Macro → KNOW.store
                                 → SAY result


See core/compound.py for the current implementation (Layers 0–1 implemented; 2–4 planned).
See docs/PRIMEBIT/CONCEPT.md for PrimeBit encoding.
See docs/PRIMES/DATA/CONCEPT.md for Layer 0 compound creation.
See docs/PRIMES/SYMBOL/CONCEPT.md for grounding.
See docs/PRIMES/KNOW/CONCEPT.md for storage and retrieval.
See docs/PRIMES/THINK/CONCEPT.md for Intent, Action, and Macro compound creation (planned).
