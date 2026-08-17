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

"""Per-curve SPL plots: line graphs, regression overlays, on-axis, group delay."""

import math

import numpy as np
from scipy import stats

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from spinorama.constant_paths import (
    MIDRANGE_MIN_FREQ,
    MIDRANGE_MAX_FREQ,
    SLOPE_MIN_FREQ,
    SLOPE_MAX_FREQ,
)
from spinorama.compute.misc import compute_slope_smoothness
from spinorama.plot.axes import (
    generate_xaxis,
    generate_yaxis_gd,
    generate_yaxis_phases,
    generate_yaxis_spl,
    plot_valid_freq_ranges,
)
from spinorama.plot.layouts import common_layout
from spinorama.plot.theme import (
    FLAG_FEATURE_CONFIDENCE_ZONES,
    FLAG_FEATURE_VISIBLE,
    FONT_H3,
    UNIFORM_COLORS,
    label_short,
    legend_rank,
)


def _parse_angle(measurement: str) -> int | None:
    """Parse angle from measurement string like '10°', '-30°', 'On Axis'."""
    if measurement == "On Axis":
        return 0
    if measurement.endswith("°"):
        try:
            return int(measurement[:-1])
        except ValueError:
            pass
    return None


def plot_graph_traces(df, measurement, params, slope, intercept, line_title, valid_freq_range):
    layout = params.get("layout", "")
    traces = []

    freq = df.Freq.to_numpy()
    freq_box = np.concatenate([freq, freq[::-1]])
    line = [slope * math.log10(f) + intercept for f in freq]
    line_box30 = np.concatenate([np.add(line, 3.0), np.add(line, -3.0)[::-1]])
    line_box15 = np.concatenate([np.add(line, 1.5), np.add(line, -1.5)[::-1]])

    # some speakers start very high
    restricted_spin = df.loc[(df.Freq >= MIDRANGE_MIN_FREQ) & (df.Freq <= MIDRANGE_MAX_FREQ)]
    restricted_line = [slope * math.log10(f) + intercept for f in restricted_spin.Freq]

    # add 3 dBs zone
    traces.append(
        go.Scatter(
            x=freq_box,
            y=line_box30,
            fill="toself",
            fillcolor="#E2F705",
            line_color="#E2F705",
            opacity=0.25,
            showlegend=True,
            name="Band ±3dB",
        )
    )
    # add 1.5 dBs zone
    traces.append(
        go.Scatter(
            x=freq_box,
            y=line_box15,
            fill="toself",
            fillcolor="#E2F705",
            line_color="#E2F705",
            showlegend=True,
            name="Band ±1.5dB",
        )
    )

    # add line
    showlegend = True
    title = line_title
    if line_title is None:
        showlegend = False
        title = "Linear interpolation"
    traces.append(
        go.Scatter(
            x=freq,
            y=line,
            line=dict(width=2, color="black", dash="dot"),
            opacity=1,
            showlegend=showlegend,
            name=title,
        )
    )

    # add -3/+3 lines
    offset = 3
    offset_freq = 0
    offset_spl = offset
    traces.append(
        go.Scatter(
            x=restricted_spin.Freq + offset_freq,
            y=np.array(restricted_line) + offset_spl,
            line=dict(width=2, color="black", dash="dash"),
            opacity=1,
            showlegend=False,
            name="Midrange Band +3dB",
        )
    )
    traces.append(
        go.Scatter(
            x=restricted_spin.Freq + offset_freq,
            y=np.array(restricted_line) - offset_spl,
            line=dict(width=2, color="black", dash="dash"),
            opacity=1,
            showlegend=False,
            name="Midrange Band -3dB",
        )
    )

    trace = go.Scatter(
        x=df.Freq,
        y=df[measurement],
        marker_color=UNIFORM_COLORS.get(measurement, "black"),
        opacity=1,
        hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
    )
    trace.name = measurement
    if layout != "compact":
        trace.legendgroup = "measurements"
        trace.legendgrouptitle = {"text": "Measurements"}
    traces.append(trace)

    return traces


