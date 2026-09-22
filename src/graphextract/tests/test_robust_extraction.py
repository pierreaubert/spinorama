"""Regressions for acceptance honesty, temporal ambiguity, and interval fields."""

import json

import cv2
import numpy as np
import pytest

from graphextract.confidence import select_threshold, validate_threshold
from graphextract.contours import extract_field, sample_bands, write_field
from graphextract.evaluate import score_panel_completeness, score_series
from graphextract.evidence import EvidenceLayers
from graphextract.schema import PanelOutcome, SegmentStatus
from graphextract.tracking import TrackConfig, track_panel


def test_acceptance_needs_statistical_support_and_independent_validation():
    with pytest.raises(ValueError, match="not substantiated"):
        select_threshold(np.array([0.99]), [True])
    point = select_threshold(np.full(800, 0.9), [True] * 800)
    assert point.precision_lower_bound >= 0.995
    valid = validate_threshold(np.full(800, 0.9), [True] * 800, point.threshold)
    assert valid.stage == "held_out"
    with pytest.raises(ValueError, match="held-out"):
        validate_threshold(np.full(800, 0.9), [True] * 790 + [False] * 10, point.threshold)
    with pytest.raises(ValueError):
        select_threshold(np.array([np.nan]), [True])


def test_duplicate_samples_cannot_buy_coverage_or_strict_pass():
    score = score_series(
        [0, 0, 0], [2, 2, 2], [True] * 3, np.arange(3), np.full(3, 2), np.ones(3, bool), "a"
    )
    assert score.measured_coverage == pytest.approx(1 / 3)
    assert score.false_support == pytest.approx(2 / 3)
    assert not score.strict_pass
    good = score_series([0], [2], [True], np.array([0]), np.array([2]), np.array([True]), "a")
    assert good.strict_pass
    assert (
        score_panel_completeness("p", ["a", "b"], ["a", "b"], {"a": good}).outcome
        is not PanelOutcome.COMPLETE
    )


def test_temporal_future_evidence_rejects_short_distractor():
    mask = np.zeros((60, 60), np.uint8)
    mask[20, :] = 255
    mask[40, :25] = 255
    gray = np.full(mask.shape, 255, np.uint8)
    gray[mask > 0] = 0
    layers = EvidenceLayers({"a": mask}, np.zeros_like(mask), (255, 255, 255))
    tr = track_panel(gray, layers, ["a"], 255, TrackConfig(backend="temporal"))["a"]
    assert all(s.status is SegmentStatus.OBSERVED and abs(s.v - 20) < 1 for s in tr.samples)


def test_temporal_equally_supported_paths_remain_ambiguous():
    mask = np.zeros((60, 40), np.uint8)
    mask[20, :] = mask[40, :] = 255
    gray = np.where(mask > 0, 0, 255).astype(np.uint8)
    layers = EvidenceLayers({"a": mask}, np.zeros_like(mask), (255, 255, 255))
    tr = track_panel(gray, layers, ["a"], 255, TrackConfig(backend="temporal"))["a"]
    assert tr.alternatives and tr.review_reasons
    assert all(s.status is SegmentStatus.AMBIGUOUS for s in tr.samples)


def test_learned_shape_prior_cannot_name_identical_colors():
    mask = np.zeros((60, 40), np.uint8)
    mask[20, :] = mask[40, :] = 255
    gray = np.where(mask > 0, 0, 255).astype(np.uint8)
    probability = np.full(mask.shape, 0.01)
    probability[20] = 0.99
    layers = EvidenceLayers(
        {"a": mask}, np.zeros_like(mask), (255, 255, 255), curve_probabilities={"a": probability}
    )
    tr = track_panel(
        gray, layers, ["a"], 255, TrackConfig(backend="temporal"), {"a": (0, 0, 0), "b": (0, 0, 0)}
    )["a"]
    assert tr.observed_support() == 0
    assert any("identity constraint" in r for r in tr.review_reasons)


