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
    refine_seed_templates,
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


def _paint_curve(img, paint, y0=100, amp=40, step=1, thick=2):
    xs = np.arange(10, img.shape[1] - 10, step)
    for xx in xs:
        yy = int(y0 + amp * np.sin(xx / 30.0))
        for t in range(thick):
            img[yy + t, xx] = paint
    return int(len(xs) * thick)


def test_refine_seed_templates_adopts_paint_median():
    """An off-swatch seed with solid core ink re-points at the measured
    paint median, so unmixing scores truth near zero."""
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (36, 46, 182))
    styles = [StyleSpec("legend_1", "Early Reflections", (32, 47, 214))]
    fixed = refine_seed_templates(img, styles)
    assert fixed[0].bgr == (36, 46, 182)
    assert fixed[0].label == "Early Reflections"


def test_refine_seed_templates_keeps_mixed_box():
    """Two core-grade paints inside one tolerance box keep the key: the
    median of a mixture is neither paint."""
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (80, 70, 145), y0=60, amp=10)
    _paint_curve(img, (135, 120, 105), y0=140, amp=10)
    styles = [StyleSpec("legend_1", "Early Reflections", (110, 100, 120))]
    fixed = refine_seed_templates(img, styles)
    assert fixed[0].bgr == (110, 100, 120)


