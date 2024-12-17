#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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
import sys
import pathlib

# from pprint import pprint


from docopt import docopt
import plotly.graph_objects as go

from spinorama.pict import write_multiformat


from generate_common import (
    get_custom_logger,
    args2level,
    cache_load,
    custom_ray_init,
    find_metadata_file,
)

from spinorama.constant_paths import CPATH_DOCS_SPEAKERS, CPATH_DATAS_EQ
from spinorama.filter_scores import scores_apply_filter
from spinorama.load_rew_eq import parse_eq_iir_rews

VERSION = 0.2


def compute_scale(speakers):
    scale = {}
    for speaker in speakers.values():
        def_measurement = speaker["default_measurement"]
        measurement = speaker["measurements"][def_measurement]
        if "pref_rating" not in measurement or "estimates" not in measurement:
            continue
        for key_score in ("pref_rating", "pref_rating_eq"):
            if key_score not in measurement:
                continue
            for key_variable in measurement[key_score]:
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


def build_scatterplot(pref_rating, scale, name):
    opacity = 0.5
    if name == "Reference":
        opacity = 1.0
    return {
        "type": "scatterpolar",
        "r": [
            scale_higher_is_better("pref_score", pref_rating["pref_score"], scale),
            scale_higher_is_better("pref_score_wsub", pref_rating["pref_score_wsub"], scale),
            scale_lower_is_better("lfx_hz", pref_rating["lfx_hz"], scale),
            scale_lower_is_better("nbd_on_axis", pref_rating["nbd_on_axis"], scale),
            scale_lower_is_better("nbd_pred_in_room", pref_rating["nbd_pred_in_room"], scale),
            scale_higher_is_better("sm_pred_in_room", pref_rating["sm_pred_in_room"], scale),
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
        "opacity": opacity,
        "name": name,
    }


def print_radar(meta_data, scale, speaker_data):
    def_measurement = meta_data["default_measurement"]
    measurement = meta_data["measurements"][def_measurement]
    if "pref_rating" not in measurement or "estimates" not in measurement:
        return
    filename = "{}/{} {}/spider_large.png".format(
        CPATH_DOCS_SPEAKERS, meta_data["brand"], meta_data["model"]
    )
    # TODO: to add check for dependancies
    if pathlib.Path(filename).is_file():
        return
    graph_data = []
    pref_rating = measurement["pref_rating"]
    # pprint(pref_rating)
    graph_data.append(build_scatterplot(pref_rating, scale, "Reference"))
    for eq_key in meta_data["eqs"]:
        if eq_key not in ("autoeq", "autoeq_lw", "autoeq_score"):
            continue
        if (
            "autoeq" in meta_data["eqs"]
            and "autoeq_score" in meta_data["eqs"]
            and eq_key == "autoeq_score"
        ):
            continue
        # load eq
        eq_filename = "{}/{} {}/iir-{}.txt".format(
            CPATH_DATAS_EQ, meta_data["brand"], meta_data["model"], eq_key.replace("_", "-")
        )
        # print(eq_filename)
        iir = parse_eq_iir_rews(eq_filename, 48000)
        # print(iir)
        # compute pref_rating and estimates
        # print(speaker_data[measurement["origin"]][def_measurement].keys())
        _, _, pref_rating_eq = scores_apply_filter(
            speaker_data[measurement["origin"]][def_measurement], iir
        )
        # pprint(pref_rating_eq)
        # add results to data
        pretty_name = {
            "autoeq_lw": "autoEQ LW",
            "autoeq": "autoEQ Score",
        }
        graph_data.append(build_scatterplot(pref_rating_eq, scale, pretty_name.get(eq_key, eq_key)))

    layout = {
        "width": 800,
        "height": 600,
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
            "t": 20,
            "l": 20,
            "r": 20,
            "b": 20,
        },
    }
    fig = go.Figure()
    for gd in graph_data:
        fig.add_trace(go.Scatterpolar(gd))
    fig.update_layout(layout)
    write_multiformat(fig, filename, False)


def main(args):
    custom_ray_init(args)
    # load all speaker data
    df_speaker = cache_load(
        filters={
            #            "speaker_name": "Alcons Audio RR12",
        },
        smoke_test=False,
        level="INFO",
    )

    # load all metadata from generated json file
    json_filename, eq_filename = find_metadata_file()
    if json_filename is None:
        logger.error("Cannot find metadata file, did you ran generate_meta.py ?")
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    eqmeta = None
    with open(eq_filename, "r") as f:
        eqmeta = json.load(f)
        for k in jsmeta:
            if k in eqmeta:
                if "eqs" in eqmeta[k]:
                    jsmeta[k]["eqs"] = eqmeta[k]["eqs"]
                else:
                    logger.info('"eqs" is not in eqmeta for %s', k)

    logger.warning("Data %s loaded (%d speakers)!", json_filename, len(jsmeta))

    scale = compute_scale(jsmeta)

    for speaker in jsmeta.items():
        speaker_name = "{} {}".format(speaker[1]["brand"], speaker[1]["model"])
        if speaker_name not in df_speaker:
            continue
        speaker_data = df_speaker[speaker_name]
        print_radar(speaker[1], scale, speaker_data)

    sys.exit(0)


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="generate_radar.py version {:1.1f}".format(VERSION),
        options_first=True,
    )
    logger = get_custom_logger(level=args2level(args), duplicate=True)
    main(args)
