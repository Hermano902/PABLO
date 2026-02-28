16. PrimeBit bitwise operations & compound semantics

- Runtime `PrimeBit` exposes bitwise and logical operators for prime-mask values: `&`, `|`, `^`, `~` and `implies()` (logical implication). These operators are defined only for prime-mask mode (non-compound) and should raise on compound references. Example behavior (reference implementation exists in `core/primebit.py`):
  - `A & B` — bitwise AND of two prime masks.
  - `A | B` — bitwise OR of two prime masks.
  - `A ^ B` — bitwise XOR of two prime masks.
  - `~A` — bitwise NOT (masked to prime bits).
  - `A.implies(B)` — logical implication, equivalent to `(~A) | B` masked to prime bits.

- Compound-mode semantics: these operators MUST NOT operate directly on compound references. Implementations should follow one of two explicit strategies when an operation involves a compound:
  1. Resolve-on-demand (preferred for non-hot paths): resolve compound(s) to their `resolved_prime_mask` (via `get_resolved_prime_mask(compound_id)`), then perform the operation on the resolved masks. This may be costly and should be avoided on hot code-paths unless cached.
  2. Fail-fast / require header-only: reject the operation and surface a clear error instructing the caller to request a header-only load or explicit resolution step. This is safer for hot paths and aligns with the current `PrimeBit` reference behavior which raises when `is_compound` is true.

- Recommended helper APIs to bridge operations and compounds:
  - `get_resolved_prime_mask(compound_id) -> Optional[int]` — returns cached mask or computes it by loading DATA; may return `None` if unavailable.
  - `resolve_then_op(op: Callable[[int,int], int], left: PrimeBit, right: PrimeBit) -> PrimeBit` — docs-only helper that resolves operands if they are compounds and applies `op` on masks; emits metrics for resolution cost.

- Codemod guidance: replace ad-hoc raw bit ops (`>> 63`, `& 0x7FFFFFFFFFFFFFFF`, direct integer `&`/`|`) with `PrimeBit` methods and resolve helpers. Prefer explicit resolution calls in performance-sensitive places and document any synchronous resolution with a TODO and metric hook.

- Testing: add unit tests verifying that `PrimeBit` operators raise on compound inputs, and integration tests where compounds are resolved and combined correctly via `get_resolved_prime_mask` (including cache-hit and cache-miss paths).

Tracking note: include references to these operator semantics in any PR that ports the docs-only `core.primebit` implementation into runtime code to ensure behavior matches the documented contract.

# PrimeBit Architecture & Implementation Notes

This file describes the concrete implementation concerns, helper APIs, payload layout, caching strategies and migration plan for PrimeBit.

1. Encoding overview
- 64-bit integer:
  - bits 0..62: prime flags (one bit per prime, canonical alphabetical mapping)
  - bit 63: compound flag (1 = payload; 0 = pure prime mask)

2. Compound payload (when bit63==1)
- The low 63 bits contain a compact payload encoding. New canonical fields (finalized layout):
  - schema_tag: 4 bits (allows versions; 0 = legacy/no-payload)
  - rel_flags: 5 bits (compact hint bitset: HAS_CHILDREN, HAS_RELATIONS, HAS_RESOLVED_MASK, IS_NAMED, etc.)
  - compound_id: 54 bits (global compound identifier; unique across the cluster)

- The payload layout is an implementation detail; always use the provided helpers to pack/unpack. The `compound_id` is a global identifier and is used for sharding (see Sharding & Consistent Hashing below).

3. Required helpers (API surface)
- `pack_compound_payload(compound_id: int, rel_flags: int, schema_tag: int) -> int`
- `unpack_compound_payload(payload: int) -> tuple[int, int, int]` (returns `(compound_id, rel_flags, schema_tag)`)
- `primebit_from_payload(payload: int) -> int` (returns full 64-bit PrimeBit value with compound flag set)
- `is_compound_primebit(value: int) -> bool`
- `primebit_to_payload(value: int) -> int` (inverse of `primebit_from_payload`)
- Export these from `core/primebit.py` and use throughout the codebase.

