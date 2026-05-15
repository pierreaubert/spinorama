# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.extract.color_segment``."""
from spinorama.extract.color_segment import (
    CurveColorSpec,
    DEFAULT_CURVE_SPECS,
    _apply_hsv_mask,
    _create_watermark_mask,
    _detect_grid_mask,
    _sample_legend_colors,
    dataclass,
    field,
    logger,
    segment_curves,
)

__all__ = [
    'CurveColorSpec', 'DEFAULT_CURVE_SPECS', '_apply_hsv_mask', '_create_watermark_mask', '_detect_grid_mask', '_sample_legend_colors', 'dataclass', 'field', 'logger', 'segment_curves',
]
