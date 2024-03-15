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
 [--sitedev=<http>]  [--log-level=<level>] [--push=<KEY>]

Options:
  --help            display usage()
  --version         script version number
  --print=<what>    print information. Options are 'eq_txt' or 'eq_csv'
  --push=<KEY>      push data to Google sheet
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import json
import sys

from docopt import docopt

from generate_common import get_custom_logger, args2level, find_metadata_file


VERSION = 0.5


def speakers2results(speakers):
    results = []
    for i in speakers:
        speaker = speakers[i]
        price = speaker.get("price", None)
        amount = speaker.get("amount", None)
        if price is not None and len(price) > 0 and amount is not None and amount == "pair":
            price = "{:d}".format(int(price) // 2)
        shape = speaker.get("shape", None)
        energy = speaker.get("type", None)
        default_measurement = speaker["default_measurement"]
        measurements = speaker["measurements"]
        eq = None
        eqs = speaker.get("eqs", None)
        if eqs:
            default_eq = speaker.get("default_eq", None)
            if default_eq:
                eq = eqs[default_eq]
        for key, measurement in measurements.items():
            pref = measurement.get("pref_rating", {})
            pref_eq = measurement.get("pref_rating_eq", {})
            estimates = measurement.get("estimates", {})
            estimates_eq = measurement.get("estimates_eq", {})
            data_format = measurement.get("format", "")
            quality = measurement.get("quality", "")
            specifications = measurement.get("specifications", {})
            sensitivity_data = speaker.get("sensitivity", {})
            sensitivity = sensitivity_data.get("sensitivity_1m")
            if quality == "" and data_format == "klippel":
                quality = "high"
            is_default = key == default_measurement
            results.append(
                (
                    i,
                    key,
                    is_default,
                    price,
                    shape,
                    energy,
                    sensitivity,
                    pref,
                    pref_eq,
                    eq,
                    data_format,
                    quality,
                    estimates,
                    estimates_eq,
                    specifications,
                )
            )
    return results


def print_eq(speakers, txt_format, push_key):
    results = speakers2results(speakers)
    header = []
    if txt_format == "txt":
        header.append(
            "                                                     | Price Shape           Type    Sensitivity | DataFormat       Quality |   -3dB  -6dB  Dev   NBD  NBD  LFX  SM |  SCR SWS | -3dB -6dB  Dev    NBD  NBD  LFX   SM |  SCR SWS |  SCR |Pre AMP | Width Height Depth Weigth"
        )
        header.append(
            "Speaker                                              | each$                                  dB |                          |                      ON  PIR   Hz PIR |      |                    ON  PIR   Hz  PIR |   EQ | DIFF |     dB | mm    mm     mm    kg"
        )
        format_characteristics = "{:5s} {:15s} {:7s} {:=11.1f}"
        format_measurement = "{:18s} {:7s}"
        format_estimates = "{:5.1f} {:5.1f} {:+5.1f} {:0.2f} {:0.2f} {:3.0f} {:0.2f} {:0.2f}"
        format_dimension = "{:4d} {:4d} {:4d} {:5.1f}"
        format_string = "{{:35s}} {{:17s}} {{:5b}}| {0:s}| {1:s} | {2:s} | {{:+1.1f}} | {2:s} | {{:+1.1f}} |  {{:+1.1f}} | {{:+5.1f}} | {3:s} |".format(
            format_characteristics, format_measurement, format_estimates, format_dimension
        )
    elif txt_format == "csv":
        header.append(
            'Speaker, Measurement, IsDefault, Price, Shape, Type, Sensitivity, DataFormat, Quality, "Measured -3dB",  "Measured -6dB", Deviation, Measured_NBD_ON,  Measured_NBD_PIR,  Measured_LFX, Measured_SM_PIR, Measured_Score, Measured_Score_With_Sub, "EQed -3dB", "EQed -6dB", EQed_Deviation, EQed_NBD_ON,  EQed_NBD_PIR, EQed_LFX, EQed_SM_PIR, EQed_Score, EQed_Score_With_Sub, EQ_Preamp_Gain, Width, Height, Depth, Weigth'
        )
        format_characteristics = "{:s}, {:s}, {:s}, {:f}"
        format_measurement = "{:s}, {:s}"
        format_estimates = "{:5.1f}, {:5.1f}, {:5.1f}, {:0.2f}, {:0.2f}, {:3.0f}, {:0.2f}, {:0.2f}"
        format_dimension = "{:4d}, {:4d}, {:4d}, {:5.1f}"
        format_string = "{{:s}}, {{:s}}, {{:b}}, {0:s}, {1:s}, {2:s}, {{:5.1f}}, {2:s}, {{:5.1f}}, {{:5.1f}}, {{:5.1f}}, {3:s}".format(
            format_characteristics, format_measurement, format_estimates, format_dimension
        )
    else:
        return

    for h in header:
        print(h)

    for (
        speaker_name,
        key,
        is_default,
        price,
        shape,
        energy,
        sensitivity,
        pref,
        pref_eq,
        eq,
        data_format,
        quality,
        estimates,
        estimates_eq,
        specifications,
    ) in sorted(results, key=lambda a: a[0]):
        # between scores
        delta = pref_eq.get("pref_score", 0.0) - pref.get("pref_score", 0.0)
        # get preamp_gain
        preamp_gain = 0.0
        if eq is not None:
            preamp_gain = float(eq.get("preamp_gain", 0.0))
        # get dimensions
        weight = -0.0
        depth = 0
        width = 0
        height = 0
        if specifications is not None:
            weight = float(specifications.get("weight", 0.0))
            size = specifications.get("size", None)
            if size is not None:
                depth = int(size.get("depth", 0))
                width = int(size.get("width", 0))
                height = int(size.get("height", 0))
        print(
            format_string.format(
                speaker_name,
                key,
                is_default,
                price,
                shape,
                energy,
                sensitivity,
                data_format,
                quality,
                estimates.get("ref_3dB", -1.0),
                estimates.get("ref_6dB", -1.0),
                estimates.get("ref_band", -1.0),
                pref.get("nbd_on_axis", -1.0),
                pref.get("nbd_pred_in_room", -1.0),
                pref.get("lfx_hz", -1.0),
                pref.get("sm_pred_in_room", -1.0),
                pref.get("pref_score", -10.0),
                pref.get("pref_score_swub", -10.0),
                estimates_eq.get("ref_3dB", -1.0),
                estimates_eq.get("ref_6dB", -1.0),
                estimates_eq.get("ref_band", -1.0),
                pref_eq.get("nbd_on_axis", -1.0),
                pref_eq.get("nbd_pred_in_room", -1.0),
                pref_eq.get("lfx_hz", -1.0),
                pref_eq.get("sm_pred_in_room", -1.0),
                pref_eq.get("pref_score", -10.0),
                pref_eq.get("pref_score_swub", -10.0),
                delta,
                preamp_gain,
                width,
                height,
                depth,
                weight,
            )
        )


def main():
    print_what = None
    if args["--print"] is not None:
        print_what = args["--print"]

    push_key = None
    if args["--push"] is not None:
        push_key = args["--push"]

    # load all metadata from generated json file
    json_filename, _ = find_metadata_file()
    if json_filename is None:
        logger.error("Cannot find metadata file, did you ran generate_meta.py ?")
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    logger.warning("Data %s loaded (%d speakers)!", json_filename, len(jsmeta))

    if print_what is not None:
        if print_what == "eq_txt":
            print_eq(jsmeta, "txt", push_key)
        elif print_what == "eq_csv":
            print_eq(jsmeta, "csv", push_key)
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
