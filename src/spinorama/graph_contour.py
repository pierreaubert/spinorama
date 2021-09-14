# -*- coding: utf-8 -*-
import logging
import math
import numpy as np
from scipy import ndimage
from astropy.convolution import Gaussian2DKernel

from .load_misc import graph_melt

logger = logging.getLogger("spinorama")


def normalize_onaxis(dfu):
    dfm = dfu.copy()
    for c in dfu.columns:
        if c not in ("Freq", "On Axis"):
            dfm[c] -= dfu["On Axis"]
        if c == "180°":
            dfm.insert(1, "-180°", dfu["180°"] - dfu["On Axis"])
    dfm["On Axis"] = 0
    return dfm


def compute_contour(dfu):
    # normalize dB values wrt on axis
    dfm = normalize_onaxis(dfu)

    # get a list of columns
    vrange = []
    for c in dfm.columns:
        if c not in ("Freq", "On Axis"):
            angle = int(c[:-1])
            vrange.append(angle)
        if c == "On Axis":
            vrange.append(0)

    # y are inverted for display
    vrange = list(reversed(vrange))

    # melt
    dfm = graph_melt(dfm)
    # compute numbers of measurements
    nm = dfm.Measurements.nunique()
    nf = int(len(dfm.index) / nm)
    logger.debug("unique={:d} nf={:d}".format(nm, nf))
    # index grid on a log scale log 2 ±= 0.3
    hrange = np.logspace(1.0 + math.log10(2), 4.0 + math.log10(2), nf)
    # 3d mesh
    af, am = np.meshgrid(hrange, vrange)
    # since it is melted generate slices
    az = np.array([dfm.dB[nf * i : nf * (i + 1)] for i in range(0, nm)])
    if af.shape != am.shape or af.shape != az.shape:
        logger.error(
            "Shape mismatch af={0} am={1} az={2}".format(af.shape, az.shape, am.shape)
        )
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


def compute_contour_smoothed(dfu, nscale=5):
    # compute contour
    x, y, z = compute_contour(dfu)
    # z_range = np.max(z) - np.min(z)
    if 0 in (len(x), len(y), len(z)):
        return (None, None, None)
    # std_dev = 1
    kernel = Gaussian2DKernel(1, 5)
    # kernel = RickerWavelet2DKernel(4)
    # extend array by x5
    rx, ry, rz = reshape(x, y, z, nscale)
    # convolve with kernel
    rzs = ndimage.convolve(rz, kernel.array, mode="mirror")
    # normalize
    # rzs_range = np.max(rzs) - np.min(rzs)
    # if rzs_range > 0:
    #    rzs *= z_range / rzs_range
    return (rx, ry, rzs)


def compute_directivity_deg(af, am, az) -> tuple[float, float, float]:
    """ "compute +/- angle where directivity is most constant between 1kHz and 10kz"""

    # kHz1 = 110
    # kHz10 = 180
    def linear_eval(x: float) -> float:
        xp1 = int(x)
        xp2 = xp1 + 1
        zp1 = az[xp1][110:180]
        zp2 = az[xp2][110:180]
        # linear interpolation
        zp = zp1 + (x - xp1) * (zp2 - zp1)
        # normˆ2 (z-(-6dB))
        return np.linalg.norm(zp + 6)

    eval_count = 180

    space_p = np.linspace(int(len(am.T[0]) / 2), 1, eval_count)
    eval_p = [linear_eval(x) for x in space_p]
    # 1% tolerance
    tol = 0.1
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

    space_m = np.linspace(int(len(am.T[0]) / 2), len(am.T[0]) - 2, eval_count)
    eval_m = [linear_eval(x) for x in space_m]
    min_m = np.min(eval_m) * (1.0 + tol)
    pos_g = [i for i, v in enumerate(eval_m) if v < min_m]
    if len(pos_g) > 1:
        pos_m = pos_g[-1]
    else:
        pos_m = np.argmin(eval_m)
    # translate in deg
    angle_m = -pos_m * 180 / eval_count

    return float(angle_p), float(angle_m), float((angle_p - angle_m) / 2)
