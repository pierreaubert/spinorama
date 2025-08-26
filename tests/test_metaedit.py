from __future__ import annotations

# ruff: noqa: S101 - allow asserts in tests

import os
import io
import re
import ast
import types
import importlib
import subprocess
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING, cast

import pytest
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QDateEdit,
    QFormLayout,
    QToolButton,
    QWidget,
    QFrame,
    QLabel,
)

pytestmark = pytest.mark.qt

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# --------------------
# Shared helpers
# --------------------

def _pick_sample_speaker():
    from datas.metadata import speakers_info

    for key, val in speakers_info.items():
        if not isinstance(val, dict):
            continue
        if not val.get("brand") or not val.get("model"):
            continue
        measurements = val.get("measurements")
        if isinstance(measurements, dict) and measurements:
            return key, val
    pytest.skip("No suitable speaker found in local metadata DB")


def _keys_in_order(keys: List[str], ordered_subset: List[str]) -> bool:
    """Return True if keys from ordered_subset appear in keys in the same relative order.

    Missing keys are ignored; only the relative order of present keys is checked.
    """
    positions = {k: i for i, k in enumerate(keys)}
    present = [k for k in ordered_subset if k in positions]
    return all(positions[present[i]] < positions[present[i + 1]] for i in range(len(present) - 1))


def _to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _normalize_expected_export(raw: Dict[str, Any]) -> Dict[str, Any]:
    # Build the expected export JSON from the raw metadata, matching the app's export shape
    from copy import deepcopy

    data: Dict[str, Any] = deepcopy(raw)

    # Convert legacy 'review' to 'reviews'
    measurements: Dict[str, Any] = (
        cast(Dict[str, Any], data.get("measurements")) if isinstance(data.get("measurements"), dict) else {}
    )
    for k, m in list(measurements.items()):
        if isinstance(m, dict) and ("review" in m) and ("reviews" not in m):
            rv = m.get("review")
            m.pop("review", None)
            m["reviews"] = {"default": rv} if isinstance(rv, str) else {}

    expected: Dict[str, Any] = {
        "brand": data.get("brand"),
        "model": data.get("model"),
        # optional top-level fields included only when present (export excludes None)
        "measurements": {},
    }
    for key in ("type", "shape", "price", "amount", "default_measurement"):
        v = data.get(key)
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        expected[key] = v

    # Measurements mapping normalization
    for meas_key, m in measurements.items():
        if not isinstance(m, dict):
            # skip non-dicts
            continue
        em: Dict[str, Any] = {}
        # Simple fields (mirror UI defaults)
        # Empty text fields should be omitted in export, so keep raw values here and prune later
        em["origin"] = m.get("origin")
        em["format"] = m.get("format")
        em["quality"] = m.get("quality")
        em["symmetry"] = m.get("symmetry") if m.get("symmetry") is not None else "none"
        rp = m.get("review_published")
        # Keep only valid 8-digit date; otherwise leave unset so it gets pruned
        if isinstance(rp, str) and len(rp) == 8 and rp.isdigit():
            em["review_published"] = rp
        else:
            em["review_published"] = None
        # Reviews
        reviews = m.get("reviews")
        em["reviews"] = reviews if isinstance(reviews, dict) else {}
        # Data Acquisition
        da: Dict[str, Any] = (
            cast(Dict[str, Any], m.get("data_acquisition")) if isinstance(m.get("data_acquisition"), dict) else {}
        )
        em["data_acquisition"] = {
            "via": (cast(str, da.get("via")) if isinstance(da.get("via"), str) else None),
            "distance": _to_float(da.get("distance")),
            "signal": (cast(str, da.get("signal")) if isinstance(da.get("signal"), str) else None),
            "resolution": _to_float(da.get("resolution")),
            "min_valid_freq": _to_float(da.get("min_valid_freq")),
            "max_valid_freq": _to_float(da.get("max_valid_freq")),
            # UI default: unchecked => False (kept in export)
            "air_absorbtion": bool(da.get("air_absorbtion")) if da.get("air_absorbtion") is not None else False,
            "notes": (cast(str, da.get("notes")) if isinstance(da.get("notes"), str) else None),
        }

        # Drop DA block if effectively empty (all None/empty/False)
        def _block_empty(d: Dict[str, Any]) -> bool:
            for _k, _v in d.items():
                if _v is None:
                    continue
                if isinstance(_v, bool) and _v is False:
                    continue
                if isinstance(_v, str) and _v.strip() == "":
                    continue
                return False
            return True

        if _block_empty(em["data_acquisition"]):
            em["data_acquisition"] = None
        # Extras
        ex: Dict[str, Any] = cast(Dict[str, Any], m.get("extras")) if isinstance(m.get("extras"), dict) else {}
        em["extras"] = {
            # UI default is unchecked -> False (kept)
            "is_equed": bool(ex.get("is_equed")) if ex.get("is_equed") is not None else False,
            "score_penalty": _to_float(ex.get("score_penalty")),
        }
        if _block_empty(em["extras"]):
            em["extras"] = None
        # Specifications (support nested SPL)
        sp: Dict[str, Any] = (
            cast(Dict[str, Any], m.get("specifications")) if isinstance(m.get("specifications"), dict) else {}
        )
        size: Dict[str, Any] = cast(Dict[str, Any], sp.get("size")) if isinstance(sp.get("size"), dict) else {}
        spl = cast(Dict[str, Any], sp.get("SPL")) if isinstance(sp.get("SPL"), dict) else None
        spl_peak = sp.get("spl_peak", None)
        spl_long = sp.get("spl_long_term", None)
        if spl is not None:
            if spl_peak is None:
                spl_peak = spl.get("peak")
            if spl_long is None:
                spl_long = spl.get("continuous")
        em["specifications"] = {
            "sensitivity": _to_float(sp.get("sensitivity")),
            "impedance": _to_float(sp.get("impedance")),
            "weight": _to_float(sp.get("weight")),
            "size": {
                "height": _to_float(size.get("height")),
                "width": _to_float(size.get("width")),
                "depth": _to_float(size.get("depth")),
            },
            "spl_peak": _to_float(spl_peak),
            "spl_long_term": _to_float(spl_long),
        }
        expected["measurements"][meas_key] = em

    # Apply the same pruning rule as the application export: remove empty strings and empty dicts
    from metaedit.models import prune_empty

    return prune_empty(expected)


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


