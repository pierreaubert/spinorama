#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2022 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import copy
import math

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from spinorama.load_misc import graph_melt
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import peq_build, peq_preamp_gain
from spinorama.compute_misc import savitzky_golay, compute_statistics
from spinorama.plot import (
    colors,
    plot_spinorama_traces,
    plot_graph_regression_traces,
    generate_xaxis,
    generate_yaxis_spl,
    generate_yaxis_di,
)


def short_curve_name(name):
    if name == "Listening Window":
        return "LW"
    elif name == "Estimated In-Room Response":
        return "PIR"
    elif name == "On Axis":
        return "ON"
    return name


def graph_eq(freq, peq, domain, title):
    df = pd.DataFrame({"Freq": freq})
    for i, (pos, eq) in enumerate(peq):
        df["{} {}".format(eq.type2str(True), i)] = peq_build(freq, [(pos, eq)])

    traces = []
    for i, key in enumerate(df.keys()):
        if key != "Freq":
            traces.append(
                go.Scatter(
                    x=df.Freq,
                    y=df[key],
                    name=key,
                    legendgroup="PEQ",
                    legendgrouptitle_text="EQ",
                    marker_color=colors[i % len(colors)],
                )
            )
    return traces


def graph_eq_compare(freq, auto_peq, auto_target_interp, domain, speaker_name, speaker_origin, target, optim_config):
    # manual_peq = [
    #    (1.0, Biquad(3, 400, 48000, 4.32, -2)),
    #    (1.0, Biquad(3, 1600, 48000, 4.32, -1)),
    #    (1.0, Biquad(3, 2000, 48000, 4.32, 1.5)),
    #    (1.0, Biquad(3, 2500, 48000, 4.32, 3)),
    #    (1.0, Biquad(3, 3150, 48000, 4.32, 3)),
    # ]
    curve_names = []
    for name in optim_config["curve_names"]:
        curve_names.append(short_curve_name(name))

    target_name = "error {}".format(curve_names[0], 0)
    df = pd.DataFrame(
        {
            "Freq": freq,
            "autoEQ": peq_build(freq, auto_peq),
            #        "manualEQ": peq_build(freq, manual_peq),
            target_name: target,
        }
    )
    for i, ati in enumerate(auto_target_interp):
        if i < len(curve_names):
            df["ideal {}".format(curve_names[i])] = ati
        else:
            df["ideal {}".format(i)] = ati

    if optim_config.get("smooth_measurements"):
        window_size = optim_config.get("smooth_window_size")
        order = optim_config.get("smooth_order")
        smoothed = savitzky_golay(target, window_size, order)
        df["smoothed {}".format(curve_names[0])] = smoothed

    traces = []
    for i, key in enumerate(df.keys()):
        if key != "Freq":
            traces.append(
                go.Scatter(
                    x=df.Freq,
                    y=df[key],
                    name=key,
                    legendgroup="target",
                    legendgrouptitle_text="EQ v.s. Target",
                    marker_color=colors[i + 1],
                )
            )
    return traces


