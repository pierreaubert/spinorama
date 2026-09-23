# -*- coding: utf-8 -*-
"""Tests for jina_fallback.py: order pairing, fail-closed cases, review flag."""

import numpy as np

from graphextract import jina_fallback
from graphextract.calibration import ScaleType
from graphextract.jina_fallback import (
    FALLBACK_CONFIDENCE,
    FALLBACK_SOURCE,
    fallback_anchors,
    maybe_jina_fallback,
    split_axis_values,
)


def test_split_y_then_x_blocks():
    values = [85.0, 80.0, 75.0, 100.0, 1000.0, 10000.0]
    assert split_axis_values(values, 3, 3) == ([100.0, 1000.0, 10000.0],
                                               [75.0, 80.0, 85.0])


def test_split_x_then_y_blocks():
    values = [100.0, 1000.0, 85.0, 80.0, 75.0]
    assert split_axis_values(values, 2, 3) == ([100.0, 1000.0],
                                               [75.0, 80.0, 85.0])


def test_split_count_mismatch_fails_closed():
    assert split_axis_values([85.0, 80.0, 100.0, 1000.0], 3, 3) is None


def test_split_prefers_log_spanning_x():
    # Both orientations satisfy counts and monotonicity; the wider x span wins.
    assert split_axis_values([1.0, 2.0, 3.0, 4.0], 2, 2) == ([1.0, 2.0], [3.0, 4.0])
    assert split_axis_values([3.0, 4.0, 1.0, 2.0], 2, 2) == ([1.0, 2.0], [3.0, 4.0])


def test_split_needs_two_anchors_per_axis():
    assert split_axis_values([85.0, 100.0, 1000.0], 2, 1) is None


def test_fallback_anchors_geometry_and_source():
    anchors, status = fallback_anchors("85 80 75 100 1000 10000", [10, 50, 90],
                                       [5, 45, 85])
    assert status["status"] == "ok"
    assert anchors is not None
    assert [(a.pixel, a.value) for a in anchors.x] == [(10, 100.0), (50, 1000.0),
                                                       (90, 10000.0)]
    assert [(a.pixel, a.value) for a in anchors.y_left] == [(5, 75.0), (45, 80.0),
                                                            (85, 85.0)]
    assert not anchors.y_right
    assert all(a.source == FALLBACK_SOURCE for a in anchors.x + anchors.y_left)
    assert all(a.confidence == FALLBACK_CONFIDENCE for a in anchors.x + anchors.y_left)
    assert anchors.source == FALLBACK_SOURCE
    assert anchors.x_scale is ScaleType.LOG10 and anchors.x_unit == "Hz"
    assert anchors.y_unit == "dB"


def test_fallback_anchors_no_match_returns_none():
    anchors, status = fallback_anchors("hello world", [10, 50], [5, 45])
    assert anchors is None and status["status"] == "no_count_match"
    anchors, status = fallback_anchors("85 80 100 1000", [10, 50, 90], [5, 45, 85])
    assert anchors is None and status["status"] == "no_count_match"


def test_fallback_partial_trailing_axis():
    # y_left block, x block, extra right-axis block: pair the prefix.
    text = "90 85 80 100 1000 35 30 25"
    anchors, status = fallback_anchors(text, [10, 50], [5, 45, 85])
    assert status["status"] == "partial" and status["unpaired"] == 3
    assert anchors is not None
    assert [a.value for a in anchors.x] == [100.0, 1000.0]
    assert [a.value for a in anchors.y_left] == [80.0, 85.0, 90.0]


def test_fallback_partial_leading_axis():
    text = "35 30 25 90 85 80 100 1000"
    anchors, status = fallback_anchors(text, [10, 50], [5, 45, 85])
    assert status["status"] == "partial" and status["edge"] == "suffix"
    assert anchors is not None
    assert [a.value for a in anchors.y_left] == [80.0, 85.0, 90.0]


def test_fallback_low_y_block_routes_right():
    anchors, status = fallback_anchors("35 30 25 100 1000", [10, 50], [5, 45, 85])
    assert status["status"] == "ok"
    assert anchors is not None
    assert not anchors.y_left
    assert [a.value for a in anchors.y_right] == [25.0, 30.0, 35.0]
    assert anchors.y_right_unit == "dB"


class _StubReader:
    def __init__(self, text: str):
        self.text = text

    def transcribe_array(self, array, prompt=None):  # noqa: ARG002
        return self.text


def test_maybe_fallback_success_flags_review(monkeypatch):
    monkeypatch.setattr(jina_fallback, "detect_grid_lines",
                        lambda interior: ([10, 50, 90], [5, 45, 85]))
    crop = np.zeros((40, 60, 3), np.uint8)
    anchors, status = maybe_jina_fallback(
        crop, crop, "panel#1", _StubReader("85 80 75 100 1000 10000"))
    assert anchors is not None and len(anchors.x) == 3 and len(anchors.y_left) == 3
    assert status == {"source": FALLBACK_SOURCE, "status": "ok", "needs_review": True}


def test_maybe_fallback_no_match_stays_empty(monkeypatch):
    monkeypatch.setattr(jina_fallback, "detect_grid_lines",
                        lambda interior: ([10, 50, 90], [5, 45, 85]))
    crop = np.zeros((40, 60, 3), np.uint8)
    anchors, status = maybe_jina_fallback(crop, crop, "panel#1",
                                          _StubReader("no numbers here"))
    assert anchors is None
    assert status["status"] == "no_count_match"
    assert "needs_review" not in status


def test_maybe_fallback_model_failure_is_status():
    class _Boom:
        def transcribe_array(self, array, prompt=None):  # noqa: ARG002
            raise RuntimeError("weights missing")

    crop = np.zeros((40, 60, 3), np.uint8)
    anchors, status = maybe_jina_fallback(crop, crop, "panel#1", _Boom())
    assert anchors is None
    assert status["status"].startswith("transcribe_failed")
