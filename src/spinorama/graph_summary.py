# -*- coding: utf-8 -*-
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
            # first col
            0.0,
            0.0,
            0.05,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            # second col
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
            [
                # first col
                1.9,
                1.6,
                1.4,
                1.2,
                1.0,
                0.8,
                0.6,
                0.4,
                # second col
                1.9,
                1.6,
                1.4,
                1.2,
                1.0,
                0.8,
                0.6,
                0.4,
                0.2,
            ]
        )
        - 0.6
    )
    logger.debug(
        "sizes X={0} Y={1} summary={2}".format(len(pointsX), len(pointsY), len(speaker_summary))
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
