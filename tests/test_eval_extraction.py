# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for the evaluation framework."""

import math
import json
from pathlib import Path

import numpy as np
import plotly.io as pio
import pytest

from graphextract.eval_extraction import (
    CurveMetrics,
    _migrate_legacy_mapbox_schema,
    compare_curves,
    load_plotly_ground_truth,
    render_plotly_to_png,
)
from spinorama.extract.axis_calibrate import AxisCalibration, calibration_from_plotly_layout
from graphextract.extract_spinorama_colors import hex_to_hsv_range

# A known CEA2034 file for real-data tests
_SAMPLE_DIR = Path("/Volumes/data/Binaries/spinorama/dist/speakers")
_SAMPLE_CEA2034 = _SAMPLE_DIR / "Arendal Sound 1723 Monitor S THX/ErinsAudioCorner/eac/CEA2034.json"


def _have_sample_data() -> bool:
    return _SAMPLE_CEA2034.exists()


# ── hex_to_hsv_range ────────────────────────────────────────────────


def test_hex_to_hsv_range_on_axis_blue():
    """Verify #5c77a5 converts to expected HSV center."""
    lower, upper = hex_to_hsv_range("#5c77a5", h_tol=10, s_tol=40, v_tol=40)
    # OpenCV HSV: H is 0-179
    # The center should be around H=108, S=112, V=165
    h_center = (lower[0] + upper[0]) / 2
    s_center = (lower[1] + upper[1]) / 2
    v_center = (lower[2] + upper[2]) / 2
    assert 95 <= h_center <= 120, f"H center {h_center} out of range"
    assert 70 <= s_center <= 150, f"S center {s_center} out of range"
    assert 120 <= v_center <= 200, f"V center {v_center} out of range"


def test_hex_to_hsv_range_red():
    """Verify red color (#c85857) has H near 0."""
    lower, upper = hex_to_hsv_range("#c85857", h_tol=10, s_tol=40, v_tol=40)
    # Red in OpenCV HSV: H near 0 or near 179
    assert lower[0] <= 15 or lower[0] >= 160


def test_hex_to_hsv_range_tolerance():
    """Verify tolerance widens the range."""
    narrow = hex_to_hsv_range("#5c77a5", h_tol=5, s_tol=20, v_tol=20)
    wide = hex_to_hsv_range("#5c77a5", h_tol=15, s_tol=60, v_tol=60)
    # Wide range should be broader
    assert (wide[1][0] - wide[0][0]) >= (narrow[1][0] - narrow[0][0])
    assert (wide[1][1] - wide[0][1]) >= (narrow[1][1] - narrow[0][1])


# ── calibration_from_plotly_layout ──────────────────────────────────


def test_calibration_from_plotly_layout_roundtrip():
    """Verify pixel↔freq/dB roundtrip with known layout."""
    layout = {
        "margin": {"l": 80, "r": 80, "t": 100, "b": 80},
        "xaxis": {"range": [math.log10(20), math.log10(20000)]},
        "yaxis": {"range": [-45, 5]},
    }
    cal = calibration_from_plotly_layout(layout, img_w=1200, img_h=800)

    # Roundtrip: freq → pixel → freq
    for freq in [20, 100, 1000, 10000, 20000]:
        px = cal.freq_to_pixel_x(freq)
        freq_back = cal.pixel_x_to_freq(px)
        assert abs(freq_back - freq) / freq < 1e-6, f"Freq roundtrip failed for {freq}"

    # Roundtrip: dB → pixel → dB
    for db in [-45, -20, 0, 5]:
        py = cal.db_to_pixel_y(db)
        db_back = cal.pixel_y_to_db(py)
        assert abs(db_back - db) < 1e-6, f"dB roundtrip failed for {db}"


def test_calibration_from_plotly_layout_bounds():
    """Verify plot bounds match margins."""
    layout = {
        "margin": {"l": 10, "r": 10, "t": 80, "b": 10},
        "xaxis": {"range": [math.log10(20), math.log10(20000)]},
        "yaxis": {"range": [-40, 10]},
    }
    cal = calibration_from_plotly_layout(layout, img_w=1200, img_h=800)

    assert cal.plot_x_min == 10
    assert cal.plot_x_max == 1190
    assert cal.plot_y_min == 80
    assert cal.plot_y_max == 790

    # freq at left edge should be 20 Hz
    assert abs(cal.pixel_x_to_freq(10) - 20) < 0.1
    # freq at right edge should be 20000 Hz
    assert abs(cal.pixel_x_to_freq(1190) - 20000) < 1.0


# ── compare_curves ──────────────────────────────────────────────────


def test_compare_curves_identical():
    """Identical curves should have RMS=0 and correlation=1."""
    freqs = np.logspace(np.log10(20), np.log10(20000), 200)
    dbs = np.sin(np.log10(freqs)) * 10

    pts = list(zip(freqs.tolist(), dbs.tolist()))
    metrics = compare_curves(pts, freqs, dbs)

    assert metrics.rms_error_db < 0.01
    assert metrics.correlation > 0.999
    assert metrics.frequency_coverage > 0.99