def _field_fixture():
    image = np.full((64, 72, 3), 255, np.uint8)
    colors = [(210, 20, 10), (10, 210, 10), (10, 20, 210)]
    for i, color in enumerate(colors):
        image[4:44, 4 + 20 * i : 24 + 20 * i] = color
        image[50:58, 4 + 20 * i : 24 + 20 * i] = color
    config = {
        "plot_xywh": [4, 4, 60, 40],
        "colorbar_xywh": [4, 50, 60, 8],
        "band_edges": [-9, -6, -3, 0],
        "unit": "dB",
        "x": {"scale": "log10", "unit": "Hz", "anchors": [[4, 100], [34, 1000], [64, 10000]]},
        "y": {"scale": "linear", "unit": "deg", "anchors": [[4, 90], [24, 0], [44, -90]]},
    }
    return image, config


def test_field_recovers_intervals_and_keeps_grid_unknown(tmp_path):
    image, config = _field_fixture()
    image[24, 4:64] = 255
    image[10:13, 30:33] = 0
    field = extract_field(image, config)
    assert field.lower[0, 0] == -9 and field.upper[0, 0] == -6
    assert field.lower[0, 30] == -6 and field.upper[0, 30] == -3
    assert not field.valid[20].any() and np.isnan(field.lower[20]).all()
    assert not field.valid[6:9, 26:29].any()
    lower, upper, valid = field.resample([100, 1000, 1e6], [90, 0])
    assert valid[0, :2].all() and not valid[:, -1].any()
    assert not valid[1].any()  # masked grid stays unknown on resampling
    path = tmp_path / "image.png"
    cv2.imwrite(str(path), image)
    meta = write_field(field, image, path, tmp_path / "field.json", tmp_path / "preview.png")
    assert meta["kind"] == "scalar_field"
    stored = np.load(tmp_path / "field.npz")
    assert np.array_equal(stored["valid"], field.valid)
    assert "NaN" not in (tmp_path / "field.json").read_text()
    assert json.loads((tmp_path / "field.json").read_text())["unit"] == "dB"


def test_vertical_reversed_colorbar_and_open_end_bands():
    image, config = _field_fixture()
    bar = image[50:58, 4:64]
    vertical = np.transpose(bar[:, ::-1], (1, 0, 2)).copy()
    bands = sample_bands(
        vertical,
        [0, 0, 8, 60],
        config["band_edges"],
        reverse=True,
        extend_min=True,
        extend_max=True,
    )
    assert bands[0].bgr == (210, 20, 10)
    assert bands[0].lower == -np.inf and bands[-1].upper == np.inf


def test_repeated_palette_is_rejected_and_cli_emits_field(tmp_path):
    from graphextract.cli import main

    image, config = _field_fixture()
    path = tmp_path / "image.png"
    cv2.imwrite(str(path), image)
    calibration = tmp_path / "calibration.json"
    calibration.write_text(json.dumps(config))
    assert main([str(path), "--kind", "filled-contour", "--calibration", str(calibration)]) == 0
    assert path.with_suffix(".npz").exists()
    image[50:58, 24:44] = image[50, 4]
    with pytest.raises(ValueError, match="palette"):
        extract_field(image, config)


def test_derived_contours_keep_closed_components_and_record_inference():
    image, config = _field_fixture()
    image[4:44, 4:64] = (210, 20, 10)
    cv2.circle(image, (20, 24), 7, (10, 210, 10), -1)
    cv2.circle(image, (48, 24), 7, (10, 210, 10), -1)
    field = extract_field(image, config)
    contour = field.contours([-6])[0]
    assert contour.status == "interpolated" and len(contour.paths) == 2
    assert all(np.allclose(p[0], p[-1]) for p in contour.paths)


def test_explicit_log_y_calibration_is_respected():
    from graphextract.pipeline import AxisAnchors, run_panel
    from graphextract.schema import ScaleType, TickAnchor

    image = np.full((64, 64, 3), 255, np.uint8)
    anchors = AxisAnchors(
        x=[TickAnchor(5, 1), TickAnchor(30, 1.5), TickAnchor(55, 2)],
        x_scale=ScaleType.LINEAR,
        y_left=[TickAnchor(5, 100), TickAnchor(30, 10), TickAnchor(55, 1)],
        y_scale=ScaleType.LOG10,
    )
    result = run_panel(image, "p", image, (0, 0), anchors, [])
    assert result.axes["y_left"].scale is ScaleType.LOG10
    assert result.axes["y_left"].invert(30) == pytest.approx(10)
