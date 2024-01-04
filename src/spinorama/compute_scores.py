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
from typing import List, Tuple
import numpy as np
import pandas as pd
from more_itertools import consecutive_groups
from scipy.stats import linregress

from spinorama import logger


def round_down(x: float, decimals: int) -> float:
    """return a rounded value down"""
    if x > 0 and decimals <= 5:
        mul = 10**decimals
        return math.floor(x * mul) / mul
    else:
        # not necessary what I want
        return round(x, decimals)


# https://courses.physics.illinois.edu/phys406/sp2017/Lab_Handouts/Octave_Bands.pdf
def octave(count: int) -> List[Tuple[float, float, float]]:
    """compute 1/N octave band

    N: >=2 when N increases, bands are narrower
    """
    # why 1290 and not 1000?
    reference = 1290.0
    p = pow(2, 1 / count)
    p_band = pow(2, 1 / (2 * count))
    o_iter = int((count * 10 + 1) / 2)
    center = (
        [reference / p**i for i in range(o_iter, 0, -1)]
        + [reference]
        + [reference * p**i for i in range(1, o_iter + 1, 1)]
    )
    return [(c / p_band, c, c * p_band) for c in center]


def aad(dfu: pd.DataFrame, min_freq) -> float:
    """aad Absolute Average Deviation"""
    # mean betwenn 200hz and 400hz
    y_data = dfu.loc[(dfu.Freq >= 200) & (dfu.Freq <= 400)].dB
    y_ref = np.mean(y_data) if not y_data.empty else 0.0
    aad_sum = 0
    n = 0
    # 1/20 octave
    bmin_freq = max(100, min_freq)
    for bmin, _, bmax in octave(20):
        # 100hz to 16k hz
        if bmin < bmin_freq or bmax > 16000:
            continue
        mean = dfu.loc[(dfu.Freq >= bmin_freq) & (dfu.Freq < bmax)].dB.mean()
        aad_sum += abs(y_ref - mean)
        n += 1
    if n == 0:
        logger.error("aad is None")
        return -1.0
    return aad_sum / n


def mad(df: pd.Series) -> float:
    # mad has been deprecated in pandas
    # I replace it with the equivalent (df - df.mean()).abs().mean()
    return (df - df.mean()).abs().mean()


def nbd(dfu: pd.DataFrame, min_freq: float) -> float:
    """nbd Narrow Band

    The narrow band deviation is defined by:
      NBD(dB)=⎜ ∑ y -y ⎟÷N  ⎛
    where ⎜ OctaveBandn⎟ is the average amplitude value
    within the 1/2-octave band n, yb is the amplitude
    value of band b, and N is the total number of 1/2­ octave bands
    between 100 Hz-12 kHz. The mean absolute deviation within each
    1/2-octave band is based a sample of 10 equally log-spaced data points.
    """
    bmin_freq = max(100, min_freq)
    return np.nanmean(
        [
            mad(dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq <= bmax)].dB)
            for (bmin, bcenter, bmax) in octave(2)
            if bmin_freq <= bcenter and bcenter <= 12000
        ]
    )


LFX_DEFAULT = math.log10(300)


