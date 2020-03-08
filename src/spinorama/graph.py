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
    'ymin': 40,
    'ymax': 110,
    'width': 600,
    'height': 360,
}

contour_params_default = {
    'xmin': 400,
    'xmax': 20000,
    'width': 420,
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
    xmin = graph_params['xmin']
    xmax = graph_params['xmax']
    ymin = graph_params['ymin']
    ymax = graph_params['ymax']
    if xmax == xmin:
        logging.error('Graph configuration is incorrect: xmin==xmax')
    if ymax == ymin:
        logging.error('Graph configuration is incorrect: ymin==ymax')
    # add selectors                                                                                                                          
    selectorsMeasurements = alt.selection_multi(
        fields=['Measurements'], 
        bind='legend')
    scales = alt.selection_interval(
        bind='scales'
    )
    # main charts
    line=alt.Chart(dfu).mark_line().encode(
        alt.X('Freq:Q', title='Freqency (Hz)',
              scale=alt.Scale(type='log', base=10, nice=False, domain=[xmin, xmax]), 
              axis=alt.Axis(format='s')),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[ymin, ymax])),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    ).properties(
        width=graph_params['width'],
        height=graph_params['height']
    )
    circle=alt.Chart(dfu).mark_circle(size=100).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[xmin, xmax])),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[ymin, ymax])),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    ).transform_calculate(Freq=f'format(datum.Freq, ".0f")', dB=f'format(datum.dB, ".1f")')    
    # assemble elements together
    spin = alt.layer(
        circle, line
    ).add_selection(
        selectorsMeasurements
    ).add_selection(
        scales
    ).add_selection(
        nearest
    )
    return spin


def graph_spinorama(dfu, graph_params):
    xmin = graph_params['xmin']
    xmax = graph_params['xmax']
    ymin = graph_params['ymin']
    ymax = graph_params['ymax']
    if xmax == xmin:
        logging.error('Graph configuration is incorrect: xmin==xmax')
    if ymax == ymin:
        logging.error('Graph configuration is incorrect: ymin==ymax')
    # add selectors                                                                                                                          
    selectorsMeasurements = alt.selection_multi(
        fields=['Measurements'], 
        bind='legend')
    scales = alt.selection_interval(
        bind='scales'
    )
    # main charts
    line=alt.Chart(dfu, title=f'CEA2034').mark_line(clip=True).transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['On Axis', 'Listening Window', 'Early Reflections', 'Sound Power'])
    ).encode(
        alt.X('Freq:Q', title='Freqency (Hz)',
              scale=alt.Scale(type='log', base=10, nice=False, domain=[xmin, xmax]), 
              axis=alt.Axis(format='s')),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[ymin, ymax])),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    ).properties(
        width=graph_params['width'],
        height=graph_params['height']
    )
    di=alt.Chart(dfu).mark_line(clip=True).transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['Early Reflections DI', 'Sound Power DI'])
    ).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[xmin, xmax])),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False)),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    )
    circle=alt.Chart(dfu).mark_circle(size=100).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[xmin, xmax])),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False)),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    ) #.transform_calculate(Freq=f'format(datum.Freq, ".0f")', dB=f'format(datum.dB, ".1f")')    

    # assemble elements together
    spin = (circle + (line + di) #.resolve_scale(y='independent'
    ).add_selection(
        selectorsMeasurements
    ).add_selection(
        scales
    ).add_selection(
        nearest
    )
    return spin


