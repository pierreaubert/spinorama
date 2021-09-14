# -*- coding: utf-8 -*-
import logging
import math
import altair as alt
import numpy as np
import pandas as pd

from .ltype import Vector, Peq, FloatVector1D
from .filter_iir import Biquad
from .load_misc import graph_melt

logger = logging.getLogger("spinorama")


def peq_equal(left: Peq, right: Peq) -> bool:
    if len(left) != len(right):
        return False
    for l, r in zip(left, right):
        if l[0] != r[0] or l[1] != r[1]:
            return False
    return True


def peq_build(freq: FloatVector1D, peq: Peq) -> Vector:
    current_filter = [0.0]
    if len(peq) > 0:
        for w, iir in peq:
            current_filter += w * iir.np_log_result(freq)
    return current_filter


def peq_freq(spl: FloatVector1D, peq: Peq) -> Vector:
    current_filter = [0.0]
    if len(peq) > 0:
        for w, iir in peq:
            current_filter += w * np.array([iir(v) for v in spl])
    return current_filter


def peq_preamp_gain(peq: Peq) -> float:
    # add 0.2 dB to have a margin for clipping
    # this assume that the DSP is operating at more that 16 or 24 bits
    # and that max gain of each PK is not generating clipping by itself
    freq = np.logspace(10 + math.log10(2), 4 + math.log10(2), 500)
    return -(np.max(peq_build(freq, peq)) + 0.2)


def peq_apply_measurements(spl: pd.DataFrame, peq: Peq) -> pd.DataFrame:
    if len(peq) == 0:
        return spl
    freq = spl["Freq"].to_numpy()
    curve_peq = peq_build(freq, peq)
    if "On Axis" in spl.columns:
        mean = np.mean(spl.loc[(spl.Freq > 500) & (spl.Freq < 10000)]["On Axis"])
        curve_peq = curve_peq - mean

    # create a new frame
    filtered = spl.loc[:, spl.columns != "Freq"].add(curve_peq, axis=0)
    filtered["Freq"] = freq
    # check for issues
    if filtered.isnull().values.any():
        logger.debug(filtered)
        logger.warning("Some filtered values post EQ are NaN")
        return filtered.dropna()
    return filtered


def peq_graph_measurements(spin: pd.DataFrame, measurement: str, peq: Peq):
    spin_freq = spin["Freq"].to_numpy()
    mean = np.mean(spin.loc[(spin.Freq > 500) & (spin.Freq < 10000)]["On Axis"])
    curve = spin[measurement] - mean
    current_filter = peq_build(spin_freq, peq)
    curve_filtered = peq_apply_measurements(curve, peq)
    dff = pd.DataFrame(
        {
            "Freq": spin_freq,
            measurement: curve,
            "{0} Filtered".format(measurement): curve_filtered,
            "Filter": current_filter,
        }
    )
    return (
        alt.Chart(graph_melt(dff))
        .mark_line(clip=True)
        .encode(
            x=alt.X(
                "Freq:Q", scale=alt.Scale(type="log", nice=False, domain=[20, 20000])
            ),
            y=alt.Y("dB:Q", scale=alt.Scale(domain=[-25, 5])),
            color=alt.Color("Measurements"),
        )
    )


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
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz".format(
                    i + 1, iir.type2str(), int(iir.freq)
                )
            )
        elif iir.typ in (Biquad.LOWSHELF, Biquad.HIGHSHELF):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB".format(
                    i + 1, iir.type2str(), int(iir.freq), iir.dbGain
                )
            )
        else:
            logger.error("kind {} is unkown".format(iir.typ))
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
