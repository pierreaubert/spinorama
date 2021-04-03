#                                                  -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd

from .load import sort_angles


logger = logging.getLogger("spinorama")


def angle2value(angle):
    if angle == "On Axis":
        return 0
    return int(angle[:-1])


def angle2str(a):
    """display an angle every 30 deg"""
    if a % 30 == 0:
        return "{:d}°".format(a)
    return ""


def join(anglelist):
    """return true if we should join the last point and the first one"""
    # 180-170-10 => join points
    delta = anglelist[-1] + anglelist[0]
    # print(delta)
    return bool(delta in (5, 10))


def angle_range(columns):
    amin = 0
    amax = 0
    for c in columns:
        if c != "Freq":
            v = angle2value(c)
            if v < 0:
                amin = min(amin, v)
            else:
                amax = max(amax, v)
    return amin, amax


def projection(anglelist, gridZ, hz):
    # map in 2d
    dbsX = [db * math.cos(a * math.pi / 180) for a, db in zip(anglelist, gridZ)]
    dbsY = [db * math.sin(a * math.pi / 180) for a, db in zip(anglelist, gridZ)]

    # join with first point (-180=180)
    # print('Calling project', anglelist)
    if join(anglelist):
        dbsX.append(dbsX[0])
        dbsY.append(dbsY[0])

    return dbsX, dbsY, [hz for i in range(0, len(dbsX))]


def circle(radius, anglelist):
    rg = range(0, len(anglelist))
    circleC = [radius for i in rg]
    circleX = [circleC[i] * math.cos(anglelist[i] * math.pi / 180) for i in rg]
    circleY = [circleC[i] * math.sin(anglelist[i] * math.pi / 180) for i in rg]
    # print('Calling circles', anglelist)
    if join(anglelist):
        circleX.append(circleX[0])
        circleY.append(circleY[0])
    return circleX, circleY


def label(i):
    return "{:d} Hz".format(i)


def grid_grid(circle_radius, anglelist):
    # to limit the annoying effect of all lines crossing at 0,0
    radius = 0.25 * circle_radius
    grid0 = [
        (radius * math.cos(p * math.pi / 180), radius * math.sin(p * math.pi / 180))
        for p in anglelist
    ]
    radius = 1
    gridC = [
        (radius * math.cos(p * math.pi / 180), radius * math.sin(p * math.pi / 180))
        for p in anglelist
    ]
    gridX = [(g0[0], gC[0], g0[0]) for (g0, gC) in zip(grid0, gridC)]
    gridY = [(g0[1], gC[1], g0[1]) for (g0, gC) in zip(grid0, gridC)]

    gridX = [s for s2 in gridX for s in s2]
    gridY = [s for s2 in gridY for s in s2]
    # print(gridX)
    return pd.DataFrame({"x": gridX, "y": gridY})


def grid_circle(radius, anglelist, dbmax):
    circleX = []
    circleY = []
    circleL = []
    legendX = []
    legendY = []
    legendT = []
    for c in [0.25, 0.5, 0.75, 1]:
        X, Y = circle(c * radius, anglelist)
        circleX.append(X)
        circleY.append(Y)
        g_label = dbmax * (1 - c) * radius
        circleL.append([g_label for i in range(0, len(X))])
        legendX.append(X[0])
        legendY.append(Y[0])
        legendT.append("{:.0f}dB".format(dbmax * (c - 1)))

    circleX = [v2 for v1 in circleX for v2 in v1]
    circleY = [v2 for v1 in circleY for v2 in v1]
    circleL = [v2 for v1 in circleL for v2 in v1]

    df = pd.DataFrame({"x": circleX, "y": circleY, "label": circleL})
    circles = (
        df.reset_index()
        .melt(id_vars=["x", "y"], var_name="label")
        .loc[lambda df: df["label"] != "index"]
    )
    # print(circles)
    text = pd.DataFrame({"x": legendX, "y": legendY, "text": legendT})
    # print(text)
    return circles, text


def grid_text(radius, anglelist):
    textX, textY = circle(1.02 * radius, anglelist)
    textT = [angle2str(a) for a in anglelist]
    if join(anglelist):
        textT += [""]
    return pd.DataFrame({"x": textX, "y": textY, "text": textT})


def find_nearest_freq(dfu, hz, tolerance=0.05):
    """ return the index of the nearest freq in dfu, return None if not found """
    ihz = None
    for i in dfu.index:
        f = dfu.loc[i]
        if abs(f - hz) < hz * tolerance:
            ihz = i
            break
    logger.debug("nearest: {0} hz at loc {1}".format(hz, ihz))
    return ihz


def plot(anglelist, df):
    dfu = sort_angles(df)
    db_mean = np.mean(dfu.loc[(dfu.Freq > 900) & (dfu.Freq < 1100)]["On Axis"].values)
    freq = dfu.Freq
    dfu = dfu.drop("Freq", axis=1)
    db_min = np.min(dfu.min(axis=0).values)
    db_max = np.max(dfu.max(axis=0).values)
    db_scale = max(abs(db_max), abs(db_min))
    # if df is normalized then 0 will be at the center of the radar which is not what
    # we want. Let's shift the whole graph up.
    if db_mean < 45:
        dfu += db_scale
    # print(db_min, db_max, db_mean, db_scale)
    # build 3 plots
    dbX = []
    dbY = []
    hzZ = []
    for hz in [100, 500, 1000, 10000, 15000]:
        ihz = find_nearest_freq(freq, hz)
        if ihz is None:
            continue
        X, Y, Z = projection(
            anglelist, dfu.loc[ihz][dfu.columns != "Freq"] / db_scale, hz
        )
        # add to global variable
        dbX.append(X)
        dbY.append(Y)
        hzZ.append(Z)

    # normalise
    dbX = [v2 for v1 in dbX for v2 in v1]
    dbY = [v2 for v1 in dbY for v2 in v1]
    # print("dbX min={} max={}".format(np.array(dbX).min(), np.array(dbX).max()))
    # print("dbY min={} max={}".format(np.array(dbY).min(), np.array(dbY).max()))

    hzZ = [label(i2) for i1 in hzZ for i2 in i1]

    return db_mean, pd.DataFrame({"x": dbX, "y": dbY, "Freq": hzZ})
