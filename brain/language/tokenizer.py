"""
Pablo Language — tokenizer (v0.1, language-only)

Policy (v0.1):
- Keep contractions/possessives as ONE token: "don't", "John’s".
- Keep hyphenated compounds as ONE token: "state-of-the-art", "10-mm".
- Keep URLs, emails, @mentions, #hashtags as ONE token.
- Ellipsis: "…" or "..." is ONE token.
- Punctuation (.,?!;: quotes, parens, dashes) are separate ONE-char tokens,
  except when captured by the protected tokens above.
- Preserve input exactly (no normalization). Offsets are Python codepoint indices.

Exports:
- dataclass Token { idx, text, start, end, flags }
- tokenize(text) -> list[Token]
- tokens_to_graph(text, *, graph_id=0, source_id=0, version=1) -> Graph
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import re

# ---------------------------
# Token shape
# ---------------------------

@dataclass
class Token:
    idx: int
    text: str
    start: int
    end: int
    flags: int  # bitfield


# Token flags (bit positions)
TF_CAP              = 1 << 0
TF_PUNCT            = 1 << 1
TF_NUM              = 1 << 2
TF_SENT_END_STRONG  = 1 << 3  # ., ?, !
TF_SENT_END_WEAK    = 1 << 4  # closers after end, or ellipsis

# ---------------------------
# Regexes (ordered by priority)
# ---------------------------

# URL (compact; no VERBOSE needed)
_URL = r"(?:https?://\S+|www\.\S+)"

# Email
_EMAIL = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"

# @mention / #hashtag
_HANDLE = r"[@#][A-Za-z0-9_]+"

# Ellipsis (unicode or three dots)
_ELLIPSIS = r"(?:\u2026|\.{3})"

# Hyphenated/apos word/number (don't, state-of-the-art, 10-mm, O’Neill)
_WORDISH = r"[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*"

# Single punctuation (quotes, parens, dashes, etc.)
_PUNCT = r"""[.,?!;:()\[\]{}"“”‘’—–\-]"""

# Whitespace (match-and-skip)
_WS = r"\s+"

_MASTER = re.compile(
    rf"(?P<URL>{_URL})|"
    rf"(?P<EMAIL>{_EMAIL})|"
    rf"(?P<HANDLE>{_HANDLE})|"
    rf"(?P<ELLIPSIS>{_ELLIPSIS})|"
    rf"(?P<WORD>{_WORDISH})|"
    rf"(?P<PUNCT>{_PUNCT})|"
    rf"(?P<WS>{_WS})",
    re.UNICODE
)

# Sets for sentence end logic
_TERMINATORS_STRONG = {".", "?", "!"}
_TERMINATORS_WEAK = {"\u2026", "..."}   # ← include "..." here

# Closers that can follow sentence-ending punctuation (flagged as weak after STRONG)
_CLOSERS = {'"', "”", "’", "'", ")", "]", "}", "»"}

# ---------------------------
# Core tokenizer
# ---------------------------

def tokenize(text: str) -> List[Token]:
    """Deterministic, lossless tokenizer following the v0.1 policy."""
    tokens: List[Token] = []
    i = 0
    idx = 0
    kinds: List[str] = []

    for m in _MASTER.finditer(text):
        kind = m.lastgroup
        s, e = m.span()
        if kind == "WS":
            i = e
            continue
        piece = text[s:e]
        flags = 0
        if kind in ("PUNCT", "ELLIPSIS"):
            flags |= TF_PUNCT
        if kind == "WORD":
            if any(ch.isdigit() for ch in piece):
                flags |= TF_NUM
            if any(ch.isalpha() for ch in piece) and piece[0].isupper():
                flags |= TF_CAP
        if kind in ("URL", "EMAIL", "HANDLE"):
            if any(ch.isdigit() for ch in piece):
                flags |= TF_NUM
        tokens.append(Token(idx=idx, text=piece, start=s, end=e, flags=flags))
        kinds.append(kind)
        idx += 1
        i = e

    if i < len(text):  # fallback (rare)
        piece = text[i:]
        flags = 0
        if any(ch.isdigit() for ch in piece):
            flags |= TF_NUM
        if piece and any(ch.isalpha() for ch in piece) and piece[0].isupper():
            flags |= TF_CAP
        tokens.append(Token(idx=idx, text=piece, start=i, end=len(text), flags=flags))
        kinds.append("WORD")

    # Sentence end cues (post-pass)
    n = len(tokens)
    for k in range(n):
        t = tokens[k]
        if kinds[k] in ("PUNCT", "ELLIPSIS"):
            if t.text in _TERMINATORS_STRONG:
                t.flags |= TF_SENT_END_STRONG
                # bubble the weak end through any immediate closers (quotes/parens)
                j = k + 1
                while j < n and tokens[j].text in _CLOSERS:
                    tokens[j].flags |= TF_SENT_END_WEAK
                    j += 1
            elif t.text in _TERMINATORS_WEAK:
                t.flags |= TF_SENT_END_WEAK

    return tokens

# ---------------------------
# Graph hookup
# ---------------------------

def tokens_to_graph(text: str, *, graph_id: int = 0, source_id: int = 0, version: int = 1):
    """
    Build a minimal language graph from tokens:
    - Node per token (NodeType.TOKEN), span=(start,end), label_id=0 (lemma TBD)
    - EdgeType.NEXT from token i -> i+1
    - Map sentence-end flags to node flags for downstream parsers
    """
    try:
        from brain.language.graph_builder import (
            GraphBuilder, NodeType, EdgeType, SchemaID, GraphType,
            NF_IS_CAPITALIZED, NF_IS_PUNCT,
            NF_SENT_END_STRONG, NF_SENT_END_WEAK
        )
    except Exception:
        import sys, pathlib
        sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
        from brain.language.graph_builder import (
            GraphBuilder, NodeType, EdgeType, SchemaID, GraphType,
            NF_IS_CAPITALIZED, NF_IS_PUNCT,
            NF_SENT_END_STRONG, NF_SENT_END_WEAK
        )

    toks = tokenize(text)
    gb = GraphBuilder(graph_id=graph_id, schema_id=SchemaID.WRITING,
                      graph_type=GraphType.HETERO, source_id=source_id, version=version)
    node_ids = []
    for t in toks:
        nflags = 0
        if t.flags & TF_PUNCT:
            nflags |= NF_IS_PUNCT
        if t.flags & TF_CAP:
            nflags |= NF_IS_CAPITALIZED
        if t.flags & TF_SENT_END_STRONG:
            nflags |= NF_SENT_END_STRONG
        if t.flags & TF_SENT_END_WEAK:
            nflags |= NF_SENT_END_WEAK
        node_id = gb.add_node(
            n_type=NodeType.TOKEN,
            sub_type=0,
            label_id=0,
            span=(t.start, t.end),
            flags=nflags,
            confidence=255
        )
        node_ids.append(node_id)
    for a, b in zip(node_ids, node_ids[1:]):
        gb.add_edge(a, b, EdgeType.NEXT)
    return gb.finalize()

if __name__ == "__main__":
    samples = [
        'He said, “Don’t move.”',
        'Email me at a.b@x.co.uk — thanks…',
        'state-of-the-art 10-mm bolts',
        "John’s book isn’t here",
        "Are you okay?",
        "Okay... I guess",
        "Wait… “Really?” Yes.",
        "Visit https://example.com/test?x=1 or www.test.org"
    ]
    from pprint import pprint
    for s in samples:
        toks = tokenize(s)
        print("TEXT:", s)
        pprint([(t.text, t.start, t.end, t.flags) for t in toks])
