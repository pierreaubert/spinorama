import pandas as pd
import altair as alt
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


def display_freq_sidebyside(s1, s2, name):
    d1 = display_freq(s1[name], 450, 450)
    d2 = display_freq(s2[name], 450, 450)
    return alt.hconcat(d1, d2)
    

def display_contour(contour):
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
        width=400,
        height=180
    )

def display_contour_smoothing(speaker):
    contourH = compute_contour(df[speaker]['SPL Horizontal_unmelted'])
    hx, hy, hz = contourH
    contourV = (hx, hy, np.array(smooth2D(hz)))
    #contourV = compute_contour(df[speaker]['SPL Vertical_unmelted'])
    return alt.hconcat(
        contour_graph(contourH), 
        contour_graph(contourV)
    ).configure_range(
    )

def display_contour_sidebyside(df, speaker):
    contourH = compute_contour(df[speaker]['SPL Horizontal_unmelted'])
    contourV = compute_contour(df[speaker]['SPL Vertical_unmelted'])
    return alt.hconcat(
        display_contour(contourH), 
        display_contour(contourV)
    ).configure_range(
    )
