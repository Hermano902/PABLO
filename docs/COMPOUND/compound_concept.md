Compound – Concept


Overview
A Compound is the universal unit of meaning in PABLO. Everything PABLO understands,
remembers, plans, and executes is a Compound. A concept, a detected intent, a task
request, an execution plan, a self-created capability — all of these are Compounds.
They differ in layer and complexity, not in kind.

A Compound is not a passive data record. It is the actual meaning of something —
expressed entirely in the 63 primes and in relations to other Compounds. The symbol
field is only the human-language handle that points to this meaning. The symbol is
not the compound. The compound IS the meaning the symbol refers to.

Crucially, Compounds are not limited to describing things. Higher-layer Compounds are
executable — they carry an execution path and can be run by THINK directly. This means
PABLO can create new capabilities at runtime, store them as Compounds, and execute them
later without any change to the prime layer. Behaviour is emergent from Compound composition.


Symbols and Compounds
In PABLO, human language words are symbols — pointers to meaning, not meaning itself.
"cat" is a symbol. The Compound it points to is the actual meaning: a living entity
with a body that can move and be felt. "read" is a symbol. The Compound it points to
is the execution of the act of reading — which ultimately maps to the READ prime.

SYMBOL's job is to resolve symbols into Compounds. Once resolved, PABLO never reasons
about the symbol — it reasons about the Compound. The symbol is discarded after grounding.
Only the meaning persists.

This separation is fundamental. It means:
- The same Compound can be referenced by multiple symbols across languages.
- A Compound's meaning can evolve without changing the symbol.
- PABLO reasons in prime-space, not in human language space.


The Reverse Pyramid
Every Compound, no matter how complex, resolves to the 63 primes when fully expanded.
This is the reverse pyramid: a directed graph that always terminates at primes.

  "philosophical_debate"
          ↓
  "argument" + "ideas" + "people"
          ↓
  "conversation" + "conflict" + "concept"
          ↓
  SAY, HEAR, OTHER, WANT, THINK, FEEL, BAD
          ↓
      63 PRIMES  ← every path terminates here

Simple concepts hit primes immediately. Complex concepts walk through layers of nested
Compounds. But every single path, no matter how deep, terminates at primes. A Compound
that cannot be fully resolved to primes is not grounded — it is flagged and queued for
enrichment.

Three natural complexity levels emerge:

  Prime-terminal    primebit only, no nested Compounds
                    "fast", "left", "now" — one step to primes

  Shallow-nested    primebit + nested Compounds
                    "cat" → cat_body → primes — two steps

  Deep-nested       nested Compounds only, no direct primes
                    "philosophical_debate" → ... → primes — N steps, always terminates


The Definition Narrative
Every Compound carries a living definition — a permanent, never-closed Narrative
embedded within the Compound's record in KNOW. This definition Narrative is not an
instance of something that happened. It is a growing description of what the concept
universally means.

The definition Narrative contains:
  relations   predicate → target links that form the actual definition
  thread      ordered history of how the meaning was built and refined over time
  constraints rules that must hold for this definition ("cat ALWAYS HAS body")

"cat" definition Narrative:
  relations:
      BE       → ENTITY
      KIND     → LIFE
      HAS      → cat_body_compound
      CAN      → MOVE
      FEEL     → GOOD
      NOT(HAS) → wing_compound

  thread:
      "BE→ENTITY added on first observation"
      "HAS→cat_body added after 12 observations with body detail"
      "NOT(HAS)→wing added after encountering flying cats incorrectly"

The definition deepens over time as PABLO encounters the concept in more contexts.
It starts minimal — just enough to distinguish this concept from others — and accretes
detail through experience. No complete definition is required upfront.

Because definitions are stored separately in KNOW and loaded on demand, Compounds
themselves stay lean. The primebit provides a fast index. The definition Narrative
provides the full meaning when deep reasoning is needed. Most operations never
load the definition at all.


Relations — Predicate → Target
Relations in a definition use prime predicates to express how concepts connect.
The predicate is always one of the 63 primes (or a logic compound wrapping a prime).
The target is always a Compound ID or prime.

  predicate   which prime governs this link
  target_id   compound this relation points to

Examples:
  BE   → ENTITY       # cat is an entity
  KIND → LIFE         # cat is a kind of living thing
  HAS  → cat_body     # cat has a body
  CAN  → MOVE         # cat can move