4. `resolved_prime_mask` caching
- When loading a compound, compute and cache `resolved_prime_mask` (full prime-mask derived from resolving nested sub-compounds). Store cache in `KNOW` metadata and invalidate when compound children change.
- Provide `get_compound_header(compound_id)` which returns header-only info (`primebit`, `rel_flags`, `resolved_prime_mask` if present) without loading full DATA.

5. `rel_flags` semantics
- `rel_flags` are quick hints used by router and DATA to decide if a deep structural load is necessary.
- Example flags: HAS_CHILDREN, HAS_RELATIONS, HAS_RESOLVED_MASK, IS_NAMED, IS_LOGICAL_TEMPLATE.

6. Indexing and lookup
- Index by `prime_mask_mask` (masked-key) to support rule lookup.
- When storing payloads referencing local_id, store segment mapping so `local_id` resolves to an addressable compound in `KNOW`.

7. Migration & rollout plan
- Implement helpers and unit tests first; keep writers gated behind `COMPOUND_PAYLOAD_SCHEMA_ENABLED` config flag.
- Reader path must support both legacy prime masks and payload-encoded PrimeBits. `schema_tag == 0` indicates legacy.
- Provide migration scripts to backfill `resolved_prime_mask` for high-value compounds.

8. Performance & safety
- Prefer header-only reads in hot paths; enqueue deep resolution to background enrichment when needed.
- Avoid computing `resolved_prime_mask` synchronously for large batches.
- Measure and document overhead of unpacking payloads vs. full DATA loads.

8.1 Partial invalidation and approximate masks (optional optimization)

- Motivation: For extremely large or deep compound trees, even background recompute of a root's full
  `resolved_prime_mask` can be costly and cause periodic load spikes. A hybrid strategy reduces peak
  work by keeping a small, approximate membership structure alongside the authoritative cache while
  enrichment runs complete.

- What to store: an approximate membership filter (for example a Bloom filter or counting Bloom)
  representing primes present anywhere in the compound's subtree. Store it as a compact header field
  (`approx_prime_bloom`) or as a small encoded blob referenced by the compound header. Mark presence
  with a `rel_flags` bit (e.g., `HAS_APPROX_MASK`).

- How to use it:
  - Membership test semantics: the filter returns either "definitely not" or "possibly yes". Treat
    "definitely not" as authoritative (skip resolves). Treat "possibly yes" as a signal to either
    (a) schedule a background resolve/enrichment, or (b) perform an on-demand header/full resolve if
    the caller needs immediate correctness.
  - During an enrichment window (when `resolved_prime_mask` is stale or being recomputed), use the
    approximate filter to safely avoid many unnecessary resolves while still preserving correctness
    (no false negatives).

- Maintenance and update patterns:
  - Incremental updates: adding a child can incrementally update the parent's bloom by inserting the
    child's primes; removals require a counting Bloom or conservative rebuild. For heavy churn, prefer
    marking the parent stale and enqueueing a background rebuild rather than attempting expensive
    synchronous maintenance.
  - Reconciliation: schedule periodic full recompute jobs that replace the approximate filter with the
    authoritative `resolved_prime_mask` and a fresh filter, capped by time or workload.
  - Cycle and deletion handling: when children are deleted or cycles detected, prefer full
    reconciliation for the affected subtree to avoid filter drift.

- Trade-offs and notes:
  - False positives cause extra resolves (work), but do not cause incorrect "misses" — this ensures
    safety: a false-positive may trigger a resolve, whereas a false-negative (not possible with Bloom)
    would be incorrect.
  - Memory vs. FPR: choose Bloom size to balance acceptable false positive rate (FPR) against
    header/storage cost. For very large trees, a small FPR (1–2%) often yields large savings.
  - Counting Bloom vs. standard Bloom: choose counting Bloom if removals are frequent and you want
    incremental deletes; otherwise prefer simpler standard Bloom with periodic rebuilds.
  - Observability: add metrics for `approx_filter_hits`, `approx_filter_false_positive_rate_estimate`,
    and `enrichment_backlog` to tune parameters in production.

