# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import math

import numpy as np
import pandas as pd
from scipy.stats import linregress

from spinorama import logger
from spinorama.ltype import Vector, Peq, DataSpeaker
from spinorama.compute_cea2034 import sp_weigths, estimated_inroom_hv
from spinorama.compute_scores import octave
from spinorama.filter_peq import peq_build
from spinorama.filter_scores import scores_apply_filter
from spinorama.filter_peq import peq_apply_measurements
from spinorama.load_misc import graph_melt
from spinorama.auto_misc import have_full_measurements

# cython import
from spinorama.c_compute_scores import c_cea2034, c_score_peq_approx

# ------------------------------------------------------------------------------
# lots of variables for the fast computations on scores in python
# ------------------------------------------------------------------------------


def intervals_nbd(freq: Vector) -> list[tuple[float, float]]:
    return [
        (np.searchsorted(freq, omin, side="right"), np.searchsorted(freq, omax, side="left"))
        for omin, ocenter, omax in octave(2)
        if 100 <= ocenter <= 12000
    ]


def build_index(spl_key: list[str], h_key: list[str], v_key: list[str]) -> list[int]:
    return [spl_key.index(f"H{k}") for k in h_key] + [spl_key.index(f"V{k}") for k in v_key]


def build_index_cea2034(spl_keys):
    idx_lw = build_index(
        spl_keys, ["10°", "20°", "30°", "-10°", "-20°", "-30°"], ["On Axis", "10°", "-10°"]
    )
    idx_er = build_index(
        spl_keys,
        [
            "On Axis",
            "10°",
            "20°",
            "30°",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-10°",
            "-20°",
            "-30°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "-90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "180°",
        ],
        ["On Axis", "-20°", "-30°", "-40°", "40°", "50°", "60°"],
    )
    idx_floor_bounce = build_index(spl_keys, [], ["-20°", "-30°", "-40°"])
    idx_ceiling_bounce = build_index(spl_keys, [], ["40°", "50°", "60°"])
    idx_front_wall_bounce = build_index(
        spl_keys, ["On Axis", "-10°", "-20°", "-30°", "10°", "20°", "30°"], []
    )
    idx_side_wall_bounce = build_index(
        spl_keys, ["-40°", "-50°", "-60°", "-70°", "-80°", "40°", "50°", "60°", "70°", "80°"], []
    )
    idx_rear_wall_bounce = build_index(
        spl_keys,
        [
            "-170°",
            "-160°",
            "-150°",
            "-140°",
            "-130°",
            "-120°",
            "-110°",
            "-100°",
            "-90°",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "180°",
        ],
        [],
    )
    idx_tvr = build_index(spl_keys, [], ["On Axis", "-20°", "-30°", "-40°", "40°", "50°", "60°"])
    idx_fr = build_index(spl_keys, [], ["On Axis", "-20°", "-30°", "-40°"])
    idx_cr = build_index(spl_keys, [], ["On Axis", "40°", "50°", "60°"])
    idx_front = build_index(spl_keys, ["On Axis", "10°", "20°", "30°", "-10°", "-20°", "-30°"], [])
    idx_side = build_index(
        spl_keys, ["40°", "50°", "60°", "70°", "80°", "-40°", "-50°", "-60°", "-70°", "-80°"], []
    )
    idx_rear = build_index(
        spl_keys,
        [
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-90°",
            "-100°",
            "-110°",
            "-120°",
            "-130°",
            "-140°",
            "-150°",
            "-160°",
            "-170°",
            "180°",
        ],
        [],
    )
    idx_thr = build_index(
        spl_keys,
        [
            "On Axis",
            "10°",
            "20°",
            "30°",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-10°",
            "-20°",
            "-30°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "-90°",
            "-100°",
            "-110°",
            "-120°",
            "-130°",
            "-140°",
            "-150°",
            "-160°",
            "-170°",
            "180°",
        ],
        [],
    )
    idx_sp = build_index(
        spl_keys,
        [
            "On Axis",
            "10°",
            "20°",
            "30°",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-10°",
            "-20°",
            "-30°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "-90°",
            "-100°",
            "-110°",
            "-120°",
            "-130°",
            "-140°",
            "-150°",
            "-160°",
            "-170°",
            "180°",
        ],
        [
            "10°",
            "20°",
            "30°",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-10°",
            "-20°",
            "-30°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "-90°",
            "-100°",
            "-110°",
            "-120°",
            "-130°",
            "-140°",
            "-150°",
            "-160°",
            "-170°",
        ],
    )
    # all the curves from CEA2034
    idx_cea2034 = [
        idx_lw,  # 0
        idx_er,  # 1
        idx_floor_bounce,  # 2
        idx_ceiling_bounce,  # 3
        idx_front_wall_bounce,  # 4
        idx_side_wall_bounce,  # 5
        idx_rear_wall_bounce,  # 6
        idx_tvr,  # 7
        idx_fr,  # 8
        idx_cr,  # 9
        idx_front,  # 10
        idx_side,  # 11
        idx_rear,  # 12
        idx_thr,  # 13
        idx_sp,  # 14
    ]
    # only the one you need to compute the score
    idx_cea2034_required = [
        idx_lw,  # 0
        idx_er,  # 1
        idx_sp,  # 2
    ]
    return idx_cea2034, idx_cea2034_required


