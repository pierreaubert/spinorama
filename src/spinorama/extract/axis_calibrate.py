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

"""Axis calibration: OCR tick labels and map pixel coordinates to (freq_Hz, dB)."""

import math
import re
from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from spinorama import logger
from spinorama.extract.plot_detect import PlotRegion

# Standard Klippel frequency tick values
STANDARD_FREQ_TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
# Standard dB tick values (typical range)
STANDARD_DB_TICKS = list(range(0, 120, 10))


@dataclass
class AxisCalibration:
    """Pixel-to-physical coordinate mapping for a plot region."""

    # Linear mapping: pixel_x = a * log10(freq) + b
    log_freq_a: float
    log_freq_b: float
    # Linear mapping: pixel_y = c * dB + d
    db_c: float
    db_d: float
    # Plot area bounds in pixels (relative to plot_img)
    plot_x_min: int
    plot_x_max: int
    plot_y_min: int
    plot_y_max: int

    @property
    def freq_min(self) -> float:
        return self.pixel_x_to_freq(self.plot_x_min)

    @property
    def freq_max(self) -> float:
        return self.pixel_x_to_freq(self.plot_x_max)

    @property
    def db_min(self) -> float:
        return self.pixel_y_to_db(self.plot_y_max)

    @property
    def db_max(self) -> float:
        return self.pixel_y_to_db(self.plot_y_min)

    def pixel_x_to_freq(self, px: float) -> float:
        log_f = (px - self.log_freq_b) / self.log_freq_a
        return 10.0**log_f

    def pixel_y_to_db(self, py: float) -> float:
        return (py - self.db_d) / self.db_c

    def freq_to_pixel_x(self, freq: float) -> float:
        return self.log_freq_a * math.log10(freq) + self.log_freq_b

    def db_to_pixel_y(self, db: float) -> float:
        return self.db_c * db + self.db_d


def _parse_freq_label(text: str) -> float | None:
    """Parse a frequency label like '1k', '200', '20k' into Hz."""
    text = text.strip().lower().replace(",", "").replace(" ", "")
    # Remove 'hz' suffix if present
    text = re.sub(r"hz$", "", text)

    match = re.match(r"^(\d+\.?\d*)\s*k$", text)
    if match:
        return float(match.group(1)) * 1000.0

    match = re.match(r"^(\d+\.?\d*)$", text)
    if match:
        val = float(match.group(1))
        if val > 0:
            return val
    return None


def _parse_db_label(text: str) -> float | None:
    """Parse a dB label like '80', '-10', '100' into dB value."""
    text = text.strip().lower().replace("db", "").replace(" ", "")
    match = re.match(r"^-?\d+\.?\d*$", text)
    if match:
        return float(text)
    return None


def _ocr_axis_labels(
    plot_img: npt.NDArray,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """OCR x-axis and y-axis tick labels.

    Returns:
        (x_ticks, y_ticks) where each is a list of (pixel_position, physical_value).
    """
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract not available, falling back to grid detection")
        return [], []

    h, w = plot_img.shape[:2]
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY) if len(plot_img.shape) == 3 else plot_img

    x_ticks: list[tuple[int, float]] = []
    y_ticks: list[tuple[int, float]] = []

    # X-axis: bottom strip (last 12% of height)
    x_strip_h = int(0.12 * h)
    x_strip = gray[h - x_strip_h :, :]

    try:
        # Use word-level detection
        x_data = pytesseract.image_to_data(
            x_strip,
            config="--psm 6 -c tessedit_char_whitelist=0123456789.kK",
            output_type=pytesseract.Output.DICT,
        )
        for i, text in enumerate(x_data["text"]):
            if not text.strip():
                continue
            freq = _parse_freq_label(text)
            if freq is not None and 10 <= freq <= 30000:
                cx = x_data["left"][i] + x_data["width"][i] // 2
                x_ticks.append((cx, freq))
                logger.debug("X tick: pixel=%d, freq=%.0f Hz", cx, freq)
    except Exception:
        logger.debug("X-axis OCR failed")

    # Y-axis: left strip (first 10% of width)
    y_strip_w = int(0.10 * w)
    y_strip = gray[:, :y_strip_w]

    try:
        y_data = pytesseract.image_to_data(
            y_strip,
            config="--psm 6 -c tessedit_char_whitelist=0123456789-.",
            output_type=pytesseract.Output.DICT,
        )
        for i, text in enumerate(y_data["text"]):
            if not text.strip():
                continue
            db = _parse_db_label(text)
            if db is not None and -50 <= db <= 150:
                cy = y_data["top"][i] + y_data["height"][i] // 2
                y_ticks.append((cy, db))
                logger.debug("Y tick: pixel=%d, dB=%.1f", cy, db)
    except Exception:
        logger.debug("Y-axis OCR failed")

    return x_ticks, y_ticks


