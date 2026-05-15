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

"""Contour (2D) and 3D surface plots of SPL across angle/frequency."""

import itertools
import math
from typing import TypeVar

import numpy as np
import pandas as pd

import plotly.graph_objects as go

from spinorama.compute.misc import compute_contour
from spinorama.plot.axes import (
    generate_colorbar,
    generate_xaxis,
    generate_yaxis_angles,
)
from spinorama.plot.layouts import contour_layout
from spinorama.plot.theme import (
    CONTOUR_COLORSCALE,
    FONT_H3,
    FONT_H4,
)

T = TypeVar("T")


def flatten(the_list: list[list[T | None]]) -> list[T | None]:
    return list(itertools.chain.from_iterable(the_list))


def plot_contour(spl, params, valid_freq_range):
    df_spl = spl.copy().filter(regex=r"^(?:(?!Phase).)*$", axis=1)
    min_freq = params.get("contour_min_freq", 100)

    contour_start = -30
    contour_end = 3

    fig = go.Figure()

    af, am, az = compute_contour(df_spl.loc[df_spl.Freq >= min_freq])
    az = np.clip(az, contour_start, contour_end)
    fig.add_trace(
        go.Contour(
            x=af[0],
            y=am.T[0],
            z=az,
            zmin=contour_start,
            zmax=contour_end,
            contours=dict(
                coloring="fill",
                start=contour_start + 0,
                end=contour_end - 0,
                size=3,
                showlines=True,
            ),
            colorbar=generate_colorbar(),
            autocolorscale=False,
            colorscale=CONTOUR_COLORSCALE,
            hovertemplate="Freq: %{x:.0f}Hz<br>Angle: %{y:.0f}<br>SPL: %{z:.1f}dB<br>",
            zorder=0,
        )
    )

    def add_lines(x, y):
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                opacity=0.5,
                marker_color="white",
                line_width=1,
                showlegend=False,
                zorder=1,
            )
        )

    def compute_horizontal_lines(
        x_min: float, x_max: float, y_data: range
    ) -> tuple[list[float | None], list[int | None]]:
        x = [x_min, x_max, None] * len(y_data)
        y = flatten([[a, a, None] for a in y_data])
        return x, y

    def compute_vertical_lines(
        y_min: int, y_max: int, x_data: list[int]
    ) -> tuple[list[int | None], list[float | None]]:
        x = flatten([[a, a, None] for a in x_data])
        y = [y_min, y_max, None] * len(x_data)
        return x, y

    hx, hy = compute_horizontal_lines(min_freq, 20000, range(-150, 180, 30))
    vrange = (
        [100 * i for i in range(2, 9)]
        + [1000 * i for i in range(1, 10)]
        + [10000 + 1000 * i for i in range(1, 9)]
    )
    vx, vy = compute_vertical_lines(-180, 180, vrange)

    add_lines(hx, hy)
    add_lines(vx, vy)

    fig.update_xaxes(generate_xaxis(min_freq))
    fig.update_yaxes(generate_yaxis_angles())
    fig.update_yaxes(
        zeroline=True,
        zerolinecolor="#000000",
        zerolinewidth=3,
    )
    fig.update_layout(contour_layout(params))
    return fig


def plot_contour_3d(spl_phase, params, valid_freq_range):
    params.get("layout", "")
    min_freq = max(20, params.get("contour_min_freq", 100))

    contour_start = -30
    contour_end = 3

    z_min = -45
    z_max = 5

    colorbar = generate_colorbar()

    angle_list_3d = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
    angle_text_3d = [f"{a}°" for a in angle_list_3d]
    spl_list_3d = [0, -5, -10, -15, -20, -25, -30, -35, -40, -45]
    spl_text_3d = [f"{s}" if s > -45 else "" for s in spl_list_3d]

    def a2v(angle: str) -> int:
        if angle == "Freq":
            return -1000
        elif angle == "On Axis":
            return 0
        iangle = int(angle[:-1])
        return iangle

    def transform(spl: pd.DataFrame, db_max: float, clip_min: float, clip_max: float):
        if "-180°" not in spl and "180°" in spl:
            spl["-180°"] = spl["180°"]
        df_spl = spl.reindex(columns=sorted(spl.columns, key=a2v)) - db_max
        # freq, angle, spl, color
        selector = (df_spl["Freq"] >= min_freq) & (df_spl["Freq"] <= 20000)
        freq = df_spl.Freq.loc[selector].to_numpy()
        angle = [a2v(i) for i in df_spl.loc[:, df_spl.columns != "Freq"].columns]
        spl = df_spl.loc[selector, df_spl.columns != "Freq"].clip(z_min, z_max).T.to_numpy()
        color = np.clip(np.multiply(np.floor_divide(spl, 3), 3), clip_min, clip_max)
        return freq, angle, spl, color

    spl = spl_phase.filter(regex=r"^(?:(?!Phase).)*$", axis=1)
    db_max = spl["On Axis"].max()

    freqs, angles, spls, surface_colors = transform(spl, db_max, contour_start, contour_end)

    fig = go.Figure()

    trace = go.Surface(
        x=freqs,
        y=angles,
        z=spls,
        showscale=True,
        autocolorscale=False,
        colorscale=CONTOUR_COLORSCALE,
        surfacecolor=surface_colors,
        colorbar=colorbar,
        cmin=contour_start,
        cmax=contour_end,
        hovertemplate="Freq: %{x:.0f}Hz<br>Angle:  %{y}°<br> SPL: %{z:.1f}dB<br>",
    )

    fig.add_trace(trace)

    fig.update_layout(
        autosize=True,
        width=800,
        height=800,
        scene=dict(
            xaxis=dict(
                title="Freq. (Hz)",
                type="log",
                range=[math.log10(min_freq), math.log10(20000)],
                showline=True,
                dtick="D1",
                tickfont=FONT_H4,
                title_font=FONT_H3,
            ),
            yaxis=dict(
                range=[-180, 180],
                showline=True,
                tickvals=angle_list_3d,
                ticktext=angle_text_3d,
                title="Angle",
                tickfont=FONT_H4,
                title_font=FONT_H3,
            ),
            zaxis=dict(
                range=[z_min, z_max],
                title="SPL",
                showline=True,
                tickvals=spl_list_3d,
                ticktext=spl_text_3d,
                tickfont=FONT_H4,
                title_font=FONT_H3,
            ),
            aspectratio=dict(
                x=1.414,
                y=1,
                z=1,
            ),
            camera_eye=dict(
                x=1.25,
                y=-2.0,
                z=1.5,
            ),
        ),
    )
    fig.update_traces(contours_z=dict(show=True, project_z=True))

    return fig
