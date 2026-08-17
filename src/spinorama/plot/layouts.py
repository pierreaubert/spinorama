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

"""Plotly layout dicts for the three figure families (line / contour / radar)."""

from spinorama.plot.theme import FONT_H1, FONT_H3, FONT_H5, FONT_H6


def common_layout(params):
    orientation = "v"
    if params.get("layout", "") == "compact":
        orientation = "h"

    return dict(
        width=params["width"],
        height=params["height"],
        title=dict(
            x=0.5,
            y=0.99,
            xanchor="center",
            yanchor="top",
            font=FONT_H1,
        ),
        legend=dict(
            x=0.5,
            y=1.075,
            xanchor="center",
            yanchor="top",
            orientation=orientation,
            font=FONT_H3,
        ),
        margin={
            "t": 80,
            "b": 10,
            "l": 10,
            "r": 10,
        },
    )


def contour_layout(params):
    orientation = "v"
    if params.get("layout", "") == "compact":
        orientation = "h"

    return dict(
        width=params["width"],
        height=params["height"],
        legend=dict(
            x=0.5,
            y=0.95,
            xanchor="center",
            orientation=orientation,
            font=FONT_H3,
        ),
        title=dict(
            x=0.5,
            y=0.99,
            xanchor="center",
            yanchor="top",
            font=FONT_H1,
        ),
        margin={
            "t": 40,
            "b": 10,
            "l": 10,
            "r": 10,
        },
        font=FONT_H6,
        polar=dict(
            bargap=0,
            hole=0.05,
        ),
    )


def radar_layout(params):
    orientation = "v"
    if params.get("layout", "") == "compact":
        orientation = "h"

    return dict(
        width=params["width"],
        height=params["height"],
        legend=dict(
            x=0.5,
            y=1.1,
            xanchor="center",
            orientation=orientation,
            title_font=FONT_H5,
            font=FONT_H6,
        ),
        title=dict(
            x=0.5,
            y=0.98,
            xanchor="center",
            yanchor="top",
        ),
        margin=dict(
            t=120,
            b=0,
            l=50,
            r=50,
        ),
    )
