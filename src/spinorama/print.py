import os
from .display import display_spinorama, display_onaxis, display_inroom, \
    display_reflection_early, display_reflection_horizontal, display_reflection_vertical, \
    display_spl_horizontal, display_spl_vertical, \
    display_contour_horizontal, display_contour_vertical, \
    display_radar_horizontal, display_radar_vertical
from .views import template_compact, template_panorama


def print_graph(speaker, title, chart, width, height, force, fileext):
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


def print_graphs(df, speaker, width=900, height=500, force=False, fileext=None):
    dirpath = 'docs/' + speaker
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)

    graphs = {}
    graphs['CEA2034'] = display_spinorama(df, speaker, width, height)
    graphs['On Axis'] = display_onaxis(df, speaker, width, height)
    graphs['Estimated In-Room Response'] = display_inroom(
        df, speaker, width, height)
    graphs['Early Reflections'] = display_reflection_early(
        df, speaker, width, height)
    graphs['Horizontal Reflections'] = display_reflection_horizontal(
        df, speaker, width, height)
    graphs['Vertical Reflections'] = display_reflection_vertical(
        df, speaker, width, height)
    graphs['SPL Horizontal'] = display_spl_horizontal(
        df, speaker, width, height)
    graphs['SPL Vertical'] = display_spl_vertical(df, speaker, width, height)
    graphs['SPL Horizontal Contour'] = display_contour_horizontal(
        df, speaker, width, height)
    graphs['SPL Vertical Contour'] = display_contour_vertical(
        df, speaker, width, height)
    # 1080p to 2k screen
    graphs['2cols'] = template_compact(df, speaker, width, height)
    # 4k screen
    graphs['3cols'] = template_panorama(df, speaker, width*3, height*3)
    # better square
    size = max(width, height)
    graphs['SPL Horizontal Radar'] = display_radar_horizontal(df, speaker, size, size)
    graphs['SPL Vertical Radar'] = display_radar_vertical(df, speaker, size, size)

    updated = 0
    for (title, graph) in graphs.items():
        updated += print_graph(speaker, title, graph, width,
                               height, force, fileext)
    return updated
