#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2022 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
import math
import numpy as np
from typing import Literal, List, Tuple
import scipy.signal as sig
from scipy.interpolate import InterpolatedUnivariateSpline

from spinorama.ltype import FloatVector1D, Vector

logger = logging.getLogger("spinorama")


# ------------------------------------------------------------------------------
# find initial values for biquads
# ------------------------------------------------------------------------------


def compute_non_admissible_freq(peq, min_freq, max_freq):
    zones = []
    for _, eq in peq:
        f = eq.freq
        q = eq.Q
        # limit the zone for small q
        if q < 1.0:
            q = 1.0
        q2 = q * q
        n = 1 + 1 / (2 * q2) + math.sqrt((2 + 1 / q2) * (2 + 1 / q2) / 4 - 1)
        n_2 = math.pow(2, n)
        w = f * (n_2 - 1) / (n_2 + 1)
        f1 = f - w
        f2 = f + w
        # print("zones f={} f1={} f2={} q={}".format(int(f), int(f1), int(f2), q))
        zones.append((f1, f2))
    return zones


def not_in_zones(zones, f):
    for f1, f2 in zones:
        if f > f1 and f < f2:
            return False
    return True


def find_largest_area(
    freq: FloatVector1D, curve: List[FloatVector1D], optim_config: dict, peq
) -> Tuple[Literal[-1, 1], int, float]:

    min_freq = optim_config["target_min_freq"]
    max_freq = optim_config["target_max_freq"]
    zones = compute_non_admissible_freq(peq, min_freq, max_freq)

    def largest_area(current_curve) -> Tuple[int, float]:
        print("[{}]".format(", ".join([str(f) for f in current_curve])))
        peaks, _ = sig.find_peaks(current_curve, distance=4)
        if len(peaks) == 0:
            print("fla: failed no peaks")
            return -1, -1
        print("fla: found peaks at {}".format(peaks))
        widths = sig.peak_widths(current_curve, peaks)[0]
        print("fla: computed width at {}".format(widths))
        areas = [
            (
                i,
                np.trapz(
                    current_curve[
                        max(0, peaks[i] - int(widths[i] // 2)) : min(len(current_curve), peaks[i] + int(widths[i] // 2))
                    ]
                ),
            )
            for i in range(0, len(peaks))
        ]
        print("fla: areas {}".format(areas))
        sorted_areas = sorted(areas, key=lambda a: -a[1])
        print("fla: sorted areas {}".format(sorted_areas))
        i = 0
        ipeaks = -1
        while i < len(sorted_areas):
            ipeaks, area = sorted_areas[i]
            f = freq[peaks[ipeaks]]
            if not_in_zones(zones, f) and f < max_freq and f > min_freq:
                print("fla: accepted peak at {}hz area {}".format(freq[peaks[ipeaks]], area))
                return f, area
            else:
                print("fla: rejected peak at {}hz area {}".format(freq[peaks[ipeaks]], area))
            i += 1
        print("fla: failed! sorted areas are {}".format(sorted_areas))
        print("fla: failed! freqs are {}".format([freq[i] for i in peaks]))
        return -1, -1

    plus_curve = np.clip(curve, a_min=0, a_max=None)
    plus_freq, plus_areas = largest_area(plus_curve)

    minus_freq, minus_areas = -1, -1.0
    if optim_config["plus_and_minus"] is True:
        minus_curve = -np.clip(curve, a_min=None, a_max=0)
        minus_freq, minus_areas = largest_area(minus_curve)

    print("fla: minus a={} f={} plus a={} f={}".format(minus_areas, minus_freq, plus_areas, plus_freq))

    if minus_areas == -1 and plus_areas == -1:
        print("fla: both plus and minus missed")
        return +1, -1

    if plus_areas == -1:
        print("fla: using minus freq")
        return -1, minus_freq

    if minus_areas == -1:
        print("fla: using plus freq")
        return +1, plus_freq

    if minus_areas > plus_areas:
        print("fla: using min freq")
        return -1, minus_freq

    print("fla: using plus freq")
    return +1, plus_freq


def propose_range_freq(
    freq: FloatVector1D, local_target: List[FloatVector1D], optim_config: dict, zones
) -> Tuple[Literal[-1, 1], float, Vector]:
    sign, init_freq = find_largest_area(freq, local_target, optim_config, zones)
    if init_freq == -1:
        init_freq = 1000
        init_freq_min = 20
        init_freq_max = 16000
        return (
            +1,
            init_freq,
            np.linspace(init_freq_min, init_freq_max, 200).tolist(),
        )

    scale = optim_config["elastic"]
    init_freq_min = max(init_freq * scale, optim_config["target_min_freq"])
    init_freq_max = min(init_freq / scale, optim_config["target_max_freq"])
    # print("prf: sign={} init_freq={} range=[{}, {}]".format(sign, init_freq, init_freq_min, init_freq_max))
    return (
        sign,
        init_freq,
        np.linspace(init_freq_min, init_freq_max, optim_config["MAX_STEPS_FREQ"]).tolist(),
    )


def propose_range_dbGain(
    freq: FloatVector1D,
    local_target: List[FloatVector1D],
    sign: Literal[-1, 1],
    init_freq: FloatVector1D,
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
    logger.debug("gain min {}dB peak {}dB max {}dB".format(init_dbGain_min, init_dbGain, init_dbGain_max))

    if sign < 0:
        return np.linspace(init_dbGain_min, init_dbGain_max, optim_config["MAX_STEPS_DBGAIN"]).tolist()
    return np.linspace(
        # no real minimim for negative values
        -init_dbGain_max * 2,
        -init_dbGain_min,
        optim_config["MAX_STEPS_DBGAIN"],
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
