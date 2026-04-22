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

import json
import multiprocessing
import os
import sys
import glob
import math

import argparse
import numpy as np

from generate_common import get_custom_logger, args2level, find_metadata_file
from spinorama.constant_paths import CPATH_DIST_SPEAKERS, CPATH_DATAS_EQ
from spinorama.misc import sanitize_filename
from spinorama.plot import plot_eqs
from spinorama.load_rew_eq import parse_eq_iir_rews


VERSION = 0.2


def build_eq_figure_and_filename(data):
    brand = data["brand"]
    model = data["model"]
    filename = "{}/{} {}/eq_compare.json".format(CPATH_DIST_SPEAKERS, sanitize_filename(brand), sanitize_filename(model))
    freq = np.logspace(math.log10(2) + 1, math.log10(2) + 4, 200)
    eqs = glob.glob("{}/{} {}/*.txt".format(CPATH_DATAS_EQ, sanitize_filename(brand), sanitize_filename(model)))
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
    return fig, filename, eqs


def _eq_compare_worker(speaker_data, force):
    """Worker: build EQ comparison figure and write to file if needed."""
    fig, filename, deps = build_eq_figure_and_filename(speaker_data)
    if not os.path.exists(filename) or os.path.getsize(filename) == 0 or force:
        content = fig.to_json()
        if os.path.exists(os.path.dirname(filename)):
            with open(filename, "w", encoding="utf-8") as f_d:
                f_d.write(content)


def main(force, batch_size):
    # load all metadata from generated json file
    json_filename, _ = find_metadata_file()
    if json_filename is None:
        logger.error("Cannot find metadata file!")
        sys.exit(1)

    jsmeta = None
    with open(json_filename, "r") as f:
        jsmeta = json.load(f)

    logger.info("Data %s loaded (%d speakers!", json_filename, len(jsmeta))

    tasks = [(speaker_data, force) for speaker_data in jsmeta.values()]

    num_processes = max(1, multiprocessing.cpu_count() - 1)
    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.starmap(_eq_compare_worker, tasks)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate EQ comparison plots.")
    parser.add_argument(
        "--version", action="version", version=f"generate_eq_compare.py version {VERSION:.1f}"
    )
    parser.add_argument(
        "--force", action="store_true", help="Regenerate pictures even if they already exist."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of figures to process per write_images batch (default: 64)",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: WARNING).",
    )

    args = parser.parse_args()

    logger = get_custom_logger(level=args2level(args), duplicate=True)

    FORCE = args.force
    BATCH_SIZE = args.batch_size

    sys.exit(main(FORCE, BATCH_SIZE))
