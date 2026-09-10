# -*- coding: utf-8 -*-
"""Tests for confidence.py: calibration improves on baseline, gates behave."""

import numpy as np
import pytest

from graphextract.confidence import (
    ConfidenceCalibrator,
    auto_acceptable,
    panel_features,
    select_threshold,
)
from graphextract.pipeline import AxisAnchors, run_panel
from graphextract.schema import PanelOutcome, PanelResult
from graphextract.training import (
    strict_rate_for_truth,
    synth_panel,
    verified_anchors,
    render_truth,
)


def _panels_and_labels(n_pos: int = 6, n_neg: int = 6, seed: int = 0):
    rnd = np.random.default_rng(seed)
    panels, labels = [], []
    for i in range(n_pos):
        panel, styles = synth_panel(rnd, crossing=False)
        truth = render_truth(panel)
        x0, y0, w, h = panel.rect_xywh
        res = run_panel(truth.image, f"pos#p{i}", truth.image[y0:y0 + h, x0:x0 + w],
                        (x0, y0), verified_anchors(panel, truth, (x0, y0)), styles)
        panels.append(res)
        m = strict_rate_for_truth(res, truth, (x0, x0 + w - 1))
        labels.append(bool(m) and all(v["strict"] for v in m.values()))
    for i in range(n_neg):
        panel, styles = synth_panel(rnd, crossing=bool(i % 2))
        truth = render_truth(panel)
        x0, y0, w, h = panel.rect_xywh
        res = run_panel(truth.image, f"neg#p{i}", truth.image[y0:y0 + h, x0:x0 + w],
                        (x0, y0), AxisAnchors(), styles)
        panels.append(res)
        labels.append(False)
    return panels, labels


def test_calibrator_beats_constant_baseline(tmp_path):
    panels, labels = _panels_and_labels()
    assert any(labels) and not all(labels)
    cal = ConfidenceCalibrator()
    rep = cal.fit(panels, labels)
    assert rep["brier"] < rep["baseline_brier"]
    proba = cal.predict_proba(panels)
    assert proba.shape == (len(panels),) and bool(((proba >= 0) & (proba <= 1)).all())
    assert proba[np.array(labels)].mean() > proba[~np.array(labels)].mean()
    p = cal.save(tmp_path / "cal.npz")
    assert ConfidenceCalibrator.load(p).predict_proba(panels) == pytest.approx(proba)


def test_threshold_selection_and_gates():
    panels, labels = _panels_and_labels()
    cal = ConfidenceCalibrator()
    cal.fit(panels, labels)
    proba = cal.predict_proba(panels)
    point = select_threshold(proba, labels, target_precision=0.9)
    assert point.precision >= 0.9 and point.coverage > 0
    with pytest.raises(ValueError):
        select_threshold(proba, labels, target_precision=1.0001)
    with pytest.raises(ValueError):
        ConfidenceCalibrator().fit(panels[:2], labels[:2])
    pos = next(p for p, lab in zip(panels, labels) if lab)
    assert auto_acceptable(pos, cal, point.threshold)
    failed = PanelResult(panel=pos.panel, outcome=PanelOutcome.FAILED)
    assert not auto_acceptable(failed, cal, 0.0)
    feats = panel_features(panels[0])
    assert feats["support_frac"] > 0.9 and feats["n_review"] == 0
