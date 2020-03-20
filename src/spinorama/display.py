import logging
import altair as alt
import pandas as pd
from .normalize import resample, normalize
from .graph import graph_freq, graph_contour_smoothed, graph_radar, graph_spinorama,\
    graph_params_default, contour_params_default, radar_params_default, \
    graph_contour, graph_directivity_matrix, graph_compare


alt.data_transformers.disable_max_rows()


def display_contour_horizontal(df, graph_params=contour_params_default):
    try:
        if 'SPL Horizontal_unmelted' not in df.keys():
            return None
        dfs = df['SPL Horizontal_unmelted']
        dfs = resample(dfs, 400)
        return graph_contour(dfs, graph_params)
    except KeyError as ke:
        logging.warning('Display Contour Horizontal failed with {0}'.format(ke))
        return None


def display_contour_vertical(df, graph_params=contour_params_default):
    try:
        if 'SPL Vertical_unmelted' not in df.keys():
            return None
        dfs = df['SPL Vertical_unmelted']
        dfs = resample(dfs, 400)
        return graph_contour(dfs, graph_params)
    except KeyError as ke:
        logging.warning('Display Contour Vertical failed with {0}'.format(ke))
        return None


def display_contour_smoothed_horizontal(df, graph_params=contour_params_default):
    try:
        if 'SPL Horizontal_unmelted' not in df.keys():
            return None
        dfs = df['SPL Horizontal_unmelted']
        dfs = resample(dfs, 400)
        return graph_contour_smoothed(dfs, graph_params)
    except KeyError as ke:
        logging.warning('Display Contour Horizontal failed with {0}'.format(ke))
        return None


def display_contour_smoothed_vertical(df, graph_params=contour_params_default):
    try:
        if 'SPL Vertical_unmelted' not in df.keys():
            return None
        dfs = df['SPL Vertical_unmelted']
        dfs = resample(dfs, 400)
        return graph_contour_smoothed(dfs, graph_params)
    except KeyError as ke:
        logging.warning('Display Contour Vertical failed with {0}'.format(ke))
        return None


def display_radar_horizontal(df, graph_params=radar_params_default):
    try:
        if 'SPL Horizontal_unmelted' not in df.keys():
            return None
        dfs = df['SPL Horizontal_unmelted']
        return graph_radar(dfs, graph_params)
    except (KeyError, IndexError, ValueError) as e:
        logging.warning('Display Radar Horizontal failed with {0}'.format(e))
        return None


def display_radar_vertical(df, graph_params=radar_params_default):
    try:
        if 'SPL Vertical_unmelted' not in df.keys():
            return None
        dfs = df['SPL Vertical_unmelted']
        return graph_radar(dfs, graph_params)
    except (KeyError, IndexError, ValueError) as e:
        logging.warning('Display Radar Horizontal failed with {0}'.format(e))
        return None


def display_contour_sidebyside(df, graph_params=contour_params_default):
    try:
        contourH = df['SPL Horizontal_unmelted']
        contourV = df['SPL Vertical_unmelted']
        return alt.hconcat(
            graph_contour_smoothed(contourH, graph_params),
            graph_contour_smoothed(contourV, graph_params))
    except KeyError as ke:
        logging.warning('Display Contour side by side failed with {0}'.format(ke))
        return None


def display_spinorama(df, graph_params=graph_params_default):
    try:
        if 'CEA2034' not in df.keys():
            return None
        spinorama = df['CEA2034']
        if spinorama is not None:
            spinorama = spinorama.loc[spinorama['Measurements'] != 'DI offset']
            return graph_spinorama(spinorama, graph_params)
        else:
            logging.info('Display CEA2034 is empty')
    except KeyError as ke:
        logging.info('Display CEA2034 not in dataframe {0}'.format(ke))
    return None


def display_reflection_early(df, graph_params=graph_params_default):
    try:
        if 'Early Reflections' not in df.keys():
            return None
        return graph_freq(df['Early Reflections'], graph_params)
    except KeyError as ke:
        logging.warning('Display Early Reflections failed with {0}'.format(ke))
        return None


def display_onaxis(df, graph_params=graph_params_default):
    try:
        if 'CEA2034' not in df.keys():
            return None
        onaxis = df['CEA2034']
        onaxis = onaxis.loc[onaxis['Measurements'] == 'On Axis']
        onaxis_graph = graph_freq(onaxis, graph_params)
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
    except KeyError as ke:
        logging.warning('Display On Axis failed with {0}'.format(ke))
        return None
    except AttributeError as ae:
        logging.warning('Display On Axis failed with {0}'.format(ae))
        return None


def display_inroom(df, graph_params=graph_params_default):
    try:
        if 'Estimated In-Room Response' not in df.keys():
            return None
        inroom = df['Estimated In-Room Response']
        inroom_graph = graph_freq(inroom, graph_params)
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
    except KeyError as ke:
        logging.warning('Display In Room failed with {0}'.format(ke))
        return None


def display_reflection_horizontal(df, graph_params=graph_params_default):
    try:
        if 'Horizontal Reflections' not in df.keys():
            return None
        return graph_freq(
            df['Horizontal Reflections'], graph_params)
    except KeyError as ke:
        logging.warning('Display Horizontal Reflections failed with {0}'.format(ke))
        return None


def display_reflection_vertical(df, graph_params=graph_params_default):
    try:
        if 'Vertical Reflections' not in df.keys():
            return None
        return graph_freq(df['Vertical Reflections'], graph_params)
    except KeyError:
        return None


def display_spl(df, axis, graph_params=graph_params_default):
    try:
        if axis not in df.keys():
            return None
        spl = df[axis]
        filter = {
            'Measurements': [
                'On Axis',
                '10°',
                '20°',
                '30°',
                '40°',
                '50°',
                '60°']}
        mask = spl.isin(filter).any(1)
        spl = spl[mask]
        spl = resample(spl, 400)
        return graph_freq(spl, graph_params)
    except KeyError as ke:
        logging.warning('Display SPL failed with {0}'.format(ke))
        return None


def display_spl_horizontal(df, graph_params=graph_params_default):
    return display_spl(df, 'SPL Horizontal', graph_params)


def display_spl_vertical(df, graph_params=graph_params_default):
    return display_spl(df, 'SPL Vertical', graph_params)


def display_directivity_matrix(df, graph_params=graph_params_default):
    try:
        return graph_directivity_matrix(df, graph_params)
    except Exception as e:
        logging.warning('Display directivity matrix failed with {0}'.format(e))
        return None


def display_compare(df,  graph_filter, graph_params=graph_params_default):

    def augment(dfa, name):
        # print(name)
        namearray = [name for i in range(0,len(dfa))]
        dfa['Speaker'] = name
        return dfa

    try:
        source = pd.concat( 
            [augment(
                normalize(
                    resample(df[k][o]['default'][graph_filter], 300)),
                k+' - '+o)
            for k in df.keys() for o in df[k].keys() if graph_filter in df[k][o]['default']]
        )

        speaker1 = 'KEF LS50 - ASR'
        speaker2 = 'KEF LS50 - Princeton'
        return graph_compare(source, graph_params, speaker1, speaker2)
    except ValueError as e:
        logging.warning('failed for {0} with {1}'.format(graph_filter, e))
        return None
