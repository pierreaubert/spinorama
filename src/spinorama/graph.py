import logging
import math
import numpy as np
import pandas as pd
import altair as alt
from .contour import compute_contour, compute_contour_smoothed


alt.data_transformers.disable_max_rows()


nearest = alt.selection(
    type='single',
    nearest=True,
    on='mouseover',
    fields=['Freq'],
    empty='none')

graph_params_default = {
    'xmin': 20,
    'xmax': 20000,
    'width': 900,
    'height': 400,
}

contour_params_default = {
    'xmin': 400,
    'xmax': 20000,
    'width': 400,
    'height': 180,
    'contour_scale': [-12, -9, -8, -7, -6, -5, -4, -3, -2.5, -2, -1.5, -1, -0.5, 0],
}

radar_params_default = {
    'xmin': 400,
    'xmax': 20000,
    'width': 180,
    'height': 180,
    'contour_scale': [-12, -9, -8, -7, -6, -5, -4, -3, -2.5, -2, -1.5, -1, -0.5, 0],
}

def graph_freq(dfu, graph_params):
    # add selectors
    # one on Frequency one on Measurements
    selectorsMeasurements = alt.selection_multi(
        fields=['Measurements'],
        bind='legend')
    # use a scale
    scales = alt.selection_interval(
        bind='scales'
    )
    # main charts
    line = alt.Chart(dfu).mark_line(
    ).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log",
                                domain=[graph_params['xmin'], graph_params['xmax']])),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False)),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    ).properties(
        width=graph_params['width'],
        height=graph_params['height']
    )
    circle = alt.Chart(dfu).mark_circle(
        size=100
    ).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[20, 20000])),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False)),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    ).transform_calculate(
        Freq=f'format(datum.Freq, ".0f")',
        dB=f'format(datum.dB, ".1f")'
    )

    # assemble elements together
    line = (circle+line)\
        .add_selection(selectorsMeasurements)\
        .add_selection(scales)\
        .add_selection(nearest)
    return line


def graph_contour_common(df, transformer,graph_params):
    try:
        width = graph_params['width']
        height = graph_params['height']
        # more interesting to look at -3/0 range
        speaker_scale = graph_params['contour_scale']
        af, am, az = transformer(df)
        freq = af.ravel()
        angle = am.ravel()
        db = az.ravel()
        if (freq.size != angle.size) or (freq.size != db.size):
            logging.warning('Size freq={:d} angle={:d} db={:d}'.format(freq.size, angle.size, db.size))
            return None
        source = pd.DataFrame({'Freq': freq, 'Angle': angle, 'dB': db})
        m_height = 12
        m_size = 8
        if width > 800:
            m_size = np.floor(m_size*width/800)
        if height > 360:
            m_height = np.floor(m_height*height/360)
        return alt.Chart(source).mark_rect(
        ).transform_filter(
            'datum.Freq>400'
        ).encode(
            alt.X('Freq:O'),
            alt.Y('Angle:O'),
            alt.Color('dB:Q', scale=alt.Scale(domain=speaker_scale))
        ).properties(
            width=width,
            height=height
        )
    except KeyError as ke:
        logging.warning('Failed with {0}'.format(ke))
        return None


def graph_contour(df, graph_params):
    return graph_contour_common(df, compute_contour, graph_params)


def graph_contour_smoothed(df, graph_params):
    return graph_contour_common(df, compute_contour_smoothed, graph_params)


