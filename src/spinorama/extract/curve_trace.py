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

"""Curve tracing: column-sweep extraction with subpixel accuracy, WPD JSON output."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from spinorama import logger

if TYPE_CHECKING:
    from spinorama.extract_axis_calibrate import AxisCalibration
    from spinorama.extract_distortion import ExtractionResult


def _find_clusters(column: npt.NDArray, min_gap: int = 3) -> list[list[int]]:
    """Find contiguous clusters of nonzero pixels in a column."""
    on_pixels = np.nonzero(column)[0]
    if len(on_pixels) == 0:
        return []

    clusters: list[list[int]] = [[int(on_pixels[0])]]
    for px in on_pixels[1:]:
        if px - clusters[-1][-1] <= min_gap:
            clusters[-1].append(int(px))
        else:
            clusters.append([int(px)])

    return clusters


def _weighted_centroid(column: npt.NDArray, cluster: list[int]) -> float:
    """Compute intensity-weighted centroid for subpixel accuracy."""
    if not cluster:
        return 0.0

    intensities = column[cluster].astype(float)
    total = np.sum(intensities)
    if total == 0:
        return float(np.mean(cluster))

    return float(np.sum(np.array(cluster, dtype=float) * intensities) / total)


def _extrapolate_position(recent_positions: list[float]) -> float | None:
    """Linear extrapolation from recent positions to predict next position."""
    if len(recent_positions) < 2:
        return None

    # Use last 5 points for extrapolation
    pts = recent_positions[-5:]
    if len(pts) < 2:
        return None

    # Simple linear extrapolation
    n = len(pts)
    xs = list(range(n))
    slope = (pts[-1] - pts[0]) / (n - 1) if n > 1 else 0
    return pts[-1] + slope


def _select_cluster(
    clusters: list[list[int]],
    column: npt.NDArray,
    recent_positions: list[float],
) -> float | None:
    """Select the best cluster when multiple are found.

    Returns subpixel y position or None.
    """
    if not clusters:
        return None

    centroids = [_weighted_centroid(column, c) for c in clusters]

    if len(centroids) == 1:
        return centroids[0]

    # Multiple clusters: pick closest to extrapolated position
    predicted = _extrapolate_position(recent_positions)
    if predicted is not None:
        distances = [abs(c - predicted) for c in centroids]
        return centroids[int(np.argmin(distances))]

    # No prediction available: pick the largest cluster
    sizes = [len(c) for c in clusters]
    return centroids[int(np.argmax(sizes))]


def _smooth_curve(
    points: list[tuple[float, float]], window: int = 5, order: int = 2
) -> list[tuple[float, float]]:
    """Apply Savitzky-Golay smoothing to the curve."""
    if len(points) < window:
        return points

    try:
        from scipy.signal import savgol_filter

        freqs = [p[0] for p in points]
        dbs = np.array([p[1] for p in points])
        smoothed = savgol_filter(dbs, window, order)
        return list(zip(freqs, smoothed.tolist()))
    except ImportError:
        logger.debug("scipy not available, skipping smoothing")
        return points


def trace_single_curve(
    mask: npt.NDArray,
    calibration: AxisCalibration,
) -> list[tuple[float, float]]:
    """Trace a single curve from its binary mask.

    Args:
        mask: Binary mask (h x w) with nonzero pixels on the curve.
        calibration: Pixel-to-physical coordinate mapping.

    Returns:
        List of (freq_hz, dB) points sorted by frequency.
    """
    h, w = mask.shape[:2]
    points: list[tuple[float, float]] = []
    recent_y_positions: list[float] = []

    x_start = max(0, calibration.plot_x_min)
    x_end = min(w, calibration.plot_x_max)

    for col_x in range(x_start, x_end):
        column = mask[:, col_x]
        clusters = _find_clusters(column)

        y_pos = _select_cluster(clusters, column, recent_y_positions)
        if y_pos is None:
            continue

        # Clamp to plot area
        if y_pos < calibration.plot_y_min or y_pos > calibration.plot_y_max:
            continue

        freq = calibration.pixel_x_to_freq(col_x)
        db = calibration.pixel_y_to_db(y_pos)

        # Sanity check
        if 10 <= freq <= 30000 and -50 < db < 200:
            points.append((freq, db))
            recent_y_positions.append(y_pos)

    # Smooth if we have enough points
    if len(points) > 10:
        points = _smooth_curve(points)

    return points


def trace_curves(
    masks: dict[str, npt.NDArray],
    calibration: AxisCalibration,
    debug: bool = False,
) -> dict[str, list[tuple[float, float]]]:
    """Trace all curves from their masks.

    Returns:
        Dict mapping curve name to list of (freq_hz, dB) points.
    """
    curves: dict[str, list[tuple[float, float]]] = {}

    for name, mask in masks.items():
        points = trace_single_curve(mask, calibration)
        if points:
            curves[name] = points
            logger.info("Traced curve '%s': %d points", name, len(points))
        else:
            logger.warning("No points traced for curve '%s'", name)

    return curves


def curves_to_wpd_json(results: list[ExtractionResult]) -> dict:
    """Convert extraction results to WPD-compatible JSON format.

    The output matches the datasetColl format used by WebPlotDigitizer:
    {
        "datasetColl": [
            {
                "name": "Curve Name",
                "data": [
                    {"value": [freq_hz, dB]},
                    ...
                ]
            },
            ...
        ]
    }
    """
    dataset_coll: list[dict] = []

    for result in results:
        title_prefix = f"{result.region.title} - " if result.region.title else ""

        for curve_name, points in result.curves.items():
            data = [{"value": [freq, db]} for freq, db in points]
            dataset_coll.append(
                {
                    "name": f"{title_prefix}{curve_name}",
                    "data": data,
                }
            )

    return {"datasetColl": dataset_coll}
