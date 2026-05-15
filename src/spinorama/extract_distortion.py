# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.extract.distortion``."""
from spinorama.extract.distortion import (
    AxisCalibration,
    CurveColorSpec,
    DEFAULT_CURVE_SPECS,
    ExtractionResult,
    Path,
    PlotRegion,
    calibrate_axes,
    curves_to_wpd_json,
    dataclass,
    detect_plot_regions,
    extract_curves,
    extract_curves_to_file,
    field,
    logger,
    segment_curves,
    trace_curves,
)

__all__ = [
    'AxisCalibration', 'CurveColorSpec', 'DEFAULT_CURVE_SPECS', 'ExtractionResult', 'Path', 'PlotRegion', 'calibrate_axes', 'curves_to_wpd_json', 'dataclass', 'detect_plot_regions', 'extract_curves', 'extract_curves_to_file', 'field', 'logger', 'segment_curves', 'trace_curves',
]
