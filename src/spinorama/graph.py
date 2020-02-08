import altair as alt
alt.data_transformers.disable_max_rows()

nearest = alt.selection(type='single', nearest=True, on='mouseover',fields=['Freq'], empty='none')
# nearest

def display_graph_freq(df, width=900, heigth=500):
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


def display_graph_sidebyside(s1, s2, name):
    d1 = display_graph_freq(s1[name], 450, 450)
    d2 = display_graph_freq(s2[name], 450, 450)
    return alt.hconcat(d1, d2)
    
