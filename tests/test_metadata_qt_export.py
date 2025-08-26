import json
from typing import Any, Dict, cast
import pytest
from PySide6.QtCore import Qt

pytestmark = pytest.mark.qt


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
        cast(Dict[str, Any], data.get("measurements"))
        if isinstance(data.get("measurements"), dict)
        else {}
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
            cast(Dict[str, Any], m.get("data_acquisition"))
            if isinstance(m.get("data_acquisition"), dict)
            else {}
        )
        em["data_acquisition"] = {
            "via": (cast(str, da.get("via")) if isinstance(da.get("via"), str) else None),
            "distance": _to_float(da.get("distance")),
            "signal": (cast(str, da.get("signal")) if isinstance(da.get("signal"), str) else None),
            "resolution": _to_float(da.get("resolution")),
            "min_valid_freq": _to_float(da.get("min_valid_freq")),
            "max_valid_freq": _to_float(da.get("max_valid_freq")),
            # UI default: unchecked => False (kept in export)
            "air_absorbtion": bool(da.get("air_absorbtion"))
            if da.get("air_absorbtion") is not None
            else False,
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
        ex: Dict[str, Any] = (
            cast(Dict[str, Any], m.get("extras")) if isinstance(m.get("extras"), dict) else {}
        )
        em["extras"] = {
            # UI default is unchecked -> False (kept)
            "is_equed": bool(ex.get("is_equed")) if ex.get("is_equed") is not None else False,
            "score_penalty": _to_float(ex.get("score_penalty")),
        }
        if _block_empty(em["extras"]):
            em["extras"] = None
        # Specifications (support nested SPL)
        sp: Dict[str, Any] = (
            cast(Dict[str, Any], m.get("specifications"))
            if isinstance(m.get("specifications"), dict)
            else {}
        )
        size: Dict[str, Any] = (
            cast(Dict[str, Any], sp.get("size")) if isinstance(sp.get("size"), dict) else {}
        )
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


# _prune_none was superseded by using prune_empty from models; helper removed.


def test_step1_to_step3_export_matches_loaded(qtbot):
    from metaedit.app import MetadataMainWindow

    name, raw = _pick_sample_speaker()

    win = MetadataMainWindow()
    qtbot.addWidget(win)
    win.show()

    # Step 1: select existing speaker
    win.page_select.rb_existing.setChecked(True)
    cb = win.page_select.speakers_cb
    idx = cb.findText(name)
    assert idx >= 0
    cb.setCurrentIndex(idx)

    # Step 1 -> Step 2
    qtbot.mouseClick(win.page_select.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_edit

    # Step 2 -> Step 3
    qtbot.mouseClick(win.page_edit.next_btn, Qt.MouseButton.LeftButton)
    assert win.stack.currentWidget() is win.page_review

    # Read JSON preview
    txt = win.page_review.summary.toPlainText()
    assert txt
    actual = json.loads(txt)

    expected = _normalize_expected_export(cast(Dict[str, Any], raw))

    assert actual == expected
