import hashlib
import json

import cv2
import numpy as np
import pytest

from graphextract.benchmark import evaluate_manifest, load_locked_manifest, stress_cases
from graphextract.calibration import axis_from_exact_range
from graphextract.corpus import ImageAnnotation, PanelAnnotation, SeriesAnnotation, TickAnnotation
from graphextract.schema import (
    AxisRole,
    DocumentResult,
    PanelGeometry,
    PanelOutcome,
    PanelResult,
    ScaleType,
    SeriesResult,
    SeriesSample,
)


def _locked_case(tmp_path):
    image = tmp_path / "source.png"
    cv2.imwrite(str(image), np.full((30, 40, 3), 255, np.uint8))
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    annotation = ImageAnnotation(
        "source.png",
        digest(image),
        40,
        30,
        panels=[PanelAnnotation("p", [0, 0, 40, 30], [10, 5, 10, 10])],
        series=[
            SeriesAnnotation("a", "p", "Alpha", centerline_uv=[[u, 10] for u in range(10, 20)])
        ],
        ticks=[
            TickAnnotation("x", 10, 100, "Hz"),
            TickAnnotation("x", 19, 1000, "Hz"),
            TickAnnotation("y_left", 5, 80, "dB"),
            TickAnnotation("y_left", 14, 50, "dB"),
        ],
        status="locked",
    )
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(annotation.to_dict()))
    case = {
        "id": "one",
        "image": image.name,
        "annotation": gold.name,
        "image_sha256": digest(image),
        "annotation_sha256": digest(gold),
        "source_group": "source-a",
        "split": "locked_test",
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"version": 1, "cases": [case]}))
    geometry = PanelGeometry("p", (0, 0, 40, 30), (10, 5, 10, 10), 40, 30)
    panel = PanelResult(
        geometry,
        axes={
            "x": axis_from_exact_range(AxisRole.X, ScaleType.LOG10, "Hz", 100, 1000, 10, 19),
            "y_left": axis_from_exact_range(AxisRole.Y_LEFT, ScaleType.LINEAR, "dB", 80, 50, 5, 14),
        },
        series=[
            SeriesResult("a", "p", "Alpha", "y_left", [SeriesSample(u, 10) for u in range(10, 20)])
        ],
        outcome=PanelOutcome.COMPLETE,
    )
    return path, case, DocumentResult("d", "source.png", 40, 30, digest(image), [panel])


def test_locked_manifest_rejects_modified_gold_and_split_leakage(tmp_path):
    path, case, _ = _locked_case(tmp_path)
    assert len(load_locked_manifest(path)) == 1
    path.write_text(
        json.dumps({"version": 1, "cases": [case, {**case, "id": "two", "split": "train"}]})
    )
    with pytest.raises(ValueError, match="leaks"):
        load_locked_manifest(path)
    path.write_text(json.dumps({"version": 1, "cases": [case]}))
    (tmp_path / case["annotation"]).write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_locked_manifest(path)


def test_image_only_benchmark_checks_calibration_and_identity(tmp_path, monkeypatch):
    path, _, doc = _locked_case(tmp_path)
    calls = []

    def extract(*args, **kwargs):
        calls.append((args, kwargs))
        return doc

    monkeypatch.setattr("graphextract.cli.extract_image", extract)
    assert evaluate_manifest(path)["complete_images"] == 1
    assert len(calls[0][0]) == 3 and set(calls[0][1]) == {"tracker"}
    doc.panels[0].axes["x"].b += 8
    assert evaluate_manifest(path)["complete_images"] == 0
    doc.panels[0].axes["x"].b -= 8
    doc.panels[0].series[0].label = "Wrong identity"
    assert evaluate_manifest(path)["complete_images"] == 0


def test_stress_rendering_is_reproducible_and_covers_failures():
    a, b = list(stress_cases(count=6)), list(stress_cases(count=6))
    assert len({c["family"] for c in a}) == 6
    assert all(np.array_equal(x["image"], y["image"]) for x, y in zip(a, b))
    assert not np.array_equal(a[0]["image"], next(stress_cases(seed=8))["image"])


def test_scalar_diagnostic_reports_containment_and_coverage():
    from graphextract.benchmark import contour_diagnostics

    clean, compressed = contour_diagnostics()
    assert clean["interval_containment"] == 1
    assert clean["visible_coverage"] > 0.99 and clean["false_support"] == 0
    pure_palette = contour_diagnostics(allow_band_mixtures=False)[1]
    assert compressed["visible_coverage"] > pure_palette["visible_coverage"] + 0.1
    assert compressed["interval_containment"] == 1
    assert compressed["mean_interval_width"] < 4
    assert compressed["false_support"] == 0
