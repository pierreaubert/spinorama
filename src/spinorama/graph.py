import logging
import math
import numpy as np
import pandas as pd
import altair as alt
from .analysis import directivity_matrix
from .contour import compute_contour, compute_contour_smoothed
from .normalize import resample


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
    'ymin': -40,
    'ymax': 10,
    'width': 600,
    'height': 360,
}

contour_params_default = {
    'xmin': 100,
    'xmax': 20000,
    'width': 400,
    'height': 360,
    # 'contour_scale': [-12, -9, -8, -7, -6, -5, -4, -3, -2.5, -2, -1.5, -1, -0.5, 0],
    'contour_scale': [-30, 0],
    # 'contour_scale': [-30, -25, -20, -15, -10, -5, 0],
    'colormap': 'spectral',
    # 'colormap': 'redyellowblue',
    # 'colormap': 'blueorange',
    # 'colormap': 'blues',
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
    ).properties(width=graph_params['width'], height=graph_params['height'])
    
    circle=alt.Chart(dfu).mark_circle(size=100).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[xmin, xmax])),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[ymin, ymax])),
        alt.Color('Measurements', type='nominal', sort=None),
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    ) # .transform_calculate(Freq=f'format(datum.Freq, ".0f")', dB=f'format(datum.dB, ".1f")')    
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
    xaxis =alt.X('Freq:Q', title='Freqency (Hz)',
                scale=alt.Scale(type='log', base=10, nice=False, domain=[xmin, xmax]),
                axis=alt.Axis(format='s'))
    yaxis = alt.Y('dB:Q', scale=alt.Scale(zero=False, domain=[ymin, ymax]))
    # why -10?
    di_yaxis = alt.Y('dB:Q', scale=alt.Scale(zero=False, domain=[-10,ymax-ymin-10]))
    color = alt.Color('Measurements', type='nominal', sort=None)
    opacity = alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    
    line=alt.Chart(dfu).mark_line().transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['On Axis', 'Listening Window', 'Early Reflections', 'Sound Power'])
    ).encode(x=xaxis, y=yaxis, color=color, opacity=opacity
    )

    circle=alt.Chart(dfu).mark_circle(size=100).transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['On Axis', 'Listening Window', 'Early Reflections', 'Sound Power'])
    ).encode(
        x=xaxis, y=yaxis, color=color, 
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    ) # .transform_calculate(Freq=f'format(datum.Freq, ".0f")', dB=f'format(datum.dB, ".1f")')    
    
    di=alt.Chart(dfu).mark_line().transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['Early Reflections DI', 'Sound Power DI'])
    ).encode(x=xaxis, y=di_yaxis, color=color, opacity=opacity)

    circle_di = alt.Chart(dfu).mark_circle(size=100).transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['Early Reflections DI', 'Sound Power DI'])
    ).encode(
        x=xaxis, y=di_yaxis, color=color, 
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    ) # .transform_calculate(Freq=f'format(datum.Freq, ".0f")', dB=f'format(datum.dB, ".1f")')    
    

    # assemble elements together
    spin = alt.layer(circle+line, circle_di+di).resolve_scale(y='independent'
    ).add_selection(
        selectorsMeasurements
    ).add_selection(
        scales
    ).add_selection(
        nearest
    ).properties(
        width=graph_params['width'],
        height=graph_params['height']
    ).interactive()
    return spin

# explicitly set ticks for X and Y axis
xTicks = [i*10 for i in range(2,10)] + [i*100 for i in range(1,10)] + [i*1000 for i in range(1, 21)]
yTicks = [-180+10*i for i in range(0,37)]