Negation wraps the predicate, never the target:
  NOT(HAS) → WING     # cat does not have wings — correct
  HAS → NOT(WING)     # wrong — "has a not-wing" is nonsensical

NOT is a logic compound (IDs 100–199). Wrapping a predicate in NOT is a valid
relation — it means the predicate relationship does not hold. The target remains
a clean compound or prime reference.

Complexity in definitions is expressed through nested Compounds, not through
richer relation schemas. When "cat has 4 legs, a tail, and fur" needs encoding:

  cat_body Compound:
      PART → leg_compound  (×4)
      PART → tail_compound
      PART → fur_compound

  cat Compound:
      HAS → cat_body      # one relation, full detail available on demand

The relation schema stays simple — predicate → target — forever. Depth lives
in the Compound graph, not in the relation structure.


The Layer Model
Compounds exist in five conceptual layers. Each layer builds on the one below it.
The layers are not stored separately — they are all Compounds in KNOW — but they have
different roles in the pipeline.

Layer 0 — Concept (formerly Token)
Layer 1 — Utterance
Layer 2 — Intent
Layer 3 — Action
Layer 4 — Macro

────────────────────────────────────────────────────────────────────────────────────────────

Layer 0: Concept Compound
The canonical definition of a symbol's meaning. One per unique surface form — including
inflected forms. "run", "ran", "running", and "runs" are four distinct Compounds, each
with its own permanent ID and primebit. They are linked by KIND relations into a
Compound Family (see below). When PABLO encounters "cat" for the thousandth time, it
does not create a new Compound — it finds the existing "cat" Compound and records the
instance in a Narrative.

Created by:  DATA on first encounter. Updated by SYMBOL as meaning refines.
PrimeBit:    Set by SYMBOL. Fast index of which primes are present in this concept.
             "cat"     → {LIFE, ENTITY, MOVE, FEEL}
             "left"    → {LEFT, MOVE}
             "fast"    → {MOVE, MORE, TIME, LESS}
             "ran"     → root primes of "run" + BEFORE (past tense)
             "running" → root primes of "run" + NOW (progressive)
nested:      Child Compound IDs whose meanings compose this concept's full definition.
             For family members: [root_compound_id] — the KIND chain.
definition:  The living definition Narrative — loaded on demand from KNOW.
executable:  False
Lifecycle:   Created ungrounded → SYMBOL grounds it → definition deepens over time.

Concept Compounds are universal and context-free. They represent what something IS
across all contexts. Contextual instances — when and how a concept appeared — live
in Narratives, not in the Compound.

────────────────────────────────────────────────────────────────────────────────────────────

Layer 1: Utterance Compound
A complete unit of input — one full message, structured as an ordered aggregate of
concept Compounds.

Created by:  DATA, after resolving all tokens in a single READ observation to their
             canonical concept Compounds.
PrimeBit:    Union of all constituent concept primebits — the "flavour" of the utterance.
nested:      Ordered list of the concept Compound IDs that make up the utterance.
relations:   Structural roles linking nested concepts — subject, verb, object, modifier.
executable:  False
Lifecycle:   Assembled after all tokens are resolved to concept Compounds.

An Utterance Compound is still a descriptor. It represents what was said, preserving
the full structure. The specific instance — who said it, when, in what context — is
recorded in the active Narrative, not in the Utterance Compound itself.

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
6. Record success/failure via KNOW's refinement tracking for this Compound.

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
    KNOW's refinement tracking drives retirement of weak paths.
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


This rule applies to context-specific compounds too, but note that whether to act
is ultimately determined by the Narrative context and SELF's salience scoring —
not by the Compound alone. A Compound containing WANT does not automatically trigger
execution. SELF decides whether THINK is woken for it.


Full Field Reference

Field                        Type              Layers    Description
id                           int               all       Permanent unique ID. Assigned by KNOW.
symbol                       str               all       Human-language handle. Not the meaning —
                                                         a pointer to it. ("cat", "read", "fast")
primebit                     PrimeBit          all       Fast prime index — which primes are present.
                                                         Used for routing and filtering. Not the
                                                         full definition — that lives in definition.
nested                       [int]             all       Child Compound IDs whose meanings compose
                                                         this concept. Empty for prime-terminal
                                                         concepts. Together with primebit, these
                                                         define the reverse pyramid structure.
