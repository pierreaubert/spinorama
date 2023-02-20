# -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd

from spinorama.ltype import Vector, Peq, FloatVector1D
from spinorama.filter_iir import Biquad

logger = logging.getLogger("spinorama")


def peq_equal(left: Peq, right: Peq) -> bool:
    """are 2 peqs equals?"""
    if len(left) != len(right):
        return False
    for l, r in zip(left, right):
        if l[0] != r[0] or l[1] != r[1]:
            return False
    return True


def peq_build(freq: FloatVector1D, peq: Peq) -> Vector:
    """compute SPL for each frequency"""
    current_filter = [0.0]
    if len(peq) > 0:
        for w, iir in peq:
            current_filter += w * iir.np_log_result(freq)
    return current_filter


def peq_freq(spl: FloatVector1D, peq: Peq) -> Vector:
    """compute SPL for each frequency"""
    current_filter = [0.0]
    if len(peq) > 0:
        for w, iir in peq:
            current_filter += w * np.array([iir(v) for v in spl])
    return current_filter


def peq_preamp_gain(peq: Peq) -> float:
    """compute preamp gain for a peq

    Note that we add 0.2 dB to have a margin for clipping
    """
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 1000)
    spl = np.array(peq_build(freq, peq))
    individual = 0.0
    if len(peq) == 0:
        return 0.0
    for w, iir in peq:
        individual = max(individual, np.max(peq_build(freq, [(1.0, iir)])))
    overall = np.max(np.clip(spl, 0, None))
    gain = -(max(individual, overall) + 0.2)
    # print('debug preamp gain: %f'.format(gain))
    return gain


def peq_apply_measurements(spl: pd.DataFrame, peq: Peq) -> pd.DataFrame:
    if len(peq) == 0:
        return spl
    freq = spl["Freq"].to_numpy()
    curve_peq = peq_build(freq, peq)
    # TODO: doesn't work all the time
    # if "On Axis" in spl.columns:
    #    mean = np.mean(spl.loc[(spl.Freq > 500) & (spl.Freq < 10000)]["On Axis"])
    #    curve_peq = curve_peq - mean

    # create a new frame
    filtered = spl.loc[:, spl.columns != "Freq"].add(curve_peq, axis=0)
    filtered["Freq"] = freq
    # check for issues
    if filtered.isnull().values.any():
        logger.debug(filtered)
        logger.warning("Some filtered values post EQ are NaN")
        return filtered.dropna()
    return filtered


def peq_print(peq: Peq) -> None:
    for i, iir in enumerate(peq):
        if iir[0] != 0:
            print(iir[1])


def peq_format_apo(comment: str, peq: Peq) -> str:
    res = [comment]
    res.append("Preamp: {:.1f} dB".format(peq_preamp_gain(peq)))
    res.append("")
    for i, data in enumerate(peq):
        _, iir = data
        if iir.typ in (Biquad.PEAK, Biquad.NOTCH, Biquad.BANDPASS):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB Q {:0.2f}".format(
                    i + 1, iir.type2str(), int(iir.freq), iir.dbGain, iir.Q
                )
            )
        elif iir.typ in (Biquad.LOWPASS, Biquad.HIGHPASS):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz".format(i + 1, iir.type2str(), int(iir.freq))
            )
        elif iir.typ in (Biquad.LOWSHELF, Biquad.HIGHSHELF):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB".format(
                    i + 1, iir.type2str(), int(iir.freq), iir.dbGain
                )
            )
        else:
            logger.error("kind %s is unkown", iir.typ)
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
