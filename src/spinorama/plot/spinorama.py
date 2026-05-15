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

"""The combined spinorama figure (CEA2034 + DI on a secondary axis)."""

import bisect
import math

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from spinorama import logger
from spinorama.constant_paths import SLOPE_MIN_FREQ, SLOPE_MAX_FREQ
from spinorama.compute.misc import compute_slope_smoothness
from spinorama.plot.axes import (
    generate_xaxis,
    generate_yaxis_di,
    generate_yaxis_spl,
    plot_valid_freq_ranges,
)
from spinorama.plot.layouts import common_layout
from spinorama.plot.theme import (
    FLAG_FEATURE_ANNOTATION,
    FLAG_FEATURE_CONFIDENCE_ZONES,
    FLAG_FEATURE_TREND_LINES,
    FLAG_FEATURE_VISIBLE,
    UNIFORM_COLORS,
    label_short,
)


def plot_spinorama_traces(
    spin: pd.DataFrame,
    params: dict,
    minmax_slopes: dict[str, tuple[float, float]] | None,
    is_normalized: bool,
    valid_freq_range: tuple[float, float],
) -> tuple[list, list, list, list]:
    layout = params.get("layout", "")
    traces = []
    lines = []
    freq = spin.Freq.to_numpy()
    if len(freq) == 0:
        logger.error("Freq is not in spin")
        return traces, traces, lines, lines
    slope_min_freq = max(SLOPE_MIN_FREQ, freq[0])
    slope_max_freq = min(SLOPE_MAX_FREQ, freq[-1])
    restricted_spin = spin.loc[(spin.Freq >= slope_min_freq) & (spin.Freq <= slope_max_freq)]
    restricted_freq = restricted_spin.Freq.to_numpy()
    first_freq = restricted_freq[0]
    last_freq = restricted_freq[-1]

    for measurement in (
        "On Axis",
        "Listening Window",
        "Early Reflections",
        "Sound Power",
    ):
        if measurement not in spin:
            continue
        trace = go.Scatter(
            x=spin.Freq,
            y=spin[measurement],
            marker_color=UNIFORM_COLORS.get(measurement, "black"),
            name=measurement,
            hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
        )
        first_spl, last_spl, _, _ = compute_slope_smoothness(
            data_frame=spin, measurement=measurement, is_normalized=is_normalized
        )
        if FLAG_FEATURE_TREND_LINES and measurement in (
            "Sound Power",
            "Early Reflections",
            "Listening Window",
        ):
            lines.append(
                go.Scatter(
                    x=[first_freq, last_freq],
                    y=[first_spl, last_spl],
                    line=dict(width=2, dash="dash", color=UNIFORM_COLORS[measurement]),
                    opacity=1,
                    visible=FLAG_FEATURE_VISIBLE,
                    showlegend=False,
                    name="{} slope".format(measurement),
                )
            )
        if (
            FLAG_FEATURE_CONFIDENCE_ZONES
            and minmax_slopes is not None
            and len(minmax_slopes) > 0
            and measurement in minmax_slopes
        ):
            # aligned with VituixCAD
            ex = 1.0
            slope_min, slope_max = minmax_slopes[measurement]
            spl_min = slope_min * math.log2(last_freq / first_freq)
            spl_max = slope_max * math.log2(last_freq / first_freq)
            x = [first_freq, last_freq, last_freq, first_freq, first_freq]
            y = np.add([-ex, -ex + spl_min, ex + spl_max, +ex, -ex], first_spl).tolist()
            lines.append(
                go.Scatter(
                    x=x,
                    y=y,
                    fill="toself",
                    opacity=0.25,
                    fillcolor=UNIFORM_COLORS[measurement],
                    mode="text",
                    visible=FLAG_FEATURE_VISIBLE,
                    name="recommended {} zone".format(label_short.get(measurement)),
                    showlegend=False,
                )
            )

        trace.name = measurement
        if layout != "compact":
            trace.legendgroup = "measurements"
            trace.legendgrouptitle = {"text": "Measurements"}
        traces.append(trace)

    traces_di = []
    lines_di = []
    for measurement in ("Early Reflections DI", "Sound Power DI"):
        if measurement not in spin:
            continue
        trace = go.Scatter(
            x=spin.Freq,
            y=spin[measurement],
            marker_color=UNIFORM_COLORS.get(measurement, "black"),
            name=measurement,
            hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
        )
        first_spl, last_spl, _, _ = compute_slope_smoothness(
            data_frame=spin, measurement=measurement, is_normalized=is_normalized
        )
        if FLAG_FEATURE_TREND_LINES:
            lines_di.append(
                go.Scatter(
                    x=[first_freq, last_freq],
                    y=[first_spl, last_spl],
                    line=dict(width=2, dash="dash", color=UNIFORM_COLORS[measurement]),
                    opacity=1,
                    showlegend=False,
                    visible=FLAG_FEATURE_VISIBLE,
                    name="{} slope".format(measurement),
                )
            )
        if (
            FLAG_FEATURE_CONFIDENCE_ZONES
            and minmax_slopes is not None
            and len(minmax_slopes) > 0
            and measurement in minmax_slopes
        ):
            # aligned with VituixCAD
            ex = 1.0
            slope_min, slope_max = minmax_slopes[measurement]
            spl_min = slope_min * math.log2(last_freq / first_freq)
            spl_max = slope_max * math.log2(last_freq / first_freq)
            x = [first_freq, last_freq, last_freq, first_freq, first_freq]
            y = np.add([-ex, -ex + spl_min, ex + spl_max, +ex, -ex], first_spl).tolist()
            lines_di.append(
                go.Scatter(
                    x=x,
                    y=y,
                    fill="toself",
                    opacity=0.25,
                    name="recommended {} zone".format(label_short.get(measurement)),
                    fillcolor=UNIFORM_COLORS[measurement],
                    mode="text",
                    showlegend=False,
                    visible=FLAG_FEATURE_VISIBLE,
                )
            )
        trace.name = measurement
        if layout != "compact":
            trace.legendgroup = "directivity"
            trace.legendgrouptitle = {"text": "Directivity"}
        traces_di.append(trace)
    return traces, traces_di, lines, lines_di


