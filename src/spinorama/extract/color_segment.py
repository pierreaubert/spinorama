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

"""Color segmentation: HSV masks per curve, grid/watermark removal."""

from dataclasses import dataclass, field

import cv2
import numpy as np
import numpy.typing as npt

from spinorama import logger


@dataclass
class CurveColorSpec:
    """HSV color specification for a distortion curve."""

    name: str
    hsv_ranges: list[tuple[tuple[int, int, int], tuple[int, int, int]]]
    remove_grid_first: bool = False


# Default Klippel distortion curve color specs
DEFAULT_CURVE_SPECS = [
    CurveColorSpec(
        name="Fundamental",
        hsv_ranges=[((80, 100, 100), (100, 255, 255))],
    ),
    CurveColorSpec(
        name="THD",
        hsv_ranges=[
            ((0, 120, 150), (10, 255, 255)),
            ((170, 120, 150), (180, 255, 255)),
        ],
    ),
    CurveColorSpec(
        name="2nd Harmonic",
        hsv_ranges=[((0, 80, 40), (20, 200, 140))],
    ),
    CurveColorSpec(
        name="3rd Harmonic",
        hsv_ranges=[((100, 100, 80), (130, 255, 255))],
    ),
    CurveColorSpec(
        name="4th Harmonic",
        hsv_ranges=[((0, 0, 80), (180, 40, 180))],
        remove_grid_first=True,
    ),
    CurveColorSpec(
        name="5th Harmonic",
        hsv_ranges=[((30, 60, 60), (80, 255, 200))],
    ),
]


def _detect_grid_mask(plot_img: npt.NDArray) -> npt.NDArray:
    """Create a mask of grid lines using Hough line detection."""
    h, w = plot_img.shape[:2]
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY) if len(plot_img.shape) == 3 else plot_img

    edges = cv2.Canny(gray, 30, 100)

    grid_mask = np.zeros((h, w), dtype=np.uint8)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=50,
        minLineLength=int(0.3 * min(h, w)),
        maxLineGap=5,
    )

    if lines is not None:
        for line in lines:
            # OpenCV returns either (N, 1, 4) or (N, 4), depending on version.
            x1, y1, x2, y2 = np.asarray(line).reshape(-1)
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            # Only axis-aligned lines (vertical or horizontal)
            if dx < 3 or dy < 3:
                # Draw with thickness to cover the grid line width
                cv2.line(grid_mask, (x1, y1), (x2, y2), 255, 3)

    # Dilate slightly to cover anti-aliased edges
    kernel = np.ones((3, 3), np.uint8)
    grid_mask = cv2.dilate(grid_mask, kernel, iterations=1)

    return grid_mask


def _create_watermark_mask(h: int, w: int) -> npt.NDArray:
    """Create a mask for known watermark/logo regions."""
    mask = np.zeros((h, w), dtype=np.uint8)

    # Mask bottom 5% for watermarks
    watermark_y = int(0.95 * h)
    mask[watermark_y:, :] = 255

    return mask


def _sample_legend_colors(plot_img: npt.NDArray) -> dict[str, tuple[int, int, int]] | None:
    """Try to sample legend color swatches at top of plot for adaptive calibration."""
    h, w = plot_img.shape[:2]
    hsv = cv2.cvtColor(plot_img, cv2.COLOR_BGR2HSV)

    # Legend is typically in the top 10% of the plot
    legend_region = hsv[: int(0.10 * h), :]

    if legend_region.size == 0:
        return None

    # Look for small colored rectangles (legend swatches)
    # This is a simplified approach - in practice might need more sophistication
    gray = cv2.cvtColor(plot_img[: int(0.10 * h), :], cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    colors: dict[str, tuple[int, int, int]] = {}
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        # Legend swatches are small squares/rectangles
        if 5 < cw < 40 and 3 < ch < 20 and 0.3 < cw / ch < 5.0:
            # Sample the center of the swatch
            cx = x + cw // 2
            cy = y + ch // 2
            hsv_val = legend_region[cy, cx]
            h_val, s_val, v_val = int(hsv_val[0]), int(hsv_val[1]), int(hsv_val[2])
            colors[f"swatch_{len(colors)}"] = (h_val, s_val, v_val)

    return colors if colors else None


def _apply_hsv_mask(
    hsv_img: npt.NDArray,
    spec: CurveColorSpec,
    grid_mask: npt.NDArray | None = None,
    watermark_mask: npt.NDArray | None = None,
) -> npt.NDArray:
    """Create a binary mask for a specific curve color."""
    h, w = hsv_img.shape[:2]
    combined_mask = np.zeros((h, w), dtype=np.uint8)

    for lower, upper in spec.hsv_ranges:
        lower_np = np.array(lower, dtype=np.uint8)
        upper_np = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv_img, lower_np, upper_np)
        combined_mask = cv2.bitwise_or(combined_mask, mask)

    # Remove grid lines for curves that need it (e.g., gray)
    if spec.remove_grid_first and grid_mask is not None:
        combined_mask = cv2.bitwise_and(combined_mask, cv2.bitwise_not(grid_mask))

    # Remove watermark regions
    if watermark_mask is not None:
        combined_mask = cv2.bitwise_and(combined_mask, cv2.bitwise_not(watermark_mask))

    # Clean up noise with morphological operations
    kernel_size = max(2, int(0.003 * min(h, w)))
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

    return combined_mask


def segment_curves(
    plot_img: npt.NDArray,
    curve_specs: list[CurveColorSpec],
    debug: bool = False,
) -> dict[str, npt.NDArray]:
    """Segment the plot image into per-curve binary masks.

    Args:
        plot_img: BGR image of the plot region.
        curve_specs: Color specifications for each curve.
        debug: If True, log additional info.

    Returns:
        Dict mapping curve name to binary mask.
    """
    h, w = plot_img.shape[:2]
    hsv = cv2.cvtColor(plot_img, cv2.COLOR_BGR2HSV)

    grid_mask = _detect_grid_mask(plot_img)
    watermark_mask = _create_watermark_mask(h, w)

    # Try adaptive calibration from legend
    _sample_legend_colors(plot_img)

    masks: dict[str, npt.NDArray] = {}
    for spec in curve_specs:
        mask = _apply_hsv_mask(hsv, spec, grid_mask=grid_mask, watermark_mask=watermark_mask)
        pixel_count = int(np.sum(mask > 0))
        if pixel_count > 0:
            masks[spec.name] = mask
            logger.debug("Curve '%s': %d pixels detected", spec.name, pixel_count)
        else:
            logger.debug("Curve '%s': no pixels detected", spec.name)

    return masks
