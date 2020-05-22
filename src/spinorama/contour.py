import collections
import logging
import math
import numpy as np
import pandas as pd
from scipy import ndimage
from astropy.convolution import Gaussian2DKernel, RickerWavelet2DKernel

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


Triangle = collections.namedtuple("Triangle", "v1 v2 v3")
Edge = collections.namedtuple("Edge", "e1 e2")

def cross_point(e1, e2, z, z_target):
    ratio = (z_target-z[e2])/(z[e1]-z[e2])
    if ratio < 0 or ratio > 1:
        print('debug e1={0} e2={1} z=[{2}, {3}] z_target={4}'.format(e1, e2, z[e1], z[e2], z_target))
        print('Out of bounds: ratio={0}'.format(ratio))
    return (ratio*e1[0] + (1-ratio)*e2[0],
            ratio*e1[1] + (1-ratio)*e2[1])


def trapeze1(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_low)
    p2 = cross_point(striangle[0], striangle[1], z, z_high)
    p3 = cross_point(striangle[0], striangle[2], z, z_high)
    p4 = cross_point(striangle[0], striangle[2], z, z_low)
    # print('p1={0} p2={1} p3={2} p4={3}'.format(p1, p2, p3, p4))
    return [p1 , p2, p3, p4]


def trapeze2(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[2], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_high)
    p3 = cross_point(striangle[1], striangle[2], z, z_high)
    p4 = cross_point(striangle[1], striangle[2], z, z_low)
    # print('p1={0} p2={1} p3={2} p4={3}'.format(p1, p2, p3, p4))
    return [p1 , p2, p3, p4]


def trapeze3(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_low)
    # print('p1={0} p2={1}'.format(p1, p2))
    return [p1 , p2, striangle[2], striangle[1]]


def trapeze4(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[1], striangle[2], z, z_high)
    p2 = cross_point(striangle[0], striangle[2], z, z_high)
    return [striangle[0], striangle[1], p1, p2]


def triangle1(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_high)
    p2 = cross_point(striangle[0], striangle[2], z, z_high)
    return [p1 , p2, striangle[0]]


def triangle2(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[1], striangle[2], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_low)
    return [p1 , p2, striangle[2]]


def pentagon(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_low)
    p3 = cross_point(striangle[0], striangle[2], z, z_high)
    p4 = cross_point(striangle[1], striangle[2], z, z_high)
    return [p1 , p2, p3, p4, striangle[1]]



def triangle2band(triangle, z, z_low, z_high):
    if triangle[0] == triangle[1] or triangle[2] == triangle[1] or triangle[0] == triangle[2]:
        print('incorrect: {0}'.format(triangle))
        return None
    # sort triangle in order of z
    striangle = [p[1] for p in sorted(enumerate(triangle), key=lambda p: z[p[1]])]
    if striangle[0] == striangle[1] or striangle[2] == striangle[1] or striangle[0] == striangle[2]:
        print('incorrect: {0}'.format(striangle))
        return None

    # 3 states
    below = [v for v in striangle if z[v] < z_low]
    within = [v for v in striangle if z[v] >= z_low and z[v] < z_high]
    above = [v for v in striangle if z[v] >= z_high]

    if len(below) == 3 or len(above) == 3:
        return []

    polygon = None
    # trapeze case
    if len(below) == 1 and len(above) == 2:
        polygon = trapeze1(striangle, z, z_low, z_high)
    elif len(below) == 2 and len(above) == 1:
        polygon = trapeze2(striangle, z, z_low, z_high)
    elif len(within) == 2 and len(below) == 1:
        polygon = trapeze3(striangle, z, z_low, z_high)
    elif len(within) == 2 and len(above) == 1:
        polygon = trapeze4(striangle, z, z_low, z_high)
    elif len(within) == 3:
        polygon = [striangle[0], striangle[1], striangle[2]] 
    elif len(above) == 2 and len(within) == 1:
        polygon = triangle1(striangle, z, z_low, z_high)
    elif len(below) == 2 and len(within) == 1:
        polygon = triangle2(striangle, z, z_low, z_high)
    elif len(below) == 1 and len(within) == 1 and len(above) == 1:
        polygon = pentagon(striangle, z, z_low, z_high)
    else:
        print('no match error')
    return polygon


def find_isoband(grid_x, grid_y, grid_z, z_low, z_high):
    # find iso band on a x,y grid where z is the elevation
    # z_low and z_high define the boundaries of the band
    triangles = []
    for ix in range(0, len(grid_x)-1):
        x1 = grid_x[0][ix]
        x2 = grid_x[0][ix+1]
        for iy in range(0, len(grid_y)-1):
            y1 = grid_y[iy][0]
            y2 = grid_y[iy+1][0]
            triangles.append(Triangle((x1,y1), (x2,y1), (x2,y2)))
            triangles.append(Triangle((x1,y1), (x1,y2), (x2,y2)))

    elevation = {}
    for ix in range(0, len(grid_x)):
        for iy in range(0, len(grid_y)):
            elevation[(grid_x[0][ix], grid_y[iy][0])] = grid_z[ix][iy]

    isoband = []
    for triangle in triangles:
        band = triangle2band(triangle, elevation, z_low, z_high)
        if len(band) > 0:
            isoband.append([[p[0], p[1]] for p in band]+ [[band[0][0], band[0][1]]])

    return isoband


def find_isobands(grid_x, grid_y, grid_z, z_values):
    # find iso bands on a x,y grid where z is the elevation, z_values define the boundaries of the bands
    # return data in geojson to please altair
    geojson = {}
    geojson['type'] = 'FeatureCollection'
    geojson['features'] = []
    for z in range(0, len(z_values)-1):
        z_low = z_values[z]
        z_high = z_values[z+1]
        isobands = find_isoband(grid_x, grid_y, grid_z, z_low, z_high)
        geojson['features'].append({ 
            'type': 'Feature',
            'geometry': {
                'type': 'MultiPolygon',
                'coordinates': [isobands],
                },
            'properties': {
                'z_low': z_low,
                'z_high': z_high,
                },
            }
        )
    return geojson

    
            