def _detect_grid_lines(plot_img: npt.NDArray) -> tuple[list[int], list[int]]:
    """Detect grid lines using Hough transform.

    Returns:
        (vertical_x_positions, horizontal_y_positions) in pixels.
    """
    h, w = plot_img.shape[:2]
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY) if len(plot_img.shape) == 3 else plot_img

    edges = cv2.Canny(gray, 30, 100)

    # Detect lines
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=50, minLineLength=int(0.3 * min(h, w)), maxLineGap=5
    )

    vertical_xs: list[int] = []
    horizontal_ys: list[int] = []

    if lines is None:
        return vertical_xs, horizontal_ys

    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dx < 3 and dy > 0.2 * h:
            # Vertical line
            vertical_xs.append((x1 + x2) // 2)
        elif dy < 3 and dx > 0.2 * w:
            # Horizontal line
            horizontal_ys.append((y1 + y2) // 2)

    # Cluster nearby lines
    vertical_xs = _cluster_positions(sorted(vertical_xs), min_gap=int(0.02 * w))
    horizontal_ys = _cluster_positions(sorted(horizontal_ys), min_gap=int(0.02 * h))

    return vertical_xs, horizontal_ys


def _cluster_positions(positions: list[int], min_gap: int = 10) -> list[int]:
    """Cluster nearby positions and return centroids."""
    if not positions:
        return []

    clusters: list[list[int]] = [[positions[0]]]
    for p in positions[1:]:
        if p - clusters[-1][-1] < min_gap:
            clusters[-1].append(p)
        else:
            clusters.append([p])

    return [int(np.mean(c)) for c in clusters]


def _fit_log_linear(
    tick_pixels: list[int], tick_values: list[float] | list[int], log_scale: bool = False
) -> tuple[float, float]:
    """Fit a linear model: pixel = a * value + b (or a * log10(value) + b if log_scale)."""
    if log_scale:
        values = [math.log10(v) for v in tick_values]
    else:
        values = list(tick_values)

    A = np.column_stack([values, np.ones(len(values))])
    pixels = np.array(tick_pixels, dtype=float)

    result, _, _, _ = np.linalg.lstsq(A, pixels, rcond=None)
    return float(result[0]), float(result[1])


def _hardcoded_klippel_calibration(h: int, w: int) -> AxisCalibration:
    """Last-resort calibration using known Klippel layout ratios."""
    # Typical Klippel plot: plot area at ~12%/8% to ~92%/88% of region
    plot_x_min = int(0.12 * w)
    plot_x_max = int(0.92 * w)
    plot_y_min = int(0.08 * h)
    plot_y_max = int(0.88 * h)

    # Standard range: 20 Hz to 20 kHz on x, 20 to 100 dB on y
    log_freq_min = math.log10(20)
    log_freq_max = math.log10(20000)
    db_min_val = 20.0
    db_max_val = 100.0

    plot_w = plot_x_max - plot_x_min
    plot_h = plot_y_max - plot_y_min

    a = plot_w / (log_freq_max - log_freq_min)
    b = plot_x_min - a * log_freq_min
    c = -plot_h / (db_max_val - db_min_val)  # negative because y increases downward
    d = plot_y_min - c * db_max_val

    return AxisCalibration(
        log_freq_a=a,
        log_freq_b=b,
        db_c=c,
        db_d=d,
        plot_x_min=plot_x_min,
        plot_x_max=plot_x_max,
        plot_y_min=plot_y_min,
        plot_y_max=plot_y_max,
    )


def _validate_calibration(
    cal: AxisCalibration,
    freq_range: tuple[float, float, float, float] = (5, 100, 10000, 30000),
    db_range: tuple[float, float, float, float] = (-20, 50, 60, 130),
) -> bool:
    """Check that calibration produces reasonable values.

    Args:
        cal: The calibration to validate.
        freq_range: (freq_min_lo, freq_min_hi, freq_max_lo, freq_max_hi) bounds.
        db_range: (db_min_lo, db_min_hi, db_max_lo, db_max_hi) bounds.
    """
    freq_min = cal.freq_min
    freq_max = cal.freq_max
    db_min = cal.db_min
    db_max = cal.db_max

    freq_min_lo, freq_min_hi, freq_max_lo, freq_max_hi = freq_range
    db_min_lo, db_min_hi, db_max_lo, db_max_hi = db_range

    if not (freq_min_lo <= freq_min <= freq_min_hi):
        logger.warning("Suspicious freq_min: %.1f Hz", freq_min)
        return False
    if not (freq_max_lo <= freq_max <= freq_max_hi):
        logger.warning("Suspicious freq_max: %.1f Hz", freq_max)
        return False
    if not (db_min_lo <= db_min <= db_min_hi):
        logger.warning("Suspicious db_min: %.1f dB", db_min)
        return False
    if not (db_max_lo <= db_max <= db_max_hi):
        logger.warning("Suspicious db_max: %.1f dB", db_max)
        return False

    # Check monotonicity
    if cal.log_freq_a <= 0:
        logger.warning("Non-monotonic frequency mapping (a=%.2f)", cal.log_freq_a)
        return False
    if cal.db_c >= 0:
        logger.warning("Non-monotonic dB mapping (c=%.2f)", cal.db_c)
        return False

    return True


def calibration_from_plotly_layout(
    layout: dict,
    img_w: int,
    img_h: int,
    yaxis_key: str = "yaxis",
) -> AxisCalibration:
    """Build an oracle AxisCalibration from Plotly layout metadata.

    This gives perfect calibration by using the exact axis ranges and margins
    from the Plotly JSON, bypassing OCR/grid detection entirely.

    Args:
        layout: The 'layout' dict from a Plotly JSON file.
        img_w: Width of the rendered PNG in pixels.
        img_h: Height of the rendered PNG in pixels.
        yaxis_key: Layout key for the y-axis ('yaxis' or 'yaxis2').

    Returns:
        AxisCalibration with exact pixel-to-physical mapping.
    """
    margin = layout.get("margin", {})
    margin_l = margin.get("l", 80)
    margin_r = margin.get("r", 80)
    margin_t = margin.get("t", 100)
    margin_b = margin.get("b", 80)

    plot_x_min = margin_l
    plot_x_max = img_w - margin_r
    plot_y_min = margin_t
    plot_y_max = img_h - margin_b

    plot_w = plot_x_max - plot_x_min
    plot_h = plot_y_max - plot_y_min

    # X axis: log10 scale
    xaxis = layout.get("xaxis", {})
    x_range = xaxis.get("range", [math.log10(20), math.log10(20000)])
    log_freq_min = x_range[0]
    log_freq_max = x_range[1]

    # Y axis: linear dB scale
    yaxis = layout.get(yaxis_key, {})
    y_range = yaxis.get("range", [-45, 5])
    db_min_val = y_range[0]
    db_max_val = y_range[1]

    # pixel_x = a * log10(freq) + b
    a = plot_w / (log_freq_max - log_freq_min)
    b = plot_x_min - a * log_freq_min

    # pixel_y = c * dB + d  (negative c because y increases downward)
    c = -plot_h / (db_max_val - db_min_val)
    d = plot_y_min - c * db_max_val

    return AxisCalibration(
        log_freq_a=a,
        log_freq_b=b,
        db_c=c,
        db_d=d,
        plot_x_min=plot_x_min,
        plot_x_max=plot_x_max,
        plot_y_min=plot_y_min,
        plot_y_max=plot_y_max,
    )


def calibrate_axes(
    plot_img: npt.NDArray,
    region: PlotRegion,
    debug: bool = False,
) -> AxisCalibration:
    """Calibrate axes for a detected plot region.

    Tries OCR first, then grid line detection, then hardcoded fallback.
    """
    h, w = plot_img.shape[:2]

    # Primary: OCR
    x_ticks, y_ticks = _ocr_axis_labels(plot_img)

    if len(x_ticks) >= 3 and len(y_ticks) >= 2:
        try:
            a, b = _fit_log_linear([t[0] for t in x_ticks], [t[1] for t in x_ticks], log_scale=True)
            c, d = _fit_log_linear(
                [t[0] for t in y_ticks], [t[1] for t in y_ticks], log_scale=False
            )

            # Estimate plot bounds from tick positions
            x_pixels = [t[0] for t in x_ticks]
            y_pixels = [t[0] for t in y_ticks]

            cal = AxisCalibration(
                log_freq_a=a,
                log_freq_b=b,
                db_c=c,
                db_d=d,
                plot_x_min=min(x_pixels),
                plot_x_max=max(x_pixels),
                plot_y_min=min(y_pixels),
                plot_y_max=max(y_pixels),
            )

            if _validate_calibration(cal):
                logger.info("Calibration via OCR successful")
                return cal
            logger.warning("OCR calibration failed validation, trying fallback")
        except Exception:
            logger.debug("OCR calibration fitting failed")

    # Fallback: Grid line detection
    vert_xs, horiz_ys = _detect_grid_lines(plot_img)

    if len(vert_xs) >= 3 and len(horiz_ys) >= 2:
        # Try to match grid lines to standard decade/10dB spacing
        # Assume standard frequency ticks aligned to detected vertical lines
        n_vert = len(vert_xs)
        if n_vert <= len(STANDARD_FREQ_TICKS):
            # Select evenly-spaced standard ticks
            step = max(1, len(STANDARD_FREQ_TICKS) // n_vert)
            matched_freqs = STANDARD_FREQ_TICKS[::step][:n_vert]

            try:
                a, b = _fit_log_linear(vert_xs, matched_freqs, log_scale=True)

                # For y-axis, assume 10dB spacing
                n_horiz = len(horiz_ys)
                db_top = 100.0
                matched_dbs = [db_top - i * 10.0 for i in range(n_horiz)]

                c, d = _fit_log_linear(horiz_ys, matched_dbs, log_scale=False)

                cal = AxisCalibration(
                    log_freq_a=a,
                    log_freq_b=b,
                    db_c=c,
                    db_d=d,
                    plot_x_min=vert_xs[0],
                    plot_x_max=vert_xs[-1],
                    plot_y_min=horiz_ys[0],
                    plot_y_max=horiz_ys[-1],
                )

                if _validate_calibration(cal):
                    logger.info("Calibration via grid detection successful")
                    return cal
            except Exception:
                logger.debug("Grid-based calibration failed")

    # Last resort: hardcoded Klippel layout
    logger.info("Using hardcoded Klippel layout calibration")
    return _hardcoded_klippel_calibration(h, w)
