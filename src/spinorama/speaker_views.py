#                                                  -*- coding: utf-8 -*-
import logging
import math
import copy
import altair as alt
from .speaker_display import \
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
    display_contour_smoothed_horizontal, \
    display_contour_smoothed_vertical, \
    display_radar_horizontal, \
    display_radar_vertical, \
    display_isoband_horizontal, \
    display_isoband_vertical, \
    display_summary, \
    display_pict


logger = logging.getLogger('spinorama')


SPACING = 20
LEGEND = 60

def scale_params(params, factor):
    new_params = copy.deepcopy(params)
    width = params['width']
    height = params['height']
    if factor == 3:
        new_width = math.floor(width - 6*SPACING)/3
        new_height = math.floor(height - 6*SPACING)/3
        new_params['height'] = new_height
    else:
        new_width = math.floor(width - 3*SPACING)/2
    new_params['width'] = new_width
    for check in ('xmin', 'xmax'):
        if check not in new_params.keys():
            logger.error('scale_param {0} is not a key'.format(check))
    if new_params['xmin'] == new_params['xmax']:
        logger.error('scale_param x-range is empty')
    if 'ymin' in new_params.keys() and 'ymax' in new_params.keys() and new_params['ymin'] == new_params['ymax']:
        logger.error('scale_param y-range is empty')
    return new_params


def template_compact(df, params, speaker, origin, key):
    params2 = scale_params(params, 2)
    params3 = scale_params(params, 3)
    # full size
    params_summary = copy.deepcopy(params)
    params_spin = copy.deepcopy(params)
    params_pict = copy.deepcopy(params)
    params_summary['width'] = 600
    params_pict['width'] = 400
    params_spin['width'] -= params_summary['width']+params_pict['width']+2*SPACING+LEGEND
    summary = display_summary(df, params_summary, speaker, origin, key)
    spinorama = display_spinorama(df, params_spin)
    pict = display_pict(speaker, params_pict)
    # side by side
    params2v2 = copy.deepcopy(params2)
    params2v2['width'] -= LEGEND
    onaxis = display_onaxis(df, params2v2)
    inroom = display_inroom(df, params2v2)
    # side by side
    params3['height'] = params2['height']
    ereflex = display_reflection_early(df, params3)
    hreflex = display_reflection_horizontal(df, params3)
    vreflex = display_reflection_vertical(df, params3)
    # side by side
    hspl = display_spl_horizontal(df, params2)  
    vspl = display_spl_vertical(df, params2)
    # min value for contours & friends
    params2['xmin'] = max(100, params2['xmin'])
    params2v2['xmin'] = params2['xmin']
    # horizontal contour / isoband / radar
    hcontour = display_contour_smoothed_horizontal(df, params2)
    hisoband = display_isoband_horizontal(df, params2)
    hradar = display_radar_horizontal(df, params2v2)
    # vertical contour / isoband / radar
    vcontour = display_contour_smoothed_vertical(df, params2)
    visoband = display_isoband_vertical(df, params2)
    vradar = display_radar_vertical(df, params2v2)
    # build the chart
    # print('Status {0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11}'.format(
    #     spinorama is None, onaxis is None, inroom is None, ereflex is None, vreflex is None, hreflex is None,
    #     hspl is None, vspl is None, hcontour is None, vcontour is None, hradar is None, vradar is None))
    chart = alt.vconcat()
    if spinorama is not None:
        title = None
        if key is not None and key != 'default':
            title = '{0} ({1})'.format(speaker, key)
        else:
            title = speaker
        if summary is not None and pict is not None:
            chart &= alt.hconcat(summary.properties(title=speaker),
                                 spinorama.properties(title='CEA2034'),
                                 pict)
        else:
            chart &= alt.hconcat(spinorama.properties(title='CEA2034'))

    if onaxis is not None:
        if inroom is not None:
            chart = alt.vconcat(
                chart,
                alt.hconcat(onaxis.properties(title='On Axis'), inroom.properties(title='In Room prediction'))
                ).resolve_scale(color='independent')
        else:
            chart &= onaxis

    if ereflex is not None and hreflex is not None and vreflex is not None:
        chart = alt.vconcat(
            chart,
            alt.hconcat(ereflex.properties(title='Early Reflections'),
                        hreflex.properties(title='Horizontal Reflections'),
                        vreflex.properties(title='Vertical Reflections'))
            ).resolve_scale(color='independent')

    if hspl is not None and vspl is not None:
        chart &= alt.hconcat(hspl.properties(title='Horizontal SPL'), vspl.properties(title='Vertical SPL'))
    else:
        if hspl is not None:
            chart &= hspl.properties(title='Horizontal SPL')
        elif vspl is not None:
            chart &= vspl.properties(title='Vertical SPL')

