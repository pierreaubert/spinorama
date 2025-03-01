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
import zipfile

import pandas as pd

from spinorama import logger
from spinorama.ltype import StatusOr
from spinorama.misc import sort_angles


def parse_graph_gll_hv_txt(dir_path: str) -> StatusOr[tuple[pd.DataFrame, pd.DataFrame]]:
    """Parse text files with meridian and parallel data"""
    file_path = f"{dir_path}/tmp/*"  # noqa: S108
    file_names = f"{file_path}/*.txt"
    files = glob.glob(file_names)

    logger.debug("Found %d files in %s", len(files), file_path)

    spl_h = []
    spl_v = []
    already_loaded_h = set()
    already_loaded_v = set()
    for file in files:
        base = os.path.basename(file)
        file_format = base[:-4].split("-")
        try:
            meridian = int(file_format[-2][1:])
            parallel = int(file_format[-1][1:])
        except ValueError as e:
            # for files like sensitibity etc
            continue
        angle = None
        orientation = None

        if meridian == 0:
            angle = parallel
            orientation = "H"
        elif meridian == 90:
            angle = parallel
            orientation = "V"
        elif meridian == 180:
            angle = -parallel
            orientation = "H"
        elif meridian == 270:
            angle = -parallel
            orientation = "V"

        if angle is None or orientation is None:
            logger.debug("skipping %s angle is %d orientation is %s", base, angle, orientation)
            continue

        angle = "On Axis" if angle == 0 else f"{angle}°"
        # print('angle is {} orientation is {}'.format(angle, orientation))

        freqs = []
        dbs = []
        with open(file, "r") as fd:
            lines = fd.readlines()
            for l in lines[6:]:
                words = l[:-1].split()
                if len(words) >= 2:
                    current_freq = float(words[0])
                    current_spl = float(words[1])
                    if current_freq > 20 and current_freq < 20000:
                        freqs.append(current_freq)
                        # GLL files are measured at 10m spl is usually reported at 1m
                        # estimating real SPL at +10dB (since 10 ~ log2(10*10*10))
                        # TODO: compute it more precisely by taking into account the speaker dispersion
                        # Keep it as measured
                        dbs.append(current_spl)

        if angle == "On Axis":
            if orientation == "H":
                if angle not in already_loaded_h:
                    spl_h.append(pd.DataFrame({"Freq": freqs, angle: dbs}))
                already_loaded_h.add(angle)
            elif orientation == "V":
                if angle not in already_loaded_v:
                    spl_v.append(pd.DataFrame({"Freq": freqs, angle: dbs}))
                already_loaded_v.add(angle)

        if angle != "-180°":
            if orientation == "H" and angle not in already_loaded_h:
                spl_h.append(pd.DataFrame({angle: dbs}))
                already_loaded_h.add(angle)
            if orientation == "V" and angle not in already_loaded_v:
                spl_v.append(pd.DataFrame({angle: dbs}))
                already_loaded_v.add(angle)

    logger.debug("found %d horizontal and %d vertical measurements", len(spl_h), len(spl_v))
    sorted_h = sort_angles(pd.concat(spl_h, axis=1))
    sorted_v = sort_angles(pd.concat(spl_v, axis=1))
    return True, (sorted_h, sorted_v)


def parse_graphs_speaker_gll_hv_txt(
    speaker_path: str, speaker_name: str, version: str
) -> StatusOr[tuple[pd.DataFrame, pd.DataFrame]]:
    """2 files per directory xxx_H_IR.mat and xxx_V_IR.mat"""
    dirname = "{0}/{1}/{2}".format(speaker_path, speaker_name, version)

    logger.debug("scanning path %s", dirname)

    zipname = "{}/{}.zip".format(dirname, speaker_name)

    if not os.path.exists(zipname):
        # maybe the name is close but not exactly the name of the speaker
        guesses = glob.glob(f"{dirname}/*.zip")
        if len(guesses) == 1:
            zipname = guesses[0]
        elif len(guesses) > 1:
            logger.error("Multiple zip files in %s", dirname)
            return False, (pd.DataFrame(), pd.DataFrame())
        else:
            logger.error("%s does not exist", zipname)
            return False, (pd.DataFrame(), pd.DataFrame())

    tmp_dirname = "{}/tmp/{}".format(dirname, speaker_name)
    os.makedirs(tmp_dirname, mode=0o751, exist_ok=True)
    try:
        with zipfile.ZipFile(zipname, "r") as gll:
            for file in gll.namelist():
                with gll.open(file) as fd:
                    base = os.path.basename(file)
                    if base[-4:] not in (".txt", ".png"):
                        continue
                    data = fd.read()
                    filename = "{}/{}".format(tmp_dirname, base)
                    with open(filename, "wb") as out:
                        out.write(data)

            return parse_graph_gll_hv_txt(dirname)
    except zipfile.BadZipFile:
        logger.exception("%s is a bad zipfile", zipname)

    return False, (pd.DataFrame(), pd.DataFrame())