definition_id                int               all       ID of this Compound's definition Narrative
                                                         in KNOW. Loaded on demand. Contains the
                                                         full relations, thread, and constraints.
grounded                     bool              all       True when full resolution terminates at
                                                         primes. False = still being enriched.
version                      int               all       Incremented each time the definition refines.
confidence                   float             all       Certainty of current primebit encoding (0–1).
candidate_interpretations    [dict]            all       Alternative primebits considered by SYMBOL
                                                         during grounding. Retained for refinement.
executable                   bool              3,4       True = this compound has an execution path.
execution_path               [Step]            3,4       Ordered execution steps. See Layer 3 above.
trigger_condition            PrimeBit|None     3,4       Primebit pattern that auto-activates this.
arity                        int               3,4       Number of argument slots.
slots                        [str]             3,4       Named argument slots matching arity.
operation_arity              int               logic     For logic compounds: number of operands.
slot_names                   [str]             logic     Operand slot names for logic compounds.

Fields removed from previous versions:
  text              — replaced by symbol (same purpose, clearer name)
  compound_type     — derived from executable + nested structure, not a stored field
  layer             — derived from compound_type, not a stored field
  children          — replaced by nested (same purpose, clearer semantics)
  relations         — moved into definition Narrative; accessed via definition_id
  provenance bucket — observation context belongs in Narratives, not Compounds
  refinement bucket — usage_count, success_rate, query_count belong in KNOW's
                      refinement tracking layer, not in the Compound definition


Compound Types

logic      Pre-defined structural operators (AND, OR, NOT, IF, THEN, etc.).
           Loaded from core/logic_compounds.json. IDs 100–199. Read-only.
           Used as predicate wrappers in relations (e.g. NOT(HAS) → WING).

concept    Layer 0. Canonical definition of a symbol's meaning. One per unique surface
           form — including inflected forms. "run", "ran", "running", "runs" are four
           distinct concept Compounds. Replaces the old "data" type.

utterance  Layer 1. Aggregate of ordered concept Compounds from one READ observation.
           Replaces the old "aggregate" type.

intent     Layer 2. THINK's interpretation of an utterance.
           Replaces the old "definition" type.

action     Layer 3 executable compound. Derived by THINK. Has execution_path.

macro      Layer 4 self-created compound. Stored by THINK after successful execution.
           Permanently available to all future THINK calls via KNOW.

internal   System-use compounds not from external observations.


Compound Families and Inflections

Inflected forms are distinct Compounds. "run", "ran", "running", and "runs" each get
their own permanent ID, symbol, and primebit. They are not aliases — they are four
separate concept Compounds linked into a Compound Family by KIND relations.

Family Structure:

  Root Compound:     "run"
  Family Members:    "ran", "running", "runs"

  "ran"     → KIND relation → target_id: "run" compound
  "running" → KIND relation → target_id: "run" compound
  "runs"    → KIND relation → target_id: "run" compound

A family member's primebit is always a superset of its root's primebit. The root
contributes its semantic primes; the member adds grammatical primes that encode the
inflection. "ran" = run's primes ∪ {BEFORE}. "running" = run's primes ∪ {NOW}.

Irregular forms (went→go, better→good, mice→mouse) follow the same model. Irregularity
is purely a surface-form problem that SYMBOL solves during lookup. Once grounded, "went"
is simply a family member of "go" with a KIND relation and BEFORE in its primebit —
structurally identical to any regular past tense form.


Grammatical Prime Mappings

The 63 primes include all the grammatical markers needed to encode inflection:

  Tense / Aspect:
    BEFORE  (bit 6)   — past tense:         "ran", "walked", "was"
    NOW     (bit 39)  — present/progressive: "running", "walking", "is"
    AFTER   (bit 0)   — future tense:        "will run", "will walk"
    LAST    (bit 27)  — perfect aspect:       "has run", "had walked"

  Number:
    ONE     (bit 40)  — singular:            "cat", "runs" (3rd-person singular verb)
    MANY    (bit 33)  — plural:              "cats", "mice"

  Degree (adjectives/adverbs):
    MORE    (bit 34)  — comparative:         "faster", "better"
    MORE+ALL          — superlative:         "fastest", "best"

  Person (verb conjugation):
    SELF    (bit 48)  — 1st person:          "am", "have" (1st-person forms)
    YOU     (bit 62)  — 2nd person:          "are" (2nd-person forms)
    OTHER   (bit 42)  — 3rd person:          "is", "has" (3rd-person forms)

