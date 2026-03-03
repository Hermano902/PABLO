DATA – Concept


Overview
DATA is PABLO's contract enforcer. It takes near-compound candidates produced by SYMBOL
and validates, structures, and commits them as real Compound objects into KNOW.
DATA does not interpret language — SYMBOL already did that. DATA's job is to ensure every
candidate meets the Compound contract before it enters permanent storage.

DATA is the gatekeeper between SYMBOL's probabilistic proposals and KNOW's authoritative store.


Where DATA sits in the pipeline

  READ → observation_queue → SYMBOL → (near-compound candidates) → DATA → (real Compounds) → KNOW

READ pushes raw observation dicts to the observation_queue.
SYMBOL pulls from that queue, interprets each observation (via heuristics or LLM specialists),
and produces near-compound candidates — structured proposals, not yet real Compounds.
DATA receives those candidates, validates them, and resolves or creates Layer 0 concept
Compounds and one Layer 1 utterance Compound per observation.
KNOW receives the validated Compounds and assigns permanent IDs.

DATA never calls KNOW directly for validation. DATA never calls SYMBOL directly.
The outputs of DATA are handed off via the candidate_queue (see core/queues.py).


Near-Compound Candidate Shape
SYMBOL's output — the input DATA receives — looks like:

  {
    "candidate_primes": [{"prime": "MOVE", "score": 0.91}],
    "roles":            [{"span": [0, 3], "role": "agent", "score": 0.87}],
    "rule_template":    {"pattern": "<agent> <MOVE> <direction>", "slots": ["agent", "direction"]},
    "confidence":       0.89,
    "provenance":       {"model": "text-grounder-v1", "adapter": "motion-detector"},
    "raw_input":        "the cat moved left"
  }

DATA treats this as a proposal, not ground truth. It checks:
- Are the candidate primes valid (within the 63-prime set)?
- Is confidence above threshold? Below threshold → token flagged for background enrichment.
- Are unknown primes present? → those tokens become placeholder Compounds.
- Does the role structure map to valid Compound relations?


What DATA Does with a Near-Compound Candidate

1. Validate candidate primes
   Check each proposed prime against the known 63-prime set.
   High-confidence, known-prime tokens → resolve or create grounded concept Compounds.
   Low-confidence or unknown tokens → create ungrounded placeholder Compounds.

2. Detect logic operators
   Check each token against the logic token map (core/logic_compounds.json).
   Logic tokens ("and", "or", "not", "if", "then", etc.) are substituted with the
   corresponding pre-defined logic Compound (IDs 100–199) — already grounded, skip SYMBOL.

3. Assign an observation ID
   A unique ID (e.g. obs_1708600000123) is stamped on the batch for traceability.
   This ID is passed to KNOW for recording in the active Instance Narrative.
   It does not live on the Compound itself.

4. Resolve or create Layer 0 concept Compounds (one per unique surface form)

   For each token in the observation:

   a. Check KNOW for an existing concept Compound matching this exact surface form.
      KNOW.by_symbol(token_text) performs an exact string match.
      If found → use the existing Compound. No new Compound is created.
      This works for both root compounds and family members — "ran" is found
      directly by its surface form, not by looking up "run" first.
      The concept's definition is already in KNOW — DATA just references it.

   b. If not found → SYMBOL has already handled family member derivation (see
      SYMBOL_CONCEPT.md "Lemmatization and Family Member Resolution"). By the time
      DATA receives the candidate, it is either:
        - A root compound candidate (no family relation)
        - A family member candidate (KIND relation to root already set by SYMBOL)
      DATA treats both identically — validate and commit.

   c. If creating a new concept Compound:
      - id:          temporary negative ID — KNOW assigns permanent IDs
      - symbol:      exact surface form string (e.g. "ran", not "run")
      - grounded:    True if prime was confirmed above threshold; False if placeholder
      - primebit:    set from candidate_primes if confident; minimal estimate if placeholder
                     For family members: root primebit ∪ grammatical primes (set by SYMBOL)
      - nested:      empty for root compounds; [root_id] for family members
      - relations:   empty for root compounds; [KIND→root_id] for family members
      - confidence:  from candidate confidence score
      - candidate_interpretations: alternative primebits considered, from candidate

   Observation-specific context (position in utterance, sibling tokens, source,
   raw input) is recorded in the active Instance Narrative by KNOW — not on the
   Compound. Compounds are universal. Observation context is instance-specific.

5. Create Layer 1 Utterance Compound
   After all tokens are resolved or created, assemble one utterance Compound:
   - symbol:      the full original input string
   - compound_type: "utterance"
   - nested:      ordered list of the concept Compound IDs in utterance order
   - primebit:    union of all constituent concept primebits
   - grounded:    True (utterance structure is always grounded; tokens may not be)
   - relations:   structural roles linking nested concepts — subject, verb, object, modifier
   This is the unit THINK reads as the entry point for each message.

