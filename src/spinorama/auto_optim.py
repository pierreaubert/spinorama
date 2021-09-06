#!/usr/bin/env python
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-21 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
import pandas as pd
import time
from typing import Literal
from ray import tune as raytune
import flaml


from .ltype import Peq, FloatVector1D
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


def optim_preflight(
    freq: FloatVector1D,
    target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    optim_config: dict,
) -> bool:
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


def optim_compute_auto_target(
    freq: FloatVector1D,
    target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    peq: Peq,
):
    peq_freq = peq_build(freq, peq)
    return [target[i] - auto_target_interp[i] + peq_freq for i, _ in enumerate(target)]


def optim_greedy(
    speaker_name: str,
    df_speaker: dict[str, pd.DataFrame],
    freq: FloatVector1D,
    auto_target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    optim_config: dict,
    use_score,
) -> tuple[list[tuple[int, float, float]], Peq]:

    if not optim_preflight(freq, auto_target, auto_target_interp, optim_config):
        logger.error("Preflight check failed!")
        return ([(0, 0, 0)], [])

    auto_peq = []
    current_auto_target = optim_compute_auto_target(
        freq, auto_target, auto_target_interp, auto_peq
    )
    best_loss = loss(df_speaker, freq, auto_target, auto_peq, 0, optim_config)
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
                df_speaker,
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
                df_speaker,
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
            results.append((int(optim_iter + 1), float(best_loss), float(-pref_score)))
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


def optim_flaml(
    speaker_name: str,
    df_speaker: dict[str, pd.DataFrame],
    optim_config: dict,
    greedy_results,
    greedy_peq,
) -> tuple[list[tuple[int, float, float]], Peq]:

    init_loss = greedy_results[-1][1]

    low_cost_partial_config = {}
    config = {}
    for i, _ in enumerate(greedy_peq):
        config["freq_{}".format(i)] = raytune.quniform(-100, 100, 1)
        config["Q_{}".format(i)] = raytune.quniform(-1, 1, 0.1)
        config["dbGain_{}".format(i)] = raytune.quniform(-4, 2, 0.2)
        low_cost_partial_config["freq_{}".format(i)] = 0.0
        low_cost_partial_config["Q_{}".format(i)] = 0.0
        low_cost_partial_config["dbGain_{}".format(i)] = 0.0

    def init_delta(config):
        return [
            (
                c,
                Biquad(
                    p.typ,
                    max(20, p.freq + config["freq_{}".format(i)]),
                    p.srate,
                    max(0.01, p.Q + config["Q_{}".format(i)]),
                    min(p.dbGain + config["dbGain_{}".format(i)], 6),
                ),
            )
            for i, (c, p) in enumerate(greedy_peq)
        ]

    def evaluate_config(config):
        eval_peq = init_delta(config)
        score = score_loss(df_speaker, eval_peq)
        raytune.report(score=score)

    time_budget_s = 300
    num_samples = -1

    # set up CFO and blendsearch
    cfo = flaml.CFO(low_cost_partial_config=low_cost_partial_config)
    blendsearch = flaml.BlendSearch(
        metric="score",
        mode="min",
        space=config,
        low_cost_partial_config=low_cost_partial_config,
    )
    blendsearch.set_search_properties(config={"time_budget_s": time_budget_s})

    analysis = raytune.run(
        evaluate_config,
        config=config,
        metric="score",
        mode="min",
        num_samples=num_samples,
        time_budget_s=time_budget_s,
        local_dir="logs/",
        search_alg=cfo,
        # search_alg=blendsearch  # or cfo
    )

    print(analysis.best_trial.last_result)
    print(analysis.best_config)

    final_loss = -analysis.best_trial.last_result["score"]
    if final_loss > init_loss:
        final_results = greedy_results
        final_results.append([greedy_results[-1][0] + 1, final_loss, final_loss])
        final_peq = init_delta(analysis.best_config)
        return final_results, final_peq
    else:
        return greedy_results, greedy_peq


def optim_multi_steps(
    speaker_name: str,
    df_speaker: dict,
    freq: FloatVector1D,
    auto_target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    optim_config: dict,
    use_score,
) -> tuple[list[tuple[int, float, float]], Peq]:

    greedy_results, greedy_peq = optim_greedy(
        speaker_name,
        df_speaker,
        freq,
        auto_target,
        auto_target_interp,
        optim_config,
        use_score,
    )

    if not use_score:
        return greedy_results, greedy_peq

    return optim_flaml(
        speaker_name,
        df_speaker,
        optim_config,
        greedy_results,
        greedy_peq,
    )
