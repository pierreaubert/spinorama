#                                                  -*- coding: utf-8 -*-
import logging
import json
import math
import numpy as np
import os
import pandas as pd
import tarfile
from .load import parse_graph_freq_check, spin_compute_di_eir


pd.set_option("display.max_rows", 1000)

logger = logging.getLogger("spinorama")


def parse_webplotdigitizer_get_jsonfilename(dirname, speaker_name, origin, version):
    filename = None
    clean_dir = dirname
    if dirname[-1] == "/":
        clean_dir = dirname[:-1]

    filedir = "{0}/{1}/{2}".format(clean_dir, speaker_name, version)
    filename = "{0}/{1}/{2}/{1}".format(clean_dir, speaker_name, version)
    tarfilename = filename + ".tar"
    jsonfilename = None
    try:
        if os.path.exists(tarfilename):
            # we are looking for info.json that may or not be in a directory
            with tarfile.open(tarfilename, "r|*") as tar:
                info_json = None
                for tarinfo in tar:
                    logging.debug("Tarinfo.name {}".format(tarinfo.name))
                    if tarinfo.isreg() and tarinfo.name[-9:] == "info.json":
                        # note that files/directory with name tmp are in .gitignore
                        tar.extract(tarinfo, path=filedir + "/tmp", set_attrs=False)
                        info_json = filedir + "/tmp/" + tarinfo.name
                        with open(info_json, "r") as f:
                            info = json.load(f)
                            jsonfilename = (
                                filedir + "/tmp/" + tarinfo.name[:-9] + info["json"]
                            )

            # now extract the large json file
            if jsonfilename is not None:
                with tarfile.open(tarfilename, "r|*") as tar:
                    for tarinfo in tar:
                        if tarinfo.isfile() and tarinfo.name in jsonfilename:
                            logger.debug("Extracting: {0}".format(tarinfo.name))
                            tar.extract(tarinfo, path=filedir + "/tmp", set_attrs=False)
        else:
            logger.debug("Tarfilename {} doesn't exist".format(tarfilename))

    except tarfile.ReadError as re:
        logger.error("Tarfile {0}: {1}".format(tarfilename, re))
    if jsonfilename is None:
        jsonfilename = filename + ".json"
    if not os.path.exists(jsonfilename):
        logger.warning(
            "Didn't find tar or json for {} {} {}".format(speaker_name, origin, version)
        )
        return None
    logger.debug("Jsonfilename {0}".format(jsonfilename))
    return jsonfilename


def parse_graph_freq_webplotdigitizer(filename):
    """ """
    # from 20Hz to 20kHz, log(2)~0.3
    ref_freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 500)
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
                udata = [
                    (data[d]["value"][0], data[d]["value"][1])
                    for d in range(0, len(data))
                ]
                sdata = sorted(udata, key=lambda a: a[0])
                # print(col['name'], len(sdata))
                # print(sdata[0])
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
                        continue
                    # look for closest match
                    while ref_freq[ref_p] <= fr:
                        if ref_p >= len(ref_freq) - 1:
                            break
                        ref_p += 1
                    # if ref_f is too large, skip
                    ref_f = ref_freq[ref_p]
                    if ref_f > frn:
                        continue
                    # linear interpolation
                    ref_db = db + ((dbn - db) * (ref_f - fr)) / (frn - fr)
                    if 0 < ref_f <= 20000 and -50 < ref_db < 200:
                        res.append([ref_f, ref_db, col["name"]])
                    else:
                        logger.info(
                            "fr={:.2f} fr_ref={:.2f} fr_n={:.2f} db={:.1f} db_ref={:.1f} db_n={:.1f}".format(
                                fr, ref_f, frn, db, ref_db, dbn
                            )
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
            freq = np.array([res[i][0] for i in range(0, len(res))]).astype(np.float)
            dB = np.array([res[i][1] for i in range(0, len(res))]).astype(np.float)
            mrt = [pretty(res[i][2]) for i in range(0, len(res))]
            df = pd.DataFrame({"Freq": freq, "dB": dB, "Measurements": mrt})
            return "CEA2034", df
    except IOError as e:
        logger.error("Cannot not open: {0}".format(e))
        return None, None


def parse_graphs_speaker_webplotdigitizer(
    speaker_path, speaker_brand, speaker_name, origin, version
):
    dfs = {}
    logger.debug("speaker_path set to {}".format(speaker_path))
    jsonfilename = parse_webplotdigitizer_get_jsonfilename(
        speaker_path, speaker_name, origin, version
    )

    if jsonfilename is None:
        logging.warning(
            "{} {} {} didn't find data file in {}".format(
                speaker_name, origin, version, speaker_path
            )
        )
        return None

    try:
        title, spin_uneven = parse_graph_freq_webplotdigitizer(jsonfilename)
        dfs = spin_compute_di_eir(speaker_name, title, spin_uneven)
    except FileNotFoundError:
        logger.info("Speaker: {0} Not found: {1}".format(speaker_name, jsonfilename))
    return dfs
