import logging
import math
import copy
import altair as alt
from .display import \
    display_spinorama, \
    display_onaxis, \
    display_inroom, \
    display_reflection_early, \
    display_reflection_horizontal, \
    display_reflection_vertical, \
    display_spl_horizontal, \
    display_spl_vertical, \
    display_contour_horizontal, \
    display_contour_vertical, \
    display_radar_horizontal, \
    display_radar_vertical


def scale_params(params, factor):
    new_params = copy.deepcopy(params)
    width = params['width']
    height = params['height']
    if factor == 3:
        new_width = math.floor(width * 30 / 100)
        new_height = math.floor(height * 30 / 100)
    else:
        new_width = math.floor(width * 45 / 100)
        new_height = math.floor(height * 45 / 100)
    new_params['width'] = new_width
    new_params['height'] = new_height
    for check in ('xmin', 'xmax'):
        if check not in new_params.keys():
            logging.error('scale_param {0} is not a key'.format(check))
    if new_params['xmin'] == new_params['xmax']:
            logging.error('scale_param x-range is empty')
    if 'ymin' in new_params.keys() and 'ymax' in new_params.keys() and new_params['ymin'] == new_params['ymax']:
            logging.error('scale_param y-range is empty')
    return new_params


def template_compact(df, params):
    params2 = scale_params(params, 2)
    params3 = scale_params(params, 3)
    # full size
    spinorama = display_spinorama(df, params)
    # side by side
    onaxis = display_onaxis(df, params2)
    inroom = display_inroom(df, params2)
    # side by side
    ereflex = display_reflection_early(df, params3)
    hreflex = display_reflection_horizontal(df, params3)
    vreflex = display_reflection_vertical(df, params3)
    # side by side
    hspl = display_spl_horizontal(df, params2)
    vspl = display_spl_vertical(df, params2)
    # side by side
    hcontour = display_contour_horizontal(df, params2)
    hradar = display_radar_horizontal(df, params2)
    # side by side
    vcontour = display_contour_vertical(df, params2)
    vradar = display_radar_vertical(df, params2)
    # build the chart
    chart = alt.vconcat()
    if spinorama is not None:
        chart &= alt.hconcat(spinorama)
    if onaxis is not None and inroom is not None:
        chart &= alt.hconcat(onaxis, inroom)
    if ereflex is not None and hreflex is not None and vreflex is not None:
        chart &= alt.hconcat(ereflex, hreflex, vreflex)
    if hspl is not None and vspl is not None:
        chart &= alt.hconcat(hspl, vspl)
    if hcontour is not None and hradar is not None:
        chart &= alt.hconcat(hcontour, hradar)
    if vcontour is not None and vradar is not None:
        chart &= alt.hconcat(vcontour, vradar)
    return chart


def template_panorama(df, params):
    params3 = scale_params(params, 3)
    # side by side
    spinorama = display_spinorama(df, params3)
    onaxis = display_onaxis(df, params3)
    inroom = display_inroom(df, params3)
    # side by side
    ereflex = display_reflection_early(df, params3)
    hreflex = display_reflection_horizontal(df, params3)
    vreflex = display_reflection_vertical(df, params3)
    # side by side
    hspl = display_spl_horizontal(df, params3)
    hcontour = display_contour_horizontal(df, params3)
    hradar = display_radar_horizontal(df, params3)
    # side by side
    vcontour = display_contour_vertical(df, params3)
    vspl = display_spl_vertical(df, params3)
    vradar = display_radar_vertical(df, params3)
    # build the chart
    chart = alt.vconcat()
    if spinorama is not None and onaxis is not None and inroom is not None:
        chart &= alt.hconcat(spinorama, onaxis, inroom)
    if ereflex is not None and hreflex is not None and vreflex is not None:
        chart &= alt.hconcat(ereflex, hreflex, vreflex)
    if hspl is not None and hcontour is not None and hradar is not None:
        chart &= alt.hconcat(hcontour, hradar, hspl)
    if vspl is not None and vcontour is not None and vradar is not None:
        chart &= alt.hconcat(vcontour, vradar, vspl)
    return chart


def template_vertical(df, params):
    spinorama = display_spinorama(df, params)
    onaxis = display_onaxis(df, params)
    inroom = display_inroom(df, params)
    ereflex = display_reflection_early(df, params)
    hreflex = display_reflection_horizontal(df, params)
    vreflex = display_reflection_vertical(df, params)
    hspl = display_spl_horizontal(df, params)
    vspl = display_spl_vertical(df, params)
    hcontour = display_contour_horizontal(df, params)
    hradar = display_radar_horizontal(df, params)
    vcontour = display_contour_vertical(df, params)
    vradar = display_radar_vertical(df, params)
    char = alt.vconcat()
    for g in (spinorama, onaxis, inroom, ereflex, hreflex, vreflex,
              hspl, vspl, hcontour, hradar, vcontour, vradar):
        if g is not None:
            chart &= g
    return chart 


# def template_freq_sidebyside(s1, s2, name, width=450, height=450):
#     df1 = display_graph_freq(s1[name], params)
#     df2 = display_graph_freq(s2[name], params)
#     if df1 is None and df2 is None:
#         return None
#     if df1 is None:
#         return df2
#     if df2 is None:
#         return df1
#     return alt.hconcat(df1, df2)
