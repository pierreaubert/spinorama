# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.compute.misc``."""
from spinorama.compute.misc import (
    DIRECTIVITY_MAX_FREQ,
    DIRECTIVITY_MIN_FREQ,
    SLOPE_MAX_FREQ,
    SLOPE_MIN_FREQ,
    compute_contour,
    compute_directivity_deg,
    compute_directivity_deg_v2,
    compute_minmax_slopes,
    compute_slope_smoothness,
    compute_statistics,
    directivity_matrix,
    dist_point_line,
    logger,
    octave,
    resample,
    reshape,
    savitzky_golay,
    sort_angles,
    unify_freq,
)

__all__ = [
    'DIRECTIVITY_MAX_FREQ', 'DIRECTIVITY_MIN_FREQ', 'SLOPE_MAX_FREQ', 'SLOPE_MIN_FREQ', 'compute_contour', 'compute_directivity_deg', 'compute_directivity_deg_v2', 'compute_minmax_slopes', 'compute_slope_smoothness', 'compute_statistics', 'directivity_matrix', 'dist_point_line', 'logger', 'octave', 'resample', 'reshape', 'savitzky_golay', 'sort_angles', 'unify_freq',
]
