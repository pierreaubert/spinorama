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
    return alt.vconcat(spinorama,
                       onaxis | inroom,
                       ereflex | hreflex | vreflex,
                       hspl | vspl,
                       hradar | vradar,
                       hcontour | vcontour)


def template_panorama(df, speaker, width=900, height=500):
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
    return alt.vconcat(spinorama | onaxis | inroom,
                       ereflex | hreflex | vreflex,
                       hcontour | hradar | hspl,
                       vcontour | vradar | vspl)


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
