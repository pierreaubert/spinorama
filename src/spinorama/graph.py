import os
import  math
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
alt.data_transformers.disable_max_rows()
from .contour import compute_contour

nearest = alt.selection(type='single', nearest=True, on='mouseover',fields=['Freq'], empty='none')

def display_freq(df, width=900, heigth=500):
    line = alt.Chart(df).mark_line(
            interpolate='basis'
    ).encode(
        alt.X('Freq:Q', scale=alt.Scale(type="log", domain=(20,20000))),
        alt.Y('dB:Q',   scale=alt.Scale(zero=False)),
        alt.Color('Measurements', type='nominal', sort=None)
    ).properties(
        width=width, 
        height=heigth
    )
    selectors = alt.Chart(df).mark_point().encode(x='Freq:Q', opacity=alt.value(0)).add_selection(nearest)
    points = line.mark_point().encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    text = line.mark_text(align='left', dx=5, dy=-5).encode(text=alt.condition(nearest, 'dB:Q', alt.value(' ')))
    rules = alt.Chart(df).mark_rule(color='gray').encode(x='Freq:Q').transform_filter(nearest)
    return line+selectors+points+rules+text


def display_freq_sidebyside(s1, s2, name, width=450, heigth=450):
    d1 = display_freq(s1[name], weigth, heigth)
    d2 = display_freq(s2[name], weigth, heigth)
    return alt.hconcat(d1, d2)
    

def display_contour(df, width=400, heigth=180):
    try:
        af, am, az = compute_contour(df)
        source = pd.DataFrame({'Freq': af.ravel(), 'Angle': am.ravel(), 'dB': az.ravel()})
        return alt.Chart(source).mark_rect(
           ).transform_filter(
               'datum.Freq>400'
           ).encode(
               alt.X('Freq:O'),
               alt.Y('Angle:O'),
               alt.Color('dB:Q',
                     scale=alt.Scale(
                         scheme='category20c'))
           ).properties(
               width=width, 
               height=heigth
           )
    except KeyError:
        return None

def display_radar(df, width, heigth):
    # build a grid
    radius=0
    anglelist = [a for a in range(-180,180,10)]
    grid0 = [(radius*math.cos(p*math.pi/180), radius*math.sin(p*math.pi/180)) for p in anglelist]
    radius=1
    gridC = [(radius*math.cos(p*math.pi/180), radius*math.sin(p*math.pi/180)) for p in anglelist]
    gridX = [(g0[0],gC[0]) for (g0, gC) in zip(grid0, gridC)] 
    gridX = [s for s2 in gridX for s in s2]
    gridY = [(g0[1],gC[1]) for (g0, gC) in zip(grid0, gridC)] 
    gridY = [s for s2 in gridY for s in s2]

    def build_circle(radius):
        circleC = [radius for i in range(0, len(anglelist)+1)]
        circleX = [circleC[i]*math.cos(anglelist[i]*math.pi/180) for i in range(0,len(anglelist))]
        circleY = [circleC[i]*math.sin(anglelist[i]*math.pi/180) for i in range(0,len(anglelist))]
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
        values = {}
        dbs = []
        for a, z in zip(gridZ.index,gridZ):
            angle = 0
            if a != 'On-Axis':
                angle = int(a[:-1])
            angles.append(angle)
            dbs.append(z)

        # map in 2d
        dbsX = [db*math.cos(a*math.pi/180) for a,db in zip(angles, dbs)]
        dbsY = [db*math.sin(a*math.pi/180) for a,db in zip(angles, dbs)]
    
        # join with first point (-180=180)
        dbsX.append(dbsX[0])
        dbsY.append(dbsY[0])

        return dbsX, dbsY, [ihz for i in range(0,len(dbsX))]


    # build 3 plots 
    dbX = []
    dbY = []
    hzZ = []
    for ihz in [47, 113, 180]:
        X, Y, Z = project(splu.loc[ihz][1:])
        # add to global variable
        dbX.append(X)
        dbY.append(Y)
        hzZ.append(Z)

    # normalise
    dbmax = max(np.array(dbX).max(), np.array(dbY).max())
    dbX = [v2/dbmax for v1 in dbX for v2 in v1]
    dbY = [v2/dbmax for v1 in dbY for v2 in v1]
    hzZ = [hzname(i2) for i1 in hzZ for i2 in i1]

    grid_df = pd.DataFrame({'x': gridX, 'y': gridY })
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
    circle_df = pd.DataFrame({'x': circleX, 'y': circleY })
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
    text_df = pd.DataFrame({'x': textX, 'y': textY, 'text': textT })
    text = alt.Chart(text_df).mark_text().encode(
        alt.Latitude('x:Q'), 
        alt.Longitude('y:Q'),
        text='text:O'
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]   
    )

    dbs_df = pd.DataFrame({'x': dbX, 'y': dbY, 'Freq': hzZ })
    dbs = alt.Chart(dbs_df).mark_line().encode(
        alt.Latitude('x:Q'), 
        alt.Longitude('y:Q'),
        alt.Color('Freq:N', sort=None),
        size=alt.value(3)
    ).project(
        type='azimuthalEquidistant',
        rotate=[0, 0, 90]   
    )
   
    return dbs+grid+circle+text


