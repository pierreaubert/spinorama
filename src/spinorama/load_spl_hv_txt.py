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

import os
import glob
import pandas as pd

from datas.incomplete import known_incomplete_measurements
from spinorama import logger
from spinorama.ltype import StatusOr
from spinorama.misc import sort_angles, measurements_missing_angles


def parse_graph_spl_find_file(dirpath: str, orientation: str) -> StatusOr[list[str]]:
    # warning this are fnmatch(es) and not regexps
    filenames = "{0}/*_{1}*[0-9]*.txt".format(dirpath, orientation)
    files = glob.glob(filenames)
    if len(files) == 0:
        filenames = "{0}/*[0-9]*_{1}.txt".format(dirpath, orientation)
        files = glob.glob(filenames)

    logger.debug("Found %d files in %s for orientation %s", len(files), dirpath, orientation)
    if len(files) == 0:
        return False, []

    return True, files


def parse_graph_spl_hv_txt(dirpath: str, orientation: str) -> StatusOr[pd.DataFrame]:
    """Parse text files with Horizontal and Vertical data"""
    status, files = parse_graph_spl_find_file(dirpath, orientation)
    if not status:
        logger.warning("Did not find files in %s", dirpath)
        return False, pd.DataFrame()

    symmetry = True
    for file in files:
        file_format = os.path.basename(file).split()
        angle = os.path.basename(file).split("_")[0]
        if len(file_format) > 2:
            angle = file_format[-1][:-4]
        if int(angle) < 0:
            symmetry = False

    logger.debug("Symmetrie is %s", symmetry)

    dfs = []
    already_loaded = set()
    for file in files:
        freqs = []
        dbs = []

        # 3 possible formats:
        # 1. angle_H or angle_V.txt
        # 2. name _H angle.txt
        # 3. _[HV] angle.txt
        # where _H could H, hor with or without _
        angle = "error"
        file_format = os.path.basename(file).split()
        if len(file_format) > 2:
            angle = file_format[-1][:-4]
        else:
            angle = os.path.basename(file).split("_")[0]

        if angle == "0":
            angle = "On Axis"
        else:
            angle += "°"

        if angle == "error":
            logger.error('read file "%s" failed for angle "%s"', file, angle)
        else:
            logger.debug('read file "%s" for angle "%s"', file, angle)
        with open(file, "r") as fd:
            lines = fd.readlines()
            for l in lines:
                # again 2 possible format
                # freq, db
                words = l[:-1].split(",")
                if len(words) == 2:
                    current_freq = float(words[0])
                    if current_freq >= 20 and current_freq <= 20000:
                        freqs.append(current_freq)
                        dbs.append(float(words[1]))
                    continue

                # freq db phase
                words = l.split()
                if len(words) == 2 or len(words) == 3:
                    freq = words[0]
                    db = words[1]
                    # skip first line
                    if freq[0] != "F" and float(freq) >= 20 and float(freq) <= 20000:
                        freqs.append(float(freq))
                        dbs.append(float(db))
                    continue

                logger.warning("unkown file format len words %d for line %s", len(words), l)

        if angle == "On Axis":
            if angle not in already_loaded:
                dfs.append(pd.DataFrame({"Freq": freqs, angle: dbs}))
                already_loaded.add(angle)
            else:
                logger.warning("angle %s already loaded (dirpath=%s)", angle, dirpath)
        else:
            if angle != "-180°":
                if angle not in already_loaded:
                    dfs.append(pd.DataFrame({angle: dbs}))
                    already_loaded.add(angle)
                else:
                    logger.warning("angle %s already loaded (dirpath=%s)", angle, dirpath)
            if symmetry and orientation == "H" and angle != "180°":
                mangle = f"-{angle}"
                dfs.append(pd.DataFrame({mangle: dbs}))

    # print("debug {}".format(orientation))
    # print(sort_angles(pd.concat(dfs, axis=1)).keys())
    # print(sort_angles(pd.concat(dfs, axis=1)).head())
    return True, sort_angles(pd.concat(dfs, axis=1))


def parse_graphs_speaker_spl_hv_txt(
    speaker_path: str, speaker_brand: str, speaker_name: str, version: str
) -> StatusOr[tuple[pd.DataFrame, pd.DataFrame]]:
    """2 files per directory xxx_H_IR.mat and xxx_V_IR.mat"""
    dirname = "{0}/{1}/{2}".format(speaker_path, speaker_name, version)

    logger.debug("scanning path %s for speaker %s %s", dirname, speaker_brand, speaker_name)

    h_status, h_spl = parse_graph_spl_hv_txt(dirname, "H")
    v_status, v_spl = parse_graph_spl_hv_txt(dirname, "V")

    if (
        len(h_spl.keys()) + len(v_spl.keys()) < 72
        and (speaker_name, version) not in known_incomplete_measurements
    ):
        logger.warning("We have only partial data in %s", dirname)
        logger.debug(
            "We have only partial data in %s len(H)=%i len(V)=%i missing measurements %s",
            dirname,
            len(h_spl),
            len(v_spl),
            measurements_missing_angles(h_spl, v_spl),
        )

    return h_status and v_status, (h_spl, v_spl)
