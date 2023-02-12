#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
usage: generate_stats.py [--help] [--version] [--dev] [--force]\
 [--log-level=<level>]

Options:
  --help            display usage()
  --version         script version number
  --force           regenerate pictures even if they already exist.
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import json
import os
import sys
import pathlib
import glob
import math

from docopt import docopt
import numpy as np

from generate_common import get_custom_logger, args2level
from spinorama.constant_paths import CPATH_METADATA_JSON, CPATH_DOCS_SPEAKERS, CPATH_DATAS_EQ
from spinorama.pict import write_multiformat
from spinorama.plot import plot_eqs
from spinorama.load_rewseq import parse_eq_iir_rews


VERSION = 0.1


def print_eq_compare(data, force):
    brand = data["brand"]
    model = data["model"]
    filename = "{}/{} {}/eq_compare.png".format(CPATH_DOCS_SPEAKERS, brand, model)
    freq = np.logspace(math.log10(2) + 1, math.log10(2) + 4, 200)
    eqs = glob.glob("{}/{} {}/*.txt".format(CPATH_DATAS_EQ, brand, model))
    peqs = [parse_eq_iir_rews(eq, 48000) for eq in eqs if os.path.basename(eq) != "iir.txt"]
    names = [os.path.basename(eq) for eq in eqs if os.path.basename(eq) != "iir.txt"]
    fig = plot_eqs(freq, peqs, names)
    fig.update_layout(title=f"EQs for {brand} {model}")
    write_multiformat(fig, filename, force)


def main(force):
    # load all metadata from generated json file
    json_filename = CPATH_METADATA_JSON
    if not os.path.exists(json_filename):
        logger.error("Cannot find {0}".format(json_filename))
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    logger.info("Data {0} loaded ({1} speakers)!".format(json_filename, len(jsmeta)))

    for speaker_name, speaker_data in jsmeta.items():
        print_eq_compare(speaker_data, force)

    sys.exit(0)


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="generate_radar.py version {:1.1f}".format(VERSION),
        options_first=True,
    )

    level = args2level(args)
    logger = get_custom_logger(True)
    logger.setLevel(level)

    force = args["--force"]

    main(force)
