import logging
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
    hrange = np.floor(np.logspace(1.3, 4.3, nf))
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
    # linear axis
    lx = np.linspace(np.min(y), np.max(y), nx*nscale)
    # this is not, interpolate between each point
    lyi = [np.linspace(x[0][i], x[0][i+1], nscale, endpoint=False)
           for i in range(0, len(x[0])-1)]
    # flatten then pad with the last value
    ly = [i for j in lyi for i in j] + \
        [x[0][len(x[0])-1] for i in range(0, nscale)]
    # build the mesh (reverse order)
    rx, ry = np.meshgrid(ly, lx)
    # copy paste the values of z into rz
    rz = np.repeat(np.repeat(z, nscale, axis=1), nscale, axis=0)
    return (rx, ry, rz)


def compute_contour_smoothed(dfu):
    # compute contour
    x, y, z = compute_contour(dfu)
    # std_dev = 1
    kernel = Gaussian2DKernel(1, mode='oversample', factor=10)
    # extend array by x5
    rx, ry, rz = reshape(x, y, z, 5)
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
