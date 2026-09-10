# -*- coding: utf-8 -*-
"""Tests for semantics.py: swatch pairing, color association, VLM validation."""

import cv2
import numpy as np

from graphextract.evidence import StyleSpec
from graphextract.ocr_adapters import OCRWord
from graphextract.semantics import (
    StubVLM,
    apply_vlm_labels,
    associate_by_color,
    detect_legend,
    extract_legend_entries,
    styles_from_legend,
    validate_proposal,
)


def _legend_image():
    img = np.full((120, 400, 3), 255, np.uint8)
    cv2.rectangle(img, (10, 10), (24, 24), (0, 0, 255), -1)
    cv2.putText(img, "Woofer", (30, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.rectangle(img, (150, 10), (164, 24), (255, 0, 0), -1)
    cv2.putText(img, "Tweeter", (170, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    words = [OCRWord("Woofer", 30, 12, 60, 13, 0.95),
             OCRWord("Tweeter", 170, 12, 62, 13, 0.95)]
    return img, words


def test_entries_pair_words_with_swatches():
    img, words = _legend_image()
    entries = extract_legend_entries(img, words)
    assert {e.text for e in entries} == {"Woofer", "Tweeter"}
    by_text = {e.text: e for e in entries}
    assert by_text["Woofer"].swatch_bgr is not None
    assert by_text["Tweeter"].swatch_bgr is not None
    assert abs(by_text["Woofer"].swatch_bgr[2] - 255) < 60  # red swatch
    assert abs(by_text["Tweeter"].swatch_bgr[0] - 255) < 60  # blue swatch


def test_color_association_and_anonymous_fallback():
    img, words = _legend_image()
    entries = extract_legend_entries(img, words)
    styles = [StyleSpec("s0", "?", (0, 0, 255)), StyleSpec("s1", "?", (0, 140, 0))]
    assocs = associate_by_color(entries, styles)
    by_id = {a.series_id: a for a in assocs}
    assert by_id["s0"].label == "Woofer" and by_id["s0"].source == "color"
    assert by_id["s1"].label is None and by_id["s1"].source == "none"


def test_vlm_proposals_validated_and_fill_anonymous_only():
    series = ["s0", "s1"]
    assocs = associate_by_color(
        extract_legend_entries(*_legend_image()),
        [StyleSpec("s0", "?", (0, 0, 255)), StyleSpec("s1", "?", (0, 140, 0))])
    good = {"labels": {"s1": "Tweeter"}, "units": {"x": "Hz"}, "family": "unknown"}
    assert validate_proposal(good, series, ["Woofer", "Tweeter"]) == []
    assert apply_vlm_labels(assocs, good, series, ["Woofer", "Tweeter"]) == []
    by_id = {a.series_id: a for a in assocs}
    assert by_id["s1"].label == "Tweeter" and by_id["s1"].source == "vlm"
    assert by_id["s0"].label == "Woofer" and by_id["s0"].source == "color"
    bad = {"labels": {"s9": "Ghost", "s1": "Invented"}, "units": {"x": "furlong"},
           "family": "mystery"}
    errs = validate_proposal(bad, series, ["Woofer", "Tweeter"])
    assert len(errs) == 5  # unknown series, 2 invented labels, unit, family
    before = (by_id["s1"].label, by_id["s1"].source)
    assert apply_vlm_labels(assocs, bad, series, ["Woofer", "Tweeter"]) != []
    assert (by_id["s1"].label, by_id["s1"].source) == before  # rejected: untouched
    assert StubVLM(good).propose(np.zeros((4, 4, 3), np.uint8), {}) == good


def _line_legend_image():
    """Legend with horizontal line samples (the common real-world style).

    Includes unsaturated black/gray samples that a saturation-only swatch
    detector misses, and an OCR misread of one line sample ('mum').
    """
    img = np.full((120, 460, 3), 255, np.uint8)
    # red line sample + label
    cv2.line(img, (10, 20), (67, 20), (0, 0, 255), 3)
    cv2.putText(img, "Woofer", (75, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    # black line sample + two-word label
    cv2.line(img, (190, 20), (247, 20), (0, 0, 0), 3)
    cv2.putText(img, "2nd", (255, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Harmonic", (290, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    # gray line sample + label
    cv2.line(img, (10, 50), (67, 50), (192, 192, 192), 3)
    cv2.putText(img, "Noise", (75, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    words = [OCRWord("Woofer", 75, 13, 60, 13, 0.95),
             OCRWord("mum", 10, 17, 57, 6, 0.50),  # OCR misread of the red sample
             OCRWord("2nd", 255, 13, 25, 13, 0.9),
             OCRWord("Harmonic", 290, 13, 67, 13, 0.94),
             OCRWord("Noise", 75, 43, 50, 13, 0.9)]
    return img, words


def test_detect_legend_absent_on_plain_plot():
    img = np.full((200, 300, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (280, 180), (180, 180, 180), 1)
    res = detect_legend(img, [])
    assert res.has_legend is False
    assert res.entries == []
    assert res.bbox_xywh is None


def test_detect_legend_box_swatches_count_and_colors():
    img, words = _legend_image()
    res = detect_legend(img, words)
    assert res.has_legend is True
    assert len(res.entries) == 2  # number of curves
    by_text = {e.text: e for e in res.entries}
    assert set(by_text) == {"Woofer", "Tweeter"}
    assert by_text["Woofer"].swatch_bgr is not None
    assert by_text["Tweeter"].swatch_bgr is not None
    assert abs(by_text["Woofer"].swatch_bgr[2] - 255) < 60
    assert abs(by_text["Tweeter"].swatch_bgr[0] - 255) < 60
    assert res.bbox_xywh is not None
    x, y, w, h = res.bbox_xywh
    assert x <= 10 and y <= 12 and x + w >= 232 and y + h >= 25


def test_detect_legend_line_samples_with_multiword_labels():
    img, words = _line_legend_image()
    res = detect_legend(img, words)
    assert res.has_legend is True
    assert len(res.entries) == 3
    by_text = {e.text: e for e in res.entries}
    assert set(by_text) == {"Woofer", "2nd Harmonic", "Noise"}
    assert by_text["Woofer"].kind == "line"
    # unsaturated black / gray samples still resolve to their curve colour
    black = by_text["2nd Harmonic"].swatch_bgr
    gray = by_text["Noise"].swatch_bgr
    assert black is not None and gray is not None
    assert max(black) < 80, black
    assert 120 < sum(gray) / 3 < 230, gray


def test_detect_legend_ignores_ocr_misread_of_swatch():
    img, words = _line_legend_image()
    res = detect_legend(img, words)
    assert "mum" not in {e.text for e in res.entries}
    entries = extract_legend_entries(img, words)
    assert "mum" not in {e.text for e in entries}


def test_extract_legend_entries_pairs_line_samples():
    img, words = _line_legend_image()
    entries = extract_legend_entries(img, words)
    by_text = {e.text: e for e in entries}
    assert by_text["Woofer"].swatch_bgr is not None
    assert abs(by_text["Woofer"].swatch_bgr[2] - 255) < 60
    assert by_text["Woofer"].kind == "line"


def test_styles_from_legend_gives_count_and_colors():
    img, words = _line_legend_image()
    res = detect_legend(img, words)
    styles = styles_from_legend(res)
    assert len(styles) == 3
    assert [s.label for s in styles] == [e.text for e in res.entries]
    bgrs = [tuple(s.bgr) for s in styles]
    assert any(b[2] > 200 and b[0] < 80 and b[1] < 80 for b in bgrs)  # red curve
    assert any(max(b) < 80 for b in bgrs)  # black curve