def plot_graph_flat_traces(df, measurement, params, valid_freq_range):
    restricted_df = df.loc[(df.Freq >= MIDRANGE_MIN_FREQ) & (df.Freq <= MIDRANGE_MAX_FREQ)]
    slope = 0
    intercept = np.mean(restricted_df[measurement]) if not restricted_df[measurement].empty else 0.0
    return plot_graph_traces(df, measurement, params, slope, intercept, None, valid_freq_range)


def plot_graph_regression_traces(df, measurement, params, valid_freq_range):
    restricted_df = df.loc[(df.Freq >= SLOPE_MIN_FREQ) & (df.Freq <= SLOPE_MAX_FREQ)]
    slope, intercept, _, _, _ = stats.linregress(
        x=np.log10(restricted_df["Freq"]), y=restricted_df[measurement]
    )
    return plot_graph_traces(
        df, measurement, params, slope, intercept, "Midrange ±3dB", valid_freq_range
    )


def plot_graph(
    df,
    params,
    valid_freq_range: tuple[float, float],
):
    layout = params.get("layout", "")
    fig = go.Figure()
    trend_curve = "0°"
    if "On Axis" in df:
        trend_curve = "On Axis"

    for measurement in df:
        if measurement != "Freq":
            trace = go.Scatter(
                x=df.Freq,
                y=df[measurement],
                hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
            )
            trace.name = measurement
            if layout != "compact":
                trace.name = measurement
                trace.legendgroup = "measurements"
                trace.legendgrouptitle = {"text": "Measurements"}
            if measurement in UNIFORM_COLORS:
                trace.marker = {"color": UNIFORM_COLORS[measurement]}
            if measurement in legend_rank:
                trace.legendrank = legend_rank[measurement]
            fig.add_trace(trace)

    if trend_curve in df:
        restricted_df = df.loc[(df.Freq >= SLOPE_MIN_FREQ) & (df.Freq <= SLOPE_MAX_FREQ)]
        if len(restricted_df) > 1:
            slope, intercept, _, _, _ = stats.linregress(
                np.log10(restricted_df["Freq"]), restricted_df[trend_curve]
            )
            trend_traces = plot_graph_traces(
                df, trend_curve, params, slope, intercept, "Trend line", valid_freq_range
            )
            # Skip the last trace (the data curve itself, already added in the for loop)
            for t in trend_traces[:-1]:
                fig.add_trace(t)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))
    fig.update_layout(common_layout(params))
    fig.add_traces(plot_valid_freq_ranges(fig, valid_freq_range, (params["ymin"], params["ymax"])))
    return fig


