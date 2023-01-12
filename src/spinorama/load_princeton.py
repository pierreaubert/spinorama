# -*- coding: utf-8 -*-
import logging
import glob
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .load_misc import sort_angles
from .compute_misc import resample

logger = logging.getLogger("spinorama")


def parse_graph_freq_princeton_mat(mat, suffix):
    """Suffix can be either H or V"""
    ir_name = "IR_{:1s}".format(suffix)
    fs_name = "fs_{:1s}".format(suffix)
    # compute Freq
    timestep = 1.0 / mat[fs_name]
    # hummm
    freq = np.fft.fftfreq(2**14, d=timestep)
    # reduce spectrum to 0 to 24kHz
    # lg = 2**14
    # 24k is lgs = int(lg/4)
    # 20k is at 3414
    lgs = 3414
    xs = freq[0][0:lgs]
    #
    df = pd.DataFrame({"Freq": xs})
    # loop over measurements (skipping the 5 increments)
    for i in range(0, 72, 1):
        # extract ir
        ir = mat[ir_name][i]
        # compute FFT
        y = np.fft.fft(ir)
        ys = np.abs(y[0:lgs])
        # check for 0 (from manual: 0 means not measured)
        if ys.max() == 0.0:
            continue
        # apply formula from paper to translate to dbFS
        ys = 105.0 + np.log10(ys) * 20.0
        # interpolate to smooth response
        # s = InterpolatedUnivariateSpline(xs, ys)
        # pretty print label, per 5 deg increment, follow klippel labelling
        ilabel = i * 5
        if ilabel > 180:
            ilabel = ilabel - 360
        label = "{:d}°".format(ilabel)
        if ilabel == 0:
            label = "On Axis"
        if ilabel % 10 == 0:
            df[label] = ys
    # check empty case
    if "On Axis" not in df.keys():
        return None
    # sort datas
    df_sa = sort_angles(df)
    # precision of measurement is ok above 500
    return resample(df_sa[df_sa.Freq >= 500], 200)


def parse_graph_princeton(filename, orient):
    matfile = loadmat(filename)
    return parse_graph_freq_princeton_mat(matfile, orient)


def parse_graphs_speaker_princeton(speaker_path, speaker_brand, speaker_name, version, symmetry):
    # 2 files per directory xxx_H_IR.mat and xxx_V_IR.mat
    matfilename = "{0}/{1}/{2}".format(speaker_path, speaker_name, version)

    dirpath = glob.glob(matfilename + "/*.mat")
    h_file = None
    v_file = None
    for d in dirpath:
        if d[-9:] == "_H_IR.mat":
            h_file = d
        elif d[-9:] == "_V_IR.mat":
            v_file = d
    if h_file is None or v_file is None:
        logger.info("Couldn't find Horizontal and Vertical IR files for speaker {:s}".format(speaker_name))
        logger.info("Looking in directory {:s}".format(matfilename))
        for d in dirpath:
            logger.info("Found file {:s}".format(d))
        return None

    h_spl = parse_graph_princeton(h_file, "H")
    v_spl = parse_graph_princeton(v_file, "V")

    return h_spl, v_spl
