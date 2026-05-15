# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.gll_hv_txt``."""
from spinorama.loaders.gll_hv_txt import (
    StatusOr,
    logger,
    parse_graph_gll_hv_txt,
    parse_graphs_speaker_gll_hv_txt,
    sort_angles,
)

__all__ = [
    'StatusOr', 'logger', 'parse_graph_gll_hv_txt', 'parse_graphs_speaker_gll_hv_txt', 'sort_angles',
]
