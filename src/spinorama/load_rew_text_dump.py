# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.rew_text_dump``."""
from spinorama.loaders.rew_text_dump import (
    StatusOr,
    logger,
    parse_graphs_speaker_rew_text_dump,
)

__all__ = [
    'StatusOr', 'logger', 'parse_graphs_speaker_rew_text_dump',
]
