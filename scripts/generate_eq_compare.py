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
from spinorama.misc import fingerprint_paths, sanitize_filename
from spinorama.plot import plot_eqs
from spinorama.loaders.rew_eq import parse_eq_iir_rews


VERSION = 0.2
EQ_COMPARE_CACHE_VERSION = "eq-compare-cache-v1"
EQ_COMPARE_CACHE_MANIFEST = ".cache/eq-compare-manifest.json"


def eq_compare_filename(data):
    """Return the generated comparison path for one speaker."""
    return "{}/{} {}/eq_compare.json".format(
        CPATH_DIST_SPEAKERS, sanitize_filename(data["brand"]), sanitize_filename(data["model"])
    )


def eq_compare_dependencies(data):
    """Return files whose changes invalidate one comparison plot."""
    eqs = glob.glob(
        "{}/{} {}/*.txt".format(
            CPATH_DATAS_EQ, sanitize_filename(data["brand"]), sanitize_filename(data["model"])
        )
    )
    return eqs + [
        __file__,
        "src/spinorama/plot.py",
        "src/spinorama/loaders/rew_eq.py",
    ]


def eq_compare_needs_update(filename, dependencies):
    """Avoid rebuilding Plotly figures when all inputs predate the output."""
    if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
        return True
    output_mtime = os.path.getmtime(filename)
    return any(
        os.path.isfile(dependency) and os.path.getmtime(dependency) > output_mtime
        for dependency in dependencies
    )


def eq_compare_cache_fingerprint(json_filename):
    return fingerprint_paths(
        [
            json_filename,
            CPATH_DATAS_EQ,
            __file__,
            "src/spinorama/plot.py",
            "src/spinorama/loaders/rew_eq.py",
        ],
        version=EQ_COMPARE_CACHE_VERSION,
    )


def eq_compare_cache_is_valid(json_filename):
    try:
        with open(EQ_COMPARE_CACHE_MANIFEST, "r", encoding="utf-8") as manifest_fd:
            manifest = json.load(manifest_fd)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return False
    if manifest.get("fingerprint") != eq_compare_cache_fingerprint(json_filename):
        return False
    outputs = manifest.get("outputs", [])
    return bool(outputs) and all(os.path.isfile(filename) for filename in outputs)


def save_eq_compare_cache_manifest(json_filename, outputs):
    os.makedirs(os.path.dirname(EQ_COMPARE_CACHE_MANIFEST), exist_ok=True)
    temporary_path = f"{EQ_COMPARE_CACHE_MANIFEST}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as manifest_fd:
        json.dump(
            {
                "version": EQ_COMPARE_CACHE_VERSION,
                "fingerprint": eq_compare_cache_fingerprint(json_filename),
                "outputs": sorted(set(outputs)),
            },
            manifest_fd,
            indent=2,
            sort_keys=True,
        )
    os.replace(temporary_path, EQ_COMPARE_CACHE_MANIFEST)


def build_eq_figure_and_filename(data):
    brand = data["brand"]
    model = data["model"]
    filename = eq_compare_filename(data)
    freq = np.logspace(math.log10(2) + 1, math.log10(2) + 4, 200)
    eqs = glob.glob(
        "{}/{} {}/*.txt".format(CPATH_DATAS_EQ, sanitize_filename(brand), sanitize_filename(model))
    )
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
    filename = eq_compare_filename(speaker_data)
    needs_update = force or eq_compare_needs_update(
        filename, eq_compare_dependencies(speaker_data)
    )
    if not needs_update:
        return
    fig, filename, deps = build_eq_figure_and_filename(speaker_data)
    if os.path.exists(os.path.dirname(filename)):
        with open(filename, "w", encoding="utf-8") as f_d:
            f_d.write(fig.to_json())


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

    if not force and eq_compare_cache_is_valid(json_filename):
        logger.info("EQ comparison cache is up to date")
        return 0

    tasks = [(speaker_data, force) for speaker_data in jsmeta.values()]

    num_processes = max(1, multiprocessing.cpu_count() - 1)
    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.starmap(_eq_compare_worker, tasks)

    if not force:
        save_eq_compare_cache_manifest(
            json_filename,
            [
                eq_compare_filename(speaker_data)
                for speaker_data in jsmeta.values()
                if os.path.isfile(eq_compare_filename(speaker_data))
            ],
        )

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate EQ comparison plots.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"./scripts/generate_eq_compare.py version {VERSION:.1f}",
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
