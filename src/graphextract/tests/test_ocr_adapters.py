# -*- coding: utf-8 -*-
"""Tests for ocr_adapters.py: association, unit inference, graceful absence."""

import cv2
import numpy as np

from graphextract.calibration import ScaleType, fit_axis
from graphextract.ocr_adapters import (
    OCRWord,
    StubOCR,
    TesseractOCR,
    anchors_from_ocr,
    associate_ticks,
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


def test_panel_anchors_ignore_interior_digit_words():
    """A digit word centred inside the plot (legend fragment, curve label)
    must not snap to a gridline as a tick anchor: the phantom would block
    real margin recovery downstream."""
    from graphextract.schema import PanelGeometry

    img = _margin_frame_image()
    panel = PanelGeometry("img#p0", (50, 30, 400, 240), (60, 40, 381, 220), 500, 300)
    interior = img[40:260, 60:441]
    words = _margin_frame_words() + [OCRWord("7", 70, 143, 14, 14, 0.9)]
    anchors = panel_anchors_from_words(words, panel, interior)
    assert [t.value for t in anchors.x] == [20.0, 200.0, 2000.0]
    assert [t.value for t in anchors.y_left] == [0.0, 50.0, 100.0]
    assert anchors.y_right == []


def test_paren_unit_names_axes():
    """Axis titles like 'Frequency (Hz)' name units the bare tick numbers
    cannot: the log axis becomes explicit instead of residual-competed."""
    assert infer_axis_spec([OCRWord("(Hz)", 0, 0, 20, 10)]) == (ScaleType.LOG10, "Hz", "")
    assert infer_axis_spec([OCRWord("Frequency (Hz)", 0, 0, 60, 10)])[1] == "Hz"
    assert infer_axis_spec([OCRWord("(dB)", 0, 0, 20, 10)])[2] == "dB"
    assert infer_axis_spec([]) == (None, "", "")
    # Square-bracket units are the same convention, not a new one.
    assert infer_axis_spec([OCRWord("[Hz]", 0, 0, 20, 10)]) == (ScaleType.LOG10, "Hz", "")
    assert infer_axis_spec([OCRWord("Frequency [Hz]", 0, 0, 60, 10)])[1] == "Hz"
    assert infer_axis_spec([OCRWord("[dB]", 0, 0, 20, 10)])[2] == "dB"


def test_dedup_words_collapses_decade_rereads():
    """Several readings of one decade label ('104', '10', '10+') collapse
    to the longest parsable one, so bare duplicates cannot wedge pitch
    triples apart; junk suffixes never evict parsable reads."""
    from graphextract.ocr_adapters import _dedup_words

    collapsed = _dedup_words([OCRWord("10", 0, 0, 60, 30, 0.9),
                              OCRWord("104", 2, 1, 60, 30, 0.1),
                              OCRWord("10+", 1, 0, 60, 30, 0.2)])
    # '10' folds into '104'; unparsable '10+' coexists as one more
    # superscript chance, never as an anchor.
    assert [w.text for w in collapsed] == ["10+", "104"]
    kept = _dedup_words([OCRWord("10", 0, 0, 60, 30, 0.9),
                         OCRWord("10eee", 1, 0, 60, 30, 0.1)])
    assert sorted(w.text for w in kept) == ["10", "10eee"]


def test_repair_pitch_decades_fills_ambiguous_middle():
    """An unfolded '102' between pitch-even 10^2/10^4 pins becomes 10^3;
    genuine numbers and folded evidence are never touched."""
    from graphextract.ocr_adapters import _repair_pitch_decades

    a = OCRWord("10^2", 600, 0, 60, 30, 0.9)
    b = OCRWord("102", 1270, 0, 60, 30, 0.9)
    c = OCRWord("10^4", 1940, 0, 60, 30, 0.9)
    new_text: dict = {}
    _repair_pitch_decades([a, b, c], new_text)
    assert new_text[id(b)][0] == "10^3"

    genuine = OCRWord("500", 1270, 0, 60, 30, 0.9)
    new_text2: dict = {}
    _repair_pitch_decades([a, genuine, c], new_text2)
    assert new_text2 == {}

    folded = OCRWord("10^2", 1270, 0, 60, 30, 0.9)
    new_text3: dict = {}
    _repair_pitch_decades([a, folded, c], new_text3)
    assert new_text3 == {}


def test_merged_superscript_box_needs_raised_digit():
    """Uniform-baseline '103' yields no superscript box; a raised small
    digit does (synthetic putText, no OCR involved)."""
    import cv2
    import numpy as np

    from graphextract.ocr_adapters import _merged_superscript_box

    flat = np.full((80, 200, 3), 255, np.uint8)
    cv2.putText(flat, "103", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    gray = cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY)
    assert _merged_superscript_box(gray, OCRWord("103", 5, 15, 90, 45, 0.9)) is None

    raised = np.full((80, 200, 3), 255, np.uint8)
    cv2.putText(raised, "10", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(raised, "3", (52, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    gray = cv2.cvtColor(raised, cv2.COLOR_BGR2GRAY)
    box = _merged_superscript_box(gray, OCRWord("103", 5, 15, 90, 45, 0.9))
    assert box is not None
    x0, y0, x1, y1 = box
    assert 45 <= x0 <= 65 and 20 <= y0 <= 35 and x1 - x0 < 20 and y1 - y0 < 20


def test_wide_x_labels_use_wider_snap_gate():
    """Multi-digit x labels centre far from their grid line (Devialet
    '10000' sits ~34px off, past the tight y gate); the x gate scales
    with image width instead."""
    img = _grid_image()
    words = [OCRWord("10k", 280, 176, 24, 14, 0.9)]  # centre 22px off x=270
    anchors, _ = anchors_from_ocr(words, img)
    assert anchors.x == []  # tight gate: honestly unmatched, never guessed
    assoc = associate_ticks(words, [30, 150, 270], [20, 90, 160],
                            img.shape[1], img.shape[0], snap_x_px=40)
    assert [t.value for t in assoc.x] == [10000.0]
    assert [t.pixel for t in assoc.x] == [270]  # grid, not box center


def test_y_tick_word_outside_plot_span_never_anchors():
    """A numeric word floating above the frame (legend-zone fragment) must
    not anchor the y fit even when it snaps to the frame row."""
    img = _grid_image()  # grid rows at y 20, 90, 160
    _ = img
    words = [OCRWord("90", 0, 82, 20, 14, 0.9),     # cy 89, inside
             OCRWord("45", 280, -16, 20, 14, 0.9)]  # cy -9, above frame
    assoc = associate_ticks(words, [30, 150, 270], [20, 90, 160], 300, 200)
    assert [t.value for t in assoc.y_left] == [90.0]
    assert any("outside plot vertical span" in u for u in assoc.unmatched)


def test_decimal_dot_graft_roundness():
    """A dot-sized round blob restores '80.0' from '800'; a gridline
    fragment in the cell must not graft '100' into '10.0'."""
    from graphextract.ocr_adapters import _restore_decimal_dots
    img = np.full((40, 90, 3), 255, np.uint8)
    cv2.putText(img, "800", (5, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (60, 60, 60), 2)
    cv2.circle(img, (72, 24), 2, (60, 60, 60), -1)  # faint decimal dot
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    words = [OCRWord("800", 5, 5, 60, 26, 0.9)]
    assert _restore_decimal_dots(gray, words)[0].text == "80.0"
    grid = np.full((40, 90, 3), 255, np.uint8)
    cv2.putText(grid, "100", (5, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.line(grid, (0, 24), (89, 24), (180, 180, 180), 2)  # gridline fragment
    ggray = cv2.cvtColor(grid, cv2.COLOR_BGR2GRAY)
    assert _restore_decimal_dots(ggray, words)[0].text == "800"


def test_conflicting_reads_on_one_row_do_not_win_fit():
    """A pile of conflicting values snapped to one grid line forms
    zero-slope pairs; the fit must skip the degenerate winner and take
    the runner-up true line."""
    from graphextract.schema import AxisRole, TickAnchor
    anchors = ([TickAnchor(1004.0, v, 0.5, "ocr") for v in (70, 2, 78, 27)]
               + [TickAnchor(float(p), float(v), 0.9, "ocr")
                  for p, v in ((5, 20), (1160, 1000), (1840, 10000), (2045, 20000))])
    fit = fit_axis(anchors, AxisRole.X, "Hz", ScaleType.LOG10)
    assert abs(fit.a - 680.0) < 5.0
    assert len(fit.anchors_used) == 4


def test_split_frequency_title_names_log_axis():
    """'Frequency / Hz' rendered as separate words names the log axis that
    bare tick numbers ('100', '1000') cannot (Devialet x axis has no
    parenthesised unit and no suffixed labels)."""
    words = [OCRWord("Frequency", 0, 0, 60, 10),
             OCRWord("/", 0, 0, 8, 10),
             OCRWord("Hz", 0, 0, 20, 10),
             OCRWord("100", 0, 0, 20, 10),
             OCRWord("1000", 0, 0, 30, 10)]
    scale, x_unit, _ = infer_axis_spec(words)
    assert scale is ScaleType.LOG10 and x_unit == "Hz"
