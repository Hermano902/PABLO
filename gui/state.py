"""
gui/state.py — system state snapshot for the GUI timer.

Rules:
- Reads from SceneStore and KNOW directly (no queues, no prime_registry).
- Never writes to any prime or scene.
- Never calls any NiceGUI function.
"""

import time

# Prime names displayed in the sidebar — in activation order.
MANAGED_PRIMES = ["READ", "SYMBOL", "DATA", "KNOW", "SELF", "THINK", "SAY"]

# Rolling event log — appended to by other modules, read by the timer.
_event_log: list[str] = []
MAX_EVENT_LOG = 200


def log_event(message: str) -> None:
    """Append a timestamped event to the rolling log. Thread-safe (GIL list append)."""
    ts = time.strftime("%H:%M:%S")
    _event_log.append(f"{ts}  {message}")
    if len(_event_log) > MAX_EVENT_LOG:
        del _event_log[:-MAX_EVENT_LOG]


def _get_know():
    """Return the KNOW prime instance, or None."""
    try:
        from primes.KNOW import know
        return know
    except Exception:
        return None


def _get_scene_store():
    """Return the SceneStore singleton, or None."""
    try:
        from core.cognitive_scene import scene_store
        return scene_store
    except Exception:
        return None


def get_state() -> dict:
    """
    Assemble a system state snapshot.
    Called from the NiceGUI timer — runs on the async event loop thread.
    """
    know = _get_know()
    scene_store = _get_scene_store()

    # ── KNOW stats ───────────────────────────────────────────────────────
    know_stats: dict = {}
    if know is not None:
        try:
            know_stats = know._get_stats()
        except Exception:
            pass

    # ── Recent scenes ────────────────────────────────────────────────────
    recent_scenes: list[dict] = []
    active_scene: dict | None = None
    if scene_store is not None:
        try:
            scenes = scene_store.recent(5)
            recent_scenes = [_scene_summary(s) for s in scenes]
            # Active scene: most recent non-terminal scene
            active_list = scene_store.all_active()
            if active_list:
                active_scene = _scene_detail(active_list[-1])
        except Exception:
            pass

    return {
        "know":          know_stats,
        "recent_scenes": recent_scenes,
        "active_scene":  active_scene,
        "events":        list(_event_log[-50:]),
        "timestamp":     time.time(),
    }


def _scene_summary(scene) -> dict:
    """Lightweight scene summary for the scene list."""
    try:
        return {
            "scene_id":    scene.scene_id,
            "source":      getattr(scene, "source", "?"),
            "thread_type": getattr(scene, "thread_type", "unconscious"),
            "status":      getattr(scene, "status", "active"),
            "opened_at":   getattr(scene, "opened_at", 0),
            "closed_at":   getattr(scene, "closed_at", None),
            "raw_input":   getattr(scene, "raw_input", "")[:60],
        }
    except Exception:
        return {}


def _scene_detail(scene) -> dict:
    """Full scene detail for the active scene panel."""
    try:
        return {
            "scene_id":         scene.scene_id,
            "source":           getattr(scene, "source", "?"),
            "thread_type":      getattr(scene, "thread_type", "unconscious"),
            "status":           getattr(scene, "status", "active"),
            "salience":         getattr(scene, "salience", 0.0),
            "conscious_slot":   getattr(scene, "conscious_slot", None),
            "opened_at":        getattr(scene, "opened_at", 0),
            "raw_input":        getattr(scene, "raw_input", ""),
            "modality":         getattr(scene, "modality", ""),
            "preliminary_tokens": getattr(scene, "preliminary_tokens", []),
            "script":           getattr(scene, "script", ""),
            "language_hint":    getattr(scene, "language_hint", {}),
            "token_resolutions":  getattr(scene, "token_resolutions", []),
            "prime_field":      getattr(scene, "prime_field", {}),
            "prime_field_bits": getattr(scene, "prime_field_bits", 0),
            "unresolved_tokens": getattr(scene, "unresolved_tokens", []),
            "utterance_id":     getattr(scene, "utterance_id", None),
            "concept_ids":      getattr(scene, "concept_ids", []),
            "known_symbols":    getattr(scene, "known_symbols", []),
            "new_symbols":      getattr(scene, "new_symbols", []),
            "active_narratives": getattr(scene, "active_narratives", []),
            "validation_flags": getattr(scene, "validation_flags", {}),
            "attention_decision": getattr(scene, "attention_decision", None),
            "relationship_quality": getattr(scene, "relationship_quality", None),
            "reasoning_mode":   getattr(scene, "reasoning_mode", None),
            "intent_id":        getattr(scene, "intent_id", None),
            "response_text":    getattr(scene, "response_text", None),
            "closed_at":        getattr(scene, "closed_at", None),
        }
    except Exception:
        return {}
