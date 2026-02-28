# PrimeBit — Architecture & Implementation

This file is the canonical implementation reference for `core/primebit.py`.
It is phase-separated: Phase 1 is the complete implementable target. Phase 2+
sections are preserved for future reference and must not be implemented until
the relevant phase begins.

---

## PHASE 1 — Implement Now

---

### 1. Scope & Purpose

PrimeBit is a pure encoding utility. It is not a prime, not a cognitive component,
and has no dependencies on any other PABLO module. Its only job is to pack and
unpack meaning into a 64-bit integer in a way that is fast, deterministic, and
consistent across the entire system.

All semantic decisions (what primes a compound has, what a compound means) belong
to other components. PrimeBit only answers: "given these primes or this compound
reference, what is the correct 64-bit representation, and vice versa."

`core/primebit.py` must have zero imports from other PABLO modules.

---

### 2. Canonical Prime Index

The following is the authoritative prime-to-bit mapping. Ordering is strictly
alphabetical. This mapping is frozen — it must never change after first use, as
all stored PrimeBit values depend on it.

```python
PRIME_INDEX = [
    "AFTER",    # bit 0
    "ALL",      # bit 1
    "AT",       # bit 2
    "BAD",      # bit 3
    "BE",       # bit 4
    "BECAUSE",  # bit 5
    "BEFORE",   # bit 6
    "BETWEEN",  # bit 7
    "BODY",     # bit 8
    "CAN",      # bit 9
    "CAUSE",    # bit 10
    "CHANGE",   # bit 11
    "DATA",     # bit 12
    "DO",       # bit 13
    "DOWN",     # bit 14
    "ENTITY",   # bit 15
    "FAR",      # bit 16
    "FEEL",     # bit 17
    "FROM",     # bit 18
    "GOOD",     # bit 19
    "HAVE",     # bit 20
    "HEAR",     # bit 21
    "HEAT",     # bit 22
    "HERE",     # bit 23
    "IN",       # bit 24
    "KIND",     # bit 25
    "KNOW",     # bit 26
    "LAST",     # bit 27
    "LEFT",     # bit 28
    "LESS",     # bit 29
    "LIFE",     # bit 30
    "LIGHT",    # bit 31
    "MAKE",     # bit 32
    "MANY",     # bit 33
    "MORE",     # bit 34
    "MOVE",     # bit 35
    "NEAR",     # bit 36
    "NEED",     # bit 37
    "NONE",     # bit 38
    "NOW",      # bit 39
    "ONE",      # bit 40
    "OPEN",     # bit 41
    "OTHER",    # bit 42
    "PART",     # bit 43
    "READ",     # bit 44
    "RIGHT",    # bit 45
    "SAY",      # bit 46
    "SEE",      # bit 47
    "SELF",     # bit 48
    "SIDE",     # bit 49
    "SOME",     # bit 50
    "SYMBOL",   # bit 51
    "THINK",    # bit 52
    "THIS",     # bit 53
    "TIME",     # bit 54
    "TO",       # bit 55
    "TOUCH",    # bit 56
    "UP",       # bit 57
    "USE",      # bit 58
    "WANT",     # bit 59
    "WITH",     # bit 60
    "WRITE",    # bit 61
    "YOU",      # bit 62
]

# Derived lookup (build once at module load)
PRIME_TO_BIT = {name: idx for idx, name in enumerate(PRIME_INDEX)}
```

Total: 63 primes occupying bits 0–62. Bit 63 is reserved as the compound flag
(see Section 3). The PRIME_INDEX list and PRIME_TO_BIT dict are the single source
of truth — all bit operations must derive from these, never from hardcoded integers.

---

### 3. Bit Layout

A PrimeBit value is a 64-bit unsigned integer with two mutually exclusive modes:

**Prime-mask mode** (`bit63 == 0`):
- Bits 0–62 are prime flags. Each bit corresponds to one prime per the canonical
  index above. A set bit means that prime is present in the set.
- This is the default mode for describing meaning.
- Example: a value with bits 35 and 44 set represents {MOVE, READ}.

**Compound-payload mode** (`bit63 == 1`):
- Bit 63 is the COMPOUND_FLAG, indicating this value references a compound rather
  than encoding a prime set directly.
- Bits 0–62 encode a compact payload (see Section 4).
- This mode is used when a PrimeBit slot needs to reference a compound by ID
  rather than describe it inline.

