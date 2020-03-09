import logging
import math
import numpy as np
from scipy import ndimage
from astropy.convolution import Gaussian2DKernel

from .load import graph_melt


def compute_contour(dfu):
    vrange = []
    # normalize dB values wrt on axis
    dfm = dfu.copy()
    for c in dfu.columns:
        if c != 'Freq' and c != 'On Axis':
            dfm[c] = dfu[c] - dfu['On Axis']
            angle = int(c[:-1])
            vrange.append(angle)
        if c == 'On Axis':
            vrange.append(0)
    dfm['On Axis'] = 0

    # melt
    dfm = graph_melt(dfm)
    # compute numbers of measurements
    nm = dfm.Measurements.nunique()
    nf = int(len(dfm.index) / nm)
    logging.debug('unique={:d} nf={:d}'.format(nm,nf))
    # index grid on a log scale log 2 ±= 0.3
    hrange = np.floor(np.logspace(1.0+math.log10(2), 4.0+math.log10(2), nf))
    # print(vrange)
    # sort data per experiments (not usefull for DataFrame but for 2d array)
    # anglemin = np.array(vrange).min()/10
    # perm = [int(vrange[i]/10-anglemin) for i in range(0, len(vrange))]
    # pvrange = [vrange[perm[i]] for i in range(0,len(vrange))]
    # 3d mesh
    af, am = np.meshgrid(hrange, vrange)
    # since it is melted generate slices
    az = np.array([dfm.dB[nf * i:nf * (i + 1)] for i in range(0, nm)])
    # smooth values to .1
    # az = np.floor(az*10)/10
    return (af, am, az)


def reshape(x, y, z, nscale):
    nx, ny = x.shape
    # expand x-axis and y-axis
    lxi = [np.linspace(x[0][i], x[0][i+1], nscale, endpoint=False) for i in range(0, len(x[0])-1)]
    lx = [i for j in lxi for i in j] + [x[0][len(x[0])-1] for i in range(0, nscale)]
    nly = (nx-1)*nscale+1
    ly = np.linspace(np.min(y), np.max(y), nly)
    # on this axis, cheat by 1% to generate round values that are better in legend
    # round off values close to those in ykeep
    ykeep = [20, 30, 100, 200, 300, 400, 500,
             1000, 2000, 3000, 4000, 5000,
             10000, 20000]
    def close(x1, x2, ykeep):
        for z in ykeep:
            if abs((x1-z)/z) < 0.01 and z<x2:
                ykeep.remove(z)
                return z
        return x1
    lx2 = [close(lx[i], lx[i+1], ykeep) for i in range(0,len(lx)-1)]
    lx2 = np.append(lx2, lx[-1])
    # build the mesh
    rx, ry = np.meshgrid(lx2, ly)
    # copy paste the values of z into rz 
    rzi = np.repeat(z[:-1], nscale, axis=0)
    rzi_x, rzi_y = rzi.shape
    rzi2 = np.append(rzi, z[-1]).reshape(rzi_x+1, rzi_y)
    rz = np.repeat(rzi2, nscale, axis=1)
    # print(rx.shape, ry.shape, rz.shape)
    return (rx, ry, rz)


def compute_contour_smoothed(dfu, nscale=5):
    # compute contour
    x, y, z = compute_contour(dfu)
    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        return (None, None, None)
    # std_dev = 1
    kernel = Gaussian2DKernel(1, mode='oversample', factor=10)
    # extend array by x5
    rx, ry, rz = reshape(x, y, z, nscale)
    # convolve with kernel
    rzs = ndimage.convolve(rz, kernel.array, mode='mirror')
    # return
    return (rx, ry, rzs)


def near(t, v):
    w = 0
    d = abs(t[0] - v)
    for i in range(len(t)):
        c = abs(t[i] - v)
        if c < d:
            d = c
            w = i
    # print(w, d)
    if v < 0 and t[w] > v:
        return None, 0
    if v > 0 and t[w] < v:
        return None, 0
    # linear interpolation (w-1, t[w-1]) (w,t[w])  ax+b=v x=>(v-b)/a
    if w > 1 and t[w] != 0 and d != 0:
        w = w - (t[w] - t[w - 1]) / t[w]
        d = 0
    return w, d


def compute_isoline(x, y, z, value):
    data = np.array(z)
    # print(len(data))
    isoline = [near(data[i], -3) for i in range(0, len(data))]
    return isoline