def _goto_step2(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    # Prepare Step 1 with a valid 'New' entry to avoid modal dialogs in headless mode
    sel = win.page_select
    sel.rb_new.setChecked(True)
    sel.new_brand.setText("TestBrand")
    sel.new_speaker_model.setText("TestModel")
    QApplication.processEvents()

    # Navigate to Step 2
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit
    return win


# --------------------
# App UI tests
# --------------------

def test_window_creation(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)

    assert win.windowTitle().startswith("Spinorama Metadata Manager")
    # Starts at first page
    assert win.stack.currentWidget() is win.page_select


def test_navigation_flow(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    # Step 1: select New and fill required fields
    sel = win.page_select
    sel.rb_new.setChecked(True)
    sel.new_brand.setText("BrandA")
    sel.new_speaker_model.setText("ModelB")
    QApplication.processEvents()

    # Step 1 -> Step 2
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit

    # Step 2 -> Step 1 (Back)
    win.page_edit.back_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_select

    # Step 1 -> Step 2 -> Step 3
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit
    # Ensure a valid measurement key before proceeding to Step 3 to avoid modal dialogs
    tabs = win.page_edit.measurements_tabs
    panel = tabs.widget(0)
    le_key = panel.findChild(QLineEdit, "meas_key")
    if isinstance(le_key, QLineEdit):
        le_key.setText("m1")
    QApplication.processEvents()
    win.page_edit.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_review

    # Step 3 -> Step 2 (Back)
    win.page_review.back_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit


def test_step2_dynamic_behaviors(qtbot):
    from typing import cast
    from metaedit.app import MetadataMainWindow
    from PySide6.QtWidgets import QComboBox, QLineEdit

    win = MetadataMainWindow()
    qtbot.addWidget(win)

    # Navigate to Step 2
    # Use helper behavior from _goto_step2 to ensure safe navigation
    win.page_select.rb_new.setChecked(True)
    win.page_select.new_brand.setText("BrandZ")
    win.page_select.new_speaker_model.setText("ModelZ")
    QApplication.processEvents()
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit

    # There should be at least one measurement tab by default
    tabs = win.page_edit.measurements_tabs
    assert tabs.count() >= 1
    panel = tabs.widget(0)

    # 1) format "klippel" sets quality to "high"
    cb_format_opt = panel.findChild(QComboBox, "meas_format")
    cb_quality_opt = panel.findChild(QComboBox, "meas_quality")
    assert cb_format_opt is not None and cb_quality_opt is not None
    cb_format = cast(QComboBox, cb_format_opt)
    cb_quality = cast(QComboBox, cb_quality_opt)
    idx = cb_format.findText("klippel")
    assert idx >= 0
    cb_format.setCurrentIndex(idx)
    qtbot.waitUntil(lambda: cb_quality.currentText() == "high")

    # 2) type "active" disables sensitivity and impedance; switching back enables them
    type_cb: QComboBox = win.page_edit.form_type_cb
    idx_active = type_cb.findText("active")
    assert idx_active >= 0
    type_cb.setCurrentIndex(idx_active)
    le_sens_opt = panel.findChild(QLineEdit, "sp_sens")
    le_imp_opt = panel.findChild(QLineEdit, "sp_imp")
    assert le_sens_opt is not None and le_imp_opt is not None
    le_sens = cast(QLineEdit, le_sens_opt)
    le_imp = cast(QLineEdit, le_imp_opt)
    qtbot.waitUntil(lambda: not le_sens.isEnabled() and not le_imp.isEnabled())
    idx_passive = type_cb.findText("passive")
    assert idx_passive >= 0
    type_cb.setCurrentIndex(idx_passive)
    qtbot.waitUntil(lambda: le_sens.isEnabled() and le_imp.isEnabled())

    # 3) editing key updates default measurement selector
    le_key_opt = panel.findChild(QLineEdit, "meas_key")
    assert le_key_opt is not None
    le_key = cast(QLineEdit, le_key_opt)
    le_key.setText("my_meas")
    dm_cb: QComboBox = win.page_edit.default_meas_cb

    def _dm_has_key() -> bool:
        return any(dm_cb.itemText(i) == "my_meas" for i in range(dm_cb.count()))

    qtbot.waitUntil(_dm_has_key)

    # 4) initial populate: creating a panel with format pre-set to klippel sets quality to high
    # Use the internal method to simulate initial population with existing data
    win._add_measurement_panel("init", {"format": "klippel"})  # type: ignore[attr-defined]
    # Find the tab/panel with key == "init"
    found_quality_high = False
    for i in range(tabs.count()):
        p2 = tabs.widget(i)
        le_key2 = p2.findChild(QLineEdit, "meas_key")
        if le_key2 and le_key2.text() == "init":
            cb_quality2 = p2.findChild(QComboBox, "meas_quality")
            assert cb_quality2 is not None
            found_quality_high = cb_quality2.currentText() == "high"
            break
    assert found_quality_high


def test_step1_visibility_toggle_and_radio_prominence(qtbot):
    from metaedit.app import MetadataMainWindow

    win = MetadataMainWindow()
    qtbot.addWidget(win)

    sel = win.page_select
    # Manually call toggle to ensure proper initialization
    # This is needed because rb_existing is already True when the widget is created,
    # so setting it to True again won't trigger the toggled signal
    sel.rb_existing.toggled.emit(True)
    
    # Initial: Existing selected -> existing group visible, new group hidden
    assert sel.rb_existing.isChecked()
    # Add a small wait to ensure the initial toggle has time to run
    qtbot.wait(50)
    # In test environments, we need to use isVisibleTo() instead of isVisible()
    assert sel.existing_group.isVisibleTo(sel)
    assert not sel.new_group.isVisibleTo(sel)

    # Toggle to New
    sel.rb_new.setChecked(True)
    qtbot.waitUntil(lambda: sel.new_group.isVisibleTo(sel))
    assert not sel.existing_group.isVisibleTo(sel)

    # Back to Existing
    sel.rb_existing.setChecked(True)
    qtbot.waitUntil(lambda: sel.existing_group.isVisibleTo(sel))
    assert not sel.new_group.isVisibleTo(sel)

    # Radios should be visually larger (style/min height)
    assert sel.rb_existing.minimumHeight() >= 32
    assert "font-size: 16px" in sel.rb_existing.styleSheet()


def test_data_acq_via_gll_defaults(qtbot):
    from typing import cast
    from metaedit.app import MetadataMainWindow
    from PySide6.QtWidgets import QComboBox, QLineEdit

    win = MetadataMainWindow()
    qtbot.addWidget(win)

    # Navigate to Step 2
    win.page_select.rb_new.setChecked(True)
    win.page_select.new_brand.setText("BrandG")
    win.page_select.new_speaker_model.setText("ModelG")
    QApplication.processEvents()
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit

    # Use first measurement panel
    tabs = win.page_edit.measurements_tabs
    panel = tabs.widget(0)

    cb_via_opt = panel.findChild(QComboBox, "da_via")
    le_dist_opt = panel.findChild(QLineEdit, "da_distance")
    le_signal_opt = panel.findChild(QLineEdit, "da_signal")
    le_min_opt = panel.findChild(QLineEdit, "da_min")
    le_max_opt = panel.findChild(QLineEdit, "da_max")
    assert cb_via_opt and le_dist_opt and le_signal_opt and le_min_opt and le_max_opt
    cb_via = cast(QComboBox, cb_via_opt)
    le_dist = cast(QLineEdit, le_dist_opt)
    le_signal = cast(QLineEdit, le_signal_opt)
    le_min = cast(QLineEdit, le_min_opt)
    le_max = cast(QLineEdit, le_max_opt)

    # Ensure empty initial values
    assert le_dist.text().strip() == ""
    assert le_signal.text().strip() == ""
    assert le_min.text().strip() == ""
    assert le_max.text().strip() == ""

    # Selecting GLL should prefill defaults when fields are empty
    cb_via.setCurrentText("GLL")
    qtbot.waitUntil(lambda: le_dist.text() == "10")
    assert le_signal.text() == "aes 20Hz-20kHz"
    assert le_min.text() == "20"
    assert le_max.text() == "20000"


def test_step3_back_does_not_invoke_to_edit(qtbot, monkeypatch):
    # Ensure that pressing Back on Step 3 doesn't call _to_edit (which reloads from Step 1)
    from metaedit.app import MetadataMainWindow

    # Spy on _to_edit to track calls
    orig_to_edit = MetadataMainWindow._to_edit
    calls = {"count": 0}

    def spy(self):  # type: ignore[no-redef]
        calls["count"] += 1
        return orig_to_edit(self)

    # Patch before window instantiation so Step 1 -> Step 2 goes through spy
    monkeypatch.setattr(MetadataMainWindow, "_to_edit", spy, raising=True)

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    # Step 1: choose New and fill required
    win.page_select.rb_new.setChecked(True)
    win.page_select.new_brand.setText("BrandC")
    win.page_select.new_speaker_model.setText("ModelC")
    QApplication.processEvents()
    # Step 1 -> Step 2 via Next (this will call _to_edit once)
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit
    called_before = calls["count"]
    assert called_before >= 1  # sanity: we did go through _to_edit once

    # Step 2 -> Step 3
    # Ensure measurement key set to avoid modal dialog in headless mode
    tabs = win.page_edit.measurements_tabs
    panel = tabs.widget(0)
    le_key = panel.findChild(QLineEdit, "meas_key")
    if isinstance(le_key, QLineEdit):
        le_key.setText("m1")
    QApplication.processEvents()
    win.page_edit.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_review

    # Step 3 -> Step 2 (Back) should NOT call _to_edit again
    win.page_review.back_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit
    assert calls["count"] == called_before


# --------------------
# CLI tests
# --------------------

def test_cli_missing_speaker_exits_with_warning():
    # Run the module with a clearly missing speaker key
    cmd = [sys.executable, "-m", "metaedit.app", "--speaker", "__nonexistent__"]
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "minimal"
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)

    assert res.returncode == 1
    assert "Warning: speaker '__nonexistent__' not found." in (res.stderr or "")


# --------------------
# Export tests
# --------------------

def test_top_level_order_min_diff() -> None:
    from metaedit.models import (
        DataAcquisition,
        Measurement,
        Size,
        SpeakerMetadata,
        Specifications,
        export_speaker_metadata,
    )

    sm = SpeakerMetadata(
        brand="BrandX",
        model="ModelY",
        shape="bookshelves",
        type="passive",
        price="$999",
        amount="pair",
        default_measurement="m1",
        measurements={
            "m1": Measurement(origin="TestOrigin", format="klippel"),
        },
    )

    out = export_speaker_metadata(sm)
    keys = list(out.keys())

    expected_order = [
        "brand",
        "model",
        "type",
        "price",
        "amount",
        "shape",
        "default_measurement",
        "measurements",
    ]

    assert keys[: len(expected_order)] == expected_order


def test_measurement_order_and_prune() -> None:
    from metaedit.models import (
        DataAcquisition,
        Measurement,
        Size,
        SpeakerMetadata,
        Specifications,
        export_speaker_metadata,
    )

    meas = Measurement(
        origin="Lab",
        format="klippel",
        quality="A",
        reviews={"default": "Great"},
        review_published="20220101",
        extras=None,  # should be omitted
        data_acquisition=DataAcquisition(via="Klippel"),
        specifications=Specifications(
            sensitivity=85.0,
            impedance=None,
            size=Size(height=10.0),
            weight=10.0,
        ),
    )

    sm = SpeakerMetadata(
        brand="B",
        model="M",
        default_measurement="m1",
        measurements={"m1": meas},
    )

    out = export_speaker_metadata(sm)

    m1 = out["measurements"]["m1"]
    m1_keys = list(m1.keys())

    # Ensure extras and notes are pruned if empty
    assert "extras" not in m1_keys
    assert "notes" not in m1_keys

    expected_meas_order = [
        "origin",
        "format",
        "quality",
        "reviews",
        "review_published",
        "extras",
        "notes",
        "data_acquisition",
        "specifications",
    ]
    assert _keys_in_order(m1_keys, expected_meas_order)

    # Check specs order
    specs = m1["specifications"]
    spec_keys = list(specs.keys())
    expected_spec_order = [
        "sensitivity",
        "impedance",
        "dispersion",
        "SPL",
        "size",
        "weight",
    ]
    assert _keys_in_order(spec_keys, expected_spec_order)


# --------------------
# GitOps tests
# --------------------

def test_plan_pr_requires_develop_and_uptodate() -> None:
    from metaedit.gitops import plan_pr_actions

    files = ["datas/metadata_a.py", "datas/pictures/Genelec 8341A.png"]
    # Not on develop
    with pytest.raises(ValueError):
        plan_pr_actions(
            current_branch="main",
            up_to_date=True,
            files=files,
            speaker_key="Genelec 8341A",
            date_str="2025-08-26",
            gh_available=True,
        )
    # Not up-to-date
    with pytest.raises(ValueError):
        plan_pr_actions(
            current_branch="develop",
            up_to_date=False,
            files=files,
            speaker_key="Genelec 8341A",
            date_str="2025-08-26",
            gh_available=True,
        )


def test_plan_pr_commands_with_and_without_gh() -> None:
    from metaedit.gitops import plan_pr_actions

    files = ["datas/metadata_g.py", "datas/pictures/Genelec 8341A.png"]
    cmds = plan_pr_actions(
        current_branch="develop",
        up_to_date=True,
        files=files,
        speaker_key="Genelec 8341A",
        date_str="2025-08-26",
        gh_available=True,
    )
    # Switch branch command
    assert cmds[0][:3] == ["git", "switch", "-c"]
    # Add includes both files
    assert ["git", "add", *files] in cmds
    # Commit present
    assert any(c[:2] == ["git", "commit"] for c in cmds)
    # Push present
    assert ["git", "push", "-u", "origin", cmds[0][3]] in cmds
    # gh pr create present
    assert any(c[:3] == ["gh", "pr", "create"] for c in cmds)

    # Without gh, gh command omitted
    cmds2 = plan_pr_actions(
        current_branch="develop",
        up_to_date=True,
        files=files,
        speaker_key="Genelec 8341A",
        date_str="2025-08-26",
        gh_available=False,
    )
    assert not any(c and c[0] == "gh" for c in cmds2)


def test_sanitize_ref() -> None:
    from metaedit.gitops import sanitize_ref

    assert sanitize_ref("Genelec 8341A") == "genelec-8341a"
    assert sanitize_ref("B&W 800 D3") == "b-w-800-d3"
    assert sanitize_ref("  ") == "meta"


# --------------------
# Merger tests
# --------------------

def test_strip_app_only_fields(tmp_path: Path) -> None:
    from metaedit import merger

    pic = str(tmp_path / "x.png")
    d = _minimal_valid_entry("Tbrand", "Model") | {"picture": pic}
    out = merger.strip_app_only_fields(d)
    assert "picture" not in out


def test_apply_merge_writes_sorted_and_valid(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    from metaedit import merger

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
    from metaedit import merger

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


# --------------------
# Models tests
# --------------------

def test_convert_legacy_reviews_single_field():
    from metaedit.models import SpeakerMetadata

    data = {
        "brand": "X",
        "model": "Y",
        "measurements": {"asr": {"origin": "ASR", "review": "https://example.com/r"}},
    }
    converted = SpeakerMetadata.convert_legacy_reviews(data)
    assert "review" not in converted["measurements"]["asr"]
    assert converted["measurements"]["asr"]["reviews"] == {"default": "https://example.com/r"}


def test_date_formatting_roundtrip():
    from metaedit.models import SpeakerMetadata

    src = "20240131"
    as_input = SpeakerMetadata.format_date_for_input(src)
    assert as_input == "2024-01-31"
    back = SpeakerMetadata.format_date_for_python(as_input)
    assert back == src


# --------------------
# Picture tests
# --------------------

def test_choose_picture_copies_and_exports(qtbot, tmp_path, monkeypatch):
    # Prepare a tiny valid PNG using QPixmap
    src_img = tmp_path / "src.png"
    pm = QPixmap(1, 1)
    pm.fill(QColor("white"))
    assert pm.save(str(src_img), "PNG")

    # Patch QFileDialog.getOpenFileName to return our image
    from metaedit import app as app_mod

    def fake_get_open_file_name(parent=None, caption="", directory="", filter_str=""):
        return str(src_img), "Images (*.png *.jpg *.jpeg *.webp)"

    # Patch the actual symbol used by the app: _choose_picture imports QFileDialog locally
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        staticmethod(fake_get_open_file_name),
    )

    # Patch pictures destination directory to be tmp_path
    monkeypatch.setattr(app_mod, "PICTURES_DIR", str(tmp_path))

    # Create window
    win = app_mod.MetadataMainWindow()
    qtbot.addWidget(win)
    # no show() in headless mode

    # Step 1: New speaker
    win.page_select.rb_new.setChecked(True)
    win.page_select.new_brand.setText("TestBrandX")
    win.page_select.new_speaker_model.setText("ModelY 123")

    # Next to edit
    QApplication.processEvents()
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit

    # Click choose picture -> should copy to PICTURES_DIR/TestBrandX ModelY 123.png
    win.page_edit.choose_picture_btn.click()
    QApplication.processEvents()

    dest_path = os.path.join(str(tmp_path), "TestBrandX ModelY 123.png")
    assert os.path.isfile(dest_path)

    # The model should record the picture path
    assert win.current is not None
    assert win.current.picture == dest_path

    # The UI label should now have a pixmap (and no placeholder text)
    lbl = win.page_edit.picture_label
    assert lbl.pixmap() is not None
    assert lbl.text() in (None, "")

    # Proceed to review and validate export contains picture
    # Set a valid measurement key before proceeding
    tabs = win.page_edit.measurements_tabs
    panel = tabs.widget(0)
    le_key = panel.findChild(QLineEdit, "meas_key")
    if isinstance(le_key, QLineEdit):
        le_key.setText("m1")
    QApplication.processEvents()
    win.page_edit.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_review
    data = json.loads(win.page_review.summary.toPlainText())
    assert data["brand"] == "TestBrandX"
    assert data["model"] == "ModelY 123"
    assert data.get("picture") == dest_path


# --------------------
# Prefill tests
# --------------------

def test_prefill_existing_speaker(qtbot):
    from metaedit.app import MetadataMainWindow

    name, meta = _pick_sample_speaker()

    win = MetadataMainWindow()
    qtbot.addWidget(win)

    # Ensure we're in Existing mode
    win.page_select.rb_existing.setChecked(True)

    # Select the sample speaker in the combobox
    cb = win.page_select.speakers_cb
    idx = cb.findText(name)
    assert idx >= 0, "Sample speaker not listed in combobox"
    cb.setCurrentIndex(idx)

    # Proceed to Step 2
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit

    # Basic fields
    assert win.page_edit.form_brand.text() == meta.get("brand")
    assert win.page_edit.form_model.text() == meta.get("model")
    # type/shape/amount are comboboxes; only assert when value exists in metadata
    _t = meta.get("type")
    if isinstance(_t, str):
        assert win.page_edit.form_type_cb.currentText() == _t
    _s = meta.get("shape")
    if isinstance(_s, str):
        assert win.page_edit.form_shape_cb.currentText() == _s
    assert win.page_edit.form_price.text() == (meta.get("price") or "")
    _a = meta.get("amount")
    if isinstance(_a, str):
        assert win.page_edit.form_amount.currentText() == _a

    # Default measurement selector
    dm = meta.get("default_measurement")
    if isinstance(dm, str):
        assert win.page_edit.default_meas_cb.currentText() == dm

    # Measurement panels count must match
    measurements = meta.get("measurements", {})
    expected_count = len(measurements)
    actual_count = win.page_edit.measurements_tabs.count()
    assert actual_count == expected_count

    # Validate a sample measurement prefill (first one)
    # Access the first panel widget
    if expected_count:
        panel = win.page_edit.measurements_tabs.widget(0)
        assert panel is not None
        # Check a few representative fields
        first_key = next(iter(measurements))
        first_meas = measurements[first_key]
        fmt = first_meas.get("format") if isinstance(first_meas, dict) else None
        origin = first_meas.get("origin") if isinstance(first_meas, dict) else None
        de_str = first_meas.get("review_published") if isinstance(first_meas, dict) else None

        cb_format: QComboBox | None = panel.findChild(QComboBox, "meas_format")
        le_origin: QLineEdit | None = panel.findChild(QLineEdit, "meas_origin")
        de: QDateEdit | None = panel.findChild(QDateEdit, "meas_review_date")

        if fmt:
            assert cb_format is not None
            assert cb_format.currentText() == fmt
        if origin:
            assert le_origin is not None
            assert le_origin.text() == origin
        if isinstance(de_str, str) and len(de_str) == 8:
            assert de is not None
            qd = QDate.fromString(de_str, "yyyyMMdd")
            assert qd.isValid()
            assert de.date() == qd


# --------------------
# Qt export tests
# --------------------

def test_step1_to_step3_export_matches_loaded(qtbot):
    from metaedit.app import MetadataMainWindow

    name, raw = _pick_sample_speaker()

    win = MetadataMainWindow()
    qtbot.addWidget(win)

    # Step 1: select existing speaker
    win.page_select.rb_existing.setChecked(True)
    cb = win.page_select.speakers_cb
    idx = cb.findText(name)
    assert idx >= 0
    cb.setCurrentIndex(idx)

    # Step 1 -> Step 2
    win.page_select.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_edit

    # Step 2 -> Step 3
    win.page_edit.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_review

    # Read JSON preview
    txt = win.page_review.summary.toPlainText()
    assert txt
    actual = json.loads(txt)

    expected = _normalize_expected_export(cast(Dict[str, Any], raw))

    assert actual == expected


# --------------------
# Sections and layout tests
# --------------------

def test_collapsible_sections_default_and_toggle(qtbot):
    from PySide6.QtWidgets import QWidget
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    assert tabs.count() >= 1
    panel: QWidget = tabs.widget(0)

    # Find toggles and containers
    da_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_da")
    ex_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_ex")
    da_container: QWidget | None = panel.findChild(QWidget, "da_container")
    ex_container: QWidget | None = panel.findChild(QWidget, "ex_container")

    assert da_toggle is not None and ex_toggle is not None
    assert da_container is not None and ex_container is not None

    # Hidden by default
    assert not da_container.isVisible()
    assert not ex_container.isVisible()

    # Toggle ON
    da_toggle.click()
    ex_toggle.click()
    QApplication.processEvents()
    
    # Instead of waiting for isVisible(), wait for isVisibleTo() which works in this context
    qtbot.waitUntil(lambda: da_container.isVisibleTo(panel) and ex_container.isVisibleTo(panel), timeout=5000)

    # Toggle OFF
    da_toggle.click()
    ex_toggle.click()
    QApplication.processEvents()
    # Instead of waiting for isVisible(), wait for isVisibleTo() which works in this context
    qtbot.waitUntil(lambda: not da_container.isVisibleTo(panel) and not ex_container.isVisibleTo(panel), timeout=5000)


def test_extras_two_columns_and_specs_fields_present(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Extras two columns (two QFormLayouts inside ex_container)
    ex_container: QWidget | None = panel.findChild(QWidget, "ex_container")
    assert ex_container is not None
    # The two columns are QFormLayouts; traverse layouts by counting children that are QFormLayout
    form_layouts = ex_container.findChildren(QFormLayout)
    assert len(form_layouts) >= 2

    # Specifications expanded fields present
    assert panel.findChild(QLineEdit, "sp_disp_h") is not None
    assert panel.findChild(QLineEdit, "sp_disp_v") is not None
    assert panel.findChild(QLineEdit, "sp_spl_max") is not None
    assert panel.findChild(QLineEdit, "sp_spl_m_noise") is not None
    assert panel.findChild(QLineEdit, "sp_spl_b_noise") is not None
    assert panel.findChild(QLineEdit, "sp_spl_pink_noise") is not None


def test_collect_form_exports_nested_spec_fields(qtbot):
    from metaedit.app import MetadataMainWindow

    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Fill required key
    le_key = panel.findChild(QLineEdit, "meas_key")
    assert isinstance(le_key, QLineEdit)
    le_key.setText("t1")

    # Fill some specifications fields
    for name, value in (
        ("sp_sens", "87.5"),
        ("sp_imp", "4"),
        ("sp_weight", "12.3"),
        ("sp_h", "300"),
        ("sp_w", "180"),
        ("sp_d", "250"),
    ):
        w = panel.findChild(QLineEdit, name)
        assert isinstance(w, QLineEdit)
        w.setText(value)

    # Dispersion
    w = panel.findChild(QLineEdit, "sp_disp_h")
    assert isinstance(w, QLineEdit)
    w.setText("90")
    w = panel.findChild(QLineEdit, "sp_disp_v")
    assert isinstance(w, QLineEdit)
    w.setText("40")

    # SPL
    for name, value in (
        ("sp_spl_peak", "110"),
        ("sp_spl_long", "98"),
        ("sp_spl_max", "112"),
        ("sp_spl_m_noise", "101"),
        ("sp_spl_b_noise", "99"),
        ("sp_spl_pink_noise", "100"),
    ):
        w = panel.findChild(QLineEdit, name)
        assert isinstance(w, QLineEdit)
        w.setText(value)

    # Proceed to review to trigger _collect_form
    win.page_edit.next_btn.click()
    QApplication.processEvents()
    assert win.stack.currentWidget() is win.page_review

    # Grab JSON summary
    txt = win.page_review.summary.toPlainText().strip()
    assert txt
    data = json.loads(txt)

    meas = data["measurements"]["t1"]
    specs = meas["specifications"]

    # Flat fields
    assert specs["spl_peak"] == 110.0
    assert specs["spl_long_term"] == 98.0

    # Nested dispersion
    assert specs["dispersion"]["horizontal"] == 90.0
    assert specs["dispersion"]["vertical"] == 40.0

    # Nested SPL alias
    assert "SPL" in specs
    spl = specs["SPL"]
    assert spl["peak"] == 110.0
    assert spl["continuous"] == 98.0
    assert spl["max"] == 112.0
    assert spl["m_noise"] == 101.0
    assert spl["b_noise"] == 99.0
    assert spl["pink_noise"] == 100.0


def test_default_symmetry_and_group_boxes_present(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Default symmetry is 'none'
    cb: QComboBox | None = panel.findChild(QComboBox, "meas_symmetry")
    assert cb is not None
    assert cb.currentText().strip().lower() == "none"

    # Group frames exist with headers
    for obj, header in (
        ("reviews_box", "Reviews"),
        ("specs_box", "Specifications"),
        ("da_box", "Data Acquisition"),
        ("ex_box", "Extras"),
    ):
        box: QFrame | None = panel.findChild(QFrame, obj)
        assert box is not None
        # A QLabel child with the expected header text exists inside the box
        labels = box.findChildren(QLabel)
        assert any(l.text() == header for l in labels)


def test_amount_combobox_and_shape_no_empty(qtbot):
    win = _goto_step2(qtbot)

    # Amount is a combobox with fixed options
    amt = win.page_edit.form_amount
    assert isinstance(amt, QComboBox)
    items = [amt.itemText(i) for i in range(amt.count())]
    assert items == ["each", "pair"]

    # Shape has no empty option
    shp = win.page_edit.form_shape_cb
    assert isinstance(shp, QComboBox)
    shp_items = [shp.itemText(i) for i in range(shp.count())]
    assert "" not in shp_items
    assert shp_items[0] != ""


def test_specs_before_da_and_extras_and_brand_model_wider(qtbot):
    from typing import cast

    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Ordering: Specifications comes before DA and Extras in the main panel layout
    layout = panel.layout()
    assert layout is not None
    specs_box = panel.findChild(QFrame, "specs_box")
    da_box = panel.findChild(QFrame, "da_box")
    ex_box = panel.findChild(QFrame, "ex_box")
    assert specs_box and da_box and ex_box
    idx_specs = layout.indexOf(specs_box)
    idx_da = layout.indexOf(da_box)
    idx_ex = layout.indexOf(ex_box)
    assert 0 <= idx_specs < idx_da
    assert 0 <= idx_specs < idx_ex

    # Brand/Model fields are wider (min width >= 260)
    assert win.page_edit.form_brand.minimumWidth() >= 260
    assert win.page_edit.form_model.minimumWidth() >= 260


def test_collapsed_headers_compact(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # DA toggle icon size small and margins reduced
    da_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_da")
    assert da_toggle is not None
    icon_sz: QSize = da_toggle.iconSize()
    assert icon_sz.width() <= 12 and icon_sz.height() <= 12

    # Layout margins on DA box are compact
    da_box: QFrame | None = panel.findChild(QFrame, "da_box")
    assert da_box is not None
    lay = da_box.layout()
    assert lay is not None
    m = lay.contentsMargins()
    assert m.left() <= 6 and m.top() <= 4 and m.right() <= 6 and m.bottom() <= 4


def test_extras_header_compact(qtbot):
    win = _goto_step2(qtbot)

    tabs = win.page_edit.measurements_tabs
    panel: QWidget = tabs.widget(0)

    # Extras toggle icon size small and margins reduced
    ex_toggle: QToolButton | None = panel.findChild(QToolButton, "toggle_ex")
    assert ex_toggle is not None
    icon_sz: QSize = ex_toggle.iconSize()
    assert icon_sz.width() <= 12 and icon_sz.height() <= 12

    # Layout margins on Extras box are compact
    ex_box: QFrame | None = panel.findChild(QFrame, "ex_box")
    assert ex_box is not None
    lay = ex_box.layout()
    assert lay is not None
    m = lay.contentsMargins()
    assert m.left() <= 6 and m.top() <= 4 and m.right() <= 6 and m.bottom() <= 4
