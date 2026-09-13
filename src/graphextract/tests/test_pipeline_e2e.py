# -*- coding: utf-8 -*-
"""End-to-end tests: synthetic truth -> canonical pipeline -> strict scoring.

The renderer plays the role of independently verified geometry: anchors are
labelled ``renderer_verified_test`` and the production score still uses only
the strict pixel/support/completeness metrics.
"""

import math

import cv2
import numpy as np

from graphextract.calibration import ScaleType
from graphextract.evaluate import (
    production_summary,
    score_panel_completeness,
    score_series,
)
from graphextract.evidence import StyleSpec
from graphextract.ocr_adapters import OCRWord
from graphextract.pipeline import manifest, run_document, run_panel
from graphextract.schema import PanelOutcome, SegmentStatus

from helpers import dense_reference, log_sine_panel, renderer_anchors, styles_ab


def _run_verified(crossing: bool):
    img, panel, truth = log_sine_panel(crossing=crossing)
    x0, y0, w, h = panel.rect_xywh
    interior = img[y0:y0 + h, x0:x0 + w]
    anchors = renderer_anchors(panel, truth, (x0, y0), "renderer_verified_test")
    res = run_panel(img, "img#p0", interior, (x0, y0), anchors, styles_ab())
    return res, truth, (x0, x0 + w - 1)


def _pred_arrays(res, sid):
    tr = next(s for s in res.series if s.series_id == sid)
    u = [s.u for s in tr.samples]
    v = [s.v for s in tr.samples]
    obs = [s.status.value == "observed" for s in tr.samples]
    return u, v, obs


def test_strict_one_pixel_pass_on_clean_two_curve_chart():
    res, truth, span = _run_verified(crossing=False)
    assert res.outcome is PanelOutcome.COMPLETE, res.review_reasons
    scores = {}
    for sid in ("a", "b"):
        u, v, obs = _pred_arrays(res, sid)
        ru, rv, vis = dense_reference(truth, sid, *span)
        sc = score_series(u, v, obs, ru, rv, vis, sid)
        scores[sid] = sc
        assert sc.strict_pass, (sid, sc)
        assert sc.max_px <= 1.0
    panel_score = score_panel_completeness("img#p0", ["a", "b"], ["a", "b"], scores)
    assert panel_score.outcome is PanelOutcome.COMPLETE
    summary = production_summary(res_panel_doc(res), [panel_score])
    assert summary["oracle_inputs_used"] is False
    assert summary["panel_acceptance_rate"] == 1.0


def res_panel_doc(res):
    from graphextract.pipeline import PIPELINE_VERSION
    from graphextract.schema import DocumentResult

    return DocumentResult("d", "img", 1, 1, "x", panels=[res],
                          provenance={"pipeline": PIPELINE_VERSION})


def test_crossing_preserves_identities():
    res, truth, span = _run_verified(crossing=True)
    au, av, aobs = _pred_arrays(res, "a")
    bu, bv, bobs = _pred_arrays(res, "b")
    rau, rav, _ = dense_reference(truth, "a", *span)
    rbu, rbv, _ = dense_reference(truth, "b", *span)
    # Columns where the true curves are well separated.
    near = set()
    for u, ya, yb in zip(rau, rav, np.interp(rau, rbu, rbv)):
        if abs(ya - yb) < 3.0:
            near.add(int(round(u)))
    checked = 0
    for u, va, vb, oa, ob in zip(au, av, bv, aobs, bobs):
        if int(round(u)) in near or not (oa and ob):
            continue
        ra = float(np.interp(u, rau, rav))
        rb = float(np.interp(u, rbu, rbv))
        # Identity preserved: each track follows its own truth, not the other's.
        assert abs(va - ra) < 1.0 and abs(vb - rb) < 1.0, (u, va, ra, vb, rb)
        assert abs(va - ra) <= abs(va - rb) + 1e-9
        assert abs(vb - rb) <= abs(vb - ra) + 1e-9
        checked += 1
    assert checked > 100