def plot_graph_spl(
    df,
    params,
    valid_freq_range: tuple[float, float],
    include_all_angles: bool = False,
):
    layout = params.get("layout", "")
    fig = go.Figure()
    trend_curve = "On Axis"
    trend_traces = []
    if trend_curve in df:
        restricted_df = df.loc[(df.Freq >= SLOPE_MIN_FREQ) & (df.Freq <= SLOPE_MAX_FREQ)]
        if len(restricted_df) > 1:
            slope, intercept, _, _, _ = stats.linregress(
                np.log10(restricted_df["Freq"]), restricted_df[trend_curve]
            )
            trend_traces = plot_graph_traces(
                df, trend_curve, params, slope, intercept, "Trend line", valid_freq_range
            )

    for measurement in df:
        if measurement != "Freq":
            visible = None
            angle = _parse_angle(measurement)
            if measurement in (
                "On Axis",
                "10°",
                "20°",
                "30°",
                "40°",
                "50°",
                "60°",
            ):
                visible = True
            elif measurement in ("-10°", "-20°", "-30°", "-40°", "-50°", "-60°"):
                visible = "legendonly"
            elif include_all_angles and angle is not None:
                visible = "legendonly"
            else:
                continue
            # Add trend/band traces instead of the regular trace, plus the data curve itself
            if measurement == trend_curve and trend_traces:
                for t in trend_traces[:-1]:
                    fig.add_trace(t)
                # Also add the On Axis data curve
                onaxis_trace = go.Scatter(
                    x=df.Freq,
                    y=df[trend_curve],
                    marker_color=UNIFORM_COLORS.get(trend_curve, "black"),
                    opacity=1,
                    hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
                    visible=True,
                    showlegend=True,
                    legendrank=legend_rank.get(trend_curve, 0),
                )
                if layout == "compact":
                    onaxis_trace.name = label_short.get(trend_curve, trend_curve)
                else:
                    onaxis_trace.name = trend_curve
                    onaxis_trace.legendgroup = "measurements"
                    onaxis_trace.legendgrouptitle = {"text": "Measurements"}
                fig.add_trace(onaxis_trace)
                continue
            else:
                trace = go.Scatter(
                    x=df.Freq,
                    y=df[measurement],
                    hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
                    visible=visible,
                    showlegend=True,
                )
                if layout == "compact":
                    trace.name = label_short.get(measurement, measurement)
                else:
                    trace.name = measurement
                    trace.legendgroup = "measurements"
                    trace.legendgrouptitle = {"text": "Measurements"}
                if measurement in UNIFORM_COLORS:
                    trace.marker = {"color": UNIFORM_COLORS[measurement]}
                if measurement in legend_rank:
                    trace.legendrank = legend_rank[measurement]
                fig.add_trace(trace)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))
    fig.update_layout(common_layout(params))
    fig.add_traces(plot_valid_freq_ranges(fig, valid_freq_range, (params["ymin"], params["ymax"])))
    return fig


def plot_graph_flat(df, measurement, params, valid_freq_range):
    fig = go.Figure()
    traces = plot_graph_flat_traces(df, measurement, params, valid_freq_range)
    for t in traces:
        fig.add_trace(t)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))

    fig.update_layout(common_layout(params))
    fig.update_traces(mode="lines")
    fig.add_traces(plot_valid_freq_ranges(fig, valid_freq_range, (params["ymin"], params["ymax"])))

    return fig


def plot_graph_regression(
    curve,
    measurement,
    spin_for_zone,
    params,
    minmax_slopes,
    is_normalized,
    valid_freq_range,
):
    """Render a curve with regression bands and an optional confidence-zone overlay.

    ``curve`` is the wide-form frame for ``measurement``. ``spin_for_zone`` is
    the matching CEA2034 spin used to anchor the recommended zone (may be
    ``None`` to suppress that layer).
    """
    fig = go.Figure()

    if curve is not None:
        fig.add_traces(plot_graph_regression_traces(curve, measurement, params, valid_freq_range))

    if (
        FLAG_FEATURE_CONFIDENCE_ZONES
        and ("Estimated In-Room Response" in measurement or "Sound Power" in measurement)
        and spin_for_zone is not None
        and curve is not None
        and minmax_slopes is not None
    ):
        spin = spin_for_zone
        freq = spin.Freq.to_numpy()
        slope_min_freq = max(SLOPE_MIN_FREQ, freq[0])
        slope_max_freq = min(SLOPE_MAX_FREQ, freq[-1])
        restricted_df = spin.loc[(spin.Freq >= slope_min_freq) & (spin.Freq <= slope_max_freq)]
        restricted_freq = restricted_df.Freq.to_numpy()
        first_freq = restricted_freq[0]
        last_freq = restricted_freq[-1]
        first_spl, _, _, _ = compute_slope_smoothness(
            data_frame=curve, measurement=measurement, is_normalized=is_normalized
        )
        slope_min, slope_max = minmax_slopes[measurement]
        spl_min = slope_min * math.log2(last_freq / first_freq)
        spl_max = slope_max * math.log2(last_freq / first_freq)
        x = [first_freq, last_freq, last_freq, first_freq, first_freq]
        y = np.add([-1, -1 + spl_min, 1 + spl_max, +1, -1], first_spl).tolist()
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill="toself",
                opacity=0.5,
                name="recommended {} zone".format(label_short.get(measurement, "???")),
                fillcolor="#FF5C00",  # neon orange
                mode="text",
                visible=FLAG_FEATURE_VISIBLE,
            )
        )

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))

    fig.update_layout(common_layout(params))
    fig.update_traces(mode="lines")

    fig.add_traces(plot_valid_freq_ranges(fig, valid_freq_range, (params["ymin"], params["ymax"])))

    return fig


