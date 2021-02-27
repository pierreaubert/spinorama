#                                                  -*- coding: utf-8 -*-
import logging
import glob
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .load import filter_graphs, sort_angles


logger = logging.getLogger("spinorama")


def parse_graph_freq_princeton_mat(mat, suffix):
    """ Suffix can be either H or V """
    ir_name = "IR_{:1s}".format(suffix)
    fs_name = "fs_{:1s}".format(suffix)
    # compute Freq
    timestep = 1.0 / mat[fs_name]
    # hummm
    freq = np.fft.fftfreq(2 ** 14, d=timestep)
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
        df[label] = ys
    # check empty case
    if "On Axis" not in df.keys():
        return None
    # sort datas
    df_sa = sort_angles(df)
    # precision of measurement is ok above 500
    return df_sa[df_sa.Freq >= 500]


def parse_graph_princeton(filename, orient):
    matfile = loadmat(filename)
    return parse_graph_freq_princeton_mat(matfile, orient)


def symmetrise_measurement(spl):
    if spl is None:
        return None

    # look for min and max
    cols = spl.columns
    min_angle = 180
    max_angle = -180
    for col in cols:
        if col != "Freq":
            angle = None
            if col == "On Axis":
                angle = 0
            else:
                angle = int(col[:-1])
            min_angle = min(min_angle, angle)
            max_angle = max(min_angle, angle)
    # print('min {} max {}'.format(min_angle, max_angle))

    # extend 0-180 to -170 0 180
    # extend 0-90  to -90 to 90
    new_spl = spl.copy()
    for col in cols:
        if col not in ("Freq", "On Axis", "180°") and col[0] != '-':
            mangle = "-{}".format(col)
            if mangle not in spl.columns:
                new_spl[mangle] = spl[col]
    return sort_angles(new_spl)


def parse_graphs_speaker_princeton(
    speaker_path, speaker_brand, speaker_name, version, symmetry
):
    # 2 files per directory xxx_H_IR.mat and xxx_V_IR.mat
    matfilename = "{0}/Princeton/{1}".format(speaker_path, speaker_name)
    if version is not None and version != "princeton":
        matfilename = "{0}/Princeton/{1}/{2}".format(
            speaker_path, speaker_name, version
        )

    dirpath = glob.glob(matfilename + "/*.mat")
    h_file = None
    v_file = None
    for d in dirpath:
        if d[-9:] == "_H_IR.mat":
            h_file = d
        elif d[-9:] == "_V_IR.mat":
            v_file = d
    if h_file is None or v_file is None:
        logger.info(
            "Couldn't find Horizontal and Vertical IR files for speaker {:s}".format(
                speaker_name
            )
        )
        logger.info("Looking in directory {:s}".format(matfilename))
        for d in dirpath:
            logger.info("Found file {:s}".format(d))
        return None

    h_spl = parse_graph_princeton(h_file, "H")
    v_spl = parse_graph_princeton(v_file, "V")

    if symmetry == "coaxial":
        h_spl2 = symmetrise_measurement(h_spl)
        if v_spl is None:
            v_spl2 = h_spl2.copy()
        else:
            v_spl2 = symmetrise_measurement(v_spl)
        return filter_graphs(speaker_name, h_spl2, v_spl2)
    elif symmetry == "horizontal":
        h_spl2 = symmetrise_measurement(h_spl)
        return filter_graphs(speaker_name, h_spl2, v_spl)

    return filter_graphs(speaker_name, h_spl, v_spl)




