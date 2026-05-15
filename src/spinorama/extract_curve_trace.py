# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.extract.curve_trace``."""
from spinorama.extract.curve_trace import (
    TYPE_CHECKING,
    _extrapolate_position,
    _find_clusters,
    _select_cluster,
    _smooth_curve,
    _weighted_centroid,
    annotations,
    curves_to_wpd_json,
    logger,
    trace_curves,
    trace_single_curve,
)

__all__ = [
    'TYPE_CHECKING', '_extrapolate_position', '_find_clusters', '_select_cluster', '_smooth_curve', '_weighted_centroid', 'annotations', 'curves_to_wpd_json', 'logger', 'trace_curves', 'trace_single_curve',
]
