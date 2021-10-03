# -*- coding: utf-8 -*-
import altair as alt
import logging
import math
import numpy as np
import pandas as pd
from .compute_directivity import directivity_matrix
from .compute_normalize import resample
from .graph_contour import (
    compute_contour,
    compute_contour_smoothed,
    compute_directivity_deg,
)
from .graph_isobands import find_isobands
from . import graph_radar as radar

logger = logging.getLogger("spinorama")


alt.data_transformers.disable_max_rows()

nearest = alt.selection(
    type="single", nearest=True, on="mouseover", fields=["Freq"], empty="none"
)

graph_params_default = {
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


# https://help.tableau.com/current/pro/desktop/en-us/formatting_create_custom_colors.htm
# tablea10
colorsA = [
    "#17becf",
    "#bcbd22",
    "#7f7f7f",
    "#e377c2",
    "#8c564b",
    "#9467bd",
    "#d62728",
    "#2ca02c",
    "#ff7f0e",
    "#1f77b4",
]
colorsB = [
    "#4e79a7",
    "#59a14f",
    "#9c755f",
    "#f28e2b",
    "#edc948",
    "#bab0ac",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]
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

uniform_color_pair = {
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
}

uniform_color_domain = list(uniform_color_pair.keys())
uniform_color_range = list(uniform_color_pair.values())
uniform_scale = alt.Scale(domain=uniform_color_domain, range=uniform_color_range)


# only return the subpart which effictively is to be plotted
def filtered_scale(dfu):
    measurements = sorted(set(dfu.Measurements))
    filtered_domain = [d for d in uniform_color_domain if d in measurements]
    filtered_range = [
        uniform_color_pair[d] for d in uniform_color_domain if d in measurements
    ]
    return alt.Scale(domain=filtered_domain, range=filtered_range)


def graph_freq(dfu, graph_params):
    xmin = graph_params["xmin"]
    xmax = graph_params["xmax"]
    ymin = graph_params["ymin"]
    ymax = graph_params["ymax"]
    if xmax == xmin:
        logger.error("Graph configuration is incorrect: xmin==xmax")
    if ymax == ymin:
        logger.error("Graph configuration is incorrect: ymin==ymax")
    # add selectors
    selectorsMeasurements = alt.selection_multi(fields=["Measurements"], bind="legend")
    scales = alt.selection_interval(bind="scales")
    # main charts
    line = (
        alt.Chart(dfu)
        .mark_line()
        .encode(
            alt.X(
                "Freq:Q",
                title="Freqency (Hz)",
                scale=alt.Scale(type="log", base=10, nice=False, domain=[xmin, xmax]),
                axis=alt.Axis(format="~s"),
            ),
            alt.Y(
                "dB:Q",
                title="Sound Pressure (dB)",
                scale=alt.Scale(zero=False, domain=[ymin, ymax]),
            ),
            alt.Color(
                "Measurements", scale=filtered_scale(dfu), type="nominal", sort=None
            ),
            opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2)),
        )
        .properties(width=graph_params["width"], height=graph_params["height"])
    )

    circle = (
        alt.Chart(dfu)
        .mark_circle(size=100)
        .encode(
            alt.X("Freq:Q", scale=alt.Scale(type="log", domain=[xmin, xmax])),
            alt.Y("dB:Q", scale=alt.Scale(zero=False, domain=[ymin, ymax])),
            alt.Color(
                "Measurements", scale=filtered_scale(dfu), type="nominal", sort=None
            ),
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            tooltip=["Measurements", "Freq", "dB"],
        )
    )  # .transform_calculate(Freq=f'format(datum.Freq, ".0f")', dB=f'format(datum.dB, ".1f")')
    # assemble elements together
    spin = (
        alt.layer(circle, line)
        .add_selection(selectorsMeasurements)
        .add_selection(scales)
        .add_selection(nearest)
    )
    return spin


