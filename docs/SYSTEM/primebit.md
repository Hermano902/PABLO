# PrimeBit

---

## Concept

PrimeBit is the compact encoding layer beneath every Compound in PABLO. It represents
the presence or absence of each of the 63 primes as a single 64-bit integer, enabling
O(1) set operations across all prime membership checks.

PrimeBit is not a data structure in the PLanguage sense — it is infrastructure. It
accelerates the operations that would otherwise require traversing Compound definitions:
membership checks, resonance matching, routing decisions. Every Compound carries two
PrimeBit values:

- `primebit` — the full set of assigned primes (may include unresolved orphans)
- `resolved_primebit` — the validated subset (only primes with confirmed Relations)

The distinction matters: `primebit` is used for broad resonance matching (is this
Compound anywhere near this concept?). `resolved_primebit` is used when coherence
matters (is the definition actually sound?).

---

### Why PrimeBit matters

KNOW's cued recall is the core memory mechanism: given the prime field of an active
scene, surface the Compounds whose primebit most overlaps with it. Without PrimeBit,
this requires iterating all stored Compounds and checking each definition. With PrimeBit,
it is a bitwise AND across integer values — orders of magnitude faster.

The same applies to routing (THINK's reasoning mode selection), DATA's validation
checks, and SYMBOL's resolution scoring. PrimeBit makes all of these O(1) or near-O(1).

---

### Canonical prime ordering

Bits 0–62 map to the 63 primes in **alphabetical order**. Alphabetical ordering is
used rather than conceptual grouping because it is stable — unambiguous and independent
of how the prime taxonomy evolves. Bit 63 is reserved.

Canonical assignment (alphabetical):

```
0: AFTER    1: ALL      2: AT       3: BAD      4: BE
5: BECAUSE  6: BEFORE   7: BETWEEN  8: BODY     9: CAN
10: CAUSE   11: CHANGE  12: DATA    13: DO      14: DOWN
15: ENTITY  16: FAR     17: FEEL    18: FROM    19: GOOD
20: HAVE    21: HEAR    22: HEAT    23: HERE    24: IN
25: KIND    26: KNOW    27: LAST    28: LEFT    29: LESS
30: LIFE    31: LIGHT   32: MAKE    33: MANY    34: MOVE
35: NEAR    36: NEED    37: NONE    38: NOW     39: ONE
40: OPEN    41: OTHER   42: PART    43: READ    44: RIGHT
45: SAY     46: SEE     47: SELF    48: SIDE    49: SOME
50: SYMBOL  51: THIS    52: THINK   53: TIME    54: TO
55: TOUCH   56: UP      57: USE     58: WANT    59: WITH
60: WRITE   61: YOU     62: YOU     ← (reserved, 62 used for future)
63: (reserved)
```

The canonical mapping lives in `core/primebit.py`. No inline bit arithmetic elsewhere.

---

## Architecture

### Core operations

```python
# Membership
PrimeBit.has(bits: int, prime: str) -> bool          # O(1)
PrimeBit.has_all(bits: int, primes: list[str]) -> bool  # O(n primes)

# Set operations
PrimeBit.union(a: int, b: int) -> int                # a | b
PrimeBit.intersection(a: int, b: int) -> int         # a & b
PrimeBit.overlap_count(a: int, b: int) -> int        # popcount(a & b)

# Construction
PrimeBit.from_primes(primes: list[str]) -> int
PrimeBit.from_prime(prime: str) -> int               # single bit
```

All bit math is centralised in `core/primebit.py`. Higher-level code uses these helpers
and never writes raw bit operations.

### Cued recall via PrimeBit

KNOW's `by_primebit_intersection(query_bits, top_k)` returns the Compounds whose
`primebit` has the highest `overlap_count` with `query_bits`. This is the mechanism
by which scene prime fields surface related memories — resonance, not text search.

### Compound primebit values

A Compound always maintains both values:

```python
compound.primebit           # full set: PrimeBit.union of all assigned prime bits
compound.resolved_primebit  # validated subset: only primes with Relations confirmed by DATA
```

DATA writes `resolved_primebit` during graph validation. It starts at 0 and grows as
Relations are confirmed. `grounded = True` when `resolved_primebit == primebit`.

### Implementation location

`core/primebit.py` — canonical prime→bit mapping, all helper functions.
No other file contains bit-level PrimeBit logic.

---

*See [compound.md](../PLANGUAGE/compound.md) for how Compounds carry PrimeBit values.*
*See [know.md](../PRIMES/know.md) for cued recall via primebit intersection.*
*See [data.md](../PRIMES/data.md) for how DATA writes resolved_primebit.*
