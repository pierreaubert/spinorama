import os
import logging
import pathlib
import copy
import pandas as pd
from .display import display_spinorama, display_onaxis, display_inroom, \
    display_reflection_early, display_reflection_horizontal, display_reflection_vertical, \
    display_spl_horizontal, display_spl_vertical, \
    display_contour_horizontal, display_contour_vertical, \
    display_contour_smoothed_horizontal, display_contour_smoothed_vertical, \
    display_radar_horizontal, display_radar_vertical, display_directivity_matrix, \
    display_compare
from .views import template_compact, template_panorama
from .graph import graph_params_default, contour_params_default, radar_params_default


def print_graph(speaker, origin, key, title, chart, force, fileext):
    updated = 0
    if chart is not None:
        filedir = 'docs/' + speaker + '/' + origin.replace('Vendors/','') + '/' + key
        logging.debug('print_graph: write to directory {0}'.format(filedir))
        pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
        for ext in ['json', 'png']: # svg and html skipped to keep size small
            # skip the 2cols.json and 3cols.json as they are really large
            # 2cols and 3cols are more for printing
            if ext == 'json' and title in ('2cols', '3cols', 'SPL Horizontal Contour_smoothed', 'SPL Vertical Contour_smoothed'):
                continue
            # for now skip 2cols and 3cols for Princeton graphs
            if origin == 'Princeton' and title in  ('2cols', '3cols', 'SPL Horizontal Contour_smoothed', 'SPL Vertical Contour_smoothed'):
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
                        chart.save(filename)
                        updated += 1
                    except Exception as e:
                        logging.error('Got unkown error {0} for {1}'.format(e, filename))
    else:
        logging.debug('Chart is None for {:s} {:s} {:s} {:s}'.format(speaker, origin, key, title))
    return updated


def print_graphs(df: pd.DataFrame,
                 speaker, origin, origins_info,
                 key='default',
                 width=900, height=500,
                 force_print=False, filter_file_ext=None):
    # may happens at development time
    if df is None:
        print('Error: print_graph is None')
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

    # 1080p to 2k screen
    params = copy.deepcopy(graph_params_default)
    params['width'] = 2160
    params['height'] = 1200
    params['xmin'] = origins_info[origin]['min hz']
    params['xmax'] = origins_info[origin]['max hz']
    params['ymin'] = origins_info[origin]['min dB']
    params['ymax'] = origins_info[origin]['max dB']
    graphs['2cols'] = template_compact(df, params)
    # 4k screen
    params['width'] = 4096
    params['height'] = 1200
    graphs['3cols'] = template_panorama(df, params)

    updated = 0
    for (title, graph) in graphs.items():
        #                      adam / asr / default
        if graph is not None:
            updated += print_graph(speaker, origin, key,
                                title, graph,
                                force_print, filter_file_ext)
    return updated


def print_compare(df, force_print=False, filter_file_ext=None):
    filedir = 'docs/compare'
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
    
    for filter in ('CEA2034', 'Estimated In-Room Response',
                   'Early Reflections', 'Horizontal Reflections', 'Vertical Reflections',
                   'SPL Horizontal', 'SPL Vertical'):
        graph = display_compare(df, filter)
        if graph is not None:
            filename = '{0}/{1}.json'.format(filedir, filter)
            if force_print or not os.path.exists(filename):
                if filter_file_ext is None or (filter_file_ext is not None and filter_file_ext == 'json'):
                    try:
                        print('Saving {0}'.format(filename))
                        graph.save(filename)
                    except Exception as e:
                        logging.error('Got unkown error {0} for {1}'.format(e, filename))
    
    