- API and doc suggestions:
  - Add `HAS_APPROX_MASK` to `rel_flags` mapping and document storage format (base64 or hex for
    compactness).
  - Recommend helpers:
    - `get_approx_prime_filter(compound_id) -> Optional[Filter]`
    - `approx_filter_may_have_prime(filter, primebit) -> bool`
    - `enqueue_recompute_resolved_mask(compound_id)`
  - Default behavior for hot paths: require header-only/defensive modes (fail-fast) and only consult
    approximate filters for cost-saving hints; never skip authoritative resolution when a caller
    explicitly requests guaranteed correctness.

- Observability & testing:
  - Unit tests: false-positive behavior (does not break correctness), rebuild correctness after many
    updates.
  - Integration tests: simulate a high-churn subtree and verify background rebuilds complete and drift
    remains bounded.
  - Metrics: track `approx_filter_queries`, `false_positive_triggered_resolves`, and `rebuild_duration`.

API signatures (recommended)

Add the following runtime helper signatures to the `core` API surface (docs-only examples):

```python
from typing import Optional

def get_approx_prime_filter(compound_id: int) -> Optional[bytes]:
    """Return the stored approximate filter blob (compact bytes) for `compound_id`, or None.

    The blob format is implementation-defined (e.g. serialized Bloom bit-array).
    Callers should not assume thread-safety; use provided helpers to query the blob.
    """

def approx_filter_may_have_prime(filter_blob: bytes, primebit: int) -> bool:
    """Return True if the approximate filter indicates the prime may be present.

    False means "definitely not"; True means "possibly yes" (may be a false positive).
    """

def enqueue_recompute_resolved_mask(compound_id: int, priority: int = 0) -> None:
    """Enqueue a background job to recompute `resolved_prime_mask` (and refresh approx filter).

    `priority` indicates scheduling preference. This returns immediately; job runs asynchronously.
    """

def get_resolved_prime_mask(compound_id: int, allow_compute: bool = False) -> Optional[int]:
    """Return the authoritative resolved prime mask if available.

    If `allow_compute` is True the call may synchronously compute the mask (expensive).
    Otherwise, return None when not cached.
    """
```

9. Tests & validation
- Unit tests for pack/unpack helpers, boundary cases, reserved bit behavior.
- Integration test: header-only read returns expected `rel_flags` and `prime_mask` for modern and legacy encodings.
- Migration test: enabling `COMPOUND_PAYLOAD_SCHEMA_ENABLED` does not change read semantics for existing data.

10. Documentation & code pointers
- Add top-level docstring in `core/primebit.py` linking to `docs/PRIMEBIT_ARCHITECTURE.md` and `docs/COMPOUND_PAYLOAD_SPEC.md`.
- Replace inline `>> 63` or `& 0x7FFFFFFFFFFFFFFF` instances with helper calls and mark deprecated locations with TODO comments.

11. Observability
- Track metrics: `primebit_unpack_latency`, `payload_write_count`, `payload_read_count`, `resolved_mask_cache_hits`.

12. Security
- Treat `local_id` and segment mapping as internal references; ensure no untrusted user input can forge payload writes without authorization.

Example helper behavior (pseudocode)

```python
# pack
payload = pack_compound_payload(local_id=12345, category=3, rel_flags=0b101, schema_tag=1)
primebit = primebit_from_payload(payload)
# unpack
fields = unpack_compound_payload(primebit_to_payload(primebit))
```

Appendix: Recommended unit tests
- Round-trip pack/unpack for min/max field values.
- Legacy read path returns correct prime mask when `schema_tag==0`.
- Cache invalidation when child compounds updated.
- Header-only read vs full load consistency.

