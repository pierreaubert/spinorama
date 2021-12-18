# -*- coding: utf-8 -*-
import logging

import bisect
import math
import numpy as np
import pandas as pd

from .load_misc import graph_melt

# pd.set_option('display.max_rows', None)
logger = logging.getLogger("spinorama")


def unify_freq(dfs: pd.DataFrame) -> pd.DataFrame:
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
    all_lw = pd.DataFrame()
    if lw.shape[0] != 0:
        all_lw = all_on[0].align(lw, axis=0)
        logger.debug("Before call: {0} and {1}".format(er.shape, all_on[0].shape))
    all_er = pd.DataFrame()
    if er.shape[0] != 0:
        all_er = all_on[0].align(er, axis=0)
    all_sp = pd.DataFrame()
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
    a_lw = pd.DataFrame()
    if lw.shape[0] != 0:
        a_lw = all_lw[1].drop("Measurements", axis=1).interpolate()
    a_er = pd.DataFrame()
    if er.shape[0] != 0:
        a_er = all_er[1].drop("Measurements", axis=1).interpolate()
    a_sp = pd.DataFrame()
    if sp.shape[0] != 0:
        a_sp = all_sp[1].drop("Measurements", axis=1).interpolate()
    # expect all the same
    logger.debug(
        "Shapes: {0} {1} {2}".format(
            a_lw.shape if not a_lw.empty else "--",
            a_er.shape if not a_er.empty else "--",
            a_sp.shape if not a_sp.empty else "--",
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


def resample(df: pd.DataFrame, target_size: int):
    len_freq = df.shape[0]
    if len_freq > 2 * target_size:
        roll = int(len_freq / target_size)
        sampled = df.loc[df.Freq.rolling(roll).max()[1::roll].index, :]
        return sampled
    return df


def compute_contour(dfm, min_freq):

    # get a list of columns
    vrange = []
    for c in dfm.columns:
        if c not in ("Freq", "On Axis"):
            angle = int(c[:-1])
            vrange.append(angle)
        if c == "On Axis":
            vrange.append(0)

    vrange = list(sorted(vrange))

    dfm = graph_melt(dfm)
    nm = dfm.Measurements.nunique()
    nf = int(len(dfm.index) / nm)
    # logger.debug("unique={:d} nf={:d}".format(nm, nf))
    hrange = np.logspace(math.log10(min_freq), 4.0 + math.log10(2), nf)
    af, am = np.meshgrid(hrange, vrange)
    az = np.array([dfm.dB[nf * i : nf * (i + 1)] for i in range(0, nm)])
    # if af.shape != am.shape or af.shape != az.shape:
    #    print(
    #        "Shape mismatch af={0} am={1} az={2}".format(af.shape, az.shape, am.shape)
    #    )
    return (af, am, az)


def reshape(x, y, z, nscale):
    nx, _ = x.shape
    # expand x-axis and y-axis
    lxi = [
        np.linspace(x[0][i], x[0][i + 1], nscale, endpoint=False)
        for i in range(0, len(x[0]) - 1)
    ]
    lx = [i for j in lxi for i in j] + [x[0][-1] for i in range(0, nscale)]
    nly = (nx - 1) * nscale + 1
    # keep order
    ly = []
    if y[0][0] > 0:
        ly = np.linspace(np.max(y), np.min(y), nly)
    else:
        ly = np.linspace(np.min(y), np.max(y), nly)

    # on this axis, cheat by 1% to generate round values that are better in legend
    # round off values close to those in ykeep
    xkeep = [
        20,
        30,
        100,
        200,
        300,
        400,
        500,
        1000,
        2000,
        3000,
        4000,
        5000,
        10000,
        20000,
    ]

    def close(x1, x2, xkeep):
        for z in xkeep:
            if abs((x1 - z) / z) < 0.01 and z < x2:
                xkeep.remove(z)
                return z
        return x1

    lx2 = [close(lx[i], lx[i + 1], xkeep) for i in range(0, len(lx) - 1)]
    lx2 = np.append(lx2, lx[-1])
    # build the mesh
    rx, ry = np.meshgrid(lx2, ly)
    # copy paste the values of z into rz
    rzi = np.repeat(z[:-1], nscale, axis=0)
    rzi_x, rzi_y = rzi.shape
    rzi2 = np.append(rzi, z[-1]).reshape(rzi_x + 1, rzi_y)
    rz = np.repeat(rzi2, nscale, axis=1)
    # print(rx.shape, ry.shape, rz.shape)
    return (rx, ry, rz)


def compute_directivity_deg(af, am, az) -> tuple[float, float, float]:
    """ "compute +/- angle where directivity is most constant between 1kHz and 10kz"""

    # print('debug af {} am {} az {}'.format(af.shape, am.shape, az.shape))
    # print('debug af {}'.format(af))
    # print('debug am {}'.format(am[17]))
    # print('debug az {}'.format(az))
    deg0 = bisect.bisect(am.T[0], 0) - 1
    kHz1 = bisect.bisect(af[0], 1000)
    kHz10 = bisect.bisect(af[0], 10000)
    zero = az[deg0][kHz1:kHz10]
    # print('debug {} {} {}'.format(kHz1, kHz10, deg0))
    def linear_eval(x: float) -> float:
        xp1 = int(x)
        xp2 = xp1 + 1
        zp1 = az[xp1][kHz1:kHz10]
        zp2 = az[xp2][kHz1:kHz10]
        # linear interpolation
        zp = zp1 + (x - xp1) * (zp2 - zp1)
        # normˆ2 (z-(-6dB))
        return np.linalg.norm(zp - zero + 6)

    eval_count = 180

    space_p = np.linspace(int(len(am.T[0]) / 2), len(am.T[0]) - 2, eval_count)
    eval_p = [linear_eval(x) for x in space_p]
    # 1% tolerance
    tol = 0.01
    min_p = np.min(eval_p) * (1.0 + tol)
    # all minimum in this 1% band from min
    pos_g = [i for i, v in enumerate(eval_p) if v < min_p]
    # be generous and take best one (widest)
    if len(pos_g) > 1:
        pos_p = pos_g[-1]
    else:
        pos_p = np.argmin(eval_p)
    # translate in deg
    angle_p = pos_p * 180 / eval_count
    # print('debug space_p: {}'.format(space_p))
    # print('debug eval_p: {}'.format(eval_p))
    # print('debug pos_g: {}'.format(pos_g))
    # print('debug: min_p {} angle_p {}'.format(min_p, angle_p))

    space_m = np.linspace(0, int(len(am.T[0]) / 2) - 1, eval_count)
    eval_m = [linear_eval(x) for x in space_m]
    min_m = np.min(eval_m) * (1.0 + tol)
    pos_g = [i for i, v in enumerate(eval_m) if v < min_m]
    if len(pos_g) > 1:
        pos_m = pos_g[-1]
    else:
        pos_m = np.argmin(eval_m)
    # translate in deg
    angle_m = -180 + pos_m * 180 / eval_count
    # print('debug space_m: {}'.format(space_m))
    # print('debug eval_m: {}'.format(eval_m))
    # print('debug pos_g: {}'.format(pos_g))
    # print('debug: min_m {} angle_m {}'.format(min_m, angle_m))

    return float(angle_p), float(angle_m), float((angle_p - angle_m) / 2)


def directivity_matrix(splH, splV):
    # print(splH.shape, splV.shape)
    # print(splH.head())
    # print(splV.head())
    if splH is None or splV is None:
        logger.info("Skipping directivty matrix, one measurement at least is empty")
        return None

    if splH.isnull().values.any() or splV.isnull().values.any():
        logger.info("Skipping directivty matrix, one value at least is NaN")
        return None

    n = splH.Freq.shape[0]
    r = np.floor(np.logspace(1.0 + math.log10(2), 4.0 + math.log10(2), n))
    x, y = np.meshgrid(r, r)
    splV = splV.set_index("Freq")
    splH = splH.set_index("Freq")
    zU = splV.dot(splH.T)
    zD = splV.dot(splV.T) * splH.dot(splH.T)
    # zD = np.matmult(np.matmult(splV, splV.T), np.matmult(splH, splH.T))
    # not completly sure why it is possible to get negative values
    zD[zD < 0] = 0.0
    z = zU / np.sqrt(zD) - 1.0
    # print('min {} max {}'.format(np.min(np.min(z)), np.max(np.max(z))))
    return (x, y, z)
