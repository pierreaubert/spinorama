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

import altair as alt
import pandas as pd
import numpy as np

from spinorama import logger


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
