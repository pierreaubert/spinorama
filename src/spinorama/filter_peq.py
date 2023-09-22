# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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
import numpy as np
import pandas as pd

from spinorama import logger
from spinorama.ltype import Vector
from spinorama.filter_iir import Biquad, DEFAULT_Q_HIGH_LOW_PASS

# declare type here to prevent circular dependencies
Peq = list[tuple[float, Biquad]]


def peq_equal(left: Peq, right: Peq) -> bool:
    """are 2 peqs equals?"""
    if len(left) != len(right):
        return False
    return all(not (l[0] != r[0] or l[1] != r[1]) for l, r in zip(left, right, strict=True))


def peq_spl(freq: Vector, peq: Peq) -> Vector:
    """compute SPL for each frequency"""
    current_filter = [0.0]
    if len(peq) > 0:
        for w, iir in peq:
            current_filter += w * iir.np_log_result(freq)
    return current_filter


def peq_preamp_gain(peq: Peq) -> float:
    """compute preamp gain for a peq: well adapted to computers"""
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 1000)
    spl = np.array(peq_spl(freq, peq))
    overall = np.max(np.clip(spl, 0, None))
    # print('debug preamp gain: %f'.format(gain))
    return -overall


def peq_preamp_gain_max(peq: Peq) -> float:
    """compute preamp gain for a peq and look at the worst case

    Note that we add 0.2 dB to have a margin for clipping
    """
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 1000)
    spl = np.array(peq_spl(freq, peq))
    individual = 0.0
    if len(peq) == 0:
        return 0.0
    for _w, iir in peq:
        individual = max(individual, np.max(peq_spl(freq, [(1.0, iir)])))
    overall = np.max(np.clip(spl, 0, None))
    gain = -(max(individual, overall) + 0.2)
    # print('debug preamp gain: %f'.format(gain))
    return gain


def peq_apply_measurements(spl: pd.DataFrame, peq: Peq) -> pd.DataFrame:
    if len(peq) == 0:
        return spl
    freq = spl["Freq"].to_numpy()
    curve_peq = peq_spl(freq, peq)

    # create a new frame
    filtered = spl.loc[:, spl.columns != "Freq"].add(curve_peq, axis=0)
    filtered["Freq"] = freq
    # check for issues
    if filtered.isna().to_numpy().any():
        logger.debug(filtered)
        logger.warning("Some filtered values post EQ are NaN")
        return filtered.dropna()
    return filtered


def peq_print(peq: Peq) -> None:
    print("IIR    Hz.  Q.   dB")
    for _, iir in peq:
        print(f"{iir.biquad_type:3d} {iir.freq:5.0f} {iir.q:1.1f} {iir.db_gain:+1.2f}")


def peq_format_apo(comment: str, peq: Peq) -> str:
    res = [comment]
    res.append("Preamp: {:.1f} dB".format(peq_preamp_gain(peq)))
    res.append("")
    for i, data in enumerate(peq):
        _, iir = data
        if iir.biquad_type in (Biquad.PEAK, Biquad.NOTCH, Biquad.BANDPASS):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB Q {:0.2f}".format(
                    i + 1, iir.type2str_short(), int(iir.freq), iir.db_gain, iir.q
                )
            )
        elif iir.biquad_type in (Biquad.LOWPASS, Biquad.HIGHPASS):
            if iir.q == DEFAULT_Q_HIGH_LOW_PASS:
                res.append(
                    "Filter {:2d}: ON {:2s} Fc {:5d} Hz".format(
                        i + 1, iir.type2str_short(), int(iir.freq)
                    )
                )
            else:
                res.append(
                    "Filter {:2d}: ON {:2s}Q Fc {:5d} Hz Q {:0.2f}".format(
                        i + 1, iir.type2str_short(), int(iir.freq), iir.q
                    )
                )
        elif iir.biquad_type in (Biquad.LOWSHELF, Biquad.HIGHSHELF):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB Q {:.2f}".format(
                    i + 1, iir.type2str_short(), int(iir.freq), iir.db_gain, iir.q
                )
            )
        else:
            logger.error("kind %s is unkown", iir.biquad_type)
    res.append("")
    return "\n".join(res)


def peq_butterworth_q(order):
    odd = (order % 2) > 0
    q_values = []
    for i in range(0, order // 2):
        q = 2.0 * math.sin(math.pi / order * (i + 0.5))
        q_values.append(1.0 / q)
    if odd:
        q_values.append(-1.0)
    return q_values


def peq_linkwitzriley_q(order):
    q_bw = peq_butterworth_q(order // 2)
    q_values = []
    if order % 4 > 0:
        q_values = np.concatenate([q_bw[:-1], q_bw[:-1], [0.5]])
    else:
        q_values = np.concatenate([q_bw, q_bw])
    return q_values


def peq_butterworth_lowpass(order, freq, srate):
    q_values = peq_butterworth_q(order)
    return [(1.0, Biquad(Biquad.LOWPASS, freq, srate, q)) for q in q_values]


def peq_butterworth_highpass(order, freq, srate):
    q_values = peq_butterworth_q(order)
    return [(1.0, Biquad(Biquad.HIGHPASS, freq, srate, q)) for q in q_values]


def peq_linkwitzriley_lowpass(order, freq, srate):
    q_values = peq_linkwitzriley_q(order)
    return [(1.0, Biquad(Biquad.LOWPASS, freq, srate, q)) for q in q_values]


def peq_linkwitzriley_highpass(order, freq, srate):
    q_values = peq_linkwitzriley_q(order)
    return [(1.0, Biquad(Biquad.HIGHPASS, freq, srate, q)) for q in q_values]
