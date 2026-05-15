# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.extract.plot_detect``."""
from spinorama.extract.plot_detect import (
    PlotRegion,
    _find_contour_regions,
    _ocr_title,
    _vertical_split_fallback,
    dataclass,
    detect_plot_regions,
    logger,
)

__all__ = [
    'PlotRegion', '_find_contour_regions', '_ocr_title', '_vertical_split_fallback', 'dataclass', 'detect_plot_regions', 'logger',
]
