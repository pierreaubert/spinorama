# -*- coding: utf-8 -*-
import logging
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from scipy import stats

from .compute_misc import compute_contour
from .load_misc import sort_angles

logger = logging.getLogger("spinorama")

pio.templates.default = "plotly_white"
width = 600

plot_params_default = {
    "xmin": 20,
    "xmax": 20000,
    "ymin": -40,
    "ymax": 10,
    "width": 600,
    "height": 360,
}

contour_params_default = {
    "xmin": 100,
    "xmax": 20000,
    "width": 400,
    "height": 360,
    # 'contour_scale': [-12, -9, -8, -7, -6, -5, -4, -3, -2.5, -2, -1.5, -1, -0.5, 0],
    "contour_scale": [-30, 0],
    # 'contour_scale': [-30, -25, -20, -15, -10, -5, 0],
    "colormap": "spectral",
    # 'colormap': 'redyellowblue',
    # 'colormap': 'blueorange',
    # 'colormap': 'blues',
}

isoband_params_default = {
    "xmin": 100,
    "xmax": 20000,
    "width": 600,
    "height": 360,
    "bands": [-72, -18, -15, -12, -9, -6, -3, +3],
}

radar_params_default = {
    "xmin": 400,
    "xmax": 20000,
    "width": 180,
    "height": 180,
    "contour_scale": [-12, -9, -8, -7, -6, -5, -4, -3, -2.5, -2, -1.5, -1, -0.5, 0],
}

colors = [
    "#5c77a5",
    "#dc842a",
    "#c85857",
    "#89b5b1",
    "#71a152",
    "#bab0ac",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]

uniform_colors = {
    # regression
    "Linear Regression": colors[0],
    "Band ±1.5dB": colors[1],
    "Band ±3dB": colors[1],
    # PIR
    "Estimated In-Room Response": colors[0],
    # spin
    "On Axis": colors[0],
    "Listening Window": colors[1],
    "Early Reflections": colors[2],
    "Sound Power": colors[3],
    "Early Reflections DI": colors[4],
    "Sound Power DI": colors[5],
    # reflections
    "Ceiling Bounce": colors[1],
    "Floor Bounce": colors[2],
    "Front Wall Bounce": colors[3],
    "Rear Wall Bounce": colors[4],
    "Side Wall Bounce": colors[5],
    #
    "Ceiling Reflection": colors[1],
    "Floor Reflection": colors[2],
    #
    "Front": colors[1],
    "Rear": colors[2],
    "Side": colors[3],
    #
    "Total Early Reflection": colors[7],
    "Total Horizontal Reflection": colors[8],
    "Total Vertical Reflection": colors[9],
    # SPL
    "10°": colors[1],
    "20°": colors[2],
    "30°": colors[3],
    "40°": colors[4],
    "50°": colors[5],
    "60°": colors[6],
    "70°": colors[7],
    #
    "500 Hz": colors[1],
    "1000 Hz": colors[2],
    "2000 Hz": colors[3],
    "10000 Hz": colors[4],
    "15000 Hz": colors[5],
}


def generate_xaxis(freq_min=20):
    return dict(
        title_text="Frequency (Hz)",
        type="log",
        range=[math.log10(freq_min), math.log10(20000)],
        tickvals=[
            20,
            30,
            40,
            50,
            60,
            70,
            80,
            90,
            100,
            200,
            300,
            400,
            500,
            600,
            700,
            800,
            900,
            1000,
            2000,
            3000,
            4000,
            5000,
            6000,
            7000,
            8000,
            9000,
            10000,
            20000,
        ],
        ticktext=[
            "20",
            " ",
            " ",
            "50",
            " ",
            " ",
            "  ",
            " ",
            "100",
            "200",
            " ",
            " ",
            "500",
            " ",
            " ",
            "  ",
            " ",
            "1k",
            "2k",
            " ",
            " ",
            "5k",
            " ",
            " ",
            "  ",
            " ",
            "10k",
            "20k",
        ],
    )


def generate_yaxis_spl():
    return dict(
        title_text="SPL (dB)",
        range=[-40, 10],
        dtick=1,
        tickvals=[i for i in range(-40, 10)],
        ticktext=["{}".format(i) if not i % 5 else " " for i in range(-40, 10)],
    )


