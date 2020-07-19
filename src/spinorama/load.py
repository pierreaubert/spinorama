#                                                  -*- coding: utf-8 -*-
import logging
import pandas as pd

from .compute_normalize import normalize_mean, normalize_cea2034, normalize_graph
from .compute_cea2034 import early_reflections, vertical_reflections, horizontal_reflections, compute_cea2034, compute_onaxis, estimated_inroom_HV


def graph_melt(df : pd.DataFrame):
    return df.reset_index().melt(id_vars='Freq', var_name='Measurements', value_name='dB').loc[lambda df: df['Measurements'] != 'index']


def load_normalize(df, ref_mean=None):
    # normalize all melted graphs
    dfc = {}
    if 'CEA2034' in df:
        mean = ref_mean
        if ref_mean == None:
            mean = normalize_mean(df['CEA2034'])
            dfc['CEA2034_original_mean'] = mean
        for graph in df.keys():
            if graph != 'CEA2034':
                if graph.replace('_unmelted', '') != graph:
                    dfc[graph] = df[graph]
                else:
                    dfc[graph] = normalize_graph(df[graph], mean)
        dfc['CEA2034'] = normalize_cea2034(df['CEA2034'], mean)
        logging.debug('mean for normalisation {0}'.format(mean))
        return dfc
    elif 'On Axis' in df:
        mean = ref_mean
        if ref_mean == None:
            mean = normalize_mean(df['On Axis'])
            dfc['On Axis_original_mean'] = mean
        for graph in df.keys():
            if graph.replace('_unmelted', '') != graph:
                dfc[graph] = df[graph]
            else:
                dfc[graph] = normalize_graph(df[graph], mean)
        logging.debug('mean for normalisation {0}'.format(mean))
        return dfc
        
    # do nothing
    logging.error('CEA2034 and On Axis are not in df knows keys are {0}'.format(df.keys()))
    return df


def filter_graphs(speaker_name, h_spl, v_spl):
    dfs = {}
    # add H and V SPL graphs
    if h_spl is not None:
        dfs['SPL Horizontal_unmelted'] = h_spl
        dfs['SPL Horizontal'] = graph_melt(h_spl)
    if v_spl is not None:
        dfs['SPL Vertical_unmelted'] = v_spl
        dfs['SPL Vertical'] = graph_melt(v_spl)
    # add computed graphs
    table = [['Early Reflections', early_reflections],
             ['Horizontal Reflections', horizontal_reflections],
             ['Vertical Reflections', vertical_reflections],
             ['Estimated In-Room Response', estimated_inroom_HV],
             ['On Axis', compute_onaxis],
             ['CEA2034', compute_cea2034],
             ]
    for title, functor in table:
        try:
            df = functor(h_spl, v_spl)
            if df is not None:
                dfs[title+'_unmelted'] = df
                dfs[title] = graph_melt(df)
            else:
                logging.info('{0} computation is None for speaker{1:s}'.format(title, speaker_name))
        except KeyError as ke:
            logging.warning('{0} computation failed with key:{1} for speaker{2:s}'.format(title, ke, speaker_name))
    return dfs