#    if hcontour is not None and hradar is not None:
#        chart &= alt.hconcat(hcontour.properties(title='Horizontal Contours'), hradar.properties(title='Horizontal Radar'))

#    if vcontour is not None and vradar is not None:
#        chart &= alt.hconcat(vcontour.properties(title='Vertical Contours'), vradar.properties(title='Vertical Radar'))

    if hisoband is not None and hradar is not None:
        chart &= alt.hconcat(hisoband.properties(title='Horizontal IsoBands'), hradar.properties(title='Horizontal Radar')).resolve_scale(color='independent')

    if visoband is not None and vradar is not None:
        chart &= alt.hconcat(visoband.properties(title='Vertical IsoBands'), vradar.properties(title='Vertical Radar')).resolve_scale(color='independent')

    return chart.configure_title(orient='top', anchor='middle', fontSize=30).configure_text(fontSize=16).configure_view(strokeWidth=0, opacity=0)



def template_panorama(df, params, speaker, origin, key):
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
    hcontour = display_contour_smoothed_horizontal(df, params3)
    hradar = display_radar_horizontal(df, params3)
    # side by side
    vcontour = display_contour_smoothed_vertical(df, params3)
    vspl = display_spl_vertical(df, params3)
    vradar = display_radar_vertical(df, params3)
    # build the chart
    chart = alt.vconcat()
    if spinorama is not None and onaxis is not None and inroom is not None:
        chart &= alt.hconcat(spinorama.properties(title='CEA2034'),
                             onaxis.properties(title='On Axis'),
                             inroom.properties(title='In Room prediction'))
    else:
        if spinorama is not None:
            chart &= spinorama
        if onaxis is not None:
            chart &= onaxis
        if inroom is not None:
            chart &= inroom
    if ereflex is not None and hreflex is not None and vreflex is not None:
        chart &= alt.hconcat(ereflex.properties(title='Early Reflections'),
                             hreflex.properties(title='Horizontal Reflections'),
                             vreflex.properties(title='Vertical Reflections'))
    else:
        logger.info('Panaroma: ereflex={0} hreflex={1} vreflex={2}'.format(
            ereflex is not None, hreflex is not None, vreflex is not None))
    if hspl is not None and hcontour is not None and hradar is not None:
        chart &= alt.hconcat(hcontour.properties(title='Horizontal SPL'),
                             hradar.properties(title='Horizontal SPL'),
                             hspl.properties(title='Horizontal SPL'))
    else:
        logger.info('Panaroma: hspl={0} hcontour={1} hradar={2}'.format(
            hspl is not None, hcontour is not None, hradar is not None))
    if vspl is not None and vcontour is not None and vradar is not None:
        chart &= alt.hconcat(vcontour.properties(title='Vertical SPL'),
                             vradar.properties(title='Vertical SPL'),
                             vspl.properties(title='Vertical SPL'))
    else:
        logger.info('Panaroma: vspl={0} vcontour={1} vradar={2}'.format(
            vspl is not None, vcontour is not None, vradar is not None))
    return chart.configure_legend(
        orient='top'
    ).configure_title(
        orient='top',
        anchor='middle',
        fontSize=18
    )


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
    chart = alt.vconcat()
    for g in (spinorama, onaxis, inroom, ereflex, hreflex, vreflex,
              hspl, vspl, hcontour, hradar, vcontour, vradar):
        if g is not None:
            chart &= g
    return chart.configure_legend(
        orient='top'
    ).configure_title(
        orient='top',
        anchor='middle',
        fontSize=18
    )

