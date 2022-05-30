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
from spinorama.filter_peq import peq_build  # peq_print
from spinorama.plot import (
    colors,
    plot_spinorama_traces,
    plot_graph_regression_traces,
    generate_xaxis,
    generate_yaxis_spl,
    generate_yaxis_di,
)


def graph_eq(freq, peq, domain, title):
    df = pd.DataFrame({"Freq": freq})
    for i, (pos, eq) in enumerate(peq):
        df["EQ {}".format(i)] = peq_build(freq, [(pos, eq)])

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


def graph_eq_compare(freq, auto_peq, auto_target_interp, domain, speaker_name, speaker_origin, target):
    df = pd.DataFrame(
        {
            "Freq": freq,
            "autoEQ": peq_build(freq, auto_peq),
            "target": target-np.mean(target),
        }
    )
    for i, ati in enumerate(auto_target_interp):
        df['line{}'.format(i)] = ati
        
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
):

    # ~ default
    g_params = {
        "xmin": 20,
        "xmax": 20000,
        "ymin": -40,
        "ymax": 10,
        "width": 400,
        "height": 250,
    }
    g_params["width"] = 800
    g_params["height"] = 400

    # what's the min over freq?
    reg_min = optim_config["freq_reg_min"]
    reg_max = optim_config["freq_reg_max"]
    domain = [reg_min, reg_max]
    # build a graph for each peq
    g_auto_eq = graph_eq(freq, auto_peq, domain, "{} auto".format(speaker_name))

    # compare the 2 eqs
    target = -(auto_target[0] - auto_target_interp[0])
    # print('target {} {}'.format(np.min(target), np.max(target)))
    g_eq_full = graph_eq_compare(
        freq, auto_peq, auto_target_interp, domain, speaker_name, speaker_origin, target
    )

    # compare the 2 corrected curves
    df_optim = pd.DataFrame({"Freq": freq})
    df_optim["Auto"] = (
        auto_target[0] - auto_target_interp[0] + peq_build(freq, auto_peq)
    )
    # show the 3 spinoramas
    unmelted_spin = spin.pivot_table(
        index="Freq", columns="Measurements", values="dB", aggfunc=max
    ).reset_index()

    g_spin_noeq, g_spin_noeq_di = plot_spinorama_traces(unmelted_spin, g_params)
    g_spin_auto, g_spin_auto_di, unmelted_spin_auto = None, None, None
    if spin_auto is not None:
        unmelted_spin_auto = spin_auto.pivot_table(
            index="Freq", columns="Measurements", values="dB", aggfunc=max
        ).reset_index()
        g_spin_auto, g_spin_auto_di = plot_spinorama_traces(
            unmelted_spin_auto, g_params
        )

    # show the 3 optimised curves
    g_curves = {}
    for which_curve in ("On Axis", "Listening Window", "Estimated In-Room Response"):
        data = unmelted_spin
        data_auto = unmelted_spin_auto
        if which_curve == "Estimated In-Room Response":
            data = pir.pivot_table(
                index="Freq", columns="Measurements", values="dB", aggfunc=max
            ).reset_index()
            data_auto = pir_auto.pivot_table(
                index="Freq", columns="Measurements", values="dB", aggfunc=max
            ).reset_index()

        # print(data.keys())
        g_curve_noeq = plot_graph_regression_traces(data, which_curve, g_params)

        g_curve_auto = None
        if data_auto is not None:
            g_curve_auto = plot_graph_regression_traces(
                data_auto, which_curve, g_params
            )
        g_curves[which_curve] = {
            "noeq": g_curve_noeq,
            "auto": g_curve_auto,
        }

    fig = make_subplots(
        rows=4,
        cols=2,
        subplot_titles=(
            "PEQ details",
            "PEQ v.s. Target",
            "Spinorama",
            "Spinorama with EQ",
            "Listening Window",
            "Listening Window with EQ",
            "Estimate In-Room Response",
            "Estimate In-Room Response with EQ",
        ),
        horizontal_spacing=0.075,
        vertical_spacing=0.075,
        specs=[
            [{}, {}],
            [{"secondary_y": True}, {"secondary_y": True}],
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

    # add LW and PIR
    for t in g_curves["Listening Window"]["noeq"]:
        fig.add_trace(t, row=3, col=1)
    for t in g_curves["Listening Window"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=3, col=2)

    fig.update_xaxes(generate_xaxis(), row=3)
    fig.update_yaxes(generate_yaxis_spl(-10, 5, 1), row=3)

    for t in g_curves["Estimated In-Room Response"]["noeq"]:
        t["showlegend"] = False
        fig.add_trace(t, row=4, col=1)
    for t in g_curves["Estimated In-Room Response"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=4, col=2)

    fig.update_xaxes(generate_xaxis(), row=4)
    fig.update_yaxes(generate_yaxis_spl(-10, 5, 1), row=4)

    fig.update_layout(
        width=1400,
        height=1600,
        legend=dict(orientation="v"),
        title="{} from {}".format(speaker_name, speaker_origin),
    )

    # add all graphs and print it
    return [
        ("eq", fig),
    ]