13. Explicit bitfield layout (canonical)

This section defines the canonical bit offsets and widths used when `bit63==1` (compound-payload mode). Bit numbering uses the LSB=bit0 convention (little-endian numbering). `bit63` is the MSB and indicates payload mode when set to 1.

Layout (bits are inclusive ranges, low→high):

- `bit63` (1 bit): COMPOUND_FLAG (1 = payload mode, 0 = prime-mask mode)
- `bits 0..53` (54 bits): `compound_id` — global compound identifier (0 .. 2**54 - 1)
- `bits 54..58` (5 bits): `rel_flags` — boolean hint flags (bitset of up to 5 quick hints)
- `bits 59..62` (4 bits): `schema_tag` — payload schema version (0..15). Reserve `0` for legacy/no-payload semantics; recommend `schema_tag=1` for this new layout.

Notes and rationale:
- Total payload bits = 63 (0..62). Using 54 bits for `compound_id` supports up to 18,014,398,509,481,575 unique compounds which is ample for long-term scaling.
- `rel_flags` at 5 bits keeps the header compact; map each bit to a documented semantic (see `rel_flags` mapping below).
- `schema_tag==0` is reserved for legacy prime-mask semantics. The new payload should use `schema_tag=1` (recommended) to avoid reader ambiguity.

Packing / unpacking (reference pseudocode)

Packing fields into a 64-bit PrimeBit value (Python-style):

```
COMPOUND_FLAG = 1 << 63

def pack_compound_payload(compound_id, rel_flags, schema_tag):
  if not (0 <= compound_id < (1 << 54)):
    raise ValueError('compound_id out of range')
  if not (0 <= rel_flags < (1 << 5)):
    raise ValueError('rel_flags out of range')
  if not (0 <= schema_tag < (1 << 4)):
    raise ValueError('schema_tag out of range')

  payload = (compound_id & ((1 << 54) - 1))
  payload |= (rel_flags & 0x1F) << 54
  payload |= (schema_tag & 0xF) << 59
  return COMPOUND_FLAG | payload

def unpack_compound_payload(primebit_value):
  if (primebit_value >> 63) & 1 == 0:
    raise ValueError('not a compound payload')
  payload = primebit_value & ((1 << 63) - 1)
  compound_id = payload & ((1 << 54) - 1)
  rel_flags = (payload >> 54) & 0x1F
  schema_tag = (payload >> 59) & 0xF
  return (compound_id, rel_flags, schema_tag)
```

Validation and safety
- Always validate ranges and reject out-of-range fields early.
- Writers must not emit `schema_tag==0` for new payloads. Recommend using `schema_tag=1` for this layout to preserve the existing legacy sentinel.
- On reads, if `schema_tag` is unknown (> current supported version), treat the payload defensively: log and either reject or perform best-effort parsing of known fields (prefer safe failure). Record an audit event when encountering unknown `schema_tag`.

Indexing key note
- The masked-key used for rule indexing is computed over the resolved prime-mask, not payload fields. Resolve header → prime-mask (either directly in prime-mask mode or via `resolved_prime_mask` cached/loaded for payload mode) then apply masked-key computation.

Rel_flags mapping (bit positions within 5-bit `rel_flags`):

- `bit0` (0x01): HAS_CHILDREN — compound contains child compounds
- `bit1` (0x02): HAS_RELATIONS — compound has relation entries
- `bit2` (0x04): HAS_RESOLVED_MASK — `resolved_prime_mask` is cached/available
- `bit3` (0x08): IS_NAMED — compound has a stable name/alias
- `bit4` (0x10): NEEDS_ENRICHMENT — background enrichment recommended
 - `bit4` (0x10): NEEDS_ENRICHMENT — background enrichment recommended
 
