#                                                  -*- coding: utf-8 -*-
import logging
import math
import numpy as np
from scipy import ndimage
from astropy.convolution import Gaussian2DKernel

from .load import graph_melt

def normalize1(dfu):
    dfm = dfu.copy()
    for c in dfu.columns:
        if c != 'Freq' and c != 'On Axis':
            dfm[c] = 20*np.log10(dfu[c]/dfu['On Axis'])
    dfm['On Axis'] = 0
    return dfm

def normalize2(dfu):
    dfm = dfu.copy()
    for c in dfu.columns:
        if c != 'Freq' and c != 'On Axis':
            dfm[c] -= dfu['On Axis']
    dfm['On Axis'] = 0
    return dfm

def compute_contour(dfu):
    # normalize dB values wrt on axis
    dfm = normalize2(dfu)

    # get a list of sorted columns
    vrange = []
    for c in dfu.columns:
        if c != 'Freq' and c != 'On Axis':
            angle = int(c[:-1])
            vrange.append(angle)
        if c == 'On Axis':
            vrange.append(0)

    # reorder from -90 to +270 and not -180 to 180 to be closer to other plots
    def a2v(angle):
        if angle == 'Freq':
            return -1000
        elif angle == 'On Axis':
            return 0
        iangle = int(angle[:-1])
        if iangle <-90:
            return iangle+270
        return iangle
        
    dfu = dfu.reindex(columns=sorted(dfu.columns, key=lambda a: a2v(a)))
    # print(dfu.keys())
    # melt
    dfm = graph_melt(dfm)
    # compute numbers of measurements
    nm = dfm.Measurements.nunique()
    nf = int(len(dfm.index) / nm)
    logging.debug('unique={:d} nf={:d}'.format(nm,nf))
    # index grid on a log scale log 2 ±= 0.3
    hrange = np.logspace(1.0+math.log10(2), 4.0+math.log10(2), nf)
    # print(vrange)
    # sort data per experiments (not usefull for DataFrame but for 2d array)
    # anglemin = np.array(vrange).min()/10
    # perm = [int(vrange[i]/10-anglemin) for i in range(0, len(vrange))]
    # pvrange = [vrange[perm[i]] for i in range(0,len(vrange))]
    # 3d mesh
    af, am = np.meshgrid(hrange, vrange)
    # since it is melted generate slices
    az = np.array([dfm.dB[nf * i:nf * (i + 1)] for i in range(0, nm)])
    if af.shape != am.shape or af.shape != az.shape:
        logging.error('Shape mismatch af={0} am={1} az={2}'.format(af.shape, az.shape, am.shape))
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
    kernel = Gaussian2DKernel(1, 5)
    # kernel = RickerWavelet2DKernel(4)
    # extend array by x5
    rx, ry, rz = reshape(x, y, z, nscale)
    # convolve with kernel
    rzs = ndimage.convolve(rz, kernel.array, mode='mirror')
    # return
    return (rx, ry, rzs)



