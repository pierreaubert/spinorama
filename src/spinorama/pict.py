# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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

import os
import pathlib

from wand.image import Image as Wim

from spinorama import logger


def write_multiformat(chart, filename, force):
    """Write a png file and then convert and save to jpg and webp"""
    if not pathlib.Path(filename).is_file() or force:
        chart.write_image(filename)
    if os.path.getsize(filename) == 0:
        logger.warning("Saving %s failed!", filename)
        return
    logger.info("Saving %s", filename)

    with Wim(filename=filename) as pict:
        filename = filename.replace("_large", "")
        webp = "{}.webp".format(filename[:-4])
        if not pathlib.Path(webp).is_file() or force:
            pict.convert("webp").save(filename=webp)
        pict.compression_quality = 75
        jpg = "{}.jpg".format(filename[:-4])
        if not pathlib.Path(jpg).is_file() or force:
            pict.convert("jpg").save(filename=jpg)
