#                                                  -*- coding: utf-8 -*-
import os
import logging
import pathlib
import copy
import pandas as pd
from altair_saver import save
import ray

from .speaker_display import display_spinorama, display_onaxis, display_inroom, \
    display_reflection_early, display_reflection_horizontal, display_reflection_vertical, \
    display_spl_horizontal, display_spl_vertical, \
    display_contour_horizontal, display_contour_vertical, \
    display_contour_smoothed_horizontal, display_contour_smoothed_vertical, \
    display_isoband_horizontal, display_isoband_vertical, \
    display_radar_horizontal, display_radar_vertical, display_directivity_matrix, \
    display_compare
from .speaker_views import template_compact, template_panorama, template_sidebyside_eq
from .graph import graph_params_default, contour_params_default, radar_params_default


def print_graph(speaker, origin, key, title, chart, force, fileext):
    updated = 0
    if chart is not None:
        filedir = 'docs/' + speaker + '/' + origin.replace('Vendors-','') + '/' + key
        pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
        for ext in ['json', 'png']: # svg and html skipped to keep size small
            # skip the 2cols.json and 3cols.json as they are really large
            # 2cols and 3cols are more for printing
            if ext == 'json' and title in (
                '2cols', '3cols',
                'SPL Horizontal Contour_smoothed', 'SPL Vertical Contour_smoothed',
                'SPL Horizontal IsoBand', 'SPL Vertical IsoBand',
                'Directivity Matrix',
                'ref_vs_eq'):
                continue
            # for now skip smoothed contours for Princeton graphs
            if origin == 'Princeton' and title in  ('SPL Horizontal Contour_smoothed', 'SPL Vertical Contour_smoothed'):
                continue
            # print high quality smoother contour and skip the others
            if ext == 'png' and (\
                (title in ('SPL Horizontal Contour', 'SPL Vertical Contour') and origin == 'ASR') or \
                (title in ('SPL Horizontal Contour_smoothed', 'SPL Vertical Contour_smoothed') and origin == 'Princeton')):
                continue
            filename = filedir + '/' + title.replace('_smoothed', '')
            if ext == 'png':
                # generate large image that are then easy to find and compress
                # before uploading
                filename +=  '_large'
            filename +=  '.' + ext
            if force or not os.path.exists(filename):
                if fileext is None or (fileext is not None and fileext == ext):
                    try:
                        print('Saving {0} in {1}'.format(title, filename))
                        save(chart, filename)
                        updated += 1
                    except Exception as e:
                        logging.error('Got unkown error {0} for {1}'.format(e, filename))
    else:
        logging.debug('Chart is None for {:s} {:s} {:s} {:s}'.format(speaker, origin, key, title))
    return updated