def test_compare_curves_offset():
    """A constant 2dB offset should give RMS≈2."""
    freqs = np.logspace(np.log10(20), np.log10(20000), 200)
    dbs = np.sin(np.log10(freqs)) * 10
    dbs_offset = dbs + 2.0

    pts = list(zip(freqs.tolist(), dbs_offset.tolist()))
    metrics = compare_curves(pts, freqs, dbs)

    assert abs(metrics.rms_error_db - 2.0) < 0.1
    assert metrics.correlation > 0.99  # shape preserved, just shifted
    assert metrics.frequency_coverage > 0.99


def test_compare_curves_partial_overlap():
    """Partial frequency overlap should reduce coverage."""
    gt_freqs = np.logspace(np.log10(20), np.log10(20000), 200)
    gt_dbs = np.zeros(200)

    # Extracted only covers 100-10000 Hz
    ext_freqs = np.logspace(np.log10(100), np.log10(10000), 100)
    ext_dbs = np.zeros(100)

    pts = list(zip(ext_freqs.tolist(), ext_dbs.tolist()))
    metrics = compare_curves(pts, gt_freqs, gt_dbs)

    assert metrics.rms_error_db < 0.01
    assert metrics.frequency_coverage < 0.8


def test_compare_curves_empty():
    """Empty extraction should return inf RMS."""
    gt_freqs = np.logspace(np.log10(20), np.log10(20000), 200)
    gt_dbs = np.zeros(200)
    metrics = compare_curves([], gt_freqs, gt_dbs)
    assert metrics.rms_error_db == float("inf")
    assert metrics.frequency_coverage == 0.0


def test_migrate_legacy_mapbox_schema_for_plotly_7():
    """Legacy exported templates should parse with Plotly 7."""
    figure_json = {
        "data": [
            {
                "type": "scattermapbox",
                "subplot": "mapbox",
                "lat": [46.95],
                "lon": [7.44],
            }
        ],
        "layout": {
            "mapbox": {"style": "open-street-map"},
            "template": {
                "data": {"scattermapbox": [{"marker": {"colorbar": {"ticks": ""}}}]},
                "layout": {"mapbox": {"style": "light"}},
            },
        },
    }

    _migrate_legacy_mapbox_schema(figure_json)
    fig = pio.from_json(json.dumps(figure_json))

    assert fig.data[0].type == "scattermap"
    assert fig.data[0].subplot == "map"
    assert fig.layout.map is not None
    assert fig.layout.template.data.scattermap is not None
    assert fig.layout.template.layout.map is not None


# ── Real data tests (require sample data) ──────────────────────────


@pytest.mark.skipif(not _have_sample_data(), reason="Sample data not available")
def test_load_plotly_ground_truth():
    """Load a real CEA2034 JSON and verify trace names, shapes, and y2 detection."""
    gt_data = load_plotly_ground_truth(_SAMPLE_CEA2034)

    assert len(gt_data.curves) >= 6, f"Expected at least 6 traces, got {len(gt_data.curves)}"
    expected_names = {
        "On Axis",
        "Listening Window",
        "Early Reflections",
        "Sound Power",
        "Early Reflections DI",
        "Sound Power DI",
    }
    assert expected_names.issubset(set(gt_data.curves.keys()))

    for name, (x, y) in gt_data.curves.items():
        assert len(x) == len(y), f"Shape mismatch for {name}"
        assert len(x) > 10, f"Too few points for {name}: {len(x)}"
        assert x[0] > 0, f"Invalid frequency for {name}"

    # DI curves should be detected as y2
    assert "Early Reflections DI" in gt_data.y2_curve_names
    assert "Sound Power DI" in gt_data.y2_curve_names
    assert "On Axis" not in gt_data.y2_curve_names


@pytest.mark.skipif(not _have_sample_data(), reason="Sample data not available")
def test_render_plotly_to_png():
    """Render a real CEA2034 file and check image dimensions."""
    img = render_plotly_to_png(_SAMPLE_CEA2034, width=1200, height=800)
    assert img.shape == (800, 1200, 3)
    # Should not be all black; mostly white background is expected
    assert img.mean() > 10
    # Should have some non-white pixels (the curves and grid)
    assert np.sum(img < 250) > 1000


@pytest.mark.skipif(not _have_sample_data(), reason="Sample data not available")
def test_end_to_end_single_file():
    """Run the full evaluation pipeline on one real CEA2034 file."""
    from graphextract.eval_extraction import evaluate_single_graph

    result = evaluate_single_graph(_SAMPLE_CEA2034, "CEA2034", calibration_mode="oracle")

    assert result.status == "success", f"Failed: {result.error}"
    assert len(result.curves) >= 1, "No curves evaluated"
    assert result.rendered_img is not None, "No rendered image"
    assert len(result.gt_curves) >= 1, "No ground truth curves"
    assert len(result.extracted_curves) >= 1, "No extracted curves"

    # At least On Axis should be present and have reasonable metrics
    if "On Axis" in result.curves:
        m = result.curves["On Axis"]
        assert m["rms_error_db"] < 10.0, f"RMS too high: {m['rms_error_db']}"
        assert m["frequency_coverage"] > 0.5, f"Coverage too low: {m['frequency_coverage']}"
