import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
alt.data_transformers.disable_max_rows()
from .contour import compute_contour

nearest = alt.selection(type='single', nearest=True, on='mouseover',fields=['Freq'], empty='none')
# nearest

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
    

def display_contour(contour, width=400, heigth=180):
    af, am, az = contour
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
    except KeyNotFound:
       return None

def display_contour_sidebyside(df, speaker, width=450, heigth=450):
    try:
        contourH = compute_contour(df[speaker]['SPL Horizontal_unmelted'])
        contourV = compute_contour(df[speaker]['SPL Vertical_unmelted'])
        return alt.hconcat(display_contour(contourH, width, heigth), 
                           display_contour(contourV, width, heigth))
    except KeyNotFound:
       return None


def display_spinorama(df, speaker, width, heigth):
    try:
        spinorama=df[speaker]['CEA2034']
        spinorama = spinorama.loc[spinorama['Measurements'] != 'DI offset']
        return display_freq(spinorama, width, heigth)
    except KeyNotFound:
       return None

def display_reflection_early(df, speaker, width, heigth):
    try:
        return display_freq(df[speaker]['Early Reflections'], width, heigth)
    except KeyNotFound:
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
    except KeyNotFound:
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
    except KeyNotFound:
       return None


def display_reflection_horizontal(df, speaker, width, heigth):
    try:
        return display_freq(df[speaker]['Horizontal Reflections'], width, heigth)
    except KeyNotFound:
       return None

def display_reflection_vertical(df, speaker, width, heigth):
    try:
        return display_freq(df[speaker]['Vertical Reflections'], width, heigth)
    except KeyNotFound:
       return None

def display_spl(df, speaker, axis, width, heigth):
    try:
        spl = df[speaker][axis]
        filter = {'Measurements': ['On-Axis', '10°', '20°', '30°', '40°', '50°', '60°']}
        mask = spl.isin(filter).any(1)
        return display_freq(spl[mask], width, heigth) #.interactive()
    except KeyNotFound:
       return None

def display_spl_horizontal(df, speaker, width, heigth):
    try:
        return display_spl(df, speaker, 'SPL Horizontal', width, heigth)
    except KeyNotFound:
       return None

def display_spl_vertical(df, speaker, width, heigth):
    try:
        return display_spl(df, speaker, 'SPL Vertical', width, heigth)
    except KeyNotFound:
       return None


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
    hcontour  = display_contour(compute_contour(df[speaker]['SPL Horizontal_unmelted']), width2, heigth2)
    vcontour  = display_contour(compute_contour(df[speaker]['SPL Vertical_unmelted']), width2, heigth2)
    return alt.vconcat(spinorama,
                       onaxis | inroom,
                       ereflex | hreflex | vreflex,
                       hspl | vspl,
                       hcontour | vcontour)