def graph_contour_common(af, am, az, graph_params):
    try:
        width = graph_params['width']
        height = graph_params['height']
        # more interesting to look at -3/0 range
        speaker_scale = None
        if 'contour_scale' in graph_params.keys():
            speaker_scale = graph_params['contour_scale']
        else:
            speaker_scale = contour_params_default['contour_scale']
        #
        colormap = 'veridis'
        if 'colormap' in graph_params:
            colormap = graph_params['colormap']
        else:
            colormap = contour_params_default['colormap']

        # flatten and build a Frame
        freq = af.ravel()
        angle = am.ravel()
        db = az.ravel()
        if (freq.size != angle.size) or (freq.size != db.size):
            logging.debug('Contour: Size freq={:d} angle={:d} db={:d}'.format(freq.size, angle.size, db.size))
            return None

        source = pd.DataFrame({'Freq': freq, 'Angle': angle, 'dB': db})

        # tweak ratios and sizes
        chart = alt.Chart(source)
        # classical case is 200 points for freq and 36 or 72 measurements on angles
        # check that width is a multiple of len(freq)
        # same for angles
        
        # build and return graph
        logging.debug('w={0} h={1}'.format(width, height))
        if width/source.shape[0] < 2 and height/source.shape[1] < 2:
            chart = chart.mark_point()
        else:
            chart = chart.mark_rect()

        chart = chart.transform_filter(
            'datum.Freq>400'
        ).encode(
            alt.X('Freq:O', 
                  scale=alt.Scale(type="log", base=10, nice=True),
                  axis=alt.Axis(
                      format='.0s',
                      labelAngle=0,
                      values=xTicks,
                      title='Freq (Hz)',
                      labelExpr="datum.value % 100 ? null : datum.label")),
            alt.Y('Angle:O',
                  axis=alt.Axis(
                      format='.0d',
                      title='Angle',
                      values=yTicks,
                    labelExpr="datum.value % 30 ? null : datum.label"),
                  sort=None),
            alt.Color('dB:Q',
                      scale=alt.Scale(scheme=colormap,
                                      domain=speaker_scale,
                                      nice=True))
        ).properties(
            width=width,
            height=height
        )
        return chart
    except KeyError as ke:
        logging.warning('Failed with {0}'.format(ke))
        return None


def graph_contour(df, graph_params):
    af, am, az = compute_contour(df)
    if af is None or am is None or az is None:
        logging.error('contour is None')
        return None
    return graph_contour_common(af, am, az, graph_params)


def graph_contour_smoothed(df, graph_params):
    af, am, az = compute_contour_smoothed(df)
    if af is None or am is None or az is None:
        logging.warning('contour is None')
        return None
    if np.max(np.abs(az)) == 0.0:
        logging.warning('contour is flat')
        return None
    return graph_contour_common(af, am, az, graph_params)


def radar_angle2str(a):
    """display an angle every 30 deg"""
    if a % 30 == 0:
        return '{:d}°'.format(a)
    else:
        return ''
    

def radar_join(anglelist):
    """return true if we should join the last point and the first one"""
    # 180-170-10 => join points
    delta = anglelist[-1]+anglelist[0]
    # print(delta)
    if delta == 10 or delta == 5:
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


def graph_radar(df_in, graph_params):
    dfu = df_in.copy()
    # which part of the circle do we plot?
    angle_min, angle_max = radar_angle_range(dfu.columns)
    if angle_min is None or angle_max is None or angle_max == angle_min:
        logging.debug('Angle is empty')
        return None
    # do we have +10 or +5 deg measurements?
    delta = 10
    if (len(dfu.columns)-1)/36 == 2:
        delta = 5
    anglelist = [a for a in range(angle_min, angle_max+delta, delta)]
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


def graph_directivity_matrix(dfu, graph_params):
    splH = dfu['SPL Horizontal_unmelted']
    splV = dfu['SPL Vertical_unmelted']

    if splH.shape != splV.shape:
        logging.debug('shapes do not match {0} and {1}'.format(splH.shape, splV.shape))
        return None
    
    splH = resample(splH, 300).reset_index()
    splV = resample(splV, 300).reset_index()

    x, y, z = directivity_matrix(splH, splV)
    
    source = pd.DataFrame({'x': x.ravel(), 'y': y.ravel(),'z': z.melt().value})

    return alt.Chart(source).mark_rect(
    ).encode(
        x=alt.X('x:O', scale=alt.Scale(type='log')),
        y=alt.Y('y:O', scale=alt.Scale(type='log')),
        color=alt.Color('z:Q', scale=alt.Scale(scheme='spectral', nice=True))
    ).properties(
        width=800,
        height=800)


def build_selections(df, speaker1, speaker2):
    speakers = sorted(df.Speaker.unique())
    input_dropdown1 = alt.binding_select(options=[s for s in speakers])
    selection1 = alt.selection_single(fields=['Speaker'], bind=input_dropdown1, name='Select right ', init={'Speaker': speaker1})
    input_dropdown2 = alt.binding_select(options=[s for s in speakers])
    selection2 = alt.selection_single(fields=['Speaker'], bind=input_dropdown2, name='Select left ', init={'Speaker': speaker2})
    selectorsMeasurements = alt.selection_multi(fields=['Measurements'], bind='legend')
    scales = alt.selection_interval(bind='scales')
    return selection1, selection2, selectorsMeasurements, scales


