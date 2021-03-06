#                                                  -*- coding: utf-8 -*-
import locale
import logging
import pandas as pd
from .load import graph_melt, sort_angles

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


def parse_graphs_speaker_klippel(speaker_path, speaker_brand, speaker_name, mversion):
    dfs = {}
    csvfiles = [
        "CEA2034",
        "Early Reflections",
        "Directivity Index",
        "Estimated In-Room Response",
        "Horizontal Reflections",
        "Vertical Reflections",
        "SPL Horizontal",
        "SPL Vertical",
    ]
    for csv in csvfiles:
        csvfilename = None
        if mversion is None or mversion == "asr":
            csvfilename = "{0}/ASR/{1}/{2}.txt".format(speaker_path, speaker_name, csv)
        elif mversion == 'eac':
            csvfilename = "{0}/ErinsAudioCorner/{1}/{2}.txt".format(speaker_path, speaker_name, csv)
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
                "Speaker: {0} (ASR) Not found: {1}".format(speaker_name, csvfilename)
            )
    return dfs
