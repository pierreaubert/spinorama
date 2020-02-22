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


def template_compact(df, width=900, height=500):
    width2 = math.floor(width * 45 / 100)
    height2 = math.floor(height * 45 / 100)
    width3 = math.floor(width * 30 / 100)
    height3 = math.floor(height * 30 / 100)
    # full size
    spinorama = display_spinorama(df, width, height)
    # side by side
    onaxis = display_onaxis(df, width2, height2)
    inroom = display_inroom(df, width2, height2)
    # side by side
    ereflex = display_reflection_early(df, width3, height3)
    hreflex = display_reflection_horizontal(df, width3, height3)
    vreflex = display_reflection_vertical(df, width3, height3)
    # side by side
    hspl = display_spl_horizontal(df, width2, height2)
    vspl = display_spl_vertical(df, width2, height2)
    # side by side
    hcontour = display_contour_horizontal(df, width2, height2)
    hradar = display_radar_horizontal(df, width2, height2)
    # side by side
    vcontour = display_contour_vertical(df, width2, height2)
    vradar = display_radar_vertical(df, width2, height2)
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


def template_panorama(df, width=900, height=500):
    width3 = math.floor(width * 30 / 100)
    height3 = math.floor(height * 30 / 100)
    # side by side
    spinorama = display_spinorama(df, width3, height3)
    onaxis = display_onaxis(df, width3, height3)
    inroom = display_inroom(df, width3, height3)
    # side by side
    ereflex = display_reflection_early(df, width3, height3)
    hreflex = display_reflection_horizontal(df, width3, height3)
    vreflex = display_reflection_vertical(df, width3, height3)
    # side by side
    hspl = display_spl_horizontal(df, width3, height3)
    hcontour = display_contour_horizontal(df, width3, height3)
    hradar = display_radar_horizontal(df, width3, height3)
    # side by side
    vcontour = display_contour_vertical(df, width3, height3)
    vspl = display_spl_vertical(df, width3, height3)
    vradar = display_radar_vertical(df, width3, height3)
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


def template_vertical(df, width=900, height=500):
    spinorama = display_spinorama(df, width, height)
    onaxis = display_onaxis(df, width, height)
    inroom = display_inroom(df, width, height)
    ereflex = display_reflection_early(df, width, height)
    hreflex = display_reflection_horizontal(df, width, height)
    vreflex = display_reflection_vertical(df, width, height)
    hspl = display_spl_horizontal(df, width, height)
    vspl = display_spl_vertical(df, width, height)
    hcontour = display_contour_horizontal(df, width, height)
    hradar = display_radar_horizontal(df, width, height)
    vcontour = display_contour_vertical(df, width, height)
    vradar = display_radar_vertical(df, width, height)
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


def template_freq_sidebyside(s1, s2, name, width=450, height=450):
    df1 = display_graph_freq(s1[name], width, height)
    df2 = display_graph_freq(s2[name], width, height)
    if df1 is None and df2 is None:
        return None
    if df1 is None:
        return df2
    if df2 is None:
        return df1
    return alt.hconcat(df1, df2)
