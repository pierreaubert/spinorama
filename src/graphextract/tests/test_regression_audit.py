# -*- coding: utf-8 -*-
"""Regression tests for the four failures reproduced in research/audit_*.

Each test fails on the legacy implementation path and passes on the canonical
pipeline. Legacy files are intentionally left unchanged as the baseline.
"""

import numpy as np

from graphextract.calibration import detect_grid_lines, unpack_hough_lines
from graphextract.evaluate import score_series
from graphextract.evidence import StyleSpec, segment_evidence
from graphextract.tracking import TrackConfig, track_panel

from tests.helpers import gray_of


def test_hough_unpack_accepts_both_opencv_layouts():
    """Audit failure 1: grid detection crashed on one HoughLinesP layout."""
    as_n14 = np.array([[[10, 0, 10, 50]], [[0, 20, 80, 20]]], dtype=np.int32)
    as_n4 = np.array([[10, 0, 10, 50], [0, 20, 80, 20]], dtype=np.int32)
    assert unpack_hough_lines(as_n14) == [(10, 0, 10, 50), (0, 20, 80, 20)]
    assert unpack_hough_lines(as_n4) == [(10, 0, 10, 50), (0, 20, 80, 20)]
    assert unpack_hough_lines(None) == []


def test_grid_detection_runs_on_realistic_grid():
    """detect_grid_lines must not raise and must find frame/grid lines."""
    img = np.full((200, 300, 3), 255, np.uint8)
    for x in (20, 150, 280):
        img[:, x - 1:x + 2] = (200, 200, 200)
    for y in (15, 100, 185):
        img[y - 1:y + 2, :] = (200, 200, 200)
    vx, hy = detect_grid_lines(img)
    assert len(vx) >= 2 and len(hy) >= 2


def test_one_pixel_line_survives_segmentation():
    """Audit failure 2: a 1px, 180-pixel line produced zero segmented pixels."""
    img = np.full((120, 200, 3), 255, np.uint8)
    img[50, 10:190] = (0, 0, 255)
    layers = segment_evidence(img, [StyleSpec("red", "red", (0, 0, 255))])
    assert "red" in layers.curve_masks
    assert int(np.count_nonzero(layers.curve_masks["red"])) == 180


def test_no_unconditional_smoothing_shift():
    """Audit failure 3: a 5px excursion was shifted 2.57px by forced smoothing."""
    mask = np.zeros((120, 200), np.uint8)
    mask[50, :] = 255
    mask[50, 100] = 0
    mask[45, 100] = 255
    gray = np.full((120, 200), 255, np.uint8)
    gray[mask > 0] = 0
    from graphextract.evidence import EvidenceLayers

    layers = EvidenceLayers(curve_masks={"s": mask},
                            grid_mask=np.zeros((120, 200), np.uint8),
                            background_bgr=(255, 255, 255))
    tracks = track_panel(gray, layers, ["s"], 255.0, TrackConfig())
    seq = tracks["s"].samples
    assert seq[100].status.value == "observed"
    assert abs(seq[100].v - 45.0) <= 0.5
    flats = [s.v for i, s in enumerate(seq) if i != 100 and s.status.value == "observed"]
    assert all(abs(v - 50.0) <= 0.5 for v in flats)


def test_gaps_are_not_interpolated_away_for_scoring():
    """Audit failure 4: two endpoints scored RMS 0 / coverage 1 over a void."""
    gt_x = np.geomspace(20, 20000, 1000)
    gt_y = np.full(1000, 80.0)
    ref_visible = np.ones(1000, dtype=bool)
    score = score_series(
        pred_u=[20.0, 20000.0], pred_v=[80.0, 80.0], pred_observed=[True, True],
        ref_u=gt_x, ref_v=gt_y, ref_visible=ref_visible, series_id="flat",
    )
    assert not score.strict_pass
    assert score.measured_coverage < 0.01
    assert score.n_ref_visible == 1000
