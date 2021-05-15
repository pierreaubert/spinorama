#                                                  -*- coding: utf-8 -*-
import altair as alt
import logging
import pandas as pd

from .graph import graph_regression_graph_simple


alt.data_transformers.disable_max_rows()
logger = logging.getLogger("spinorama")

short_map = {
    "On Axis": "ON",
    "Listening Window": "LW",
    "Estimated In-Room Response": "PIR",
    "Early Reflections": "ER",
    "Sound Power": "SP",
    "Early Reflections DI": "ERDI",
    "Sound Power DI": "SPDI",
    "Floor Bounce": "FB",
    "Ceiling Bounce": "CB",
    "Front Wall Bounce": "FWB",
    "Side Wall Bounce": "SWB",
    "Rear Wall Bounce": "RWB",
    "Total Early Reflection": "TER",
    "Front": "F",
    "Side": "S",
    "Rear": "R",
    "Total Horizontal": "TH",
    "Floor Reflections": "FR",
    "Ceiling Reflections": "CR",
    "Total Vertical": "TV",
}


def compact_df(dfi):
    dfu = pd.DataFrame()
    format1 = lambda x: round(x, 1)
    format4 = lambda x: round(x, 4)
    short = lambda f: short_map.get(f, f)
    dfu["F"] = dfi.Freq.map(format1)
    dfu["M"] = dfi.Measurements.map(short)
    dfu["G"] = dfi.dB.map(format4)
    dfu["Speaker"] = dfi.Speaker
    return dfu


nearest = alt.selection(
    type="single", nearest=True, on="mouseover", fields=["Freq"], empty="none"
)


def build_selections(df, speaker1, speaker2):
    speakers = sorted(df.Speaker.unique())
    input_dropdown1 = alt.binding_select(options=list(speakers))
    selection1 = alt.selection_single(
        fields=["Speaker"],
        bind=input_dropdown1,
        name="Select (continous line) ",
        init={"Speaker": speaker1},
    )
    input_dropdown2 = alt.binding_select(options=list(speakers))
    selection2 = alt.selection_single(
        fields=["Speaker"],
        bind=input_dropdown2,
        name="Select (dash line) ",
        init={"Speaker": speaker2},
    )
    selectorsMeasurements = alt.selection_multi(fields=["Measurements"], bind="legend")
    scales = alt.selection_interval(bind="scales")
    return selection1, selection2, selectorsMeasurements, scales


x_axis = alt.X(
    "Freq:Q",
    title="Frequency (Hz)",
    scale=alt.Scale(type="log", domain=[20, 20000], nice=False),
)

y_axis = alt.Y(
    "dB:Q",
    title="Sound Pressure (dB)",
    scale=alt.Scale(zero=False, domain=[-40, 10]),
)

color = alt.Color("Measurements", type="nominal", sort=None)

di_axis = (
    alt.Y(
        "dB:Q",
        title="DI",
        scale=alt.Scale(zero=False, domain=[-5, 45], nice=False),
        axis=alt.Axis(
            grid=True, tickCount=10, labelExpr="datum.value >15 ? null : datum.label"
        ),
    ),
)


def graph_compare_freq(df, graph_params, speaker1, speaker2):
    # df = compact_df(dfi)
    selection1, selection2, selectorsMeasurements, scales = build_selections(
        df, speaker1, speaker2
    )
    line = alt.Chart(df).encode(
        x_axis,
        y_axis,
        color,
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2)),
    )

    graph1 = line.mark_line().add_selection(selection1).transform_filter(selection1)
    graph2 = (
        line.mark_line(strokeDash=[4, 2])
        .add_selection(selection2)
        .transform_filter(selection2)
    )

    return (
        alt.layer(graph2, graph1)
        .add_selection(selectorsMeasurements)
        .add_selection(scales)
        .add_selection(nearest)
        .interactive()
    )


def graph_compare_cea2034(df, graph_params, speaker1, speaker2):
    selection1, selection2, selectorsMeasurements, _ = build_selections(
        df, speaker1, speaker2
    )
    scales1 = alt.selection_interval(bind="scales")
    scales2 = alt.selection_interval(bind="scales")
    scales3 = alt.selection_interval(bind="scales")
    scales4 = alt.selection_interval(bind="scales")
    di_yaxis = alt.Y(
        "dB:Q",
        title="Directivity Index (dB)",
        scale=alt.Scale(zero=False, nice=False, domain=[-5, 45]),
        axis=alt.Axis(
            grid=True, tickCount=10, labelExpr="datum.value >15 ? null : datum.label"
        ),
    )
    opacity = alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2))

    line = (
        alt.Chart(df)
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
        .encode(x=x_axis, y=y_axis, color=color, opacity=opacity)
    )
    di = (
        alt.Chart(df)
        .mark_line()
        .transform_filter(
            alt.FieldOneOfPredicate(
                field="Measurements", oneOf=["Early Reflections DI", "Sound Power DI"]
            )
        )
        .encode(x=x_axis, y=di_yaxis, color=color, opacity=opacity)
    )
    speaker1 = (
        (
            line.mark_line().add_selection(scales1)
            + di.mark_line().add_selection(scales2)
        )
        .resolve_scale(y="independent")
        .add_selection(selection1)
        .transform_filter(selection1)
    )
    speaker2 = (
        (
            line.mark_line(strokeDash=[4, 2]).add_selection(scales3)
            + di.mark_line(strokeDash=[4, 2], clip=True).add_selection(scales4)
        )
        .resolve_scale(y="independent")
        .add_selection(selection2)
        .transform_filter(selection2)
    )

    layers = (
        alt.layer(speaker1, speaker2)
        .add_selection(selectorsMeasurements)
        .add_selection(nearest)
        .properties(width=800, height=800 * 3 / 5)
        .interactive()
    )
    return layers


def graph_compare_freq_regression(df, graph_params, speaker1, speaker2):
    # df = compact_df(dfi)
    selection1, selection2, selectorsMeasurements, scales = build_selections(
        df, speaker1, speaker2
    )
    xaxis = alt.X("Freq:Q", scale=alt.Scale(type="log", domain=[20, 20000], nice=False))
    yaxis = alt.Y("dB:Q", scale=alt.Scale(zero=False, domain=[-40, 10]))

    line = alt.Chart(df).encode(
        xaxis,
        yaxis,
        color,
        opacity=alt.condition(selectorsMeasurements, alt.value(1), alt.value(0.2)),
    )

    # points = line.mark_circle(size=100).encode(
    #    opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
    #    tooltip=["Measurements", "Freq", "dB"],
    # )

    rules = (
        alt.Chart(df)
        .mark_rule(color="gray")
        .encode(x="Freq:Q")
        .transform_filter(nearest)
    )

    line1 = line.transform_filter(selection1)
    line2 = line.transform_filter(selection2)

    reg1 = graph_regression_graph_simple(line1, 80, 10000).mark_line()
    reg2 = graph_regression_graph_simple(line2, 80, 10000).mark_line(strokeDash=[4, 2])

    graph1 = line1.mark_line().add_selection(selection1)
    graph2 = line2.mark_line(strokeDash=[4, 2]).add_selection(selection2)

    return (
        alt.layer(graph2, reg2, graph1, reg1, rules)
        .add_selection(selectorsMeasurements)
        .add_selection(scales)
        .add_selection(nearest)
        .interactive()
    )
