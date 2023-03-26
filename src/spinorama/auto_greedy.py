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

import numpy as np
import pandas as pd

from spinorama import logger
from spinorama.ltype import Peq, Vector
from spinorama.filter_iir import Biquad
from spinorama.auto_loss import loss, score_loss
from spinorama.auto_range import (
    propose_range_freq,
    propose_range_q,
    propose_range_db_gain,
    propose_range_biquad,
)
from spinorama.auto_biquad import find_best_biquad, find_best_peak
from spinorama.auto_target import optim_compute_auto_target
from spinorama.auto_preflight import optim_preflight


def optim_greedy(
    speaker_name: str,
    df_speaker: dict[str, pd.DataFrame],
    freq: Vector,
    auto_target: list[Vector],
    auto_target_interp: list[Vector],
    optim_config: dict,
    use_score: bool,
) -> tuple[bool, tuple[tuple[int, float, float], Peq]]:
    """Main optimiser: follow a greedy strategy"""

    if not optim_preflight(freq, auto_target, auto_target_interp, df_speaker):
        logger.error("Preflight check failed!")
        return False, ((0, 0, 0), [])

    auto_peq = []
    current_auto_target = optim_compute_auto_target(
        freq, auto_target, auto_target_interp, auto_peq, optim_config
    )

    best_loss = loss(df_speaker, freq, auto_target, auto_peq, 0, optim_config)
    pref_score = 1000.0
    if use_score:
        pref_score = score_loss(df_speaker, auto_peq)

    results = [(0, best_loss, -pref_score)]
    logger.info(
        "OPTIM %s START %s #PEQ %d Freq #%d Gain #%d +/-[%s, %s] Q #%s [%s, %s] Loss %2.2f Score %2.2f",
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

    nb_iter = optim_config["MAX_NUMBER_PEQ"]
    (
        state,
        current_type,
        current_freq,
        current_q,
        current_db_gain,
        current_loss,
        current_nit,
    ) = (False, -1, -1, -1, -1, -1, -1)

    for optim_iter in range(0, nb_iter):
        # we are optimizing above target_min_hz on anechoic data
        current_auto_target = optim_compute_auto_target(
            freq, auto_target, auto_target_interp, auto_peq, optim_config
        )

        sign = None
        init_freq = None
        init_freq_range = None
        init_db_gain_range = None
        biquad_range = None
        if optim_iter == 0:
            if optim_config["full_biquad_optim"] is True:
                # see if a LP can help get some flatness of bass
                init_freq_range = [
                    optim_config["target_min_freq"] / 2,
                    16000,
                ]  # optim_config["target_min_freq"] * 2]
                init_db_gain_range = [-3, -2, -1, 0, 1, 2, 3]
                init_q_range = [0.5, 1, 2, 3]
                biquad_range = [0, 1, 3, 5, 6]  # LP, HP, LS, HS
            else:
                # greedy strategy: look for lowest & highest peak
                init_freq_range = [
                    optim_config["target_min_freq"] / 2,
                    optim_config["target_min_freq"] * 2,
                ]
                init_db_gain_range = [-3, -2, -1, 0, 1, 2, 3]
                init_q_range = [0.5, 1, 2, 3]
                biquad_range = [3]  # PK
        else:
            # min_freq = optim_config["target_min_freq"]
            sign, init_freq, init_freq_range = propose_range_freq(
                freq, current_auto_target[0], optim_config, auto_peq
            )
            # don't use the pre computed range
            # init_freq_range = [optim_config["target_min_freq"], optim_config["target_max_freq"]]
            init_db_gain_range = propose_range_db_gain(
                freq, current_auto_target[0], sign, init_freq, optim_config
            )
            init_q_range = propose_range_q(optim_config)
            biquad_range = propose_range_biquad(optim_config)
            biquad_range = [3]

        logger.debug(
            "sign %.0f init_freq %.0fHz init_freq_range %s init_q_range %s biquad_range %s",
            sign if sign is not None else 0.0,
            init_freq if init_freq is not None else 0.0,
            init_freq_range,
            init_q_range,
            biquad_range,
        )

        if optim_config["full_biquad_optim"] is True:
            (
                state,
                current_type,
                current_freq,
                current_q,
                current_db_gain,
                current_loss,
                current_nit,
            ) = find_best_biquad(
                df_speaker,
                freq,
                current_auto_target,
                init_freq_range,
                init_q_range,
                init_db_gain_range,
                biquad_range,
                optim_iter,
                optim_config,
                current_loss,
            )
        else:
            (
                state,
                current_type,
                current_freq,
                current_q,
                current_db_gain,
                current_loss,
                current_nit,
            ) = find_best_peak(
                df_speaker,
                freq,
                current_auto_target,
                init_freq_range,
                init_q_range,
                init_db_gain_range,
                biquad_range,
                optim_iter,
                optim_config,
                current_loss,
            )

        if state:
            biquad = (
                1.0,
                Biquad(current_type, current_freq, 48000, current_q, current_db_gain),
            )
            auto_peq.append(biquad)
            best_loss: float = current_loss
            if use_score:
                pref_score = score_loss(df_speaker, auto_peq)
                results.append((optim_iter + 1, best_loss, -pref_score))
            logger.info(
                "Speaker %s Iter %2d Optim converged loss %2.2f pref score %2.2f biquad %2s F:%5.0fHz Q:%2.2f G:%+2.2fdB in %d iterations",
                speaker_name,
                optim_iter,
                best_loss,
                -pref_score,
                biquad[1].type2str(),
                current_freq,
                current_q,
                current_db_gain,
                current_nit,
            )
        else:
            logger.error(
                "Speaker %s Skip failed optim for best %2.2f current %2.2f",
                speaker_name,
                best_loss,
                current_loss,
            )
            break

    if len(results) == 0:
        logger.info("OPTIM END %s: 0 PEQ", speaker_name)
        return False, ((-1, -1000, -1000), [])

    # recompute auto_target with the full auto_peq
    current_auto_target = optim_compute_auto_target(
        freq, auto_target, auto_target_interp, auto_peq, optim_config
    )
    if results[-1][1] < best_loss:
        if use_score:
            pref_score = score_loss(df_speaker, auto_peq)
        results.append((nb_iter + 1, best_loss, -pref_score))

    # best score is not necessary the last one
    best_results = None
    if use_score:
        idx_max = np.argmax((np.array(results).T)[-1])
        best_results = results[idx_max]
        auto_peq = auto_peq[:idx_max]
    else:
        best_results = results[-1]

    logger.info(
        "OPTIM END %s: best loss %2.2f final score %2.2f with %2d PEQs",
        speaker_name,
        best_results[1],
        best_results[2],
        len(auto_peq),
    )
    return True, (best_results, auto_peq)