def compute_scores_prep(
    spl_h: pd.DataFrame, spl_v: pd.DataFrame
) -> dict[str, Vector | list[list] | list[tuple[int, int]] | pd.DataFrame]:
    freq = spl_h["Freq"].to_numpy()
    spl_h = spl_h.drop("Freq", axis=1)
    spl_v = spl_v.drop("Freq", axis=1)
    spl_keys = [f"H{k}" for k in spl_h] + [f"V{k}" for k in spl_v]
    weigths = np.asarray([sp_weigths[k] for k in spl_h] + [sp_weigths[k] for k in spl_v])
    intervals = intervals_nbd(freq)
    idx, _ = build_index_cea2034(spl_keys)
    spl = np.concatenate((spl_h.T.to_numpy(), spl_v.T.to_numpy()), axis=0)
    spin = c_cea2034(spl, idx, weigths)
    return {
        "freq": freq,
        "intervals": intervals,
        "weigths": weigths,
        "idx": idx,
        "on": spl_h["On Axis"].to_numpy(),
        "spin": spin,
    }


# ------------------------------------------------------------------------------
# various loss function
# ------------------------------------------------------------------------------


def l2_loss(freq: Vector, local_target: list[Vector], peq: Peq) -> float:
    # L2 norm
    return np.linalg.norm(local_target + peq_build(freq, peq), 2)


def leastsquare_loss(freq: Vector, local_target: list[Vector], peq: Peq, iterations: int) -> float:
    # sum of L2 norms if we have multiple targets
    return math.sqrt(np.square([l2_loss(freq, lt, peq) for lt in local_target]).sum())


def flat_loss(
    freq: Vector, local_target: list[Vector], peq: Peq, iterations: int, weigths: Vector
) -> float:
    # make LW as close as target as possible and SP flat
    lw = np.sum([l2_loss(freq, [local_target[i]], peq) for i in range(0, len(local_target) - 1)])
    # want sound power to be flat but not necessary aligned
    # with a target
    sp = 1.0
    if len(local_target) > 1:
        _, _, r_value, _, _ = linregress(np.log10(freq), local_target[-1])
        sp = 1 - r_value**2
    # * or +
    # return weigths[0]*lw+weigths[1]*sp
    return lw * sp


def flat_loss_exp(
    freq: Vector, local_target: list[Vector], peq: Peq, iterations: int, weigths: Vector
) -> float:
    _, _, r_value, _, _ = linregress(np.log10(freq), local_target[0])
    sp = 1 - r_value**2
    return sp


def swap_loss(freq: Vector, local_target: list[Vector], peq: Peq, iteration: int) -> float:
    # try to alternate, optimise for 1 objective then the second one
    if len(local_target) == 0 or iteration < 10:
        return l2_loss(freq, [local_target[0]], peq)
    return l2_loss(freq, [local_target[1]], peq)


