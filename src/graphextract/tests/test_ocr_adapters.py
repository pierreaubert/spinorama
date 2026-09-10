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
