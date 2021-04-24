#                                                  -*- coding: utf-8 -*-
import os
import logging
import altair as alt
import pandas as pd
import numpy as np


logger = logging.getLogger("spinorama")


def graph_summary(speaker_name, speaker_summary, params):
    #  Title
    #                Score
    #  mean 300-10kHz
    #  -3dB          lfx
    #  -6dB          lfq
    # +/- nDB        nbd_on
    #                nbd_pir
    #                sm_pir
    # --------------------------
    pointsX = np.array(
        [
            0.0,
            0.0,
            0.05,
            0.0,
            0.0,
            0.0,
            0.5,
            0.5,
            0.55,
            0.55,
            0.5,
            0.55,
            0.55,
            0.5,
            0.55,
        ]
    )
    pointsY = (
        np.array(
            [1.9, 1.6, 1.4, 1.2, 1.0, 0.8, 1.9, 1.6, 1.4, 1.2, 1.0, 0.8, 0.6, 0.4, 0.2]
        )
        - 0.6
    )
    logger.debug(
        "sizes X={0} Y={1} summary={2}".format(
            len(pointsX), len(pointsY), len(speaker_summary)
        )
    )
    source = pd.DataFrame({"x": pointsX, "y": pointsY, "summary": speaker_summary})
    return (
        alt.Chart(source)
        .mark_text(align="left", dx=0)
        .encode(
            x=alt.X("x", title="", scale=alt.Scale(domain=[0, 1]), axis=None),
            y=alt.Y("y", title="", axis=None),
            text="summary:N",
        )
        .properties(width=params["width"], height=params["height"])
    )


# import urllib
# import os
def graph_image(speaker_name, params):
    # url = 'https://pierreaubert.github.io/spinorama/pictures/{0}.jpg'.format(urllib.parse.quote(speaker_name))
    # url = "file://{1}/docs/pictures/{0}.jpg".format(urllib.parse.quote(speaker_name), os.getcwd())
    url = None
    pict_path = "./docs/pictures/{0}.jpg".format(speaker_name)
    default_path = "./docs/pictures/speaker-default.jpg"
    if os.path.exists(pict_path):
        url = "file://docs/pictures/{0}.jpg".format(speaker_name)
    else:
        url = "file://docs/pictures/speaker-default.jpg"

    source = pd.DataFrame.from_records([{"x": 0, "y": 0.0, "img": url}])
    return (
        alt.Chart(source)
        .mark_image(
            width=params["width"] - 40,
            height=params["height"] - 40,
        )
        .encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            url="img",
        )
        .properties(
            width=params["width"],
            height=params["height"],
        )
    )