6. Resolve intra-batch temp ID references
   Before handing to KNOW, DATA resolves all internal temp ID references within the
   batch (e.g. utterance nested list pointing to sibling token temp IDs). See
   COMPOUND_CONCEPT.md for the batch resolution contract.

7. Push to KNOW via store_batch


Phase 1 Fallback (heuristic-only)
In Phase 1, SYMBOL runs heuristic-only candidates — a symbol map lookup (token string →
prime index) rather than an LLM call. DATA's validation path is identical regardless of
whether candidates came from heuristics or a model.


Consultation Mode
DATA can be called on-demand by THINK with a raw text string or a pre-built candidate.
In consultation mode:
- The observation_queue is bypassed — the input is processed directly.
- The result is returned synchronously to the caller.
- Change detection and deduplication are skipped.


What DATA Does NOT Do
DATA does not interpret raw text.
DATA does not choose prime groundings — SYMBOL proposes, DATA enforces.
DATA does not assign confidence scores — it reads them from the candidate.
DATA does not talk to KNOW or SYMBOL directly.
DATA does not filter observations based on content.
DATA does not store observation context on Compounds — that belongs in Instance Narratives.
DATA does not create a new Compound when an existing one already covers the symbol —
  it finds and references the existing Compound instead.


Statistics
DATA tracks internal counters for system monitoring:

  observations_processed      Total candidates received from SYMBOL
  tokens_processed            Total tokens processed from candidates
  concepts_found              Tokens resolved to existing KNOW compounds
  concepts_created            New concept Compounds created for unknown symbols
  utterances_assembled        Total Layer 1 utterance Compounds assembled
  grounded_directly           Tokens confirmed grounded from candidate
  placeholders_created        Tokens left ungrounded (low confidence / unknown prime)
  logic_operators_found       Tokens matched to logic compound IDs
  validation_failures         Candidates rejected for contract violations


## Triple Validation (Phase 1.5)

When SYMBOL produces triple output (rather than a prime bag), DATA validates
triples instead of prime candidates. The processing pipeline is identical in
structure — DATA still enforces the Compound contract — but the inputs change:

**Prime-bag validation (Phase 1 — current):**
- Check each `candidate_prime` against the 63-prime set
- Create concept Compound with primebit union of valid primes

**Triple validation (Phase 1.5 — after DeepSeek extractor):**
- Check each triple's `predicate` against the 63-prime set
- Resolve `source` and `target_compound` surface forms to KNOW compound IDs via `by_symbol()`
- Call `know.store_triple()` for each validated triple
- Create concept Compound with primebit = union of all predicates in the triple set

DATA accepts both formats. If `triples` key is present in the candidate, triple
validation is used. Otherwise, prime-bag validation is used. No breaking change.

Both formats can appear in the same batch — heuristic-grounded tokens produce
prime bags; DeepSeek-grounded tokens produce triples.


## DATA's Long-Term Role — Phase 4 Absorption

DATA is scaffolding, not a permanent pipeline stage.

In Phase 4, when the activation cloud matures, DATA's validation contract becomes
an internal validation step inside cloud assembly. The cloud assembles triples
directly from its pattern activation — the weighted prime candidates already imply
the relational structure. DATA's explicit validation step dissolves into the cloud.

The cloud calls KNOW.store_batch() directly. DATA's logic — prime validation,
logic operator detection, temp ID resolution, utterance compound assembly — is
replicated inside the cloud's commit phase.

DATA does not disappear. It becomes internal mechanics of the cloud assembly step,
not a separate pipeline stage visible from outside:

```
Phase 1:  READ → SYMBOL → DATA → KNOW → SELF → THINK
Phase 4:  READ → activation cloud (contains DATA logic) → THINK
```

Until Phase 4, DATA continues exactly as it does today. No premature changes.


See primes/DATA.py for the implementation.
See docs/PRIMES/COMPOUND/CONCEPT.md for what a Compound is and what layers mean.
See docs/PRIMES/PERCEPTORS/READ/CONCEPT.md for what READ emits.
See docs/PRIMES/SYMBOL/CONCEPT.md for how SYMBOL produces near-compound candidates.
See docs/PRIMES/KNOW/CONCEPT.md for how Compounds are stored after DATA validates them.
See docs/PRIMES/NARRATIVES/CONCEPT.md for where observation context is recorded.
See docs/TRIPLES/triple_concept.md for the triple format DATA validates in Phase 1.5.
See docs/ACTIVATION_CLOUD/activation_cloud_concept.md for Phase 4 DATA absorption.