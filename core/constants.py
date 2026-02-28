"""
Canonical prime constants and mappings.
Prime indices are assigned alphabetically 0-62.
"""

# Alphabetically sorted primes with indices 0-62
PRIMES = [
    "AFTER",    # 0
    "ALL",      # 1
    "AT",       # 2
    "BAD",      # 3
    "BE",       # 4
    "BECAUSE",  # 5
    "BEFORE",   # 6
    "BETWEEN",  # 7
    "BODY",     # 8
    "CAN",      # 9
    "CAUSE",    # 10
    "CHANGE",   # 11
    "DATA",     # 12
    "DO",       # 13
    "DOWN",     # 14
    "ENTITY",   # 15
    "FAR",      # 16
    "FEEL",     # 17
    "FROM",     # 18
    "GOOD",     # 19
    "HAVE",     # 20
    "HEAR",     # 21
    "HEAT",     # 22
    "HERE",     # 23
    "IN",       # 24
    "KIND",     # 25
    "KNOW",     # 26
    "LAST",     # 27
    "LEFT",     # 28
    "LESS",     # 29
    "LIFE",     # 30
    "LIGHT",    # 31
    "MAKE",     # 32
    "MANY",     # 33
    "MORE",     # 34
    "MOVE",     # 35
    "NEAR",     # 36
    "NEED",     # 37
    "NONE",     # 38
    "NOW",      # 39
    "ONE",      # 40
    "OPEN",     # 41
    "OTHER",    # 42
    "PART",     # 43
    "READ",     # 44
    "RIGHT",    # 45
    "SAY",      # 46
    "SEE",      # 47
    "SELF",     # 48
    "SIDE",     # 49
    "SOME",     # 50
    "SYMBOL",   # 51
    "THINK",    # 52
    "THIS",     # 53
    "TIME",     # 54
    "TO",       # 55
    "TOUCH",    # 56
    "UP",       # 57
    "USE",      # 58
    "WANT",     # 59
    "WITH",     # 60
    "WRITE",    # 61
    "YOU",      # 62
]

# Create reverse mappings
PRIME_TO_INDEX = {prime: idx for idx, prime in enumerate(PRIMES)}
INDEX_TO_PRIME = {idx: prime for idx, prime in enumerate(PRIMES)}

# Bitmask for primes (bits 0-62 set)
PRIME_MASK = 0x7FFFFFFFFFFFFFFF  # 63 bits for primes

# Compound flag bit (bit 63)
COMPOUND_FLAG_BIT = 63
COMPOUND_FLAG_MASK = 1 << COMPOUND_FLAG_BIT

# Validate we have exactly 63 primes
assert len(PRIMES) == 63, f"Expected 63 primes, got {len(PRIMES)}"