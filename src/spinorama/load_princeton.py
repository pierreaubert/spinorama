# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.princeton``."""
from spinorama.loaders.princeton import (
    StatusOr,
    loadmat,
    logger,
    parse_graph_freq_princeton_mat,
    parse_graph_princeton,
    parse_graphs_speaker_princeton,
    resample,
    sort_angles,
)

__all__ = [
    'StatusOr', 'loadmat', 'logger', 'parse_graph_freq_princeton_mat', 'parse_graph_princeton', 'parse_graphs_speaker_princeton', 'resample', 'sort_angles',
]
