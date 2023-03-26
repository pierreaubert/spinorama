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

import os
import glob
import pandas as pd

from spinorama import logger
from spinorama.load_misc import sort_angles


def parse_graph_splHVtxt(dirpath: str, orientation: str) -> pd.DataFrame:
    """Parse text files with Horizontal and Vertical data"""
    filenames = "{0}/*_{1}.txt".format(dirpath, orientation)
    files = glob.glob(filenames)
    if len(files) == 0:
        filenames = "{0}/* _{1} *.txt".format(dirpath, orientation)
        files = glob.glob(filenames)

    logger.debug("Found %d files in %s", len(files), dirpath)

    symmetry = True
    for file in files:
        file_format = os.path.basename(file).split()
        if len(file_format) > 2:
            angle = file_format[-1][:-4]
        else:
            angle = os.path.basename(file).split("_")[0]

        if int(angle) < 0:
            symmetry = False

    logger.info("Symmetrie is %s", symmetry)

    dfs = []
    already_loaded = set()
    for file in files:
        freqs = []
        dbs = []

        # 2 possible formats:
        # 1. angle_H or angle_V.txt
        # 2. name _H angle.txt
        file_format = os.path.basename(file).split()
        if len(file_format) > 2:
            angle = file_format[-1][:-4]
        else:
            angle = os.path.basename(file).split("_")[0]

        if angle == "0":
            angle = "On Axis"
        else:
            angle += "°"

        logger.debug('read file "%s" for angle "%s"', file, angle)
        with open(file, "r") as fd:
            lines = fd.readlines()
            for l in lines:
                # again 2 possible format
                # freq, db
                words = l[:-1].split(",")
                if len(words) == 2:
                    current_freq = float(words[0])
                    if current_freq < 20000:
                        freqs.append(current_freq)
                        dbs.append(float(words[1]))
                    continue

                # freq db phase
                words = l.split()
                if len(words) == 2 or len(words) == 3:
                    freq = words[0]
                    db = words[1]
                    # skip first line
                    if freq[0] != "F" and float(freq) < 20000:
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

    return sort_angles(pd.concat(dfs, axis=1))


def parse_graphs_speaker_splHVtxt(
    speaker_path: str, speaker_brand: str, speaker_name: str, version: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """2 files per directory xxx_H_IR.mat and xxx_V_IR.mat"""
    dirname = "{0}/{1}/{2}".format(speaker_path, speaker_name, version)

    logger.debug("scanning path %s", dirname)

    h_spl = parse_graph_splHVtxt(dirname, "H")
    v_spl = parse_graph_splHVtxt(dirname, "V")

    return h_spl, v_spl
