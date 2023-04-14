#!/usr/bin/env python3
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

from docopt import docopt
import pandas as pd

from spinorama.constant_paths import CPATH_METADATA_JSON
from generate_common import get_custom_logger, args2level


VERSION = 0.4


def meta2df(meta):
    df_unroll = pd.DataFrame(
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
                    df_unroll.loc[count] = [i, k, v, ref, origin, brand]
                    count += 1
            if "pref_rating_eq" in measurement:
                ref = "EQ"
                for k, v in measurement["pref_rating_eq"].items():
                    df_unroll.loc[count] = [i, k, v, ref, origin, brand]
                    count += 1
    logger.info("meta2df %d generated data", count)
    # print(df_unroll)
    return df_unroll


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
        for i, pref, pref_eq, _ in sorted(results, key=lambda a: -a[2]["pref_score"]):
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
                    pref_eq.get("preamp_gain", 0.0),
                )
            )
    elif txt_format == "csv":
        print(
            '"Speaker", "NBD", "NBD", "LFX", "SM", "SCR", "NBD", "NBD", "LFX", "SM", "SCR", "SCR", "PRE"'
        )
        print(
            '"Speaker", "ON", "PIR", "Hz", "PIR", "ASR", "ON", "PIR", "Hz", "PIR", "EQ", "DIFF", "dB"'
        )
        for i, pref, pref_eq, _ in sorted(results, key=lambda a: -a[2]["pref_score"]):
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
                    pref_eq.get("preamp_gain", 0.0),
                )
            )


def main():
    print_what = None
    if args["--print"] is not None:
        print_what = args["--print"]

    # load all metadata from generated json file
    json_filename = CPATH_METADATA_JSON
    if not os.path.exists(json_filename):
        logger.error("Cannot find %s", json_filename)
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    logger.warning("Data %s loaded (%d speakers)!", json_filename, len(jsmeta))

    if print_what is not None:
        if print_what == "eq_txt":
            print_eq(jsmeta, "txt")
        elif print_what == "eq_csv":
            print_eq(jsmeta, "csv")
        else:
            logger.error('unkown print type either "eq_txt" or "eq_csv"')

    sys.exit(0)


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="./generate_stats.py version {:1.1f}".format(VERSION),
        options_first=True,
    )
    logger = get_custom_logger(level=args2level(args), duplicate=True)
    main()
