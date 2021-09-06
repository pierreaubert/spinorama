#                                                  -*- coding: utf-8 -*-
import locale
import logging
import os

import pandas as pd
from .load_misc import graph_melt, sort_angles
from .load import filter_graphs, symmetrise_measurement

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

removequote = str.maketrans({'"': None, "\n": ""})

logger = logging.getLogger("spinorama")


def parse_graph_freq_klippel(filename: str) -> tuple[str, pd.DataFrame]:
    """Parse a klippel generated file"""
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


def find_data_klippel(
    speaker_path, speaker_brand, speaker_name, mversion_in, csvname
) -> str:
    """return the expected filename for Klippel data"""
    csvfilename = "{}/{}/{}/{}.txt".format(
        speaker_path, speaker_name, mversion_in, csvname
    )

    if os.path.exists(csvfilename):
        return csvfilename

    logger.debug("no match for {}".format(csvfilename))
    return ""


def parse_graphs_speaker_klippel(
    speaker_path, speaker_brand, speaker_name, mversion, symmetry
):
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
            logger.info(
                "Didn't find this mandatory files {} for speaker {} {}".format(
                    csv, speaker_name, mversion
                )
            )

    if found != len(mandatory_csvfiles):
        logger.info(
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
            csvfilename = find_data_klippel(
                speaker_path, speaker_brand, speaker_name, mversion, csv
            )
            try:
                title, df = parse_graph_freq_klippel(csvfilename)
                dfs[title + "_unmelted"] = df
                dfs[title] = graph_melt(df)
                logger.debug(
                    "Speaker: {0} (Klippel)  Loaded: {1}".format(
                        speaker_name, csvfilename
                    )
                )
            except FileNotFoundError:
                logger.info(
                    "Speaker: {} {} Not found: {}".format(
                        speaker_name, mversion, csvfilename
                    )
                )
        return dfs

    h_name = find_data_klippel(
        speaker_path, speaker_brand, speaker_name, mversion, "SPL Horizontal"
    )
    v_name = find_data_klippel(
        speaker_path, speaker_brand, speaker_name, mversion, "SPL Vertical"
    )
    # print(h_name, v_name)
    _, h_spl = parse_graph_freq_klippel(h_name)
    _, v_spl = parse_graph_freq_klippel(v_name)
    logger.debug("Speaker: {0} (Klippel) loaded".format(speaker_name))

    if symmetry == "coaxial":
        h_spl2 = symmetrise_measurement(h_spl)
        if v_spl is None:
            v_spl2 = h_spl2.copy()
        else:
            v_spl2 = symmetrise_measurement(v_spl)
        return filter_graphs(speaker_name, h_spl2, v_spl2)

    if symmetry == "horizontal":
        h_spl2 = symmetrise_measurement(h_spl)
        return filter_graphs(speaker_name, h_spl2, v_spl)

    return filter_graphs(speaker_name, h_spl, v_spl)
