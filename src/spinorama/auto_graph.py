#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

from spinorama.load_misc import graph_melt
from spinorama.filter_peq import peq_build  # peq_print
from spinorama.graph import graph_spinorama, graph_freq, graph_regression


def graph_eq(freq, peq, domain, title):
    df_eq = pd.DataFrame({"Freq": freq})
    for i, (pos, eq) in enumerate(peq):
        df_eq["EQ {}".format(i)] = peq_build(freq, [(pos, eq)])

    g_eq = (
        alt.Chart(graph_melt(df_eq))
        .mark_line()
        .encode(
            alt.X(
                "Freq:Q",
                title="Freq (Hz)",
                scale=alt.Scale(type="log", nice=False, domain=domain),
            ),
            alt.Y(
                "dB:Q",
                title="Sound Pressure (dB)",
                scale=alt.Scale(zero=False, domain=[-5, 5]),
            ),
            alt.Color("Measurements", type="nominal", sort=None),
        )
        .properties(width=800, height=400, title="{} EQ".format(title))
    )
    return g_eq


def graph_eq_compare(freq, manual_peq, auto_peq, domain, speaker_name):
    if manual_peq is None:
        peq_df = pd.DataFrame(
            {
                "Freq": freq,
                "dB": peq_build(freq, auto_peq),
            }
        )
        chart = (
            alt.Chart(peq_df)
            .mark_line()
            .encode(
                alt.X(
                    "Freq:Q",
                    title="Freq (Hz)",
                    scale=alt.Scale(type="log", nice=False, domain=domain),
                ),
                alt.Y(
                    "dB:Q",
                    title="Sound Pressure (dB)",
                    scale=alt.Scale(zero=False, domain=[-5, 5]),
                ),
            )
            .properties(
                width=800,
                height=400,
                title="{} auto EQ".format(speaker_name),
            )
        )
    else:
        chart = (
            alt.Chart(
                graph_melt(
                    pd.DataFrame(
                        {
                            "Freq": freq,
                            "Manual": peq_build(freq, manual_peq),
                            "Auto": peq_build(freq, auto_peq),
                        }
                    )
                )
            )
            .mark_line()
            .encode(
                alt.X(
                    "Freq:Q",
                    title="Freq (Hz)",
                    scale=alt.Scale(type="log", nice=False, domain=domain),
                ),
                alt.Y(
                    "dB:Q",
                    title="Sound Pressure (dB)",
                    scale=alt.Scale(zero=False, domain=[-5, 5]),
                ),
                alt.Color("Measurements", type="nominal", sort=None),
            )
            .properties(
                width=800,
                height=400,
                title="{} manual and auto EQ filters".format(speaker_name),
            )
        )
    return chart


def graph_results(
    speaker_name,
    freq,
    manual_peq,
    auto_peq,
    auto_target,
    auto_target_interp,
    manual_target,
    manual_target_interp,
    spin,
    spin_manual,
    spin_auto,
    pir,
    pir_manual,
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

    # generate an empty graph
    empty_data = pd.DataFrame({"Freq": spin.Freq.values, "dB": 0, "Measurements": ""})
    empty_graph = graph_freq(empty_data, g_params)

    # what's the min over freq?
    reg_min = optim_config["freq_reg_min"]
    reg_max = optim_config["freq_reg_max"]
    domain = [reg_min, reg_max]
    # build a graph for each peq
    if manual_peq is not None:
        g_manual_eq = graph_eq(
            freq, manual_peq, domain, "{} manual".format(speaker_name)
        )
    g_auto_eq = graph_eq(freq, auto_peq, domain, "{} auto".format(speaker_name))

    # compare the 2 eqs
    g_eq_full = graph_eq_compare(freq, manual_peq, auto_peq, domain, speaker_name)

    # compare the 2 corrected curves
    df_optim = pd.DataFrame({"Freq": freq})
    df_optim["Auto"] = (
        auto_target[0] - auto_target_interp[0] + peq_build(freq, auto_peq)
    )
    if manual_target is not None:
        df_optim["Manual"] = (
            manual_target[0] - manual_target_interp[0] + peq_build(freq, manual_peq)
        )
        g_optim = (
            alt.Chart(graph_melt(df_optim))
            .mark_line()
            .encode(
                alt.X(
                    "Freq:Q",
                    title="Freq (Hz)",
                    scale=alt.Scale(type="log", nice=False, domain=domain),
                ),
                alt.Y(
                    "dB:Q",
                    title="Sound Pressure (dB)",
                    scale=alt.Scale(zero=False, domain=[-5, 5]),
                ),
                alt.Color("Measurements", type="nominal", sort=None),
            )
            .properties(
                width=800,
                height=400,
                title="{} manual and auto corrected {}".format(
                    speaker_name, optim_config["curve_names"][0]
                ),
            )
        )

    # show the 3 spinoramas
    g_spin_asr = graph_spinorama(spin, g_params).properties(
        title="{} from ASR".format(speaker_name)
    )
    if manual_peq is not None:
        g_spin_manual = graph_spinorama(spin_manual, g_params).properties(
            title="{} ASR + manual EQ".format(speaker_name)
        )
    g_spin_auto = empty_graph
    if spin_auto is not None:
        g_spin_auto = graph_spinorama(spin_auto, g_params).properties(
            title="{} ASR + auto EQ".format(speaker_name)
        )

    # show the 3 optimised curves
    # which_curve='Listening Window
    # which_curve='Sound Power'
    which_curve = "Estimated In-Room Response"
    data = spin
    if manual_peq is not None:
        data_manual = spin_manual
    data_auto = spin_auto
    if which_curve == "Estimated In-Room Response":
        data = pir
        if manual_peq is not None:
            data_manual = pir_manual
        data_auto = pir_auto

    g_pir_reg = empty_graph
    if data_auto is not None:
        g_pir_reg = graph_regression(
            data_auto.loc[(data_auto.Measurements == which_curve)], 100, reg_max
        )

    g_pir_asr = (
        (graph_freq(data.loc[(data.Measurements == which_curve)], g_params) + g_pir_reg)
        .properties(title="{} from ASR [{}]".format(speaker_name, which_curve))
        .resolve_scale(color="independent")
        .resolve_legend(shape="independent")
    )

    g_pir_manual = empty_graph
    if manual_peq is not None:
        g_pir_manual = (
            (
                graph_freq(
                    data_manual.loc[(data_manual.Measurements == which_curve)], g_params
                )
                + g_pir_reg
            )
            .properties(
                title="{} from ASR [{}] + manual EQ".format(speaker_name, which_curve)
            )
            .resolve_scale(color="independent")
            .resolve_legend(shape="independent")
        )

    g_pir_auto = empty_graph
    if data_auto is not None:
        g_pir_auto = (
            (
                graph_freq(
                    data_auto.loc[(data_auto.Measurements == which_curve)], g_params
                )
                + g_pir_reg
            )
            .properties(
                title="{} from ASR [{}] + auto EQ".format(speaker_name, which_curve)
            )
            .resolve_scale(color="independent")
            .resolve_legend(shape="independent")
        )

    # add all graphs and print it
    if manual_peq is not None:
        return [
            (g_manual_eq | g_auto_eq) & (g_eq_full | g_optim),
            (g_spin_asr | g_spin_manual | g_spin_auto),
            (g_pir_asr | g_pir_manual | g_pir_auto).resolve_scale(y="independent"),
        ]

    return [
        (g_auto_eq | g_eq_full),
        (g_spin_asr | g_spin_auto),
        (g_pir_asr | g_pir_auto).resolve_scale(y="independent"),
    ]
