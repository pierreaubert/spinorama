# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.filters.iir``."""

from spinorama.filters.iir import (
    Biquad,
    DEFAULT_Q_HIGH_LOW_PASS,
    DEFAULT_Q_HIGH_LOW_SHELF,
    Vector,
    bw2q,
    frozendict,
    q2bw,
)

__all__ = [
    "DEFAULT_Q_HIGH_LOW_PASS",
    "DEFAULT_Q_HIGH_LOW_SHELF",
    "Biquad",
    "Vector",
    "bw2q",
    "frozendict",
    "q2bw",
]
