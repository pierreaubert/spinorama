# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

import math
from typing import Literal

import numpy as np
import scipy.signal as sig
from scipy.interpolate import InterpolatedUnivariateSpline

from spinorama import logger
from spinorama.ltype import Vector, Zone
from spinorama.filter_peq import Peq

# ------------------------------------------------------------------------------
# find initial values for biquads
# ------------------------------------------------------------------------------


def compute_non_admissible_freq(peq: Peq, min_freq: float, max_freq: float) -> Zone:
    """returns a list of zones (range of frequencies) which are not admissible"""
    zones = []
    for _, current_eq in peq:
        f = current_eq.freq
        q = current_eq.q
        # limit the zone for small q
        q = max(1.0, q)
        q2 = q * q
        n = 1 + 1 / (2 * q2) + math.sqrt((2 + 1 / q2) * (2 + 1 / q2) / 4 - 1)
        n_2 = math.pow(2, n)
        w = f * (n_2 - 1) / (n_2 + 1)
        f1 = f - w
        f2 = f + w
        logger.debug("zones f=%d f1=%d f2=%d q=%f", int(f), int(f1), int(f2), q)
        zones.append((f1, f2))
    return zones


def not_in_zones(zones: Zone, freq: float) -> bool:
    """check if frequency is in range for each zone"""
    return all(not (freq > zone_low and freq < zone_high) for zone_low, zone_high in zones)


def find_largest_area(
    freq: Vector, curve: Vector, optim_config: dict, peq: Peq
) -> tuple[Literal[-1] | Literal[1], float]:
    min_freq = optim_config["target_min_freq"]
    max_freq = optim_config["target_max_freq"]
    zones = compute_non_admissible_freq(peq, min_freq, max_freq)

    def largest_area(current_curve) -> tuple[int, float]:
        peaks, _ = sig.find_peaks(current_curve, distance=4)
        if len(peaks) == 0:
            return -1, -1
        widths = sig.peak_widths(current_curve, peaks)[0]
        areas = [
            (
                i,
                np.trapz(
                    current_curve[
                        max(0, peaks[i] - int(widths[i] // 2)) : min(
                            len(current_curve), peaks[i] + int(widths[i] // 2)
                        )
                    ]
                ),
            )
            for i in range(0, len(peaks))
        ]
        sorted_areas = sorted(areas, key=lambda a: -a[1])
        i = 0
        ipeaks = -1
        while i < len(sorted_areas):
            ipeaks, area = sorted_areas[i]
            f = freq[peaks[ipeaks]]
            if not_in_zones(zones, f) and f < max_freq and f > min_freq:
                return f, area
            i += 1
        return -1, -1

    plus_curve = np.clip(curve, a_min=0, a_max=None)
    plus_freq, plus_areas = largest_area(plus_curve)

    minus_freq, minus_areas = -1, -1.0
    if optim_config["plus_and_minus"] is True:
        minus_curve = -np.clip(curve, a_min=None, a_max=0)
        minus_freq, minus_areas = largest_area(minus_curve)

    if minus_areas == -1 and plus_areas == -1:
        return +1, -1

    if plus_areas == -1:
        return -1, minus_freq

    if minus_areas == -1:
        return +1, plus_freq

    if minus_areas > plus_areas:
        return -1, minus_freq

    return +1, plus_freq


def propose_range_freq(
    freq: Vector, local_target: Vector, optim_config: dict, peq: Peq
) -> tuple[Literal[-1, 1], float, Vector]:
    sign, init_freq = find_largest_area(freq, local_target, optim_config, peq)
    if init_freq == -1:
        init_freq = 1000
        init_freq_min = 20
        init_freq_max = 16000
        return (+1, init_freq, [init_freq_min, init_freq_max])

    scale = optim_config["elastic"]
    init_freq_min = max(init_freq * scale, optim_config["target_min_freq"])
    init_freq_max = min(init_freq / scale, optim_config["target_max_freq"])
    return (
        sign,
        init_freq,
        np.linspace(init_freq_min, init_freq_max, optim_config["MAX_STEPS_FREQ"]).tolist(),
    )


def propose_range_db_gain(
    freq: Vector,
    local_target: Vector,
    sign: Literal[-1, 1],
    init_freq: float,
    optim_config: dict,
) -> list[float]:
    spline = InterpolatedUnivariateSpline(np.log10(freq), local_target, k=1)
    scale = optim_config["elastic"]
    init_dbgain = abs(spline(math.log10(init_freq)))
    init_dbgain_min = max(init_dbgain * scale, optim_config["MIN_DBGAIN"])
    init_dbgain_max = min(init_dbgain / scale, optim_config["MAX_DBGAIN"])
    if init_dbgain_max <= init_dbgain_min:
        init_dbgain_min = optim_config["MIN_DBGAIN"]
        init_dbgain_max = optim_config["MAX_DBGAIN"]
    logger.debug("gain min %fdB peak %fdB max %fdB", init_dbgain_min, init_dbgain, init_dbgain_max)

    if sign < 0:
        return np.linspace(
            init_dbgain_min, init_dbgain_max, optim_config["MAX_STEPS_DBGAIN"]
        ).tolist()
    return np.linspace(
        # no real minimim for negative values
        -init_dbgain_max * 2,
        -init_dbgain_min,
        optim_config["MAX_STEPS_DBGAIN"],
    ).tolist()


def propose_range_q(optim_config: dict) -> list[float]:
    # return np.concatenate(
    #    (
    #        np.linspace(optim_config["MIN_Q"], 1.0, optim_config["MAX_STEPS_Q"]),
    #        np.linspace(
    #            1 + optim_config["MIN_Q"],
    #            optim_config["MAX_Q"],
    #            optim_config["MAX_STEPS_Q"],
    #        ),
    #    ),
    #    axis=0,
    # ).tolist()
    return np.linspace(
        optim_config["MIN_Q"], optim_config["MAX_Q"], optim_config["MAX_STEPS_Q"]
    ).tolist()


def propose_range_biquad(optim_config: dict) -> list[int]:
    return [
        0,  # Biquad.lowpass
        1,  # Biquad.highpass
        2,  # Biquad.bandpass
        3,  # Biquad.peak
        4,  # Biquad.notch
        5,  # Biquad.lowshelf
        6,  # Biquad.highshelf
    ]
