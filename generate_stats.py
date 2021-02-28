#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

"""
usage: generate_stats.py [--help] [--version] [--dev] [--print=<what>]\
 [--sitedev=<http>]  [--log-level=<level>]

Options:
  --help            display usage()
  --version         script version number
  --print=<what>    print information. Options are 'eq_txt' or 'eq_csv'
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import json
import os
import sys
import pathlib
from docopt import docopt
import pandas as pd
import altair as alt


from generate_common import get_custom_logger, args2level


def meta2df(meta):
    df = pd.DataFrame(
        {
            "speaker": [],
            "param": [],
            "value": [],
            "ref": [],
            "origin": [],
            "brand": [],
        }
    )
    count = 0
    for i in meta:
        speaker = meta[i]
        brand = speaker.get("brand", "unknown")
        measurements = speaker["measurements"]
        for version, measurement in measurements.items():
            origin = measurement["origin"]
            if origin[1:5] == "endor":
                origin = "Vendor"
            if version not in ("asr", "vendor", "princeton"):
                origin = "{} - {}".format(origin, version)
            if "pref_rating" in measurement:
                ref = "Origin"
                for k, v in measurement["pref_rating"].items():
                    logger.debug(
                        "{} {} {} {} {} {}".format(i, k, v, ref, origin, brand)
                    )
                    df.loc[count] = [i, k, v, ref, origin, brand]
                    count += 1
            if "pref_rating_eq" in measurement:
                ref = "EQ"
                for k, v in measurement["pref_rating_eq"].items():
                    logger.debug(
                        "{} {} {} {} {} {}".format(i, k, v, ref, origin, brand)
                    )
                    df.loc[count] = [i, k, v, ref, origin, brand]
                    count += 1
    logger.info("meta2df {0} generated data".format(count))
    # print(df)
    return df


def print_eq(speakers, txt_format):
    results = []
    for i in speakers:
        speaker = speakers[i]
        measurements = speaker["measurements"]
        eq = speaker.get("eq", None)
        for key, measurement in measurements.items():
            pref = measurement.get("pref_rating", None)
            pref_eq = measurement.get("pref_rating_eq", None)
            if pref is not None and pref_eq is not None:
                name = i
                if key not in ("asr", "princeton", "eac", "vendor", "misc"):
                    name = "{} ({})".format(i, key)
                results.append((name, pref, pref_eq, eq))

    if txt_format == "txt":
        print(
            "                                           | NBD  NBD  LFX   SM |  SCR | NBD  NBD  LFX   SM | SCR |  SCR|Pre AMP"
        )
        print(
            "Speaker                                    |  ON  PIR   Hz  PIR |  ASR |  ON  PIR   Hz  PIR |  EQ | DIFF|     dB"
        )
        print(
            "-------------------------------------------+--------------------+------+--------------------+-----+-----+-------"
        )
        for i, pref, pref_eq, eq in sorted(results, key=lambda a: -a[2]["pref_score"]):
            print(
                "{0:42s} | {1:0.2f} {2:0.2f} {3:3.0f} {4:0.2f} | {5:+1.1f} | {6:0.2f} {7:0.2f} {8:3.0f} {9:0.2f} | {10:1.1f} | {11:+1.1f} |  {12:+1.1f}".format(
                    i,
                    pref["nbd_on_axis"],
                    pref["nbd_pred_in_room"],
                    pref["lfx_hz"],
                    pref["sm_pred_in_room"],
                    pref["pref_score"],
                    pref_eq["nbd_on_axis"],
                    pref_eq["nbd_pred_in_room"],
                    pref_eq["lfx_hz"],
                    pref_eq["sm_pred_in_room"],
                    pref_eq["pref_score"],
                    pref_eq["pref_score"] - pref["pref_score"],
                    eq["preamp_gain"],
                )
            )
    elif txt_format == "csv":
        print(
            '"Speaker", "NBD", "NBD", "LFX", "SM", "SCR", "NBD", "NBD", "LFX", "SM", "SCR", "SCR", "PRE"'
        )
        print(
            '"Speaker", "ON", "PIR", "Hz", "PIR", "ASR", "ON", "PIR", "Hz", "PIR", "EQ", "DIFF", "dB"'
        )
        for i, pref, pref_eq, eq in sorted(results, key=lambda a: -a[2]["pref_score"]):
            print(
                '"{0}", {1:0.2f}, {2:0.2f}, {3:3.0f}, {4:0.2f}, {5:+1.1f}, {6:0.2f}, {7:0.2f}, {8:3.0f}, {9:0.2f}, {10:+1.1f}, {11:+1.1f}, {12:+1.1f}'.format(
                    i,
                    pref["nbd_on_axis"],
                    pref["nbd_pred_in_room"],
                    pref["lfx_hz"],
                    pref["sm_pred_in_room"],
                    pref["pref_score"],
                    pref_eq["nbd_on_axis"],
                    pref_eq["nbd_pred_in_room"],
                    pref_eq["lfx_hz"],
                    pref_eq["sm_pred_in_room"],
                    pref_eq["pref_score"],
                    pref_eq["pref_score"] - pref["pref_score"],
                    eq["preamp_gain"],
                )
            )


def generate_stats(meta):
    df = meta2df(meta)

    pref_score = df.loc[(df.param == "pref_score")].reset_index()
    pref_score_wsub = df.loc[(df.param == "pref_score_wsub")].reset_index()
    brand = df.loc[(df.param == "brand")].reset_index()
    lfx_hz = df.loc[(df.param == "lfx_hz")].reset_index()
    nbd_on = df.loc[(df.param == "nbd_on_axis")].reset_index()
    nbd_pir = df.loc[(df.param == "nbd_pred_in_room")].reset_index()
    sm_pir = df.loc[(df.param == "sm_pred_in_room")].reset_index()

    spread_score = (
        alt.Chart(pref_score)
        .mark_circle(size=100)
        .encode(
            x=alt.X("speaker", sort="y", axis=None),
            y=alt.Y("value", title="Preference Score"),
            color=alt.Color("ref"),
            tooltip=["speaker", "origin", "value", "ref"],
        )
        .properties(
            width=1024,
            height=300,
            title="Speakers sorted by Preference Score (move your mouse over a point to get data)",
        )
    )

    spread_score_wsub = (
        alt.Chart(pref_score_wsub)
        .mark_circle(size=100)
        .encode(
            x=alt.X("speaker", sort="y", axis=None),
            y=alt.Y("value", title="Preference Score w/Sub"),
            color=alt.Color("ref"),
            tooltip=["speaker", "origin", "value", "ref"],
        )
        .properties(
            width=1024,
            height=300,
            title="Speakers sorted by Preference Score with a Subwoofer (move your mouse over a point to get data)",
        )
    )

    distribution1 = (
        alt.Chart(pref_score)
        .mark_bar()
        .encode(
            x=alt.X("value:Q", bin=True, title="Preference Score"),
            y=alt.Y("count()", title="Count"),
        )
        .properties(width=450, height=300)
    )

    distribution2 = (
        alt.Chart(pref_score_wsub)
        .mark_bar()
        .encode(
            x=alt.X("value:Q", bin=True, title="Preference Score w/Sub"),
            y=alt.Y("count()", title="Count"),
        )
        .properties(width=450, height=300)
    )

    distribution = distribution1 | distribution2

    source = pd.DataFrame(
        {
            "speaker": pref_score.speaker,
            "pref_score": pref_score.value,
            "lfx_hz": lfx_hz.value,
            "nbd_on": nbd_on.value,
            "nbd_pir": nbd_pir.value,
            "sm_pir": sm_pir.value,
            "brand": brand.value,
        }
    )

    logger.debug(source)

    graphs = {}
    for g in ("lfx_hz", "nbd_pir", "nbd_on", "sm_pir"):
        data = (
            alt.Chart(source)
            .mark_point()
            .encode(
                x=alt.X("{0}:Q".format(g)),
                y=alt.Y("pref_score:Q", title="Preference Score"),
                color=alt.Color("brand:N"),
                tooltip=["speaker", g, "pref_score"],
            )
        )
        graphs[g] = data + data.transform_regression(g, "pref_score").mark_line()

    correlation = (graphs["lfx_hz"] | graphs["nbd_on"]) & (
        graphs["nbd_pir"] | graphs["sm_pir"]
    )

    # used in website
    filedir = "docs/stats"
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)

    for graph, name in (
        (correlation, "correlation"),
        (distribution, "distribution"),
        (spread_score, "spread_score"),
        (spread_score_wsub, "spread_score_wsub"),
    ):
        filename = "{0}/{1}.json".format(filedir, name)
        graph.save(filename)

    # used in book
    filedir = "book/stats"
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)

    for graph in graphs:
        graph_name = "{0}/{1}.png".format(filedir, graph)
        graphs[graph].save(graph_name)

    for graph, name in (
        (distribution1, "distribution1"),
        (distribution2, "distribution2"),
        (spread_score, "spread_score"),
        # (spread_score_wsub, 'spread_score_wsub'),
    ):
        filename = "{0}/{1}.png".format(filedir, name)
        graph.save(filename)

    return 0


if __name__ == "__main__":
    args = docopt(__doc__, version="generate_stats.py version 0.3", options_first=True)

    print_what = None
    if args["--print"] is not None:
        print_what = args["--print"]

    level = args2level(args)
    logger = get_custom_logger(True)
    logger.setLevel(level)

    # load all metadata from generated json file
    json_filename = "./docs/assets/metadata.json"
    if not os.path.exists(json_filename):
        logger.error("Cannot find {0}".format(json_filename))
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    logger.warning("Data {0} loaded ({1} speakers)!".format(json_filename, len(jsmeta)))

    if print_what is not None:
        if print_what == "eq_txt":
            print_eq(jsmeta, "txt")
        elif print_what == "eq_csv":
            print_eq(jsmeta, "csv")
        else:
            logger.error('unkown print type either "eq_txt" or "eq_csv"')
    else:
        generate_stats(jsmeta)

    sys.exit(0)
