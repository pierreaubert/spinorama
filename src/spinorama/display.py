import logging
import altair as alt
import matplotlib.pyplot as plt
from .graph import graph_freq, graph_contour, graph_radar
#    graph_contour_smoothed


alt.data_transformers.disable_max_rows()


def display_contour_horizontal(df, width=400, height=180):
    try:
        dfs = df['SPL Horizontal_unmelted']
        return graph_contour(dfs, width, height)
    except KeyError as ke:
        logging.warning('Contour Horizontal failed with {0}'.format(ke))
        return None


def display_contour_vertical(df, width=400, height=180):
    try:
        dfs = df['SPL Vertical_unmelted']
        return graph_contour(dfs, width, height)
    except KeyError as ke:
        logging.warning('Contour Vertical failed with {0}'.format(ke))
        return None


def display_radar_horizontal(df, width=400, height=180):
    try:
        dfs = df['SPL Horizontal_unmelted']
        return graph_radar(dfs, width, height)
    except KeyError as ke:
        logging.warning('Radar Horizontal failed with {0}'.format(ke))
        return None
    except IndexError as ie:
        logging.warning('Radar Horizontal failed with {0}'.format(ie))
        return None


def display_radar_vertical(df, width=400, height=180):
    try:
        dfs = df['SPL Vertical_unmelted']
        return graph_radar(dfs, width, height)
    except KeyError as ke:
        logging.warning('Radar Vertical failed with {0}'.format(ke))
        return None
    except IndexError as ie:
        logging.warning('Radar Vertical failed with {0}'.format(ie))
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


def display_contour_sidebyside(df, width=450, height=450):
    try:
        contourH = df['SPL Horizontal_unmelted']
        contourV = df['SPL Vertical_unmelted']
        return alt.hconcat(
            graph_contour(contourH, width, height),
            graph_contour(contourV, width, height))
    except KeyError:
        return None


def display_spinorama(df, width, height):
    try:
        spinorama = df['CEA2034']
        if spinorama is not None:
            spinorama = spinorama.loc[spinorama['Measurements'] != 'DI offset']
            return graph_freq(spinorama, width, height)
        else:
            logging.info('\'CEA2034\' is empty')
    except KeyError:
        logging.info('\'CEA2034\' not in dataframe')
    return None


def display_reflection_early(df, width, height):
    try:
        return graph_freq(df['Early Reflections'], width, height)
    except KeyError:
        return None


def display_onaxis(df, width, height):
    try:
        onaxis = df['CEA2034']
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
    except (KeyError, AttributeError):
        return None


def display_inroom(df, width, height):
    try:
        inroom = df['Estimated In-Room Response']
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


def display_reflection_horizontal(df, width, height):
    try:
        return graph_freq(
            df['Horizontal Reflections'], width, height)
    except KeyError:
        return None


def display_reflection_vertical(df, width, height):
    try:
        return graph_freq(df['Vertical Reflections'], width, height)
    except KeyError:
        return None


def display_spl(df, axis, width, height):
    try:
        spl = df[axis]
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


def display_spl_horizontal(df, width, height):
    return display_spl(df, 'SPL Horizontal', width, height)


def display_spl_vertical(df, width, height):
    return display_spl(df, 'SPL Vertical', width, height)
