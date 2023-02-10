#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2022 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import logging
import math
import numpy as np
from scipy.stats import linregress

from .load_misc import graph_melt
from .compute_cea2034 import estimated_inroom_HV
from spinorama.ltype import List, Vector, Peq
from spinorama.filter_peq import peq_build
from spinorama.filter_scores import scores_apply_filter
from .filter_peq import peq_apply_measurements

logger = logging.getLogger("spinorama")


# ------------------------------------------------------------------------------
# various loss function
# ------------------------------------------------------------------------------


def l2_loss(local_target: Vector, freq: Vector, peq: Peq) -> float:
    # L2 norm
    return np.linalg.norm(local_target + peq_build(freq, peq), 2)


def leastsquare_loss(freq: Vector, local_target: List[Vector], peq: Peq, iterations: int) -> float:
    # sum of L2 norms if we have multiple targets
    l = [l2_loss(lt, freq, peq) for lt in local_target]
    return math.sqrt(np.square(l).sum())


def flat_loss(freq: Vector, local_target: List[Vector], peq: Peq, iterations: int, weigths: Vector) -> float:
    # make LW as close as target as possible and SP flat
    lw = np.sum([l2_loss(local_target[i], freq, peq) for i in range(0, len(local_target) - 1)])
    # want sound power to be flat but not necessary aligned
    # with a target
    sp = 1.0
    if len(local_target) > 1:
        _, _, r_value, _, _ = linregress(np.log10(freq), local_target[-1])
        sp = 1 - r_value**2
    # * or +
    # return weigths[0]*lw+weigths[1]*sp
    return lw * sp


def flat_loss_exp(freq: Vector, local_target: List[Vector], peq: Peq, iterations: int, weigths: Vector) -> float:
    _, _, r_value, _, _ = linregress(np.log10(freq), local_target[0])
    sp = 1 - r_value**2
    return sp


def swap_loss(freq: Vector, local_target: List[Vector], peq: Peq, iteration: int) -> float:
    # try to alternate, optimise for 1 objective then the second one
    if len(local_target) == 0 or iteration < 10:
        return l2_loss([local_target[0]], freq, peq)
    return l2_loss([local_target[1]], freq, peq)


def alternate_loss(freq: Vector, local_target: List[Vector], peq: Peq, iteration: int) -> float:
    # optimise for 2 objectives 1 each time
    if 0 in (len(local_target), iteration % 2):
        return l2_loss([local_target[0]], freq, peq)
    return l2_loss([local_target[1]], freq, peq)


def flat_pir(freq, df_spin, peq):
    """Flatten the PIR"""
    pir_filtered = df_spin.get("Estimated In-Room Response_unmelted", None)
    if pir_filtered is None:
        spl_h = df_spin["SPL Horizontal_unmelted"]
        spl_v = df_spin["SPL Vertical_unmelted"]
        # apply EQ to all horizontal and vertical measurements
        spl_h_filtered = peq_apply_measurements(spl_h, peq)
        spl_v_filtered = peq_apply_measurements(spl_v, peq)
        # compute pir
        pir_filtered = graph_melt(estimated_inroom_HV(spl_h_filtered, spl_v_filtered))
    else:
        if len(peq) > 0:
            pir_filtered["Estimated In-Room Response"].add(peq_build(pir_filtered.Freq.values, peq))
        pir_filtered = graph_melt(pir_filtered)

    data = pir_filtered.loc[(pir_filtered.Freq >= 100) & (pir_filtered.Freq <= 16000)]
    _, _, r_value, _, _ = linregress(np.log10(data.Freq), data.dB)
    return r_value**2


def score_loss(df_spin, peq):
    """Compute the preference score for speaker
    local_target: unsued
    peq: evaluated peq
    return minus score (we want to maximise the score)
    """
    _, _, score = scores_apply_filter(df_spin, peq)
    # if len(peq)>0:
    #    print('{} {}'.format(score.get("pref_score", -1000), peq[0][1]))
    return -score["pref_score"]


def loss(df_speaker, freq, local_target, peq, iterations, optim_config):
    """Compute the loss and switch to the one defined in the config"""
    which_loss = optim_config["loss"]
    if which_loss == "flat_loss":
        weigths = optim_config["loss_weigths"]
        return flat_loss(freq, local_target, peq, iterations, weigths)
    if which_loss == "leastsquare_loss":
        return leastsquare_loss(freq, local_target, peq, iterations)
    if which_loss == "alternate_loss":
        return alternate_loss(freq, local_target, peq, iterations)
    if which_loss == "flat_pir":
        return flat_pir(freq, df_speaker, peq)
    if which_loss == "score_loss":
        return score_loss(df_speaker, peq)
    if which_loss == "combine_loss":
        weigths = optim_config["loss_weigths"]
        return score_loss(df_speaker, peq) + flat_loss(freq, local_target, peq, iterations, weigths)
    logger.error("loss function is unkown")
