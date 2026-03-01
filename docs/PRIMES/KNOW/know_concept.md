KNOW – Concept


Overview
KNOW is PABLO's memory. It is the single authoritative store for all Compounds,
Definition Narratives, Instance Narratives, and Refinement data the system has ever
created, received, or derived. Every piece of knowledge PABLO holds — a concept it
has grounded, a relationship it has built, a capability it has learned — lives in KNOW.

KNOW does not decide what to store. It stores what it is given.
KNOW does not understand the contents of what it holds. It retrieves on demand.
KNOW does not reason over its contents. That is THINK's job.
KNOW does not forget by default. Records persist until explicitly retired.

KNOW is the only prime that owns persistent state.

KNOW is designed to be called concurrently by every autonomous prime simultaneously
without a global bottleneck. It achieves this through sharded storage, fine-grained
locking, and a priority-aware thread pool that ensures important work is always
served before background work.


Where KNOW sits in the pipeline

  DATA   → (concept + utterance Compounds)          → KNOW
  SYMBOL → (grounding updates, definition refinement) → KNOW
  THINK  → (intent, action, macro Compounds)         → KNOW
  THINK  → (instance Narratives, binding updates)    → KNOW
  THINK  → (query)  → KNOW → (Compounds, Narratives) → THINK
  SELF   → (relational Narrative reads)              → KNOW

All primes access KNOW through the same priority-aware interface. No prime has
direct access to KNOW's internal store — all reads and writes go through the
task queue.


What KNOW Stores

KNOW holds four distinct record types, each in its own sharded store:

  Compounds           The canonical concept definitions. One per unique concept.
                      Lean records — identity, primebit, nested IDs, grounding state,
                      version, confidence. The fast-access core of the memory.

  Definition          The living definition of each compound's universal meaning.
  Narratives          Relations (predicate → target), thread of refinements, constraints.
                      Stored separately from the compound record — loaded on demand.
                      Permanent, never closed. One per compound.

  Instance            Contextual memory — episodic and relational Narratives.
  Narratives          Bindings, constraints, thread of events, relationship history.
                      Loaded by relevance, aged out over time by background maintenance.

  Refinement          Usage signals tracked by KNOW, not stored on the compound itself.
  Records             usage_count, success_rate, query_count per compound ID.
                      Updated by KNOW on every access and outcome signal.

These four record types are stored, sharded, locked, and persisted independently.
A read of a compound's core record never loads its definition Narrative unless
explicitly requested. Most operations only ever touch the compound core.


Sub-Record Decomposition

Each compound's data is decomposed into independent sub-records, each with its own
lock. This allows concurrent primes to work on different facets of the same compound
without blocking each other.

  Sub-record      Contents
  ──────────────────────────────────────────────────────────────────────
  core            id, symbol, primebit, grounded, version, confidence,
                  nested_ids, definition_narrative_id, executable
  execution       execution_path, trigger_condition, arity, slots
                  (populated only for Layers 3–4)
  refinement      usage_count, success_rate, query_count,
                  candidate_interpretations
  embedding       vector representation for similarity search (Phase 2+)

The core sub-record is always cached. Execution and refinement sub-records are
loaded on demand. The embedding sub-record is a Phase 2+ concern.

For Definition Narratives and Instance Narratives, the sub-record split is:

  header          id, name, status, created_at, compound_id (for definition)
  relations       predicate → target entries (definition Narratives only)
  thread          ordered NarrativeEvent log
  bindings        local_name → Binding map (instance Narratives only)
  constraints     active and inactive Constraint list


Storage Tiers

KNOW operates across three logical tiers:

  Hot Cache       Fixed-size in-memory LRU cache. Holds the most recently and
                  frequently accessed sub-records. This is working memory.
                  Per-entry reader-writer locks allow many simultaneous readers.
                  Default: compound core sub-records for the active working set.

  Main Store      Authoritative sharded in-memory store for all records.
                  This is long-term memory. Sub-records not in cache are fetched
                  from the main store (under shard lock) and promoted to cache.
                  Sharded by record ID: shard = id % NUM_SHARDS.

  Persistence     Optional disk backend (JSON files, SQLite in Phase 2+).
                  Reads and writes are asynchronous and batched.
                  The main store is always the primary source — persistence is
                  a durable copy, never the read path.

