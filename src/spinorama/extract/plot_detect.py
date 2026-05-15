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

"""Plot region detection: find and crop individual sub-plots from Klippel images."""

from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from spinorama import logger


@dataclass
class PlotRegion:
    """A detected plot region within the image."""

    x: int
    y: int
    w: int
    h: int
    title: str = ""


def _find_contour_regions(
    gray: npt.NDArray, img_area: int, min_area_ratio: float = 0.10
) -> list[PlotRegion]:
    """Find large rectangular contours that represent plot areas."""
    # Threshold for near-white background
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    # Invert so plot area is white
    thresh_inv = cv2.bitwise_not(thresh)

    # Find contours
    contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < img_area * min_area_ratio:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0

        # Klippel plots have aspect ratio roughly 1.0 to 2.5
        if 0.8 <= aspect <= 3.0:
            regions.append(PlotRegion(x=x, y=y, w=w, h=h))

    # Sort left to right
    regions.sort(key=lambda r: r.x)
    return regions


def _vertical_split_fallback(img: npt.NDArray) -> list[PlotRegion]:
    """Split image vertically at the point of minimal horizontal gradient in center third."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # Look in center third for a vertical split
    center_start = w // 3
    center_end = 2 * w // 3

    # Compute column-wise intensity variance
    col_var = np.var(gray[:, center_start:center_end].astype(float), axis=0)

    # Find the column with minimum variance (likely a gap between plots)
    min_col = center_start + int(np.argmin(col_var))

    # Check if there's a meaningful gap (high variance columns on both sides)
    left_var = np.mean(col_var[: len(col_var) // 3])
    right_var = np.mean(col_var[2 * len(col_var) // 3 :])
    gap_var = col_var[min_col - center_start]

    if gap_var < 0.5 * min(left_var, right_var):
        # Significant gap found - split into two plots
        margin = int(0.02 * h)
        return [
            PlotRegion(x=0, y=margin, w=min_col - margin, h=h - 2 * margin),
            PlotRegion(x=min_col + margin, y=margin, w=w - min_col - 2 * margin, h=h - 2 * margin),
        ]

    # No clear split - treat as single plot with margin
    margin_x = int(0.05 * w)
    margin_y = int(0.05 * h)
    return [PlotRegion(x=margin_x, y=margin_y, w=w - 2 * margin_x, h=h - 2 * margin_y)]


def _ocr_title(img: npt.NDArray, region: PlotRegion) -> str:
    """Try to OCR a title above the plot region."""
    try:
        import pytesseract
    except ImportError:
        return ""

    # Look above the plot region for title text
    title_h = min(region.y, int(0.08 * img.shape[0]))
    if title_h < 10:
        return ""

    title_roi = img[max(0, region.y - title_h) : region.y, region.x : region.x + region.w]
    if title_roi.size == 0:
        return ""

    gray = cv2.cvtColor(title_roi, cv2.COLOR_BGR2GRAY) if len(title_roi.shape) == 3 else title_roi
    try:
        text = pytesseract.image_to_string(gray, config="--psm 7").strip()
        return text
    except Exception:
        logger.debug("OCR title extraction failed")
        return ""


def detect_plot_regions(img: npt.NDArray, debug: bool = False) -> list[PlotRegion]:
    """Detect plot regions in a Klippel distortion graph image.

    Args:
        img: BGR image array.
        debug: If True, log additional debug info.

    Returns:
        List of PlotRegion objects sorted left-to-right.
    """
    h, w = img.shape[:2]
    img_area = h * w

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Try contour-based detection first
    regions = _find_contour_regions(gray, img_area)

    if not regions:
        logger.info("Contour detection failed, trying vertical split fallback")
        regions = _vertical_split_fallback(img)

    # Try to OCR titles
    for region in regions:
        region.title = _ocr_title(img, region)
        if region.title:
            logger.debug("Plot title: '%s'", region.title)

    logger.info("Detected %d plot region(s)", len(regions))
    return regions