def graph_contour_common(df, transformer, graph_params):
    try:
        width = graph_params['width']
        height = graph_params['height']
        # more interesting to look at -3/0 range
        speaker_scale = None
        if 'contour_scale' in graph_params.keys():
            speaker_scale = graph_params['contour_scale']
        else:
            speaker_scale = contour_params_default['contour_scale']
        af, am, az = transformer(df)
        if af is None or am is None or az is None:
            return None
        freq = af.ravel()
        angle = am.ravel()
        db = az.ravel()
        if (freq.size != angle.size) or (freq.size != db.size):
            logging.debug('Contour: Size freq={:d} angle={:d} db={:d}'.format(freq.size, angle.size, db.size))
            return None
        source = pd.DataFrame({'Freq': freq, 'Angle': angle, 'dB': db})
        m_height = 12
        m_size = 8
        if width > 800:
            m_size = np.floor(m_size*width/800)
        if height > 360:
            m_height = np.floor(m_height*height/360)
        return alt.Chart(source).mark_circle(
        ).transform_filter(
            'datum.Freq>400'
        ).encode(
            alt.X('Freq:O'),
            alt.Y('Angle:O'),
            alt.Color('dB:Q', scale=alt.Scale(scheme='lightmulti', domain=speaker_scale, nice=True))
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


def radar_angle2str(a):

    if a % 30 == 0:
        return '{:d}°'.format(a)
    else:
        return ''
    

def radar_join(anglelist):
    """return true if we should join the last point and the first one"""
    # 180-170-10 => join points
    delta = anglelist[-1]+anglelist[0]-10
    # print(delta)
    if delta == 0:
        return True
    else:
        return False

def radar_angle_range(columns):
    amin = 0
    amax = 0
    for c in columns:
        if c != 'Freq':
            v = angle2value(c)
            if v < 0:
                amin = min(amin, v)
            else:
                amax = max(amax, v)
    return amin, amax


def radar_projection(anglelist, gridZ, hz):
    # map in 2d                                                                                                                                                                                  
    dbsX = [db * math.cos(a * math.pi / 180) for a, db in zip(anglelist, gridZ)]
    dbsY = [db * math.sin(a * math.pi / 180) for a, db in zip(anglelist, gridZ)]

    # join with first point (-180=180) 
    # print('Calling project', anglelist)
    if radar_join(anglelist):
        dbsX.append(dbsX[0])
        dbsY.append(dbsY[0])

    return dbsX, dbsY, [hz for i in range(0, len(dbsX))]


def radar_circle(radius, anglelist):
    rg = range(0, len(anglelist))
    circleC = [radius for i in rg]
    circleX = [circleC[i]*math.cos(anglelist[i]*math.pi/180) for i in rg]
    circleY = [circleC[i]*math.sin(anglelist[i]*math.pi/180) for i in rg]
    # print('Calling circles', anglelist)
    if radar_join(anglelist):
        circleX.append(circleX[0])
        circleY.append(circleY[0])
    return circleX, circleY

def radar_label(i):
    return '{:d} Hz'.format(i)


def radar_grid_grid(anglelist):
    # to limit the annoying effect of all lines crossing at 0,0
    radius = 0.25
    grid0 = [(radius * math.cos(p * math.pi / 180), radius *
              math.sin(p * math.pi / 180)) for p in anglelist]
    radius = 1
    gridC = [(radius * math.cos(p * math.pi / 180), radius *
              math.sin(p * math.pi / 180)) for p in anglelist]
    gridX = [(g0[0], gC[0], g0[0]) for (g0, gC) in zip(grid0, gridC)]
    gridY = [(g0[1], gC[1], g0[1]) for (g0, gC) in zip(grid0, gridC)]
    
    gridX = [s for s2 in gridX for s in s2]
    gridY = [s for s2 in gridY for s in s2]
    # print(gridX)
    return pd.DataFrame({'x': gridX, 'y': gridY})


def radar_grid_circle(anglelist, dbmax):
    circleX = []
    circleY = []
    circleL = []
    legendX = []
    legendY = []
    legendT = []
    for c in [0.25, 0.5, 0.75, 1]:
        X, Y = radar_circle(c, anglelist)
        circleX.append(X)
        circleY.append(Y)
        label = dbmax*(1-c)
        circleL.append([label for i in range(0, len(X))])
        legendX.append(X[0])
        legendY.append(Y[0])
        legendT.append('{:.0f}dB'.format(dbmax*(c-1)))

    circleX = [v2 for v1 in circleX  for v2 in v1]
    circleY = [v2 for v1 in circleY  for v2 in v1]
    circleL = [v2 for v1 in circleL  for v2 in v1]

    df = pd.DataFrame({'x': circleX, 'y': circleY, 'label': circleL})
    circles = df.reset_index().melt(id_vars=['x', 'y'], var_name='label').loc[lambda df: df['label'] != 'index']
    # print(circles)
    text = pd.DataFrame({'x': legendX, 'y': legendY, 'text': legendT})
    # print(text)
    return circles, text


def radar_grid_text(anglelist):
    textX, textY = radar_circle(1.02, anglelist)
    textT = [radar_angle2str(a) for a in anglelist] 
    if radar_join(anglelist):
        textT += ['']
    return pd.DataFrame({'x': textX, 'y': textY, 'text': textT})


def radar_find_nearest_freq(dfu, hz, tolerance=0.05):
    """ return the index of the nearest freq in dfu, return None if not found """
    ihz = None
    for i in dfu.index:
        f = dfu.loc[i, 'Freq']
        if abs(f-hz) < hz*tolerance:
            ihz = i
            break
    # print('nearest: {0} hz at loc {1}'.format(hz, ihz))                                                                                                                                        
    return ihz


def radar_plot(anglelist, dfu):
    # build 3 plots                                                                                                                                                                              
    dbX = []
    dbY = []
    hzZ = []
    for hz in [100, 500, 1000, 10000, 15000]:
        # ihz = [47, 113, 180]                                                                                                                                                                   
        ihz = radar_find_nearest_freq(dfu, hz)
        if ihz is None:
            continue
        X, Y, Z = radar_projection(anglelist, dfu.loc[ihz][1:], hz)
        # add to global variable                                                                                                                                                                 
        dbX.append(X)
        dbY.append(Y)
        hzZ.append(Z)

    # normalise                                                                                                                                                                                  
    dbmax = max(np.array(dbX).max(), np.array(dbY).max())
    dbX = [v2 / dbmax for v1 in dbX for v2 in v1]
    dbY = [v2 / dbmax for v1 in dbY for v2 in v1]
    hzZ = [radar_label(i2) for i1 in hzZ for i2 in i1]

    return dbmax, pd.DataFrame({'x': dbX, 'y': dbY, 'Freq': hzZ})


def angle2value(angle):
    if angle == 'On Axis':
        return 0
    else:
        return int(angle[:-1])


def graph_radar(dfu, graph_params):

    # which part of the circle do we plot?
    angle_min, angle_max = radar_angle_range(dfu.columns)
    if angle_min is None or angle_max is None or angle_max == angle_min:
        logging.debug('Angle is empty')
        return None
    anglelist = [a for a in range(angle_min, angle_max+10, 10)]
    # print(angle_min, angle_max)
    # print(dfu.columns)
    # print(anglelist)

    # display some curves                                                                                                                                                                        
    dbmax, dbs_df = radar_plot(anglelist, dfu)
    
    # build a grid                                                                                                                                                                               
    grid_df = radar_grid_grid(anglelist)
    circle_df, circle_text = radar_grid_circle(anglelist, dbmax)
    text_df = radar_grid_text(anglelist)

    grid = alt.Chart(grid_df).mark_line(
    ).encode(
        alt.Latitude('x:Q'), 
        alt.Longitude('y:Q'), 
        size=alt.value(1),
        opacity=alt.value(0.2)
    ).project(type='azimuthalEquidistant', rotate=[0, 0, 90])

    circle = alt.Chart(circle_df).mark_line(
    ).encode(
        alt.Latitude('x:Q'),
        alt.Longitude('y:Q'),
        alt.Color('value:Q', legend=None),
        size=alt.value(0.5)
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]
    )
    
    legend = alt.Chart(circle_text).mark_text(
        dx=15,
        dy=-10
    ).encode(
        alt.Latitude('x:Q'), 
        alt.Longitude('y:Q'), 
        text='text:O'
    ).project(type='azimuthalEquidistant', rotate=[0, 0, 90])
        
    text = alt.Chart(text_df).mark_text(
    ).encode(
        alt.Latitude('x:Q'), 
        alt.Longitude('y:Q'), 
        text='text:O'
    ).project(type='azimuthalEquidistant', rotate=[0, 0, 90])

    dbs = alt.Chart(dbs_df).mark_line(
        thickness=3
    ).encode(
        alt.Latitude('x:Q'), 
        alt.Longitude('y:Q'), 
        alt.Color('Freq:N', sort=None), 
    ).project(
        type='azimuthalEquidistant', rotate=[0, 0, 90]
    ).properties(width=graph_params['width'], height=graph_params['height'])

    # return (dbs | grid) & (circle+legend | text) & (grid+circle+legend+text+dbs)
    return (grid+circle+legend+text+dbs)


