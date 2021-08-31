#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
import numpy as np
from scipy.stats import linregress

from spinorama.ltype import List, Vector, Peq
from spinorama.filter_peq import peq_build
from spinorama.filter_scores import scores_apply_filter

logger = logging.getLogger("spinorama")


# ------------------------------------------------------------------------------
# various loss function
# ------------------------------------------------------------------------------


def l2_loss(local_target: Vector, freq: Vector, peq: Peq) -> float:
    # L2 norm
    return np.linalg.norm(local_target + peq_build(freq, peq), 2)


def leastsquare_loss(
    freq: Vector, local_target: List[Vector], peq: Peq, iterations: int
) -> float:
    # sum of L2 norms if we have multiple targets
    return float(np.sum([l2_loss(lt, freq, peq) for lt in local_target]))


def flat_loss_prev(
    freq: Vector, local_target: List[Vector], peq: Peq, iterations: int, weigths: Vector
) -> float:
    # make LW as close as target as possible and SP flat
    lw = np.sum(
        [l2_loss(local_target[i], freq, peq) for i in range(0, len(local_target) - 1)]
    )
    # want sound power to be flat but not necessary aligned
    # with a target
    sp = 1.0
    if len(local_target) > 1:
        _, _, r_value, _, _ = linregress(np.log10(freq), local_target[-1])
        sp = 1 - r_value ** 2
    # * or +
    # return weigths[0]*lw+weigths[1]*sp
    return lw * sp


def flat_loss(
    freq: Vector, local_target: List[Vector], peq: Peq, iterations: int, weigths: Vector
) -> float:
    _, _, r_value, _, _ = linregress(np.log10(freq), local_target[0])
    sp = 1 - r_value ** 2
    return sp


def swap_loss(
    freq: Vector, local_target: List[Vector], peq: Peq, iteration: int
) -> float:
    # try to alternate, optimise for 1 objective then the second one
    if len(local_target) == 0 or iteration < 10:
        return l2_loss([local_target[0]], freq, peq)
    return l2_loss([local_target[1]], freq, peq)


def alternate_loss(
    freq: Vector, local_target: List[Vector], peq: Peq, iteration: int
) -> float:
    # optimise for 2 objectives 1 each time
    if 0 in (len(local_target), iteration % 2):
        return l2_loss([local_target[0]], freq, peq)
    return l2_loss([local_target[1]], freq, peq)


def score_loss(df_spin, peq):
    """Compute the preference score for speaker
    local_target: unsued
    peq: evaluated peq
    return minus score (we want to maximise the score)
    """
    _, _, score = scores_apply_filter(df_spin, peq)
    return -score["pref_score"]


def loss(df_speaker, freq, local_target, peq, iterations, optim_config):
    which_loss = optim_config["loss"]
    if which_loss == "flat_loss":
        weigths = optim_config["loss_weigths"]
        return flat_loss(freq, local_target, peq, iterations, weigths)
    if which_loss == "leastsquare_loss":
        return leastsquare_loss(freq, local_target, peq, iterations)
    if which_loss == "alternate_loss":
        return alternate_loss(freq, local_target, peq, iterations)
    if which_loss == "score_loss":
        return score_loss(df_speaker, peq)
    if which_loss == "combine_loss":
        weigths = optim_config["loss_weigths"]
        return score_loss(df_speaker, peq) + flat_loss(
            freq, local_target, peq, iterations, weigths
        )
    logger.error("loss function is unkown")