def display_contour_horizontal(df, speaker, width=400, heigth=180):
    try:
        dfs = df[speaker]['SPL Horizontal_unmelted']
        return display_contour(dfs, width, heigth)
    except KeyError:
        return None

def display_contour_vertical(df, speaker, width=400, heigth=180):
    try:
        dfs = df[speaker]['SPL Vertical_unmelted']
        return display_contour(dfs, width, heigth)
    except KeyError:
        return None

def display_radar_horizontal(df, speaker, width=400, heigth=180):
    try:
        dfs = df[speaker]['SPL Horizontal_unmelted']
        return display_radar(dfs, width, heigth)
    except KeyError:
        return None

def display_radar_vertical(df, speaker, width=400, heigth=180):
    try:
        dfs = df[speaker]['SPL Vertical_unmelted']
        return display_radar(dfs, width, heigth)
    except KeyError:
        return None

def display_contour2(contour, width=400, heigth=180):
    # slighly better looking
    x, y, z = contour

    plt.figure()
    #levels = [-9,-6,-3]
    #contour = plt.contour(x, y, z, levels=3, alpha=0.2)
    #plt.clabel(contour, colors = 'k', fmt = '%2.1f', fontsize=12)
    levels = [-60,-40,-20,-10,-6,-5.5,-5,-4.5,-4,-3.5,-3, -2.5, -2, -1.5, -1, -0.5,0]
    contour_filled = plt.contourf(x, y, z, levels, alpha=0.5, cmap='rainbow')
    plt.colorbar(contour_filled)
    #plt.pcolormesh(x, y, z, shading='gouraud') #, cmap=plt.cm.BuGn_r)
    plt.title('Plot from level list')
    plt.xlabel('frequency (hz)')
    plt.ylabel('angle (degree)')
    plt.show()


def display_contour_smoothing(speaker, width=450, heigth=450):
    try:
        contourH = compute_contour(df[speaker]['SPL Horizontal_unmelted'])
        hx, hy, hz = contourH
        contourV = (hx, hy, np.array(smooth2D(hz)))
        #contourV = compute_contour(df[speaker]['SPL Vertical_unmelted'])
        return alt.hconcat(
            display_contour(contourH, width, heigth), 
            display_contour(contourV, width, heigth)
            )
    except KeyError:
       return None

def display_contour_sidebyside(df, speaker, width=450, heigth=450):
    try:
        contourH = compute_contour(df[speaker]['SPL Horizontal_unmelted'])
        contourV = compute_contour(df[speaker]['SPL Vertical_unmelted'])
        return alt.hconcat(display_contour(contourH, width, heigth), 
                           display_contour(contourV, width, heigth))
    except KeyError:
       return None


def display_spinorama(df, speaker, width, heigth):
    try:
        spinorama=df[speaker]['CEA2034']
        spinorama = spinorama.loc[spinorama['Measurements'] != 'DI offset']
        return display_freq(spinorama, width, heigth)
    except KeyError:
        return None

def display_reflection_early(df, speaker, width, heigth):
    try:
        return display_freq(df[speaker]['Early Reflections'], width, heigth)
    except KeyError:
       return None

def display_onaxis(df, speaker, width, heigth):
    try:
        onaxis=df[speaker]['CEA2034']
        onaxis = onaxis.loc[onaxis['Measurements']=='On Axis']
        onaxis_graph=display_freq(onaxis, width, heigth)
        onaxis_reg = alt.Chart(onaxis).transform_filter(
            'datum.Freq>80 & datum.Freq<18000'
        ).transform_regression(
            "Freq", "dB"
        ).mark_line().encode(
            alt.X('Freq:Q'),
            alt.Y('dB:Q'), 
            color=alt.value('red')
        )
        return onaxis_graph+onaxis_reg
    except KeyError:
        return None


def display_inroom(df, speaker, width, heigth):
    try:
        inroom = df[speaker]['Estimated In-Room Response']
        inroom_graph=display_freq(inroom, width, heigth)
        inroom_reg=alt.Chart(inroom).transform_filter(
            'datum.Freq>100 & datum.Freq<10000'
            ).transform_regression(
            "Freq", "dB"
        ).mark_line().encode(
            alt.X('Freq:Q'),
            alt.Y('dB:Q'), 
            color=alt.value('red')
        )
        return inroom_graph+inroom_reg
    except KeyError:
       return None


def display_reflection_horizontal(df, speaker, width, heigth):
    try:
        return display_freq(df[speaker]['Horizontal Reflections'], width, heigth)
    except KeyError:
       return None