def plot_spinorama_annotation(
    fig,
    spin: dict[str, pd.DataFrame | float],
    is_normalized: bool,
    valid_freq_range: tuple[float, float],
):
    if not FLAG_FEATURE_ANNOTATION:
        return fig

    _graph_param = (
        (2000, "On Axis", "y", -20, "right", "bottom"),
        (16000, "Listening Window", "y", -20, "right", "bottom"),
        (10000, "Early Reflections", "y", 20, "right", "top"),
        (10000, "Sound Power", "y", 20, "right", "top"),
        (10000, "Early Reflections DI", "y2", 20, "right", "top"),
        (10000, "Sound Power DI", "y2", -20, "right", "bottom"),
    )

    for freq_initial, measurement, yref, ay_initial, xanchor, yanchor in _graph_param:
        ay = ay_initial
        freq = freq_initial
        if measurement not in spin:
            continue
        _, _, slope, sm = compute_slope_smoothness(spin, measurement, is_normalized=is_normalized)
        closest_freq = bisect.bisect_left(spin.Freq.to_numpy(), freq)
        curve = spin[measurement].to_numpy()
        closest_freq = min(closest_freq, len(curve) - 1)
        spl = curve[closest_freq]
        if measurement == "On Axis":
            res_spin = spin.loc[(spin.Freq >= 1000) & (spin.Freq < 5000)]
            on = res_spin["On Axis"].to_numpy()
            idx = on.argmax()
            spl = on[idx]
            freq = res_spin.Freq.to_numpy()[idx]
        elif measurement == "Listening Window":
            res_spin = spin.loc[(spin.Freq >= 8000) & (spin.Freq < 16000)]
            lw = res_spin["Listening Window"].to_numpy()
            idx = lw.argmax()
            spl = lw[idx]
            freq = res_spin.Freq.to_numpy()[idx]
            if "On Axis" in res_spin:
                spl_on = res_spin["On Axis"].to_numpy()[idx]
                ay -= int((spl_on - spl) * 5)
        fig.add_annotation(
            x=math.log10(freq),
            y=spl,
            text="{:4.2f} db/oct sm {:3.2f}".format(slope, sm),
            font=dict(
                size=10,
                color=UNIFORM_COLORS.get(measurement, "black"),
            ),
            bordercolor=UNIFORM_COLORS.get(measurement, "black"),
            showarrow=True,
            arrowhead=2,
            arrowcolor=UNIFORM_COLORS.get(measurement, "black"),
            xanchor=xanchor,
            yanchor=yanchor,
            yref=yref,
            ay=ay,
            visible=FLAG_FEATURE_VISIBLE,
        )
    return fig


def plot_spinorama(
    spin,
    params,
    minmax_slopes,
    is_normalized,
    valid_freq_range: tuple[float, float],
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    t_max = 0
    traces, traces_di, lines, lines_di = plot_spinorama_traces(
        spin, params, minmax_slopes, is_normalized, valid_freq_range
    )

    if len(traces) == 0:
        logger.error("Error in plotting spinorama traces")
        return None

    for t in traces:
        t_max = max(t_max, np.max(t.y[np.where(t.x < 20000)]))
        fig.add_trace(t, secondary_y=False)

    t_max = 5 + int(t_max / 5) * 5
    t_min = t_max - 50

    shapes = plot_valid_freq_ranges(fig, valid_freq_range, (t_min, t_max))
    for shape in shapes:
        fig.add_trace(shape, secondary_y=False)

    di_max = 0
    for t in traces_di:
        di_max = max(di_max, np.max(t.y[np.where(t.x < 20000)]))
        fig.add_trace(t, secondary_y=True)

    di_max = 35 + int(di_max / 5) * 5
    di_min = di_max - 50

    fig.add_traces(lines)
    for t in lines_di:
        fig.add_trace(t, secondary_y=True)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(t_min, t_max, 5))
    fig.update_yaxes(generate_yaxis_di(di_min, di_max, 5), secondary_y=True)

    fig.update_layout(common_layout(params))

    if minmax_slopes is not None:
        fig = plot_spinorama_annotation(fig, spin, is_normalized, valid_freq_range)

    return fig
