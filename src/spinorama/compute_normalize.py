#                                                  -*- coding: utf-8 -*-
import logging

import numpy as np
import pandas as pd


# pd.set_option('display.max_rows', None)
logger = logging.getLogger("spinorama")


def unify_freq(dfs):
    """unify_freq

    There is no guaranty that all frequency points are the same on all graphs. This is
    an issue for operations on multiple graphs at the same time. Let's merge all freq
    points such that all graphs have exactlty the same set of points and thus the same shape.

    This use linear interpolation for missing points and can generate some NaN in the frame.
    Rows (Freq) with at least 1 NaN are removed.

    dfs: a spinorama stored into a panda DataFrame
    """
    on = (
        dfs[dfs.Measurements == "On Axis"]
        .rename(columns={"dB": "ON"})
        .set_index("Freq")
    )
    lw = (
        dfs[dfs.Measurements == "Listening Window"]
        .rename(columns={"dB": "LW"})
        .set_index("Freq")
    )
    er = (
        dfs[dfs.Measurements == "Early Reflections"]
        .rename(columns={"dB": "ER"})
        .set_index("Freq")
    )
    sp = (
        dfs[dfs.Measurements == "Sound Power"]
        .rename(columns={"dB": "SP"})
        .set_index("Freq")
    )
    logger.debug(
        "unify_freq: on.shape={0} lw.shape={1} er.shape={2} sp.shape={3}".format(
            on.shape, lw.shape, er.shape, sp.shape
        )
    )

    # align 2 by 2
    align = on.align(lw, axis=0)
    logger.debug("on+lw shape: {0}".format(align[0].shape))
    if er.shape[0] != 0:
        align = align[0].align(er, axis=0)
        logger.debug("+er shape: {0}".format(align[0].shape))
    else:
        logger.debug("skipping ER")
    all_on = align[0].align(sp, axis=0)
    logger.debug("+sp shape: {0}".format(all_on[0].shape))
    # realigned with the largest frame
    all_lw = None
    if lw.shape[0] != 0:
        all_lw = all_on[0].align(lw, axis=0)
        logger.debug("Before call: {0} and {1}".format(er.shape, all_on[0].shape))
    all_er = None
    if er.shape[0] != 0:
        all_er = all_on[0].align(er, axis=0)
    all_sp = None
    if sp.shape[0] != 0:
        all_sp = all_on[0].align(sp, axis=0)
    # expect all the same
    logger.debug(
        "Shapes ON {0} LW {1} ER {2} SP {3}".format(
            all_on[0].shape if all_on is not None else "--",
            all_lw[1].shape if all_lw is not None else "--",
            all_er[1].shape if all_er is not None else "--",
            all_sp[1].shape if all_sp is not None else "--",
        )
    )
    # extract right parts and interpolate
    a_on = all_on[0].drop("Measurements", axis=1).interpolate()
    a_lw = None
    if lw.shape[0] != 0:
        a_lw = all_lw[1].drop("Measurements", axis=1).interpolate()
    a_er = None
    if er.shape[0] != 0:
        a_er = all_er[1].drop("Measurements", axis=1).interpolate()
    a_sp = None
    if sp.shape[0] != 0:
        a_sp = all_sp[1].drop("Measurements", axis=1).interpolate()
    # expect all the same
    logger.debug(
        "Shapes: {0} {1} {2}".format(
            a_lw.shape if a_lw is not None else "--",
            a_er.shape if a_er is not None else "--",
            a_sp.shape if a_sp is not None else "--",
        )
    )
    # remove NaN numbers
    data = {}
    data["Freq"] = a_lw.index
    data["On Axis"] = a_on.ON
    if a_lw is not None:
        data["Listening Window"] = a_lw.LW
    if a_er is not None:
        data["Early Reflections"] = a_er.ER
    if a_sp is not None:
        data["Sound Power"] = a_sp.SP

    res2 = pd.DataFrame(data)

    # print(res2.head())
    return res2.dropna().reset_index(drop=True)


def normalize_mean(df):
    # this is messy: first version was using On Axis data from Spinorama but some
    # speaker don't have it.
    mean = None
    if "dB" in df.keys():
        on = df[df.Measurements == "On Axis"]
        mean = np.mean(on.loc[(on.Freq > 500) & (on.Freq < 10000)].dB)
    elif "On Axis" in df.columns:
        on = df[["Freq", "On Axis"]]
        mean = np.mean(on.loc[(on.Freq > 500) & (on.Freq < 10000)].dB)

    return mean


def normalize_cea2034(dfc, mean):
    # use a copy to be able to run it multiple times in one session
    df = dfc.copy()

    for measurement in (
        "On Axis",
        "Listening Window",
        "Sound Power",
        "Early Reflections",
    ):
        if df.loc[df.Measurements == measurement, "dB"].shape[0] != 0:
            df.loc[df.Measurements == measurement, "dB"] -= mean

    # 3 different cases Princeton+ASR and Vendors
    offset = 0
    if "DI offset" in df.Measurements.unique():
        offset = np.mean(df[df.Measurements == "DI offset"].dB)

    for measurement in ("Sound Power DI", "Early Reflections DI", "DI offset"):
        if df.loc[df.Measurements == measurement, "dB"].shape[0] != 0:
            df.loc[df.Measurements == measurement, "dB"] -= offset
            s = df.loc[df.Measurements == measurement, "dB"]
            logger.debug(
                "{0} min={1} max={2}".format(measurement, np.min(s), np.max(s))
            )

    return df


def normalize_graph(dfc, mean):
    df = dfc.copy()
    df.dB -= mean
    return df


def pprint(df):
    for m in df.Measurements.unique():
        df_min = np.min(df[df.Measurements == m].dB)
        df_max = np.max(df[df.Measurements == m].dB)
        print("{0} {1} {2}".format(df_min, df_max, m))


def resample(df, target_size):
    len_freq = df.shape[0]
    if len_freq > 2 * target_size:
        roll = int(len_freq / target_size)
        sampled = df.loc[df.Freq.rolling(roll).max()[1::roll].index, :]
        return sampled
    return df