On startup: load persistence into main store, populate hot cache with logic compounds
and any open instance Narratives. The system is ready before the first observation.


Concurrency Model — Priority-Aware Thread Pool

KNOW uses a fixed-size thread pool (one thread per CPU core by default). All requests
from all primes enter a single priority queue. Workers always take the highest-priority
task available. No prime calls KNOW's internals directly — every operation is a task.

Priority levels (highest to lowest):

  Priority    Source / Type
  ──────────────────────────────────────────────────────────────────────
  100         THINK — conscious reasoning (fetching compounds for a decision)
  80          SELF — salience scoring, relational Narrative reads
  60          SYMBOL — resolving an unknown token on-demand
  40          DATA — storing a new observation batch
  20          Background enrichment — SYMBOL refining a definition
  5           Maintenance — consolidation, pruning, index rebuild

Tasks that must wait for a lock yield immediately — the worker thread moves to the
next task. This ensures that even when high-priority tasks are waiting for a resource,
the pool never stalls completely.

Deadlock prevention: all sub-record locks are always acquired in a fixed global order
(core → execution → refinement → embedding for compounds; header → relations →
thread → bindings → constraints for narratives). No task ever acquires locks in
a different order.


ID Assignment

  IDs 0–99      Reserved for system bootstrapping.
  IDs 100–199   Logic compounds — pre-loaded at startup from core/logic_compounds.json.
                Fixed forever. Never reassigned.
  IDs 200+      Runtime compounds — assigned sequentially, incrementing by one.
  Narrative IDs Separate counter, not shared with compound ID space.
                Narrative IDs start at 1 and increment independently.

IDs are permanent. Once assigned, never reused or changed. Temporary negative IDs
from DATA's batch construction are replaced with permanent IDs during store_batch.


Logic Compounds

At startup, KNOW loads core/logic_compounds.json and populates IDs 100–199 with
pre-defined logic Compounds: AND, OR, NOT, IF, THEN, IMPLIES, TRUE, FALSE, and others.
These are the structural operators used as predicate wrappers in compound definitions
(e.g. NOT(HAS) → WING) and for logical reasoning in THINK.
They are read-only for the lifetime of the system — never modified, never removed.
Logic compounds are always pre-loaded into the hot cache at startup.


Retrieval

KNOW answers queries through the priority task queue. All retrieval respects the
caller's priority — THINK's queries are served before background enrichment jobs.

  by_id(id)                   Returns compound core sub-record by ID.
  by_symbol(symbol)           Returns the compound whose symbol matches. Used by
                               DATA and SYMBOL to find existing concept compounds.
  by_prime(prime_name)        Returns all compounds that include that prime in primebit.
  by_type(compound_type)      Returns all compounds of a given type.
  by_trigger(primebit)        Returns action/macro compounds whose trigger_condition
                               matches. Used by THINK to find existing macros.
  search(query_dict)          Returns compounds matching a set of field conditions.
  get_definition(compound_id) Returns the full Definition Narrative for a compound.
                               Loaded on demand — not included in by_id results.
  get_narrative(id)           Returns a full Instance Narrative by ID.
  open_narratives()           Returns all Instance Narratives with status="open".
  narrative_by_source(source) Finds the open Instance Narrative for a source.

Spreading activation (Phase 2+):
  associative(cues, depth, limit)
                              Starting from seed compounds matching cues, traverse
                              relations outward accumulating activation scores.
                              Returns ranked compound IDs. Used by THINK for analogy
                              and by WANT for goal discovery.


Refinement Tracking

KNOW tracks usage signals for every compound independently of the compound definition.
These signals live in the refinement sub-record, not on the compound itself.

  usage_count       Incremented every time a compound is used in reasoning.
  success_rate      Updated when THINK emits an outcome signal (good/bad).
  query_count       Incremented every time a compound is retrieved by any prime.

KNOW updates refinement sub-records automatically on every access and outcome event.
No prime needs to manually update these — KNOW handles it as a side effect of normal
operation.

Refinement data feeds background maintenance: compounds with low success_rate and
low usage_count are candidates for pruning or archiving. Compounds with high
usage_count and high confidence are promoted to larger cache allocations.


Definition Narrative Storage

