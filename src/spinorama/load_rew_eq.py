# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.rew_eq``."""

from spinorama.loaders.rew_eq import (
    Biquad,
    INPUT_MAX_GAIN,
    INPUT_MAX_Q,
    Peq,
    bw2q,
    logger,
    parse_eq_iir_rews,
    parse_eq_line,
)

__all__ = [
    "Biquad",
    "INPUT_MAX_GAIN",
    "INPUT_MAX_Q",
    "Peq",
    "bw2q",
    "logger",
    "parse_eq_iir_rews",
    "parse_eq_line",
]