def graph_results(
    speaker_name,
    speaker_origin,
    freq,
    auto_peq,
    auto_target,
    auto_target_interp,
    spin,
    spin_auto,
    pir,
    pir_auto,
    optim_config,
    score,
    auto_score,
):
    # ~ default
    g_params = {
        "xmin": 20,
        "xmax": 20000,
        "ymin": -40,
        "ymax": 10,
        "width": 800,
        "height": 400,
    }

    # what's the min over freq?
    reg_min = optim_config["freq_reg_min"]
    reg_max = optim_config["freq_reg_max"]
    domain = [reg_min, reg_max]
    # build a graph for each peq
    g_auto_eq = graph_eq(freq, auto_peq, domain, "{} auto".format(speaker_name))

    # compare the 2 eqs
    target = -(auto_target[0] - auto_target_interp[0])
    # with open("debug_target.txt", "w") as fd:
    #    for f, a in zip(freq, target):
    #        fd.write("{} {}\n".format(f, a))
    #    fd.close()

    # print('target {} {}'.format(np.min(target), np.max(target)))
    g_eq_full = graph_eq_compare(freq, auto_peq, auto_target_interp, domain, speaker_name, speaker_origin, target, optim_config)

    # compare the 2 corrected curves
    df_optim = pd.DataFrame({"Freq": freq})
    df_optim["Auto"] = auto_target[0] - auto_target_interp[0] + peq_build(freq, auto_peq)
    # show the 2 spinoramas
    unmelted_spin = spin.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max).reset_index()

    g_spin_noeq, g_spin_noeq_di = plot_spinorama_traces(unmelted_spin, g_params)
    g_spin_auto, g_spin_auto_di, unmelted_spin_auto = None, None, None
    if spin_auto is not None:
        unmelted_spin_auto = spin_auto.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max).reset_index()
        g_spin_auto, g_spin_auto_di = plot_spinorama_traces(unmelted_spin_auto, g_params)

    # show the 3 optimised curves
    g_curves = {}
    for which_curve in ("On Axis", "Listening Window", "Estimated In-Room Response"):
        data = unmelted_spin
        data_auto = unmelted_spin_auto
        if which_curve == "Estimated In-Room Response":
            data = pir.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max).reset_index()
            data_auto = pir_auto.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max).reset_index()

        # print(data.keys())
        g_curve_noeq = plot_graph_regression_traces(data, which_curve, g_params)

        g_curve_auto = None
        if data_auto is not None:
            g_curve_auto = plot_graph_regression_traces(data_auto, which_curve, g_params)

        # gather stats
        short_curve = short_curve_name(which_curve)
        noeq_slope, noeq_hist, noeq_max = compute_statistics(data, which_curve, 250, 10000, 250, 10000)
        auto_slope, auto_hist, auto_max = compute_statistics(data_auto, which_curve, 250, 10000, 250, 10000)

        # generate title
        noeq_title = f"{short_curve} slope {noeq_slope:+0.2f}dB/Octave error max={noeq_max:.1f}dB"
        auto_title = f"{short_curve} with EQ slope {auto_slope:+0.2f}dB/Octave error max={auto_max:.1f}dB"

        # generate histogram of deviation
        noeq_counts, noeq_bins = noeq_hist
        auto_counts, auto_bins = noeq_hist
        bins = sorted([s for s in set(noeq_bins).union(auto_bins)])
        bins = ["{:0.1f}-{:0.1f}".format(noeq_bins[i], noeq_bins[i + 1]) for i in range(0, len(noeq_bins) - 1)]
        bins.append("{:0.1f}+".format(noeq_bins[-1]))
        auto_counts, _ = auto_hist
        hist_plot = [
            go.Bar(
                x=bins,
                y=noeq_counts,
                marker_color=colors[0],
                legendgroup="Errors",
                legendgrouptitle_text="Errors",
                name="noEQ",
            ),
            go.Bar(
                x=bins,
                y=auto_counts,
                marker_color=colors[1],
                legendgroup="Errors",
                legendgrouptitle_text="Errors",
                name="autoEQ",
            ),
        ]

        # recompute over midrange only (300Hz--5kHz)
        noeq_slope, noeq_hist, noeq_max = compute_statistics(data, which_curve, 250, 10000, 300, 5000)
        auto_slope, auto_hist, auto_max = compute_statistics(data_auto, which_curve, 250, 10000, 300, 5000)
        noeq_counts, noeq_bins = noeq_hist
        auto_counts, auto_bins = auto_hist
        bins = sorted([s for s in set(noeq_bins).union(auto_bins)])
        bins = ["{:0.1f}-{:0.1f}".format(noeq_bins[i], noeq_bins[i + 1]) for i in range(0, len(noeq_bins) - 1)]
        bins.append("{:0.1f}+".format(noeq_bins[-1]))
        hist_plot_midrange = [
            go.Bar(
                x=bins,
                y=noeq_counts,
                marker_color=colors[0],
                legendgroup="Errors",
                legendgrouptitle_text="Errors",
                name="noEQ",
            ),
            go.Bar(
                x=bins,
                y=auto_counts,
                marker_color=colors[1],
                legendgroup="Errors",
                legendgrouptitle_text="Errors",
                name="autoEQ",
            ),
        ]

        g_curves[which_curve] = {
            "noeq": g_curve_noeq,
            "auto": g_curve_auto,
            "noeq_title": noeq_title,
            "auto_title": auto_title,
            "hist": hist_plot,
            "hist_midrange": hist_plot_midrange,
        }

    spin_title = "Spin"
    if score is not None and isinstance(score, dict):
        spin_title = "Spin (score={:0.1f} lfx={:.0f}Hz sm_pir={:0.2f})".format(
            score.get("pref_score", -100),
            score.get("lfx_hz", -1),
            score.get("sm_pred_in_room", 0),
        )

    auto_spin_title = "Spin with EQ"
    if auto_score is not None and isinstance(auto_score, dict):
        auto_spin_title = "Spin w/autoEQ (score={:0.1f} lfx={:.0f}Hz sm_pir={:0.2f})".format(
            auto_score.get("pref_score", -100),
            auto_score.get("lfx_hz", -1),
            auto_score.get("sm_pred_in_room", 0),
        )

    fig = make_subplots(
        rows=6,
        cols=2,
        subplot_titles=(
            "PEQ details (N={} Gain={:0.1f})".format(len(auto_peq), peq_preamp_gain(auto_peq)),
            "PEQ v.s. Target",
            spin_title,
            auto_spin_title,
            g_curves["On Axis"]["noeq_title"],
            g_curves["On Axis"]["auto_title"],
            g_curves["Listening Window"]["noeq_title"],
            g_curves["Listening Window"]["auto_title"],
            g_curves["Estimated In-Room Response"]["noeq_title"],
            g_curves["Estimated In-Room Response"]["auto_title"],
            "Distribution of errors of {}".format(short_curve_name(optim_config["curve_names"][0])),
            "Distribution of errors of {} (300Hz-5kHz)".format(short_curve_name(optim_config["curve_names"][0])),
        ),
        row_heights=[0.15, 0.25, 0.15, 0.15, 0.15, 0.15],
        horizontal_spacing=0.075,
        vertical_spacing=0.075,
        specs=[
            [{}, {}],
            [{"secondary_y": True}, {"secondary_y": True}],
            [{}, {}],
            [{}, {}],
            [{}, {}],
            [{}, {}],
        ],
    )

    # add EQ and EQ v.s. Target
    auto_eq_max = -1
    auto_eq_min = 1
    for t in g_auto_eq:
        auto_eq_min = min(auto_eq_min, np.min(t.y))
        auto_eq_max = max(auto_eq_max, np.max(t.y))
        fig.add_trace(t, row=1, col=1)

    for t in g_eq_full:
        auto_eq_min = min(auto_eq_min, np.min(t.y))
        auto_eq_max = max(auto_eq_max, np.max(t.y))
        fig.add_trace(t, row=1, col=2)
    auto_eq_max = int(auto_eq_max) + 1
    auto_eq_min = int(auto_eq_min) - 2
    # auto_eq_max = min(auto_eq_max, 5)

    fig.update_xaxes(generate_xaxis(), row=1)
    fig.update_yaxes(generate_yaxis_spl(auto_eq_min, auto_eq_max, 1), row=1)

    # add 2 spins
    for t in g_spin_noeq:
        fig.add_trace(t, row=2, col=1, secondary_y=False)

    for t in g_spin_noeq_di:
        fig.add_trace(t, row=2, col=1, secondary_y=True)

    for t in g_spin_auto:
        t["showlegend"] = False
        fig.add_trace(t, row=2, col=2, secondary_y=False)

    for t in g_spin_auto_di:
        t["showlegend"] = False
        fig.add_trace(t, row=2, col=2, secondary_y=True)

    fig.update_xaxes(generate_xaxis(), row=2)
    fig.update_yaxes(generate_yaxis_spl(), row=2)
    fig.update_yaxes(generate_yaxis_di(), row=2, secondary_y=True)

    # add ON, LW and PIR
    on_min = -10
    on_max = 5
    for t in g_curves["On Axis"]["noeq"]:
        fig.add_trace(t, row=3, col=1)
        on_min = min(on_min, np.min(t.y))
        on_max = max(on_max, np.max(t.y))

    for t in g_curves["On Axis"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=3, col=2)
        on_min = min(on_min, np.min(t.y))
        on_max = max(on_max, np.max(t.y))

    fig.update_xaxes(generate_xaxis(), row=3)

    if on_min < -5:
        on_min = max(-40, -5 * round(-on_min / 5))
    else:
        on_min = -5
    if on_max > 5:
        on_max = min(20, 5 * (round(on_max / 5) + 1))
    else:
        on_max = 5
    on_min = max(-5, on_min)
    fig.update_yaxes(generate_yaxis_spl(on_min, on_max, 1), row=4)

    lw_min = -10
    lw_max = 5
    for t in g_curves["Listening Window"]["noeq"]:
        fig.add_trace(t, row=4, col=1)
        lw_min = min(lw_min, np.min(t.y))
        lw_max = max(lw_max, np.max(t.y))

    for t in g_curves["Listening Window"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=4, col=2)
        lw_min = min(lw_min, np.min(t.y))
        lw_max = max(lw_max, np.max(t.y))

    fig.update_xaxes(generate_xaxis(), row=4)

    if lw_min < -5:
        lw_min = max(-40, -5 * round(-lw_min / 5))
    else:
        lw_min = -5
    if lw_max > 5:
        lw_max = min(20, 5 * (round(lw_max / 5) + 1))
    else:
        lw_max = 5
    lw_min = max(-10, lw_min)
    fig.update_yaxes(generate_yaxis_spl(lw_min, lw_max, 1), row=3)

    pir_min = -10
    pir_max = 5
    for t in g_curves["Estimated In-Room Response"]["noeq"]:
        t["showlegend"] = False
        fig.add_trace(t, row=5, col=1)
        pir_min = min(pir_min, np.min(t.y))
        pir_max = max(pir_max, np.max(t.y))

    for t in g_curves["Estimated In-Room Response"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=5, col=2)
        pir_min = min(pir_min, np.min(t.y))
        pir_max = max(pir_max, np.max(t.y))

    if pir_min < -5:
        pir_min = max(-40, -5 * round(-pir_min / 5))
    else:
        pir_min = -5
    if pir_max > 5:
        pir_max = min(20, 5 * (round(pir_max / 5) + 1))
    else:
        pir_max = 5
    pir_min = max(-10, pir_min)

    fig.update_xaxes(generate_xaxis(), row=5)
    fig.update_yaxes(generate_yaxis_spl(pir_min, pir_max, 1), row=4)

    # add error distribution
    for t in g_curves["Listening Window"]["hist"]:
        fig.add_trace(t, row=6, col=1)
    fig.update_xaxes(title="Error (dB)", row=6, col=1)
    fig.update_yaxes(title="Count", row=6, col=1)
    for t in g_curves["Listening Window"]["hist_midrange"]:
        fig.add_trace(t, row=6, col=2)
    fig.update_xaxes(title="Error (dB)", row=6, col=2)
    fig.update_yaxes(title="Count", row=6, col=2)

    # add tonal balance

    # almost done
    fig.update_layout(
        width=1400,
        # height=1400*29.7/21, # a4 is a bit squeezed
        height=2000,
        legend=dict(orientation="v"),
        title="{} from {}. Config: curves={} target_min_freq={:.0f}Hz".format(
            speaker_name,
            speaker_origin,
            ", ".join(optim_config["curve_names"]),
            optim_config["target_min_freq"],
        ),
    )

    # add all graphs and print it
    return [
        ("eq", fig),
    ]
