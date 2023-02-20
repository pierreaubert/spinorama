# -*- coding: utf-8 -*-
import os
import logging
import pathlib
from wand.image import Image as wim

logger = logging.getLogger("spinorama")


def write_multiformat(chart, filename, force):
    """Write a png file and then convert and save to jpg and webp"""
    if not pathlib.Path(filename).is_file() or force:
        chart.write_image(filename)
    if os.path.getsize(filename) == 0:
        logger.warning("Saving %s failed!", filename)
        return
    logger.info("Saving %s", filename)

    with wim(filename=filename) as pict:
        filename = filename.replace("_large", "")
        webp = "{}.webp".format(filename[:-4])
        if not pathlib.Path(webp).is_file() or force:
            pict.convert("webp").save(filename=webp)
        pict.compression_quality = 75
        jpg = "{}.jpg".format(filename[:-4])
        if not pathlib.Path(jpg).is_file() or force:
            pict.convert("jpg").save(filename=jpg)
