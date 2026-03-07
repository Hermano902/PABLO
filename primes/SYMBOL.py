"""
SYMBOL — Universal interpreter prime.

Watches for unconscious scenes that have raw_input but no script
classification yet. Runs the full interpretation pipeline:

  1. Script detection    — Unicode block analysis → scene.script
  2. Language detection  — lingua → scene.language_hint
  3. Tokenisation        — script-appropriate segmenter → scene.preliminary_tokens
  4. Lemmatisation       — spaCy → base forms for each token
  5. Compound resolution — KNOW store lookup (exact → lemma → placeholder)
  6. Utterance assembly  — ordered concept IDs → utterance Compound stored in KNOW
  7. Memory layer write  — token_resolutions, prime_field_bits, utterance_id, etc.

Entry condition: scene.raw_input present AND scene.script empty.

SYMBOL never calls another prime. It reads KNOW's store (shared storage),
writes resolved Compounds back to KNOW, and writes the memory layer to the scene.

See docs/PRIMES/symbol.md for full spec.
"""

from __future__ import annotations

import re
import threading
import time

from core.cognitive_scene import CognitiveScene, SceneContribution, scene_store
from core.prime_base import Prime
from core.primebit import PRIME_INDEX, PRIME_TO_BIT, PrimeBit


# ── Script detection ──────────────────────────────────────────────────────────

_BLOCK_RANGES: list[tuple[int, int, str]] = [
    (0x0000, 0x007F, "latin"),
    (0x0080, 0x024F, "latin"),
    (0x0370, 0x03FF, "greek"),
    (0x0400, 0x04FF, "cyrillic"),
    (0x0600, 0x06FF, "arabic"),
    (0x0900, 0x097F, "devanagari"),
    (0x4E00, 0x9FFF, "cjk"),
    (0x3000, 0x303F, "cjk"),
    (0x3040, 0x309F, "hiragana"),
    (0x30A0, 0x30FF, "katakana"),
    (0xAC00, 0xD7AF, "hangul"),
    (0x0E00, 0x0E7F, "thai"),
    (0x1200, 0x137F, "ethiopic"),
]


def _char_script(cp: int) -> str | None:
    for lo, hi, name in _BLOCK_RANGES:
        if lo <= cp <= hi:
            return name
    return None


def _detect_script(text: str) -> str:
    counts: dict[str, int] = {}
    for ch in text:
        s = _char_script(ord(ch))
        if s:
            counts[s] = counts.get(s, 0) + 1
    if not counts:
        return "latin"
    if len(counts) == 1:
        return next(iter(counts))
    total = sum(counts.values())
    dominant = max(counts, key=counts.__getitem__)
    return dominant if counts[dominant] / total >= 0.7 else "mixed"


# ── Language detection ────────────────────────────────────────────────────────

def _detect_language(text: str) -> dict:
    """Top-3 language confidence dict. Falls back to {"und": 1.0}."""
    try:
        from lingua import LanguageDetectorBuilder
        detector = LanguageDetectorBuilder.from_all_languages().build()
        results = detector.compute_language_confidence_values(text)
        top3 = sorted(results, key=lambda r: r.value, reverse=True)[:3]
        return {r.language.iso_code_639_1.name.lower(): round(r.value, 4) for r in top3}
    except Exception:
        return {"und": 1.0}


# ── Tokenisers ────────────────────────────────────────────────────────────────

_LATIN_SPLIT = re.compile(r"[^\w']", re.UNICODE)
_PUNCT_STRIP = re.compile(r"^['\"\-]+|['\"\-.,!?;:]+$")


def _tokenise_latin(text: str) -> list[str]:
    tokens = [_PUNCT_STRIP.sub("", t) for t in _LATIN_SPLIT.split(text)]
    return [t for t in tokens if t]


def _tokenise_cjk(text: str) -> list[str]:
    return [ch for ch in text if not ch.isspace()]


def _tokenise_arabic(text: str) -> list[str]:
    return text.split()


def _tokenise_mixed(text: str) -> list[str]:
    runs: list[tuple[str, str]] = []
    current_script: str | None = None
    current_run: list[str] = []
    for ch in text:
        if ch.isspace():
            if current_run:
                runs.append((current_script or "latin", "".join(current_run)))
                current_run = []
            current_script = None
            continue
        s = _char_script(ord(ch)) or current_script or "latin"
        if s != current_script and current_run:
            runs.append((current_script or "latin", "".join(current_run)))
            current_run = []
        current_script = s
        current_run.append(ch)
    if current_run:
        runs.append((current_script or "latin", "".join(current_run)))
    tokens: list[str] = []
    for run_script, run_text in runs:
        if run_script == "cjk":
            tokens.extend(_tokenise_cjk(run_text))
        elif run_script == "arabic":
            tokens.extend(_tokenise_arabic(run_text))
        else:
            tokens.extend(_tokenise_latin(run_text))
    return tokens


def _tokenise(text: str, script: str) -> list[str]:
    if script == "cjk":
        return _tokenise_cjk(text)
    if script == "arabic":
        return _tokenise_arabic(text)
    if script == "mixed":
        return _tokenise_mixed(text)
    return _tokenise_latin(text)


# ── Lemmatisation ─────────────────────────────────────────────────────────────

def _lemmatise(tokens: list[str]) -> dict[str, str]:
    """Return {surface: lemma}. Falls back to lowercase surface."""
    try:
        from core.lemmatizer import get_nlp
        nlp = get_nlp()
        doc = nlp(" ".join(tokens))
        return {tok.text: tok.lemma_ for tok in doc}
    except Exception:
        return {t: t.lower() for t in tokens}