Note: consider reserving an explicit `HAS_APPROX_MASK` flag for `rel_flags` (or expanding
`rel_flags` width) to indicate the presence of an approximate membership filter (Bloom). For
now, deployments may temporarily reuse `NEEDS_ENRICHMENT` to signal enrichment/approximate-mask
presence, but a dedicated flag is recommended for clarity in future schema updates.

Packing/unpacking tests should include verifying these flag mappings.

Sharding & Consistent Hashing
- `compound_id` is the primary key for locating compounds across the cluster. Each node owns a subset of `compound_id` values determined by the cluster's consistent-hashing scheme.
- Recommendation: use Jump Consistent Hash or Rendezvous (Highest Random Weight) hashing with a configurable replication factor `R` and a configurable number of virtual nodes per physical node for smoother rebalancing.
- Documented behaviors to include:
  - Hash function and parameters (virtual nodes, replication factor).
  - Node membership service and how membership changes are propagated (gossip, central registry, or orchestrator).
  - Ownership changes: graceful handoff (drain), limited-time dual ownership during migration window, and background re-replication.
  - Request handling when owner unavailable: retry with backoff; if still unavailable, either redirect client to a new owner (HTTP-style redirect) or proxy the request through a healthy node (configurable). Log and emit metrics on redirects/proxies.

RocksDB & Indexing notes
- Masked-key unchanged: `masked_key = prime_mask & rule_mask` (64-bit). Serialize as 8-byte big-endian for RocksDB keys.
- RocksDB index key: `masked_key` (8B BE) || `rel_flags` (1B) → 9-byte key. Value: compressed/varint list of rule IDs.
- Recovery: rely on RocksDB WAL and checkpoints; provide an offline rebuild path from rule compounds if necessary.

Migration & rollout
- Gate writes behind `ENABLE_NEW_PAYLOAD` feature flag. Readers must continue to accept legacy prime-mask encodings (`schema_tag==0`).
- Dual-read: in canary mode read both legacy and new payload paths and compare results; collect metrics on mismatches.
- Backfill: run offline jobs to compute and persist `resolved_prime_mask` for hot compounds; do not rely on the payload format for backfill correctness.

Examples
- Example packed value (conceptual):
  - `compound_id = 12345`, `rel_flags = 0b00011`, `schema_tag = 1`
  - `pack_compound_payload(12345, 0b11, 1)` → returns 64-bit integer with MSB set.

Recommended unit tests additions
- Round-trip tests for edge values (compound_id=0, compound_id=2**54-1; rel_flags=0/31; schema_tag=1/15).
- Test that readers treat `schema_tag==0` as legacy prime-mask.
- Test behavior on unknown `schema_tag` (log + safe failure / permissive canary).
- Fuzz test: random payload bits should either parse to valid fields or fail safely.

14. Docs-only: `core/primebit.py` docstring & example helpers

This section provides a copy-pasteable, docs-only reference implementation and top-level docstring for `core/primebit.py`. The canonical implementation in code should mirror this behavior; tests should exercise the same examples.

