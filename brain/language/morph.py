"""
Pablo Language — morph & lemma stub (v0.1, language-only)

What it does (deterministic, tiny):
- Produces a coarse POS id and a lemma string per token.
- Packs a small morph bitfield (currently unused by others, but ready).
- Uses a tiny in-memory vocab to map lemma strings -> integer IDs.
- Can annotate an existing token-only Graph with (label_id=lemma_id, sub_type=POS).
- Marks simple stopwords with NF_IS_STOP.

Notes
- English-only heuristics for v0.1.
- We do NOT split contractions here; lemma('Don’t') == "don’t" (normalized quotes).
- Safe defaults: unknown word => POS=X, lemma=lowercased form.

You can extend/replace this with an FST later without changing callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple

import re

# Import tokenizer Token + flags
from .tokenizer import Token, tokenize, TF_NUM, TF_PUNCT
# Graph flags used when annotating
from .graph_builder import NF_IS_STOP


# ---------------------------
# POS ids (coarse)
# ---------------------------

class POS(IntEnum):
    X = 0
    NOUN = 1
    VERB = 2
    ADJ = 3
    ADV = 4
    PRON = 5
    DET = 6
    ADP = 7   # preposition/subposition
    CCONJ = 8
    SCONJ = 9
    PUNCT = 10
    NUM = 11
    PROPN = 12
    AUX = 13


# ---------------------------
# Morph bitfield (16 bits for v0.1)
# layout:  0..3 POS (redundant but handy) | 4..5 TENSE | 6..7 NUMBER | 8..9 PERSON
# ---------------------------

TENSE_NONE, TENSE_PRES, TENSE_PAST = 0, 1, 2
NUM_NONE, NUM_SING, NUM_PLUR = 0, 1, 2
PER_NONE, PER_1, PER_2, PER_3 = 0, 1, 2, 3

def pack_bits(pos: int, tense: int = 0, num: int = 0, per: int = 0) -> int:
    return (pos & 0xF) | ((tense & 0x3) << 4) | ((num & 0x3) << 6) | ((per & 0x3) << 8)


# ---------------------------
# Tiny vocab (process-local)
# ---------------------------

class Vocab:
    def __init__(self) -> None:
        self._tok2id: dict[str, int] = {}
        self._id2tok: list[str] = []

    def get_id(self, s: str) -> int:
        if s in self._tok2id:
            return self._tok2id[s]
        idx = len(self._id2tok) + 1  # 0 is reserved for "unknown"
        self._tok2id[s] = idx
        self._id2tok.append(s)
        return idx

    def get_str(self, i: int) -> str:
        if i <= 0 or i > len(self._id2tok):
            return ""
        return self._id2tok[i - 1]


# ---------------------------
# Heuristics dictionaries
# ---------------------------

_STOP = {
    "the","a","an","and","or","but","if","because","that","which","who","whom","whose",
    "to","of","in","on","at","by","for","with","from","as","than","then","so","yet",
    "is","are","was","were","be","been","being","do","does","did","have","has","had",
    "not","no","yes","it","i","you","he","she","we","they","me","him","her","us","them",
    "this","that","these","those"
}

_PRON = {"i","you","he","she","it","we","they","me","him","her","us","them","my","your","his","her","our","their"}
_DET  = {"the","a","an","this","that","these","those"}
_ADP  = {"of","to","in","on","at","by","for","with","from","as","into","onto","over","under","between","through"}
_CCONJ = {"and","or","but","nor","yet","so"}
_SCONJ = {"because","if","that","although","though","when","while","since","unless"}
_AUX_MAP = {
    # be
    "am":("be", TENSE_PRES, NUM_SING, PER_1),
    "are":("be", TENSE_PRES, 0, 0),
    "is":("be", TENSE_PRES, NUM_SING, PER_3),
    "was":("be", TENSE_PAST, NUM_SING, PER_1),
    "were":("be", TENSE_PAST, 0, 0),
    "be":("be", 0, 0, 0),
    "been":("be", 0, 0, 0),
    "being":("be", 0, 0, 0),
    # have
    "have":("have", TENSE_PRES, 0, 0),
    "has":("have", TENSE_PRES, NUM_SING, PER_3),
    "had":("have", TENSE_PAST, 0, 0),
    # do
    "do":("do", TENSE_PRES, 0, 0),
    "does":("do", TENSE_PRES, NUM_SING, PER_3),
    "did":("do", TENSE_PAST, 0, 0),
    # modals (treated as AUX, no tense)
    "can":("can", 0, 0, 0), "could":("could", 0, 0, 0),
    "may":("may", 0, 0, 0), "might":("might", 0, 0, 0),
    "must":("must", 0, 0, 0), "should":("should", 0, 0, 0),
    "would":("would", 0, 0, 0), "will":("will", 0, 0, 0), "shall":("shall", 0, 0, 0),
}

# crude proper noun detector (initial cap + letters)
_RE_INITIAL_CAP = re.compile(r"^[A-Z][A-Za-z]+$")


def _norm_apostrophes(s: str) -> str:
    return s.replace("’", "'").replace("‘", "'")


def _strip_possessive(s: str) -> str:
    # handles "'s" and "’s" and bare trailing apostrophe
    s2 = _norm_apostrophes(s)
    if s2.endswith("'s"):
        return s2[:-2]
    if s2.endswith("'"):
        return s2[:-1]
    return s2


def _lemma_guess(lower: str) -> str:
    # very small stemmer-ish: try ing/ed/s
    if lower.endswith("ing") and len(lower) > 4:
        return lower[:-3]
    if lower.endswith("ed") and len(lower) > 3:
        return lower[:-2]
    if lower.endswith("s") and len(lower) > 3 and not lower.endswith("ss"):
        return lower[:-1]
    return lower


@dataclass
class MorphInfo:
    lemma: str
    lemma_id: int
    pos: int
    bits: int
    is_stop: bool


def analyze_tokens(tokens: List[Token], vocab: Vocab) -> List[MorphInfo]:
    out: List[MorphInfo] = []
    for t in tokens:
        raw = t.text
        norm = _strip_possessive(_norm_apostrophes(raw))
        lower = norm.lower()

        # punctuation
        if t.flags & TF_PUNCT:
            lemma = norm
            pos = POS.PUNCT
            bits = pack_bits(pos)
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, bits, False))
            continue

        # numbers or url-like (very naive)
        if t.flags & TF_NUM:
            pos = POS.NUM
            lemma = lower
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), False))
            continue

        # closed classes
        if lower in _PRON:
            pos = POS.PRON
            lemma = lower
            is_stop = True
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), is_stop))
            continue

        if lower in _DET:
            pos = POS.DET
            lemma = lower
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), True))
            continue

        if lower in _ADP:
            pos = POS.ADP
            lemma = lower
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), True))
            continue

        if lower in _CCONJ:
            pos = POS.CCONJ
            lemma = lower
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), True))
            continue

        if lower in _SCONJ:
            pos = POS.SCONJ
            lemma = lower
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), True))
            continue

        # aux/verbs (irregular + modals)
        if lower in _AUX_MAP:
            lemma, tense, num, per = _AUX_MAP[lower]
            pos = POS.AUX
            bits = pack_bits(pos, tense, num, per)
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, bits, lower in _STOP))
            continue

        # proper nouns (very crude: initial cap and letters only -> PROPN, lemma = surface)
        if _RE_INITIAL_CAP.match(raw):
            pos = POS.PROPN
            lemma = raw  # keep case for names
            out.append(MorphInfo(lemma, vocab.get_id(lemma), pos, pack_bits(pos), False))
            continue

        # fallback: NOUN/VERB-ish guess; keep simple
        # try simple lemma guess for verbs/adjectives, else noun
        guess = _lemma_guess(lower)
        pos = POS.NOUN  # conservative default
        out.append(MorphInfo(guess, vocab.get_id(guess), pos, pack_bits(pos), lower in _STOP))
    return out


# ---------------------------
# Graph annotation helper
# ---------------------------

def annotate_graph(g, tokens: List[Token], morphs: List[MorphInfo]) -> None:
    """
    In-place: set node.sub_type = POS id, node.label_id = lemma_id.
    Also set NF_IS_STOP for stopwords.
    Assumes graph nodes were added in the same order as the tokenizer produced tokens.
    """
    from .graph_builder import NF_IS_STOP
    n = min(len(g.nodes), len(tokens), len(morphs))
    for i in range(n):
        node = g.nodes[i]
        mi = morphs[i]
        node.sub_type = int(mi.pos)
        node.label_id = int(mi.lemma_id)
        if mi.is_stop:
            node.flags |= NF_IS_STOP


# ---------------------------
# Quick manual check
# ---------------------------

if __name__ == "__main__":
    text = "He said, “Don’t move.” Are you okay?"
    toks = tokenize(text)
    vocab = Vocab()
    morphs = analyze_tokens(toks, vocab)

    # Pretty-print a few
    from pprint import pprint
    pprint([(t.text, mi.lemma, int(mi.pos), mi.bits, mi.is_stop) for t, mi in zip(toks, morphs)][:12])

    # Annotate a graph
    from .tokenizer import tokens_to_graph
    g = tokens_to_graph(text)
    annotate_graph(g, toks, morphs)
    # Show (label_id, sub_type) for first 8 nodes
    print([(n.label_id, n.sub_type) for n in g.nodes[:8]])
