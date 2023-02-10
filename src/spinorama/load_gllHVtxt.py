# -*- coding: utf-8 -*-
import logging
import os
import glob
import pandas as pd
import zipfile

from .load_misc import sort_angles

logger = logging.getLogger("spinorama")


def parse_graph_gllHVtxt(dirpath):
    """Parse text files with meridian and parallel data"""
    filepath = "{}/tmp/*".format(dirpath)
    filenames = "{}/*.txt".format(filepath)
    files = glob.glob(filenames)

    logger.debug("Found {} files in {}".format(len(files), filepath))

    spl_h = []
    spl_v = []
    already_loaded_h = set()
    already_loaded_v = set()
    for file in files:
        base = os.path.basename(file)
        file_format = base[:-4].split("-")
        meridian = int(file_format[-2][1:])
        parallel = int(file_format[-1][1:])
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
            logger.debug("skipping {} angle is {} orientation is {}".format(base, angle, orientation))
            continue

        if angle == 0:
            angle = "On Axis"
        else:
            angle = f"{angle}°"

        # print('angle is {} orientation is {}'.format(angle, orientation))

        freqs = []
        dbs = []
        with open(file, "r") as fd:
            lines = fd.readlines()
            for l in lines[6:]:
                words = l[:-1].split()
                if len(words) == 2:
                    current_freq = float(words[0])
                    current_spl = float(words[1])
                    if current_freq > 20 and current_freq < 20000:
                        freqs.append(current_freq)
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
        else:
            if angle != "-180°":
                if orientation == "H":
                    if angle not in already_loaded_h:
                        spl_h.append(pd.DataFrame({angle: dbs}))
                        already_loaded_h.add(angle)
                elif orientation == "V":
                    if angle not in already_loaded_v:
                        spl_v.append(pd.DataFrame({angle: dbs}))
                        already_loaded_v.add(angle)

    logger.debug("found {} horizontal and {} vertical measurements".format(len(spl_h), len(spl_v)))
    return sort_angles(pd.concat(spl_h, axis=1)), sort_angles(pd.concat(spl_v, axis=1))


def parse_graphs_speaker_gllHVtxt(speaker_path, speaker_brand, speaker_name, version):
    """2 files per directory xxx_H_IR.mat and xxx_V_IR.mat"""
    dirname = "{0}/{1}/{2}".format(speaker_path, speaker_name, version)

    logger.debug("scanning path {}".format(dirname))

    zipname = "{}/{}.zip".format(dirname, speaker_name)

    if not os.path.exists(zipname):
        # maybe the name is close but not exactly the name of the speaker
        guesses = glob.glob(f"{dirname}/*.zip")
        if len(guesses) == 1:
            zipname = guesses[0]
        elif len(guesses) > 1:
            logger.error("Multiple zip files in {}".format(dirname))
            return None, None
        else:
            logger.error("{} does not exist".format(zipname))
            return None, None

    tmp_dirname = "{}/tmp".format(dirname)
    try:
        with zipfile.ZipFile(zipname, "r") as gll:
            gll.extractall(tmp_dirname)
            return parse_graph_gllHVtxt(dirname)
    except zipfile.BadZipFile as bf:
        logger.error("{} is a bad zipfile".format(zipname))

    return None, None
