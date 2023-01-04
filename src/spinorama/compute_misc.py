# -*- coding: utf-8 -*-
import logging

import bisect
import math
import numpy as np
import pandas as pd
from scipy import stats

from .load_misc import graph_melt, sort_angles
from .compute_scores import octave

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
    on = dfs[dfs.Measurements == "On Axis"].rename(columns={"dB": "ON"}).set_index("Freq")
    lw = dfs[dfs.Measurements == "Listening Window"].rename(columns={"dB": "LW"}).set_index("Freq")
    er = dfs[dfs.Measurements == "Early Reflections"].rename(columns={"dB": "ER"}).set_index("Freq")
    sp = dfs[dfs.Measurements == "Sound Power"].rename(columns={"dB": "SP"}).set_index("Freq")
    logger.debug(
        "unify_freq: on.shape={0} lw.shape={1} er.shape={2} sp.shape={3}".format(on.shape, lw.shape, er.shape, sp.shape)
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
            all_on[0].shape if all_on is not None and len(all_on) > 0 else "--",
            all_lw[1].shape if all_lw is not None and len(all_lw) > 1 else "--",
            all_er[1].shape if all_er is not None and len(all_er) > 1 else "--",
            all_sp[1].shape if all_sp is not None and len(all_sp) > 1 else "--",
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
    data["Freq"] = a_on.index
    if a_on is not None and "ON" in a_on.keys() and len(a_on.ON) == len(a_on.index):
        data["On Axis"] = a_on.ON
    if a_lw is not None and "LW" in a_lw.keys() and len(a_lw.LW) == len(a_on.index):
        data["Listening Window"] = a_lw.LW
    if a_er is not None and "ER" in a_er.keys() and len(a_er.ER) == len(a_on.index):
        data["Early Reflections"] = a_er.ER
    if a_sp is not None and "SP" in a_sp.keys() and len(a_sp.SP) == len(a_on.index):
        data["Sound Power"] = a_sp.SP

    res2 = pd.DataFrame(data)

    # print(res2.head())
    return res2.dropna().reset_index(drop=True)


def resample(df: pd.DataFrame, target_size: int):
    # resample dataframe to minimize size
    len_freq = df.shape[0]
    if len_freq > 2 * target_size:
        roll = int(len_freq / target_size)
        # sampled = df.loc[df.Freq.rolling(roll).max()[1::roll].index, :]
        sampled = df.loc[df.Freq.rolling(roll).max().iloc[1::roll].index, :]
        return sampled
    return df


def compute_contour(dfm_in):
    # generate 3 arrays x, y, z suitable for computing equilevels
    dfm = sort_angles(dfm_in)
    # check if we have -180
    if "180°" in dfm.keys() and "-180°" not in dfm.keys():
        dfm.insert(1, "-180°", dfm_in["180°"])

    # print('debug -- 180 -- min {} max {}'.format(np.min(dfm_in["180°"]), np.max(dfm_in["180°"])))
    # print(dfm.keys())

    # get a list of columns
    vrange = []
    for c in dfm.columns:
        if c not in ("Freq", "On Axis"):
            angle = int(c[:-1])
            vrange.append(angle)
        if c == "On Axis":
            vrange.append(0)

    vrange = list(sorted(vrange))

    # print("nf={:d} vrange={}".format(len(vrange), vrange))
    hrange = dfm_in.Freq
    af, am = np.meshgrid(hrange, vrange)
    dfm.drop("Freq", axis=1, inplace=True)
    az = dfm.T.to_numpy()
    # if af.shape != am.shape or af.shape != az.shape:
    #   print(
    #       "Shape mismatch af={0} am={1} az={2}".format(af.shape, az.shape, am.shape)
    #   )
    return (af, am, az)


def reshape(x, y, z, nscale):
    # change the shape and rescale it by nscale
    nx, _ = x.shape
    # expand x-axis and y-axis
    lxi = [np.linspace(x[0][i], x[0][i + 1], nscale, endpoint=False) for i in range(0, len(x[0]) - 1)]
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
    deg0 = bisect.bisect(am.T[0], 0) - 1
    # parameters
    kHz1 = bisect.bisect(af[0], 1000)
    kHz10 = bisect.bisect(af[0], 10000)
    dbLess = -6
    # 2% tolerance
    tol = 0.0001
    #
    zero = az[deg0][kHz1:kHz10]
    # print('debug af {} am {} az {}'.format(af.shape, am.shape, az.shape))
    # print('debug af {}'.format(af))
    # print('debug am {}'.format(am.T[deg0]))
    # print('debug az {}'.format(az))
    # print('debug 1kHz at pos{} 10kHz at pos {} def0 at pos {}'.format(kHz1, kHz10, deg0))
    def linear_eval(x: float) -> float:
        xp1 = int(x)
        xp2 = xp1 + 1
        zp1 = az[xp1][kHz1:kHz10]
        zp2 = az[xp2][kHz1:kHz10]
        # linear interpolation
        zp = zp1 + (x - xp1) * (zp2 - zp1)
        # normˆ2 (z-(-6dB))
        return np.linalg.norm(zp - zero - dbLess)

    def linear_eval_octave(x: float) -> float:
        xp1 = int(x)
        xp2 = xp1 + 1
        per_octave = []
        for (bmin, bcenter, bmax) in octave(2):
            # 100hz to 16k hz
            if bmin < 1000 or bmax > 10000:
                continue
            kmin = bisect.bisect(af[0], bmin)
            kmax = bisect.bisect(af[0], bmax)
            kzero = az[deg0][kmin:kmax]
            zp1 = az[xp1][kmin:kmax]
            zp2 = az[xp2][kmin:kmax]
            # linear interpolation
            zp = zp1 + (x - xp1) * (zp2 - zp1)
            # normˆ2 (z-(-6dB))
            # print('{}hz {} {}hz {} {}'.format(bmin, kmin, bmax, kmax, zp))
            per_octave.append(np.linalg.norm(zp - kzero - dbLess))
        # print('x={} min= {} per_octave={}'.format(x, np.min(per_octave), per_octave))
        # print("x={} min= {}".format(x, np.min(per_octave)))
        return np.min(per_octave)

    eval_count = 180  # 180

    space_p = np.linspace(deg0, len(am.T[0]) - 2, eval_count)
    eval_p = [linear_eval(x) for x in space_p]
    min_p = np.min(eval_p) * (1.0 + tol)
    # all minimum in this 1% band from min
    pos_g = [i for i, v in enumerate(eval_p) if v < min_p]
    # be generous and take best one (widest)
    if len(pos_g) > 1:
        pos_p = pos_g[0]
    else:
        pos_p = np.argmin(eval_p)
    # translate in deg
    angle_p = pos_p * 180 / eval_count
    # print('debug: space_p boundaries [{}, {}] steps {}'.format(deg0, len(am.T[0])-2, eval_count))
    # print('debug space_p: {}'.format(space_p))
    # print('debug eval_p: {}'.format(eval_p))
    # print('debug pos_g: {}'.format(pos_g))
    # print('debug: min_p {} angle_p {}'.format(min_p, angle_p))

    space_m = np.linspace(0, deg0 - 1, eval_count)
    eval_m = [linear_eval_octave(x) for x in space_m]
    min_m = np.min(eval_m) * (1.0 + tol)
    pos_g = [i for i, v in enumerate(eval_m) if v < min_m]
    if len(pos_g) > 1:
        pos_m = pos_g[-1]
    else:
        pos_m = np.argmin(eval_m)
    # translate in deg
    angle_m = pos_m * 180 / eval_count - 180
    # print('debug: space_m boundaries [{}, {}] steps {}'.format(0, deg0-1, eval_count))
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
    # print('max {} max {}'.format(np.max(np.max(z)), np.max(np.max(z))))
    return (x, y, z)


def compute_directivity_deg_v2(df) -> tuple[float, float, float]:

    # def compute(spl, r):
    #     mean = spl[((spl.Freq>1000) & (spl.Freq<10000))]['On Axis'].mean()
    #     for k in r:
    #         key = '{}°'.format(k)
    #         db = spl[((spl.Freq>1000) & (spl.Freq<6000))][key] - mean
    #         pos = db.min()
    #         # print('key {}  pos {} {}'.format(key, pos, db.values))
    #         if pos < -6:
    #             return k
    #     return 0

    def compute(spl, r):
        mean = spl[((spl.Freq > 1000) & (spl.Freq < 10000))]["On Axis"].mean()
        for k in r:
            key = "{}°".format(k)
            db = spl[((spl.Freq > 1000) & (spl.Freq < 6000))][key] - mean
            # smooth on 5 points
            pos = db.ewm(span=10).mean().min()
            # print('key {}  pos {} {}'.format(key, pos, db.values))
            if pos < -6:
                return k
        return 0

    dir_p = compute(df, range(10, 180, 10))
    dir_m = compute(df, range(-10, -180, -10))

    # print('dir_p {}'.format(dir_p))
    return float(dir_p), float(dir_m), float((dir_p + dir_m) / 2)


def savitzky_golay(y, window_size, order, deriv=0, rate=1):
    r"""Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    Examples
    --------
    t = np.linspace(-4, 4, 500)
    y = np.exp( -t**2 ) + np.random.normal(0, 0.05, t.shape)
    ysg = savitzky_golay(y, window_size=31, order=4)
    import matplotlib.pyplot as plt
    plt.plot(t, y, label='Noisy signal')
    plt.plot(t, np.exp(-t**2), 'k', lw=1.5, label='Original signal')
    plt.plot(t, ysg, 'r', label='Filtered signal')
    plt.legend()
    plt.show()
    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """
    try:
        window_size = abs(int(window_size))
        order = abs(int(order))
    except ValueError as msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size - 1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * math.factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs(y[1 : half_window + 1][::-1] - y[0])
    lastvals = y[-1] + np.abs(y[-half_window - 1 : -1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve(m[::-1], y, mode="valid")


def dist_point_line(x, y, A, B, C):
    return abs(A * x + B * y + C) / math.sqrt(A * A + B * B)


def compute_statistics(df, measurement, min_freq, max_freq):
    restricted = df.loc[(df.Freq > min_freq) & (df.Freq < max_freq)]
    spl = restricted[measurement]
    slope, intercept, r, p, se = stats.linregress(x=np.log10(restricted["Freq"]), y=spl)
    # regression line
    line = [slope * math.log10(f) + intercept for f in df.Freq]
    # distance between each point and the regression line
    dist = [dist_point_line(math.log10(f), db, slope, -1, intercept) for f, db in zip(df.Freq,spl)]
    # build an histogram to see where the deviation is above each treshhole
    hist = np.histogram(dist, bins=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4.0, 4.5, 5.0])
    # 3 = math.log10(20000)-math.log10(20)
    # 11 octaves between 20Hz and 20kHz
    db_per_octave = slope * 3 / 11
    return db_per_octave, hist, np.max(dist)
