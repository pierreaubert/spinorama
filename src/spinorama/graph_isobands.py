#                                                  -*- coding: utf-8 -*-
import logging
import collections
import numpy as np

Triangle = collections.namedtuple("Triangle", "v1 v2 v3")
Edge = collections.namedtuple("Edge", "e1 e2")

logger = logging.getLogger("spinorama")


def transform_id_x(x, y):
    return x


def transform_id_y(x, y):
    return y


def cross_point(e1, e2, z, z_target):
    ratio = (z_target - z[e2]) / (z[e1] - z[e2])
    if ratio < 0 or ratio > 1:
        logger.error(
            "debug e1={0} e2={1} z=[{2}, {3}] z_target={4}".format(
                e1, e2, z[e1], z[e2], z_target
            )
        )
        logger.error("Out of bounds: ratio={0}".format(ratio))
    return (ratio * e1[0] + (1 - ratio) * e2[0], ratio * e1[1] + (1 - ratio) * e2[1])


def trapeze1(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_low)
    p2 = cross_point(striangle[0], striangle[1], z, z_high)
    p3 = cross_point(striangle[0], striangle[2], z, z_high)
    p4 = cross_point(striangle[0], striangle[2], z, z_low)
    # print('p1={0} p2={1} p3={2} p4={3}'.format(p1, p2, p3, p4))
    return [p1, p2, p3, p4]


def trapeze2(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[2], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_high)
    p3 = cross_point(striangle[1], striangle[2], z, z_high)
    p4 = cross_point(striangle[1], striangle[2], z, z_low)
    # print('p1={0} p2={1} p3={2} p4={3}'.format(p1, p2, p3, p4))
    return [p1, p2, p3, p4]


def trapeze3(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_low)
    # print('p1={0} p2={1}'.format(p1, p2))
    return [p1, p2, striangle[2], striangle[1]]


def trapeze4(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[1], striangle[2], z, z_high)
    p2 = cross_point(striangle[0], striangle[2], z, z_high)
    return [striangle[0], striangle[1], p1, p2]


def triangle1(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_high)
    p2 = cross_point(striangle[0], striangle[2], z, z_high)
    return [p1, p2, striangle[0]]


def triangle2(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[1], striangle[2], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_low)
    return [p1, p2, striangle[2]]


def pentagon(striangle, z, z_low, z_high):
    p1 = cross_point(striangle[0], striangle[1], z, z_low)
    p2 = cross_point(striangle[0], striangle[2], z, z_low)
    p3 = cross_point(striangle[0], striangle[2], z, z_high)
    p4 = cross_point(striangle[1], striangle[2], z, z_high)
    return [p1, p2, p3, p4, striangle[1]]


def triangle2band(triangle, z, z_low, z_high):
    if (
        triangle[0] == triangle[1]
        or triangle[2] == triangle[1]
        or triangle[0] == triangle[2]
    ):
        logger.error("incorrect: {0}".format(triangle))
        return None
    # sort triangle in order of z
    striangle = [p[1] for p in sorted(enumerate(triangle), key=lambda p: z[p[1]])]
    if (
        striangle[0] == striangle[1]
        or striangle[2] == striangle[1]
        or striangle[0] == striangle[2]
    ):
        logger.error("incorrect (sorted): {0}".format(striangle))
        return None

    # 3 states
    below = [v for v in striangle if z[v] < z_low]
    within = [v for v in striangle if z[v] >= z_low and z[v] <= z_high]
    above = [v for v in striangle if z[v] > z_high]

    if 3 in (len(below), len(above)):
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
        logger.error(
            "no match error below={0} within={1} above={2}".format(below, within, above)
        )
    return polygon


