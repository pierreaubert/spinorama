# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.extract.axis_calibrate``."""
from spinorama.extract.axis_calibrate import (
    AxisCalibration,
    PlotRegion,
    STANDARD_DB_TICKS,
    STANDARD_FREQ_TICKS,
    _cluster_positions,
    _detect_grid_lines,
    _fit_log_linear,
    _hardcoded_klippel_calibration,
    _ocr_axis_labels,
    _parse_db_label,
    _parse_freq_label,
    _validate_calibration,
    calibrate_axes,
    calibration_from_plotly_layout,
    dataclass,
    logger,
)

__all__ = [
    'AxisCalibration', 'PlotRegion', 'STANDARD_DB_TICKS', 'STANDARD_FREQ_TICKS', '_cluster_positions', '_detect_grid_lines', '_fit_log_linear', '_hardcoded_klippel_calibration', '_ocr_axis_labels', '_parse_db_label', '_parse_freq_label', '_validate_calibration', 'calibrate_axes', 'calibration_from_plotly_layout', 'dataclass', 'logger',
]
