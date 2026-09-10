# -*- coding: utf-8 -*-
"""Tests for shadow.py: comparison, gates, promote/refuse/rollback."""

import numpy as np
import pytest

from graphextract.shadow import (
    Candidate,
    check_gates,
    current,
    promote,
    rollback,
    shadow_compare,
)
from graphextract.training import strict_rate_for_truth, synth_panel, verified_anchors, render_truth


def _items(n: int = 2, seed: int = 0):
    rnd = np.random.default_rng(seed)
    items = []
    for i in range(n):
        panel, styles = synth_panel(rnd, crossing=(i % 2 == 1))
        truth = render_truth(panel)
        x0, y0, w, h = panel.rect_xywh
        anchors = verified_anchors(panel, truth, (x0, y0))
        span = (x0, x0 + w - 1)
        items.append({
            "img": truth.image, "panel_id": f"img#p{i}",
            "interior": truth.image[y0:y0 + h, x0:x0 + w], "offset": (x0, y0),
            "anchors": anchors, "styles": styles,
            "strict_checker": (lambda res, t=truth, s=span:
                               all(m["strict"] for m in
                                   strict_rate_for_truth(res, t, s).values())),
        })
    return items


def test_gates_require_no_regression():
    base = {"n_failed": 0, "accept_rate": 0.8, "strict_rate": 0.7}
    assert check_gates(base, dict(base)).passed
    assert not check_gates(base, {**base, "n_failed": 1}).passed
    assert not check_gates(base, {**base, "accept_rate": 0.7}).passed
    assert not check_gates(base, {**base, "strict_rate": 0.6}).passed


def test_shadow_compare_and_promote_cycle(tmp_path):
    items = _items()
    inc = Candidate("incumbent")
    same = Candidate("challenger-same")
    report = shadow_compare(items, inc, [same])
    assert set(report["candidates"]) == {"incumbent", "challenger-same"}
    gate = report["candidates"]["challenger-same"]["gate"]
    assert gate["passed"] and gate["details"]["failed_delta"] == 0
    promote("challenger-same", report, tmp_path)
    assert current(tmp_path)["name"] == "challenger-same"
    promote("incumbent", {**report, "candidates": {
        **report["candidates"],
        "incumbent": {**report["candidates"]["incumbent"],
                      "gate": {"passed": True, "details": {}}}}}, tmp_path)
    assert current(tmp_path)["name"] == "incumbent"
    assert rollback(tmp_path)["name"] == "challenger-same"
    assert current(tmp_path)["name"] == "challenger-same"


def test_promote_refuses_failing_gates(tmp_path):
    report = {"candidates": {"bad": {"gate": {"passed": False, "details": {}}}}}
    with pytest.raises(ValueError):
        promote("bad", report, tmp_path)
    assert current(tmp_path) is None
    with pytest.raises(ValueError):
        rollback(tmp_path)
