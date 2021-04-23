#                                                  -*- coding: utf-8 -*-
import logging
import json
import math
import numpy as np
import os
import pandas as pd
import tarfile
from .compute_cea2034 import estimated_inroom
from .compute_normalize import unify_freq
from .load import graph_melt


pd.set_option("display.max_rows", 1000)

logger = logging.getLogger("spinorama")


def parse_webplotdigitizer_get_jsonfilename(dirname, speaker_name, origin, version):
    filename = None
    if dirname[-1] == "/":
        filename = dirname + speaker_name
    else:
        filename = dirname + "/" + speaker_name
    if origin == "Misc":
        filename = "{0}/{1}".format(dirname, speaker_name)
    else:
        if version is not None and version not in ("vendor", "eac"):
            filename = "{0}/{1}/{2}".format(dirname, version, speaker_name)

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
                        tar.extract(tarinfo, path=dirname + "/tmp", set_attrs=False)
                        info_json = dirname + "tmp/" + tarinfo.name
                        with open(info_json, "r") as f:
                            info = json.load(f)
                            jsonfilename = (
                                dirname + "tmp/" + tarinfo.name[:-9] + info["json"]
                            )

            # now extract the large json file
            if jsonfilename is not None:
                with tarfile.open(tarfilename, "r|*") as tar:
                    for tarinfo in tar:
                        if tarinfo.isfile() and tarinfo.name in jsonfilename:
                            logger.debug("Extracting: {0}".format(tarinfo.name))
                            tar.extract(tarinfo, path=dirname + "/tmp", set_attrs=False)
        else:
            logger.debug("Tarfilename {} doesn't exist".format(tarfilename))

    except tarfile.ReadError as re:
        logger.error("Tarfile {0}: {1}".format(tarfilename, re))
    if jsonfilename is None:
        jsonfilename = filename + ".json"
    if not os.path.exists(jsonfilename):
        logger.warning("jsonfilename {} doesn't exist".format(jsonfilename))
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


def parse_graph_freq_webplotdigitizer_check(speaker_name, df_spin):
    status = True
    spin_cols = set(df_spin.Measurements.values)
    mandatory_cols = ("Listening Window", "On Axis", "Early Reflections", "Sound Power")
    other_cols = ("Early Reflections DI", "Sound Power DI")
    for col in mandatory_cols:
        if col not in spin_cols:
            logger.warning(
                "{} measurement doesn't have a {} column".format(speaker_name, col)
            )
            status = False
        else:
            logging.debug(
                "Loading {:s} {:s} {:.1f}--{:.1f}Hz {:.1f}--{:.1f}dB".format(
                    speaker_name,
                    col,
                    df_spin.loc[df_spin.Measurements == col].Freq.min(),
                    df_spin.loc[df_spin.Measurements == col].Freq.max(),
                    df_spin.loc[df_spin.Measurements == col].dB.min(),
                    df_spin.loc[df_spin.Measurements == col].dB.max(),
                )
            )
    for col in spin_cols:
        if col not in mandatory_cols and col not in other_cols:
            logger.warning(
                "{} measurement have extra column {}".format(speaker_name, col)
            )
    return status