def graph_spinorama(dfu, graph_params):
    xmin = graph_params["xmin"]
    xmax = graph_params["xmax"]
    ymin = graph_params["ymin"]
    ymax = graph_params["ymax"]
    if xmax == xmin:
        logger.error("Graph configuration is incorrect: xmin==xmax")
    if ymax == ymin:
        logger.error("Graph configuration is incorrect: ymin==ymax")
    # add selectors
    selectorsMeasurements = alt.selection_multi(fields=["Measurements"], bind="legend")
    scales = alt.selection_interval(bind="scales")
    scales_di = alt.selection_interval(bind="scales")
    # main charts
    xaxis = alt.X(
        "Freq:Q",
        title="Freqency (Hz)",
        scale=alt.Scale(type="log", base=10, nice=False, domain=[xmin, xmax]),
        axis=alt.Axis(format="~s"),
    )
    yaxis = alt.Y(
        "dB:Q",
        title="Sound Pressure (dB)",
        scale=alt.Scale(zero=False, domain=[ymin, ymax]),
    )
    # why -10?
    di_yaxis = alt.Y(
        "dB:Q",
        title="Sound Pressure DI (dB)",
        scale=alt.Scale(zero=False, nice=False, domain=[-5, ymax - ymin - 5]),
        axis=alt.Axis(
            grid=True, tickCount=10, labelExpr="datum.value >15 ? null : datum.label"
        ),
    )
    color = alt.Color(
        "Measurements", scale=filtered_scale(dfu), type="nominal", sort=None
    )
    opacity = alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))

    line = (
        alt.Chart(dfu)
        .mark_line()
        .transform_filter(
            alt.FieldOneOfPredicate(
                field="Measurements",
                oneOf=[
                    "On Axis",
                    "Listening Window",
                    "Early Reflections",
                    "Sound Power",
                ],
            )
        )
        .encode(x=xaxis, y=yaxis, color=color, opacity=opacity)
    )

    circle = (
        alt.Chart(dfu)
        .mark_circle(size=100)
        .transform_filter(
            alt.FieldOneOfPredicate(
                field="Measurements",
                oneOf=[
                    "On Axis",
                    "Listening Window",
                    "Early Reflections",
                    "Sound Power",
                ],
            )
        )
        .encode(
            x=xaxis,
            y=yaxis,
            color=color,
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            tooltip=["Measurements", "Freq", "dB"],
        )
    )

    di = (
        alt.Chart(dfu)
        .mark_line()
        .transform_filter(
            alt.FieldOneOfPredicate(
                field="Measurements", oneOf=["Early Reflections DI", "Sound Power DI"]
            )
        )
        .encode(x=xaxis, y=di_yaxis, color=color, opacity=opacity)
    )

    circle_di = (
        alt.Chart(dfu)
        .mark_circle(size=100)
        .transform_filter(
            alt.FieldOneOfPredicate(
                field="Measurements", oneOf=["Early Reflections DI", "Sound Power DI"]
            )
        )
        .encode(
            x=xaxis,
            y=di_yaxis,
            color=color,
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            tooltip=["Measurements", "Freq", "dB"],
        )
    )

    # assemble elements together
    spin = (
        alt.layer(
            (circle + line).add_selection(scales),
            (circle_di + di).add_selection(scales_di),
        )
        .resolve_scale(y="independent")
        .add_selection(selectorsMeasurements)
        .add_selection(nearest)
        .properties(width=graph_params["width"], height=graph_params["height"])
    )

    return spin


def graph_empty(freq_min, freq_max, angle_min, angle_max):
    # empty graph but with axis
    empty = pd.DataFrame({"Freq", "Angle"})
    isoTicks = [-180 + 30 * i for i in range(0, 13)]
    return (
        alt.Chart(empty)
        .mark_point(clip=True)
        .encode(
            x=alt.X(
                "x:Q",
                scale=alt.Scale(type="log", nice=False, domain=[freq_min, freq_max]),
                axis=alt.Axis(format="s", title="Frequency (Hz)"),
            ),
            y=alt.Y(
                "y:Q",
                scale=alt.Scale(nice=False, domain=[angle_min, angle_max]),
                axis=alt.Axis(
                    values=isoTicks, title="Angle (deg)", labelExpr="datum.value+'°'"
                ),
            ),
        )
    )


