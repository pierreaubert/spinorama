#                                                  -*- coding: utf-8 -*-
import logging

from .ltype import DataSpeaker, Peq
from .load import graph_melt
from .compute_scores import speaker_pref_rating, nbd
from .compute_cea2034 import compute_cea2034, estimated_inroom_HV, listening_window
from .filter_peq import peq_apply_measurements
from .graph import graph_spinorama


logger = logging.getLogger("spinorama")


def scores_apply_filter(df_speaker: DataSpeaker, peq: Peq):
    # get SPL H & V
    splH = df_speaker["SPL Horizontal_unmelted"]
    splV = df_speaker["SPL Vertical_unmelted"]
    # apply EQ to all horizontal and vertical measurements
    splH_filtered = peq_apply_measurements(splH, peq)
    splV_filtered = peq_apply_measurements(splV, peq)
    # compute filtered score
    spin_filtered = graph_melt(compute_cea2034(splH_filtered, splV_filtered))
    pir_filtered = graph_melt(estimated_inroom_HV(splH_filtered, splV_filtered))
    score_filtered = speaker_pref_rating(spin_filtered, pir_filtered, rounded=False)
    if score_filtered is None:
        logger.info("computing pref score for eq failed")
        # max score is around 10
        return None, None, {"pref_score": -10.0}
    return spin_filtered, pir_filtered, score_filtered


def noscore_apply_filter(df_speaker: DataSpeaker, peq: Peq):
    spin_filtered = None
    pir_filtered = None
    if "CEA2034" in df_speaker.keys():
        spin = df_speaker["CEA2034"]
        try:
            pivoted_spin = spin.pivot_table(
                index="Freq", columns="Measurements", values="dB", aggfunc=max
            ).reset_index()
            # modify all curve but should not touch DI
            spin_filtered = peq_apply_measurements(pivoted_spin, peq)
            # not modified by eq
            for curve in ("Early Reflections DI", "Sound Power DI", "DI offset"):
                if curve in pivoted_spin.keys():
                    spin_filtered[curve] = pivoted_spin[curve]
        except ValueError:
            print("debug: {}".format(spin.keys()))
            return None, None

    if "Estimated In-Room Response" in df_speaker.keys():
        pir = df_speaker["Estimated In-Room Response"]
        pivoted_pir = pir.pivot(*pir).rename_axis(columns=None).reset_index()
        pir_filtered = peq_apply_measurements(pivoted_pir, peq)

    if spin_filtered is not None and pir_filtered is not None:
        return graph_melt(spin_filtered), graph_melt(pir_filtered)
    return None, None


def scores_graph(spin: DataSpeaker, spin_filtered: DataSpeaker, params: dict):
    return graph_spinorama(spin, params) | graph_spinorama(spin_filtered, params)


def scores_print(score: dict, score_filtered: dict):
    print("         SPK auEQ")
    print("-----------------")
    print(
        "NBD  ON {0:0.2f} {1:0.2f}".format(
            score["nbd_on_axis"], score_filtered["nbd_on_axis"]
        )
    )
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
    print(
        "LFX       {0:0.0f}   {1:0.0f}".format(
            score["lfx_hz"], score_filtered["lfx_hz"]
        )
    )
    print("LFQ     {0:0.2f} {1:0.2f}".format(score["lfq"], score_filtered["lfq"]))
    print("-----------------")
    print(
        "Score    {0:0.1f}  {1:0.1f}".format(
            score["pref_score"], score_filtered["pref_score"]
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
        "LFQ     {0:0.2f} {1:0.2f} {2:0.2f}".format(
            score["lfq"], score1["lfq"], score2["lfq"]
        )
    )
    res.append("----------------------")
    res.append(
        "Score    {0:0.1f}  {1:0.1f}  {2:0.1f}".format(
            score["pref_score"], score1["pref_score"], score2["pref_score"]
        )
    )
    res.append("----------------------")
    return "\n".join(res)


def scores_loss(df_speaker: dict, peq) -> float:
    # optimise for score directly
    _, _, score_filtered = scores_apply_filter(df_speaker, peq)
    # optimize max score is the same as optimize min -score
    return -score_filtered["pref_score"]


def lw_loss(df_speaker: dict, peq) -> float:
    # optimise LW
    # get SPL H & V
    splH = df_speaker["SPL Horizontal_unmelted"]
    splV = df_speaker["SPL Vertical_unmelted"]
    # apply EQ to all horizontal and vertical measurements
    splH_filtered = peq_apply_measurements(splH, peq)
    splV_filtered = peq_apply_measurements(splV, peq)
    # compute LW
    lw_filtered = listening_window(splH_filtered, splV_filtered)
    # optimize nbd
    score = nbd(lw_filtered)
    # print("LW score: {}".format(score))
    return score
