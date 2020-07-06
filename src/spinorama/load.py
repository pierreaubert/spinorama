#                                                  -*- coding: utf-8 -*-
import logging
import pandas as pd


from .compute_cea2034 import early_reflections, vertical_reflections, horizontal_reflections, compute_cea2034, compute_onaxis, estimated_inroom_HV

def graph_melt(df : pd.DataFrame):
    return df.reset_index().melt(id_vars='Freq', var_name='Measurements', value_name='dB').loc[lambda df: df['Measurements'] != 'index']

def compute_graphs(speaker_name, h_spl, v_spl):
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
                logging.info('{0} computation is None for speaker{1:s} (Princeton)'.format(title, speaker_name))
        except KeyError as ke:
            logging.warning('{0} computation failed with key:{1} for speaker{2:s} (Princeton)'.format(title, ke, speaker_name))
    return dfs


