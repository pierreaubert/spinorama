#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-21 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
import zipfile

from docopt import docopt
import pandas as pd
import plotly.graph_objects as go

from generate_common import get_custom_logger, args2level


VERSION = 0.1


def compute_scale(speakers):
    scale = {}
    for speaker in speakers.values():
        def_measurement = speaker["default_measurement"]
        measurement = speaker["measurements"][def_measurement]
        if (
            "pref_rating" not in measurement.keys()
            or "estimates" not in measurement.keys()
        ):
            continue
        for key_score in ("pref_rating", "pref_rating_eq"):
            if key_score not in measurement.keys():
                continue
            for key_variable in measurement[key_score].keys():
                scale[key_variable] = (
                    min(
                        scale.get(key_variable, [+100, 0])[0],
                        measurement[key_score][key_variable],
                    ),
                    max(
                        scale.get(key_variable, [0, -100])[1],
                        measurement[key_score][key_variable],
                    ),
                )
    # print(scale)
    return scale


def scale_higher_is_better(key, val, scale):
    v_min = scale[key][0]
    v_max = scale[key][1]
    return (val - v_min) / (v_max - v_min)


def scale_lower_is_better(key, val, scale):
    v_min = scale[key][0]
    v_max = scale[key][1]
    return 1 - (val - v_min) / (v_max - v_min)


def print_radar(speaker, data, scale):
    def_measurement = data["default_measurement"]
    measurement = data["measurements"][def_measurement]
    if "pref_rating" not in measurement.keys() or "estimates" not in measurement.keys():
        return
    filename = "docs/{} {}/spider.jpg".format(data["brand"], data["model"])
    if pathlib.Path(filename).is_file():
        return
    graph_data = []
    for key in ("pref_rating", "pref_rating_eq"):
        pref_rating = measurement[key]
        r = []
        graph_data.append(
            {
                "type": "scatterpolar",
                "r": [
                    scale_higher_is_better(
                        "pref_score", pref_rating["pref_score"], scale
                    ),
                    scale_higher_is_better(
                        "pref_score_wsub", pref_rating["pref_score_wsub"], scale
                    ),
                    scale_lower_is_better("lfx_hz", pref_rating["lfx_hz"], scale),
                    scale_lower_is_better(
                        "nbd_on_axis", pref_rating["nbd_on_axis"], scale
                    ),
                    scale_lower_is_better(
                        "nbd_pred_in_room", pref_rating["nbd_pred_in_room"], scale
                    ),
                    scale_higher_is_better(
                        "sm_pred_in_room", pref_rating["sm_pred_in_room"], scale
                    ),
                ],
                "theta": [
                    "Score",
                    "Score w/sub",
                    "LFX",
                    "NBD ON",
                    "NBD PIR",
                    "SM PIR",
                ],
                "fill": "toself",
            }
        )

    graph_data[0]["name"] = "Default"
    graph_data[1]["name"] = "With EQ"

    layout = {
        "width": 400,
        "height": 300,
        "polar": {
            "radialaxis": {
                "visible": True,
                "range": [0, 1],
            },
        },
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
        },
        "margin": {
            "t": 0,
            "l": 0,
            "r": 0,
            "b": 0,
        },
    }
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(graph_data[0]))
    fig.add_trace(go.Scatterpolar(graph_data[1]))
    fig.update_layout(layout)
    fig.write_image(filename)


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="generate_radar.py version {:1.1f}".format(VERSION),
        options_first=True,
    )

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

    scale = compute_scale(jsmeta)

    for speaker in jsmeta.items():
        print_radar(speaker[0], speaker[1], scale)

    sys.exit(0)
