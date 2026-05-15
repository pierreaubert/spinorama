# -*- coding: utf-8 -*-
"""Backwards-compatibility shim. See ``spinorama.filters.peq``."""
from spinorama.filters.peq import (
    Biquad,
    DEFAULT_Q_HIGH_LOW_PASS,
    Peq,
    Vector,
    logger,
    peq_apply_measurements,
    peq_butterworth_highpass,
    peq_butterworth_lowpass,
    peq_butterworth_q,
    peq_equal,
    peq_format_apo,
    peq_linkwitzriley_highpass,
    peq_linkwitzriley_lowpass,
    peq_linkwitzriley_q,
    peq_preamp_gain,
    peq_preamp_gain_max,
    peq_print,
    peq_spl,
)

__all__ = [
    'Biquad', 'DEFAULT_Q_HIGH_LOW_PASS', 'Peq', 'Vector', 'logger', 'peq_apply_measurements', 'peq_butterworth_highpass', 'peq_butterworth_lowpass', 'peq_butterworth_q', 'peq_equal', 'peq_format_apo', 'peq_linkwitzriley_highpass', 'peq_linkwitzriley_lowpass', 'peq_linkwitzriley_q', 'peq_preamp_gain', 'peq_preamp_gain_max', 'peq_print', 'peq_spl',
]
