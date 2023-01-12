# -*- coding: utf-8 -*-
import logging
import math
import copy
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
    if "ymin" in new_params.keys() and "ymax" in new_params.keys() and new_params["ymin"] == new_params["ymax"]:
        logger.error("scale_param y-range is empty")
    return new_params
