#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import math
import pandas as pd
import time
from typing import Literal
from ray import tune
from ray.tune.schedulers import (
    PopulationBasedTraining,
    AsyncHyperBandScheduler,
    ASHAScheduler,
)
from ray.tune.schedulers.pb2 import PB2
from ray.tune.suggest import ConcurrencyLimiter
from ray.tune.suggest.flaml import CFO, BlendSearch
from ray.tune.suggest.bayesopt import BayesOptSearch

from .ltype import Peq, FloatVector1D
from .filter_iir import Biquad
from .filter_peq import peq_build, peq_print
from .auto_loss import loss, score_loss, flat_loss, leastsquare_loss, flat_pir
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


def savitzky_golay(y, window_size, order, deriv=0, rate=1):
    r"""Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    Examples
    --------
    t = np.linspace(-4, 4, 500)
    y = np.exp( -t**2 ) + np.random.normal(0, 0.05, t.shape)
    ysg = savitzky_golay(y, window_size=31, order=4)
    import matplotlib.pyplot as plt
    plt.plot(t, y, label='Noisy signal')
    plt.plot(t, np.exp(-t**2), 'k', lw=1.5, label='Original signal')
    plt.plot(t, ysg, 'r', label='Filtered signal')
    plt.legend()
    plt.show()
    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """
    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError as msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size - 1) // 2
    # precompute coefficients
    b = np.mat(
        [[k ** i for i in order_range] for k in range(-half_window, half_window + 1)]
    )
    m = np.linalg.pinv(b).A[deriv] * rate ** deriv * math.factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs(y[1 : half_window + 1][::-1] - y[0])
    lastvals = y[-1] + np.abs(y[-half_window - 1 : -1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve(m[::-1], y, mode="valid")


def optim_compute_auto_target(
    freq: FloatVector1D,
    target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    peq: Peq,
    optim_config: dict,
):
    peq_freq = peq_build(freq, peq)
    delta = [target[i] - auto_target_interp[i] + peq_freq for i, _ in enumerate(target)]
    if optim_config.get("smooth_measurements"):
        window_size = optim_config.get("smooth_window_size")
        order = optim_config.get("smooth_order")
        smoothed = [savitzky_golay(d, window_size, order) for d in delta]
        logger.warning(smoothed)
        return smoothed
    return delta


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
        freq, auto_target, auto_target_interp, auto_peq, optim_config
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
            freq, auto_target, auto_target_interp, auto_peq, optim_config
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
        freq, auto_target, auto_target_interp, auto_peq, optim_config
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


# def optim_flat(
#     speaker_name: str,
#     df_speaker: dict[str, pd.DataFrame],
#     freq: FloatVector1D,
#     auto_target: list[FloatVector1D],
#     auto_target_interp: list[FloatVector1D],
#     optim_config: dict,
#     greedy_results,
#     greedy_peq,
# ) -> tuple[list[tuple[int, float, float]], Peq]:
#
#     # loss from previous optim algo
#     init_loss = greedy_results[-1][2]
#
#     low_cost_partial_config = {}
#     config = {}
#     for i, _ in enumerate(greedy_peq):
#         config["freq_{}".format(i)] = tune.qloguniform(100, 20000, 1)
#
#     for i, _ in enumerate(greedy_peq):
#         low_cost_partial_config["freq_{}".format(i)] = 0.0
#
#     def evaluate_config(current_config, checkpoint_dir=None):
#         current_min = 1000.0
#         for Q in np.linspace(1, 6, 50):
#             for dB in np.linspace(-6, 6, 120):
#                 eval_peq = [
#                     (1.0, Biquad(3, current_config["freq_{}".format(i)], 48000, Q, dB))
#                     for i, _ in enumerate(current_config)
#                 ]
#                 current_auto_target = optim_compute_auto_target(
#                     freq, auto_target, auto_target_interp, eval_peq
#                 )
#                 current_min = min(
#                     current_min,
#                     flat_loss(freq, current_auto_target, eval_peq, 0, [1, 1]),
#                 )
#
#         tune.report(score=current_min)
#
#     time_budget_s = 30
#     num_samples = 750
#
#     # possible schedulers
#     pbt = PopulationBasedTraining(
#         time_attr="training_iteration",
#         perturbation_interval=10,
#     )
#
#     asha = ASHAScheduler(
#         time_attr="training_iteration",
#         max_t=100,
#         grace_period=10,
#         reduction_factor=3,
#         brackets=1,
#     )
#
#     # possible search algos
#     algo_cfo = CFO(low_cost_partial_config=low_cost_partial_config)
#     algo_blendsearch = BlendSearch(low_cost_partial_config=low_cost_partial_config)
#     algo_bos = BayesOptSearch(utility_kwargs={"kind": "ucb", "kappa": 2.5, "xi": 0.0})
#     algo = ConcurrencyLimiter(algo_bos, max_concurrent=128)
#
#     analysis = tune.run(
#         evaluate_config,
#         config=config,
#         metric="score",
#         mode="min",
#         num_samples=num_samples,
#         time_budget_s=time_budget_s,
#         local_dir="logs/",
#         # search_alg=algo, # bos working well
#         # scheduler=asha,
#         scheduler=pbt,
#         verbose=1,
#         stop={"training_iteration": 128, "score": init_loss * 0.98},
#     )
#
#     print(analysis.best_trial.last_result)
#     print(analysis.best_config)
#
#     final_loss = score_loss(df_speaker, analysis.best_config)
#     print(final_loss, init_loss)
#     if final_loss > init_loss:
#         final_results = greedy_results
#         final_results.append([greedy_results[-1][0] + 1, final_loss, final_loss])
#         final_peq = init_delta(analysis.best_config)
#         return final_results, final_peq
#     else:
#         return greedy_results, greedy_peq


def optim_refine(
    speaker_name: str,
    df_speaker: dict[str, pd.DataFrame],
    freq: FloatVector1D,
    auto_target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    optim_config: dict,
    greedy_results,
    greedy_peq,
) -> tuple[list[tuple[int, float, float]], Peq]:

    # loss from previous optim algo
    init_loss = greedy_results[-1][2]

    low_cost_partial_config = {}
    config = {}
    for i, (_, i_peq) in enumerate(greedy_peq):
        f_i = int(i_peq.freq * 0.3)
        config["freq_{}".format(i)] = tune.quniform(-f_i, f_i, 1)
        q_i = int(i_peq.Q * 6) / 10
        config["Q_{}".format(i)] = tune.quniform(-q_i, q_i, 0.01)
        db_i = int(i_peq.dbGain * 6) / 10
        config["dbGain_{}".format(i)] = tune.quniform(-db_i, db_i, 0.01)

    for i, _ in enumerate(greedy_peq):
        low_cost_partial_config["freq_{}".format(i)] = 0.0
        low_cost_partial_config["Q_{}".format(i)] = 0.0
        low_cost_partial_config["dbGain_{}".format(i)] = 0.0

    def init_delta(current_config):
        return [
            (
                c,
                Biquad(
                    # p.typ,
                    p.typ,
                    # p.freq,
                    min(
                        optim_config["freq_reg_max"],
                        max(
                            optim_config["freq_reg_min"],
                            p.freq + current_config["freq_{}".format(i)],
                        ),
                    ),
                    # p.srate,
                    p.srate,
                    # p.Q,
                    min(
                        optim_config["MAX_Q"],
                        max(
                            optim_config["MIN_Q"],
                            p.Q + current_config["Q_{}".format(i)],
                        ),
                    ),
                    # p.dbGain,
                    min(
                        optim_config["MAX_DBGAIN"],
                        max(
                            optim_config["MIN_DBGAIN"],
                            p.dbGain + current_config["dbGain_{}".format(i)],
                        ),
                    ),
                ),
            )
            for i, (c, p) in enumerate(greedy_peq)
        ]

    def evaluate_config(current_config, checkpoint_dir=None):
        eval_peq = init_delta(current_config)
        # score = flat_pir(freq, df_speaker, eval_peq)
        score = score_loss(df_speaker, eval_peq)
        tune.report(score=score)  # , h_score=h_score)

    time_budget_s = 300
    num_samples = 10000

    class CustomStopper(tune.Stopper):
        def __init__(self):
            self.should_stop = False

        def __call__(self, trial_id, result):
            max_iter = 5
            return self.should_stop or result["training_iteration"] >= max_iter

        def stop_all(self):
            return self.should_stop

    stopper = CustomStopper()

    # possible schedulers
    pbt = PopulationBasedTraining(
        time_attr="training_iteration",
        perturbation_interval=2,
    )

    asha = ASHAScheduler(
        time_attr="training_iteration",
        max_t=100,
        grace_period=10,
        reduction_factor=3,
        brackets=1,
    )

    # possible search algos
    algo_cfo = CFO(low_cost_partial_config=low_cost_partial_config)
    algo_blendsearch = BlendSearch(low_cost_partial_config=low_cost_partial_config)
    algo_bos = BayesOptSearch(utility_kwargs={"kind": "ucb", "kappa": 2.5, "xi": 0.0})
    algo = ConcurrencyLimiter(algo_blendsearch, max_concurrent=128)

    analysis = tune.run(
        evaluate_config,
        config=config,
        metric="score",
        mode="min",
        num_samples=num_samples,
        time_budget_s=time_budget_s,
        local_dir="logs/",
        # search_alg=algo, # bos working well
        # scheduler=asha,
        # stop=stopper,
        fail_fast=True,
        scheduler=pbt,
        verbose=1,
    )

    print(analysis.best_trial.last_result)
    print(analysis.best_config)

    final_loss = -analysis.best_trial.last_result["score"]
    print(final_loss, init_loss)
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

    if not use_score or not optim_config["second_optimiser"]:
        return greedy_results, greedy_peq

    return optim_refine(
        speaker_name,
        df_speaker,
        freq,
        auto_target,
        auto_target_interp,
        optim_config,
        greedy_results,
        greedy_peq,
    )
