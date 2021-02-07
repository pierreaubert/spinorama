#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import numpy as np
from typing import Literal, List, Tuple

from scipy.stats import linregress
import scipy.signal as sig
from scipy.interpolate import InterpolatedUnivariateSpline

from spinorama.ltype import Vector, Peq
from spinorama.filter_peq import peq_build
from spinorama.filter_scores import scores_apply_filter

logger = logging.getLogger("spinorama")


# ------------------------------------------------------------------------------
# find initial values for biquads
# ------------------------------------------------------------------------------


def find_largest_area(freq, curve, optim_config):
    def largest_area(positive_curve):
        # print('freq {} positive_curve {}'.format(freq, positive_curve))
        found_peaks, _ = sig.find_peaks(positive_curve, distance=10)
        if len(found_peaks) == 0:
            return None, None
        # print('found peaks at {}'.format(found_peaks))
        found_widths = sig.peak_widths(positive_curve, found_peaks, rel_height=0.1)[0]
        # print('computed width at {}'.format(found_widths))
        areas = [
            (i, positive_curve[found_peaks[i]] * found_widths[i])
            for i in range(0, len(found_peaks))
        ]
        # print('areas {}'.format(areas))
        sorted_areas = sorted(areas, key=lambda a: -a[1])
        # print('sorted {}'.format(sorted_areas))
        ipeaks, area = sorted_areas[0]
        return found_peaks[ipeaks], area

    plus_curve = np.clip(curve, a_min=0, a_max=None)
    plus_index, plus_areas = largest_area(plus_curve)

    minus_index, minus_areas = None, None
    if optim_config["plus_and_minus"] is True:
        minus_curve = -np.clip(curve, a_min=None, a_max=0)
        minus_index, minus_areas = largest_area(minus_curve)

    if minus_areas is None and plus_areas is None:
        logger.error("No initial freq found")
        return +1, None, None

    if plus_areas is None:
        return -1, minus_index, freq[minus_index]

    if minus_areas is None:
        return +1, plus_index, freq[plus_index]

    if minus_areas > plus_areas:
        return -1, minus_index, freq[minus_index]
    return +1, plus_index, freq[plus_index]


def propose_range_freq(freq, local_target, optim_config):
    sign, indice, init_freq = find_largest_area(freq, local_target, optim_config)
    scale = optim_config["elastic"]
    # print('Scale={} init_freq {}'.format(scale, init_freq))
    init_freq_min = max(init_freq * scale, optim_config["freq_reg_min"])
    init_freq_max = min(init_freq / scale, optim_config["freq_reg_max"])
    logger.debug(
        "freq min {}Hz peak {}Hz max {}Hz".format(
            init_freq_min, init_freq, init_freq_max
        )
    )
    if optim_config["MAX_STEPS_FREQ"] == 1:
        return sign, init_freq, [init_freq]
    return (
        sign,
        init_freq,
        np.linspace(
            init_freq_min, init_freq_max, optim_config["MAX_STEPS_FREQ"]
        ).tolist(),
    )


def propose_range_dbGain(
    freq: Vector,
    local_target: List[Vector],
    sign: Literal[-1, 1],
    init_freq: Vector,
    optim_config: dict,
) -> Vector:
    spline = InterpolatedUnivariateSpline(np.log10(freq), local_target, k=1)
    scale = optim_config["elastic"]
    init_dbGain = abs(spline(np.log10(init_freq)))
    init_dbGain_min = max(init_dbGain * scale, optim_config["MIN_DBGAIN"])
    init_dbGain_max = min(init_dbGain / scale, optim_config["MAX_DBGAIN"])
    if init_dbGain_max <= init_dbGain_min:
        init_dbGain_min = optim_config["MIN_DBGAIN"]
        init_dbGain_max = optim_config["MAX_DBGAIN"]
    logger.debug(
        "gain min {}dB peak {}dB max {}dB".format(
            init_dbGain_min, init_dbGain, init_dbGain_max
        )
    )

    if sign < 0:
        return np.linspace(
            init_dbGain_min, init_dbGain_max, optim_config["MAX_STEPS_DBGAIN"]
        ).tolist()
    return np.linspace(
        -init_dbGain_max, -init_dbGain_min, optim_config["MAX_STEPS_DBGAIN"]
    ).tolist()


def propose_range_Q(optim_config):
    return np.concatenate(
        (
            np.linspace(optim_config["MIN_Q"], 1.0, optim_config["MAX_STEPS_Q"]),
            np.linspace(
                1 + optim_config["MIN_Q"],
                optim_config["MAX_Q"],
                optim_config["MAX_STEPS_Q"],
            ),
        ),
        axis=0,
    ).tolist()


def propose_range_biquad(optim_config):
    return [
        0,  # Biquad.lowpass
        1,  # Biquad.highpass
        2,  # Biquad.bandpass
        3,  # Biquad.peak
        4,  # Biquad.notch
        5,  # Biquad.lowshelf
        6,  # Biquad.highshelf
    ]


