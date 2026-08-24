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
from spinorama.measurements import Measurements
from spinorama.misc import graph_melt, graph_unmelt
from spinorama.compute.scores import speaker_pref_rating, nbd
from spinorama.compute.cea2034 import compute_cea2034, estimated_inroom_hv, listening_window
from spinorama.filters.peq import Peq, peq_apply_measurements


def scores_apply_filter(
    m: Measurements, peq: Peq
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, dict[str, float] | None]:
    """Apply a PEQ to the H/V sweeps (when available) and return the resulting
    CEA2034 spin, PIR, and preference score. Falls back to per-curve EQ on the
    pre-computed CEA2034 when H/V sweeps are not present.
    """
    spin_filtered: pd.DataFrame | None = pd.DataFrame()
    pir_filtered: pd.DataFrame | None = pd.DataFrame()
    if m.h_spl is not None and m.v_spl is not None:
        spl_h_filtered = peq_apply_measurements(m.h_spl, peq)
        spl_v_filtered = peq_apply_measurements(m.v_spl, peq)
        spin_filtered = graph_melt(compute_cea2034(spl_h_filtered, spl_v_filtered))
        pir_filtered = graph_melt(estimated_inroom_hv(spl_h_filtered, spl_v_filtered))
    else:
        spin_filtered, pir_filtered, _ = noscore_apply_filter(m, peq, False)

    score_filtered = speaker_pref_rating(cea2034=spin_filtered, pir=pir_filtered, rounded=False)
    if score_filtered is None:
        logger.info("computing pref score for eq failed")

    return spin_filtered, pir_filtered, score_filtered


def noscore_apply_filter(
    m: Measurements, peq: Peq, is_normalized: bool
) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    """Apply a PEQ to the pre-computed CEA2034 / EIR / On Axis curves and
    return the three filtered melted frames (any may be ``None``).
    """
    spin_filtered = None
    pir_filtered = None
    on_filtered = None

    spin = m.cea2034_normalized if is_normalized else m.cea2034
    if spin is not None:
        try:
            spin_filtered = peq_apply_measurements(spin, peq)
        except ValueError:
            logger.error("Peq apply measurement failed %s", ",".join(list(spin.keys())))
            return None, None, None

    pir = m.eir_normalized if is_normalized else m.eir
    if pir is not None:
        pir_filtered = peq_apply_measurements(pir, peq)

    if m.on_axis is not None:
        on = m.on_axis
        if is_normalized:
            # The normalised on-axis curve is identically zero; copy so we
            # don't mutate the caller's frame.
            on = on.copy()
            on["On Axis"] = 0.0
        on_filtered = peq_apply_measurements(on, peq)

    spin_melted = graph_melt(spin_filtered) if spin_filtered is not None else None
    pir_melted = graph_melt(pir_filtered) if pir_filtered is not None else None
    on_melted = graph_melt(on_filtered) if on_filtered is not None else None

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


def scores_loss(m: Measurements, peq: Peq) -> float:
    """Negated preference score, suitable as a scipy minimisation objective."""
    _, _, score_filtered = scores_apply_filter(m, peq)
    return -score_filtered["pref_score"]


def lw_loss(m: Measurements, peq: Peq) -> float:
    """Listening-window NBD after applying ``peq`` to the H/V sweeps."""
    if m.h_spl is None or m.v_spl is None:
        raise ValueError("lw_loss requires H and V SPL sweeps")
    spl_h_filtered = peq_apply_measurements(m.h_spl, peq)
    spl_v_filtered = peq_apply_measurements(m.v_spl, peq)
    lw_filtered = listening_window(spl_h_filtered, spl_v_filtered)
    return nbd(dfu=lw_filtered, min_freq=100)
