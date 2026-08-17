# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.webplotdigitizer``."""

from spinorama.loaders.webplotdigitizer import (
    StatusOr,
    logger,
    parse_graph_freq_webplotdigitizer,
    parse_graphs_speaker_webplotdigitizer,
    parse_webplotdigitizer_get_jsonfilename,
)

__all__ = [
    "StatusOr",
    "logger",
    "parse_graph_freq_webplotdigitizer",
    "parse_graphs_speaker_webplotdigitizer",
    "parse_webplotdigitizer_get_jsonfilename",
]
