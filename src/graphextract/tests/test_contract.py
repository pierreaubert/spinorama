# -*- coding: utf-8 -*-
"""Contract tests: coordinates, axis families, stable IDs, gap-safe exports."""

from pathlib import Path

import numpy as np
import pytest

from graphextract.calibration import (
    CalibrationUnresolved,
    ScaleType,
    axis_from_exact_range,
    fit_axis,
    held_out_tick_error,
    parse_tick_label,
)
from graphextract.exports import to_wpd_json
from graphextract.panels import detect_panels
from graphextract.pipeline import AxisAnchors, run_document, run_panel
from graphextract.render import RenderPanel, RenderSeries, render_panel, verify_transforms
from graphextract.schema import AxisRole, PanelOutcome, SegmentStatus, SeriesResult, SeriesSample

from helpers import log_sine_panel, renderer_anchors, styles_ab


def _anchors(pixels, values, source="manual"):
    from graphextract.schema import TickAnchor

    return [TickAnchor(p, v, 1.0, source) for p, v in zip(pixels, values)]


def test_native_origin_and_axis_round_trip():
    fit = axis_from_exact_range(AxisRole.X, ScaleType.LOG10, "Hz", 20, 20000, 70, 610)
    assert fit.transform(20.0) == pytest.approx(70.0)
    assert fit.transform(20000.0) == pytest.approx(610.0)
    for v in (20, 55.5, 1000, 19999.9):
        assert fit.invert(fit.transform(v)) == pytest.approx(v, rel=1e-9)


def test_renderer_transforms_are_exact():
    img, panel, truth = log_sine_panel()
    assert verify_transforms(truth, panel) < 1e-6
    assert set(truth.geometric_masks) == {"a", "b"}


def test_percent_axis_with_negative_free_range():
    fit = fit_axis(_anchors([400, 300, 200, 100], [-2.0, 0.0, 2.0, 4.0]),
                   AxisRole.Y_LEFT, "%", ScaleType.LINEAR)
    assert fit.invert(300.0) == pytest.approx(0.0)
    assert fit.invert(100.0) == pytest.approx(4.0)


def test_linear_time_axis_with_negative_ordinates():
    fit = fit_axis(_anchors([50, 200, 350, 500], [0.0, 0.01, 0.02, 0.03]),
                   AxisRole.X, "s", ScaleType.LINEAR)
    assert fit.invert(50.0) == pytest.approx(0.0)
    assert fit.invert(500.0) == pytest.approx(0.03)
    y = fit_axis(_anchors([400, 300, 200], [-1.0, 0.0, 1.0]),
                 AxisRole.Y_LEFT, "V", ScaleType.LINEAR)
    assert y.invert(400.0) == pytest.approx(-1.0)


def test_dual_y_axes_attach_independently():
    left = fit_axis(_anchors([400, 300, 200], [0.0, 50.0, 100.0]), AxisRole.Y_LEFT, "dB",
                    ScaleType.LINEAR)
    right = fit_axis(_anchors([400, 300, 200], [-20.0, 0.0, 20.0]), AxisRole.Y_RIGHT, "dB",
                     ScaleType.LINEAR)
    assert left.invert(300.0) == pytest.approx(50.0)
    assert right.invert(300.0) == pytest.approx(0.0)


def test_tick_label_kinds():
    assert parse_tick_label("1k") == (1000.0, "freq")
    assert parse_tick_label("20Hz") == (20.0, "freq")
    assert parse_tick_label("-10 dB") == (-10.0, "db")
    assert parse_tick_label("2.5%") == (2.5, "percent")
    assert parse_tick_label("10ms") == (0.01, "time")
    assert parse_tick_label("nonsense") is None


def test_ambiguous_scale_stays_unresolved():
    anchors = _anchors([0, 100, 200], [1.0, 2.0, 3.0])
    with pytest.raises(CalibrationUnresolved):
        fit_axis(anchors, AxisRole.X, "?", None)


def test_malformed_ticks_raise_not_guess():
    with pytest.raises(CalibrationUnresolved):
        fit_axis([], AxisRole.X, "Hz", ScaleType.LOG10)


def test_held_out_ticks_quantify_whole_axis_error():
    fit = fit_axis(_anchors([0, 100, 200, 300], [1.0, 2.0, 3.0, 4.0]),
                   AxisRole.X, "u", ScaleType.LINEAR)
    err = held_out_tick_error(fit, _anchors([150], [2.5]))
    assert err["n"] == 1 and err["max_px"] < 1e-6


def test_uncalibrated_panel_needs_review_without_guessed_values():
    img, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    interior = img[y0:y0 + h, x0:x0 + w]
    res = run_panel(img, "img#p0", interior, (x0, y0), AxisAnchors(), styles_ab())
    assert res.outcome is PanelOutcome.PARTIAL_REVIEW
    assert res.series
    assert all(s.value_x is None and s.value_y is None for t in res.series for s in t.samples)
    assert any("needed:" in r for r in res.review_reasons)


