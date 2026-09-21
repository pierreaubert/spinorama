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
    seed_fallback_styles,
    snap_legend_seeds,
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


def test_wide_label_words_join_beyond_window():
    """Later words of wide high-resolution labels sit past the ±80px window
    yet still belong to the key on their left (PMC10: 'On' + 'Axis')."""
    img = np.full((60, 500, 3), 255, np.uint8)
    cv2.line(img, (10, 20), (70, 20), (0, 0, 255), 3)
    words = [OCRWord("Longword", 120, 13, 80, 13, 0.9),
             OCRWord("Tail", 260, 13, 30, 13, 0.9)]
    res = detect_legend(img, words)
    assert res.has_legend is True
    assert len(res.entries) == 1
    assert res.entries[0].text == "Longword Tail"


def test_wide_highres_line_key_detected():
    """Legend keys on high-resolution renders reach ~95px; the width cap
    must not silently drop them (PMC10 found zero of seven keys)."""
    img = np.full((60, 300, 3), 255, np.uint8)
    cv2.line(img, (10, 20), (104, 20), (0, 0, 255), 4)
    words = [OCRWord("Red", 115, 13, 35, 13, 0.9)]
    res = detect_legend(img, words)
    assert res.has_legend is True
    assert len(res.entries) == 1
    assert res.entries[0].text == "Red"
    assert res.entries[0].swatch_bgr is not None
    assert abs(res.entries[0].swatch_bgr[2] - 255) < 60


def test_line_sample_resolves_core_colour_not_fringe_average():
    """A thin anti-aliased key must resolve to its core ink colour.

    High-resolution legend keys carry light anti-aliased skirts several
    rows wide; the median over all ink pixels lands halfway to white
    (PMC12 On Axis read #57839a for a #23577b stroke), so the tracker's
    own-ink test then fails on the true stroke and the series rides a
    neighbour's ink. The core quartile must stay near the true colour.
    """
    teal = (123, 87, 35)  # BGR #23577b
    img = np.full((60, 200, 3), 255, np.uint8)
    x0, x1 = 10, 70
    core = np.array(teal, dtype=float)
    mixes = {21: 0.25, 22: 0.55, 23: 1.0, 24: 1.0, 25: 1.0, 26: 0.55, 27: 0.25}
    for y, alpha in mixes.items():
        img[y, x0:x1] = tuple(int(255 - alpha * (255 - c)) for c in core)
    words = [OCRWord("Teal", 80, 13, 40, 13, 0.9)]
    res = detect_legend(img, words)
    assert res.has_legend is True
    assert len(res.entries) == 1
    swatch = res.entries[0].swatch_bgr
    assert swatch is not None
    assert all(abs(a - b) < 25 for a, b in zip(swatch, teal, strict=True)), swatch


def test_tall_misread_box_dropped_by_sample_overlap():
    """A tall OCR box blanketing its key ('——' with padded height) covers
    little of its own area yet most of the key: still the key, not a label."""
    img = np.full((60, 200, 3), 255, np.uint8)
    cv2.line(img, (10, 20), (70, 20), (0, 0, 255), 3)
    words = [OCRWord("eee", 8, 8, 64, 30, 0.5)]
    res = detect_legend(img, words)
    assert res.has_legend is False
    assert res.entries == []


def test_dashed_key_fragments_merge_into_one_entry():
    """One dashed legend key detected as per-dash fragments (boxes, a line
    sample, or a mix) yields one entry, not one per dash: unmerged dashes
    split one curve's label across several keys (Devialet green dashes cut
    'Listening Window' into per-dash entries)."""
    img = np.full((80, 500, 3), 255, np.uint8)
    green = (29, 114, 58)
    for x0 in (10, 38, 66):
        cv2.rectangle(img, (x0, 20), (x0 + 16, 27), green, -1)
    cv2.rectangle(img, (94, 20), (133, 27), green, -1)
    words = [OCRWord("Listening", 150, 13, 80, 13, 0.9),
             OCRWord("Window", 240, 13, 60, 13, 0.9)]
    res = detect_legend(img, words)
    assert res.has_legend is True
    assert len(res.entries) == 1
    assert res.entries[0].text == "Listening Window"