def find_isoband(
    grid_x, grid_y, grid_z, z_low, z_high, transform_x, transform_y, wrap_x, wrap_y
):
    # find iso band on a x,y grid where z is the elevation
    # z_low and z_high define the boundaries of the band
    gx = grid_x[-1]
    gy = np.array(grid_y).T[0]
    triangles = []
    # x_min = 100000
    # x_max = -100000
    # y_min = 100000
    # y_max = -100000
    for ix in range(0, len(gx) - 1):
        x1 = gx[ix]
        x2 = gx[ix + 1]
        # x_min = min(x1, x_min)
        # x_max = max(x2, x_max)
        for iy in range(0, len(gy) - 1):
            y1 = gy[iy]
            y2 = gy[iy + 1]
            # y_min = min(y1, y_min)
            # y_max = max(y2, y_max)
            if x1 == x2 or y1 == y2:
                logger.error(
                    "Input error: not a rectangle ({0}, {1}) and ({2}, {3})".format(
                        x1, y1, x2, y2
                    )
                )
                continue
            triangles.append(Triangle((x1, y1), (x2, y1), (x2, y2)))
            triangles.append(Triangle((x1, y1), (x1, y2), (x2, y2)))
    if wrap_x:
        x1 = gx[0]
        x2 = gx[-1]
        for iy in range(0, len(gy) - 1):
            y1 = gy[iy]
            y2 = gy[iy + 1]
            triangles.append(Triangle((x1, y1), (x2, y1), (x2, y2)))
            triangles.append(Triangle((x1, y1), (x1, y2), (x2, y2)))
    if wrap_y:
        y1 = gy[0]
        y2 = gy[-1]
        print(y1, y2)
        for ix in range(0, len(gx) - 1):
            x1 = gx[ix]
            x2 = gx[ix + 1]
            triangles.append(Triangle((x1, y1), (x2, y1), (x2, y2)))
            triangles.append(Triangle((x1, y1), (x1, y2), (x2, y2)))

    # print('Triangles range X=[{0}, {1}] Y=[{2}, {3}]'.format(x_min, x_max, y_min, y_max))
    elevation = {}
    for ix in enumerate(gx):
        for iy in enumerate(gy):
            elevation[(gx[ix], gy[iy])] = grid_z[ix][iy]

    isoband = []
    for triangle in triangles:
        band = triangle2band(triangle, elevation, z_low, z_high)
        if band is not None and len(band) > 0:
            transform_band = [
                [transform_x(p[0], p[1]), transform_y(p[0], p[1]), z_high + 10000]
                for p in band
            ] + [
                [
                    transform_x(band[0][0], band[0][1]),
                    transform_y(band[0][0], band[0][1]),
                    z_high + 10000,
                ]
            ]
            isoband.append(transform_band)

    # print('debug: z_low={0} z_high={1} isoband={2}'.format(z_low, z_high, pps(isoband)))
    # print('debug: merged={0}'.format(pps(merge_connected_polygons(isoband))))
    # don't work yet, need to take care of polygons with holes ...
    # return merge_connected_polygons(isoband)
    return isoband


def find_isobands(
    grid_x,
    grid_y,
    grid_z,
    z_values,
    transform_x,
    transform_y,
    wrap_x=False,
    wrap_y=False,
):
    # find iso bands on a x,y grid where z is the elevation, z_values define the boundaries of the bands
    # return data in geojson to please altair
    z_colors = [
        "#5c77a5",
        "#dc842a",
        "#c85857",
        "#89b5b1",
        "#71a152",
        "#bab0ac",
        "#e15759",
        "#b07aa1",
        "#76b7b2",
        "#ff9da7",
    ]
    geojson = {}
    geojson["type"] = "FeatureCollection"
    geojson["features"] = []
    for z in range(0, len(z_values) - 1):
        z_low = z_values[z]
        z_high = z_values[z + 1]
        isobands = find_isoband(
            grid_x,
            grid_y,
            grid_z,
            z_low,
            z_high,
            transform_x,
            transform_y,
            wrap_x,
            wrap_y,
        )
        geojson["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [isobands],
                },
                "properties": {
                    "z_low": z_low,
                    "z_high": z_high,
                    "stroke": "#000000",
                    "stroke-opacity": 0,
                    "stroke-width": 0,
                    "fill-opacity": 1,
                    "fill": z_colors[z % len(z_colors)],
                },
            }
        )
    return geojson
