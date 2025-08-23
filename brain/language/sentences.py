"""
Pablo Language — sentence segmentation (v0.1, language-only)

Rule-of-thumb (deterministic):
- End a sentence at any token flagged TF_SENT_END_STRONG (., ?, !).
  Carry the boundary over any immediate closing quotes/brackets that are flagged weak.
- Also end at ellipsis (weak end: … or ...) if it's the last token OR the next
  non-punctuation token is capitalized. In all ellipsis-end cases, the sentence
  closes at the ellipsis token itself (opener quotes belong to the next sentence).

Outputs:
- segment_tokens(tokens) -> list[(tok_start_idx, tok_end_idx_exclusive)]
- segment(text)         -> list[(char_start, char_end)]
- segment_to_graph(text)-> (Graph, token_spans)
"""
from __future__ import annotations
from typing import List, Tuple

from .tokenizer import (
    tokenize, Token,
    TF_CAP, TF_PUNCT,
    TF_SENT_END_STRONG, TF_SENT_END_WEAK,
    tokens_to_graph,
)


def segment_tokens(tokens: List[Token]) -> List[Tuple[int, int]]:
    """
    Return sentence spans as (start_idx, end_idx_exclusive) over tokens.
    """
    spans: List[Tuple[int, int]] = []
    n = len(tokens)
    if n == 0:
        return spans

    s = 0
    k = 0
    while k < n:
        t = tokens[k]

        # Strong terminators always end; extend over any immediate weak closers
        if t.flags & TF_SENT_END_STRONG:
            end = k
            j = k + 1
            while j < n and (tokens[j].flags & TF_SENT_END_WEAK):
                end = j
                j += 1
            spans.append((s, end + 1))
            s = end + 1
            k = s
            continue

        # Ellipsis (weak) can end if last token OR next non-punct token is capitalized.
        # We always end the sentence exactly at the ellipsis token (k+1),
        # so any opener quotes/brackets start the next sentence.
        if (t.flags & TF_SENT_END_WEAK) and t.text in ("…", "..."):
            j = k + 1
            # Look ahead to decide *whether* it ends (skip weak closers and general punct)
            while j < n and ((tokens[j].flags & TF_SENT_END_WEAK) or (tokens[j].flags & TF_PUNCT)):
                j += 1
            if j >= n or (tokens[j].flags & TF_CAP):
                spans.append((s, k + 1))  # close exactly at ellipsis
                s = k + 1
                k = s
                continue

        k += 1

    # trailing material without explicit terminator
    if s < n:
        spans.append((s, n))
    return spans


def segment(text: str) -> List[Tuple[int, int]]:
    toks = tokenize(text)
    spans_tok = segment_tokens(toks)
    out: List[Tuple[int, int]] = []
    for a, b in spans_tok:
        if a >= b:
            continue
        start = toks[a].start
        end = toks[b - 1].end
        out.append((start, end))
    return out


def segment_to_graph(text: str):
    g = tokens_to_graph(text)
    toks = tokenize(text)
    spans_tok = segment_tokens(toks)
    return g, spans_tok


if __name__ == "__main__":
    samples = [
        'He said, “Don’t move.”',
        'Are you okay?',
        'Okay... I guess',
        'Wait… “Really?” Yes.',
    ]
    from pprint import pprint
    for s in samples:
        spans = segment(s)
        print("TEXT:", s)
        print("SENTENCE CHAR SPANS:", spans, "=>", [s[a:b] for a, b in spans])