def alternate_loss(freq: Vector, local_target: list[Vector], peq: Peq, iteration: int) -> float:
    # optimise for 2 objectives 1 each time
    if 0 in (len(local_target), iteration % 2):
        return l2_loss(freq, [local_target[0]], peq)
    return l2_loss(freq, [local_target[1]], peq)


def flat_pir(freq: Vector, df_spin: DataSpeaker, peq: Peq) -> float:
    """Flatten the PIR"""
    pir_filtered = df_spin.get("Estimated In-Room Response_unmelted", None)
    if pir_filtered is None:
        spl_h = df_spin["SPL Horizontal_unmelted"]
        spl_v = df_spin["SPL Vertical_unmelted"]
        # apply EQ to all horizontal and vertical measurements
        spl_h_filtered = peq_apply_measurements(spl_h, peq)
        spl_v_filtered = peq_apply_measurements(spl_v, peq)
        # compute pir
        pir_filtered = graph_melt(estimated_inroom_hv(spl_h_filtered, spl_v_filtered))
    else:
        if len(peq) > 0:
            pir_filtered["Estimated In-Room Response"].add(peq_build(pir_filtered.Freq.values, peq))
        pir_filtered = graph_melt(pir_filtered)

    data = pir_filtered.loc[(pir_filtered.Freq >= 100) & (pir_filtered.Freq <= 16000)]
    _, _, r_value, _, _ = linregress(np.log10(data.Freq), data.dB)
    return r_value**2


def score_loss_slow(df_spin: DataSpeaker, peq: Peq) -> float:
    """Compute the preference score for speaker
    local_target: unsued
    peq: evaluated peq
    return minus score (we want to maximise the score)
    """
    _, _, score = scores_apply_filter(df_spin, peq)
    if len(peq) > 0:
        logger.debug("score %.2f peq %s", score.get("pref_score", -1000), peq[0][1])
    return -score["pref_score"]


def score_loss(df_spin: DataSpeaker, peq: Peq) -> float:
    """Compute the preference score for speaker
    local_target: unsued
    peq: evaluated peq
    return minus score (we want to maximise the score)
    """
    if not have_full_measurements(df_spin):
        return score_loss_slow(df_spin, peq)

    pre_computed = df_spin.get("pre_computed", None)
    if pre_computed is None:
        spl_h = df_spin["SPL Horizontal_unmelted"]
        spl_v = df_spin["SPL Vertical_unmelted"]
        pre_computed = compute_scores_prep(spl_h, spl_v)
        df_spin["pre_computed"] = pre_computed

    peq_spl = np.asarray(peq_build(pre_computed["freq"], peq))

    # print('debug: freq {}'.format(pre_computed["freq"].shape()))
    # print('debug: spin {}'.format(pre_computed["spin"].shape()))
    # print('debug:   on {}'.format(pre_computed["on"].shape()))
    # print('debug:  peq {}'.format(peq_spl.shape()))

    score = c_score_peq_approx(
        np.asarray(pre_computed["freq"]),
        pre_computed["idx"],
        pre_computed["intervals"],
        pre_computed["spin"],
        np.asarray(pre_computed["on"]),
        np.asarray(peq_spl),
    )
    if len(peq) > 0:
        logger.debug("score %.2f peq %s", score.get("pref_score", -1000), peq[0][1])
    return -score["pref_score"]


def loss(
    df_speaker: DataSpeaker,
    freq: Vector,
    local_target: list[Vector],
    peq: Peq,
    iterations: int,
    optim_config: dict,
) -> float:
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
        score = score_loss(df_speaker, peq)
        flatness = leastsquare_loss(freq, local_target, peq, iterations)
        # flatness = l2_loss(freq, local_target[1], peq)
        # add flatness as a penalty or score optim goes crazy (pir parameter)
        # print("debug: score {} flatness {}".format(score, flatness))
        return score + flatness / 20
    if which_loss == "combine_loss":
        weigths = optim_config["loss_weigths"]
        return (
            score_loss(df_speaker, peq)
            + flat_loss(freq, local_target, peq, iterations, weigths) / 20
        )
    logger.error("loss function is unknown %s", which_loss)
    return -1
