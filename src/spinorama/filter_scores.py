# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

import pandas as pd

from spinorama import logger
from spinorama.ltype import DataSpeaker
from spinorama.misc import graph_melt, graph_unmelt
from spinorama.compute_scores import speaker_pref_rating, nbd
from spinorama.compute_cea2034 import compute_cea2034, estimated_inroom_hv, listening_window
from spinorama.filter_peq import Peq, peq_apply_measurements


def scores_apply_filter(
    df_speaker: DataSpeaker, peq: Peq
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    spin_filtered = pd.DataFrame()
    pir_filtered = pd.DataFrame()
    if "SPL Horizontal_unmelted" in df_speaker and "SPL Vertical_unmelted" in df_speaker:
        # get SPL H & V
        spl_h = df_speaker["SPL Horizontal_unmelted"]
        spl_v = df_speaker["SPL Vertical_unmelted"]
        # apply EQ to all horizontal and vertical measurements
        spl_h_filtered = peq_apply_measurements(spl_h, peq)
        spl_v_filtered = peq_apply_measurements(spl_v, peq)
        spin_filtered = graph_melt(compute_cea2034(spl_h_filtered, spl_v_filtered))
        pir_filtered = graph_melt(estimated_inroom_hv(spl_h_filtered, spl_v_filtered))
    else:
        logger.error("error bad call to apply filter: %s", ",".join(list(df_speaker.keys())))
        return None, None, None

    score_filtered = speaker_pref_rating(cea2034=spin_filtered, pir=pir_filtered, rounded=False)
    if score_filtered is None:
        logger.info("computing pref score for eq failed")

    return spin_filtered, pir_filtered, score_filtered


def noscore_apply_filter(
    df_speaker: DataSpeaker, peq: Peq, is_normalized: bool
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    spin_filtered = None
    pir_filtered = None
    on_filtered = None

    key_cea2034 = "CEA203 Normalized_unmelted" if is_normalized else "CEA2034_unmelted"
    if key_cea2034 in df_speaker:
        spin = df_speaker[key_cea2034]
        try:
            print("DEBUG SPIN {} {}".format(is_normalized, spin.keys()))
            spin_filtered = peq_apply_measurements(spin, peq)
        except ValueError:
            logger.debug("%s", ",".join(list(spin.keys())))
            return None, None, None

    key_pir = (
        "Estimated In-Room Response Normalized_unmelted"
        if is_normalized
        else "Estimated In-Room Response_unmelted"
    )
    if key_pir in df_speaker:
        pir = df_speaker[key_pir]
        pir_filtered = peq_apply_measurements(pir, peq)

    if "On Axis_unmelted" in df_speaker:
        on = df_speaker["On Axis_unmelted"]
        if is_normalized:
            on["On Axis"] = 0.0
        print("DEBUG ON {} {}".format(is_normalized, on.keys()))
        on_filtered = peq_apply_measurements(on, peq)

    spin_melted = None
    if spin_filtered is not None:
        spin_melted = graph_melt(spin_filtered)

    pir_melted = None
    if pir_filtered is not None:
        pir_melted = graph_melt(pir_filtered)

    on_melted = None
    if on_filtered is not None:
        on_melted = graph_melt(on_filtered)

    return spin_melted, pir_melted, on_melted


def scores_print(score: dict, score_filtered: dict):
    print("         SPK auEQ")
    print("-----------------")
    print("NBD  ON {0:0.2f} {1:0.2f}".format(score["nbd_on_axis"], score_filtered["nbd_on_axis"]))
    print(
        "NBD  LW {0:0.2f} {1:0.2f}".format(
            score["nbd_listening_window"], score_filtered["nbd_listening_window"]
        )
    )
    print(
        "NBD PIR {0:0.2f} {1:0.2f}".format(
            score["nbd_pred_in_room"], score_filtered["nbd_pred_in_room"]
        )
    )
    print(
        "SM  PIR {0:0.2f} {1:0.2f}".format(
            score["sm_pred_in_room"], score_filtered["sm_pred_in_room"]
        )
    )
    print(
        "SM   SP {0:0.2f} {1:0.2f}".format(
            score["sm_sound_power"], score_filtered["sm_sound_power"]
        )
    )
    print("LFX       {0:0.0f}   {1:0.0f}".format(score["lfx_hz"], score_filtered["lfx_hz"]))
    print("LFQ     {0:0.2f} {1:0.2f}".format(score["lfq"], score_filtered["lfq"]))
    print("-----------------")
    print("Score    {0:0.1f}  {1:0.1f}".format(score["pref_score"], score_filtered["pref_score"]))
    print(
        "w/sub    {0:0.1f}  {1:0.1f}".format(
            score.get("pref_score_wsub", 0.0),
            score_filtered.get("pref_score_wsub", 0.0),
        )
    )
    print("-----------------")


def scores_print2(score: dict, score1: dict, score2: dict):
    res = []
    res.append("         SPK   S1   S2")
    res.append("----------------------")
    res.append(
        "NBD  ON {0:0.2f} {1:0.2f} {2:0.2f}".format(
            score["nbd_on_axis"], score1["nbd_on_axis"], score2["nbd_on_axis"]
        )
    )
    res.append(
        "NBD  LW {0:0.2f} {1:0.2f} {2:0.2f}".format(
            score["nbd_listening_window"],
            score1["nbd_listening_window"],
            score2["nbd_listening_window"],
        )
    )
    res.append(
        "NBD PIR {0:0.2f} {1:0.2f} {2:0.2f}".format(
            score["nbd_pred_in_room"],
            score1["nbd_pred_in_room"],
            score2["nbd_pred_in_room"],
        )
    )
    res.append(
        "SM  PIR {0:0.2f} {1:0.2f} {2:0.2f}".format(
            score["sm_pred_in_room"],
            score1["sm_pred_in_room"],
            score2["sm_pred_in_room"],
        )
    )
    res.append(
        "SM   SP {0:0.2f} {1:0.2f} {2:0.2f}".format(
            score["sm_sound_power"], score1["sm_sound_power"], score2["sm_sound_power"]
        )
    )
    res.append(
        "LFX       {0:0.0f}   {1:0.0f}   {2:0.0f}".format(
            score["lfx_hz"], score1["lfx_hz"], score2["lfx_hz"]
        )
    )
    res.append(
        "LFQ     {0:0.2f} {1:0.2f} {2:0.2f}".format(score["lfq"], score1["lfq"], score2["lfq"])
    )
    res.append("----------------------")
    res.append(
        "Score    {0:0.1f}  {1:0.1f}  {2:0.1f}".format(
            score["pref_score"], score1["pref_score"], score2["pref_score"]
        )
    )
    res.append("----------------------")
    return "\n".join(res)


def scores_loss(df_speaker: dict, peq: Peq) -> float:
    # optimise for score directly
    _, _, score_filtered = scores_apply_filter(df_speaker, peq)
    # optimize max score is the same as optimize min -score
    return -score_filtered["pref_score"]


def lw_loss(df_speaker: dict, peq: Peq) -> float:
    # optimise LW
    # get SPL H & V
    spl_h = df_speaker["SPL Horizontal_unmelted"]
    spl_v = df_speaker["SPL Vertical_unmelted"]
    # apply EQ to all horizontal and vertical measurements
    spl_h_filtered = peq_apply_measurements(spl_h, peq)
    spl_v_filtered = peq_apply_measurements(spl_v, peq)
    # compute LW
    lw_filtered = listening_window(spl_h_filtered, spl_v_filtered)
    # optimize nbd
    score = nbd(dfu=lw_filtered, min_freq=100)
    # print("LW score: {}".format(score))
    return score