# ── SYMBOL prime ──────────────────────────────────────────────────────────────

class SYMBOL(Prime):
    """
    Universal interpreter. Runs autonomously on a background thread.
    Owns the full interpretation pipeline from raw signal to memory layer.
    """

    POLL_INTERVAL = 0.015   # 15 ms

    def __init__(self) -> None:
        super().__init__("SYMBOL")
        self._thread: threading.Thread | None = None
        self._processed: set[str] = set()
        self._processed_lock = threading.Lock()

    def _on_initialize(self) -> None:
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="SYMBOL-poll",
            daemon=True,
        )
        self._thread.start()

    def _on_shutdown(self) -> None:
        pass

    def __call__(self, context: dict) -> None:
        raise NotImplementedError("SYMBOL is autonomous; do not call directly.")

    # ── Poll loop ─────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while not self._shutdown_flag.is_set():
            for scene in scene_store.active_unconscious():
                if self._should_process(scene):
                    self._process(scene)
            time.sleep(self.POLL_INTERVAL)

    def _should_process(self, scene: CognitiveScene) -> bool:
        if not scene.raw_input:
            return False
        if scene.script:        # already classified
            return False
        with self._processed_lock:
            if scene.scene_id in self._processed:
                return False
        return True

    # ── Full interpretation pipeline ──────────────────────────────────────

    def _process(self, scene: CognitiveScene) -> None:
        with self._processed_lock:
            self._processed.add(scene.scene_id)

        text = scene.raw_input

        # 1–2. Script + language
        script        = _detect_script(text)
        language_hint = _detect_language(text)

        # 3. Tokenise
        tokens = _tokenise(text, script) or text.split()

        # Write classification immediately so other primes can see it
        scene.write(
            script=script,
            language_hint=language_hint,
            preliminary_tokens=tokens,
        )

        # 4. Lemmatise
        lemmas = _lemmatise(tokens)

        # 5. Resolve each token to a Compound
        try:
            from primes.KNOW import know
        except Exception:
            return  # KNOW not ready — scene stays available for retry on next poll

        resolutions: list[dict] = []
        prime_field:  dict[str, float] = {}
        bits          = 0
        unresolved:   list[str] = []
        concept_ids:  list[int] = []
        known_syms:   list[str] = []
        new_syms:     list[str] = []
        union_bits    = 0

        from core.compound import Compound

        for token in tokens:
            lemma    = lemmas.get(token, token.lower())
            existing = know.by_symbol(token) or know.by_symbol(lemma)

            if existing is not None:
                is_exact = know.by_symbol(token) is not None
                score    = 1.0 if is_exact else 0.9
                method   = "exact" if is_exact else "lemma"
                cid      = existing.id
                concept_ids.append(cid)
                known_syms.append(token)
                union_bits |= existing.primebit.value
                # Prime field: first set prime wins for ordering
                prime_name = next(
                    (PRIME_INDEX[i] for i in range(len(PRIME_INDEX))
                     if existing.primebit.value & (1 << i)),
                    None,
                )
                resolutions.append({
                    "token": token, "compound_id": cid,
                    "symbol": existing.symbol, "score": score, "method": method,
                })
                if prime_name:
                    if score > prime_field.get(prime_name, 0.0):
                        prime_field[prime_name] = score
                    if prime_name in PRIME_TO_BIT:
                        bits |= 1 << PRIME_TO_BIT[prime_name]
            else:
                # No match — create placeholder Compound
                new_c = Compound.concept(
                    temp_id=0,
                    symbol=token,
                    primebit=PrimeBit(0),
                    confidence=0.0,
                    grounded=False,
                )
                try:
                    perm_id = know.store(new_c)
                    concept_ids.append(perm_id)
                    new_syms.append(token)
                    resolutions.append({
                        "token": token, "compound_id": perm_id,
                        "symbol": token, "score": 0.0, "method": "placeholder",
                    })
                    unresolved.append(token)
                except Exception:
                    resolutions.append({
                        "token": token, "compound_id": None,
                        "symbol": token, "score": 0.0, "method": "none",
                    })
                    unresolved.append(token)

        # 6. Assemble utterance Compound
        utterance_id = None
        if concept_ids:
            utt = Compound.utterance(
                temp_id=0,
                symbol=text[:80],
                nested=concept_ids,
                primebit=PrimeBit(union_bits),
                source=scene.source,
            )
            try:
                utterance_id = know.store(utt)
            except Exception:
                pass

        # 7. Write full memory layer to scene
        scene.write(
            token_resolutions=resolutions,
            prime_field=prime_field,
            prime_field_bits=bits,
            unresolved_tokens=unresolved,
            utterance_id=utterance_id,
            concept_ids=concept_ids,
            known_symbols=known_syms,
            new_symbols=new_syms,
        )

        # SymbolicScene contribution
        dominant_lang = next(iter(language_hint), "und")
        marker = Compound.concept(
            temp_id=0,
            symbol=f"{script}:{dominant_lang}",
            primebit=PrimeBit(1 << PRIME_TO_BIT["SYMBOL"]) if "SYMBOL" in PRIME_TO_BIT else PrimeBit(0),
            confidence=1.0,
            grounded=True,
        )
        scene.contribute_symbolic(SceneContribution(
            prime="SYMBOL",
            compounds=[marker],
            triples=[],
            narrative_fragment=None,
        ))


# ── Module-level singleton ────────────────────────────────────────────────────
symbol = SYMBOL()