def graph_contour_common(af, am, az, graph_params):
    try:
        width = graph_params["width"]
        height = graph_params["height"]
        # more interesting to look at -3/0 range
        speaker_scale = None
        if "contour_scale" in graph_params.keys():
            speaker_scale = graph_params["contour_scale"]
        else:
            speaker_scale = contour_params_default["contour_scale"]
        #
        colormap = "veridis"
        if "colormap" in graph_params:
            colormap = graph_params["colormap"]
        else:
            colormap = contour_params_default["colormap"]

        # flatten and build a Frame
        freq = af.ravel()
        freq_min = np.min(freq)
        angle = am.ravel()
        db = az.ravel()
        if (freq.size != angle.size) or (freq.size != db.size):
            logger.debug(
                "Contour: Size freq={:d} angle={:d} db={:d}".format(
                    freq.size, angle.size, db.size
                )
            )
            return None

        source = pd.DataFrame({"Freq": freq, "Angle": angle, "dB": db})

        # tweak ratios and sizes
        chart = alt.Chart(source)
        # classical case is 200 points for freq and 36 or 72 measurements on angles
        # check that width is a multiple of len(freq)
        # same for angles

        # build and return graph
        logger.debug("w={0} h={1}".format(width, height))
        if width / source.shape[0] < 2 and height / source.shape[1] < 2:
            chart = chart.mark_point()
        else:
            chart = chart.mark_rect()

        chart = chart.transform_filter("datum.Freq>400").encode(
            alt.X("Freq:O", axis=None),
            alt.Y("Angle:O", title="Angle (deg.)", axis=None, sort=None),
            alt.Color(
                "dB:Q",
                scale=alt.Scale(scheme=colormap, domain=speaker_scale, nice=True),
            ),
        )

        # add axis and 3 lines (0, +/-6dB)
        dir_deg_p, dir_deg_m, _ = compute_directivity_deg(af, am, az)
        lines = graph_directivity_lines(freq_min, dir_deg_p, dir_deg_m, True)
        axis = graph_empty(400, 20000, -180, 180)

        return (
            (chart + lines + axis)
            .resolve_scale(x="independent", y="independent")
            .properties(width=width, height=height)
        )
    except KeyError as ke:
        logger.warning("Failed with {0}".format(ke))
        return None


def graph_contour(df, graph_params):
    af, am, az = compute_contour(df)
    if af is None or am is None or az is None:
        logger.error("contour is None")
        return None
    return graph_contour_common(af, am, az, graph_params)


def graph_isoband(df, isoband_params):
    af, am, az = compute_contour(df.loc[df.Freq > isoband_params["xmin"]])
    if af is None or am is None or az is None:
        logger.error("contour is None")
        return None

    graph_width = isoband_params["width"]
    graph_height = isoband_params["height"]
    if "bands" in isoband_params:
        bands = isoband_params["bands"]
    else:
        bands = isoband_params_default["bands"]
    freq_min = isoband_params["xmin"]
    freq_max = isoband_params["xmax"]

    logger.debug(
        "w {0} h {1} fq=[{2},{3}]".format(graph_width, graph_height, freq_min, freq_max)
    )

    dir_deg_p, dir_deg_m, _ = compute_directivity_deg(af, am, az)
    # print('debug {} {}'.format(dir_deg_p, dir_deg_m))
    lines = graph_directivity_lines(freq_min, dir_deg_p, dir_deg_m)

    def transform_log(x, y):
        return np.log10(x) * graph_width / 172

    def transform_radian(x, y):
        return y / 180 * math.pi * graph_height / 360

    df_iso = find_isobands(af, am, az.T, bands, transform_log, transform_radian)
    # color_legend = [
    #    "[{0}, {1}]".format(bands[i], bands[i + 1]) for i in range(0, len(bands) - 1)
    # ] + [">{0}".format(bands[-1])]
    color_range = [
        "black",
        "blue",
        "steelblue",
        "green",
        "yellow",
        "orange",
        "red",
        "white",
    ]

    isobands = (
        alt.Chart(alt.Data(values=df_iso["features"]))
        .mark_geoshape(stroke="red", strokeWidth=0)
        .encode(
            alt.Color(
                "properties.z_low:O",
                scale=alt.Scale(domain=bands, range=color_range),
                legend=alt.Legend(title="Relative dB SPL"),
            )
        )
        .project("identity")
    )
    axis = graph_empty(freq_min, freq_max, -180, 180)
    return (
        alt.layer(isobands, axis, lines)
        .resolve_scale(x="independent", y="independent")
        .properties(width=graph_width, height=graph_height)
    )


