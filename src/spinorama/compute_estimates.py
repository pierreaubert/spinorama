# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.compute.estimates``."""

from spinorama.compute.estimates import (
    MIDRANGE_MAX_FREQ,
    MIDRANGE_MIN_FREQ,
    SENSITIVITY_MAX_FREQ,
    SENSITIVITY_MIN_FREQ,
    compute_directivity_deg_v2,
    compute_sensitivity,
    compute_sensitivity_details,
    compute_sensitivity_distance,
    compute_slope_smoothness,
    estimates,
    estimates_slopes,
    estimates_spin,
    logger,
)

__all__ = [
    "MIDRANGE_MAX_FREQ",
    "MIDRANGE_MIN_FREQ",
    "SENSITIVITY_MAX_FREQ",
    "SENSITIVITY_MIN_FREQ",
    "compute_directivity_deg_v2",
    "compute_sensitivity",
    "compute_sensitivity_details",
    "compute_sensitivity_distance",
    "compute_slope_smoothness",
    "estimates",
    "estimates_slopes",
    "estimates_spin",
    "logger",
]
