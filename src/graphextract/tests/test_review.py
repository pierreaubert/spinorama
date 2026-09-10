# -*- coding: utf-8 -*-
"""Tests for review.py: correction validation, application, re-run, export."""

import json

import pytest

from graphextract.pipeline import AxisAnchors
from graphextract.review import (
    Correction,
    apply_corrections,
    build_html_bundle,
    export_regression_case,
    rerun_with_corrections,
)
from graphextract.schema import PanelOutcome, TickAnchor

from tests.helpers import log_sine_panel, renderer_anchors, styles_ab


def test_correction_rejects_unknown_target():
    with pytest.raises(ValueError):
        Correction("telepathy", "p0", {})


def test_tick_and_scale_corrections_verify_anchors():
    base = AxisAnchors()
    now = 123.0
    corr = Correction("tick", "p0", {"axis": "x", "pixel": 40, "value": 20.0},
                      author="rev", timestamp=now, rationale="first tick")
    anchors, notes = apply_corrections(base, [corr])
    assert anchors.source == "user_verified"
    assert len(anchors.x) == 1 and anchors.x[0].source == "manual"
    assert Correction.from_dict(corr.to_dict()).timestamp == now
    anchors2, _ = apply_corrections(
        anchors, [Correction("scale_unit", "p0", {"axis": "x", "scale": "log10",
                                                 "unit": "Hz"})])
    assert anchors2.x_scale.value == "log10" and anchors2.x_unit == "Hz"


def test_rerun_with_manual_tick_completes_panel():
    img, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    interior = img[y0:y0 + h, x0:x0 + w]
    full = renderer_anchors(panel, truth, (x0, y0), "renderer_verified_test")
    # Drop to two x anchors: fit needs independent support -> review, not numbers.
    short = AxisAnchors(x=full.x[:2], y_left=full.y_left, x_scale=full.x_scale,
                        x_unit=full.x_unit, y_unit=full.y_unit,
                        source="renderer_verified_test")
    res0, _ = rerun_with_corrections(img, "img#p0", interior, (x0, y0), short,
                                     styles_ab(), [])
    assert res0.outcome is PanelOutcome.PARTIAL_REVIEW
    missing = full.x[2]
    fix = Correction("tick", "img#p0",
                     {"axis": "x", "pixel": missing.pixel, "value": missing.value},
                     rationale="add third anchor")
    res1, notes = rerun_with_corrections(img, "img#p0", interior, (x0, y0), short,
                                         styles_ab(), [fix])
    assert res1.outcome is PanelOutcome.COMPLETE, res1.review_reasons
    assert res1.provenance["corrections"][0]["target"] == "tick"
    assert any("manual tick" in n for n in notes)


def test_regression_export_round_trip(tmp_path):
    img, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    anchors = renderer_anchors(panel, truth, (x0, y0), "renderer_verified_test")
    corr = [Correction("unresolvable", "img#p0", {"u0": 10, "u1": 12},
                       rationale="label overprint")]
    d = export_regression_case(tmp_path, "img", "img#p0", img[y0:y0 + h, x0:x0 + w],
                               anchors, styles_ab(), corr, notes="probe")
    assert (d / "interior.png").exists() and (d / "README.txt").exists()
    loaded = [Correction.from_dict(c) for c in
              json.loads((d / "corrections.json").read_text())]
    assert loaded[0].rationale == "label overprint"
    styles = json.loads((d / "styles.json").read_text())
    assert {s["series_id"] for s in styles} == {"a", "b"}


def test_server_stores_posted_corrections(tmp_path):
    from graphextract.review_server import store_correction

    p = store_correction(tmp_path, {"target": "tick", "panel_id": "img#p0",
                                    "payload": {}})
    assert p.name == "img_p0.jsonl"
    assert json.loads(p.read_text().strip())["target"] == "tick"
    with pytest.raises(ValueError):
        store_correction(tmp_path, {"nope": True})


def test_html_bundle_embeds_panels_and_samples(tmp_path):
    img, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    anchors = renderer_anchors(panel, truth, (x0, y0), "renderer_verified_test")
    from graphextract.pipeline import run_panel
    res = run_panel(img, "img#p0", img[y0:y0 + h, x0:x0 + w], (x0, y0),
                    anchors, styles_ab())
    doc = type("D", (), {"image_id": "img", "panels": [res]})()
    out = build_html_bundle(doc, {"img#p0": img}, tmp_path / "review.html")
    html = out.read_text()
    assert "img#p0" in html and "observed" in html and "correction.json" in html
