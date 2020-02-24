import os
import logging
import pathlib
from .display import display_spinorama, display_onaxis, display_inroom, \
    display_reflection_early, display_reflection_horizontal, display_reflection_vertical, \
    display_spl_horizontal, display_spl_vertical, \
    display_contour_horizontal, display_contour_vertical, \
    display_radar_horizontal, display_radar_vertical
from .views import template_compact, template_panorama


def print_graph(speaker, origin, key, title, chart, width, height, force, fileext):
    updated = 0
    if chart is not None:
        filedir = 'docs/' + speaker + '/' + origin + '/' + key
        logging.debug('print_graph: write to directory {0}'.format(filedir))
        pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
        for ext in ['json', 'png', 'html']:  # svg skipped slow
            filename = filedir + '/' + title.replace('_unmelted', '') + '.' + ext
            if force or not os.path.exists(filename):
                if fileext is None or (fileext is not None and fileext == ext):
                    chart.save(filename)
                    updated += 1
    else:
        logging.debug('Chart is None for {:s} {:s} {:s} {:s}'.format(speaker, origin, key, title))
    return updated


def print_graphs(df,
                 speaker, origin, key='default',
                 width=900, height=500,
                 force_print=False, filter_file_ext=None):
    # may happens at development time
    if df is None:
        print('Error: print_graph is None')
        return 0

    graphs = {}
    graphs['CEA2034'] = display_spinorama(df, width, height)
    graphs['On Axis'] = display_onaxis(df, width, height)
    graphs['Estimated In-Room Response'] = display_inroom(df, width, height)
    graphs['Early Reflections'] = display_reflection_early(df, width, height)
    graphs['Horizontal Reflections'] = display_reflection_horizontal(df, width, height)
    graphs['Vertical Reflections'] = display_reflection_vertical(df, width, height)
    graphs['SPL Horizontal'] = display_spl_horizontal(df, width, height)
    graphs['SPL Vertical'] = display_spl_vertical(df, width, height)
    graphs['SPL Horizontal Contour'] = display_contour_horizontal(df, width, height)
    graphs['SPL Vertical Contour'] = display_contour_vertical(df, width, height)
    # 1080p to 2k screen
    graphs['2cols'] = template_compact(df, width, height)
    # 4k screen
    graphs['3cols'] = template_panorama(df, width*3, height*3)
    # better square
    size = max(width, height)
    graphs['SPL Horizontal Radar'] = display_radar_horizontal(df, size, size)
    graphs['SPL Vertical Radar'] = display_radar_vertical(df, size, size)

    updated = 0
    for (title, graph) in graphs.items():
        #                      adam / asr / default
        updated += print_graph(speaker, origin, key,
                               title, graph,
                               width, height, force_print, filter_file_ext)
    return updated
