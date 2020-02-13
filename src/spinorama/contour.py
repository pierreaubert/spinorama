import numpy as np
from .load import graph_melt


def compute_contour(dfu):
    vrange = []
    # normalize dB values wrt on axis
    dfm = dfu.copy()
    for c in dfu.columns:
        if c != 'Freq' and c != 'On-Axis':
            dfm[c] = dfu[c] - dfu['On-Axis']
            angle = int(c[:-1])
            vrange.append(angle)
        if c == 'On-Axis':
            vrange.append(0)
    dfm['On-Axis'] = 0
    # print([(math.floor(min*10)/10, math.floor(max*10)/10) for (min,max) in zip(dfm.min(), dfm.max())])

    # melt
    dfm = graph_melt(dfm)
    # compute numbers of measurements
    nm = dfm.Measurements.nunique()
    nf = int(len(dfm.index) / nm)
    # print((nm,nf))
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


kernel33 = [
    [1, 1, 1],
    [1, 3, 1],
    [1, 1, 1]
]
offset33 = 1
sum33 = np.array(kernel33).sum()
kernel55 = [
    [1, 1, 1, 1, 1],
    [1, 3, 3, 3, 1],
    [1, 3, 9, 3, 1],
    [1, 3, 3, 3, 1],
    [1, 1, 1, 1, 1]
]
offset55 = 2
sum55 = np.array(kernel55).sum()


def smooth(z, i, j, zx, zy, offset, kernel, total):
    s = 0
    if not (not (i < offset) and not ((zx - i) < offset) and not (j < offset) and not ((zy - j) < offset)):
        s = z[i][j]
    else:
        s = 0
        for ii in range(-offset, offset):
            for jj in range(-offset, offset):
                s += kernel[ii + offset][jj + offset] * z[i + ii][j + jj]
        s /= total
    return s


def smooth2D(z):
    zx = len(z)
    zy = len(z[0])
    kernel = kernel55
    offset = offset55
    kernel_total = sum55
    return [[smooth(z, i, j, zx, zy, offset, kernel, kernel_total)
             for j in range(0, zy)] for i in range(0, zx)]


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