def parse_graphs_speaker_webplotdigitizer(
    speaker_path, speaker_brand, speaker_name, origin, version
):
    dfs = {}
    dirname = None
    if origin in ("ASR", "ErinsAudioCorner"):
        dirname = "{0}/{1}/{2}/".format(speaker_path, origin, speaker_name)
    elif origin in ("Misc"):
        dirname = "{0}/Misc/{1}/{2}/".format(speaker_path, speaker_brand, speaker_name)
    else:
        dirname = "{0}/Vendors/{1}/{2}/".format(
            speaker_path, speaker_brand, speaker_name
        )
    logger.debug("dirname set to {}".format(dirname))
    jsonfilename = parse_webplotdigitizer_get_jsonfilename(
        dirname, speaker_name, origin, version
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
        if not parse_graph_freq_webplotdigitizer_check(speaker_name, spin_uneven):
            logger.warning("title is {0}".format(title))
            return None

        spin_even = unify_freq(spin_uneven)
        spin = graph_melt(spin_even)
        if title != "CEA2034":
            logger.debug("title is {0}".format(title))
            return None

        if spin is not None:
            # compute EIR
            on = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
            lw = spin.loc[spin["Measurements"] == "Listening Window"].reset_index(
                drop=True
            )
            er = spin.loc[spin["Measurements"] == "Early Reflections"].reset_index(
                drop=True
            )
            sp = spin.loc[spin["Measurements"] == "Sound Power"].reset_index(drop=True)

            # check DI index
            if 0 not in (lw.shape[0], sp.shape[0]):
                sp_di_computed = lw.dB - sp.dB
                sp_di = spin.loc[spin["Measurements"] == "Sound Power DI"].reset_index(
                    drop=True
                )
                if sp_di.shape[0] == 0:
                    logger.debug("No Sound Power DI curve, computing one!")
                    df2 = pd.DataFrame(
                        {
                            "Freq": on.Freq,
                            "dB": sp_di_computed,
                            "Measurements": "Sound Power DI",
                        }
                    )
                    spin = spin.append(df2).reset_index(drop=True)
                else:
                    delta = np.mean(sp_di) - np.mean(sp_di_computed)
                    logger.debug("Sound Power DI curve: removing {0}".format(delta))
                    spin.loc[spin["Measurements"] == "Sound Power DI", "dB"] -= delta

                # sp_di = spin.loc[spin['Measurements'] == 'Sound Power DI'].reset_index(drop=True)
                logger.debug(
                    "Post treatment SP DI: shape={0} min={1} max={2}".format(
                        sp_di.shape, sp_di_computed.min(), sp_di_computed.max()
                    )
                )
                # print(sp_di)
            else:
                logger.debug("Shape LW={0} SP={1}".format(lw.shape, sp.shape))

            if 0 not in (lw.shape[0], er.shape[0]):
                er_di_computed = lw.dB - er.dB
                er_di = spin.loc[
                    spin["Measurements"] == "Early Reflections DI"
                ].reset_index(drop=True)
                if er_di.shape[0] == 0:
                    logger.debug("No Early Reflections DI curve!")
                    df2 = pd.DataFrame(
                        {
                            "Freq": on.Freq,
                            "dB": er_di_computed,
                            "Measurements": "Early Reflections DI",
                        }
                    )
                    spin = spin.append(df2).reset_index(drop=True)
                else:
                    delta = np.mean(er_di) - np.mean(er_di_computed)
                    logger.debug(
                        "Early Reflections DI curve: removing {0}".format(delta)
                    )
                    spin.loc[
                        spin["Measurements"] == "Early Reflections DI", "dB"
                    ] -= delta

                # er_di = spin.loc[spin['Measurements'] == 'Early Reflections DI'].reset_index(drop=True)
                logger.debug(
                    "Post treatment ER DI: shape={0} min={1} max={2}".format(
                        er_di.shape, er_di_computed.min(), er_di_computed.max()
                    )
                )
                # print(er_di)
            else:
                logger.debug("Shape LW={0} ER={1}".format(lw.shape, er.shape))

            di_offset = spin.loc[spin["Measurements"] == "DI offset"].reset_index(
                drop=True
            )
            if di_offset.shape[0] == 0:
                logger.debug("No DI offset curve!")
                df2 = pd.DataFrame(
                    {"Freq": on.Freq, "dB": 0, "Measurements": "DI offset"}
                )
                spin = spin.append(df2).reset_index(drop=True)

            logger.debug(
                "Shape ON {0} LW {1} ER {2} SP {3}".format(
                    on.shape, lw.shape, er.shape, sp.shape
                )
            )
            if 0 not in (lw.shape[0], er.shape[0], sp.shape[0]):
                eir = estimated_inroom(lw, er, sp)
                logger.debug("eir {0}".format(eir.shape))
                # print(eir)
                dfs["Estimated In-Room Response"] = graph_melt(eir)
            else:
                logger.debug(
                    "Shape LW={0} ER={1} SP={2}".format(lw.shape, er.shape, sp.shape)
                )

            # add spin (at the end because we could have modified DI curves
            dfs[title] = spin

            if on.isna().values.any():
                logger.error("On Axis has NaN values")

    except FileNotFoundError:
        logger.info("Speaker: {0} Not found: {1}".format(speaker_name, jsonfilename))
    return dfs
