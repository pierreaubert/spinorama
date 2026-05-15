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

"""Plotly axis dict generators and the valid-frequency shaded region helper."""

import math

import plotly.graph_objects as go

from spinorama.plot.theme import FONT_H3, FONT_H4, FONT_H5


def generate_xaxis(freq_min=20, freq_max=20000):
    return dict(
        title=dict(
            text="Frequency (Hz)",
            font=FONT_H3,
        ),
        type="log",
        range=[math.log10(freq_min), math.log10(freq_max)],
        autorange=False,
        showline=True,
        dtick="D1",
        tickfont=FONT_H3,
        ticks="inside",
    )


def generate_yaxis_spl(range_min=-40, range_max=10, range_step=1):
    spl_range = range_max - range_min
    if spl_range <= 12:
        label_interval = 2
    elif spl_range <= 30:
        label_interval = 5
    else:
        label_interval = 10
    return dict(
        title=dict(
            text="SPL (dB)",
            font=FONT_H3,
        ),
        range=[range_min, range_max],
        autorange=False,
        dtick=range_step,
        tickvals=list(range(range_min, range_max + range_step, range_step)),
        ticktext=[
            "{}".format(i) if not i % label_interval else " "
            for i in range(range_min, range_max + range_step, range_step)
        ],
        tickfont=FONT_H3,
        ticks="inside",
        showline=True,
    )


def generate_yaxis_gd(range_min=-2, range_max=10, range_step=2):
    return dict(
        title=dict(
            text="Group Delay (ms)",
            font=FONT_H3,
        ),
        range=[range_min, range_max],
        dtick=range_step,
        tickvals=list(range(range_min, range_max + range_step, range_step)),
        ticktext=[
            "{}".format(i) if not i % 5 else " "
            for i in range(range_min, range_max + range_step, range_step)
        ],
        tickfont=FONT_H3,
        ticks="inside",
        showline=True,
    )


def generate_yaxis_di(range_min=-5, range_max=45, range_step=5):
    tickvals = list(range(range_min, range_max, range_step))
    ticktext = [
        f"{di}" if pos < 5 else "" for pos, di in enumerate(range(range_min, range_max, range_step))
    ]
    return dict(
        title=dict(
            text="DI (dB)                                                    &nbsp;",
            font=FONT_H3,
        ),
        range=[range_min, range_max],
        dtick=range_step,
        tickvals=tickvals,
        ticktext=ticktext,
        tickfont=FONT_H3,
        ticks="inside",
        showline=True,
    )


def generate_yaxis_angles(angle_min=-180, angle_max=180, angle_step=30):
    return dict(
        title=dict(
            text="Angle (deg)",
            font=FONT_H3,
        ),
        range=[angle_min, angle_max],
        dtick=angle_step,
        tickvals=list(range(angle_min, angle_max + angle_step, angle_step)),
        ticktext=[""]
        + ["{}°".format(v) for v in range(angle_min + angle_step, angle_max, angle_step)]
        + [""],
        tickfont=FONT_H3,
        ticks="inside",
        showline=True,
    )


def generate_yaxis_phases(phase_min=-180, phase_max=180, phase_step=30):
    # Extend range to 540 so phase data can wrap beyond 180 without clipping.
    # Ticks and labels are only shown in the visible range [-180, 180].
    extended_max = 540
    tickvals = list(range(phase_min, phase_max + phase_step, phase_step))
    ticktext = (
        [""]
        + ["{}°".format(v) for v in range(phase_min + phase_step, phase_max, phase_step)]
        + [""]
    )
    # Title is removed here and added as an annotation in the On Axis plot
    # so it can be centered on the visible portion [-180, 180] instead of
    # the full extended range [-180, 540].
    return dict(
        title=dict(
            text="",
            font=FONT_H3,
        ),
        range=[phase_min, extended_max],
        dtick=phase_step,
        tickvals=tickvals,
        ticktext=ticktext,
        tickfont=FONT_H3,
        ticks="inside",
        showline=True,
    )


def generate_colorbar():
    return dict(
        dtick=3,
        len=0.5,
        lenmode="fraction",
        thickness=15,
        thicknessmode="pixels",
        tickfont=FONT_H5,
        title=dict(
            text="dB (SPL)",
            font=FONT_H4,
        ),
    )


def plot_valid_freq_ranges(fig, freq_range, spl_range=(-40, 10)):
    """Shade frequency ranges outside the speaker's valid measurement window."""
    traces = []
    min_freq, max_freq = freq_range
    min_spl, max_spl = spl_range
    # for some reasons (possibly https://github.com/plotly/plotly.py/issues/2580)
    #   add_vrect is not working
    #   add_shape is working partially for some graphs and not others
    if min_freq > 30.0:
        traces.append(
            go.Scatter(
                x=[20, min_freq, min_freq, 20],
                y=[min_spl, min_spl, max_spl, max_spl],
                mode="none",
                fill="toself",
                name="N/A",
                showlegend=True,
                fillcolor="LightGreen",
                opacity=0.3,
                zorder=-1,
                visible=True,
            ),
        )
    if max_freq < 19500:
        traces.append(
            go.Scatter(
                x=[max_freq, 20000, 20000, max_freq],
                y=[min_spl, min_spl, max_spl, max_spl],
                mode="none",
                fill="toself",
                name="N/A",
                showlegend=False,
                fillcolor="LightGreen",
                opacity=0.3,
                zorder=-1,
            ),
        )
    return traces