def lfx(lw, sp) -> float:
    """lfx Low Frequency Extension

    The low frequency extension (LFX)
         LFX = log10(xSP-6dB.re:y _ LW(300Hz-10kHz) (7)
    where LFX is the log10 of the first frequency x_SP below 300 Hz
    in the sound power curve, that is -6 dB relative to the mean level y_LW
    measured in listening window (LW) between 300 Hz-10 kHz.
    LFX is log-transformed to produce a linear relationship between the
    variable LFX and preference rating. The sound power curve (SP) is used
    for the calculation because it better defines the true bass output of
    the loudspeaker, particularly speakers that have rear-firing ports.
    """
    lw_data = lw.loc[(lw.Freq >= 300) & (lw.Freq <= 10000)].dB
    lw_ref = np.mean(lw_data) if not lw_data.empty else 0.0
    lw_ref -= 6.0
    # find first freq such that y[freq]<y_ref-6dB
    lfx_range = sp.loc[(sp.Freq <= 300) & (sp.dB <= lw_ref)].Freq
    if lfx_range.shape[0] == 0:
        # happens with D&D 8C when we do not have a point low enough to get the -6
        return math.log10(sp.Freq.to_numpy()[0])

    # trying to deal with oscillating bass range
    # trick is: index is contiguous, the filter above make creates hole
    lfx_grouped = consecutive_groups(lfx_range.items(), lambda x: x[0])
    try:
        # grab the last group and return freq
        lfx_last = list(next(lfx_grouped))[-1]
        lfx_pos = lfx_last[0]
        # get the next freq to be more inlined with the other people computing the code
        # nothing wrong if you remove the +1
        lfx_hz = (sp.Freq)[lfx_pos + 1]
    except Exception:
        # some speaker measurements start above 300Hz
        return LFX_DEFAULT
    return math.log10(lfx_hz)


LFQ_DEFAULT = 10


def lfq(lw, sp, lfx_log) -> float:
    """lfq Low Frequency Quality

    LFQ is intended to quantify deviations in amplitude response over the
    bass region between the low frequency cut-off and 300 Hz.
    """
    val_lfx = pow(10, lfx_log)
    lfq_sum = 0
    n = 0
    # print('DEBUG lfx={1} octave(2): {0}'.format(octave(2), val_lfx))
    for bmin, _, bmax in octave(2):
        # 100hz to 12k hz
        if bmin < val_lfx or bmax > 300:
            continue
        s_lw = lw.loc[(lw.Freq >= bmin) & (lw.Freq < bmax)]
        s_sp = sp.loc[(sp.Freq >= bmin) & (sp.Freq < bmax)]
        if s_lw.shape[0] > 0 and s_sp.shape[0] > 0:
            y_lw = np.mean(s_lw.dB) if not s_lw.dB.empty else 0.0
            y_sp = np.mean(s_sp.dB) if not s_sp.dB.empty else 0.0
            lfq_sum += abs(y_lw - y_sp)
            n += 1
    if n == 0:
        logger.debug("lfq is None: lfx=%f", val_lfx)
        return LFQ_DEFAULT
    return lfq_sum / n


def sm(dfu):
    """sm Smoothness

    For each of the 7 frequency response curves, the overall smoothness (SM) and
    slope (SL) of the curve was determined by estimating the line that best fits
    the frequency curve over the range of 100 Hz-16 kHz. This was done using a
    regression based on least square error. SM is the Pearson correlation
    coefficient of determination (r2) that describes the goodness of fit of the
    regression line defined by:
    ⎛ SM =⎜ n(∑XY)-(∑X)(∑Y) ⎟ / ⎜ (n∑X2-(∑X)2)(n∑Y2-(∑Y)2)⎟

    where n is number of data points used to estimate the regression curve and
    X and Y represent the measured versus estimated amplitude values of the
    regression line. A natural log transformation is applied to the measured
    frequency values (Hz) so that they are linearly spaced (see equation 5).
    Smoothness (SM) values can range from 0 to 1, with larger values representing
    smoother frequency response curves.
    """
    data = dfu.loc[(dfu.Freq >= 100) & (dfu.Freq <= 16000)]
    log_freq = np.log10(data.Freq)
    _, _, r_value, _, _ = linregress(log_freq, data.dB)
    return r_value**2


"""
    # same results as above
    slope, intercept, r_value, _, _ = linregress(log_freq, data.dB)
    n = log_freq.size
    x = data.dB.to_numpy()
    y = intercept + slope * log_freq
    sm_num = n*np.sum(np.multiply(x, y))-np.sum(x)*np.sum(y)
    sm_den_x = n*np.sum(np.multiply(x, x))-np.sum(x)**2
    sm_den_y = n*np.sum(np.multiply(y, y))-np.sum(y)**2
    sm_den = math.sqrt(sm_den_x*sm_den_y)
    sm_pir = (sm_num/sm_den)**2
    logger.error('debug: sm_pir %f r2 %f', sm_pir, r_value**2)
    return sm_pir
"""


