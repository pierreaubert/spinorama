# -*- coding: utf-8 -*-
import logging
import os
import glob
import pandas as pd
from .load_misc import sort_angles

logger = logging.getLogger("spinorama")


def parse_graph_splHVtxt(dirpath, orientation):
    """Parse text files with Horizontal and Vertical data"""
    filenames = "{0}/*_{1}.txt".format(dirpath, orientation)
    files = glob.glob(filenames)
    if len(files) == 0:
        filenames = "{0}/* _{1} *.txt".format(dirpath, orientation)
        files = glob.glob(filenames)

    logger.debug("Found {} files in {}".format(len(files), dirpath))

    symmetry = True
    for file in files:
        file_format = os.path.basename(file).split()
        if len(file_format) > 2:
            angle = file_format[-1][:-4]
        else:
            angle = os.path.basename(file).split("_")[0]

        if int(angle) < 0:
            symmetry = False

    logger.info("Symmetrie is {}".format(symmetry))

    dfs = []
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

        logger.debug('read file "{}" for angle "{}"'.format(file, angle))
        with open(file, "r") as fd:
            lines = fd.readlines()
            for l in lines:
                # again 2 possible format
                # freq, db
                words = l[:-1].split(",")
                if len(words) == 2:
                    freqs.append(float(words[0]))
                    dbs.append(float(words[1]))
                    continue

                # freq db phase
                words = l.split()
                if len(words) == 2 or len(words) == 3:
                    freq = words[0]
                    db = words[1]
                    # skip first line
                    if freq[0] != "F":
                        freqs.append(float(freq))
                        dbs.append(float(db))
                    continue

                logger.warning(
                    "unkown file format len words {} for line {}".format(len(words), l)
                )

        if angle == "On Axis":
            dfs.append(pd.DataFrame({"Freq": freqs, angle: dbs}))
        else:
            if angle != "-180°":
                dfs.append(pd.DataFrame({angle: dbs}))
            if symmetry and orientation == "H" and angle != "180°":
                mangle = "-{0}".format(angle)
                dfs.append(pd.DataFrame({mangle: dbs}))

    return sort_angles(pd.concat(dfs, axis=1))


def parse_graphs_speaker_splHVtxt(speaker_path, speaker_brand, speaker_name, version):
    """2 files per directory xxx_H_IR.mat and xxx_V_IR.mat"""
    dirname = "{0}/{1}/{2}".format(speaker_path, speaker_name, version)

    logger.debug("scanning path {}".format(dirname))

    h_spl = parse_graph_splHVtxt(dirname, "H")
    v_spl = parse_graph_splHVtxt(dirname, "V")

    return h_spl, v_spl