def test_refine_seed_templates_keeps_starved_and_discovered():
    """Starved seeds and discovered curve_ seeds pass through untouched."""
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (36, 46, 182), step=40, thick=1)  # sparse: starved
    styles = [StyleSpec("legend_1", "Early Reflections", (32, 47, 214)),
              StyleSpec("curve_2", "curve_2", (36, 46, 182))]
    fixed = refine_seed_templates(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (32, 47, 214)
    assert by_id["curve_2"].bgr == (36, 46, 182)


def _entry(text, xywh, kind="line", bgr=(10, 10, 10)):
    from graphextract.semantics import LegendEntry
    return LegendEntry(text=text, word_xywh=xywh, swatch_bgr=bgr,
                       swatch_xywh=xywh, kind=kind)


def test_misshapen_line_keys_drop_square_blobs():
    from graphextract.semantics import _drop_misshapen_line_keys
    # Neumann margin shape: rotated-title glyph fragments pair words with
    # near-square grey blobs; true dashes are wide and thin.
    thin = _entry("On Axis", (174, 98, 130, 10))
    short = _entry("On-axis", (1579, 514, 7, 3))
    blob = _entry("ee", (47, 784, 32, 20))
    shard = _entry("Pessure", (99, 949, 48, 28))
    box = _entry("Woofer", (10, 10, 14, 14), kind="box")
    assert _drop_misshapen_line_keys([thin, short, blob, shard, box]) == [
        thin, short, box]


def test_misshapen_line_keys_rescue_icons():
    from graphextract.semantics import _drop_misshapen_line_keys
    # Harman-BW shape: icon-style keys are squarish but big and lead
    # full-phrase labels.
    icon = _entry("54: Total Sound Power", (560, 1551, 72, 57))
    assert _drop_misshapen_line_keys([icon]) == [icon]


def test_incoherent_keys_drop_unaligned_outlier():
    from graphextract.semantics import _drop_incoherent_keys
    # PMC shape: seven keys share one row band; the axis-title pairing a
    # thousand pixels below shares neither row nor column.
    row = [_entry(f"c{i}", (400 + i * 300, 171, 94, 9)) for i in range(7)]
    outlier = _entry("Amplitude", (83, 1228, 35, 6))
    assert _drop_incoherent_keys(row + [outlier]) == row
    # Sovox shape: a vertical stack shares one column band.
    stack = [_entry(f"c{i}", (1580, 418 + i * 32, 16, 3)) for i in range(7)]
    assert _drop_incoherent_keys(stack) == stack
    # Pairs and singletons cannot show incoherence.
    assert _drop_incoherent_keys(row[:2]) == row[:2]


def test_styles_from_legend_carries_key_boxes():
    img, words = _legend_image()
    entries = extract_legend_entries(img, words)
    styles = styles_from_legend(entries)
    assert len(styles) == 2
    for style in styles:
        assert style.key_xywh is not None
        x, y, w, h = style.key_xywh
        assert w > 0 and h > 0


def test_misshapen_line_keys_rescue_grid_short_labels():
    from graphextract.semantics import _drop_misshapen_line_keys
    # Icon legend grid: short-label keys on kept row+column junctions are
    # real entries; off-grid short labels and shards stay dropped.
    row = [_entry("54: Total Sound Power", (560, 1551, 72, 57)),
           _entry("57: Predicted In Room", (1230, 1551, 73, 57)),
           _entry("53: First Reflections", (18, 1692, 72, 58))]
    short = _entry("51: On Axis", (18, 1551, 72, 57))
    offgrid = _entry("52: Glass", (900, 1300, 72, 57))
    shard = _entry("os", (18, 1621, 72, 57))
    assert _drop_misshapen_line_keys(row + [short, offgrid, shard]) == row + [short]


def test_zigzag_samples_read_stroke_not_dark_frame():
    import cv2
    import numpy as np
    from graphextract.ocr_adapters import OCRWord
    from graphextract.semantics import _zigzag_samples
    img = np.full((200, 400, 3), 255, np.uint8)
    # Dark L frame with a red zigzag stroke inside (Harman-BW icons).
    cv2.line(img, (20, 100), (20, 150), (40, 40, 40), 2)
    cv2.line(img, (20, 100), (90, 100), (40, 40, 40), 2)
    pts = np.array([[20, 138], [38, 116], [52, 138], [66, 116], [80, 138]])
    cv2.polylines(img, [pts], False, (30, 30, 220), 2)
    words = [OCRWord("Stroke", 110, 112, 90, 26, 0.9)]
    samples = _zigzag_samples(img, words)
    assert len(samples) == 1
    b, g, r = samples[0].bgr
    assert r > b + 40 and r > g + 40, samples[0].bgr  # red stroke, not frame
    # Unsaturated zigzag keeps the legacy darkest-quartile colour.
    img2 = np.full((200, 400, 3), 255, np.uint8)
    cv2.line(img2, (20, 100), (20, 150), (200, 200, 200), 2)
    cv2.line(img2, (20, 100), (90, 100), (200, 200, 200), 2)
    cv2.polylines(img2, [pts], False, (60, 60, 60), 2)
    samples2 = _zigzag_samples(img2, words)
    assert len(samples2) == 1
    assert max(samples2[0].bgr) < 110, samples2[0].bgr


def test_zigzag_samples_survive_overlapping_misreads():
    import cv2
    import numpy as np
    from graphextract.ocr_adapters import OCRWord
    from graphextract.semantics import _zigzag_samples
    img = np.full((200, 400, 3), 255, np.uint8)
    cv2.line(img, (20, 100), (20, 150), (40, 40, 40), 2)
    cv2.line(img, (20, 100), (90, 100), (40, 40, 40), 2)
    pts = np.array([[20, 138], [38, 116], [52, 138], [66, 116], [80, 138]])
    cv2.polylines(img, [pts], False, (30, 30, 220), 2)
    label = [OCRWord("Stroke", 110, 112, 90, 26, 0.9)]
    # Two overlapping icon-fragment misreads are one cluster: the key stays.
    misreads = [OCRWord("ly", 19, 102, 71, 50, 0.59),
                OCRWord("x51:", 19, 101, 100, 51, 0.23)]
    assert len(_zigzag_samples(img, label + misreads)) == 1
    # Two disjoint touching words are a text run: the key goes.
    run = [OCRWord("Total", 30, 80, 40, 25, 0.9),
           OCRWord("Power", 30, 148, 40, 25, 0.9)]
    assert _zigzag_samples(img, run) == []


def test_snap_wall_to_wall_grid_never_backs():
    import numpy as np
    from graphextract.evidence import StyleSpec
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    # Dark solid gridlines, hue B: measured furniture rows exclude them
    # with or without the mask, and the hue rule keeps the R seed from
    # adopting their pool colour.
    img[50:150:4, 10:390] = (140, 110, 120)
    _paint_curve(img, (60, 40, 120))
    grid = np.zeros((200, 400), np.uint8)
    grid[50:150:4, 10:390] = 255
    styles = [StyleSpec("legend_1", "Early Reflections", (140, 130, 150))]
    kept = snap_legend_seeds(img, styles)
    # Wall-to-wall gridlines are measured furniture rows, never backing
    assert kept[0].bgr != (140, 130, 150)
    fixed = snap_legend_seeds(img, styles, exclude_mask=grid)
    assert fixed[0].bgr != (140, 130, 150)  # starved: snapped to paint
    assert fixed[0].bgr[2] > fixed[0].bgr[0] + 30
    assert fixed[0].bgr[2] > fixed[0].bgr[1] + 30


def test_refine_excludes_grid_from_median():
    import numpy as np
    from graphextract.evidence import StyleSpec
    from graphextract.semantics import refine_seed_templates
    img = np.full((200, 400, 3), 255, np.uint8)
    img[50:150:4, 10:390] = (140, 110, 120)
    _paint_curve(img, (125, 105, 140))
    grid = np.zeros((200, 400), np.uint8)
    grid[50:150:4, 10:390] = 255
    styles = [StyleSpec("legend_1", "Window", (140, 130, 150))]
    dragged = refine_seed_templates(img, styles)
    assert dragged[0].bgr == (140, 110, 120)  # grid outvotes the paint
    paint = refine_seed_templates(img, styles, exclude_mask=grid)
    assert paint[0].bgr == (125, 105, 140)  # masked grid never votes


def test_seed_support_rejects_edge_hugging_furniture():
    import numpy as np
    from graphextract.evidence import StyleSpec
    from graphextract.semantics import refine_seed_templates, snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    # Margin bars both edges: connected, unimodal, numerous, spanning
    # the width yet concentrated in the edge bins.
    img[:, 388:400] = (132, 118, 128)
    img[:, 0:6] = (132, 118, 128)
    _paint_curve(img, (30, 30, 220))
    styles = [StyleSpec("legend_1", "Total Sound Power", (105, 89, 96))]
    fixed = snap_legend_seeds(img, styles)
    assert fixed[0].bgr != (105, 89, 96)  # starved despite the bars
    kept = refine_seed_templates(img, styles)
    assert kept[0].bgr == (105, 89, 96)  # furniture never votes


def test_seed_backing_ignores_achromatic_dots():
    import numpy as np
    from graphextract.evidence import StyleSpec
    from graphextract.semantics import refine_seed_templates, snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    # Achromatic dotted grid spanning the plot: no mask, yet a chromatic
    # seed finds no backing in it.
    img[50:150:4, 10:390:4] = (150, 150, 150)
    _paint_curve(img, (30, 30, 220))
    styles = [StyleSpec("legend_1", "Early Reflections", (150, 150, 200))]
    fixed = snap_legend_seeds(img, styles)
    assert fixed[0].bgr[2] > fixed[0].bgr[0] + 40  # snapped to red
    assert fixed[0].bgr[2] > fixed[0].bgr[1] + 40
    kept = refine_seed_templates(img, styles)
    assert kept[0].bgr == (150, 150, 200)  # dots never vote


def test_snap_shares_pool_among_same_paint_siblings():
    import numpy as np
    from graphextract.evidence import StyleSpec
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (30, 30, 220))
    # Two washed red keys over one red curve: both adopt the pool red.
    styles = [StyleSpec("legend_1", "On Axis", (112, 113, 142)),
              StyleSpec("legend_2", "First Reflections", (109, 113, 137))]
    fixed = snap_legend_seeds(img, styles)
    assert fixed[0].bgr == fixed[1].bgr
    assert fixed[0].bgr[2] > fixed[0].bgr[0] + 40