def template_sidebyside_eq(df_ref, df_eq, params, speaker, origin, key):
    params2 = scale_params(params, 2)
    logger.debug('params width {0} height {1} xmin {2} xmax {3} ymin {4} ymax {5}'\
                  .format(params2['width'], params2['height'], params2['xmin'], params2['xmax'], params2['ymin'], params2['ymax']))
    # ref
    summary_ref = display_summary(df_ref, params2, speaker, origin, key)
    spinorama_ref = display_spinorama(df_ref, params2)
    onaxis_ref = display_onaxis(df_ref, params2)
    inroom_ref = display_inroom(df_ref, params2)
    ereflex_ref = display_reflection_early(df_ref, params2)
    hreflex_ref = display_reflection_horizontal(df_ref, params2)
    vreflex_ref = display_reflection_vertical(df_ref, params2)
    hspl_ref = display_spl_horizontal(df_ref, params2)  
    vspl_ref = display_spl_vertical(df_ref, params2)
    # eq
    summary_eq = display_summary(df_eq, params2, speaker, origin, key)
    spinorama_eq = display_spinorama(df_eq, params2)
    onaxis_eq = display_onaxis(df_eq, params2)
    inroom_eq = display_inroom(df_eq, params2)
    ereflex_eq = display_reflection_early(df_eq, params2)
    hreflex_eq = display_reflection_horizontal(df_eq, params2)
    vreflex_eq = display_reflection_vertical(df_eq, params2)
    hspl_eq = display_spl_horizontal(df_eq, params2)  
    vspl_eq = display_spl_vertical(df_eq, params2)
    # min value for contours & friends
    params2['xmin'] = max(100, params2['xmin'])
    # ref
    hcontour_ref = display_contour_smoothed_horizontal(df_ref, params2)
    hisoband_ref = display_isoband_horizontal(df_ref, params2)
    hradar_ref = display_radar_horizontal(df_ref, params2)
    vcontour_ref = display_contour_smoothed_vertical(df_ref, params2)
    visoband_ref = display_isoband_vertical(df_ref, params2)
    vradar_ref = display_radar_vertical(df_ref, params2)
    # eq
    hcontour_eq = display_contour_smoothed_horizontal(df_eq, params2)
    hisoband_eq = display_isoband_horizontal(df_eq, params2)
    hradar_eq = display_radar_horizontal(df_eq, params2)
    vcontour_eq = display_contour_smoothed_vertical(df_eq, params2)
    visoband_eq = display_isoband_vertical(df_eq, params2)
    vradar_eq = display_radar_vertical(df_eq, params2)

    chart = alt.vconcat()

    for (title, g_ref, g_eq) in [
            ('summary', summary_ref, summary_eq),
            ('spinorama', spinorama_ref, spinorama_eq),
            ('onaxis', onaxis_ref, onaxis_eq),
            ('inroom', inroom_ref, inroom_eq),
            ('ereflex', ereflex_ref, ereflex_eq),
            ('hreflex', hreflex_ref, hreflex_eq),
            ('vreflex', vreflex_ref, vreflex_eq),
            ('hspl', hspl_ref, hspl_eq),
            ('vspl', vspl_ref, vspl_eq),
            ('hcontour', hcontour_ref, hcontour_eq),
            ('vcontour', vcontour_ref, vcontour_eq),
            ('hisoband', hisoband_ref, hisoband_eq),
            ('visoband', visoband_ref, visoband_eq),
            ('hradar', hradar_ref, hradar_eq),
            ('vradar', vradar_ref, vradar_eq),
        ]:
        logger.debug('concatenating {0} for {1}'.format(title, speaker))
        if g_ref is not None:
            if g_eq is not None:
                chart &= alt.hconcat(g_ref.properties(title=speaker), g_eq.properties(title='with EQ')).resolve_scale(color='independent')
            else:
                chart &= alt.hconcat(g_ref)
        else:
            if g_eq is not None:
                chart &= alt.hconcat(g_eq)

    return chart.configure_title(orient='top', anchor='middle', fontSize=30).configure_text(fontSize=16).configure_view(strokeWidth=0, opacity=0)



