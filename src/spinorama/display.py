import altair as alt
import matplotlib.pyplot as plt
from .graph import graph_freq, graph_contour, graph_radar
#    graph_contour_smoothed


alt.data_transformers.disable_max_rows()


def graph_freq_sidebyside(s1, s2, name, width=450, height=450):
    d1 = graph_freq(s1[name], width, height)
    d2 = graph_freq(s2[name], width, height)
    return alt.hconcat(d1, d2)


def display_contour_horizontal(df, speaker, width=400, height=180):
    try:
        dfs = df[speaker]['SPL Horizontal_unmelted']
        return graph_contour(dfs, width, height)
    except KeyError:
        return None


def display_contour_vertical(df, speaker, width=400, height=180):
    try:
        dfs = df[speaker]['SPL Vertical_unmelted']
        return graph_contour(dfs, width, height)
    except KeyError:
        return None


def display_radar_horizontal(df, speaker, width=400, height=180):
    try:
        dfs = df[speaker]['SPL Horizontal_unmelted']
        return graph_radar(dfs, width, height)
    except KeyError:
        return None


def display_radar_vertical(df, speaker, width=400, height=180):
    try:
        dfs = df[speaker]['SPL Vertical_unmelted']
        return graph_radar(dfs, width, height)
    except KeyError:
        return None


def display_contour2(contour, width=400, height=180):
    # slighly better looking
    x, y, z = contour

    plt.figure()
    # levels = [-9,-6,-3]
    # contour = plt.contour(x, y, z, levels=3, alpha=0.2)
    # plt.clabel(contour, colors = 'k', fmt = '%2.1f', fontsize=12)
    levels = [-60, -40, -20, -10, -6, -5.5, -5, -
              4.5, -4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0]
    contour_filled = plt.contourf(x, y, z, levels, alpha=0.5, cmap='rainbow')
    plt.colorbar(contour_filled)
    # plt.pcolormesh(x, y, z, shading='gouraud') #, cmap=plt.cm.BuGn_r)
    plt.title('Plot from level list')
    plt.xlabel('frequency (hz)')
    plt.ylabel('angle (degree)')
    plt.show()


def display_contour_sidebyside(df, speaker, width=450, height=450):
    try:
        contourH = df[speaker]['SPL Horizontal_unmelted']
        contourV = df[speaker]['SPL Vertical_unmelted']
        return alt.hconcat(
            graph_contour(contourH, width, height),
            graph_contour(contourV, width, height))
    except KeyError:
        return None


def display_spinorama(df, speaker, width, height):
    try:
        spinorama = df[speaker]['CEA2034']
        spinorama = spinorama.loc[spinorama['Measurements'] != 'DI offset']
        return graph_freq(spinorama, width, height)
    except KeyError:
        return None


def display_reflection_early(df, speaker, width, height):
    try:
        return graph_freq(df[speaker]['Early Reflections'], width, height)
    except KeyError:
        return None


def display_onaxis(df, speaker, width, height):
    try:
        onaxis = df[speaker]['CEA2034']
        onaxis = onaxis.loc[onaxis['Measurements'] == 'On Axis']
        onaxis_graph = graph_freq(onaxis, width, height)
        onaxis_reg = alt.Chart(onaxis).transform_filter(
            'datum.Freq>80 & datum.Freq<18000'
        ).transform_regression(
            "Freq", "dB"
        ).mark_line().encode(
            alt.X('Freq:Q'),
            alt.Y('dB:Q'),
            color=alt.value('red')
        )
        return onaxis_graph + onaxis_reg
    except KeyError:
        return None


def display_inroom(df, speaker, width, height):
    try:
        inroom = df[speaker]['Estimated In-Room Response']
        inroom_graph = graph_freq(inroom, width, height)
        inroom_reg = alt.Chart(inroom).transform_filter(
            'datum.Freq>100 & datum.Freq<10000'
        ).transform_regression(
            "Freq", "dB"
        ).mark_line().encode(
            alt.X('Freq:Q'),
            alt.Y('dB:Q'),
            color=alt.value('red')
        )
        return inroom_graph + inroom_reg
    except KeyError:
        return None


def display_reflection_horizontal(df, speaker, width, height):
    try:
        return graph_freq(
            df[speaker]['Horizontal Reflections'], width, height)
    except KeyError:
        return None


def display_reflection_vertical(df, speaker, width, height):
    try:
        return graph_freq(df[speaker]['Vertical Reflections'], width, height)
    except KeyError:
        return None


def display_spl(df, speaker, axis, width, height):
    try:
        spl = df[speaker][axis]
        filter = {
            'Measurements': [
                'On-Axis',
                '10°',
                '20°',
                '30°',
                '40°',
                '50°',
                '60°']}
        mask = spl.isin(filter).any(1)
        return graph_freq(spl[mask], width, height)  # .interactive()
    except KeyError:
        return None


def display_spl_horizontal(df, speaker, width, height):
    return display_spl(df, speaker, 'SPL Horizontal', width, height)


def display_spl_vertical(df, speaker, width, height):
    return display_spl(df, speaker, 'SPL Vertical', width, height)