def test_snap_recovers_dot_grid_fragmented_paint():
    import numpy as np
    from graphextract.evidence import StyleSpec
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (36, 46, 182))
    # dotted-grid punches shred the stroke below any connectivity floor
    for xx in range(10, 390, 9):
        img[55:145, xx] = (255, 255, 255)
    styles = [StyleSpec("legend_1", "Early Reflections", (112, 113, 142))]
    fixed = snap_legend_seeds(img, styles)
    assert fixed[0].bgr != (112, 113, 142)  # starved: pool core adopted
    assert fixed[0].bgr[2] > fixed[0].bgr[0] + 40
    assert fixed[0].bgr[2] > fixed[0].bgr[1] + 40


def test_snap_keeps_curve_seed_amid_glyph_clutter():
    """A spanning stroke backs its seed whatever clutter shares the box:
    legend glyphs and a connected frame web inside the plot must not
    starve it into adopting a foreign pool colour."""
    from graphextract.semantics import snap_legend_seeds
    rng = np.random.default_rng(7)
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (10, 10, 10))
    img[0:2, :] = (10, 10, 10)  # connected frame web (all sides)
    img[-2:, :] = (10, 10, 10)
    img[:, 0:2] = (10, 10, 10)
    img[:, -2:] = (10, 10, 10)
    for _ in range(45):  # scattered glyph-like blobs across the plot
        x, y = int(rng.integers(4, 390)), int(rng.integers(4, 186))
        img[y:y + 8, x:x + 3] = (10, 10, 10)
    styles = [StyleSpec("legend_1", "On Axis", (0, 0, 0))]
    fixed = snap_legend_seeds(img, styles)
    assert fixed[0].bgr == (0, 0, 0)


