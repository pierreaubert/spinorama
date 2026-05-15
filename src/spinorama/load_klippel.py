# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.klippel``."""
from spinorama.loaders.klippel import (
    StatusOr,
    find_data_klippel,
    inwall_cleanup,
    logger,
    parse_graph_freq_klippel,
    parse_graphs_speaker_klippel,
    removequote,
    sort_angles,
)

__all__ = [
    'StatusOr', 'find_data_klippel', 'inwall_cleanup', 'logger', 'parse_graph_freq_klippel', 'parse_graphs_speaker_klippel', 'removequote', 'sort_angles',
]
