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

import locale
import os

import pandas as pd

from spinorama import logger
from spinorama.ltype import StatusOr
from spinorama.load_misc import sort_angles

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

removequote = str.maketrans({'"': None, "\n": ""})


def parse_graph_freq_klippel(filename: str) -> StatusOr[tuple[str, pd.DataFrame]]:
    """Parse a klippel generated file"""
    title = None
    columns = ["Freq"]
    usecols = [0]
    try:
        with open(filename) as csvfile:
            # first line is graph title
            title = csvfile.readline().split("\t")[0][1:-1]
            if title[-1] == '"':
                title = title[:-1]
            # second line is column titles
            csvcolumns = [c.translate(removequote) for c in csvfile.readline().split("\t")]
            # third line is column units
            # units = [c.translate(removequote)
            #         for c in csvfile.readline().split('\t')]
            # print(units)
            columns.extend([c for c in csvcolumns if len(c) > 0])
            # print(columns)
            usecols.extend([1 + i * 2 for i in range(len(columns) - 1)])
            # print(usecols)
    except FileNotFoundError as file_not_found:
        logger.error("File not found: %s", file_not_found)
        raise

    # read all columns, drop 0
    df_klippel = pd.read_csv(
        filename, sep="\t", skiprows=2, usecols=usecols, names=columns, thousands=","
    ).drop(0)
    # convert to float (issues with , and . in numbers)
    df_klippel = df_klippel.map(locale.atof)
    # put it in order, not relevant for pandas but for np array
    if len(df_klippel.columns) > 2 and df_klippel.columns[2] == "10°":
        return True, (title, sort_angles(df_klippel))
    return True, (title, df_klippel)


def find_data_klippel(
    speaker_path, speaker_brand, speaker_name, mversion_in, csvname
) -> StatusOr[str]:
    """return the expected filename for Klippel data"""
    csvfilename = f"{speaker_path}/{speaker_name}/{mversion_in}/{csvname}.txt"

    if os.path.exists(csvfilename):
        logger.debug("match for %s", csvfilename)
        return True, csvfilename

    logger.error("no match for %s", csvfilename)
    return False, ""


def parse_graphs_speaker_klippel(
    speaker_path, speaker_brand, speaker_name, mversion, symmetry
) -> StatusOr[tuple[pd.DataFrame, pd.DataFrame]]:
    mandatory_csvfiles = [
        "SPL Horizontal",
        "SPL Vertical",
    ]
    found = 0
    for csv in mandatory_csvfiles:
        if find_data_klippel(speaker_path, speaker_brand, speaker_name, mversion, csv) is not None:
            found = found + 1
        else:
            logger.info(
                "Didn't find this mandatory files %s for speaker %s %s", csv, speaker_name, mversion
            )

    if found != len(mandatory_csvfiles):
        logger.info("Didn't find all mandatory files for speaker %s %s", speaker_name, mversion)
        return False, (pd.DataFrame(), pd.DataFrame())

    h_status, h_name = find_data_klippel(
        speaker_path, speaker_brand, speaker_name, mversion, "SPL Horizontal"
    )
    v_status, v_name = find_data_klippel(
        speaker_path, speaker_brand, speaker_name, mversion, "SPL Vertical"
    )

    if not h_status or not v_status:
        logger.info("File error")
        return False, (pd.DataFrame(), pd.DataFrame())
    h_status, (_, h_spl) = parse_graph_freq_klippel(h_name)
    v_status, (_, v_spl) = parse_graph_freq_klippel(v_name)

    if not h_status or not v_status:
        logger.info("Parse error")
        return False, (pd.DataFrame(), pd.DataFrame())

    logger.debug("Speaker: %s (Klippel) loaded", speaker_name)

    return True, (h_spl, v_spl)