def test_seed_curve_backed_rejects_halo_sheath_and_frame():
    """A pale fringe sheath hugging a darker curve spans and counts
    like paint but is all complement-adjacent and paler than the
    hugged core, so it never backs; the hugged curve itself backs.
    Frame furniture never backs either."""
    from graphextract.semantics import (_core_voters, _ink_fraction,
                                        _measure_frame_mask,
                                        _seed_curve_backed)
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (140, 20, 20))
    for xx in range(10, 390):  # mid-pale sheath hugging the dark stroke
        yy = int(100 + 40 * np.sin(xx / 30.0))
        img[yy - 1, xx] = (170, 100, 100)
        img[yy + 2, xx] = (170, 100, 100)
    px = img.astype(int)
    bg = np.full(3, 255.0)
    dark = _ink_fraction(img, bg)
    ink = dark >= 0.5
    frame = _measure_frame_mask(ink)
    pale = (np.max(np.abs(px - np.array((170, 100, 100))), axis=2) <= 40) & ink
    assert int(pale.sum()) > 300  # the sheath itself reaches the count floor
    pale_v = _core_voters(img.astype(float), bg,
                          np.array((170, 100, 100), dtype=float), pale)
    core = (np.max(np.abs(px - np.array((140, 20, 20))), axis=2) <= 40) & ink
    core_v = _core_voters(img.astype(float), bg,
                          np.array((140, 20, 20), dtype=float), core)
    assert not _seed_curve_backed(pale_v, pale, ink, dark, frame,
                                  400, 200, 300)
    assert _seed_curve_backed(core_v, core, ink, dark, frame,
                              400, 200, 300)
    img2 = np.full((200, 400, 3), 255, np.uint8)
    img2[0:2, :] = (10, 10, 10)
    img2[-2:, :] = (10, 10, 10)
    img2[:, 0:2] = (10, 10, 10)
    img2[:, -2:] = (10, 10, 10)
    dark2 = _ink_fraction(img2, bg)
    ink2 = dark2 >= 0.5
    frame2 = _measure_frame_mask(ink2)
    frame_v = _core_voters(img2.astype(float), bg,
                           np.array((10, 10, 10), dtype=float), ink2)
    assert not _seed_curve_backed(frame_v, ink2, ink2, dark2, frame2,
                                  400, 200, 300)


