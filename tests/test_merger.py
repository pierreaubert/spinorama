from __future__ import annotations

# ruff: noqa: S101 - allow asserts in tests

from typing import Any, Dict, TYPE_CHECKING

import importlib
import io
import os
import re
import types
import ast
from pathlib import Path

if TYPE_CHECKING:
    from pytest import MonkeyPatch

from metaedit import merger


def _minimal_valid_entry(brand: str, model: str) -> Dict[str, Any]:
    return {
        "brand": brand,
        "model": model,
        "type": "passive",
        "shape": "bookshelves",
        "default_measurement": "m1",
        "measurements": {
            "m1": {
                "origin": "TestOrigin",
                "format": "klippel",
            }
        },
    }


def test_strip_app_only_fields(tmp_path: Path) -> None:
    pic = str(tmp_path / "x.png")
    d = _minimal_valid_entry("Tbrand", "Model") | {"picture": pic}
    out = merger.strip_app_only_fields(d)
    assert "picture" not in out


def test_apply_merge_writes_sorted_and_valid(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    # Prepare a dummy module to stand in for datas.metadata_t
    letter = "t"
    mod_name = f"datas.metadata_{letter}"
    attr_name = f"speakers_info_{letter}"

    # Initial existing DB with one entry
    existing: Dict[str, Dict[str, Any]] = {"Tbrand Zeta": _minimal_valid_entry("Tbrand", "Zeta")}

    # Create a fake module with __file__ pointing to a temp file
    file_path = os.path.join(str(tmp_path / "merger"), f"metadata_{letter}.py")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    # Write an initial file so backup logic can copy it
    with io.open(file_path, "w", encoding="utf-8") as f:
        f.write("# initial dummy file\n")

    dummy = types.SimpleNamespace()
    setattr(dummy, attr_name, existing)
    dummy.__file__ = file_path  # type: ignore[attr-defined]

    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None):  # type: ignore[override]
        if name == mod_name:
            return dummy
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    # Now merge a new entry that should sort before 'Zeta'
    export = _minimal_valid_entry("Tbrand", "Beta")
    written_file, key = merger.apply_merge(export)

    assert key == "Tbrand Beta"
    assert written_file == file_path
    # Read back file content and extract the dict literal to verify keys order
    with io.open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Extract the literal after the first '='
    m = re.search(r"=\s*(\{.*\})\s*\Z", content, re.S)
    assert m, f"Unexpected file content: {content[:200]}..."
    literal = m.group(1)
    data = ast.literal_eval(literal)
    assert list(data.keys()) == ["Tbrand Beta", "Tbrand Zeta"]
    # Validate the merged entry remains intact
    assert data["Tbrand Beta"]["default_measurement"] == "m1"


def test_apply_merge_runs_ruff_format(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    # Prepare a dummy module to stand in for datas.metadata_t
    letter = "t"
    mod_name = f"datas.metadata_{letter}"
    attr_name = f"speakers_info_{letter}"

    # Initial existing DB with one entry
    existing: Dict[str, Dict[str, Any]] = {"Tbrand Zeta": _minimal_valid_entry("Tbrand", "Zeta")}

    # Create a fake module with __file__ pointing to a temp file
    file_path = os.path.join(str(tmp_path / "merger"), f"metadata_{letter}.py")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with io.open(file_path, "w", encoding="utf-8") as f:
        f.write("# initial dummy file\n")

    dummy = types.SimpleNamespace()
    setattr(dummy, attr_name, existing)
    dummy.__file__ = file_path  # type: ignore[attr-defined]

    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None):  # type: ignore[override]
        if name == mod_name:
            return dummy
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    called: Dict[str, Any] = {"path": None}

    def fake_format(path: str) -> None:
        called["path"] = path

    monkeypatch.setattr(merger, "_format_with_ruff", fake_format)

    # Now merge a new entry
    export = _minimal_valid_entry("Tbrand", "Beta")
    written_file, _ = merger.apply_merge(export)

    # Ensure our formatting hook was invoked with the expected file path
    assert called["path"] == written_file