def graph_compare_freq(df, graph_params, speaker1, speaker2):
    selection1, selection2, selectorsMeasurements, scales = build_selections(df, speaker1, speaker2)
    xaxis = alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[20,20000], nice=False))
    yaxis = alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[-40,10]))
    color = alt.Color('Measurements', type='nominal', sort=None)
    line = alt.Chart(df).encode(
        xaxis, yaxis, color,
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    ).properties(width=600, height=300)

    points = line.mark_circle(size=100).encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    )
    rules = alt.Chart(df).mark_rule(color='gray').encode(x='Freq:Q').transform_filter(nearest)
    graph1 = (points+line.mark_line()).add_selection(selection1).transform_filter(selection1)
    graph2 = (points+line.mark_line(strokeDash=[4,2])).add_selection(selection2).transform_filter(selection2)

    return alt.layer(
        graph2, graph1, rules
    ).add_selection(
        selectorsMeasurements
    ).add_selection(
        scales
    ).add_selection(
        nearest
    ).interactive()


def graph_compare_cea2034(df, graph_params, speaker1, speaker2):
    selection1, selection2, selectorsMeasurements, scales = build_selections(df, speaker1, speaker2)

    # TODO(move to parameters)
    x_axis = alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[20,20000], nice=False))
    y_axis = alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[-40,10]))
    color = alt.Color('Measurements', type='nominal', sort=None)
    opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    
    line = alt.Chart(df).transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['On Axis', 'Listening Window', 'Early Reflections', 'Sound Power'])
    ).encode(x=x_axis, y=y_axis, color=color, opacity=opacity)
    points = line.mark_circle(size=100).encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    )

    di_axis = alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[-10, 40], nice=False))
    di = alt.Chart(df).transform_filter(
        alt.FieldOneOfPredicate(
            field='Measurements',
            oneOf=['Early Reflections DI', 'Sound Power DI'])
    ).encode(x=x_axis, y=di_axis, color=color, opacity=opacity)
    points_di = di.mark_circle(size=100).encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    )

    spin_full = alt.layer(
        points+line.mark_line(), 
        points_di+di.mark_line(clip=True)
    ).resolve_scale(y='independent').properties(width=600, height=300)
    
    spin_dash = alt.layer(
        points+line.mark_line(strokeDash=[4,2]), 
        points_di+di.mark_line(clip=True,strokeDash=[4,2])
    ).resolve_scale(y='independent').properties(width=600, height=300)

    line1 = spin_full.add_selection(selection1).transform_filter(selection1)
    line2 = spin_dash.add_selection(selection2).transform_filter(selection2)

    points = line.mark_point().encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))                                                   \

    rules = alt.Chart(df).mark_rule(color='gray').encode(x='Freq:Q').transform_filter(nearest)                                                      \
                                                                                                                                                      
    layers = alt.layer(line2,line1, rules).add_selection(
        selectorsMeasurements
    ).add_selection(
        scales
    ).add_selection(
        nearest
    ).interactive()
    return layers


def graph_regression_graph(graph, freq_start, freq_end):
    reg = graph.transform_filter(
        'datum.Freq>{0} & datum.Freq<{1}'.format(freq_start, freq_end)
    ).transform_regression(
        method='log',
        on='Freq',
        regression='dB',
        extent=[20,20000]
    ).encode(
        alt.X('Freq:Q'),
        alt.Y('dB:Q'),
        color=alt.value('red')
    )
    return reg


def graph_regression(source, freq_start, freq_end):
    return graph_regression_graph(alt.Chart(source), freq_start, freq_end).mark_line()


def graph_compare_freq_regression(df, graph_params, speaker1, speaker2):
    selection1, selection2, selectorsMeasurements, scales = build_selections(df, speaker1, speaker2)
    xaxis = alt.X('Freq:Q', scale=alt.Scale(type="log", domain=[20,20000], nice=False))
    yaxis = alt.Y('dB:Q',   scale=alt.Scale(zero=False, domain=[-40,10]))
    color = alt.Color('Measurements', type='nominal', sort=None)

    line = alt.Chart(df).encode(
        xaxis, yaxis, color,
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))
    )

    points = line.mark_circle(size=100).encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=['Measurements', 'Freq', 'dB']
    )

    rules = alt.Chart(df).mark_rule(color='gray').encode(x='Freq:Q').transform_filter(nearest)

    line1 = line.transform_filter(selection1)
    line2 = line.transform_filter(selection2)

    reg1 = graph_regression_graph(line1, 80, 10000).mark_line()
    reg2 = graph_regression_graph(line2, 80, 10000).mark_line(strokeDash=[4,2])

    graph1 = line1.mark_line().add_selection(selection1)
    graph2 = line2.mark_line(strokeDash=[4,2]).add_selection(selection2)

    return alt.layer(
        graph2, reg2, graph1, reg1, rules
    ).add_selection(
        selectorsMeasurements
    ).add_selection(
        scales
    ).add_selection(
        nearest
    ).interactive()