def test_seed_curve_backed_backs_dashes_rejects_dots():
    """Long wandering dashes back a seed through the fallback (no one
    component spans), while dotted-grid dots never reach the dash run
    floor and flat rulers never reach the row-span floor."""
    from graphextract.semantics import (_core_voters, _ink_fraction,
                                        _measure_frame_mask,
                                        _seed_curve_backed)
    bg = np.full(3, 255.0)
    img = np.full((200, 400, 3), 255, np.uint8)
    for i, x0 in enumerate(range(10, 390, 30)):  # wandering 20px dashes
        yy = int(100 + 30 * np.sin(i / 2.0))
        img[yy:yy + 2, x0:x0 + 20] = (113, 113, 113)
    px = img.astype(int)
    dark = _ink_fraction(img, bg)
    ink = dark >= 0.5
    frame = _measure_frame_mask(ink)
    dash = (np.max(np.abs(px - np.array((113, 113, 113))), axis=2) <= 40) & ink
    dash_v = _core_voters(img.astype(float), bg,
                          np.array((113, 113, 113), dtype=float), dash)
    assert _seed_curve_backed(dash_v, dash, ink, dark, frame,
                              400, 200, 300)
    img3 = np.full((200, 400, 3), 255, np.uint8)
    for x0 in range(10, 390, 30):  # flat ruler dashes
        img3[100:102, x0:x0 + 20] = (113, 113, 113)
    px3 = img3.astype(int)
    dark3 = _ink_fraction(img3, bg)
    ink3 = dark3 >= 0.5
    frame3 = _measure_frame_mask(ink3)
    ruler = ((np.max(np.abs(px3 - np.array((113, 113, 113))),
                     axis=2) <= 40) & ink3)
    ruler_v = _core_voters(img3.astype(float), bg,
                           np.array((113, 113, 113), dtype=float), ruler)
    assert int(ruler_v.sum()) > 300  # rulers reach the count floor
    assert not _seed_curve_backed(ruler_v, ruler, ink3, dark3, frame3,
                                  400, 200, 300)
    img2 = np.full((200, 400, 3), 255, np.uint8)
    for y in range(10, 190, 20):  # 3px dark dotted grid
        for x in range(10, 390, 20):
            img2[y:y + 3, x:x + 3] = (100, 100, 100)
    px2 = img2.astype(int)
    dark2 = _ink_fraction(img2, bg)
    ink2 = dark2 >= 0.5
    frame2 = _measure_frame_mask(ink2)
    dots = (np.max(np.abs(px2 - np.array((100, 100, 100))), axis=2) <= 40) & ink2
    assert int(dots.sum()) > 300  # the dots reach the count floor
    dots_v = _core_voters(img2.astype(float), bg,
                          np.array((100, 100, 100), dtype=float), dots)
    assert not _seed_curve_backed(dots_v, dots, ink2, dark2, frame2,
                                  400, 200, 300)


def test_core_voters_excludes_off_direction_ink():
    """Paint-strength voters exclude fringe and foreign paint caught in
    a washed box: only full-strength ink along the seed direction
    votes, so fringe boxes starve into adoption."""
    from graphextract.semantics import _core_voters
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (40, 0, 244))
    for xx in range(10, 390):  # pale fringe hugging the red stroke
        yy = int(100 + 40 * np.sin(xx / 30.0))
        img[yy - 1, xx] = (200, 170, 220)
        img[yy + 2, xx] = (200, 170, 220)
    bg = np.full(3, 255.0)
    px = img.astype(int)
    grey_box = ((np.max(np.abs(px - np.array((140, 140, 140))),
                        axis=2) <= 60))
    voters = _core_voters(img.astype(float), bg,
                          np.array((140, 140, 140), dtype=float),
                          grey_box)
    assert int(voters.sum()) < 300  # fringe never reaches the floor
    red_box = ((np.max(np.abs(px - np.array((40, 0, 244))),
                       axis=2) <= 40))
    red_voters = _core_voters(img.astype(float), bg,
                              np.array((40, 0, 244), dtype=float),
                              red_box)
    assert int(red_voters.sum()) >= 300  # the paint itself votes


