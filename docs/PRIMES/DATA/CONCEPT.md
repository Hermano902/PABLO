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
DATA receives those candidates, validates them, and creates real Layer 0 token Compounds
and one Layer 1 utterance Compound per observation.
KNOW receives the validated Compounds and assigns permanent IDs.

DATA never calls KNOW directly. DATA never calls SYMBOL directly.
The outputs of DATA are handed off via the candidate_queue (see core/queues.py).


Near-compound candidate shape
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


What DATA does with a near-compound candidate

1. Validate candidate primes
   Check each proposed prime against the known 63-prime set.
   High-confidence, known-prime tokens → create grounded Layer 0 Compounds directly.
   Low-confidence or unknown tokens → create ungrounded placeholder Compounds.

2. Detect logic operators
   Check each token against the logic token map (core/logic_compounds.json).
   Logic tokens ("and", "or", "not", "if", "then", etc.) are substituted with the
   corresponding pre-defined logic Compound (IDs 100–199) — already grounded, skip SYMBOL.

3. Assign an observation ID
   A unique ID (e.g. obs_1708600000123) is stamped on all Compounds from this observation.

4. Create Layer 0 token Compounds (one per token)
   - id:            temporary negative ID — KNOW assigns permanent IDs
   - text:          token string
   - compound_type: "data"
   - grounded:      True if prime was confirmed; False if placeholder
   - primebit:      set from candidate_primes if confident; empty if placeholder
   - relations:     set from roles if present
   - provenance:    source, observation_id, raw_input, sibling_tokens, position, model provenance

5. Create Layer 1 Utterance Compound
   After all token Compounds are built, assemble one aggregate Compound:
   - compound_type: "aggregate"
   - children:      ordered list of the token Compound IDs
   - text:          the full original input string
   - provenance:    same observation_id, source
   This is the unit THINK reads as the entry point for each message.

6. Push to candidate_queue for KNOW


Phase 1 fallback (heuristic-only)
In Phase 1, SYMBOL runs heuristic-only candidates — a symbol map lookup (token string →
prime index) rather than an LLM call. DATA's validation path is identical regardless of
whether candidates came from heuristics or a model.


Consultation mode
DATA can be called on-demand by THINK with a raw text string or a pre-built candidate.
In consultation mode:
- The observation_queue is bypassed — the input is processed directly.
- The result is returned synchronously to the caller.
- Change detection and deduplication are skipped.


What DATA does NOT do
DATA does not interpret raw text.
DATA does not choose prime groundings — SYMBOL proposes, DATA enforces.
DATA does not assign confidence scores — it reads them from the candidate.
DATA does not talk to KNOW or SYMBOL directly.
DATA does not filter observations based on content.


Statistics
DATA tracks internal counters for system monitoring:

  observations_processed      Total candidates received from SYMBOL
  tokens_processed            Total Layer 0 token Compounds created
  utterances_assembled        Total Layer 1 utterance Compounds assembled
  grounded_directly           Tokens confirmed grounded from candidate
  placeholders_created        Tokens left ungrounded (low confidence / unknown prime)
  logic_operators_found       Tokens matched to logic compound IDs
  validation_failures         Candidates rejected for contract violations


See primes/DATA.py for the implementation.
See docs/PRIMES/COMPOUND/CONCEPT.md for what a Compound is and what layers mean.
See docs/PRIMES/PERCEPTORS/READ/CONCEPT.md for what READ emits.
See docs/PRIMES/SYMBOL/CONCEPT.md for how SYMBOL produces near-compound candidates.
See docs/PRIMES/KNOW/CONCEPT.md for how Compounds are stored after DATA validates them.