def graph_radar(dfu, graph_params):
    # build a grid
    radius = 0
    anglelist = [a for a in range(-180, 180, 10)]
    grid0 = [(radius * math.cos(p * math.pi / 180), radius *
              math.sin(p * math.pi / 180)) for p in anglelist]
    radius = 1
    gridC = [(radius * math.cos(p * math.pi / 180), radius *
              math.sin(p * math.pi / 180)) for p in anglelist]
    gridX = [(g0[0], gC[0]) for (g0, gC) in zip(grid0, gridC)]
    gridX = [s for s2 in gridX for s in s2]
    gridY = [(g0[1], gC[1]) for (g0, gC) in zip(grid0, gridC)]
    gridY = [s for s2 in gridY for s in s2]

    def build_circle(radius):
        circleC = [radius for i in range(0, len(anglelist) + 1)]
        circleX = [
            circleC[i] *
            math.cos(
                anglelist[i] *
                math.pi /
                180) for i in range(
                0,
                len(anglelist))]
        circleY = [
            circleC[i] *
            math.sin(
                anglelist[i] *
                math.pi /
                180) for i in range(
                0,
                len(anglelist))]
        circleX.append(circleX[0])
        circleY.append(circleY[0])
        return circleX, circleY

    # 100hz 47
    #  1khz 113
    # 10khz 180
    def hzname(i):
        if i == 47:
            return '100 Hz'
        elif i == 113:
            return '1 kHz'
        elif i == 180:
            return '10 kHz'
        else:
            return 'error'

    def project(gridZ):
        angles = []
        dbs = []
        for a, z in zip(gridZ.index, gridZ):
            angle = 0
            # On-Axis case
            if a[0] != 'O':
                angle = int(a[:-1])
            angles.append(angle)
            dbs.append(z)

        # map in 2d
        dbsX = [db * math.cos(a * math.pi / 180) for a, db in zip(angles, dbs)]
        dbsY = [db * math.sin(a * math.pi / 180) for a, db in zip(angles, dbs)]

        # join with first point (-180=180)
        dbsX.append(dbsX[0])
        dbsY.append(dbsY[0])

        return dbsX, dbsY, [ihz for i in range(0, len(dbsX))]

    # build 3 plots
    dbX = []
    dbY = []
    hzZ = []
    for ihz in [47, 113, 180]:
        X, Y, Z = project(dfu.loc[ihz][1:])
        # add to global variable
        dbX.append(X)
        dbY.append(Y)
        hzZ.append(Z)

    # normalise
    dbmax = max(np.array(dbX).max(), np.array(dbY).max())
    dbX = [v2 / dbmax for v1 in dbX for v2 in v1]
    dbY = [v2 / dbmax for v1 in dbY for v2 in v1]
    hzZ = [hzname(i2) for i1 in hzZ for i2 in i1]

    grid_df = pd.DataFrame({'x': gridX, 'y': gridY})
    grid = alt.Chart(grid_df).mark_line(
    ).encode(
        alt.Latitude('x:Q'),
        alt.Longitude('y:Q'),
        size=alt.value(1)
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]
    )

    circleX, circleY = build_circle(0.8)
    circle_df = pd.DataFrame({'x': circleX, 'y': circleY})
    circle = alt.Chart(circle_df).mark_line().encode(
        alt.Latitude('x:Q'),
        alt.Longitude('y:Q'),
        size=alt.value(1)
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]
    )

    def angle2str(a):
        if a % 30 == 0:
            return '{:d}°'.format(a)
        else:
            return ''

    textX, textY = build_circle(1.1)
    textT = [angle2str(a) for a in anglelist] + ['']
    text_df = pd.DataFrame({'x': textX, 'y': textY, 'text': textT})
    text = alt.Chart(text_df).mark_text().encode(
        alt.Latitude('x:Q'),
        alt.Longitude('y:Q'),
        text='text:O'
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]
    )

    dbs_df = pd.DataFrame({'x': dbX, 'y': dbY, 'Freq': hzZ})
    dbs = alt.Chart(dbs_df).mark_line().encode(
        alt.Latitude('x:Q'),
        alt.Longitude('y:Q'),
        alt.Color('Freq:N', sort=None),
        size=alt.value(3)
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]
    ).properties(
        width=graph_params['width'],
        height=graph_params['height']
    )

    return dbs + grid + circle + text