def test_snap_starved_key_adopts_same_hue_backed_sibling():
    """A washed key starved of its own ink adopts its backed same-hue
    sibling's paint: the key is a washed sample of that family's paint,
    and fencing plus the same-paint swap sort out the assignment."""
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (40, 0, 244))
    styles = [StyleSpec("legend_1", "Early Reflections", (41, 0, 244)),
              StyleSpec("legend_2", "Early Reflections DI", (32, 0, 189))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (41, 0, 244)
    assert by_id["legend_2"].bgr == (41, 0, 244)


def test_snap_sibling_prefers_labelled_over_textless():
    """A nearer textless sibling (a positional guess, often fringe)
    must not veto a farther labelled same-hue sibling's paint."""
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (200, 40, 40))
    styles = [StyleSpec("legend_1", "Early Reflections", (200, 40, 40)),
              StyleSpec("legend_2", "curve_2", (165, 25, 35)),
              StyleSpec("legend_3", "Early Reflections DI", (107, 101, 90))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (200, 40, 40)
    assert by_id["legend_3"].bgr == (200, 40, 40)


def test_snap_starved_key_stands_against_other_hue_sibling():
    """A starved key nearer a backed other-hue sibling is its own paint:
    adopting the sibling would steal junk, so the key stands."""
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (40, 0, 244))
    styles = [StyleSpec("legend_1", "Early Reflections", (41, 0, 244)),
              StyleSpec("legend_2", "Sound Power DI", (140, 30, 90))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (41, 0, 244)
    assert by_id["legend_2"].bgr == (140, 30, 90)


def _eviction_image():
    """Red plus olive curves; washed grey keys match neither paint."""
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (40, 0, 244))
    _paint_curve(img, (60, 150, 80), y0=140, amp=20)
    return img


