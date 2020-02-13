import os
from .display import *

def print_graph(speaker, title, chart, width, heigth, force, fileext):
    updated = 0
    filepath = 'docs/' + speaker + '/' + title
    if chart is not None:
        for ext in ['json', 'png', 'html']:  # svg skipped slow
            filename = filepath + '.' + ext
            if force or not os.path.exists(filename):
                if fileext is None or (fileext is not None and fileext == ext):
                    chart.save(filename)
                    updated += 1
    return updated


def print_graphs(df, speaker, width=900, heigth=500, force=False, fileext=None):
    dirpath = 'docs/' + speaker
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)

    graphs = {}
    graphs['CEA2034'] = display_spinorama(df, speaker, width, heigth)
    graphs['On Axis'] = display_onaxis(df, speaker, width, heigth)
    graphs['Estimated In-Room Response'] = display_inroom(
        df, speaker, width, heigth)
    graphs['Early Reflections'] = display_reflection_early(
        df, speaker, width, heigth)
    graphs['Horizontal Reflections'] = display_reflection_horizontal(
        df, speaker, width, heigth)
    graphs['Vertical Reflections'] = display_reflection_vertical(
        df, speaker, width, heigth)
    graphs['SPL Horizontal'] = display_spl_horizontal(
        df, speaker, width, heigth)
    graphs['SPL Vertical'] = display_spl_vertical(df, speaker, width, heigth)
    graphs['SPL Horizontal Contour'] = display_contour_horizontal(
        df, speaker, width, heigth)
    graphs['SPL Vertical Contour'] = display_contour_vertical(
        df, speaker, width, heigth)
    graphs['SPL Horizontal Radar'] = display_radar_horizontal(
        df, speaker, width, heigth)
    graphs['SPL Vertical Radar'] = display_radar_vertical(
        df, speaker, width, heigth)

    updated = 0
    for (title, graph) in graphs.items():
        updated += print_graph(speaker, title, graph, width, 
                               heigth, force, fileext)
    print('Speaker: {:s} updated {:2d} files'.format(speaker, updated))
