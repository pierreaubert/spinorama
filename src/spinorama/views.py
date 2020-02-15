from .display import \
    display_spinorama, \
    display_onaxis, \
    display_inroom, \
    display_reflection_early, \
    display_reflection_horizontal, \
    display_reflection_vertical, \
    display_contour_horizontal, \
    display_contour_vertical, \
    display_radar_horizontal, \
    display_radar_vertical


def template_compact(df, speaker, width=900, heigth=500):
    width2 = math.floor(width * 45 / 100)
    heigth2 = math.floor(heigth * 45 / 100)
    width3 = math.floor(width * 30 / 100)
    heigth3 = math.floor(heigth * 30 / 100)
    # full size
    spinorama = display_spinorama(df, speaker, width, heigth)
    # side by side
    onaxis = display_onaxis(df, speaker, width2, heigth2)
    inroom = display_inroom(df, speaker, width2, heigth2)
    # side by side
    ereflex = display_reflection_early(df, speaker, width3, heigth3)
    hreflex = display_reflection_horizontal(df, speaker, width3, heigth3)
    vreflex = display_reflection_vertical(df, speaker, width3, heigth3)
    # side by side
    hspl = display_spl_horizontal(df, speaker, width2, heigth2)
    vspl = display_spl_vertical(df, speaker, width2, heigth2)
    # side by side
    hcontour = display_contour_horizontal(df, speaker, width2, heigth2)
    vcontour = display_contour_vertical(df, speaker, width2, heigth2)
    return alt.vconcat(spinorama,
                       onaxis | inroom,
                       ereflex | hreflex | vreflex,
                       hspl | vspl,
                       hcontour | vcontour)


def template_vertical(df, speaker, width=900, heigth=500):
    spinorama = display_spinorama(df, speaker, width, heigth)
    onaxis = display_onaxis(df, speaker, width, heigth)
    inroom = display_inroom(df, speaker, width, heigth)
    ereflex = display_reflection_early(df, speaker, width, heigth)
    hreflex = display_reflection_horizontal(df, speaker, width, heigth)
    vreflex = display_reflection_vertical(df, speaker, width, heigth)
    hspl = display_spl_horizontal(df, speaker, width, heigth)
    vspl = display_spl_vertical(df, speaker, width, heigth)
    hcontour = display_contour_horizontal(df, speaker, width, heigth)
    hradar = display_radar_horizontal(df, speaker, width, heigth)
    vcontour = display_contour_vertical(df, speaker, width, heigth)
    vradar = display_radar_vertical(df, speaker, width, heigth)
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
