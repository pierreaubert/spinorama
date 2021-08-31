#                                                  -*- coding: utf-8 -*-
import logging
import math
from typing import List, Tuple
import numpy as np
import pandas as pd
from more_itertools import consecutive_groups
from scipy.stats import linregress

from .compute_cea2034 import estimated_inroom_HV
from .load_misc import graph_melt

logger = logging.getLogger("spinorama")


# https://courses.physics.illinois.edu/phys406/sp2017/Lab_Handouts/Octave_Bands.pdf
def octave(N: int) -> List[Tuple[float, float, float]]:
    """compute 1/N octave band

    N: >=2 when N increases, bands are narrower
    """
    # why 1290 and not 1000?
    reference = 1290.0
    p = pow(2, 1 / N)
    p_band = pow(2, 1 / (2 * N))
    o_iter = int((N * 10 + 1) / 2)
    center = (
        [reference / p ** i for i in range(o_iter, 0, -1)]
        + [reference]
        + [reference * p ** i for i in range(1, o_iter + 1, 1)]
    )
    return [(c / p_band, c, c * p_band) for c in center]


def aad(dfu: pd.DataFrame) -> float:
    """aad Absolute Average Deviation"""
    # mean betwenn 200hz and 400hz
    y_ref = np.mean(dfu.loc[(dfu.Freq >= 200) & (dfu.Freq <= 400)].dB)
    # print(y_ref)
    aad_sum = 0
    n = 0
    # 1/20 octave
    for (bmin, bcenter, bmax) in octave(20):
        # 100hz to 16k hz
        if bcenter < 100 or bmax > 16000:
            continue
        selection = dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq < bmax)]
        if selection.shape[0] > 0:
            aad_sum += abs(y_ref - np.nanmean(selection.dB))
            n += 1
    if n == 0:
        logger.error("aad is None")
        return -1.0
    aad_value = aad_sum / n
    # if math.isnan(aad_value):
    #    pd.set_option('display.max_rows', dfu.shape[0]+1)
    #    print(aad_sum, n, dfu)
    return aad_value


def nbd(dfu: pd.DataFrame) -> float:
    """nbd Narrow Band

    The narrow band deviation is defined by:
      NBD(dB)=⎜ ∑ y −y ⎟÷N  ⎛
    where ⎜ OctaveBandn⎟ is the average amplitude value
    within the 1⁄2-octave band n, yb is the amplitude
    value of band b, and N is the total number of 1⁄2­ octave bands
    between 100 Hz-12 kHz. The mean absolute deviation within each
    1⁄2-octave band is based a sample of 10 equally log-spaced data points.
    """
    # return np.mean([median_absolute_deviation(dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq <= bmax)].dB)
    #                for (bmin, bcenter, bmax) in octave(2)
    #                if bcenter >=100 and bcenter <=12000])
    return np.nanmean(
        [
            dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq <= bmax)].dB.mad()
            for (bmin, bcenter, bmax) in octave(2)
            if 100 <= bcenter <= 12000
        ]
    )


def lfx(lw, sp) -> float:
    """lfx Low Frequency Extension

    The low frequency extension (LFX)
         LFX = log10(xSP−6dB.re:y _ LW(300Hz−10kHz) (7)
    where LFX is the log10 of the first frequency x_SP below 300 Hz
    in the sound power curve, that is -6 dB relative to the mean level y_LW
    measured in listening window (LW) between 300 Hz-10 kHz.
    LFX is log-transformed to produce a linear relationship between the
    variable LFX and preference rating. The sound power curve (SP) is used
    for the calculation because it better defines the true bass output of
    the loudspeaker, particularly speakers that have rear-firing ports.
    """
    lw_ref = np.mean(lw.loc[(lw.Freq >= 300) & (lw.Freq <= 10000)].dB) - 6
    logger.debug("lw_ref {}".format(lw_ref))
    # find first freq such that y[freq]<y_ref-6dB
    lfx_range = sp.loc[(sp.Freq < 300) & (sp.dB <= lw_ref)].Freq
    if len(lfx_range.values) == 0:
        # happens with D&D 8C when we do not have a point low enough to get the -6
        lfx_hz = sp.Freq.values[0]
    else:
        lfx_grouped = consecutive_groups(lfx_range.iteritems(), lambda x: x[0])
        # logger.debug('lfx_grouped {}'.format(lfx_grouped))
        try:
            lfx_hz = list(next(lfx_grouped))[-1][1]
        except Exception:
            lfx_hz = -1.0
            logger.error("lfx: selecting max {0}".format(lfx_hz))
    logger.debug("lfx_hz {}".format(lfx_hz))
    return math.log10(lfx_hz)


