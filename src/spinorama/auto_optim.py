#!/usr/bin/env python
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

from typing import Literal, List, Tuple
from .ltype import Vector
from .filter_iir import Biquad
from .filter_peq import peq_build  # peq_print
from .auto_loss import loss, score_loss
from .auto_range import (
    propose_range_freq,
    propose_range_Q,
    propose_range_dbGain,
    propose_range_biquad,
)
from .auto_biquad import find_best_biquad, find_best_peak

logger = logging.getLogger("spinorama")


def optim_preflight(freq, target, auto_target_interp, optim_config):
    """Some quick checks before optim runs."""
    sz = len(freq)
    nbt = len(target)
    nbi = len(auto_target_interp)

    status = True

    if sz != len(target[0]):
        logger.error("Size mismatch #freq {} != #target {}".format(sz, len(target[0])))
        status = False

    if nbt != nbi:
        logger.error(
            "Size mismatch #target {} != #auto_target_interp {}".format(nbt, nbi)
        )
        status = False

    for i in range(0, min(nbt, nbi)):
        if len(target[i]) != len(auto_target_interp[i]):
            logger.error(
                "Size mismatch #target[{0}] {1} != #auto_target_interp[{0}] {2}".format(
                    i, len(target[i]), len(auto_target_interp[i])
                )
            )
            status = False

    return status


def optim_compute_auto_target(freq, target, auto_target_interp, peq):
    peq_freq = peq_build(freq, peq)
    return [target[i] - auto_target_interp[i] + peq_freq for i, _ in enumerate(target)]


def optim_greedy(
    speaker_name: str,
    df_speaker: dict,
    freq: Vector,
    auto_target: List[Vector],
    auto_target_interp: List[Vector],
    optim_config: dict,
    use_score,
) -> List[Tuple[int, float, float]]:

    if optim_preflight(freq, auto_target, auto_target_interp, optim_config) is False:
        logger.error("Preflight check failed!")
        return None, None

    auto_peq = []
    current_auto_target = optim_compute_auto_target(
        freq, auto_target, auto_target_interp, auto_peq
    )
    best_loss = loss(freq, auto_target, auto_peq, 0, optim_config)
    pref_score = 1.0
    if use_score:
        pref_score = score_loss(df_speaker, auto_peq)

    results = [(0, best_loss, -pref_score)]
    logger.info(
        "OPTIM {} START {} #PEQ {:d} Freq #{:d} Gain #{:d} +/-[{}, {}] Q #{} [{}, {}] Loss {:2.2f} Score {:2.2f}".format(
            speaker_name,
            optim_config["curve_names"],
            optim_config["MAX_NUMBER_PEQ"],
            optim_config["MAX_STEPS_FREQ"],
            optim_config["MAX_STEPS_DBGAIN"],
            optim_config["MIN_DBGAIN"],
            optim_config["MAX_DBGAIN"],
            optim_config["MAX_STEPS_Q"],
            optim_config["MIN_Q"],
            optim_config["MAX_Q"],
            best_loss,
            -pref_score,
        )
    )

    for optim_iter in range(0, optim_config["MAX_NUMBER_PEQ"]):

        # we are optimizing above my_freq_reg_min hz on anechoic data
        current_auto_target = optim_compute_auto_target(
            freq, auto_target, auto_target_interp, auto_peq
        )

        # greedy strategy: look for lowest & highest peak
        sign, init_freq, init_freq_range = propose_range_freq(
            freq, current_auto_target[0], optim_config
        )
        init_dbGain_range = propose_range_dbGain(
            freq, current_auto_target[0], sign, init_freq, optim_config
        )
        init_Q_range = propose_range_Q(optim_config)
        biquad_range = propose_range_biquad(optim_config)

        (
            state,
            current_type,
            current_freq,
            current_Q,
            current_dbGain,
            current_loss,
            current_nit,
        ) = (False, -1, -1, -1, -1, -1, -1)
        if optim_config["full_biquad_optim"] is True:
            (
                state,
                current_type,
                current_freq,
                current_Q,
                current_dbGain,
                current_loss,
                current_nit,
            ) = find_best_biquad(
                freq,
                current_auto_target,
                init_freq_range,
                init_Q_range,
                init_dbGain_range,
                biquad_range,
                optim_iter,
                optim_config,
            )
        else:
            (
                state,
                current_type,
                current_freq,
                current_Q,
                current_dbGain,
                current_loss,
                current_nit,
            ) = find_best_peak(
                freq,
                current_auto_target,
                init_freq_range,
                init_Q_range,
                init_dbGain_range,
                biquad_range,
                optim_iter,
                optim_config,
            )
        if state:
            biquad = (
                1.0,
                Biquad(current_type, current_freq, 48000, current_Q, current_dbGain),
            )
            auto_peq.append(biquad)
            best_loss = current_loss
            if use_score:
                pref_score = score_loss(df_speaker, auto_peq)
            results.append((optim_iter + 1, best_loss, -pref_score))
            logger.info(
                "Speaker {} Iter {:2d} Optim converged loss {:2.2f} pref score {:2.2f} biquad {:2s} F:{:5.0f}Hz Q:{:2.2f} G:{:+2.2f}dB in {} iterations".format(
                    speaker_name,
                    optim_iter,
                    best_loss,
                    -pref_score,
                    biquad[1].type2str(),
                    current_freq,
                    current_Q,
                    current_dbGain,
                    current_nit,
                )
            )
        else:
            logger.error(
                "Speaker {} Skip failed optim for best {:2.2f} current {:2.2f}".format(
                    speaker_name, best_loss, current_loss
                )
            )
            break

    # recompute auto_target with the full auto_peq
    current_auto_target = optim_compute_auto_target(
        freq, auto_target, auto_target_interp, auto_peq
    )
    # final_loss = loss(freq, current_auto_target, [], 0, optim_config)
    # final_score = 1.0
    # if use_score:
    #    final_score = score_loss(df_speaker, auto_peq)
    if results[-1][1] < best_loss:
        results.append((optim_config["MAX_NUMBER_PEQ"] + 1, best_loss, -pref_score))
    if use_score:
        idx_max = np.argmax((np.array(results).T)[-1])
        results = results[0 : idx_max + 1]
        auto_peq = auto_peq[0 : idx_max + 1]
    logger.info(
        "OPTIM END {}: best loss {:2.2f} final score {:2.2f} with {:2d} PEQs".format(
            speaker_name, results[-1][1], results[-1][2], len(auto_peq)
        )
    )
    return results, auto_peq