def graph_contour_smoothed(df, graph_params):
    af, am, az = compute_contour_smoothed(df)
    if af is None or am is None or az is None:
        logger.warning("contour is None")
        return None
    if np.max(np.abs(az)) == 0.0:
        logger.warning("contour is flat")
        return None
    return graph_contour_common(af, am, az, graph_params)


def graph_radar(df_in, graph_params):
    dfu = df_in.copy()
    # which part of the circle do we plot?
    angle_min, angle_max = radar.angle_range(dfu.columns)
    if angle_min is None or angle_max is None or angle_max == angle_min:
        logger.debug("Angle is empty")
        return None
    # do we have +10 or +5 deg measurements?
    delta = 10
    if (len(dfu.columns) - 1) / 36 == 2:
        delta = 5
    anglelist = list(range(angle_min, angle_max + delta, delta))
    # print(angle_min, angle_max)
    # print(dfu.columns)
    # print(anglelist)

    # display some curves
    _, dbs_df = radar.plot(anglelist, dfu)

    # normalize all
    radius = 1

    # build a grid
    grid_df = radar.grid_grid(radius, anglelist)
    circle_df, circle_text = radar.grid_circle(radius, anglelist, 100)
    text_df = radar.grid_text(radius, anglelist)

    grid = (
        alt.Chart(grid_df)
        .mark_line()
        .encode(
            alt.Latitude("x:Q"),
            alt.Longitude("y:Q"),
            size=alt.value(1),
            opacity=alt.value(0.2),
        )
        .project(type="azimuthalEquidistant", rotate=[0, 0, 90])
    )

    circle = (
        alt.Chart(circle_df)
        .mark_line()
        .encode(
            alt.Latitude("x:Q"),
            alt.Longitude("y:Q"),
            alt.Color("value:Q", legend=None),
            size=alt.value(0.5),
        )
        .project(type="azimuthalEquidistant", rotate=[0, 0, 90])
    )

    legend = (
        alt.Chart(circle_text)
        .mark_text(dx=15, dy=-10)
        .encode(alt.Latitude("x:Q"), alt.Longitude("y:Q"), text="text:O")
        .project(type="azimuthalEquidistant", rotate=[0, 0, 90])
    )

    text = (
        alt.Chart(text_df)
        .mark_text()
        .encode(alt.Latitude("x:Q"), alt.Longitude("y:Q"), text="text:O")
        .project(type="azimuthalEquidistant", rotate=[0, 0, 90])
    )

    dbs = (
        alt.Chart(dbs_df)
        .mark_line(thickness=3)
        .encode(
            alt.Latitude("x:Q"),
            alt.Longitude("y:Q"),
            alt.Color("Freq:N", sort=None),
        )
        .project(type="azimuthalEquidistant", rotate=[0, 0, 90])
        .properties(width=graph_params["width"], height=graph_params["height"])
    )

    # return (dbs | grid) & (circle+legend | text) & (grid+circle+legend+text+dbs)
    return grid + circle + legend + text + dbs


def graph_directivity_matrix(dfu, graph_params):
    splH = dfu["SPL Horizontal_unmelted"]
    splV = dfu["SPL Vertical_unmelted"]

    if splH.shape != splV.shape:
        logger.debug("shapes do not match {0} and {1}".format(splH.shape, splV.shape))
        return None

    splH = resample(splH, 300).reset_index()
    splV = resample(splV, 300).reset_index()

    x, y, z = directivity_matrix(splH, splV)

    source = pd.DataFrame({"x": x.ravel(), "y": y.ravel(), "z": z.melt().value})

    matrix = (
        alt.Chart(source)
        .transform_filter("datum.x>=500 & datum.y>=500")
        .mark_rect()
        .encode(
            x=alt.X("x:O", axis=None),
            y=alt.Y("y:O", axis=None),
            color=alt.Color(
                "z:Q",
                scale=alt.Scale(
                    scheme="spectral", domain=np.linspace(-0.15, 0.15, 50), nice=True
                ),
            ),
        )
    )
    empty = pd.DataFrame({"Freq", "Angle"})
    axis = (
        alt.Chart(empty)
        .mark_point(clip=True)
        .encode(
            x=alt.X(
                "x:Q",
                scale=alt.Scale(type="log", nice=False, domain=[500, 20000]),
                title="Frequency (Hz)",
            ),
            y=alt.Y(
                "y:Q",
                scale=alt.Scale(type="log", nice=False, domain=[500, 20000]),
                title="Frequency (Hz)",
            ),
        )
    )
    return (matrix + axis).properties(width=800, height=800)