```python
"""
core.primebit helpers (docs reference)

This module provides helpers to pack/unpack PrimeBit compound payloads and
to detect compound-mode vs prime-mask mode. See docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md
for canonical bit layouts and rollout guidance.

APIs (reference):
 - pack_compound_payload(compound_id: int, rel_flags: int, schema_tag: int) -> int
 - unpack_compound_payload(payload: int) -> tuple[int, int, int]
 - primebit_from_payload(payload: int) -> int
 - primebit_to_payload(value: int) -> int
 - is_compound_primebit(value: int) -> bool

Constants (bit widths/masks):
COMPOUND_FLAG = 1 << 63
COMPOUND_ID_BITS = 54
REL_FLAGS_BITS = 5
SCHEMA_TAG_BITS = 4
PAYLOAD_MASK = (1 << 63) - 1
COMPOUND_ID_MASK = (1 << COMPOUND_ID_BITS) - 1
REL_FLAGS_MASK = (1 << REL_FLAGS_BITS) - 1
SCHEMA_TAG_MASK = (1 << SCHEMA_TAG_BITS) - 1

def pack_compound_payload(compound_id: int, rel_flags: int, schema_tag: int) -> int:
  if not (0 <= compound_id < (1 << COMPOUND_ID_BITS)):
    raise ValueError('compound_id out of range')
  if not (0 <= rel_flags < (1 << REL_FLAGS_BITS)):
    raise ValueError('rel_flags out of range')
  if not (0 <= schema_tag < (1 << SCHEMA_TAG_BITS)):
    raise ValueError('schema_tag out of range')

  payload = compound_id & COMPOUND_ID_MASK
  payload |= (rel_flags & REL_FLAGS_MASK) << COMPOUND_ID_BITS
  payload |= (schema_tag & SCHEMA_TAG_MASK) << (COMPOUND_ID_BITS + REL_FLAGS_BITS)
  return COMPOUND_FLAG | payload

def unpack_compound_payload(primebit_value: int) -> tuple[int, int, int]:
  if (primebit_value >> 63) & 1 == 0:
    raise ValueError('not a compound payload')
  payload = primebit_value & PAYLOAD_MASK
  compound_id = payload & COMPOUND_ID_MASK
  rel_flags = (payload >> COMPOUND_ID_BITS) & REL_FLAGS_MASK
  schema_tag = (payload >> (COMPOUND_ID_BITS + REL_FLAGS_BITS)) & SCHEMA_TAG_MASK
  return (compound_id, rel_flags, schema_tag)

def primebit_from_payload(payload: int) -> int:
  # If `payload` is already a full 64-bit value with MSB set, return it;
  # otherwise OR the COMPOUND_FLAG.
  return payload | COMPOUND_FLAG

def primebit_to_payload(value: int) -> int:
  # Strip MSB and return low-63 payload value.
  return value & PAYLOAD_MASK

def is_compound_primebit(value: int) -> bool:
  return ((value >> 63) & 1) == 1

def get_compound_header(compound_id: int) -> dict:
  # Docs-only: semantic API contract. Implementers should return at least:
  # { 'primebit': int, 'rel_flags': int, 'resolved_prime_mask': Optional[int] }
  raise NotImplementedError
"""
```

Notes:
- Add this docstring to the real `core/primebit.py` when implementing code.
- Use the constants above to avoid magic numbers across the codebase; prefer the helpers over raw bit ops.

15. Implemented artifacts & integration notes

- Implemented in docs (reference): the docs-only `core.primebit` reference implementation and examples (see Section 14). This is a canonical, copy-pasteable reference intended to be ported into `core/primebit.py`.
- Pending runtime artifacts (to be implemented from docs):
  - `core/primebit.py` (pack/unpack, `is_compound_primebit`, `primebit_from_payload`, `primebit_to_payload`, `get_compound_header` and helpers/constants).
  - Unit tests exercising pack/unpack bounds, legacy `schema_tag==0` behavior, and round-trip invariants.
  - CI codemod and pre-commit checks to replace raw bit ops with helper calls.

PrimeBit runtime API (merge checklist):
- `pack_compound_payload(compound_id: int, rel_flags: int, schema_tag: int) -> int`
- `unpack_compound_payload(payload: int) -> tuple[int, int, int]`
- `primebit_from_payload(payload: int) -> int`
- `primebit_to_payload(value: int) -> int`
- `is_compound_primebit(value: int) -> bool`
- `get_compound_header(compound_id: int) -> dict` (header-only read; should return `primebit`, `rel_flags`, optionally `resolved_prime_mask`)
- `get_resolved_prime_mask(compound_id: int) -> Optional[int]` (may load/compute and cache)