def generate_yaxis_angles():
    return dict(
        title_text="Angle",
        range=[-180, 180],
        dtick=30,
        tickvals=[v for v in range(-180, 210, 30)],
        ticktext=["{}°".format(v) for v in range(-180, 210, 30)],
    )


def plot_spinorama(spin, graph_params):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for measurement in (
        "On Axis",
        "Listening Window",
        "Early Reflections",
        "Sound Power",
    ):
        if measurement not in spin.keys():
            continue
        fig.add_trace(
            go.Scatter(
                x=spin.Freq,
                y=spin[measurement],
                name=measurement,
                legendgroup="measurements",
                legendgrouptitle_text="Measurements",
                marker_color=uniform_colors.get(measurement, "black"),
            ),
            secondary_y=False,
        )
    for measurement in ("Early Reflections DI", "Sound Power DI"):
        if measurement not in spin.keys():
            continue
        fig.add_trace(
            go.Scatter(
                x=spin.Freq,
                y=spin[measurement],
                name=measurement,
                legendgroup="DI",
                legendgrouptitle_text="Directivity",
                marker_color=uniform_colors.get(measurement, "black"),
            ),
            secondary_y=True,
        )
    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl())
    fig.update_yaxes(
        title_text="DI (dB)                                                    &nbsp;",
        secondary_y=True,
        range=[-5, 45],
        dtick=5,
        tickvals=[-5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45],
        ticktext=["-5", "0", "5", "10", "15", " ", " ", " ", " ", " ", " "],
    )
    fig.update_layout(
        width=600 * math.sqrt(2),
        height=600,
        legend=dict(orientation="v"),
    )
    return fig


def plot_graph(df, graph_params):
    fig = go.Figure()
    for measurement in df.keys():
        if measurement != "Freq":
            fig.add_trace(
                go.Scatter(
                    x=df.Freq,
                    y=df[measurement],
                    name=measurement,
                    legendgroup="measurements",
                    legendgrouptitle_text="Measurements",
                    marker_color=uniform_colors.get(measurement, "black"),
                ),
            )
    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl())
    fig.update_layout(
        width=600 * math.sqrt(2),
        height=600,
        legend=dict(orientation="v"),
    )
    return fig


def plot_graph_regression(df, measurement, graph_params):
    # print("{} {}".format(measurement, df.keys()))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.Freq,
            y=df[measurement],
            name=measurement,
            legendgroup="measurements",
            legendgrouptitle_text="Measurements",
            marker_color=uniform_colors.get(measurement, "black"),
        ),
    )

    current_restricted = df.loc[(df.Freq > 300) & (df.Freq < 3000)]

    slope, intercept, r, p, se = stats.linregress(
        x=current_restricted["Freq"], y=current_restricted[measurement]
    )

    # print("step {} {}".format(slope, intercept))

    # 600 px = 50 dB
    height = 600
    one_db = 600 / 50
    fig.add_trace(
        go.Scatter(
            x=df.Freq,
            y=[slope * math.log10(f) + intercept for f in df.Freq],
            line=dict(width=2, color="black"),
            opacity=1,
            name="Linear regression",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.Freq,
            y=[slope * math.log10(f) + intercept for f in df.Freq],
            line=dict(width=3 * one_db, color="gray"),
            opacity=0.15,
            name="Band ±1.5dB",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.Freq,
            y=[slope * math.log10(f) + intercept for f in df.Freq],
            line=dict(width=6 * one_db, color="gray"),
            opacity=0.1,
            name="Band ±3dB",
        )
    )

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl())
    fig.update_layout(
        width=600 * math.sqrt(2),
        height=600,
        legend=dict(orientation="v"),
    )
    # print("fig is {}".format(fig))
    return fig


def plot_contour(spl, params):
    min_freq = 200
    contour_start = -72
    contour_end = 3
    contour_range = contour_end - contour_start
    contour_bands = [-72, -18, -15, -12, -9, -6, -3, +3]
    contour_colors = [
        "black",
        "blue",
        "steelblue",
        "green",
        "yellow",
        "orange",
        "red",
        "white",
    ]

    contour_colorscale = [
        [1 + (scale - contour_end) / contour_range, color]
        for scale, color in zip(contour_bands, contour_colors)
    ]

    fig = go.Figure()

    af, am, az = compute_contour(spl.loc[spl.Freq > min_freq], min_freq)
    fig.add_trace(
        go.Contour(
            x=af[0],
            y=am.T[0],
            z=az,
            contours=dict(
                start=contour_start, end=contour_end, size=3, showlabels=True
            ),
            colorscale=contour_colorscale,
        )
    )
    fig.update_xaxes(generate_xaxis(min_freq))
    fig.update_yaxes(generate_yaxis_angles())
    fig.update_layout(width=600 * 1.414, height=600)
    return fig