def display_reflection_vertical(df, speaker, width, heigth):
    try:
        return display_freq(df[speaker]['Vertical Reflections'], width, heigth)
    except KeyError:
       return None

def display_spl(df, speaker, axis, width, heigth):
    try:
        spl = df[speaker][axis]
        filter = {'Measurements': ['On-Axis', '10°', '20°', '30°', '40°', '50°', '60°']}
        mask = spl.isin(filter).any(1)
        return display_freq(spl[mask], width, heigth) #.interactive()
    except KeyError:
       return None


def display_spl_horizontal(df, speaker, width, heigth):
    return display_spl(df, speaker, 'SPL Horizontal', width, heigth)


def display_spl_vertical(df, speaker, width, heigth):
    return display_spl(df, speaker, 'SPL Vertical', width, heigth)


def display_template1(df, speaker, width=900, heigth=500):
    width2 = width*45/100
    heigth2 = heigth*45/100
    width3 = width*30/100
    heigth3 = heigth*30/100
    # full size
    spinorama = display_spinorama(df, speaker, width, heigth)
    # side by side
    onaxis    = display_onaxis(df, speaker, width2, heigth2)
    inroom    = display_inroom(df, speaker, width2, heigth2)
    # side by side
    ereflex   = display_reflection_early(df, speaker, width3, heigth3)
    hreflex   = display_reflection_horizontal(df, speaker, width3, heigth3)
    vreflex   = display_reflection_vertical(df, speaker, width3, heigth3)
    # side by side
    hspl      = display_spl_horizontal(df, speaker, width2, heigth2)
    vspl      = display_spl_vertical(df, speaker, width2, heigth2)
    # side by side
    hcontour  = display_contour_horizontal(df,speaker, width2, heigth2)
    vcontour  = display_contour_vertical(df,speaker, width2, heigth2)
    return alt.vconcat(spinorama,
                       onaxis | inroom,
                       ereflex | hreflex | vreflex,
                       hspl | vspl,
                       hcontour | vcontour)

def display_vertical(df, speaker, width=900, heigth=500):
    spinorama = display_spinorama(df, speaker, width, heigth)
    onaxis    = display_onaxis(df, speaker, width, heigth)
    inroom    = display_inroom(df, speaker, width, heigth)
    ereflex   = display_reflection_early(df, speaker, width, heigth)
    hreflex   = display_reflection_horizontal(df, speaker, width, heigth)
    vreflex   = display_reflection_vertical(df, speaker, width, heigth)
    hspl      = display_spl_horizontal(df, speaker, width, heigth)
    vspl      = display_spl_vertical(df, speaker, width, heigth)
    hcontour  = display_contour_horizontal(df,speaker, width, heigth)
    hradar    = display_radar_horizontal(df,speaker, width, heigth)
    vcontour  = display_contour_vertical(df,speaker, width, heigth)
    vradar    = display_radar_vertical(df,speaker, width, heigth)
    return alt.vconcat(spinorama,
                       onaxis,
                       inroom,
                       ereflex,
                       hreflex,
                       vreflex,
                       hspl,
                       vspl,
                       hcontour,
                       hradar,
                       vcontour,
                       vradar)


def print_graph(speaker, title, chart, width, heigth, force):
    updated = 0
    filepath='docs/'+speaker+'/'+title
    if chart is not None:
        for ext in ['.json', '.png', '.html']: # .svg skipped slow
            if force or not os.path.exists(filepath+ext):
                chart.save(filepath+ext)
                updated += 1
    return updated


def print_graphs(df, speaker, width=900, heigth=500, force=False):
    dirpath = 'docs/'+speaker
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)

    graphs = {}
    graphs['CEA2034'] = display_spinorama(df, speaker, width, heigth)
    graphs['On Axis'] = display_onaxis(df, speaker, width, heigth)
    graphs['Estimated In-Room Response']  = display_inroom(df, speaker, width, heigth)
    graphs['Early Reflections'] = display_reflection_early(df, speaker, width, heigth)
    graphs['Horizontal Reflections'] = display_reflection_horizontal(df, speaker, width, heigth)
    graphs['Vertical Reflections'] = display_reflection_vertical(df, speaker, width, heigth)
    graphs['SPL Horizontal'] = display_spl_horizontal(df, speaker, width, heigth)
    graphs['SPL Vertical'] = display_spl_vertical(df, speaker, width, heigth)
    graphs['SPL Horizontal Contour'] = display_contour_horizontal(df, speaker, width, heigth)
    graphs['SPL Vertical Contour'] = display_contour_vertical(df, speaker, width, heigth)
    graphs['SPL Horizontal Radar'] = display_radar_horizontal(df, speaker, width, heigth)
    graphs['SPL Vertical Radar'] = display_radar_vertical(df, speaker, width, heigth)

    updated = 0
    for (title, graph) in graphs.items():
        updated += print_graph(speaker, title, graph, width, heigth, force)
    print('Speaker: {:s} updated {:2d} files'.format(speaker, updated))
