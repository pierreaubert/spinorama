# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from spinorama.constant_paths import MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ
from spinorama.filter_peq import peq_build, peq_preamp_gain
from spinorama.compute_misc import savitzky_golay, compute_statistics
from spinorama.plot import (
    colors,
    plot_spinorama_traces,
    plot_graph_regression_traces,
    plot_graph_flat_traces,
    generate_xaxis,
    generate_yaxis_spl,
    generate_yaxis_di,
)


def short_curve_name(name):
    """Return an abbrev for curve name"""
    if name == "Listening Window":
        return "LW"
    if name == "Estimated In-Room Response":
        return "PIR"
    if name == "On Axis":
        return "ON"
    return name


def print_freq(freq):
    """Pretty print frequency"""
    if freq < 1000:
        return f"{int(freq)}Hz"

    if int(freq) % 1000 == 0:
        return f"{freq // 1000}kHz"

    return f"{freq / 1000:0.1f}kHz"


def graph_eq(freq, peq):
    """take a PEQ and return traces (for plotly) with frequency data"""
    data_frame = pd.DataFrame({"Freq": freq})
    for i, (pos, biquad) in enumerate(peq):
        data_frame[f"{biquad.type2str(True)} {i}"] = peq_build(freq, [(pos, biquad)])

    traces = []
    for i, key in enumerate(data_frame.keys()):
        if key != "Freq":
            traces.append(
                go.Scatter(
                    x=data_frame.Freq,
                    y=data_frame[key],
                    name=key,
                    legendgroup="PEQ",
                    legendgrouptitle_text="EQ",
                    marker_color=colors[i % len(colors)],
                )
            )
    return traces


