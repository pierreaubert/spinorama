# -*- coding: utf-8 -*-
"""Tests for calibration.py: tick parsing, axis fits, DI offset recovery."""

import numpy as np

from graphextract.calibration import (
    AxisRole,
    ScaleType,
    fit_axis,
    parse_di_offset,
    parse_tick_label,
    solve_di_offset,
)
from graphextract.schema import TickAnchor


def test_parse_di_offset_stated_and_unstated():
    assert parse_di_offset("Sound Power DI (Offset:45dB)") == 45.0
    assert parse_di_offset("F228 Early Refelctions DI (Offset:45dB)") == 45.0
    assert parse_di_offset("DI offset 40 dB") == 40.0
    assert parse_di_offset("Sound Power DI") is None
    assert parse_di_offset("Early Reflections Dl") is None
    assert parse_di_offset("") is None


def test_parse_tick_label_superscript_power():
    # Folded superscript notation reads as powers of ten ...
    assert parse_tick_label("10^2") == (100.0, "linear")
    assert parse_tick_label("10^3") == (1000.0, "linear")
    assert parse_tick_label("10²") == (100.0, "linear")
    # ... while plain digit strings keep their face value.
    assert parse_tick_label("102") == (102.0, "linear")
    assert parse_tick_label("103") == (103.0, "linear")


def test_parse_tick_label_trailing_dash_is_tick_mark():
    # A touching tick mark reads as a trailing dash, never a minus.
    assert parse_tick_label("100.0-") == (100.0, "linear")
    assert parse_tick_label("90-") == (90.0, "linear")
    assert parse_tick_label("-80") == (-80.0, "linear")
    assert parse_tick_label("-") is None


def test_detect_frame_ticks_finds_protruding_marks():
    import cv2

    from graphextract.calibration import detect_frame_ticks

    img = np.full((300, 500, 3), 255, np.uint8)
    img[100:103, 50:451] = (60, 60, 60)  # frame bottom edge
    img[97:100, 50:451] = (60, 60, 60)  # frame top edge
    img[40:100, 50:53] = (60, 60, 60)  # frame left edge
    img[40:100, 448:451] = (60, 60, 60)  # frame right edge
    for tx in (100, 250, 400):  # ticks protruding below the frame
        img[103:115, tx - 1:tx + 2] = (60, 60, 60)
    tick_xs, tick_ys = detect_frame_ticks(
        cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (50, 40, 401, 63))
    assert tick_xs == [50, 200, 350]
    assert tick_ys == []


def test_fit_axis_retol_resolves_noisy_grid():
    from graphextract.calibration import ScaleType, fit_axis
    from graphextract.schema import AxisRole, TickAnchor

    # Gridline noise of ~3px plus one far misread: the strict pass locks
    # onto a garbage pair and finds no support, while the retry recovers
    # the four consistent ticks.
    anchors = [TickAnchor(3.0, 100.0), TickAnchor(230.0, 30.0),
               TickAnchor(454.0, 80.0), TickAnchor(673.0, 70.0),
               TickAnchor(1124.0, 50.0)]
    fit = fit_axis(anchors, AxisRole.Y_LEFT, "dB", ScaleType.LINEAR)
    assert fit.method == "ransac_pairs+retol"
    assert len(fit.anchors_used) == 4
    assert abs(fit.invert(3.0) - 100.0) < 0.5


def _ramps(n=200):
    us = np.arange(n, dtype=float)
    a = 80.0 + 10.0 * us / n
    b = 70.0 + 5.0 * us / n
    c = 60.0 + 25.0 * np.sin(us / 15.0)  # decoy: unrelated shape
    return us, a, b, c


def test_solve_di_offset_recovers_offset_and_pair():
    us, a, b, c = _ramps()
    left_a, left_b = -12.0, 1170.0
    pix = lambda d: {float(u): left_a * v + left_b for u, v in zip(us, d)}
    di = {float(u): left_a * ((av - bv) + 45.0) + left_b
          for u, av, bv in zip(us, a, b)}
    hit = solve_di_offset(di, [("A", pix(a)), ("B", pix(b)), ("C", pix(c))],
                          left_a, left_b)
    assert hit is not None
    off, (la, lb), iqr, n = hit
    assert (la, lb) == ("A", "B")
    assert off == 45.0
    assert iqr < 1e-9
    assert n == 200


def test_solve_di_offset_rejects_loose_identity():
    # A wobbling residual (IQR ~2dB) is a wrong pair, not an offset.
    us, a, b, c = _ramps()
    left_a, left_b = -12.0, 1170.0
    pix = lambda d: {float(u): left_a * v + left_b for u, v in zip(us, d)}
    di = {float(u): left_a * ((av - bv) + 45.0 + 1.5 * np.sin(u / 10.0)) + left_b
          for u, av, bv in zip(us, a, b)}
    assert solve_di_offset(di, [("A", pix(a)), ("B", pix(b))],
                           left_a, left_b) is None


def test_fit_refit_weights_confidence_over_shaky_outlier():
    # Five solid ticks on pixel = -22*v + 1000 plus one shaky re-read
    # 1.9px off that still lands inside the inlier gate: unweighted least
    # squares would drag the intercept ~0.3px; confidence weighting must
    # hold it within 0.2px of truth.
    anchors = [TickAnchor(-22.0 * v + 1000.0, float(v), 0.9, "ocr")
               for v in (10, 15, 20, 25, 30)]
    anchors.append(TickAnchor(-22.0 * 35 + 1000.0 + 1.9, 35.0, 0.1, "ocr"))
    fit = fit_axis(anchors, AxisRole.Y_LEFT, "dB", ScaleType.LINEAR)
    assert abs(fit.a - -22.0) < 0.02
    assert abs(fit.b - 1000.0) < 0.2
    assert len(fit.anchors_used) == 6


def test_solve_di_offset_needs_points_and_refs():
    us, a, b, _c = _ramps()
    left_a, left_b = -12.0, 1170.0
    pix = lambda d: {float(u): left_a * v + left_b for u, v in zip(us, d)}
    di = {float(u): left_a * ((av - bv) + 45.0) + left_b
          for u, av, bv in zip(us, a, b)}
    assert solve_di_offset(dict(list(di.items())[:9]),
                           [("A", pix(a)), ("B", pix(b))],
                           left_a, left_b) is None
    assert solve_di_offset(di, [("A", pix(a))], left_a, left_b) is None
