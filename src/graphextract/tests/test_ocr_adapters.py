# -*- coding: utf-8 -*-
"""Tests for ocr_adapters.py: association, unit inference, graceful absence."""

import cv2
import numpy as np

from graphextract.calibration import ScaleType
from graphextract.ocr_adapters import (
    OCRWord,
    StubOCR,
    TesseractOCR,
    anchors_from_ocr,
    infer_axis_spec,
    ocr_anchor_provider,
    panel_anchors_from_words,
)


def _grid_image():
    img = np.full((200, 300, 3), 255, np.uint8)
    for x in (30, 150, 270):
        cv2.line(img, (x, 10), (x, 170), (200, 200, 200), 1)
    for y in (20, 90, 160):
        cv2.line(img, (10, y), (290, y), (200, 200, 200), 1)
    return img


def test_ticks_snap_to_grid_not_box_centers():
    img = _grid_image()
    words = [
        OCRWord("20", 20, 176, 20, 14, 0.9),     # bottom strip, near x=30
        OCRWord("1k", 140, 176, 20, 14, 0.9),    # near x=150
        OCRWord("10k", 260, 176, 24, 14, 0.9),   # near x=270
        OCRWord("20", 2, 14, 16, 12, 0.9),       # left strip, near y=20
        OCRWord("60", 2, 84, 16, 12, 0.9),       # near y=90
        OCRWord("100", 0, 154, 20, 12, 0.9),     # near y=160
        OCRWord("mystery", 140, 100, 40, 12, 0.9),  # unparseable, mid-plot
        OCRWord("99999", 210, 176, 30, 14, 0.9),    # 45px from any grid line
    ]
    anchors, unmatched = anchors_from_ocr(words, img)
    assert [t.value for t in anchors.x] == [20.0, 1000.0, 10000.0]
    assert [t.pixel for t in anchors.x] == [30, 150, 270]  # grid, not box center
    assert [t.value for t in anchors.y_left] == [20.0, 60.0, 100.0]
    assert [t.pixel for t in anchors.y_left] == [20, 90, 160]
    assert anchors.x_scale is ScaleType.LOG10 and anchors.x_unit == "Hz"
    assert len(unmatched) == 2


def test_right_strip_ticks_associate_to_y_right():
    """A second (right-hand) y axis calibrates from its margin ticks."""
    img = _grid_image()
    words = [
        OCRWord("20", 2, 14, 16, 12, 0.9),      # left strip -> y_left
        OCRWord("10", 272, 14, 16, 12, 0.9),    # right strip, near y=20
        OCRWord("30", 272, 84, 16, 12, 0.9),    # near y=90
        OCRWord("50", 272, 154, 16, 12, 0.9),   # near y=160
    ]
    anchors, unmatched = anchors_from_ocr(words, img)
    assert [t.value for t in anchors.y_left] == [20.0]
    assert [t.value for t in anchors.y_right] == [10.0, 30.0, 50.0]
    assert [t.pixel for t in anchors.y_right] == [20, 90, 160]
    assert unmatched == []


def test_unit_inference_percent_and_time():
    assert infer_axis_spec([OCRWord("5%", 0, 0, 8, 8)])[2] == "%"
    scale, x_unit, _ = infer_axis_spec([OCRWord("10ms", 0, 0, 8, 8)])
    assert scale is ScaleType.LINEAR and x_unit == "s"
    assert infer_axis_spec([]) == (None, "", "")


def test_unavailable_ocr_degrades_to_review():
    ocr = TesseractOCR()
    ocr.available = False  # simulate a backend without the binary
    provider = ocr_anchor_provider(ocr)
    anchors = provider("p0", _grid_image())
    assert anchors.source == "ocr_unavailable"
    assert anchors.x == [] and anchors.y_left == []


def test_real_tesseract_reads_synthetic_ticks():
    import pytest
    ocr = TesseractOCR()
    if not ocr.available:
        pytest.skip("tesseract backend not installed")
    img = np.full((200, 300, 3), 255, np.uint8)
    for x in (30, 150, 270):
        cv2.line(img, (x, 10), (x, 170), (200, 200, 200), 1)
    for lab, x in (("20", 30), ("1k", 150), ("10k", 270)):
        cv2.putText(img, lab, (x - 14, 192), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 0, 0), 2)
    anchors = ocr_anchor_provider(ocr)("p0", img)
    by_value = {t.value: t.pixel for t in anchors.x}
    assert by_value[20.0] == 30
    assert by_value[10000.0] == 270  # '1k' may misread as 'ak' -> unmatched, not guessed
    assert anchors.x_scale is ScaleType.LOG10


def test_stub_provider_feeds_pipeline():
    ocr = StubOCR([OCRWord("20", 20, 176, 20, 14, 0.9)])
    anchors = ocr_anchor_provider(ocr)("p0", _grid_image())
    assert anchors.source == "ocr_unverified"
    assert len(anchors.x) == 1


def _margin_frame_image():
    """Plot frame with log-decade x grids, linear y grids, and margin labels."""
    img = np.full((300, 500, 3), 255, np.uint8)
    img[40:43, 60:441] = (0, 0, 0)
    img[257:260, 60:441] = (0, 0, 0)
    img[40:260, 60:63] = (0, 0, 0)
    img[40:260, 438:441] = (0, 0, 0)
    for gx in (60, 250, 440):
        img[40:260, gx:gx + 2] = (180, 180, 180)
    for gy in (40, 150, 259):
        img[gy:gy + 2, 60:441] = (180, 180, 180)
    return img


def _margin_frame_words():
    return [
        OCRWord("20", 50, 265, 20, 14, 0.9),
        OCRWord("200", 240, 265, 24, 14, 0.9),
        OCRWord("2000", 425, 265, 30, 14, 0.9),
        OCRWord("0", 44, 33, 14, 14, 0.9),
        OCRWord("50", 28, 143, 18, 14, 0.9),
        OCRWord("100", 24, 250, 26, 14, 0.9),
    ]


def test_panel_anchors_from_margin_words():
    """Margin tick labels (outside the frame) snap to grid geometry in
    interior-local coordinates; bare numbers leave the scale undecided."""
    from graphextract.schema import PanelGeometry

    img = _margin_frame_image()
    panel = PanelGeometry("img#p0", (50, 30, 400, 240), (60, 40, 381, 220), 500, 300)
    interior = img[40:260, 60:441]
    anchors = panel_anchors_from_words(_margin_frame_words(), panel, interior)
    assert [t.value for t in anchors.x] == [20.0, 200.0, 2000.0]
    for tick, expected in zip(anchors.x, (0, 190, 380)):
        assert abs(tick.pixel - expected) <= 2
    assert [t.value for t in anchors.y_left] == [0.0, 50.0, 100.0]
    for tick, expected in zip(anchors.y_left, (0, 110, 219)):
        assert abs(tick.pixel - expected) <= 2
    assert anchors.x_scale is None and anchors.x_unit == ""


def test_paren_unit_names_axes():
    """Axis titles like 'Frequency (Hz)' name units the bare tick numbers
    cannot: the log axis becomes explicit instead of residual-competed."""
    assert infer_axis_spec([OCRWord("(Hz)", 0, 0, 20, 10)]) == (ScaleType.LOG10, "Hz", "")
    assert infer_axis_spec([OCRWord("Frequency (Hz)", 0, 0, 60, 10)])[1] == "Hz"
    assert infer_axis_spec([OCRWord("(dB)", 0, 0, 20, 10)])[2] == "dB"
    assert infer_axis_spec([]) == (None, "", "")