The WITH prime is used as a relational wrapper for grammatical primes in the
Definition Narrative. WITH→BEFORE on a family member means "this form carries
past tense." This keeps grammatical primes in the same relation schema as all
other definition links — predicate → target, using primes.


Dictionary Inflection Tables as Family Blueprints

The dictionary data (data/out/) contains INFLECTIONS tables for each headword.
These serve as blueprints for family construction during bootstrap:

  HEADWORD "run" (verb)
    INFLECTIONS:
      3rd person singular: "runs"
      present participle:  "running"
      past tense:          "ran"
      past participle:     "run"

During dictionary bootstrap, the parser:
  1. Creates the root compound for "run" from the headword definition
  2. Reads the INFLECTIONS table
  3. Creates family member compounds for each inflected form
  4. Links each member to the root via KIND relation
  5. Adds the appropriate grammatical primes to each member's primebit

Family members created from INFLECTIONS inherit the root's semantic primebit
and add only the grammatical markers. No LLM call is needed — the dictionary
provides the family structure directly.


SYMBOL's Role with Families

When SYMBOL encounters a token:
  1. Exact surface form lookup — search KNOW by_symbol(token)
  2. If found: use the existing compound (root or family member)
  3. If not found: attempt family member derivation
     a. Lemmatise the token to find a potential root
     b. If root exists in KNOW, create a family member compound
        linked by KIND with appropriate grammatical primes
  4. If no root found: create a new root compound (LLM fallback if needed)

This resolution order means SYMBOL tries the cheapest path first (cached lookup),
then morphological derivation (no LLM), and only falls back to LLM for genuinely
novel roots. Family members are created on-demand as new inflected forms are
encountered.


ID Ranges

Range       Purpose
0–99        Reserved for system bootstrapping.
100–199     Logic compounds (fixed at startup).
200+        All runtime compounds — concept, utterance, intent, action, macro, internal.
            Assigned sequentially by KNOW.


Compounds and Narratives — The Boundary
Compounds are universal and context-free. They represent what something means
across all contexts, all times, all observations.

Narratives are contextual and temporal. They represent what happened — when a
concept appeared, alongside what, behaving how, in what relationship.

When PABLO processes "the cat moved left":
  KNOW holds (universal):
      Compound "cat"   — definition deepens over time
      Compound "moved" — maps to MOVE prime
      Compound "left"  — maps to LEFT prime

  Narrative holds (instance):
      THIS_CAT appeared at position 1
      THIS_CAT performed MOVE in direction LEFT
      Timestamp, context, relationship to other entities in this episode

A Compound is never modified to record an instance. An instance is always recorded
in a Narrative. This separation keeps Compounds clean as universal building blocks
and Narratives rich as contextual memory.


This rule keeps compounds clean, universal, and trustworthy as building blocks across
all reasoning contexts.


The Full Pipeline

  READ detects input
    → observation_queue
      → SYMBOL interprets observation → resolves symbols to concept Compounds
        → DATA assembles → Layer 0 concept Compounds + Layer 1 utterance Compound
          → KNOW stores → permanent IDs assigned
            → THINK reads Utterance Compound
              → builds Intent Compound (Layer 2)
                → checks primebit for action primes
                  → [descriptor] → compose response → SAY
                  → [actionable] → find Macro OR derive Action Compound
                                 → execute execution_path
                                 → if successful: bundle as new Macro → KNOW.store
                                 → SAY result


See core/compound.py for the implementation.
See docs/PRIMEBIT/CONCEPT.md for PrimeBit encoding.
See docs/PRIMES/DATA/CONCEPT.md for Layer 0 compound creation.
See docs/PRIMES/SYMBOL/CONCEPT.md for symbol resolution and grounding.
See docs/PRIMES/KNOW/CONCEPT.md for storage, definition narratives, and refinement tracking.
See docs/PRIMES/NARRATIVES/CONCEPT.md for instance-space reasoning.
See docs/PRIMES/THINK/CONCEPT.md for Intent, Action, and Macro compound creation.