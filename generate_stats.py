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


VERSION = 0.7
DEBUG_TYPE = False

structured = [
    # Group,         Field name,     Short,   Unit , Formatter
    ("Speaker", "Speaker", "SPK", None, "{:35s}"),
    ("Speaker", "Measurement", "MSR", None, "{:17s}"),
    ("Speaker", "Price", "$$$", None, "{:s}"),
    ("Speaker", "Shape", "SHP", None, "{:18s}"),
    ("Speaker", "Energy", "P/A", None, "{:7s}"),
    #
    ("Dimension", "Width", "WID", "mm", "{:4d}"),
    ("Dimension", "Heigth", "HEI", "mm", "{:4d}"),
    ("Dimension", "Depth", "DEP", "mm", "{:4d}"),
    ("Dimention", "Weight", "WEI", "kg", "{:5.1f}"),
    #
    ("Measurement", "IsDefault", "Def", None, "{:5s}"),
    ("Measurement", "DataFormat", "FMT", None, "{:8s}"),
    ("Measurement", "Quality", "Qua", None, "{:8s}"),
    ("Measurement", "Distance", "Dis", "m", "{:4f}"),
    #
    ("Properties", "Sensitivity Computed", "Sen", "Ohm", "{:4.1f}"),
    ("Properties", "Sensitivity Estimated at 1m", "S1m", "Ohm", "{:4.1f}"),
    ("Properties", " -3", " -3", "Hz", "{:2f}"),
    ("Properties", " -6", " -6", "Hz", "{:2f}"),
    ("Properties", " -9", " -9", "Hz", "{:2f}"),
    ("Properties", " -12", "-12", "Hz", "{:2f}"),
    ("Properties", "Directivity Constant", "Dir Con", "#", "{:3.1f}"),
    ("Properties", "Directivity Horinzontal", "Dir Hor", "o", "{:3.1f}"),
    ("Properties", "Directivity Vertical", "Dir Vor", "o", "{:3.1f}"),
    ("Properties", "Ref", "Ref", "SPL", "{:4.1f}"),
    ("Properties", "NBD On Axis", "NON", None, "{:3.1f}"),
    ("Properties", "NBD In-Room", "NIR", None, "{:3.1f}"),
    ("Properties", "LFX", "LFX", "Hz", "{:3.1f}"),
    ("Properties", "SM In-Room", "SIR", None, "{:3.1f}"),
    ("Properties", "Preference Score", "SCR", None, "{:3.1f}"),
    ("Properties", "Preference Score With Sub", "Sub", None, "{:3.1f}"),
    #
    ("EQ", " -3", " -3", "dB", "{:2f}"),
    ("EQ", " -6", " -6", "dB", "{:2f}"),
    ("EQ", " -9", " -9", "dB", "{:2f}"),
    ("EQ", " -12", "-12", "dB", "{:2f}"),
    ("EQ", "Ref", "Ref", "SPL", "{:4.1f}"),
    ("EQ", "NBD On Axis", "NON", None, "{:3.1f}"),
    ("EQ", "NBD In-Room", "NIR", None, "{:3.1f}"),
    ("EQ", "LFX", "LFX", None, "{:3.1f}"),
    ("EQ", "SM In-Room", "SIR", None, "{:3.1f}"),
    ("EQ", "Preference Score w/eq", "SEQ", None, "{:3.1f}"),
    ("EQ", "Preference Score with Sub w/eq", "SSE", None, "{:3.1f}"),
    ("EQ", "Preamp-Gain", "PAG", "dB", "{:3.1f}"),
    ("EQ", "Score Delta", "DEL", None, "{:3.1f}"),
]


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
            sensitivity_data = measurement.get("sensitivity", {})
            sensitivity = sensitivity_data.get("computed", -1)
            sensitivity_distance = sensitivity_data.get("distance", 1.0)
            sensitivity_1m = sensitivity_data.get("sensitivity_1m", -1)
            if quality == "" and data_format == "klippel":
                quality = "high"
            is_default = str(key == default_measurement)
            results.append(
                (
                    i,
                    key,
                    is_default,
                    price,
                    shape,
                    energy,
                    sensitivity,
                    sensitivity_distance,
                    sensitivity_1m,
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


def print_eq(speakers, txt_format):
    format_string = ""
    results = speakers2results(speakers)
    headers = []
    if txt_format == "csv":
        header = ""
        for group, field, _, unit, formatter in structured:
            if unit is None:
                if group != field:
                    header += '"{} {}", '.format(group, field)
                else:
                    header += '"{}", '.format(group)
            else:
                header += '"{} {} ({})", '.format(group, field, unit)
            if formatter[-2] == "s":
                format_string += '"{:s}",'
            else:
                format_string += "{{:{0}}},".format(formatter[-2])
        headers.append(header)
    elif txt_format == "txt":
        header = ""
        for group, _, short, _, formatter in structured:
            header += '"{} {} "'.format(group, short)
            format_string += " {}".format(formatter)
        headers.append(header)
    else:
        print("Warning: {} is unknown".format(txt_format))
        return

    for header in headers:
        print(header)

    for (
        speaker_name,
        key,
        is_default,
        price,
        shape,
        energy,
        sensitivity,
        sensitivity_distance,
        sensitivity_1m,
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

        format_parameters = (
            # speaker
            speaker_name,
            key,
            price,
            shape,
            energy,
            # dimension
            width,
            height,
            depth,
            weight,
            # measurement
            is_default,
            data_format,
            quality,
            sensitivity_distance,
            # properties
            sensitivity,
            sensitivity_1m,
            estimates.get("ref_3dB", -1.0),
            estimates.get("ref_6dB", -1.0),
            estimates.get("ref_9dB", -1.0),
            estimates.get("ref_12dB", -1.0),
            estimates.get("ref_band", -1.0),
            estimates.get("dir_constant", -1.0),
            estimates.get("dir_horizontal", 0.0),
            estimates.get("dir_vertical", 0.0),
            pref.get("nbd_on_axis", -1.0),
            pref.get("nbd_pred_in_room", -1.0),
            pref.get("lfx_hz", -1.0),
            pref.get("sm_pred_in_room", -1.0),
            pref.get("pref_score", -10.0),
            pref.get("pref_score_wsub", -10.0),
            # eq
            estimates_eq.get("ref_3dB", -1.0),
            estimates_eq.get("ref_6dB", -1.0),
            estimates_eq.get("ref_9dB", -1.0),
            estimates_eq.get("ref_12dB", -1.0),
            estimates_eq.get("ref_band", -1.0),
            pref_eq.get("nbd_on_axis", -1.0),
            pref_eq.get("nbd_pred_in_room", -1.0),
            pref_eq.get("lfx_hz", -1.0),
            pref_eq.get("sm_pred_in_room", -1.0),
            pref_eq.get("pref_score", -10.0),
            pref_eq.get("pref_score_wsub", -10.0),
            preamp_gain,
            delta,
        )
        if DEBUG_TYPE:
            for i, p in enumerate(format_parameters):
                if p is None:
                    print("Parameter {} is None".format(i))
                else:
                    print("Parameter {} is {}".format(i, type(p)))

        print(format_string.format(*format_parameters))


def main():
    print_what = None
    if args["--print"] is not None:
        print_what = args["--print"]

    # TODO: wanted to push directly to GCP but you need a project id and so one
    # I will just generate an Excel file
    #
    # push_key = None
    # if args["--push"] is not None:
    #     push_key = args["--push"]

    # load all metadata from generated json file
    meta_filename, eq_filename = find_metadata_file()
    if meta_filename is None:
        logger.error("Cannot find metadata file, did you ran generate_meta.py ?")
        sys.exit(1)

    jsmeta = None
    with open(meta_filename, "r") as f:
        jsmeta = json.load(f)

    eqmeta = None
    with open(eq_filename, "r") as f:
        eqmeta = json.load(f)
        for k in jsmeta:
            if k in eqmeta:
                jsmeta[k]["eqs"] = eqmeta[k]["eqs"]

    logger.warning("Data %s loaded (%d speakers)!", meta_filename, len(jsmeta))

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
        str(__doc__),
        version="./generate_stats.py version {:1.1f}".format(VERSION),
        options_first=True,
    )
    logger = get_custom_logger(level=args2level(args), duplicate=True)
    main()