def test_document_words_yield_log_data_coordinates():
    """Full-image margin words calibrate the run: samples carry log-Hz
    x values (not pixels) while the outcome stays review-gated."""
    img = np.full((300, 500, 3), 255, np.uint8)
    img[40:43, 60:441] = (0, 0, 0)
    img[257:260, 60:441] = (0, 0, 0)
    img[40:260, 60:63] = (0, 0, 0)
    img[40:260, 438:441] = (0, 0, 0)
    for gx in (60, 250, 440):
        img[40:260, gx:gx + 2] = (180, 180, 180)
    for gy in (40, 150, 259):
        img[gy:gy + 2, 60:441] = (180, 180, 180)
    cv2.line(img, (60, 259), (440, 40), (0, 0, 255), 2)
    words = [
        OCRWord("20", 50, 265, 20, 14, 0.9),
        OCRWord("200", 240, 265, 24, 14, 0.9),
        OCRWord("2000", 425, 265, 30, 14, 0.9),
        OCRWord("0", 44, 33, 14, 14, 0.9),
        OCRWord("50", 28, 143, 18, 14, 0.9),
        OCRWord("100", 24, 250, 26, 14, 0.9),
    ]
    doc = run_document(img, "img", [StyleSpec("s", "S", (0, 0, 255))], words=words)
    assert len(doc.panels) == 1
    panel = doc.panels[0]
    assert panel.axes["x"].scale is ScaleType.LOG10
    assert panel.axes["y_left"].scale is ScaleType.LINEAR
    assert panel.outcome is PanelOutcome.PARTIAL_REVIEW  # ocr_unverified, never guessed
    assert any("not verified" in r for r in panel.review_reasons)
    track = panel.series[0]
    observed = [s for s in track.samples if s.status is SegmentStatus.OBSERVED]
    assert len(observed) > 200
    ox = panel.panel.interior_xywh[0]
    for sample in observed[::50]:
        assert sample.value_x is not None and sample.value_y is not None
        expected = math.log10(20.0) + (sample.u - ox) / 380.0 * 2.0
        assert abs(math.log10(sample.value_x) - expected) < 0.05


def test_di_labels_assign_to_calibrated_right_axis():
    """Directivity labels ride y_right once right ticks calibrate it."""
    from graphextract.pipeline import _axis_for_label
    for label in ("Directivity Index", "Reflections Dl", "Index",
                  "Early Reflections DI", "Sound Power DI"):
        assert _axis_for_label(label) == "y_right"
    for label in ("On Axis", "Sound Power", "Listening Window",
                  "Reflections", "Estimated In-Room"):
        assert _axis_for_label(label) == "y_left"


def test_right_axis_ticks_assign_di_series_to_y_right():
    """End to end: right-margin ticks fit y_right and DI series use it."""
    img = np.full((340, 500, 3), 255, np.uint8)
    img[40:43, 60:441] = (0, 0, 0)
    img[277:280, 60:441] = (0, 0, 0)
    img[40:280, 60:63] = (0, 0, 0)
    img[40:280, 438:441] = (0, 0, 0)
    for gx in (60, 250, 440):
        img[40:280, gx:gx + 2] = (180, 180, 180)
    for gy in (40, 130, 220):
        img[gy:gy + 2, 60:441] = (180, 180, 180)
    words = [
        OCRWord("20", 50, 290, 20, 14, 0.9),
        OCRWord("200", 240, 290, 24, 14, 0.9),
        OCRWord("2000", 425, 290, 30, 14, 0.9),
        OCRWord("0", 44, 33, 14, 14, 0.9),
        OCRWord("50", 40, 123, 18, 14, 0.9),
        OCRWord("100", 36, 213, 26, 14, 0.9),
        OCRWord("0", 452, 33, 14, 14, 0.9),
        OCRWord("5", 454, 123, 14, 14, 0.9),
        OCRWord("10", 450, 213, 18, 14, 0.9),
    ]
    styles = [StyleSpec("m", "On Axis", (0, 0, 255)),
              StyleSpec("d", "Directivity Index", (0, 255, 0))]
    doc = run_document(img, "img", styles, words=words)
    assert len(doc.panels) == 1
    panel = doc.panels[0]
    assert "y_right" in panel.axes
    by_label = {sr.label: sr for sr in panel.series}
    assert by_label["On Axis"].axis_id == "y_left"
    assert by_label["Directivity Index"].axis_id == "y_right"


def test_manifest_lists_review_queue_and_provenance():
    res, _, _ = _run_verified(crossing=False)
    doc = res_panel_doc(res)
    m = manifest(doc)
    assert m["oracle_inputs_used"] is False
    assert m["pipeline"] == doc.provenance["pipeline"]
    assert m["panels"][0]["outcome"] == "complete"
    assert m["panels"][0]["observed_support"] == {"a": len(doc.panels[0].series[0].samples),
                                                  "b": len(doc.panels[0].series[1].samples)}
    assert m["review_queue"] == []
