import math
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


def template_compact(df, speaker, width=900, height=500):
    width2 = math.floor(width * 45 / 100)
    height2 = math.floor(height * 45 / 100)
    width3 = math.floor(width * 30 / 100)
    height3 = math.floor(height * 30 / 100)
    # full size
    spinorama = display_spinorama(df, speaker, width, height)
    # side by side
    onaxis = display_onaxis(df, speaker, width2, height2)
    inroom = display_inroom(df, speaker, width2, height2)
    # side by side
    ereflex = display_reflection_early(df, speaker, width3, height3)
    hreflex = display_reflection_horizontal(df, speaker, width3, height3)
    vreflex = display_reflection_vertical(df, speaker, width3, height3)
    # side by side
    hspl = display_spl_horizontal(df, speaker, width2, height2)
    vspl = display_spl_vertical(df, speaker, width2, height2)
    # side by side
    hcontour = display_contour_horizontal(df, speaker, width2, height2)
    vcontour = display_contour_vertical(df, speaker, width2, height2)
    # side by side
    hradar = display_radar_horizontal(df, speaker, width2, height2)
    vradar = display_radar_vertical(df, speaker, width2, height2)
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
    if hcontour is not None and vcontour is not None:
        chart &= alt.hconcat(hcontour, vcontour)
    if hradar is not None and vradar is not None:
        chart &= alt.hconcat(hradar, vradar)
    return chart


def template_panorama(df, speaker, width=900, height=500):
    width3 = math.floor(width * 30 / 100)
    height3 = math.floor(height * 30 / 100)
    # side by side
    spinorama = display_spinorama(df, speaker, width3, height3)
    onaxis = display_onaxis(df, speaker, width3, height3)
    inroom = display_inroom(df, speaker, width3, height3)
    # side by side
    ereflex = display_reflection_early(df, speaker, width3, height3)
    hreflex = display_reflection_horizontal(df, speaker, width3, height3)
    vreflex = display_reflection_vertical(df, speaker, width3, height3)
    # side by side
    hspl = display_spl_horizontal(df, speaker, width3, height3)
    hcontour = display_contour_horizontal(df, speaker, width3, height3)
    hradar = display_radar_horizontal(df, speaker, width3, height3)
    # side by side
    vcontour = display_contour_vertical(df, speaker, width3, height3)
    vspl = display_spl_vertical(df, speaker, width3, height3)
    vradar = display_radar_vertical(df, speaker, width3, height3)
    # build the chart
    chart = alt.vconcat()
    if spinorama is not None and onaxis is not None and inroom is not None \
       and ereflex is not None and hreflex is not None and vreflex is not None \
       and hspl is not None and hcontour is not None and hradar is not None \
       and vspl is not None and vcontour is not None and vradar is not None:
        #chart &= alt.hconcat(spinorama, onaxis, inroom)
        #chart &= alt.hconcat(ereflex, hreflex, vreflex)
        #chart &= alt.hconcat(hcontour, hradar, hspl)
        #chart &= alt.hconcat(vcontour, vradar, vspl)
        chart = alt.vconcat(
            alt.hconcat(spinorama, onaxis, inroom),
            alt.hconcat(ereflex, hreflex, vreflex),
            alt.hconcat(hcontour, hradar, hspl),
            alt.hconcat(vcontour, vradar, vspl))
    return chart


def template_vertical(df, speaker, width=900, height=500):
    spinorama = display_spinorama(df, speaker, width, height)
    onaxis = display_onaxis(df, speaker, width, height)
    inroom = display_inroom(df, speaker, width, height)
    ereflex = display_reflection_early(df, speaker, width, height)
    hreflex = display_reflection_horizontal(df, speaker, width, height)
    vreflex = display_reflection_vertical(df, speaker, width, height)
    hspl = display_spl_horizontal(df, speaker, width, height)
    vspl = display_spl_vertical(df, speaker, width, height)
    hcontour = display_contour_horizontal(df, speaker, width, height)
    hradar = display_radar_horizontal(df, speaker, width, height)
    vcontour = display_contour_vertical(df, speaker, width, height)
    vradar = display_radar_vertical(df, speaker, width, height)
    return alt.vconcat(spinorama,
                       onaxis,
                       inroom,
                       ereflex,
                       hreflex,
                       vreflex,
                       hspl,
                       vspl,
                       hcontour,
                       hradar,
                       vcontour,
                       vradar)