Every compound has exactly one Definition Narrative stored in KNOW. The compound's
core sub-record holds a definition_narrative_id pointer. The Definition Narrative
itself is stored separately and loaded only when deep reasoning about the concept
is required.

KNOW's contract for Definition Narratives:

  get_definition(compound_id)           Returns full Definition Narrative.
  update_definition_relations(id, rels) Appends or updates relations in the definition.
                                        Increments compound version. Appends to thread.
  refine_definition(compound_id, ...)   Called by SYMBOL after enrichment. Updates
                                        primebit, relations, confidence. Appends Snap.

Definition Narratives are never closed or archived. They grow for the lifetime of
the system. Their thread records the full history of how the concept's meaning was
built — what SYMBOL proposed, what THINK confirmed, what co-occurrence patterns
contributed.


Instance Narrative Storage

KNOW's contract for Instance Narratives (unchanged from prior design):

  store_narrative(narrative)    Assigns ID, persists to storage.
  get_narrative(id)             Fetches full Instance Narrative by ID.
  open_narratives()             Returns all with status="open".
  narrative_by_source(source)   Finds open Narrative for a source.
  close_narrative(id)           Sets status="closed", closed_at=now.
  archive_narrative(id)         Sets status="archived", compresses thread.

Instance Narratives use a separate ID counter from compounds. Open Instance
Narratives are loaded into the hot cache at startup. Archived Narratives are
in the main store, loaded on demand.


Background Maintenance

Separate from the request-handling pool, KNOW runs background threads at priority 5
that maintain memory health over time:

  Consolidation     Strengthens frequently co-occurring relations in Definition
                    Narratives. Creates summary sub-records for deeply nested compounds.
                    Updates resolved prime masks where useful.

  Forgetting        Decrements confidence for compounds not accessed recently.
                    When confidence drops below threshold, relations are pruned and
                    the compound is flagged for review. Mimics natural memory decay.

  Index Rebuild     Rebuilds symbol, prime, and relation indexes to ensure fast
                    associative access as the compound graph grows.

  Integrity Check   Verifies all relation targets exist, detects cycles in nested
                    compound graphs, logs anomalies for review.

These threads use the same task queue as all other primes, at the lowest priority.
They never interfere with real-time requests.


Persistence

KNOW autosaves asynchronously. Disk writes are batched and never block the main store.

Persistence files:
  storage/compounds.json        Serialised compound core + execution sub-records
  storage/definitions.json      Serialised Definition Narratives
  storage/narratives.json       Serialised Instance Narratives (open + recently closed)
  storage/refinement.json       Serialised refinement sub-records
  storage/metadata.json         System metadata (next_id counters, timestamps, stats)

Logic compounds (100–199) are NOT saved — always re-loaded from core/logic_compounds.json.
Archived Instance Narratives are compressed before saving to reduce storage footprint.

Persistence can be disabled for testing:
  know = KNOW(enable_persistence=False)


Statistics

KNOW tracks:

  compounds_stored          Total compounds written to the store
  compounds_retrieved       Total successful by_id lookups
  definitions_loaded        Total Definition Narrative loads (on-demand)
  narratives_stored         Total Instance Narratives created
  queries_processed         Total search/filter queries answered
  cache_hits                Hot cache hits vs main store fetches
  task_queue_depth          Current priority queue depth (observability)
  errors                    Exceptions caught during store operations


What KNOW Does NOT Do

KNOW does not ground compounds — that is SYMBOL's job.
KNOW does not structure observations — that is DATA's job.
KNOW does not reason over its contents — that is THINK's job.
KNOW does not decide which compounds are relevant — it returns matches; THINK selects.
KNOW does not modify compound definitions as a side effect of instance reasoning —
  definition updates are explicit deliberate operations, never silent side effects.


See primes/KNOW.py for the implementation.
See docs/PRIMES/COMPOUND/CONCEPT.md for what a Compound is and what sub-records contain.
See docs/PRIMES/NARRATIVES/CONCEPT.md for Definition and Instance Narrative structures.
See docs/PRIMES/DATA/CONCEPT.md for how Compounds are created before reaching KNOW.
See docs/PRIMES/SYMBOL/CONCEPT.md for how Compounds are grounded and definitions refined.
See core/persistence.py for the serialisation implementation.