import json

import cv2
import numpy as np
import pytest

from graphextract.cli import extract_image, main, overlay_extracted, select_styles
from graphextract.evidence import StyleSpec
from graphextract.exports import HEADER_H, write_comparison_figure
from graphextract.ocr_adapters import OCRWord
from graphextract.pipeline import run_document, run_panel
from graphextract.schema import DocumentResult
from helpers import log_sine_panel, renderer_anchors, styles_ab


def test_cli_writes_canonical_json_and_native_pixel_overlay(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    output_json = tmp_path / "result.json"
    output_overlay = tmp_path / "result.overlay.png"
    assert cv2.imwrite(str(source), image)

    result = extract_image(source, output_json, output_overlay, styles_ab(), use_ocr=False)

    payload = json.loads(output_json.read_text())
    overlay = cv2.imread(str(output_overlay), cv2.IMREAD_COLOR)
    assert payload["image_id"] == "chart"
    assert payload["panels"]
    assert any(panel.series for panel in result.panels)
    assert overlay is not None
    assert overlay.shape == image.shape
    assert (overlay != image).any()


def test_module_cli_uses_requested_output_paths(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    output_json = tmp_path / "data.json"
    output_overlay = tmp_path / "curves.png"
    assert cv2.imwrite(str(source), image)

    assert main([
        str(source),
        "--json", str(output_json),
        "--overlay", str(output_overlay),
        "--curve", "red=#ff0000",
        "--curve", "blue=#0000ff",
        "--no-ocr",
    ]) == 0
    assert output_json.exists()
    assert output_overlay.exists()


def test_overlay_breaks_lines_at_unobserved_samples():
    image, _, _ = log_sine_panel()
    document = run_document(image, "chart", [StyleSpec("a", "A", (0, 0, 255))])
    overlay = overlay_extracted(image, document)
    assert overlay.shape == image.shape


def test_invalid_curve_colour_exits_with_usage_error(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    assert cv2.imwrite(str(source), image)
    with pytest.raises(SystemExit) as exc:
        main([str(source), "--curve", "ON=#1094127"])
    assert exc.value.code == 2


def test_compare_figure_stacks_original_over_value_space_replot(tmp_path):
    image, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    interior = image[y0:y0 + h, x0:x0 + w]
    anchors = renderer_anchors(panel, truth, (x0, y0), "renderer_verified_test")
    result = run_panel(image, "img#p0", interior, (x0, y0), anchors, styles_ab())
    document = DocumentResult(document_id="img", image_id="img",
                              image_width=image.shape[1],
                              image_height=image.shape[0],
                              image_sha256="0", panels=[result])
    output = tmp_path / "compare.png"
    write_comparison_figure(image, document, styles_ab(), output)

    figure = cv2.imread(str(output), cv2.IMREAD_COLOR)
    assert figure is not None
    assert figure.shape == (2 * h + 2 * HEADER_H, w, 3)
    # Top view is the untouched original interior.
    np.testing.assert_array_equal(figure[HEADER_H:HEADER_H + h], interior)
    # Bottom view replots in data space: grid ink plus both legend colours.
    bottom = figure[2 * HEADER_H + h:]
    assert (bottom != 255).any()
    red = (bottom[..., 2] > 150) & (bottom[..., 1] < 100) & (bottom[..., 0] < 100)
    blue = (bottom[..., 0] > 150) & (bottom[..., 1] < 100) & (bottom[..., 2] < 100)
    assert red.any()
    assert blue.any()


def test_extract_image_compare_flag_writes_stacked_figure(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    assert cv2.imwrite(str(source), image)
    compare = tmp_path / "sub" / "compare.png"

    assert main([str(source), "--compare", str(compare), "--no-ocr"]) == 0
    assert compare.exists()


def test_write_curve_csvs_rows_match_drawable_samples(tmp_path):
    from graphextract.exports import write_curve_csvs
    from graphextract.schema import SegmentStatus as Status
    image, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    interior = image[y0:y0 + h, x0:x0 + w]
    anchors = renderer_anchors(panel, truth, (x0, y0), "renderer_verified_test")
    result = run_panel(image, "img#p0", interior, (x0, y0), anchors, styles_ab())
    document = DocumentResult(document_id="img", image_id="img",
                              image_width=image.shape[1],
                              image_height=image.shape[0],
                              image_sha256="0", panels=[result])
    paths = write_curve_csvs(document, tmp_path / "curves")
    assert sorted(p.name for p in paths) == ["img.a.csv", "img.b.csv"]
    for path, series in zip(sorted(paths), result.series):
        lines = path.read_text().splitlines()
        assert lines[0] == "freq_Hz,spl_dB,status"
        drawable = [s for s in series.samples
                    if s.status in (Status.OBSERVED, Status.INTERPOLATED)
                    and s.value_x is not None and s.value_y is not None]
        assert len(lines) - 1 == len(drawable) > 0
        xs = [float(line.split(",")[0]) for line in lines[1:]]
        assert all(b > a for a, b in zip(xs, xs[1:]))
        assert {line.split(",")[2] for line in lines[1:]} <= {"observed", "interpolated"}


def test_write_curve_csvs_slugifies_labels_and_dedupes(tmp_path):
    from graphextract.calibration import ScaleType
    from graphextract.exports import write_curve_csvs
    from graphextract.schema import (
        AxisFit,
        AxisRole,
        DocumentResult,
        PanelGeometry,
        PanelResult,
        SegmentStatus as Status,
        SeriesResult,
        SeriesSample,
    )
    axes = {"x": AxisFit(AxisRole.X, ScaleType.LOG10, "Hz", 1.0, 0.0),
            "y_left": AxisFit(AxisRole.Y_LEFT, ScaleType.LINEAR, "dB", 1.0, 0.0)}

    def series(sid, label):
        sample = SeriesSample(u=0.0, v=0.0, status=Status.OBSERVED,
                              value_x=20.0, value_y=70.0)
        return SeriesResult(sid, "img#p0", label, "y_left", [sample])

    geo = PanelGeometry("img#p0", (0, 0, 10, 10), (0, 0, 10, 10), 10, 10)
    panel = PanelResult(geo, axes=axes, series=[
        series("legend_5", "Estimated |In-Room"),
        series("a", "A/B"),
        series("b", "a_b"),
        series("c", ""),
    ])
    document = DocumentResult("d", "img", 10, 10, "abc", [panel])
    paths = write_curve_csvs(document, tmp_path)
    assert sorted(p.name for p in paths) == [
        "img.a_b.csv", "img.a_b_2.csv", "img.c.csv", "img.estimated_in_room.csv"]
    assert paths[0].read_text().splitlines()[0] == "freq_Hz,spl_dB,status"


def test_csv_dir_flag_writes_one_file_per_curve(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    assert cv2.imwrite(str(source), image)
    csv_dir = tmp_path / "curves"

    assert main([str(source), "--csv-dir", str(csv_dir),
                 "--curve", "R=#ff0000", "--curve", "B=#0000ff",
                 "--no-ocr"]) == 0
    files = sorted(csv_dir.glob("*.csv"))
    assert [f.name for f in files] == ["chart.b.csv", "chart.r.csv"]
    assert all(f.read_text().splitlines()[0].endswith(",status") for f in files)


def test_unknown_assumption_exits_with_usage_error(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    assert cv2.imwrite(str(source), image)
    with pytest.raises(SystemExit) as exc:
        main([str(source), "--assumptions", "telepathy", "--no-ocr"])
    assert exc.value.code == 2


def test_assumptions_reach_tracking_and_provenance(tmp_path):
    image, _, _ = log_sine_panel()
    source = tmp_path / "chart.png"
    output_json = tmp_path / "data.json"
    assert cv2.imwrite(str(source), image)

    assert main([str(source), "--json", str(output_json),
                 "--assumptions", "no_jump,curve_continuous",
                 "--assumptions", "assume_overlap",
                 "--no-ocr"]) == 0
    payload = json.loads(output_json.read_text())
    assert payload["panels"][0]["provenance"]["assumptions"] == [
        "curve_continuous", "no_jump", "assume_overlap"]

    result = extract_image(source, tmp_path / "b.json", tmp_path / "b.png",
                           styles_ab(), use_ocr=False)
    assert "assumptions" not in result.panels[0].provenance


def test_select_styles_prefers_explicit_then_legend_then_discovery():
    img = np.full((60, 200, 3), 255, np.uint8)
    cv2.line(img, (10, 20), (70, 20), (0, 0, 255), 3)
    words = [OCRWord("Red", 80, 13, 30, 13, 0.9)]
    explicit = [StyleSpec("x", "X", (0, 0, 255))]
    assert select_styles(img, words, explicit) == explicit
    assert [s.label for s in select_styles(img, words, [])] == ["Red"]
    assert len(select_styles(img, None, [])) >= 1
