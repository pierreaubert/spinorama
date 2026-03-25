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

import csv
import logging
from glob import glob

logger = logging.getLogger("spinorama")

AUTOEQ_MEASUREMENTS_DIR = "/Volumes/data/src/python/AutoEq/measurements"


def normalize_name(name: str) -> str:
    """Normalize a headphone name for dedup comparison."""
    return name.strip().lower().replace("-", " ").replace("_", " ")


def build_autoeq_index(autoeq_dir: str = AUTOEQ_MEASUREMENTS_DIR) -> set[str]:
    """Read all name_index.tsv files from AutoEq and return a set of normalized names.

    TSV format: url\tsource_name\tname\tform\trig
    Collects all source_name values where form != "ignore".
    """
    names: set[str] = set()
    pattern = f"{autoeq_dir}/*/name_index.tsv"
    tsv_files = glob(pattern)

    if not tsv_files:
        logger.warning("No name_index.tsv files found in %s", pattern)
        return names

    for tsv_path in tsv_files:
        try:
            with open(tsv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                header = next(reader, None)
                if header is None:
                    continue

                # Find column indices
                try:
                    source_name_idx = header.index("source_name")
                    form_idx = header.index("form")
                except ValueError:
                    logger.warning("Unexpected TSV header in %s: %s", tsv_path, header)
                    continue

                for row in reader:
                    if len(row) <= max(source_name_idx, form_idx):
                        continue
                    form = row[form_idx].strip()
                    if form == "ignore":
                        continue
                    source_name = row[source_name_idx].strip()
                    if source_name:
                        names.add(normalize_name(source_name))

        except OSError as e:
            logger.warning("Could not read %s: %s", tsv_path, e)

    logger.info("AutoEq index: %d names from %d sources", len(names), len(tsv_files))
    return names