def test_later_label_words_stay_on_left_key():
    """A later word nearer the next key still belongs to its own key on the
    left: keys precede labels, so distance must never pull a word onto the
    following entry (Devialet 'Power' drifted from orange onto blue)."""
    img = np.full((80, 500, 3), 255, np.uint8)
    cv2.line(img, (10, 20), (70, 20), (255, 0, 0), 3)
    cv2.line(img, (330, 20), (390, 20), (0, 0, 255), 3)
    words = [OCRWord("Alpha", 85, 13, 50, 13, 0.9),
             OCRWord("Beta", 200, 13, 40, 13, 0.9),
             OCRWord("Gamma", 405, 13, 55, 13, 0.9)]
    res = detect_legend(img, words)
    assert {e.text for e in res.entries} == {"Alpha Beta", "Gamma"}


def test_tick_labels_and_marks_are_not_legend_entries():
    """Axis tick labels pair with nearby tick marks; both must be ignored,
    never counted as curves (Devialet grew a phantom '65' curve from a y
    tick label plus its tick mark)."""
    img = np.full((200, 400, 3), 255, np.uint8)
    cv2.line(img, (10, 20), (67, 20), (0, 0, 255), 3)
    cv2.putText(img, "Woofer", (75, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.line(img, (2, 150), (19, 150), (150, 150, 150), 3)
    words = [OCRWord("Woofer", 75, 13, 60, 13, 0.95),
             OCRWord("65", 2, 144, 16, 12, 0.9)]
    res = detect_legend(img, words)
    assert {e.text for e in res.entries} == {"Woofer"}


def test_gray_dash_fragments_detected_and_merged():
    """Unsaturated short dashes (~19x10, aspect ~1.9) are legend keys too:
    the aspect gate missed them, so an unsaturated dashed curve lost its
    key entirely (Devialet grey 'DI offset' key was invisible)."""
    img = np.full((80, 500, 3), 255, np.uint8)
    gray = (150, 150, 150)
    for x0 in (10, 38, 66, 94):
        cv2.rectangle(img, (x0, 20), (x0 + 18, 29), gray, -1)
    words = [OCRWord("DI", 150, 13, 20, 13, 0.9),
             OCRWord("offset", 180, 13, 45, 13, 0.9)]
    res = detect_legend(img, words)
    assert len(res.entries) == 1
    assert res.entries[0].text == "DI offset"


def test_word_overlapping_next_key_stays_on_left_key():
    """A label word printed over the next entry's key (crowded legend row)
    belongs to the key on its left: a word never prints on top of its own
    key, so overlap disqualifies the key (Devialet 'Dl' sat on the grey key
    yet belongs to the blue 'Early Reflections DI' label)."""
    img = np.full((80, 500, 3), 255, np.uint8)
    cv2.line(img, (10, 30), (70, 30), (255, 0, 0), 3)
    cv2.rectangle(img, (100, 30), (199, 37), (150, 150, 150), -1)
    words = [OCRWord("Early", 80, 23, 50, 13, 0.9),
             OCRWord("Dl", 150, 23, 21, 13, 0.9),
             OCRWord("DI", 210, 23, 20, 13, 0.9),
             OCRWord("offset", 235, 23, 45, 13, 0.9)]
    res = detect_legend(img, words)
    assert {e.text for e in res.entries} == {"Early Dl", "DI offset"}


def test_interword_dash_does_not_become_legend_entry():
    """A dash between title words ('CEA2034 -- TOPPING') is punctuation,
    not a legend key: its paired words span both its sides, while real
    keys lead their labels on one side only."""
    img = np.full((120, 500, 3), 255, np.uint8)
    cv2.rectangle(img, (200, 20), (223, 24), (150, 150, 150), -1)  # title dash
    cv2.line(img, (10, 60), (70, 60), (0, 0, 255), 3)  # real red key
    words = [OCRWord("CEA2034", 100, 13, 80, 15, 0.9),
             OCRWord("--", 200, 15, 22, 8, 0.9),
             OCRWord("TOPPING", 230, 13, 90, 15, 0.9),
             OCRWord("On", 80, 53, 25, 13, 0.9),
             OCRWord("Axis", 110, 53, 40, 13, 0.9)]
    res = detect_legend(img, words)
    assert {e.text for e in res.entries} == {"On Axis"}


def test_wide_solid_bar_keys_detected():
    """Wide solid bars (~130x24, saturated or dark) key legend items: the
    size caps admit them while frame strokes stay excluded."""
    img = np.full((120, 500, 3), 255, np.uint8)
    cv2.rectangle(img, (10, 10), (139, 33), (32, 47, 214), -1)  # red bar
    cv2.rectangle(img, (10, 50), (139, 73), (20, 20, 20), -1)  # dark bar
    words = [OCRWord("Early", 150, 12, 50, 16, 0.9),
             OCRWord("On", 150, 52, 25, 16, 0.9),
             OCRWord("Axis", 180, 52, 40, 16, 0.9)]
    res = detect_legend(img, words)
    assert res.has_legend
    by_text = {e.text: e for e in res.entries}
    assert by_text["Early"].swatch_bgr[2] > 150  # red bar kept
    assert max(by_text["On Axis"].swatch_bgr) < 100  # dark bar kept


def test_seed_fallback_styles_finds_dark_curve_not_grid_dots():
    """Legend-free seeding recovers an unsaturated black sine curve while
    refusing evenly scattered grey dotted-grid dots."""
    img = np.full((300, 600, 3), 255, np.uint8)
    for y in range(20, 300, 40):  # dotted grey grid
        for x in range(10, 600, 25):
            img[y, x] = (170, 170, 170)
    xs = np.arange(10, 590)
    for xx in xs[::3]:  # black sine curve, 2px
        yy = int(150 + 80 * np.sin(xx / 40.0))
        img[yy, xx] = (10, 10, 10)
        img[yy + 1, xx] = (10, 10, 10)
    for xx in xs[::3]:  # red sine curve, 2px
        yy = int(150 + 80 * np.cos(xx / 40.0))
        img[yy, xx] = (30, 30, 220)
        img[yy + 1, xx] = (30, 30, 220)
    seeds = seed_fallback_styles(img, [], limit=8)
    assert seeds, "expected curve seeds on a legend-free plot"
    assert all(s.series_id.startswith("curve_") for s in seeds)
    assert any(max(s.bgr) < 90 for s in seeds), "black curve must seed"
    assert any(s.bgr[2] > 150 for s in seeds), "red curve must seed"
    assert not any(120 <= min(s.bgr) <= 200 and max(s.bgr) - min(s.bgr) < 40
                   for s in seeds), "grey grid dots must not seed"


def test_snap_legend_seeds_repoints_starved_only():
    """A legend seed with no interior ink snaps to the vetted curve
    colour; seeds with their own ink stay untouched."""
    img = np.full((200, 400, 3), 255, np.uint8)
    xs = np.arange(10, 390)
    for xx in xs[::2]:  # dark-navy sine curve for a black key
        yy = int(100 + 50 * np.sin(xx / 30.0))
        img[yy, xx] = (90, 60, 30)
        img[yy + 1, xx] = (90, 60, 30)
    for xx in xs:  # green sine curve, already keyed correctly
        yy = int(100 + 50 * np.cos(xx / 30.0))
        img[yy, xx] = (30, 120, 60)
        img[yy + 1, xx] = (30, 120, 60)
        img[yy + 2, xx] = (30, 120, 60)
    styles = [StyleSpec("legend_1", "On Axis", (0, 0, 0)),
              StyleSpec("legend_2", "Listening Window", (30, 120, 60))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr != (0, 0, 0)  # starved: snapped to navy
    assert by_id["legend_1"].label == "On Axis"
    assert by_id["legend_2"].bgr == (30, 120, 60)  # own ink: untouched