These two modes must never be confused. All code that receives a PrimeBit value
must check `is_compound_primebit()` before interpreting the low bits.

---

### 4. Compound Payload — Canonical Bitfield Layout

When `bit63 == 1`, the low 63 bits encode the following fields. Bit numbering
uses LSB = bit 0 convention.

```
bit 63       : COMPOUND_FLAG (always 1 in payload mode)
bits  0..53  : compound_id   (54 bits — up to ~18 quadrillion unique compounds)
bits 54..58  : rel_flags     (5 bits  — quick hint flags, see Section 6)
bits 59..62  : schema_tag    (4 bits  — payload schema version, 0..15)
```

**schema_tag values:**
- `0` — reserved for legacy / prime-mask mode sentinel. Writers must never emit
  `schema_tag=0` for compound payloads.
- `1` — current canonical layout (this document). Use for all new writes.
- `2–15` — reserved for future schema versions.

On read, if `schema_tag` is unknown (greater than the highest supported version),
treat the payload defensively: log the event and either reject or perform
best-effort parsing of known fields. Never silently misinterpret.

---

### 5. Required Helpers — Phase 1 API Surface

All of the following must be implemented in `core/primebit.py` and exported.
No other module should perform raw bit operations on PrimeBit values — always
use these helpers.

```python
# ── Constants ────────────────────────────────────────────────────────────────

COMPOUND_FLAG      = 1 << 63
PAYLOAD_MASK       = (1 << 63) - 1          # low 63 bits

COMPOUND_ID_BITS   = 54
REL_FLAGS_BITS     = 5
SCHEMA_TAG_BITS    = 4

COMPOUND_ID_MASK   = (1 << COMPOUND_ID_BITS) - 1
REL_FLAGS_MASK     = (1 << REL_FLAGS_BITS) - 1
SCHEMA_TAG_MASK    = (1 << SCHEMA_TAG_BITS) - 1

CURRENT_SCHEMA_TAG = 1


# ── Prime-mask helpers ────────────────────────────────────────────────────────

def prime_mask(prime_names: list[str]) -> int:
    """Return a prime-mask PrimeBit for the given list of prime names.

    Raises ValueError for any unknown prime name.
    """

def has_prime(primebit: int, prime_name: str) -> bool:
    """Return True if the prime-mask has the given prime set.

    Raises if primebit is in compound mode — caller must resolve first.
    """

def has_all_primes(primebit: int, prime_names: list[str]) -> bool:
    """Return True if all given primes are set in the prime-mask."""

def prime_names_from_mask(primebit: int) -> list[str]:
    """Return the list of prime names set in a prime-mask PrimeBit."""


# ── Mode detection ────────────────────────────────────────────────────────────

def is_compound_primebit(value: int) -> bool:
    """Return True if bit63 is set (compound-payload mode)."""
    return bool((value >> 63) & 1)


# ── Compound payload pack / unpack ────────────────────────────────────────────

def pack_compound_payload(
    compound_id: int,
    rel_flags: int,
    schema_tag: int = CURRENT_SCHEMA_TAG,
) -> int:
    """Pack fields into a 64-bit compound-mode PrimeBit value.

    Always sets bit63. schema_tag must not be 0 (reserved for legacy).

    Returns the full 64-bit PrimeBit integer.
    """
    if not (0 <= compound_id < (1 << COMPOUND_ID_BITS)):
        raise ValueError(f"compound_id out of range: {compound_id}")
    if not (0 <= rel_flags < (1 << REL_FLAGS_BITS)):
        raise ValueError(f"rel_flags out of range: {rel_flags}")
    if not (1 <= schema_tag < (1 << SCHEMA_TAG_BITS)):
        raise ValueError(f"schema_tag must be 1–15, got: {schema_tag}")

    payload  = compound_id & COMPOUND_ID_MASK
    payload |= (rel_flags  & REL_FLAGS_MASK)  << COMPOUND_ID_BITS
    payload |= (schema_tag & SCHEMA_TAG_MASK) << (COMPOUND_ID_BITS + REL_FLAGS_BITS)
    return COMPOUND_FLAG | payload


def unpack_compound_payload(primebit_value: int) -> tuple[int, int, int]:
    """Unpack a compound-mode PrimeBit into (compound_id, rel_flags, schema_tag).

    Raises ValueError if bit63 is not set.
    """
    if not is_compound_primebit(primebit_value):
        raise ValueError("not a compound-mode PrimeBit")
    payload     = primebit_value & PAYLOAD_MASK
    compound_id = payload & COMPOUND_ID_MASK
    rel_flags   = (payload >> COMPOUND_ID_BITS) & REL_FLAGS_MASK
    schema_tag  = (payload >> (COMPOUND_ID_BITS + REL_FLAGS_BITS)) & SCHEMA_TAG_MASK
    return (compound_id, rel_flags, schema_tag)


def primebit_from_payload(raw_payload: int) -> int:
    """Given a raw 63-bit payload integer, return the full 64-bit compound PrimeBit.

    Input must always be a raw 63-bit payload (bit63 clear).
    This function always sets bit63. It never accepts a pre-flagged value.
    """
    if raw_payload & COMPOUND_FLAG:
        raise ValueError("raw_payload must not have bit63 set — pass the raw 63-bit value")
    return raw_payload | COMPOUND_FLAG


def primebit_to_payload(value: int) -> int:
    """Strip bit63 and return the raw 63-bit payload integer."""
    return value & PAYLOAD_MASK
```

