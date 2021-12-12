# -*- coding: utf-8 -*-
import logging
import math
import copy
import altair as alt
import warnings

# from altair_saver import save
from .speaker_display import (
    display_spinorama,
    display_onaxis,
    display_inroom,
    display_reflection_early,
    display_reflection_horizontal,
    display_reflection_vertical,
    display_spl_horizontal,
    display_spl_vertical,
    display_contour_horizontal,
    display_contour_vertical,
    display_radar_horizontal,
    display_radar_vertical,
    display_summary,
    display_pict,
)


logger = logging.getLogger("spinorama")


SPACING = 20
LEGEND = 60


def scale_params(params, factor):
    new_params = copy.deepcopy(params)
    width = params["width"]
    height = params["height"]
    if factor == 3:
        new_width = math.floor(width - 6 * SPACING) / 3
        new_height = math.floor(height - 6 * SPACING) / 3
        new_params["height"] = new_height
    else:
        new_width = math.floor(width - 3 * SPACING) / 2
    new_params["width"] = new_width
    for check in ("xmin", "xmax"):
        if check not in new_params.keys():
            logger.error("scale_param {0} is not a key".format(check))
    if new_params["xmin"] == new_params["xmax"]:
        logger.error("scale_param x-range is empty")
    if (
        "ymin" in new_params.keys()
        and "ymax" in new_params.keys()
        and new_params["ymin"] == new_params["ymax"]
    ):
        logger.error("scale_param y-range is empty")
    return new_params


def template_compact(df, params, speaker, origin, key):
    params2 = scale_params(params, 2)
    params3 = scale_params(params, 3)
    # full size
    params_summary = copy.deepcopy(params)
    params_spin = copy.deepcopy(params)
    params_pict = copy.deepcopy(params)
    params_summary["width"] = 600
    params_pict["width"] = 400
    params_spin["width"] -= (
        params_summary["width"] + params_pict["width"] + 3 * SPACING + LEGEND
    )
    summary = display_summary(df, params_summary, speaker, origin, key)
    spinorama = display_spinorama(df, params_spin)
    pict = display_pict(speaker, params_pict)
    # side by side
    params2v2 = copy.deepcopy(params2)
    params2v2["width"] -= LEGEND
    onaxis = display_onaxis(df, params2v2)
    inroom = display_inroom(df, params2v2)
    # side by side
    params3["height"] = params2["height"]
    ereflex = display_reflection_early(df, params3)
    hreflex = display_reflection_horizontal(df, params3)
    vreflex = display_reflection_vertical(df, params3)
    # side by side
    hspl = display_spl_horizontal(df, params2)
    vspl = display_spl_vertical(df, params2)
    # min value for contours & friends
    params2["xmin"] = max(100, params2["xmin"])
    params2v2["xmin"] = params2["xmin"]

    # remove warning from altair (it works fine)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "Conflicting (scale|property)")

        # build the chart
        # print('Status {0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11}'.format(
        #     spinorama is None, onaxis is None, inroom is None, ereflex is None, vreflex is None, hreflex is None,
        #     hspl is None, vspl is None, hcontour is None, vcontour is None, hradar is None, vradar is None))
        chart = alt.vconcat()
        if spinorama is not None:
            # title = None
            # if key is not None and key != "default":
            #    title = "{0} ({1})".format(speaker, key)
            # else:
            #    title = speaker
            if summary is not None and pict is not None:
                chart = alt.vconcat(
                    chart,
                    alt.hconcat(
                        summary.properties(title=speaker),
                        spinorama.properties(title="CEA2034"),
                        pict,
                    ),
                ).resolve_scale(color="independent")
            else:
                chart &= alt.hconcat(spinorama.properties(title="CEA2034"))

        if onaxis is not None:
            if inroom is not None:
                chart = alt.vconcat(
                    chart,
                    alt.hconcat(
                        onaxis.properties(title="On Axis"),
                        inroom.properties(title="In Room prediction"),
                    ),
                ).resolve_scale(color="independent")
            else:
                chart &= onaxis

        if ereflex is not None and hreflex is not None and vreflex is not None:
            chart = alt.vconcat(
                chart,
                alt.hconcat(
                    ereflex.properties(title="Early Reflections"),
                    hreflex.properties(title="Horizontal Reflections"),
                    vreflex.properties(title="Vertical Reflections"),
                ).resolve_scale(
                    color="shared"
                ),  # generates a warning
            ).resolve_scale(color="independent")

        if hspl is not None and vspl is not None:
            chart &= alt.hconcat(
                hspl.properties(title="Horizontal SPL"),
                vspl.properties(title="Vertical SPL"),
            )
        else:
            if hspl is not None:
                chart &= hspl.properties(title="Horizontal SPL")
            elif vspl is not None:
                chart &= vspl.properties(title="Vertical SPL")

        #    if hcontour is not None and hradar is not None:
        #        chart &= alt.hconcat(hcontour.properties(title='Horizontal Contours'), hradar.properties(title='Horizontal Radar'))

        #    if vcontour is not None and vradar is not None:
        #        chart &= alt.hconcat(vcontour.properties(title='Vertical Contours'), vradar.properties(title='Vertical Radar'))

        # can be usefull for debugging
        # save(summary, "/tmp/summary.png")

        return (
            chart.configure_title(orient="top", anchor="middle", fontSize=30)
            .configure_text(fontSize=16)
            .configure_view(strokeWidth=0, opacity=0)
            # .configure_legend(orient='bottom')
        )
