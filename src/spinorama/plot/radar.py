# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

"""Polar radar plots: SPL across a band of frequencies for each direction."""

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from spinorama import logger
from spinorama.misc import sort_angles
from spinorama.plot.layouts import radar_layout
from spinorama.plot.theme import (
    FONT_H5,
    FONT_H6,
    RADAR_COLORS,
)


def find_nearest_freq(dfu: pd.DataFrame, hz: float, tolerance: float = 0.05) -> int | None:
    """return the index of the nearest freq in dfu, return None if not found"""
    ihz = None
    for i in dfu.index:
        f = dfu.loc[i]
        if abs(f - hz) < hz * tolerance:
            ihz = i
            break
    if ihz:
        logger.debug("nearest: %.1f hz at loc %d", hz, ihz)
    return ihz


def plot_radar(spl, params, valid_plot_range):
    layout = params.get("layout", "")

    anglestep = 10
    if "5°" in spl and "25°" in spl:
        anglestep = 5

    anglelist = list(range(-180, 180, anglestep))

    def projection(anglelist, grid_z, hz):
        dbs_r = [db for _, db in zip(anglelist, grid_z, strict=False)]
        dbs_theta = [a for a, _ in zip(anglelist, grid_z, strict=False)]
        dbs_r.append(dbs_r[0])
        dbs_theta.append(dbs_theta[0])
        return dbs_r, dbs_theta, [hz for _ in range(0, len(dbs_r))]

    def label(i):
        return "{:d} Hz".format(i)

    def plot_radar_freq(anglelist, freqlist, df):
        dfu = sort_angles(df)
        db_mean = dfu.loc[(dfu.Freq > 900) & (dfu.Freq < 1100)]["On Axis"].mean()
        freq = dfu.Freq
        dfu = dfu.drop("Freq", axis=1)
        db_x = []
        db_y = []
        hz_z = []
        for hz in freqlist:
            ihz = find_nearest_freq(freq, hz)
            if ihz is None:
                continue
            p_x, p_y, p_z = projection(anglelist, dfu.loc[ihz][dfu.columns != "Freq"], hz)
            db_x.append(p_x)
            db_y.append(p_y)
            hz_z.append(p_z)

        db_x = [v2 for v1 in db_x for v2 in v1]
        db_y = [v2 for v1 in db_y for v2 in v1]
        hz_z = [label(i2) for i1 in hz_z for i2 in i1]

        return db_mean, pd.DataFrame({"R": db_x, "Theta": db_y, "Freq": hz_z})

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[
            [{"type": "polar"}, {"type": "polar"}],
            [{"type": "polar"}, {"type": "polar"}],
        ],
        horizontal_spacing=0.15,
        vertical_spacing=0.05,
    )

    radialaxis = dict(
        range=[-45, 5],
        dtick=5,
        tickfont=FONT_H5,
    )
    angularaxis = dict(
        dtick=10,
        tickvals=list(range(0, 360, 10)),
        ticktext=[
            f"{x}°" if abs(x) < 60 or not x % 30 else " "
            for x in (list(range(0, 180, 10)) + list(range(-180, 0, 10)))
        ],
        tickfont=FONT_H6,
    )

    def update_pict(anglelist, freqlist, row, col, spl):
        _, dbs_df = plot_radar_freq(anglelist, freqlist, spl)

        for freq in np.unique(dbs_df["Freq"].to_list()):
            mslice = dbs_df.loc[dbs_df.Freq == freq]
            trace = go.Scatterpolar(
                r=mslice.R,
                theta=mslice.Theta,
                dtheta=30,
                name=freq,
                marker_color=RADAR_COLORS.get(freq, "black"),
                legendrank=int(freq[:-3]),
            )
            if layout != "compact":
                trace.legendgroup = "Measurements"
                trace.legendgrouptitle = dict(
                    text="Frequencies",
                )
            fig.add_trace(trace, row=row, col=col)
            fig.update_polars(radialaxis=radialaxis, angularaxis=angularaxis, row=row, col=col)

    update_pict(anglelist, [100, 125, 160, 200], 1, 1, spl)
    update_pict(anglelist, [1600, 2000, 2500, 3150], 1, 2, spl)
    update_pict(anglelist, [250, 315, 400, 500], 2, 1, spl)
    update_pict(anglelist, [4000, 5000, 6300, 8000], 2, 2, spl)

    fig.update_layout(radar_layout(params))
    return fig
