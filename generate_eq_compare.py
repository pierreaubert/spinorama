#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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
import glob
import math

from docopt import docopt
import numpy as np

from generate_common import get_custom_logger, args2level, find_metadata_file
from spinorama.constant_paths import CPATH_DOCS_SPEAKERS, CPATH_DATAS_EQ
from spinorama.need_update import need_update
from spinorama.pict import write_multiformat
from spinorama.plot import plot_eqs
from spinorama.load_rew_eq import parse_eq_iir_rews


VERSION = 0.2


def print_eq_compare(data, force):
    brand = data["brand"]
    model = data["model"]
    filename = "{}/{} {}/eq_compare.png".format(CPATH_DOCS_SPEAKERS, brand, model)
    freq = np.logspace(math.log10(2) + 1, math.log10(2) + 4, 200)
    eqs = glob.glob("{}/{} {}/*.txt".format(CPATH_DATAS_EQ, brand, model))
    peqs = [parse_eq_iir_rews(eq, 48000) for eq in eqs if os.path.basename(eq) != "iir.txt"]
    names = [os.path.basename(eq) for eq in eqs if os.path.basename(eq) != "iir.txt"]
    fig = plot_eqs(freq, peqs, names)
    fig.update_layout(
        title={
            "text": f"EQs for {brand} {model}",
            "x": 0.5,
            "y": 0.1,
            "xanchor": "center",
            "yanchor": "bottom",
        }
    )
    recent = need_update(filename, dependencies=eqs)
    write_multiformat(fig, filename, force or recent)


def main(force):
    # load all metadata from generated json file
    json_filename, _ = find_metadata_file()
    if json_filename is None:
        logger.error("Cannot find metadata file!")
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    logger.info("Data %s loaded (%d speakers!", json_filename, len(jsmeta))

    for speaker_data in jsmeta.values():
        print_eq_compare(speaker_data, force)

    return 0


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version=f"generate_radar.py version {VERSION:1.1f}",
        options_first=True,
    )

    logger = get_custom_logger(level=args2level(args), duplicate=True)

    FORCE = args["--force"]

    sys.exit(main(FORCE))