def graph_eq_compare(freq, auto_peq, auto_target_interp, target, optim_config):
    """ "return traces with eq v.s. target"""
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

    target_name = f"error {curve_names[0]}"
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
            df[f"ideal {curve_names[i]}"] = ati
        else:
            df[f"ideal {i}"] = ati

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
    optim_config["freq_reg_min"]
    optim_config["freq_reg_max"]
    # build a graph for each peq
    g_auto_eq = graph_eq(freq, auto_peq)

    # compare the 2 eqs
    target = -(auto_target[0] - auto_target_interp[0])
    # with open("debug_target.txt", "w") as fd:
    #    for f, a in zip(freq, target):
    #        fd.write("{} {}\n".format(f, a))
    #    fd.close()

    g_eq_full = graph_eq_compare(
        freq,
        auto_peq,
        auto_target_interp,
        target,
        optim_config,
    )

    # compare the 2 corrected curves
    df_optim = pd.DataFrame({"Freq": freq})
    df_optim["Auto"] = auto_target[0] - auto_target_interp[0] + peq_build(freq, auto_peq)
    # show the 2 spinoramas
    unmelted_spin = spin.pivot_table(
        index="Freq", columns="Measurements", values="dB", aggfunc=max
    ).reset_index()

    g_spin_noeq, g_spin_noeq_di = plot_spinorama_traces(unmelted_spin, g_params)
    g_spin_auto, g_spin_auto_di, unmelted_spin_auto = None, None, None
    if spin_auto is not None:
        unmelted_spin_auto = spin_auto.pivot_table(
            index="Freq", columns="Measurements", values="dB", aggfunc=max
        ).reset_index()
        g_spin_auto, g_spin_auto_di = plot_spinorama_traces(unmelted_spin_auto, g_params)

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

        if which_curve == "Estimated In-Room Response":
            g_curve_noeq = plot_graph_regression_traces(data, which_curve, g_params)
        else:
            g_curve_noeq = plot_graph_flat_traces(data, which_curve, g_params)

        g_curve_auto = None
        if data_auto is not None:
            if which_curve == "Estimated In-Room Response":
                g_curve_auto = plot_graph_regression_traces(data_auto, which_curve, g_params)
            else:
                g_curve_auto = plot_graph_flat_traces(data_auto, which_curve, g_params)

        # ranges in Freq
        target_min_freq = optim_config["target_min_freq"]
        target_max_freq = optim_config["target_max_freq"]

        # gather stats
        short_curve = short_curve_name(which_curve)
        noeq_slope, noeq_hist, noeq_max = compute_statistics(
            data, which_curve, target_min_freq, target_max_freq, target_min_freq, target_max_freq
        )
        auto_slope, auto_hist, auto_max = compute_statistics(
            data_auto,
            which_curve,
            target_min_freq,
            target_max_freq,
            target_min_freq,
            target_max_freq,
        )

        # generate title
        noeq_title = f"{short_curve} slope {noeq_slope:+0.2f}dB/Octave error max={noeq_max:.1f}dB"
        auto_title = (
            f"{short_curve} with EQ slope {auto_slope:+0.2f}dB/Octave error max={auto_max:.1f}dB"
        )

        # generate histogram of deviation
        noeq_counts, noeq_bins = noeq_hist
        auto_counts, auto_bins = auto_hist
        bins = sorted(list(set(noeq_bins).union(auto_bins)))
        bins = [f"{noeq_bins[i]:0.1f}-{noeq_bins[i+1]:0.1f}" for i in range(0, len(noeq_bins) - 1)]
        bins.append(f"{noeq_bins[-1]:0.1f}+")
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
        noeq_slope, noeq_hist, noeq_max = compute_statistics(
            data,
            which_curve,
            target_min_freq,
            target_max_freq,
            MIDRANGE_MIN_FREQ,
            MIDRANGE_MAX_FREQ,
        )
        auto_slope, auto_hist, auto_max = compute_statistics(
            data_auto,
            which_curve,
            target_min_freq,
            target_max_freq,
            MIDRANGE_MIN_FREQ,
            MIDRANGE_MAX_FREQ,
        )
        noeq_counts, noeq_bins = noeq_hist
        auto_counts, auto_bins = auto_hist
        bins = sorted(list(set(noeq_bins).union(auto_bins)))
        bins = [f"{noeq_bins[i]:0.1f}-{noeq_bins[i+1]:0.1f}" for i in range(0, len(noeq_bins) - 1)]
        bins.append(f"{noeq_bins[-1]:0.1f}+")
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
        rows=8,
        cols=2,
        subplot_titles=(
            f"PEQ details (N={len(auto_peq)} Gain={peq_preamp_gain(auto_peq):0.1f})",
            "PEQ v.s. Target",
            spin_title,
            auto_spin_title,
            g_curves["On Axis"]["noeq_title"],
            g_curves["On Axis"]["auto_title"],
            "",
            "",
            g_curves["Listening Window"]["noeq_title"],
            g_curves["Listening Window"]["auto_title"],
            "",
            "",
            g_curves["Estimated In-Room Response"]["noeq_title"],
            g_curves["Estimated In-Room Response"]["auto_title"],
            "",
            "",
        ),
        row_heights=[
            0.15,  # PEQ
            0.20,  # SPIN
            0.15,  # ON
            0.066,  # ON HIST
            0.15,  # LW
            0.066,  # LW HIST
            0.15,  # PIR
            0.066,  # PIR HIST
        ],
        horizontal_spacing=0.075,
        vertical_spacing=0.05,
        specs=[
            [{}, {}],
            [{"secondary_y": True}, {"secondary_y": True}],
            [{}, {}],
            [{}, {}],
            [{}, {}],
            [{}, {}],
            [{}, {}],
            [{}, {}],
        ],
    )

    # separated figures for mobile rendering
    fig_auto_eq = go.Figure()
    fig_eq_full = go.Figure()

    # use an index to be able to move plots around
    current_row = 1

    # add EQ and EQ v.s. Target
    auto_eq_max = -1
    auto_eq_min = 1
    for t in g_auto_eq:
        auto_eq_min = min(auto_eq_min, np.min(t.y))
        auto_eq_max = max(auto_eq_max, np.max(t.y))
        fig.add_trace(t, row=current_row, col=1)
        t["legendgroup"] = None
        fig_auto_eq.add_trace(t)

    for t in g_eq_full:
        auto_eq_min = min(auto_eq_min, np.min(t.y))
        auto_eq_max = max(auto_eq_max, np.max(t.y))
        fig.add_trace(t, row=current_row, col=2)
        t["legendgroup"] = None
        fig_eq_full.add_trace(t)
    auto_eq_max = int(auto_eq_max) + 1
    auto_eq_min = int(auto_eq_min) - 2
    # auto_eq_max = min(auto_eq_max, 5)

    xaxis = generate_xaxis()
    yaxis = generate_yaxis_spl(auto_eq_min, auto_eq_max, 1)
    fig.update_xaxes(xaxis, row=current_row)
    fig.update_yaxes(yaxis, row=current_row)
    fig_auto_eq.update_xaxes(xaxis)
    fig_auto_eq.update_yaxes(yaxis)
    fig_eq_full.update_xaxes(xaxis)
    fig_eq_full.update_yaxes(yaxis)

    # add 2 spins
    current_row += 1
    fig_spin_noeq = make_subplots(specs=[[{"secondary_y": True}]])
    fig_spin_auto = make_subplots(specs=[[{"secondary_y": True}]])

    for t in g_spin_noeq:
        fig.add_trace(t, row=current_row, col=1, secondary_y=False)
        t["legendgroup"] = None
        fig_spin_noeq.add_trace(t, secondary_y=False)

    for t in g_spin_noeq_di:
        fig.add_trace(t, row=current_row, col=1, secondary_y=True)
        t["legendgroup"] = None
        fig_spin_noeq.add_trace(t, secondary_y=True)

    for t in g_spin_auto:
        t["showlegend"] = False
        fig.add_trace(t, row=current_row, col=2, secondary_y=False)
        t["showlegend"] = True
        t["legendgroup"] = None
        fig_spin_auto.add_trace(t, secondary_y=False)

    for t in g_spin_auto_di:
        t["showlegend"] = False
        fig.add_trace(t, row=current_row, col=2, secondary_y=True)
        t["showlegend"] = True
        t["legendgroup"] = None
        fig_spin_auto.add_trace(t, secondary_y=True)

    xaxis = generate_xaxis()
    yaxis = generate_yaxis_spl()
    yaxis_di = generate_yaxis_di()
    fig.update_xaxes(xaxis, row=current_row)
    fig.update_yaxes(yaxis, row=current_row)
    fig.update_yaxes(yaxis_di, row=current_row, secondary_y=True)
    fig_spin_noeq.update_xaxes(xaxis)
    fig_spin_noeq.update_yaxes(yaxis)
    fig_spin_noeq.update_yaxes(yaxis_di, secondary_y=True)
    fig_spin_auto.update_xaxes(xaxis)
    fig_spin_auto.update_yaxes(yaxis)
    fig_spin_auto.update_yaxes(yaxis_di, secondary_y=True)

    # add ON, LW and PIR

    fig_on_noeq = go.Figure()
    fig_lw_noeq = go.Figure()
    fig_pir_noeq = go.Figure()
    fig_on_auto = go.Figure()
    fig_lw_auto = go.Figure()
    fig_pir_auto = go.Figure()

    current_row += 1
    on_min = -10
    on_max = 5
    for t in g_curves["On Axis"]["noeq"]:
        fig.add_trace(t, row=current_row, col=1)
        t["legendgroup"] = None
        t["legendgrouptitle"] = None
        fig_on_noeq.add_trace(t)
        on_min = min(on_min, np.min(t.y))
        on_max = max(on_max, np.max(t.y))

    for t in g_curves["On Axis"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=current_row, col=2)
        t["legendgroup"] = None
        t["legendgrouptitle"] = None
        t["showlegend"] = True
        fig_on_auto.add_trace(t)
        on_min = min(on_min, np.min(t.y))
        on_max = max(on_max, np.max(t.y))

    xaxis = generate_xaxis()
    fig.update_xaxes(xaxis, row=current_row)
    fig_on_noeq.update_xaxes(xaxis)
    fig_on_auto.update_xaxes(xaxis)

    on_min = max(-15, -5 * round(-on_min / 5)) if on_min < -5 else -5
    on_max = min(20, 5 * (round(on_max / 5) + 1)) if on_max > 5 else 5

    yaxis = generate_yaxis_spl(on_min, on_max, 1)
    fig.update_yaxes(yaxis, row=current_row)
    fig_on_noeq.update_yaxes(yaxis)
    fig_on_auto.update_yaxes(yaxis)

    # LW

    current_row += 2

    lw_min = -10
    lw_max = 5
    for t in g_curves["Listening Window"]["noeq"]:
        fig.add_trace(t, row=current_row, col=1)
        t["legendgroup"] = None
        t["legendgrouptitle"] = None
        fig_lw_noeq.add_trace(t)
        lw_min = min(lw_min, np.min(t.y))
        lw_max = max(lw_max, np.max(t.y))

    for t in g_curves["Listening Window"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=current_row, col=2)
        t["legendgroup"] = None
        t["legendgrouptitle"] = None
        t["showlegend"] = True
        fig_lw_auto.add_trace(t)
        lw_min = min(lw_min, np.min(t.y))
        lw_max = max(lw_max, np.max(t.y))

    xaxis = generate_xaxis()
    fig.update_xaxes(xaxis, row=current_row)
    fig_lw_noeq.update_xaxes(xaxis)
    fig_lw_auto.update_xaxes(xaxis)

    lw_min = max(-15, -5 * round(-lw_min / 5)) if lw_min < -5 else -5
    lw_max = min(20, 5 * (round(lw_max / 5) + 1))

    yaxis = generate_yaxis_spl(lw_min, lw_max, 1)
    fig.update_yaxes(yaxis, row=current_row)
    fig_lw_noeq.update_yaxes(yaxis)
    fig_lw_auto.update_yaxes(yaxis)

    # PIR

    current_row += 2

    pir_min = -10
    pir_max = 5
    for t in g_curves["Estimated In-Room Response"]["noeq"]:
        fig.add_trace(t, row=current_row, col=1)
        t["legendgroup"] = None
        t["legendgrouptitle"] = None
        fig_pir_noeq.add_trace(t)
        pir_min = min(pir_min, np.min(t.y))
        pir_max = max(pir_max, np.max(t.y))

    for t in g_curves["Estimated In-Room Response"]["auto"]:
        t["showlegend"] = False
        fig.add_trace(t, row=current_row, col=2)
        t["legendgroup"] = None
        t["legendgrouptitle"] = None
        t["showlegend"] = True
        fig_pir_auto.add_trace(t)
        pir_min = min(pir_min, np.min(t.y))
        pir_max = max(pir_max, np.max(t.y))

    pir_min = max(-15, -5 * round(-pir_min / 5))
    pir_max = min(20, 5 * (round(pir_max / 5) + 1))

    xaxis = generate_xaxis()
    fig.update_xaxes(xaxis, row=current_row)
    fig_pir_noeq.update_xaxes(xaxis)
    fig_pir_auto.update_xaxes(xaxis)

    yaxis = generate_yaxis_spl(pir_min, pir_max, 1)
    fig.update_yaxes(yaxis, row=current_row)
    fig_pir_auto.update_yaxes(yaxis)
    fig_pir_noeq.update_yaxes(yaxis)

    # add error distribution
    fig_hist_fullrange = {}
    fig_hist_midrange = {}
    for i, curve in enumerate(["On Axis", "Listening Window", "Estimated In-Room Response"]):
        current_hist_fr = go.Figure()
        for t in g_curves[curve]["hist"]:
            fig.add_trace(t, row=4 + 2 * i, col=1)
            fig.update_yaxes(title="Count", row=4 + 2 * i, col=1)
            t["legendgroup"] = None
            t["legendgrouptitle"] = None
            current_hist_fr.add_trace(t)
            current_hist_fr.update_yaxes(title="Count")
        fig_hist_fullrange[curve] = current_hist_fr

        current_hist_mr = go.Figure()
        for t in g_curves[curve]["hist_midrange"]:
            fig.add_trace(t, row=4 + 2 * i, col=2)
            fig.update_yaxes(title="Count", row=4 + 2 * i, col=2)
            t["legendgroup"] = None
            t["legendgrouptitle"] = None
            current_hist_mr.add_trace(t)
            current_hist_mr.update_yaxes(title="Count")
        fig_hist_midrange[curve] = current_hist_mr

    # add tonal balance

    # almost done
    fig.update_layout(
        width=1400,
        # height=1400*29.7/21, # a4 is a bit squeezed
        height=2400,
        legend=dict(orientation="v"),
        title="{} from {}. Config: curves={} fitness={} target_min_freq={:.0f}Hz".format(
            speaker_name,
            speaker_origin,
            ", ".join(optim_config["curve_names"]),
            optim_config.get("loss", "unknown"),
            optim_config["target_min_freq"],
        ),
    )

    for f in (
        fig_auto_eq,
        fig_eq_full,
        fig_spin_noeq,
        fig_spin_auto,
        fig_on_noeq,
        fig_on_auto,
        fig_lw_noeq,
        fig_lw_auto,
        fig_pir_noeq,
        fig_pir_auto,
    ):
        f.update_layout(
            width=600,
            height=450,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                xanchor="left",
                y=1.02,
                x=0.02,
                title=None,
                font=dict(size=12),
            ),
        )

    for c in ["On Axis", "Listening Window", "Estimated In-Room Response"]:
        for f in (fig_hist_fullrange[c], fig_hist_midrange[c]):
            f.update_layout(
                width=600,
                height=300,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    xanchor="left",
                    y=1.02,
                    x=0.02,
                    title=None,
                    font=dict(size=12),
                ),
            )

    # add all graphs and print it
    return [
        # all together
        ("eq", fig),
        # eq
        ("auto_eq", fig_auto_eq),
        ("eq_full", fig_eq_full),
        # spin
        ("spin_noeq", fig_spin_noeq),
        ("spin_auto", fig_spin_auto),
        # on
        ("on_noeq", fig_on_noeq),
        ("on_auto", fig_on_auto),
        ("on_hist_fullrange", fig_hist_fullrange["On Axis"]),
        ("on_hist_midrange", fig_hist_midrange["On Axis"]),
        # lw
        ("lw_noeq", fig_lw_noeq),
        ("lw_auto", fig_lw_auto),
        ("lw_hist_fullrange", fig_hist_fullrange["Listening Window"]),
        ("lw_hist_midrange", fig_hist_midrange["Listening Window"]),
        # pir
        ("pir_noeq", fig_pir_noeq),
        ("pir_auto", fig_pir_auto),
        ("pir_hist_fullrange", fig_hist_fullrange["Estimated In-Room Response"]),
        ("pir_hist_midrange", fig_hist_midrange["Estimated In-Room Response"]),
    ]
