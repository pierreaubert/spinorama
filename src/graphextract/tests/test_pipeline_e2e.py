# -*- coding: utf-8 -*-
"""End-to-end tests: synthetic truth -> canonical pipeline -> strict scoring.

The renderer plays the role of independently verified geometry: anchors are
labelled ``renderer_verified_test`` and the production score still uses only
the strict pixel/support/completeness metrics.
"""

import numpy as np

from graphextract.evaluate import (
    production_summary,
    score_panel_completeness,
    score_series,
)
from graphextract.pipeline import manifest, run_panel
from graphextract.schema import PanelOutcome

from tests.helpers import dense_reference, log_sine_panel, renderer_anchors, styles_ab


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
