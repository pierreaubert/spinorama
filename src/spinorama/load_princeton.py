# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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

import glob

import numpy as np
import pandas as pd
from scipy.io import loadmat

from spinorama import logger
from spinorama.ltype import StatusOr
from spinorama.load_misc import sort_angles
from spinorama.compute_misc import resample


def parse_graph_freq_princeton_mat(mat, suffix: str, onaxis) -> StatusOr[pd.DataFrame]:
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
    df_3d3a = pd.DataFrame({"Freq": xs})
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
            df_3d3a[label] = ys
        logger.debug("%d %s", ilabel, label)
    # check empty case
    if "On Axis" not in df_3d3a:
        if suffix == "V" and onaxis is not None:
            df_3d3a["On Axis"] = onaxis
        else:
            logger.info(
                "On Axis not in %s file, keys are %s", suffix, ",".join(list(df_3d3a.keys()))
            )
            return False, pd.DataFrame()
    # sort datas
    df_3d3a_sa = sort_angles(df_3d3a)
    # precision of measurement is ok above 500
    return True, resample(df_3d3a_sa[df_3d3a_sa.Freq >= 500], 200)


def parse_graph_princeton(filename: str, orient: str, onaxis) -> StatusOr[pd.DataFrame]:
    matfile = loadmat(filename)
    return parse_graph_freq_princeton_mat(matfile, orient, onaxis)


def parse_graphs_speaker_princeton(
    speaker_path, speaker_brand, speaker_name, version, symmetry
) -> StatusOr[tuple[pd.DataFrame, pd.DataFrame]]:
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
        logger.info("Couldn't find Horizontal and Vertical IR files for speaker {:s}", speaker_name)
        logger.info("Looking in directory {:s}", matfilename)
        for d in dirpath:
            logger.info("Found file {:s}", d)
        return False, (pd.DataFrame(), pd.DataFrame())

    h_status, h_spl = parse_graph_princeton(h_file, "H", None)
    if not h_status:
        logger.info("Found file but loading didn't work for %s %s", speaker_name, version)
        return False, (pd.DataFrame(), pd.DataFrame())

    onaxis = h_spl["On Axis"]
    v_status, v_spl = parse_graph_princeton(v_file, "V", onaxis)

    if not v_status:
        logger.info("Found file but loading didn't work for %s %s", speaker_name, version)
        return False, (pd.DataFrame(), pd.DataFrame())

    return True, (h_spl, v_spl)
