# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.loaders.rew_impulse``."""
from spinorama.loaders.rew_impulse import (
    logger,
    parse_impulse_rews,
)

__all__ = [
    'logger', 'parse_impulse_rews',
]