def find_nearest_freq(dfu, hz, tolerance=0.05):
    """return the index of the nearest freq in dfu, return None if not found"""
    ihz = None
    for i in dfu.index:
        f = dfu.loc[i]
        if abs(f - hz) < hz * tolerance:
            ihz = i
            break
    logger.debug("nearest: {0} hz at loc {1}".format(hz, ihz))
    return ihz


def plot_radar(spl, params):

    anglelist = [a for a in range(-180, 180, 10)]

    def projection(anglelist, gridZ, hz):
        dbsR = [db for a, db in zip(anglelist, gridZ)]
        dbsTheta = [a for a, db in zip(anglelist, gridZ)]
        dbsR.append(dbsR[0])
        dbsTheta.append(dbsTheta[0])
        return dbsR, dbsTheta, [hz for i in range(0, len(dbsR))]

    def label(i):
        return "{:d} Hz".format(i)

    def plot_radar_freq(anglelist, df):
        dfu = sort_angles(df)
        db_mean = np.mean(
            dfu.loc[(dfu.Freq > 900) & (dfu.Freq < 1100)]["On Axis"].values
        )
        freq = dfu.Freq
        dfu = dfu.drop("Freq", axis=1)
        db_min = np.min(dfu.min(axis=0).values)
        db_max = np.max(dfu.max(axis=0).values)
        db_scale = max(abs(db_max), abs(db_min))
        # if df is normalized then 0 will be at the center of the radar which is not what
        # we want. Let's shift the whole graph up.
        # if db_mean < 45:
        #    dfu += db_scale
        # print(db_min, db_max, db_mean, db_scale)
        # build 3 plots
        dbX = []
        dbY = []
        hzZ = []
        for hz in [500, 1000, 2000, 10000, 15000]:
            ihz = find_nearest_freq(freq, hz)
            if ihz is None:
                continue
            X, Y, Z = projection(anglelist, dfu.loc[ihz][dfu.columns != "Freq"], hz)
            # add to global variable
            dbX.append(X)
            dbY.append(Y)
            hzZ.append(Z)

        # normalise
        dbX = [v2 for v1 in dbX for v2 in v1]
        dbY = [v2 for v1 in dbY for v2 in v1]
        # print("dbX min={} max={}".format(np.array(dbX).min(), np.array(dbX).max()))
        # print("dbY min={} max={}".format(np.array(dbY).min(), np.array(dbY).max()))

        hzZ = [label(i2) for i1 in hzZ for i2 in i1]

        return db_mean, pd.DataFrame({"R": dbX, "Theta": dbY, "Freq": hzZ})

    fig = go.Figure()

    _, dbs_df = plot_radar_freq(anglelist, spl)

    for freq in np.unique(dbs_df["Freq"].values):
        slice = dbs_df.loc[dbs_df.Freq == freq]
        fig.add_trace(
            go.Scatterpolar(
                r=slice.R,
                theta=slice.Theta,
                dtheta=30,
                name=freq,
                marker_color=uniform_colors.get(freq, "black"),
                legendgroup="measurements",
                legendgrouptitle_text="Frequencies",
                legendrank=int(freq[:-3]),
            ),
        )

    fig.update_layout(
        # specs={"type": "polar"},
        width=600 * 2,
        height=800,
        polar=dict(
            radialaxis=dict(
                range=[-45, 5],
                dtick=5,
            ),
            angularaxis=dict(
                dtick=10,
                tickvals=list(range(0, 360, 10)),
                ticktext=[
                    "{}°".format(x) if abs(x) < 60 or not x % 30 else " "
                    for x in (list(range(0, 190, 10)) + list(range(-170, 0, 10)))
                ],
            ),
        ),
    )

    return fig


def plot_image(df):
    return None


def plot_summary(df):
    return None


def plot_compare_spinorama():
    return None


def plot_compare_graph():
    return None


def plot_compare_graph_regression():
    return None