def lfq(lw, sp, lfx_log) -> float:
    """lfq Low Frequency Quality

    LFQ is intended to quantify deviations in amplitude response over the
    bass region between the low frequency cut-off and 300 Hz.
    """
    val_lfx = pow(10, lfx_log)
    lfq_sum = 0
    n = 0
    # print('DEBUG lfx={1} octave(20): {0}'.format(octave(20), val_lfx))
    for bmin, _, bmax in octave(20):
        # 100hz to 12k hz
        if bmin < val_lfx or bmax > 300:
            continue
        s_lw = lw.loc[(lw.Freq >= bmin) & (lw.Freq < bmax)]
        s_sp = sp.loc[(sp.Freq >= bmin) & (sp.Freq < bmax)]
        if s_lw.shape[0] > 0 and s_sp.shape[0] > 0:
            y_lw = np.mean(s_lw.dB)
            y_sp = np.mean(s_sp.dB)
            lfq_sum += abs(y_lw - y_sp)
            n += 1
    if n == 0:
        logger.warning("lfq is None")
        return -1.0
    return lfq_sum / n


def sm(dfu):
    """sm Smoothness

    For each of the 7 frequency response curves, the overall smoothness (SM) and
    slope (SL) of the curve was determined by estimating the line that best fits
    the frequency curve over the range of 100 Hz-16 kHz. This was done using a
    regression based on least square error. SM is the Pearson correlation
    coefficient of determination (r2) that describes the goodness of fit of the
    regression line defined by:
    ⎛ SM =⎜ n(∑XY)−(∑X)(∑Y) ⎟ / ⎜ (n∑X2 −(∑X)2)(n∑Y2 −(∑Y)2)⎟

    where n is number of data points used to estimate the regression curve and
    X and Y represent the measured versus estimated amplitude values of the
    regression line. A natural log transformation is applied to the measured
    frequency values (Hz) so that they are linearly spaced (see equation 5).
    Smoothness (SM) values can range from 0 to 1, with larger values representing
    smoother frequency response curves.
    """
    data = dfu.loc[(dfu.Freq >= 100) & (dfu.Freq <= 16000)]
    log_freq = np.log(data.Freq)
    _, _, r_value, _, _ = linregress(log_freq, data.dB)
    return r_value ** 2


def pref_rating(nbd_on, nbd_pir, lf_x, sm_pir):
    return 12.69 - 2.49 * nbd_on - 2.99 * nbd_pir - 4.31 * lf_x + 2.32 * sm_pir