**Note on `get_compound_header`:** this function requires reading from KNOW
(to retrieve `resolved_prime_mask` and full compound metadata). It does not
belong in `core/primebit.py`. It will be defined in KNOW's architecture as
`KNOW.get_compound_header(compound_id)`.

---

### 6. rel_flags — Bit Mapping

The 5-bit `rel_flags` field encodes quick hints that allow callers to make
routing and load decisions without fetching the full compound record.

```
bit 0  (0x01)  HAS_CHILDREN       — compound has child compound IDs
bit 1  (0x02)  HAS_RELATIONS      — compound has relation entries
bit 2  (0x04)  HAS_RESOLVED_MASK  — resolved_prime_mask is cached and valid
bit 3  (0x08)  IS_NAMED           — compound has a stable name or alias
bit 4  (0x10)  NEEDS_ENRICHMENT   — background enrichment is recommended
```

These are hints only — callers must not treat them as authoritative without
verification. A missing flag does not guarantee absence; it means the hint
was not set at write time.

```python
class RelFlags:
    HAS_CHILDREN      = 0x01
    HAS_RELATIONS     = 0x02
    HAS_RESOLVED_MASK = 0x04
    IS_NAMED          = 0x08
    NEEDS_ENRICHMENT  = 0x10
```

---

### 7. Bitwise Operators on Prime-Masks

The following operations are defined only for prime-mask mode (`bit63 == 0`).
Any attempt to perform these on a compound-mode PrimeBit must raise immediately —
never silently operate on payload bits.

```
mask_a & mask_b     — intersection: primes present in both sets
mask_a | mask_b     — union: primes present in either set
mask_a ^ mask_b     — symmetric difference
~mask_a             — complement, masked to bits 0–62 only
implies(a, b)       — logical implication: (~a | b) masked to bits 0–62
```

When a caller needs to perform set operations involving a compound-mode PrimeBit,
it must first resolve the compound to its `resolved_prime_mask` via
`KNOW.get_compound_header()`, then operate on the resulting prime-mask. This
resolution must never happen silently inside PrimeBit helpers.

---

### 8. Tests — Phase 1

All of the following must pass before `core/primebit.py` is considered complete.

**Pack / unpack round-trips:**
- `unpack(pack(id, flags, tag)) == (id, flags, tag)` for min and max field values.
- `compound_id = 0`, `rel_flags = 0`, `schema_tag = 1`.
- `compound_id = 2**54 - 1`, `rel_flags = 0x1F`, `schema_tag = 15`.

**Mode detection:**
- `is_compound_primebit(pack_compound_payload(...))` returns `True`.
- `is_compound_primebit(prime_mask(["READ", "MOVE"]))` returns `False`.

**schema_tag = 0 rejection:**
- `pack_compound_payload(1, 0, schema_tag=0)` raises `ValueError`.

**`primebit_from_payload` contract:**
- Passing a value with bit63 already set raises `ValueError`.
- Passing a clean 63-bit value returns a value with bit63 set.

**Prime-mask helpers:**
- `prime_mask(["READ", "MOVE"])` sets exactly bits 44 and 35.
- `has_prime(mask, "READ")` returns `True`; `has_prime(mask, "FEEL")` returns `False`.
- `prime_names_from_mask(mask)` returns `["MOVE", "READ"]` (or equivalent sorted list).