def test_snap_evicts_overclaimed_paint_twin_stays():
    """Two dB keys over one red curve evict the greyer one to the
    unclaimed olive paint; the DI twin never follows, since families
    do not always share paint, and the backed key keeps red."""
    from graphextract.semantics import snap_legend_seeds
    img = _eviction_image()
    styles = [StyleSpec("legend_1", "On Axis", (60, 20, 220)),
              StyleSpec("legend_2", "First Reflections", (109, 113, 137)),
              StyleSpec("legend_3", "First Reflections DI", (78, 85, 94))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (60, 20, 220)  # backed: keeps red
    olive = by_id["legend_2"].bgr
    assert olive[1] > olive[0] + 20 and olive[1] > olive[2] - 60
    assert olive != by_id["legend_1"].bgr
    assert by_id["legend_3"].bgr[2] > by_id["legend_3"].bgr[0] + 40


def test_snap_eviction_keeps_confident_adopted_key():
    """Past one dB key per paint, the more saturated adopted key keeps
    the paint and the greyer one is evicted to the unclaimed paint."""
    from graphextract.semantics import snap_legend_seeds
    img = _eviction_image()
    styles = [StyleSpec("legend_1", "On Axis", (60, 40, 180)),
              StyleSpec("legend_2", "First Reflections", (109, 113, 137))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr[2] > by_id["legend_1"].bgr[0] + 40
    assert by_id["legend_2"].bgr != by_id["legend_1"].bgr
    assert by_id["legend_2"].bgr[1] > by_id["legend_2"].bgr[0]


def test_snap_no_eviction_for_balanced_pairs():
    """One dB key plus its DI twin per paint is the intended sharing:
    an unclaimed pool paint does not pull them apart."""
    from graphextract.semantics import snap_legend_seeds
    img = _eviction_image()
    styles = [StyleSpec("legend_1", "Early Reflections", (41, 0, 244)),
              StyleSpec("legend_2", "Early Reflections DI", (32, 0, 189))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (41, 0, 244)
    assert by_id["legend_2"].bgr == (41, 0, 244)


def test_snap_di_key_takes_two_banded_twin_paint():
    """A DI key takes its twin's paint when it inks two separated
    bands, even over its own backing on a same-grey reference line:
    the twin's paint is then shared with this family's DI curve."""
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (200, 40, 40), y0=60, amp=10)  # blue dB curve
    _paint_curve(img, (200, 40, 40), y0=150, amp=10)  # blue DI curve
    for x0 in range(10, 390, 30):  # grey zero-line dashes
        img[180:182, x0:x0 + 20] = (113, 113, 113)
    styles = [StyleSpec("legend_1", "Early Reflections", (200, 40, 40)),
              StyleSpec("legend_2", "Early Reflections DI", (107, 101, 90))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (200, 40, 40)
    assert by_id["legend_2"].bgr == (200, 40, 40)


def test_two_banded_ignores_achromatic_impostor_rows():
    """Achromatic tick digits inside a chromatic paint's tolerance box
    never fake a second band: a chromatic paint needs chromatic ink in
    both bands, so the DI key keeps its own black instead of taking a
    twin's purple."""
    from graphextract.semantics import _paint_two_banded, snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (62, 9, 54), y0=60, amp=10)  # purple dB curve
    _paint_curve(img, (0, 0, 0), y0=150, amp=10)  # black DI curve
    for x0 in range(10, 390, 15):  # dark tick digits, far band
        img[150:170, x0:x0 + 8] = (40, 40, 40)
    assert not _paint_two_banded(img, (62, 9, 54))
    styles = [StyleSpec("legend_1", "Sound Power", (62, 9, 54)),
              StyleSpec("legend_2", "Sound Power DI", (2, 2, 2))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (62, 9, 54)
    assert by_id["legend_2"].bgr == (2, 2, 2)


def test_two_banded_rejects_two_paints_in_one_box():
    """Two different paints sharing one tolerance box (teal dB curve
    upstairs, grey-green DI curve downstairs) are not one shared paint:
    band medians must agree, so the verdict is False."""
    from graphextract.semantics import _paint_two_banded
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (135, 170, 125), y0=60, amp=10)  # teal, upper
    _paint_curve(img, (185, 180, 145), y0=150, amp=10)  # grey-green, lower
    assert not _paint_two_banded(img, (160, 175, 135))
    img2 = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img2, (200, 40, 40), y0=60, amp=10)
    _paint_curve(img2, (200, 40, 40), y0=150, amp=10)
    assert _paint_two_banded(img2, (200, 40, 40))


def test_snap_di_key_keeps_own_with_single_band_twin():
    """A single-band twin paint leaves the DI key's own colour alone:
    families do not always share paint."""
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (60, 150, 80), y0=60, amp=10)  # olive dB curve
    _paint_curve(img, (40, 0, 244), y0=100, amp=10)  # red dB curve
    _paint_curve(img, (40, 0, 244), y0=170, amp=10)  # red DI curve
    styles = [StyleSpec("legend_1", "First Reflections", (60, 150, 80)),
              StyleSpec("legend_2", "First Reflections DI", (80, 40, 200))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (60, 150, 80)  # olive kept
    assert by_id["legend_2"].bgr[2] > by_id["legend_2"].bgr[0] + 40


def test_snap_flat_ruler_backs_only_offset_keys():
    """A flat dashed ruler never backs a curve key (its curve wanders):
    the key starves into adoption, while an offset-labeled key names
    the ruler itself and keeps it."""
    from graphextract.semantics import snap_legend_seeds
    img = np.full((200, 400, 3), 255, np.uint8)
    _paint_curve(img, (200, 40, 40))
    for x0 in range(10, 390, 30):  # flat grey ruler dashes
        img[170:172, x0:x0 + 20] = (113, 113, 113)
    styles = [StyleSpec("legend_1", "Early Reflections", (200, 40, 40)),
              StyleSpec("legend_2", "Early Reflections DI", (107, 101, 90)),
              StyleSpec("legend_3", "DI offset", (113, 113, 113))]
    fixed = snap_legend_seeds(img, styles)
    by_id = {s.series_id: s for s in fixed}
    assert by_id["legend_1"].bgr == (200, 40, 40)
    assert by_id["legend_2"].bgr == (200, 40, 40)  # sibling blue adopted
    assert by_id["legend_3"].bgr == (113, 113, 113)  # ruler kept


def test_family_words_strips_numbers_and_di_markers():
    """Row numbers and DI suffixes (including misreads) never
    distinguish families; fused suffixes split first."""
    from graphextract.semantics import _family_words
    assert (_family_words("53: First Reflections")
            == _family_words("56: First Reflections DI"))
    assert (_family_words("54: Total Sound Power")
            == _family_words("65: Total Sound Power Dl"))
    assert (_family_words("377: Total Sound Power O1")
            == _family_words("376: Total Sound Power"))
    assert _family_words("Sound PowerDI") == frozenset({"sound", "power"})
    assert (_family_words("51: On Axis")
            != _family_words("53: First Reflections"))