def speaker_pref_rating(cea2034, df_pred_in_room, rounded=True):
    try:
        if df_pred_in_room is None or df_pred_in_room.shape[0] == 0:
            logger.info("PIR is empty")
            return None
        df_on_axis = cea2034.loc[lambda df: df.Measurements == "On Axis"]
        df_listening_window = cea2034.loc[
            lambda df: df.Measurements == "Listening Window"
        ]
        df_sound_power = cea2034.loc[lambda df: df.Measurements == "Sound Power"]
        skip_full = False
        for dfu in (df_on_axis, df_listening_window, df_sound_power):
            # need a better test
            if dfu.loc[(dfu.Freq >= 100) & (dfu.Freq <= 200)].shape[0] == 0:
                skip_full = True
        nbd_on_axis = nbd(df_on_axis)
        nbd_listening_window = nbd(df_listening_window)
        nbd_sound_power = nbd(df_sound_power)
        nbd_pred_in_room = nbd(df_pred_in_room)
        lfx_hz = -1.0
        lfq_db = -1.0
        aad_on_axis = -1.0
        if not skip_full:
            aad_on_axis = aad(df_on_axis)
            lfx_hz = lfx(df_listening_window, df_sound_power)
            lfq_db = lfq(df_listening_window, df_sound_power, lfx_hz)
        sm_sound_power = sm(df_sound_power)
        sm_pred_in_room = sm(df_pred_in_room)
        if nbd_on_axis is None or nbd_pred_in_room is None or sm_pred_in_room is None:
            logger.info("One of the pref score components is None")
            return None
        # 14.5hz or 20hz see discussion
        # https://www.audiosciencereview.com/forum/index.php?threads/master-preference-ratings-for-loudspeakers.11091/page-25#post-448733
        pref = None
        pref_wsub = pref_rating(
            nbd_on_axis, nbd_pred_in_room, math.log10(14.5), sm_pred_in_room
        )
        if not skip_full:
            pref = pref_rating(nbd_on_axis, nbd_pred_in_room, lfx_hz, sm_pred_in_room)
        if pref is None or pref_wsub is None:
            logger.info("Pref score is None")
            return None

        if rounded:
            ratings = {
                "nbd_on_axis": round(nbd_on_axis, 2),
                "nbd_listening_window": round(nbd_listening_window, 2),
                "nbd_sound_power": round(nbd_sound_power, 2),
                "nbd_pred_in_room": round(nbd_pred_in_room, 2),
                "sm_pred_in_room": round(sm_pred_in_room, 2),
                "sm_sound_power": round(sm_sound_power, 2),
                "pref_score_wsub": round(pref_wsub, 1),
            }
            if not skip_full:
                if aad_on_axis != -1.0:
                    ratings["aad_on_axis"] = round(aad_on_axis, 2)
                if lfx_hz != -1.0:
                    ratings["lfx_hz"] = int(pow(10, lfx_hz))  # in Hz
                if lfq_db != -1.0:
                    ratings["lfq"] = round(lfq_db, 2)
                ratings["pref_score"] = round(pref, 1)
        else:
            ratings = {
                "nbd_on_axis": nbd_on_axis,
                "nbd_listening_window": nbd_listening_window,
                "nbd_sound_power": nbd_sound_power,
                "nbd_pred_in_room": nbd_pred_in_room,
                "sm_pred_in_room": sm_pred_in_room,
                "sm_sound_power": sm_sound_power,
                "pref_score_wsub": pref_wsub,
            }
            if not skip_full:
                ratings["aad_on_axis"] = (aad_on_axis,)
                if lfx_hz is not None:
                    ratings["lfx_hz"] = pow(10, lfx_hz)
                if lfq_db is not None:
                    ratings["lfq"] = lfq_db
                ratings["pref_score"] = pref
        logger.info("Ratings: {0}".format(ratings))
        return ratings
    except ValueError as e:
        logger.error("{0}".format(e))
        return None


def scores(df_speaker):
    pir = None
    spin = None
    if "CEA2034" in df_speaker:
        spin = df_speaker["CEA2034"]
        pir = spin.get("Estimated In-Room Response", None)
        if pir is None:
            logger.error("Don t find pir {} v1".format(df_speaker["CEA2034"].keys()))
    elif "CEA2034_unmelted" in df_speaker:
        spin = graph_melt(df_speaker["CEA2034_unmelted"])
        if "Estimated In-Room Response" in df_speaker["CEA2034_unmelted"]:
            pir = graph_melt(
                df_speaker["CEA2034_unmelted"]["Estimated In-Room Response"]
            )
        else:
            logger.error(
                "Don t find pir {} v2".format(df_speaker["CEA2034_unmelted"].keys())
            )

    if pir is None:
        logger.error("pir is None, recompute")
        splH = df_speaker["SPL Horizontal_unmelted"]
        splV = df_speaker["SPL Vertical_unmelted"]
        pir = graph_melt(estimated_inroom_HV(splH, splV))

    return speaker_pref_rating(cea2034=spin, df_pred_in_room=pir, rounded=False)
