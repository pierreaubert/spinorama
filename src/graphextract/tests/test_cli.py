import json

import cv2

from graphextract.cli import extract_image, main, overlay_extracted
from graphextract.evidence import StyleSpec
from graphextract.pipeline import run_document
from tests.helpers import log_sine_panel, styles_ab


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