def graph_regression_graph(graph, freq_start, freq_end, withBands=True):

    # regression line
    reg = graph.transform_filter(
        "datum.Freq>{0} & datum.Freq<{1}".format(freq_start, freq_end)
    ).transform_regression(method="log", on="Freq", regression="dB", extent=[20, 20000])

    if withBands:
        # +/- 3dB
        reg3 = (
            reg.transform_calculate(dBm3=alt.datum.dB - 3)
            .transform_calculate(dBp3=alt.datum.dB + 3)
            .transform_calculate(text='"Band ±3dB"')
        )

        # +/- 1.5dB
        reg1 = (
            reg.transform_calculate(dBm1=alt.datum.dB - 1.5)
            .transform_calculate(dBp1=alt.datum.dB + 1.5)
            .transform_calculate(text='"Band ±1.5dB"')
        )

        # band at +/- 3dB
        err3 = reg3.mark_area(opacity=0.06).encode(
            x=alt.X("Freq:Q"), y=alt.Y("dBm3:Q"), y2=alt.Y2("dBp3:Q")
        )

        # band at +/- 1.5dB
        err1 = reg1.mark_area(opacity=0.12).encode(
            x=alt.X("Freq:Q"), y=alt.Y("dBm1:Q"), y2=alt.Y2("dBp1:Q")
        )

    # line
    line = (
        reg.transform_calculate(text='"Linear Regression"')
        .mark_line(color="firebrick")
        .encode(
            x=alt.X("Freq:Q"),
            y=alt.Y("dB:Q", axis=alt.Axis(title="Sound Pressure (dB)")),
            color=alt.Color(
                "text:O",
                scale=alt.Scale(
                    domain=["Linear Regression", "Band ±3dB", "Band ±1.5dB"],
                    range=["firebrick", "blue", "blue"],
                ),
                legend=alt.Legend(title="Regression"),
            ),
        )
    )

    if withBands:
        return err3 + err1 + line
    return line


def graph_regression(source, freq_start, freq_end):
    return graph_regression_graph(alt.Chart(source), freq_start, freq_end)


def graph_regression_graph_simple(graph, freq_start, freq_end):
    reg = (
        graph.transform_filter(
            "datum.Freq>{0} & datum.Freq<{1}".format(freq_start, freq_end)
        )
        .transform_regression(
            method="log", on="Freq", regression="dB", extent=[20, 20000]
        )
        .encode(alt.X("Freq:Q"), alt.Y("dB:Q"), color=alt.value("red"))
    )
    return reg


def graph_directivity_lines(freq_min, angle_p, angle_m, onlyZero=False):

    x_axis = alt.X(
        "Freq:Q",
        axis=None,
        scale=alt.Scale(type="log", domain=[freq_min, 20000], nice=False),
    )
    y_axis = alt.Y(
        "Angle:Q", axis=None, scale=alt.Scale(domain=[-180, 180], nice=False)
    )
    color = alt.value("white")
    size = alt.value(3)

    line_source = pd.DataFrame(
        {"Freq": [freq_min, 20000], "Angle": [0, 0], "dB": [0, 0]}
    )
    line_0 = (
        alt.Chart(line_source)
        .mark_line()
        .encode(x=x_axis, y=y_axis, color=color, size=size)
    )
    if onlyZero:
        return line_0

    line_source_p = pd.DataFrame(
        {"Freq": [freq_min, 20000], "Angle": [angle_p, angle_p], "dB": [+6, +6]}
    )
    line_source_m = pd.DataFrame(
        {"Freq": [freq_min, 20000], "Angle": [angle_m, angle_m], "dB": [-6, -6]}
    )

    line_p = (
        alt.Chart(line_source_p)
        .mark_line()
        .encode(x=x_axis, y=y_axis, color=color, size=size)
    )
    line_m = (
        alt.Chart(line_source_m)
        .mark_line()
        .encode(x=x_axis, y=y_axis, color=color, size=size)
    )

    return line_0 + line_p + line_m
