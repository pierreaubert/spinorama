#                                                  -*- coding: utf-8 -*-
import locale
import logging
import os
import string

import pandas as pd
from .load import graph_melt, sort_angles, filter_graphs

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

removequote = str.maketrans({'"': None, "\n": ""})

logger = logging.getLogger("spinorama")


def parse_graph_freq_klippel(filename):
    title = None
    columns = ["Freq"]
    usecols = [0]
    with open(filename) as csvfile:
        # first line is graph title
        title = csvfile.readline().split("\t")[0][1:-1]
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

    # read all columns, drop 0
    df = pd.read_csv(
        filename, sep="\t", skiprows=2, usecols=usecols, names=columns, thousands=","
    ).drop(0)
    # convert to float (issues with , and . in numbers)
    df = df.applymap(locale.atof)
    # put it in order, not relevant for pandas but for np array
    if len(df.columns) > 2 and df.columns[2] == "10°":
        return title, sort_angles(df)
    return title, df


def find_data_klippel(speaker_path, speaker_brand, speaker_name, mversion_in, csvname):
    nest = False
    mdir = []
    mversion = []
    if mversion_in == None:
        mversion.append("asr", "eac")
        mdir.append["ASR", "ErinsAudioCorner"]
    else:
        if mversion_in[0:3] in ("asr", "eac"):
            if mversion_in[0:3] == "asr":
                mversion.append(mversion_in)
                mdir.append("ASR")
            elif mversion_in[0:3] == "eac":
                mversion.append(mversion_in)
                mdir.append("ErinsAudioCorner")
            if len(mversion_in) > 3:
                nest = True

    csvfilenames = []
    if nest is False:
        for cdir in mdir:
            csvfilenames.append(
                "{0}/{3}/{1}/{2}.txt".format(speaker_path, speaker_name, csvname, cdir)
            )
    else:
        for version in mversion:
            for cdir in mdir:
                csvfilenames.append(
                    "{0}/{3}/{1}/{4}/{2}.txt".format(
                        speaker_path, speaker_name, csvname, cdir, version
                    )
                )
                csvfilenames.append(
                    "{0}/{3}/{1}/{4}/{1} -- {2}.txt".format(
                        speaker_path, speaker_name, csvname, cdir, version
                    )
                )
                csvfilenames.append(
                    "{0}/{3}/{1}/{4}/{5} -- {2}.txt".format(
                        speaker_path,
                        speaker_name,
                        csvname,
                        cdir,
                        version,
                        string.capwords(speaker_name),
                    )
                )

    # logger.warning("looking at {} option with #mdir {} #mversion {}".format(
    #    len(csvfilenames), len(mdir), len(mversion)))

    for match in csvfilenames:
        if os.path.exists(match):
            return match

    for match in csvfilenames:
        logger.debug("no match for {}".format(match))

    return None


def parse_graphs_speaker_klippel(speaker_path, speaker_brand, speaker_name, mversion):
    dfs = {}
    mandatory_csvfiles = [
        "SPL Horizontal",
        "SPL Vertical",
    ]
    found = 0
    for csv in mandatory_csvfiles:
        if (
            find_data_klippel(speaker_path, speaker_brand, speaker_name, mversion, csv)
            is not None
        ):
            found = found + 1
        else:
            logger.warning(
                "Didn't find this mandatory files {} for speaker {} {}".format(
                    csv, speaker_name, mversion
                )
            )

    if found != len(mandatory_csvfiles):
        logger.warning(
            "Didn't find all mandatory files for speaker {} {}".format(
                speaker_name, mversion
            )
        )
        return dfs

    use_all_files = False
    if use_all_files:
        csvfiles = [
            "CEA2034",
            "Early Reflections",
            "Directivity Index",
            "Estimated In-Room Response",
            "Horizontal Reflections",
            "Vertical Reflections",
        ]
        for csv in set(mandatory_csvfiles + csvfiles):
            csvfilename = None
            csvfilename2 = None
            if mversion is None or mversion == "asr":
                csvfilename = "{0}/ASR/{1}/{2}.txt".format(
                    speaker_path, speaker_name, csv
                )
            elif mversion == "eac":
                csvfilename = "{0}/ErinsAudioCorner/{1}/{2}.txt".format(
                    speaker_path, speaker_name, csv
                )
                csvfilename2 = "{0}/ErinsAudioCorner/{1}/{1} -- {2}.txt".format(
                    speaker_path, speaker_name, csv
                )
                csvfilename3 = "{0}/ErinsAudioCorner/{1}/{3} -- {2}.txt".format(
                    speaker_path, speaker_name, csv, string.capwords(speaker_name)
                )
                if not os.path.exists(csvfilename):
                    if csvfilename2 is not None and os.path.exists(csvfilename2):
                        csvfilename = csvfilename2
                    elif csvfilename3 is not None and os.path.exists(csvfilename3):
                        csvfilename = csvfilename3
                    else:
                        csvfilename = "{0}/ASR/{1}/{3}/{2}.txt".format(
                            speaker_path, speaker_name, csv, mversion
                        )
            try:
                title, df = parse_graph_freq_klippel(csvfilename)
                logger.debug(
                    "Speaker: {0} (ASR)  Loaded: {1}".format(speaker_name, csvfilename)
                )
                dfs[title + "_unmelted"] = df
                dfs[title] = graph_melt(df)
            except FileNotFoundError:
                logger.info(
                    "Speaker: {} {} Not found: {}".format(
                        speaker_name, mversion, csvfilename
                    )
                )
        return dfs
    else:
        h_name = find_data_klippel(
            speaker_path, speaker_brand, speaker_name, mversion, "SPL Horizontal"
        )
        v_name = find_data_klippel(
            speaker_path, speaker_brand, speaker_name, mversion, "SPL Vertical"
        )
        print(h_name, v_name)
        _, h_spl = parse_graph_freq_klippel(h_name)
        _, v_spl = parse_graph_freq_klippel(v_name)
        return filter_graphs(speaker_name, h_spl, v_spl)