**Operator guard:**
- All bitwise helpers raise when called with a compound-mode PrimeBit input.

**Out-of-range inputs:**
- `compound_id >= 2**54` raises `ValueError`.
- `rel_flags >= 32` raises `ValueError`.
- `schema_tag >= 16` raises `ValueError`.
- Unknown prime name in `prime_mask()` raises `ValueError`.

---

### 9. Security & Safety Notes

- `core/primebit.py` accepts no user input directly. All inputs arrive from
  internal PABLO components. Range validation in helpers is a correctness
  guard, not a security boundary.
- The PRIME_INDEX list must be treated as a compile-time constant. No runtime
  code may append to, remove from, or reorder it. Any such change would silently
  corrupt all stored PrimeBit values.
- Raw bit operations (`>> 63`, `& 0x7FFFFFFFFFFFFFFF`) must not appear outside
  `core/primebit.py`. All other modules use the helpers.

---

## PHASE 2+ — Deferred (Do Not Implement Yet)

The following sections describe infrastructure needed at scale. They are
preserved here to inform future architecture decisions. Nothing below this
line should be implemented in Phase 1 or 2.

---

### D1. resolved_prime_mask Caching & Invalidation

When compounds have children, their effective prime set is the union of all
descendant prime masks. Computing this recursively on every read is expensive.

Future work: cache `resolved_prime_mask` in KNOW metadata. Invalidate on child
updates. Provide `invalidate_resolved_mask(compound_id)` to mark stale and enqueue
background recompute. Prefer stale + async recompute over synchronous full recompute
on writes.

Background enrichment jobs must be idempotent, rate-limited, retryable, and
cycle-aware (topological sort; break back-edges deterministically on cycle detection).

---

### D2. Approximate Filters (Bloom)

For very large compound trees, even background recompute of `resolved_prime_mask`
can cause load spikes. A Bloom filter (`approx_prime_bloom`) stored alongside the
compound header can serve as a fast "definitely not present" check, avoiding many
unnecessary resolves.

False positives trigger extra resolves (acceptable). False negatives are impossible
with Bloom (safe). Choose filter size to balance false positive rate (~1–2%) against
storage cost.

Add `HAS_APPROX_MASK` to `rel_flags` (requires expanding to 6 bits or repurposing
a flag) when this is implemented.

Helpers to add: `get_approx_prime_filter(compound_id)`,
`approx_filter_may_have_prime(filter_blob, primebit)`,
`enqueue_recompute_resolved_mask(compound_id, priority)`.

---

### D3. Indexing & Lookup

Rule lookup requires indexing by `masked_key = prime_mask & rule_mask`.

Future: index compounds by masked prime key to support efficient rule matching.
Masked key is computed over the resolved prime-mask, not payload fields.

---

### D4. Sharding & Consistent Hashing

`compound_id` (54 bits) is sized for distributed use. When PABLO scales to
multiple nodes, use Jump Consistent Hash or Rendezvous hashing with configurable
replication factor and virtual nodes.

Documented behaviors to define at that time: hash function and parameters, node
membership propagation, ownership changes and graceful handoff, request handling
when owner is unavailable.

---

### D5. RocksDB Notes

For high-throughput persistence: RocksDB index key = `masked_key` (8B BE) ||
`rel_flags` (1B) → 9-byte key. Value: compressed list of rule IDs. Rely on
RocksDB WAL and checkpoints for recovery; provide offline rebuild path from
rule compounds.

---

### D6. Migration & Feature Flag Rollout

When the compound payload format changes: gate writes behind
`ENABLE_NEW_PAYLOAD` feature flag. Run dual-read canary (compare legacy and
new paths). Backfill `resolved_prime_mask` for hot compounds offline before
enabling writes. Deploy in stages: canary → limited cohort → full rollout.

---

### D7. Observability & Alerting

Metrics to add when scale requires it:
- `primebit_unpack_latency` (histogram)
- `payload_read_count` / `payload_write_count` (counters)
- `resolved_mask_cache_hits` (gauge)
- `resolved_mask_compute_latency` (histogram)
- `approx_filter_queries` / `false_positive_triggered_resolves` (counters)
- `enrichment_backlog` (gauge)

CLI utility: `primebit inspect <value>` to decode any PrimeBit integer for
debugging. Pre-commit codemod to detect raw bit operations outside
`core/primebit.py`.