def plot_graph_onaxis(onaxis_df, h_spl, params, valid_freq_range):
    """Plot the on-axis frequency response with optional phase overlay from H SPL."""
    fig_onaxis = make_subplots(specs=[[{"secondary_y": True}]])

    traces = plot_graph_regression_traces(onaxis_df, "On Axis", params, valid_freq_range)
    for trace in traces:
        fig_onaxis.add_trace(trace, secondary_y=False)

    fig_onaxis.update_xaxes(generate_xaxis())
    fig_onaxis.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))

    fig_onaxis.update_layout(common_layout(params))
    fig_onaxis.update_traces(mode="lines")

    if h_spl is not None and "Phase On Axis" in h_spl:
        freq = h_spl.Freq
        phase = h_spl["Phase On Axis"]
        phase_min = np.min(phase)
        phase_max = np.max(phase)
        if phase_max - phase_min <= 2 * math.pi + 1:
            phase = np.rad2deg(phase)
        phase = np.array(phase) - 180 - phase_min
        fig_onaxis.add_trace(
            go.Scatter(
                x=freq,
                y=phase.tolist(),
                name="Phase (deg)",
            ),
            secondary_y=True,
        )
        fig_onaxis.update_yaxes(generate_yaxis_phases(), secondary_y=True)
        fig_onaxis.update_layout(margin_r=50)
        # Add "Phase (deg)" as an annotation centered on the visible range [-180, 180].
        # In paper coordinates, y=0.25 is the midpoint of [-180, 180] within [-180, 540].
        fig_onaxis.add_annotation(
            text="Phase (deg)",
            xref="paper",
            yref="paper",
            x=1.05,
            y=0.25,
            showarrow=False,
            textangle=-90,
            font=FONT_H3,
        )

    fig_onaxis.add_traces(
        plot_valid_freq_ranges(fig_onaxis, valid_freq_range, (params["ymin"], params["ymax"]))
    )

    return fig_onaxis


def plot_graph_group_delay(h_spl, params, valid_freq_range):
    """Plot group delay (ms) derived from the horizontal-SPL on-axis phase."""
    fig_group_delay = go.Figure()

    if h_spl is None or "Phase On Axis" not in h_spl:
        return None

    spl_h = h_spl

    freq = spl_h.Freq
    phase = spl_h["Phase On Axis"]
    unphase = np.unwrap(np.deg2rad(phase))
    group_delay = -1000 * np.gradient(unphase, freq)
    fig_group_delay.add_trace(
        go.Scatter(
            x=freq,
            y=group_delay,
            name="Group Delay (ms)",
        )
    )
    gd_max = int(np.max(group_delay)) // 10 * 10
    fig_group_delay.update_xaxes(generate_xaxis())
    fig_group_delay.update_yaxes(generate_yaxis_gd(-5, gd_max, 5))
    fig_group_delay.update_layout(common_layout(params))
    fig_group_delay.update_traces(mode="lines")
    fig_group_delay.add_traces(
        plot_valid_freq_ranges(fig_group_delay, valid_freq_range, (params["ymin"], params["ymax"]))
    )
    return fig_group_delay
