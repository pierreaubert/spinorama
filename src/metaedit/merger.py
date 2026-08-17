from __future__ import annotations

from typing import Any, Dict, Tuple

import importlib
import io
import os
import shutil
import subprocess
import sys
from pprint import pformat


def speaker_key(brand: str, model: str) -> str:
    brand = " ".join((brand or "").split())
    model = " ".join((model or "").split())
    return f"{brand} {model}".strip()


def target_letter(brand: str) -> str:
    if not brand:
        raise ValueError("Missing brand")
    return brand[0].lower()


def target_module_and_attr(letter: str) -> Tuple[str, str]:
    mod = f"datas.speaker_{letter}"
    attr = f"speakers_info_{letter}"
    return mod, attr


def load_existing(letter: str) -> Tuple[Dict[str, Dict[str, Any]], str]:
    mod_name, attr = target_module_and_attr(letter)
    mod = importlib.import_module(mod_name)
    data: Dict[str, Dict[str, Any]] = getattr(mod, attr)
    # Best-effort to locate file on disk
    file_path = os.path.abspath(mod.__file__)  # type: ignore[attr-defined]
    return dict(data), file_path


def merge_entry(
    existing: Dict[str, Dict[str, Any]], key: str, value: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    # Replace or insert
    updated = dict(existing)
    updated[key] = value
    # Rebuild dict sorted by key
    return {k: updated[k] for k in sorted(updated.keys())}


def generate_file_content(letter: str, db: Dict[str, Dict[str, Any]]) -> str:
    # Keep deterministic output; do not sort nested dicts so entry order is preserved
    header = (
        """# -*- coding: utf-8 -*-\nfrom . import SpeakerDatabase, gll_data_acquisition_std\n\n"""
    )
    body = f"speakers_info_{letter}: SpeakerDatabase = "
    literal = pformat(db, sort_dicts=False, width=100)
    return header + body + literal + "\n"


def write_with_backup(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # backup
    bak = path + ".bak"
    try:
        shutil.copy2(path, bak)
    except Exception:
        # ignore if original doesn't exist
        pass
    # write atomically
    tmp_path = path + ".tmp"
    with io.open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp_path, path)


def _format_with_ruff(path: str) -> None:
    """Best-effort: run `ruff format` on path; ignore if unavailable/errors."""
    try:
        exe = shutil.which("ruff")
        if exe:
            subprocess.run([exe, "format", path], check=False)
        else:
            # Try module form via current interpreter
            subprocess.run([sys.executable, "-m", "ruff", "format", path], check=False)
    except Exception:
        # Formatting is optional; never raise from here
        pass


def strip_app_only_fields(speaker: Dict[str, Any]) -> Dict[str, Any]:
    # The app may attach transient fields (e.g., 'picture') that are not part of datas schema
    out = dict(speaker)
    out.pop("picture", None)
    return out


def validate_or_raise(key: str, data: Dict[str, Any]) -> None:
    # Lazy import so tools/tests that import this module without full datas context don't fail.
    try:
        from datas.checks import validate_speaker_data  # type: ignore[reportMissingImports]
    except Exception:
        # If validation utilities are unavailable, skip validation as best-effort.
        # Normal runs (within the project) will have datas on sys.path.
        return
    res = validate_speaker_data(key, data)
    if not res.valid:
        msgs = "\n".join(res.messages)
        msg = f"Validation failed for {key}:\n{msgs}"
        raise ValueError(msg)


def apply_merge(export_dict: Dict[str, Any]) -> Tuple[str, str]:
    """
    Apply a Step 3 export (single speaker) to the appropriate datas/metadata_*.py file.

    Returns (file_path, speaker_key) on success.
    Raises ValueError on validation or IO errors.
    """
    brand = str(export_dict.get("brand") or "").strip()
    model = str(export_dict.get("model") or "").strip()
    if not brand or not model:
        raise ValueError("Brand and Model are required")

    key = speaker_key(brand, model)
    letter = target_letter(brand)

    clean_entry = strip_app_only_fields(export_dict)
    validate_or_raise(key, clean_entry)

    existing, file_path = load_existing(letter)
    merged = merge_entry(existing, key, clean_entry)

    new_content = generate_file_content(letter, merged)
    write_with_backup(file_path, new_content)
    _format_with_ruff(file_path)
    return file_path, key