@ray.remote
def print_graphs(df: pd.DataFrame,
                 df_eq: pd.DataFrame,
                 speaker, origin, origins_info,
                 key='default',
                 width=900, height=500,
                 force_print=False, filter_file_ext=None):
    # may happens at development time
    if df is None:
        return 0

    params = copy.deepcopy(graph_params_default)
    params['width'] = width
    params['height'] = height
    params['xmin'] = origins_info[origin]['min hz']
    params['xmax'] = origins_info[origin]['max hz']
    params['ymin'] = origins_info[origin]['min dB']
    params['ymax'] = origins_info[origin]['max dB']
    logging.debug('Graph configured with {0}'.format(params))
    
    graphs = {}
    graphs['CEA2034'] = display_spinorama(df, params)
    graphs['On Axis'] = display_onaxis(df, params)
    graphs['Estimated In-Room Response'] = display_inroom(df, params)
    graphs['Early Reflections'] = display_reflection_early(df, params)
    graphs['Horizontal Reflections'] = display_reflection_horizontal(df, params)
    graphs['Vertical Reflections'] = display_reflection_vertical(df, params)
    graphs['SPL Horizontal'] = display_spl_horizontal(df, params)
    graphs['SPL Vertical'] = display_spl_vertical(df, params)

    # change params for contour
    params = copy.deepcopy(contour_params_default)
    params['width'] = width
    params['height'] = height
    params['xmin'] = origins_info[origin]['min hz']
    params['xmax'] = origins_info[origin]['max hz']

    # compute both: smoothed are large but looks better 
    graphs['SPL Horizontal Contour_smoothed'] = display_contour_smoothed_horizontal(df, params)
    graphs['SPL Vertical Contour_smoothed'] = display_contour_smoothed_vertical(df, params)
    graphs['SPL Horizontal Contour'] = display_contour_horizontal(df, params)
    graphs['SPL Vertical Contour'] = display_contour_vertical(df, params)

    # compute isoband
    isoband_params = {
        'xmin': 100,
        'xmax': 20000,
        'width': width,
        'height': height,
        'bands': [-72, -18, -15, -12, -9, -6, -3, +3],
    }

    graphs['SPL Horizontal IsoBand'] = display_isoband_horizontal(df, isoband_params)
    graphs['SPL Vertical IsoBand'] = display_isoband_vertical(df, isoband_params)

    # better square
    params = copy.deepcopy(radar_params_default)
    size = min(width, height)
    params['width'] = size
    params['height'] = size
    params['xmin'] = origins_info[origin]['min hz']
    params['xmax'] = origins_info[origin]['max hz']

    graphs['SPL Horizontal Radar'] = display_radar_horizontal(df, params)
    graphs['SPL Vertical Radar'] = display_radar_vertical(df, params)

    # compute directivity plots
    graphs['Directivity Matrix'] = display_directivity_matrix(df, params)

    # add a title and setup legend
    for k in graphs.keys():
        title = k.replace('_smoothed', '')
        # optimised for small screens / vertical orientation
        if graphs[k] is not None:
            graphs[k] = graphs[k].configure_legend(
                orient='bottom'
            ).configure_title(
                orient='top',
                anchor='middle',
                fontSize=16
            ).properties(
                    title='{2} for {0} measured by {1}'.format(speaker, origin, title)
            )

    # 1080p to 2k screen
    # -----------
    params = copy.deepcopy(graph_params_default)
    params['width'] = 2160
    # ratio for A4 is 21cm / 29.7cm, TODO for letter 
    params['height'] = 400
    params['xmin'] = origins_info[origin]['min hz']
    params['xmax'] = origins_info[origin]['max hz']
    params['ymin'] = origins_info[origin]['min dB']
    params['ymax'] = origins_info[origin]['max dB']
    graphs['2cols'] = template_compact(df, params, speaker, origin, key)

    # 4k screen
    # -----------
    #params['width'] = 4096
    #params['height'] = 1200
    #graphs['3cols'] = template_panorama(df, params, speaker, origin, key)

    # Ref vs. EQ
    # -----------
    # this graphs works but we can generate the same with html by building a 2 columns table
    # pointing to ref and eq versions
    # params = copy.deepcopy(graph_params_default)
    # params['width'] = 1200
    # params['height'] = 300
    # if df_eq is not None:
    #     graphs['ref_vs_eq'] = template_sidebyside_eq(df, df_eq, params, speaker, origin, key)

    updated = 0
    for (title, graph) in graphs.items():
        if graph is not None:
            updated = print_graph(speaker, origin, key, title, graph, force_print, filter_file_ext)
    return updated

@ray.remote
def print_compare(df, force_print=False, filter_file_ext=None):
    filedir = 'docs/compare'
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
    
    for graph_filter in (
        'CEA2034', 'Estimated In-Room Response',
        'Early Reflections', 'Horizontal Reflections', 'Vertical Reflections',
        'SPL Horizontal', 'SPL Vertical'):
        graph = display_compare(df, graph_filter)
        if graph is not None:
            graph = graph.configure_legend(orient='bottom').configure_title(orient='top', anchor='middle', fontSize=16)
            filename = '{0}/{1}.json'.format(filedir, graph_filter)
            try:
                print('Saving {0}'.format(filename))
                graph.save(filename)
            except Exception as e:
                logging.error('Got unkown error {0} for {1}'.format(e, filename))
    
    
