KNOW – Concept


Overview
KNOW is PABLO's memory. It is the single authoritative store of all Compounds the system has ever created, received, or derived. Every piece of knowledge that PABLO holds — a word it has seen, a concept it has grounded, a logic operator it uses for reasoning — lives in KNOW.

KNOW does not decide what to store. It stores what it is given.
KNOW does not understand the contents of what it holds. It retrieves on demand.
KNOW does not expire or forget. All Compounds persist until explicitly retired.

KNOW is the only prime that owns persistent state.


Where KNOW sits in the pipeline

  SYMBOL → DATA → (validated Layer 0/1 Compounds) → KNOW
  THINK  → (Layer 3 Action / Layer 4 Macro Compounds) → KNOW
  THINK  → (query) → KNOW → (Compounds) → THINK

SYMBOL produces grounded token and utterance Compounds and hands them to KNOW for storage.
THINK writes Action Compounds it has derived, and Macro Compounds it has created after
successful execution — these are stored in KNOW permanently and retrieved on future calls.
THINK also queries KNOW to retrieve any Compound layer when building context or finding
existing Macros that match the current intent.


What KNOW stores
KNOW holds a single in-memory dictionary:

  _store: dict[int, Compound]   # id → Compound

Every Compound at every layer lives in this dict — token Compounds (Layer 0), utterance
Compounds (Layer 1), intent Compounds (Layer 2), Action Compounds (Layer 3), and Macro
Compounds (Layer 4). KNOW makes no distinction between them at storage time.
All are stored, retrieved, and persisted identically.
The dict is the ground truth. Persistence (disk) is a serialised copy — never the primary source.


ID assignment
When KNOW receives a new Compound from SYMBOL, it assigns a permanent integer ID:

  - IDs 0–99:    reserved for system bootstrapping (not currently populated).
  - IDs 100–199: logic compounds — pre-loaded at startup from core/logic_compounds.json.
                 These IDs are fixed and never reassigned.
  - IDs 200+:    runtime compounds — assigned sequentially, starting at 200,
                 incrementing by one per new compound.

IDs are permanent. Once assigned, an ID is never reused or changed.
Temporary negative IDs (from DATA's placeholder Compounds) are replaced here
with the permanent sequential ID before storage.


Logic compounds
At startup, KNOW loads core/logic_compounds.json and populates IDs 100–199 with
pre-defined logic Compounds: AND, OR, NOT, IF, THEN, IMPLIES, TRUE, FALSE, and others.
These are the structural operators that SYMBOL and THINK use for all logical reasoning.
They are read-only for the lifetime of the system — never modified, never removed.


Retrieval
KNOW answers queries from THINK (and any other prime in consultation mode).
Retrieval modes:

  by_id(id)                   Returns the Compound with that ID, or None.
  by_prime(prime_name)        Returns all Compounds that include that prime in their primebit.
  by_text(token)              Returns Compounds whose text field matches the token.
  by_type(compound_type)      Returns all Compounds of a given type (e.g. "macro", "action").
  by_trigger(primebit)        Returns Action/Macro Compounds whose trigger_condition
                               matches the given primebit. Used by THINK to find existing
                               Macros before deriving a new execution path.
  search(query_dict)          Returns Compounds matching a set of field conditions.

All retrieval is synchronous and runs in the caller's thread.
KNOW uses a threading.RLock for all store access — multiple primes can query concurrently
without corrupting the store.


Persistence
KNOW autosaves the entire _store to disk every 30 seconds (configurable).
On initialisation, KNOW loads from disk before starting its input thread — the store
is restored to its last saved state before any new observations are processed.

Persistence files live in storage/:
  storage/compounds.json    Serialised _store (all runtime Compounds)
  storage/metadata.json     System metadata (next_id counter, timestamps, stats)
  storage/state.json        Runtime state snapshot

Logic compounds (100–199) are NOT saved to compounds.json — they are always re-loaded
from core/logic_compounds.json at startup. Saving them would create duplication risk.

Persistence can be disabled:
  know = KNOW(enable_persistence=False)   # test/ephemeral use


Thread safety
KNOW's _store is accessed from multiple threads:
  - SYMBOL's grounding thread writing new Compounds
  - THINK's query calls reading from the store
  - The autosave thread serialising the store

All access goes through threading.RLock. Writers and readers are serialised correctly.
KNOW never holds the lock across I/O (disk writes happen on a copy of the store data).


Statistics
KNOW tracks:

  compounds_stored      Total compounds written to the store
  compounds_retrieved   Total successful get-by-id lookups
  queries_processed     Total search/filter queries answered
  errors                Exceptions caught during store operations
  loads_from_disk       Times persistence was loaded at startup
  saves_to_disk         Times the store was written to disk


What KNOW does NOT do
KNOW does not ground Compounds — that is SYMBOL's job.
KNOW does not structure observations — that is DATA's job.
KNOW does not reason over its contents — that is THINK's job.
KNOW does not decide which Compounds are relevant to a given query — it returns matches;
THINK ranks and selects.


See primes/KNOW.py for the implementation.
See docs/PRIMES/COMPOUND/CONCEPT.md for what a Compound is.
See docs/PRIMES/DATA/CONCEPT.md for how Compounds are created before they reach KNOW.
See docs/PRIMES/SYMBOL/CONCEPT.md for how Compounds are grounded before KNOW stores them.
See core/persistence.py for the serialisation implementation.
