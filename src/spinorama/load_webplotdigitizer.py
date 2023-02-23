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

import json
import math
import numpy as np
import os
import pandas as pd
import tarfile

from spinorama import logger
from spinorama.load import parse_graph_freq_check, spin_compute_di_eir


pd.set_option("display.max_rows", 1000)


def parse_webplotdigitizer_get_jsonfilename(dirname, speaker_name, origin, version):
    filename = None
    clean_dir = dirname
    if dirname[-1] == "/":
        clean_dir = dirname[:-1]

    filedir = f"{clean_dir}/{speaker_name}/{version}"
    filename = f"{filedir}/{speaker_name}"
    tarfilename = filename + ".tar"
    jsonfilename = None
    try:
        if os.path.exists(tarfilename):
            # we are looking for info.json that may or not be in a directory
            with tarfile.open(tarfilename, "r|*") as tar:
                info_json = None
                for tarinfo in tar:
                    logger.debug("Tarinfo.name %s".format(tarinfo.name))
                    if tarinfo.isreg() and tarinfo.name[-9:] == "info.json":
                        # note that files/directory with name tmp are in .gitignore
                        tar.extract(tarinfo, path=filedir + "/tmp", set_attrs=False)
                        info_json = filedir + "/tmp/" + tarinfo.name
                        with open(info_json, "r") as f:
                            info = json.load(f)
                            jsonfilename = filedir + "/tmp/" + tarinfo.name[:-9] + info["json"]

            # now extract the large json file
            if jsonfilename is not None:
                with tarfile.open(tarfilename, "r|*") as tar:
                    for tarinfo in tar:
                        if tarinfo.isfile() and tarinfo.name in jsonfilename:
                            logger.debug("Extracting: %s", tarinfo.name)
                            tar.extract(tarinfo, path=filedir + "/tmp", set_attrs=False)
        else:
            logger.debug("Tarfilename %s doesn't exist", tarfilename)

    except tarfile.ReadError as re:
        logger.exception("Tarfile %s: %s", tarfilename, re)
    if jsonfilename is None:
        jsonfilename = filename + ".json"
    if not os.path.exists(jsonfilename):
        logger.warning("Didn't find tar or json for %s %s %s", speaker_name, origin, version)
        return None
    logger.debug("Jsonfilename %s", jsonfilename)
    return jsonfilename


def parse_graph_freq_webplotdigitizer(filename):
    """ """
    # from 20Hz to 20kHz, log(2)~0.3
    ref_freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 1000)
    #
    try:
        with open(filename, "r") as f:
            # data are stored in a json file.
            speaker_data = json.load(f)
            # store all results
            res = []
            for col in speaker_data["datasetColl"]:
                data = col["data"]
                # sort data
                udata = [(data[d]["value"][0], data[d]["value"][1]) for d in range(0, len(data))]
                sdata = sorted(udata, key=lambda a: a[0])
                logger.debug("reading col %s with %d data", col["name"], len(sdata))
                # if len(sdata) > 0:
                #   print(sdata)
                # since sdata and freq_ref are both sorted, iterate over both
                ref_p = 0
                for di in range(0, len(sdata) - 1):
                    d = sdata[di]
                    dn = sdata[di + 1]
                    fr = d[0]
                    db = d[1]
                    frn = dn[0]
                    dbn = dn[1]
                    # remove possible errors
                    if fr == frn:
                        logger.debug("found points with equal frequency %f", fr)
                        continue
                    # look for closest match
                    while ref_freq[ref_p] <= fr:
                        if ref_p >= len(ref_freq) - 1:
                            logger.debug("closest match at %f %f", ref_p, ref_freq)
                            break
                        ref_p += 1
                    # if ref_f is too large, skip
                    ref_f = ref_freq[ref_p]
                    if ref_f > frn:
                        logger.debug("ref freq too large, skipping %f %f", ref_f, frn)
                        continue
                    # linear interpolation
                    ref_db = db + ((dbn - db) * (ref_f - fr)) / (frn - fr)
                    if 0 < ref_f <= 20000 and -50 < ref_db < 200:
                        res.append([ref_f, ref_db, col["name"]])
                    else:
                        logger.info(
                            "fr={:.2f} fr_ref={:.2f} fr_n={:.2f} db={:.1f} db_ref={:.1f} db_n={:.1f}",
                            fr,
                            ref_f,
                            frn,
                            db,
                            ref_db,
                            dbn,
                        )
                        break

            # build dataframe
            def pretty(name):
                newname = name
                if newname.lower() in ("on axis", "on-axis", "oa", "onaxis", "on"):
                    newname = "On Axis"
                if newname.lower() in ("listening window", "lw"):
                    newname = "Listening Window"
                if newname.lower() in (
                    "early reflections",
                    "early reflection",
                    "early reflexion",
                    "first reflections",
                    "first reflection",
                    "first reflexion",
                    "er",
                ):
                    newname = "Early Reflections"
                if newname.lower() in (
                    "early reflections di",
                    "early reflection di",
                    "early reflexion di",
                    "first reflections di",
                    "first reflection di",
                    "first reflexion di",
                    "erdi",
                    "erd",
                ):
                    newname = "Early Reflections DI"
                if newname.lower() in ("sound power", "sp"):
                    newname = "Sound Power"
                if newname.lower() in ("sound power di", "spdi", "spd"):
                    newname = "Sound Power DI"
                return newname

            # print(res)
            freq = np.array([res[i][0] for i in range(0, len(res))]).astype(float)
            dB = np.array([res[i][1] for i in range(0, len(res))]).astype(float)
            mrt = [pretty(res[i][2]) for i in range(0, len(res))]
            df = pd.DataFrame({"Freq": freq, "dB": dB, "Measurements": mrt})
            logger.debug(
                "scan complete fr=[%f, %f], dB=[%f, %f]",
                df.Freq.min(),
                df.Freq.max(),
                df.dB.min(),
                df.dB.max(),
            )
            return "CEA2034", df
    except IOError as e:
        logger.exception("Cannot not open: %s", e)
        return None, None


def parse_graphs_speaker_webplotdigitizer(
    speaker_path, speaker_brand, speaker_name, origin, version
):
    dfs = {}
    logger.debug("speaker_path set to %s", speaker_path)
    jsonfilename = parse_webplotdigitizer_get_jsonfilename(
        speaker_path, speaker_name, origin, version
    )

    if jsonfilename is None:
        logger.warning(
            "%s %s %s didn't find data file in %s", speaker_name, origin, version, speaker_path
        )
        return None

    try:
        return parse_graph_freq_webplotdigitizer(jsonfilename)
    except FileNotFoundError:
        logger.info("Speaker: %s Not found: %s", speaker_name, jsonfilename)
    return dfs
