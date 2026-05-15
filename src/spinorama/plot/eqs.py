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

"""Side-by-side comparison of multiple PEQ frequency responses."""

import bisect
import math
import warnings

import numpy as np

import plotly.graph_objects as go

from spinorama.filters.peq import peq_spl
from spinorama.plot.theme import FONT_H3


def plot_eqs(freq, peqs, names):
    peqs_spl = [peq_spl(freq, peq) for peq in peqs]
    if len(peqs) > 1:
        freq_min = bisect.bisect_right(freq, 80)
        freq_max = bisect.bisect_left(freq, 3000)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            if freq_min < freq_max:
                peqs_restriced = [np.array(spl)[freq_min:freq_max] for spl in peqs_spl]
                peqs_avg = [np.mean(v) if len(v) > 0 else 0.0 for v in peqs_restriced]
                peqs_spl = [
                    np.array(spl) - (peqs_avg[i] - peqs_avg[0]) for i, spl in enumerate(peqs_spl)
                ]
    traces = None
    if names is None:
        traces = [go.Scatter(x=freq, y=spl) for spl in peqs_spl]
    else:
        traces = [
            go.Scatter(
                x=freq,
                y=spl,
                name=name,
                hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
            )
            for spl, name in zip(peqs_spl, names, strict=False)
        ]
    fig = go.Figure(data=traces)
    fig.update_xaxes(
        dict(
            title_text="Frequency (Hz)",
            type="log",
            range=[math.log10(20), math.log10(20000)],
            autorange=False,
            showline=True,
            dtick="D1",
        ),
    )
    spl_min = -5
    if len(peqs) > 0:
        spl_min = np.min([np.min(peq_spl(freq, peq)) for peq in peqs])
        spl_min = max(-10, -5 * round(-spl_min / 5)) if spl_min < -5 else -5
    spl_max = 5
    if len(peqs) > 0:
        spl_max = np.max([np.max(peq_spl(freq, peq)) for peq in peqs])
        spl_max = min(15, 5 * round(spl_max / 5) + 5) if spl_max > 5 else 5
    spl_range = spl_max - spl_min
    if spl_range <= 6:
        y_dtick = 1
    elif spl_range <= 12:
        y_dtick = 2
    else:
        y_dtick = 5
    fig.update_yaxes(
        dict(
            title_text="SPL (dB)",
            range=[spl_min, spl_max],
            autorange=False,
            showline=True,
            dtick=y_dtick,
        ),
    )
    fig.update_layout(
        title="EQs",
        width=600,
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            xanchor="center",
            y=1.1,
            x=0.5,
            title=None,
            font=FONT_H3,
        ),
    )
    return fig