def pref_rating(nbd_on: float, nbd_pir: float, lf_x: float, sm_pir: float) -> float:
    return 12.69 - 2.49 * nbd_on - 2.99 * nbd_pir - 4.31 * lf_x + 2.32 * sm_pir


def speaker_pref_rating(cea2034, pir, rounded):
    try:
        if pir is None or pir.shape[0] == 0:
            logger.info("PIR is empty")
            return None
        df_on_axis = cea2034.loc[lambda df: df.Measurements == "On Axis"]
        df_listening_window = cea2034.loc[lambda df: df.Measurements == "Listening Window"]
        df_sound_power = cea2034.loc[lambda df: df.Measurements == "Sound Power"]
        min_freq = cea2034.Freq.min()
        nbd_on_axis = nbd(df_on_axis, min_freq)
        nbd_listening_window = nbd(df_listening_window, min_freq)
        nbd_sound_power = nbd(df_sound_power, min_freq)
        nbd_pred_in_room = nbd(pir, min_freq)
        lfx_hz = LFX_DEFAULT
        lfq_db = LFQ_DEFAULT
        aad_on_axis = -1.0
        aad_on_axis = aad(df_on_axis, min_freq)
        lfx_hz = lfx(df_listening_window, df_sound_power)
        lfq_db = lfq(df_listening_window, df_sound_power, lfx_hz)
        sm_sound_power = sm(df_sound_power)
        sm_pred_in_room = sm(pir)
        if nbd_on_axis is None or nbd_pred_in_room is None or sm_pred_in_room is None:
            logger.info("One of the pref score components is None")
            return None
        # 14.5hz or 20hz see discussion
        # https://www.audiosciencereview.com/forum/index.php?threads/master-preference-ratings-for-loudspeakers.11091/page-25#post-448733
        pref = None
        pref_wsub = pref_rating(nbd_on_axis, nbd_pred_in_room, math.log10(14.5), sm_pred_in_room)
        pref = pref_rating(nbd_on_axis, nbd_pred_in_room, lfx_hz, sm_pred_in_room)
        if pref is None or pref_wsub is None:
            logger.info("Pref score is None")
            return None

        if rounded:
            ratings = {
                "nbd_on_axis": round_down(nbd_on_axis, 3),
                "nbd_listening_window": round_down(nbd_listening_window, 3),
                "nbd_sound_power": round_down(nbd_sound_power, 3),
                "nbd_pred_in_room": round_down(nbd_pred_in_room, 3),
                "sm_pred_in_room": round_down(sm_pred_in_room, 3),
                "sm_sound_power": round_down(sm_sound_power, 3),
                "pref_score_wsub": round_down(pref_wsub, 2),
                "lfx_hz": int(pow(10, lfx_hz)),  # in Hz
                "lfq": round_down(lfq_db, 3),
                "pref_score": round_down(pref, 2),
            }
            if aad_on_axis != -1.0:
                ratings["aad_on_axis"] = round_down(aad_on_axis, 3)
        else:
            ratings = {
                "nbd_on_axis": nbd_on_axis,
                "nbd_listening_window": nbd_listening_window,
                "nbd_sound_power": nbd_sound_power,
                "nbd_pred_in_room": nbd_pred_in_room,
                "sm_pred_in_room": sm_pred_in_room,
                "sm_sound_power": sm_sound_power,
                "pref_score_wsub": pref_wsub,
                "aad_on_axis": (aad_on_axis,),
                "pref_score": pref,
            }
            if lfx_hz is not None:
                ratings["lfx_hz"] = pow(10, lfx_hz)
            if lfq_db is not None:
                ratings["lfq"] = lfq_db
        logger.debug("Ratings: %s", ratings)
    except ValueError:
        logger.exception("Compute pref_rating failed")
        return None
    return ratings
