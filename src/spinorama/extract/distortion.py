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

"""Orchestrator: extract distortion curves from Klippel graph images to WPD JSON."""

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from spinorama import logger
from spinorama.extract_plot_detect import PlotRegion, detect_plot_regions
from spinorama.extract_axis_calibrate import AxisCalibration, calibrate_axes
from spinorama.extract_color_segment import CurveColorSpec, DEFAULT_CURVE_SPECS, segment_curves
from spinorama.extract_curve_trace import trace_curves, curves_to_wpd_json


@dataclass
class ExtractionResult:
    """Result of extracting curves from one plot region."""

    region: PlotRegion
    calibration: AxisCalibration
    curves: dict[str, list[tuple[float, float]]]
    debug_images: dict[str, npt.NDArray] = field(default_factory=dict)


def extract_curves(
    image_path: str | Path,
    curve_specs: list[CurveColorSpec] | None = None,
    debug: bool = False,
) -> dict:
    """Extract distortion curves from a Klippel graph image.

    Args:
        image_path: Path to the input image (PNG/JPEG).
        curve_specs: Optional list of color specs for curves to extract.
        debug: If True, populate debug_images in results.

    Returns:
        WPD-compatible JSON dict with datasetColl format.
    """
    image_path = Path(image_path)
    img = cv2.imread(str(image_path))
    if img is None:
        msg = f"Cannot read image: {image_path}"
        raise FileNotFoundError(msg)

    if curve_specs is None:
        curve_specs = DEFAULT_CURVE_SPECS

    regions = detect_plot_regions(img, debug=debug)
    if not regions:
        msg = f"No plot regions detected in {image_path}"
        raise ValueError(msg)

    logger.info("Detected %d plot region(s) in %s", len(regions), image_path.name)

    all_results: list[ExtractionResult] = []
    for region in regions:
        plot_img = img[region.y : region.y + region.h, region.x : region.x + region.w]

        calibration = calibrate_axes(plot_img, region, debug=debug)
        logger.info(
            "Calibrated axes: freq=[%.0f, %.0f] Hz, dB=[%.1f, %.1f]",
            calibration.freq_min,
            calibration.freq_max,
            calibration.db_min,
            calibration.db_max,
        )

        masks = segment_curves(plot_img, curve_specs, debug=debug)

        curves = trace_curves(masks, calibration, debug=debug)

        result = ExtractionResult(
            region=region,
            calibration=calibration,
            curves=curves,
        )
        all_results.append(result)

    return curves_to_wpd_json(all_results)


def extract_curves_to_file(
    image_path: str | Path,
    output_path: str | Path | None = None,
    curve_specs: list[CurveColorSpec] | None = None,
    debug: bool = False,
    debug_dir: str | Path | None = None,
) -> Path:
    """Extract curves and write WPD JSON to a file.

    Returns:
        Path to the output JSON file.
    """
    import json

    image_path = Path(image_path)
    if output_path is None:
        output_path = image_path.with_suffix(".json")
    else:
        output_path = Path(output_path)

    wpd_json = extract_curves(image_path, curve_specs=curve_specs, debug=debug)

    with open(output_path, "w") as f:
        json.dump(wpd_json, f, indent=2)

    logger.info("Wrote WPD JSON to %s", output_path)

    if debug and debug_dir:
        debug_dir = Path(debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Debug images would be saved to %s", debug_dir)

    return output_path