def test_wpd_export_preserves_gaps_and_stable_ids():
    from graphextract.schema import DocumentResult, PanelGeometry, PanelResult

    def samp(u, v, status):
        s = SeriesSample(u=u, v=v, status=status)
        s.value_x, s.value_y = float(u), float(v)
        return s

    series = SeriesResult("s0", "img#p0", label="Same Title", axis_id="y_left",
                          samples=[samp(0, 1, SegmentStatus.OBSERVED),
                                   samp(1, 2, SegmentStatus.OBSERVED),
                                   samp(2, 0, SegmentStatus.MISSING),
                                   samp(3, 4, SegmentStatus.OBSERVED)])
    geo = PanelGeometry("img#p0", (0, 0, 10, 10), (0, 0, 10, 10), 10, 10, title="Same Title")
    geo2 = PanelGeometry("img#p1", (0, 0, 10, 10), (0, 0, 10, 10), 10, 10, title="Same Title")
    series2 = SeriesResult("s0", "img#p1", label="Same Title", axis_id="y_left",
                           samples=[samp(0, 9, SegmentStatus.OBSERVED)])
    doc = DocumentResult("d", "img", 10, 10, "abc",
                         [PanelResult(geo, series=[series]),
                          PanelResult(geo2, series=[series2])])
    wpd = to_wpd_json(doc)
    names = [d["name"] for d in wpd["datasetColl"]]
    assert len(set(names)) == len(names)  # stable IDs survive repeated titles
    assert sum("p0" in n for n in names) == 2  # gap split into two runs, not joined


def test_mixture_match_sees_aa_edges_not_grid_or_text():
    from graphextract.evidence import mixture_match

    bg = (255, 255, 255)
    red = (0, 0, 255)
    assert mixture_match(np.full((1, 1, 3), (127, 127, 255), np.uint8), bg, red)[0, 0]
    assert mixture_match(np.full((1, 1, 3), (0, 0, 255), np.uint8), bg, red)[0, 0]
    assert not mixture_match(np.full((1, 1, 3), (220, 220, 220), np.uint8), bg, red)[0, 0]
    assert not mixture_match(np.full((1, 1, 3), (0, 0, 0), np.uint8), bg, red)[0, 0]
    assert not mixture_match(np.full((1, 1, 3), (255, 255, 255), np.uint8), bg, red)[0, 0]


def test_side_by_side_sample_finds_two_panels():
    datas = Path(__file__).resolve().parents[1] / "datas"
    img_path = datas / "AsciLab C8C speakers active 3-way cardioid speaker hypex distortion measurement.png"
    import cv2

    img = cv2.imread(str(img_path))
    assert img is not None
    panels = detect_panels(img, "sample")
    assert len(panels) == 2
    for p in panels:
        assert p.interior_confidence in ("low", "refined")


def test_bridged_panels_split_on_tick_stack():
    import cv2

    from graphextract.ocr_adapters import OCRWord
    from graphextract.panels import detect_panels

    img = np.full((300, 640, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 40), (300, 260), (0, 0, 0), 2)
    cv2.rectangle(img, (340, 40), (620, 260), (0, 0, 0), 2)
    # Shared background band bridging both panels (one content contour by
    # construction: no pixel-level gutter exists).
    img[40:261, 300:341] = (235, 235, 235)
    # Right-panel y-tick labels sitting in the gutter.
    for v, y in zip((0, 10, 20, 30, 40), (80, 120, 160, 200, 240)):
        cv2.putText(img, str(v), (308, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    words = [OCRWord(str(v), 308, y, 24, 12, 0.9)
             for v, y in zip((0, 10, 20, 30, 40), (80, 120, 160, 200, 240))]
    assert len(detect_panels(img, "bridged")) == 1  # geometric only: merged
    panels = detect_panels(img, "bridged", words=words)
    assert len(panels) == 2
    assert panels[1].interior_xywh[0] > 320


def test_stacked_and_quad_layouts_detected():
    import cv2

    img = np.full((600, 600, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 20), (570, 280), (0, 0, 0), 2)
    cv2.rectangle(img, (30, 320), (570, 580), (0, 0, 0), 2)
    assert len(detect_panels(img, "stacked")) == 2

    img4 = np.full((600, 600, 3), 255, np.uint8)
    for (x, y) in ((20, 20), (310, 20), (20, 310), (310, 310)):
        cv2.rectangle(img4, (x, y), (x + 270, y + 270), (0, 0, 0), 2)
    assert len(detect_panels(img4, "quad")) == 4


def test_faint_dashed_frame_keeps_full_interior_width():
    """Dashed frame strokes fragment under Hough; the projection pass must
    still recover the outer frame so the interior is not truncated onto an
    interior decade line (PMC10 CTA-2034 kept only the 20-200Hz third)."""
    img = np.full((400, 800, 3), 255, np.uint8)
    img[20:23, 10:791] = (0, 0, 0)  # top frame
    img[377:380, 10:791] = (0, 0, 0)  # bottom frame
    img[20:380, 10:13] = (0, 0, 0)  # solid left frame
    img[20:380, 300:303] = (0, 0, 0)  # solid interior decade line
    for y in range(30, 370, 30):  # dashed right frame: 15px segments Hough cannot link
        img[y:y + 15, 788:791] = (0, 0, 0)
    panels = detect_panels(img, "dashed")
    assert len(panels) == 1
    x, _y, w, _h = panels[0].interior_xywh
    assert w > 0.9 * panels[0].envelope_xywh[2]
    assert x <= panels[0].envelope_xywh[0] + 5


def test_panel_failure_isolation_in_document():
    img, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh

    def provider(pid, crop):
        if pid.endswith("#p0"):
            raise RuntimeError("simulated executor fault")
        return AxisAnchors()

    doc = run_document(img, "img", styles_ab(), anchor_provider=provider)
    assert len(doc.panels) >= 1
    by_id = {p.panel.panel_id: p for p in doc.panels}
    assert by_id["img#p0"].outcome is PanelOutcome.FAILED
    assert "RuntimeError" in by_id["img#p0"].review_reasons[0]
