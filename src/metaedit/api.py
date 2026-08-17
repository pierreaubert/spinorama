from __future__ import annotations

from typing import Any, Dict, List, Optional
import copy
import importlib
import logging

try:
    # Prefer real metadata database when available
    from datas.speaker import speakers_info  # type: ignore[import-not-found]
except Exception:
    # Test/lean environments may not ship the datas package as an importable module.
    # Provide a safe, typed fallback so UI can still function with empty lists.
    speakers_info: Dict[str, Dict[str, Any]] = {}


def get_speakers() -> List[str]:
    """Return the list of speaker keys from the local metadata database.

    Keys are the canonical names used throughout the project (e.g. "Brand Model").
    """
    try:
        return sorted([str(k) for k in speakers_info])
    except Exception:
        return []


def get_brands() -> List[str]:
    """Return sorted unique brands from the local metadata database."""
    try:
        brands = {str(v.get("brand", "")) for v in speakers_info.values() if isinstance(v, dict)}
        brands.discard("")
        return sorted(brands)
    except Exception:
        return []


def get_speaker_metadata(name: str) -> Optional[Dict[str, Any]]:
    """Return the full metadata dict for a given speaker key from local DB.

    If the key is not found, returns None.
    """
    val = speakers_info.get(name)
    if val is None:
        return None
    # return a deep copy to avoid accidental mutation of the global DB
    return copy.deepcopy(val)  # type: ignore[return-value]


def reload_metadata() -> None:
    """Reload the aggregated speakers_info from datas.metadata.

    Updates this module's "speakers_info" binding in-place so callers see
    fresh data without restarting the process.
    """
    try:
        dm = importlib.import_module("datas.speaker")  # type: ignore[import-not-found]
        mod = importlib.reload(dm)
        # Rebind our module-level name to the freshly loaded dictionary
        globals()["speakers_info"] = mod.speakers_info  # type: ignore[attr-defined]
    except Exception as exc:
        # Best effort: leave previous data intact, but log for debugging
        logging.getLogger(__name__).debug("reload_metadata failed: %s", exc)
