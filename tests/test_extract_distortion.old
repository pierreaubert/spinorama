#!/usr/bin/env python3
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

"""Tests for the distortion curve extraction pipeline."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from spinorama.extract.plot_detect import PlotRegion, detect_plot_regions
from spinorama.extract.axis_calibrate import (
    AxisCalibration,
    _parse_freq_label,
    _parse_db_label,
    _hardcoded_klippel_calibration,
    _validate_calibration,
)
from spinorama.extract.color_segment import (
    CurveColorSpec,
    DEFAULT_CURVE_SPECS,
    segment_curves,
)
from spinorama.extract.curve_trace import (
    _find_clusters,
    _weighted_centroid,
    trace_single_curve,
    curves_to_wpd_json,
)
from spinorama.extract.distortion import ExtractionResult


def _make_synthetic_plot(
    width: int = 800,
    height: int = 600,
    curves: dict[str, tuple[tuple[int, int, int], list[tuple[float, float]]]] | None = None,
) -> np.ndarray:
    """Generate a synthetic Klippel-like plot image.

    Args:
        width: Image width.
        height: Image height.
        curves: Dict of curve_name -> (BGR_color, [(freq_hz, dB), ...]).

    Returns:
        BGR image array.
    """
    img = np.full((height, width, 3), 255, dtype=np.uint8)

    # Plot area margins (matching hardcoded calibration ratios)
    px_min = int(0.12 * width)
    px_max = int(0.92 * width)
    py_min = int(0.08 * height)
    py_max = int(0.88 * height)

    # Draw plot border
    cv2.rectangle(img, (px_min, py_min), (px_max, py_max), (200, 200, 200), 1)

    # Draw grid lines
    log_freq_min = math.log10(20)
    log_freq_max = math.log10(20000)
    db_min = 20.0
    db_max = 100.0

    plot_w = px_max - px_min
    plot_h = py_max - py_min

    # Vertical grid lines at decade frequencies
    for freq in [100, 1000, 10000]:
        x = int(px_min + plot_w * (math.log10(freq) - log_freq_min) / (log_freq_max - log_freq_min))
        cv2.line(img, (x, py_min), (x, py_max), (220, 220, 220), 1)

    # Horizontal grid lines every 10 dB
    for db in range(20, 110, 10):
        y = int(py_max - plot_h * (db - db_min) / (db_max - db_min))
        cv2.line(img, (px_min, y), (px_max, y), (220, 220, 220), 1)

    if curves is None:
        # Default: draw a fundamental curve (cyan)
        curves = {
            "Fundamental": (
                (200, 200, 0),  # cyan in BGR
                [
                    (f, 85.0 - 5.0 * abs(math.log10(f / 1000)))
                    for f in np.logspace(math.log10(20), math.log10(20000), 200)
                ],
            ),
            "THD": (
                (0, 0, 200),  # red in BGR
                [
                    (f, 55.0 - 3.0 * abs(math.log10(f / 1000)))
                    for f in np.logspace(math.log10(20), math.log10(20000), 200)
                ],
            ),
        }

    for _name, (color, points) in curves.items():
        prev_pt = None
        for freq, db in points:
            x = int(
                px_min + plot_w * (math.log10(freq) - log_freq_min) / (log_freq_max - log_freq_min)
            )
            y = int(py_max - plot_h * (db - db_min) / (db_max - db_min))

            if px_min <= x <= px_max and py_min <= y <= py_max:
                if prev_pt is not None:
                    cv2.line(img, prev_pt, (x, y), color, 2)
                prev_pt = (x, y)

    return img


class TestParseFreqLabel(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(_parse_freq_label("200"), 200.0)

    def test_k_suffix(self):
        self.assertEqual(_parse_freq_label("1k"), 1000.0)
        self.assertEqual(_parse_freq_label("20k"), 20000.0)

    def test_k_suffix_uppercase(self):
        self.assertEqual(_parse_freq_label("5K"), 5000.0)

    def test_hz_suffix(self):
        self.assertEqual(_parse_freq_label("200Hz"), 200.0)

    def test_invalid(self):
        self.assertIsNone(_parse_freq_label("abc"))
        self.assertIsNone(_parse_freq_label(""))

    def test_zero(self):
        self.assertIsNone(_parse_freq_label("0"))


class TestParseDbLabel(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(_parse_db_label("80"), 80.0)

    def test_negative(self):
        self.assertEqual(_parse_db_label("-10"), -10.0)

    def test_with_db_suffix(self):
        self.assertEqual(_parse_db_label("80dB"), 80.0)

    def test_invalid(self):
        self.assertIsNone(_parse_db_label("abc"))


class TestAxisCalibration(unittest.TestCase):
    def test_hardcoded_calibration_roundtrip(self):
        cal = _hardcoded_klippel_calibration(600, 800)

        # Check that freq mapping roundtrips
        for freq in [20, 100, 1000, 10000, 20000]:
            px = cal.freq_to_pixel_x(freq)
            freq_back = cal.pixel_x_to_freq(px)
            self.assertAlmostEqual(freq, freq_back, places=0)

        # Check that dB mapping roundtrips
        for db in [20, 40, 60, 80, 100]:
            py = cal.db_to_pixel_y(db)
            db_back = cal.pixel_y_to_db(py)
            self.assertAlmostEqual(db, db_back, places=1)

    def test_validation_passes_for_hardcoded(self):
        cal = _hardcoded_klippel_calibration(600, 800)
        self.assertTrue(_validate_calibration(cal))

    def test_calibration_properties(self):
        cal = _hardcoded_klippel_calibration(600, 800)
        self.assertAlmostEqual(cal.freq_min, 20.0, delta=1.0)
        self.assertAlmostEqual(cal.freq_max, 20000.0, delta=100.0)
        self.assertAlmostEqual(cal.db_min, 20.0, delta=1.0)
        self.assertAlmostEqual(cal.db_max, 100.0, delta=1.0)


class TestFindClusters(unittest.TestCase):
    def test_single_cluster(self):
        col = np.zeros(100, dtype=np.uint8)
        col[40:50] = 255
        clusters = _find_clusters(col)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 10)

    def test_two_clusters(self):
        col = np.zeros(100, dtype=np.uint8)
        col[20:25] = 255
        col[70:75] = 255
        clusters = _find_clusters(col)
        self.assertEqual(len(clusters), 2)

    def test_empty(self):
        col = np.zeros(100, dtype=np.uint8)
        clusters = _find_clusters(col)
        self.assertEqual(len(clusters), 0)


class TestWeightedCentroid(unittest.TestCase):
    def test_uniform(self):
        col = np.ones(100, dtype=np.uint8) * 255
        cluster = [40, 41, 42, 43, 44]
        centroid = _weighted_centroid(col, cluster)
        self.assertAlmostEqual(centroid, 42.0, places=1)

    def test_weighted(self):
        col = np.zeros(100, dtype=np.uint8)
        col[40] = 100
        col[41] = 200
        col[42] = 100
        cluster = [40, 41, 42]
        centroid = _weighted_centroid(col, cluster)
        # Should be weighted toward index 41
        self.assertAlmostEqual(centroid, 41.0, places=1)


class TestPlotDetection(unittest.TestCase):
    def test_detect_single_plot(self):
        img = _make_synthetic_plot()
        regions = detect_plot_regions(img)
        self.assertGreaterEqual(len(regions), 1)

    def test_region_dimensions(self):
        img = _make_synthetic_plot(800, 600)
        regions = detect_plot_regions(img)
        if regions:
            region = regions[0]
            self.assertGreater(region.w, 100)
            self.assertGreater(region.h, 100)


class TestColorSegmentation(unittest.TestCase):
    def test_segment_synthetic_curves(self):
        img = _make_synthetic_plot()
        # Crop to plot area
        h, w = img.shape[:2]
        plot_img = img[int(0.05 * h) : int(0.95 * h), int(0.05 * w) : int(0.95 * w)]

        masks = segment_curves(plot_img, DEFAULT_CURVE_SPECS)
        # At least one curve should be detected (the cyan fundamental or red THD)
        self.assertGreater(len(masks), 0)


class TestCurveTracing(unittest.TestCase):
    def test_trace_synthetic_fundamental(self):
        """Trace a known curve and verify accuracy."""
        width, height = 800, 600
        cal = _hardcoded_klippel_calibration(height, width)

        # Create a mask with a horizontal line at 80 dB
        mask = np.zeros((height, width), dtype=np.uint8)
        target_db = 80.0
        y = int(cal.db_to_pixel_y(target_db))
        if 0 <= y < height:
            mask[y - 1 : y + 2, cal.plot_x_min : cal.plot_x_max] = 255

        points = trace_single_curve(mask, cal)
        self.assertGreater(len(points), 50)

        # All dB values should be close to 80
        for freq, db in points:
            self.assertAlmostEqual(db, target_db, delta=1.5)
            self.assertGreater(freq, 15)
            self.assertLess(freq, 25000)


class TestWpdJsonOutput(unittest.TestCase):
    def test_output_format(self):
        result = ExtractionResult(
            region=PlotRegion(x=0, y=0, w=800, h=600, title="Test"),
            calibration=_hardcoded_klippel_calibration(600, 800),
            curves={
                "Fundamental": [(100.0, 85.0), (1000.0, 80.0), (10000.0, 75.0)],
                "THD": [(100.0, 55.0), (1000.0, 50.0), (10000.0, 45.0)],
            },
        )

        wpd = curves_to_wpd_json([result])
        self.assertIn("datasetColl", wpd)
        self.assertEqual(len(wpd["datasetColl"]), 2)

        for ds in wpd["datasetColl"]:
            self.assertIn("name", ds)
            self.assertIn("data", ds)
            for d in ds["data"]:
                self.assertIn("value", d)
                self.assertEqual(len(d["value"]), 2)

    def test_compatible_with_load_wpd(self):
        """Verify output can be parsed by parse_graph_freq_webplotdigitizer."""
        from spinorama.loaders.webplotdigitizer import parse_graph_freq_webplotdigitizer

        result = ExtractionResult(
            region=PlotRegion(x=0, y=0, w=800, h=600),
            calibration=_hardcoded_klippel_calibration(600, 800),
            curves={
                "On Axis": [
                    (float(f), 85.0 - 5.0 * abs(math.log10(f / 1000)))
                    for f in np.logspace(math.log10(20), math.log10(20000), 100)
                ],
            },
        )

        wpd = curves_to_wpd_json([result])

        # Write to temp file and parse
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(wpd, f)
            tmp_path = f.name

        try:
            status, (graph_type, df) = parse_graph_freq_webplotdigitizer(tmp_path)
            self.assertTrue(status)
            self.assertGreater(len(df), 0)
            self.assertIn("Freq", df.columns)
            self.assertIn("dB", df.columns)
        finally:
            Path(tmp_path).unlink()


if __name__ == "__main__":
    unittest.main()
