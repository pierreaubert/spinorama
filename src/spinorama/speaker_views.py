# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import math
import copy

# from altair_saver import save
from spinorama import logger

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
            logger.error("scale_param %s is not a key", check)
    if new_params["xmin"] == new_params["xmax"]:
        logger.error("scale_param x-range is empty")
    if (
        "ymin" in new_params.keys()
        and "ymax" in new_params.keys()
        and new_params["ymin"] == new_params["ymax"]
    ):
        logger.error("scale_param y-range is empty")
    return new_params