Merge checklist for implementers:
- Port the docs-only reference into `core/primebit.py` with identical constants and behavior.
- Add top-level docstring linking to `docs/PRIMEBIT/PRIMEBIT_ARCHITECTURE.md` and `docs/COMPOUND_PAYLOAD_SPEC.md`.
- Add unit tests mirroring Section 13/14 examples and edge-cases.
- Run codemod to replace raw `>> 63` / `& 0x7FFFFFFFFFFFFFFF` occurrences with `is_compound_primebit` / `primebit_to_payload` and add TODOs for remaining manual cases.
- Add metrics hooks where appropriate (`primebit_unpack_latency`, `payload_read_count`, `payload_write_count`).
- Deploy behind `ENABLE_NEW_PAYLOAD` feature flag and exercise dual-read canary before enabling writes.

Tracking: update the project TODOs and changelog when runtime code is landed; reference this doc section in the commit message to tie implementation to architecture.

## Operational guidance (atomicity, enrichment, migration, cache, concurrency, observability)

Atomic updates and invalidation
- Use a transactional helper when modifying structural relations: update the `relations` payload
  and the `resolved_prime_mask` (or mark it stale) within the same atomic operation to avoid
  transient inconsistencies. If the storage backend lacks multi-document transactions, provide a
  strong helper that performs a compare-and-swap on the `main` header after updating relation
  partitions.
- Provide `invalidate_resolved_mask(compound_id)` to mark a header stale and enqueue background
  recompute; prefer marking stale + background recompute over synchronous full recompute on writes.

Background enrichment worker behaviour
- Enrichment jobs should be idempotent, rate-limited, and retryable. Use a job queue with
  configurable concurrency and a small priority hint. Jobs must detect and avoid cycles and
  opportunistically back off for very large subtrees.
- Record metrics per job: enqueue time, compute duration, whether a full recompute or incremental
  update was used, and result (success/failure). Emit alerts when enrichment backlog exceeds
  configured thresholds.

Migration checklist (operator-facing)
- Gate payload writes with `ENABLE_NEW_PAYLOAD` and run dual-read canary mode: read both legacy
  and payload paths and compare results for a representative sample of compounds.
- Backfill hot compounds by running offline jobs that compute and persist `resolved_prime_mask` and
  (optionally) `approx_prime_bloom`. Verify parity with legacy behavior before enabling writes.
- Deploy feature flag enabling in stages: canary -> limited cohort -> full rollout. Monitor
  `resolved_mask_cache_hits`, `payload_read_count`, and mismatch metrics during rollout.

Cache policy guidance
- Recommend an in-memory LRU cache for `main` headers with a default TTL (e.g., 5m) and a
  configurable size depending on working set. Cache both `resolved_prime_mask` and `approx_prime_bloom`.
- Instrument cache hits/misses and provide a warm-up script to prepopulate hot compound masks when
  starting a node.

Concurrency & cycles
- Compute `resolved_prime_mask` iteratively using topological sort where possible. Detect cycles by
  tracking visited nodes; if a cycle is found, break it deterministically (e.g., ignore back-edge
  for mask union) and log an audit event for reconciliation.
- Prefer eventual consistency for very large graphs: short-lived drift is acceptable if corrected by
  background reconciliation jobs and if approximate filters prevent catastrophic misses.

Observability & alerting
- Consolidate the key metrics (examples):
  - `resolved_mask_cache_hits` (gauge/counter)
  - `resolved_mask_compute_latency` (histogram)
  - `payload_read_count` / `payload_write_count` (counters)
  - `approx_filter_queries` / `false_positive_triggered_resolves` (counters)
  - `enrichment_backlog` (gauge)
- Alert on: rising synchronous compute rate, enrichment backlog growth, and guardrail thresholds for
  false-positive rates if approximate filters are deployed.

Developer ergonomics
- Provide a small CLI utility `primebit inspect <value>` to decode primebit values and payloads for
  debugging. Add a pre-commit codemod recipe to find and replace raw bit operations (`>> 63`, mask
  constants) with calls to `core.primebit` helpers.

End of operational guidance.

