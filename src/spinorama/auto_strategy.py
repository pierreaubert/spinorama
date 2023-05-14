# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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

from copy import deepcopy

import numpy as np

from spinorama import logger
from spinorama.constant_paths import MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ
from spinorama.ltype import DataSpeaker, OptimResult
from spinorama.filter_peq import Peq
from spinorama.compute_misc import compute_statistics
from spinorama.filter_peq import peq_print
from spinorama.filter_scores import scores_apply_filter
from spinorama.auto_misc import get3db, have_full_measurements
from spinorama.auto_target import get_freq, get_target
from spinorama.auto_msteps import optim_multi_steps


TRACE = False


def optim_eval_strategy(
    current_speaker_name: str,
    df_speaker: DataSpeaker,
    optim_config: dict,
    use_score: bool,  # noqa: FBT001
) -> tuple[bool, tuple[dict, OptimResult, Peq, float]]:
    """Find the best EQ for this speaker"""
    # shortcut
    curves = optim_config["curve_names"]

    # get freq and targets
    data_frame, freq, auto_target = get_freq(df_speaker, optim_config)
    if data_frame is None or freq is None or auto_target is None:
        logger.error("Cannot compute freq for %s", current_speaker_name)
        return False, ({}, (0, 0, 0), [], 0.0)

    auto_target_interp = []
    for curve in curves:
        target = get_target(data_frame, freq, curve, optim_config)
        auto_target_interp.append(target)

    auto_status, (auto_results, auto_peq) = optim_multi_steps(
        current_speaker_name,
        df_speaker,
        freq,
        auto_target,
        auto_target_interp,
        optim_config,
        use_score,
    )

    auto_score = {}
    auto_slope_lw = 0.0
    if use_score and auto_status:
        auto_spin, _, auto_score = scores_apply_filter(df_speaker, auto_peq)
        if auto_spin is not None:
            unmelted_auto_spin = auto_spin.pivot_table(
                index="Freq", columns="Measurements", values="dB", aggfunc=max
            ).reset_index()
            try:
                auto_slope_lw, _, _ = compute_statistics(
                    unmelted_auto_spin,
                    "Listening Window",
                    optim_config["target_min_freq"],
                    optim_config["target_max_freq"],
                    MIDRANGE_MIN_FREQ,
                    MIDRANGE_MAX_FREQ,
                )
            except ValueError:
                logger.exception("error: %s", current_speaker_name)

    if TRACE:
        print("debug trace eval strategy")
        print("  auto score {}".format(auto_score))
        print("  auto results {}".format(auto_results))
        print("  auto peq")
        print(peq_print(auto_peq))
        print("  auto slope lw {}".format(auto_slope_lw))
        print("end trace debug eval strategy")
    return True, (auto_score, auto_results, auto_peq, auto_slope_lw)


def optim_strategy(
    current_speaker_name: str,
    df_speaker: DataSpeaker,
    optim_config: dict,
    use_score: bool,  # noqa: FBT001
) -> tuple[bool, tuple[dict, OptimResult, Peq, dict]]:
    # do we use -3dB point for target?
    if optim_config["target_min_freq"] is None:
        status, spl = get3db(df_speaker, 3.0)
        if status is None:
            logger.debug("error: cannot get -3dB point for %s", current_speaker_name)
            optim_config["target_min_freq"] = 80  # arbitrary
        else:
            optim_config["target_min_freq"] = spl

    logger.debug("set target_min_freq to %.0fHz", optim_config["target_min_freq"])

    # create a few options for controling the optimiser
    configs = []
    # add a default config
    if use_score and optim_config.get("loss") == "score_loss":
        configs.append(
            {
                "curve_names": [
                    "Listening Window",
                    "Estimated In-Room Response",
                ],  # fit on the 2 curves
                "full_biquad_optim": optim_config.get("full_biquad_option", True),
                "smooth_measurements": optim_config.get("smooth_measurements", False),
                "loss": "score_loss",
            }
        )
    else:
        configs.append(
            {
                "curve_names": ["Listening Window"],  # robust default
                "full_biquad_optim": False,  # only PK
                "smooth_measurements": True,  # some smoothing
                "smooth_window_size": 21,
                "smooth_order": 3,
                "loss": "leastsquare_loss",  # robust function
            }
        )

    constraint_optim = False
    if (
        optim_config["curve_names"] is not None
        or optim_config["full_biquad_optim"] is not None
        or optim_config["smooth_measurements"] is not None
        or optim_config["smooth_window_size"] is not None
        or optim_config["smooth_order"] is not None
        or optim_config["loss"] is not None
    ):
        constraint_optim = True

    # add a few possible configs
    if constraint_optim is False:
        configs.append(
            {
                "curve_names": ["Listening Window"],
                "full_biquad_optim": True,
                "smooth_measurements": True,
                "smooth_window_size": 21,
                "smooth_order": 3,
                "loss": "leastsquare_loss",
            }
        )
        configs.append(
            {
                "curve_names": ["Estimated In-Room Response"],
                "full_biquad_optim": False,
                "smooth_measurements": True,
                "smooth_window_size": 21,
                "smooth_order": 3,
                "loss": "leastsquare_loss",
            }
        )
        configs.append(
            {
                "curve_names": ["Estimated In-Room Response"],
                "full_biquad_optim": True,
                "smooth_measurements": True,
                "smooth_window_size": 21,
                "smooth_order": 3,
                "loss": "leastsquare_loss",
            }
        )
        configs.append(
            {
                "curve_names": ["Listening Window"],
                "full_biquad_optim": True,
                "smooth_measurements": True,
                "smooth_window_size": 9,
                "smooth_order": 3,
                "loss": "leastsquare_loss",
            }
        )
        configs.append(
            {
                "curve_names": ["Estimated In-Room Response"],
                "full_biquad_optim": False,
                "smooth_measurements": True,
                "smooth_window_size": 9,
                "smooth_order": 3,
                "loss": "leastsquare_loss",
            }
        )
        configs.append(
            {
                "curve_names": ["Estimated In-Room Response"],
                "full_biquad_optim": True,
                "smooth_measurements": True,
                "smooth_window_size": 9,
                "smooth_order": 3,
                "loss": "leastsquare_loss",
            }
        )
        if have_full_measurements(df_speaker):
            configs.append(
                {
                    "curve_names": ["Listening Window", "Estimated In-Room Response"],
                    "full_biquad_optim": True,
                    "smooth_measurements": False,
                    "loss": "score_loss",
                }
            )

    # run optimiser for each config
    best_score = -1000.0
    results = None
    for config in configs:
        current_optim_config = deepcopy(optim_config)
        for k, v in config.items():
            current_optim_config[k] = v
        # don't compute configs that do not match
        if optim_config["curve_names"] is not None and set(optim_config["curve_names"]) != set(
            config["curve_names"]
        ):
            logger.debug(
                "curves: optim_config %s config %s current %s bool %s",
                optim_config["curve_names"],
                config["curve_names"],
                current_optim_config.get("curve_name"),
                constraint_optim,
            )
            if not constraint_optim:
                continue
            current_optim_config["curve_name"] = optim_config["curve_names"]

        # compute
        auto_status, (auto_score, auto_results, auto_peq, auto_slope_lw) = optim_eval_strategy(
            current_speaker_name, df_speaker, current_optim_config, use_score
        )
        logger.debug(
            "strategy: status %s score %s results %s peq %s slope %s",
            auto_status,
            auto_score,
            auto_results,
            auto_peq,
            auto_slope_lw,
        )
        if use_score:
            logger.info("strategy: %s %2.2f", auto_status, auto_score.get("pref_score", -1000.0))
        else:
            logger.info("strategy: %s %2.2f", auto_status, auto_results[1])

        if auto_status is False or len(auto_peq) == 0:
            logger.error(
                "optim_strategy failed for %s with %s",
                current_speaker_name,
                current_optim_config,
            )
            continue

        if (
            "CEA2034_unmelted" in df_speaker
            and auto_slope_lw is not None
            and optim_config.get("loss", "") != "score_loss"
            and not constraint_optim
        ):
            for loop in range(1, 6):
                # slope 20Hz-20kHz
                auto_slope_lw *= 11 / 3
                # name should be consistent but they are not
                slope_name = None
                if current_optim_config["curve_names"][0] == "Listening Window":
                    slope_name = "slope_listening_window"
                elif current_optim_config["curve_names"][0] == "Estimated In-Room Response":
                    slope_name = "slope_estimated_inroom"
                elif current_optim_config["curve_names"][0] == "On Axis":
                    slope_name = "slope_onaxis"
                elif current_optim_config["curve_names"][0] == "Sound Power":
                    slope_name = "slope_sound_power"
                elif current_optim_config["curve_names"][0] == "Early Reflections":
                    slope_name = "slope_early_reflections"

                if slope_name is None:
                    continue

                delta = 0.0
                if (
                    current_optim_config["curve_names"][0] == "Listening Window"
                    and auto_slope_lw >= 0
                    or auto_slope_lw > -1
                ):
                    delta = optim_config[slope_name] - np.sign(auto_slope_lw) * 0.5 * loop
                if (
                    current_optim_config["curve_names"][0] == "Estimated In-Room Response"
                    and auto_slope_lw >= 0
                    or auto_slope_lw < -1
                ):
                    delta = optim_config[slope_name] - np.sign(auto_slope_lw) * 0.5 * loop
                if delta == 0.0:
                    continue

                current_optim_config[slope_name] = delta
                auto_status2, (
                    auto_score2,
                    auto_results2,
                    auto_peq2,
                    auto_slope_lw2,
                ) = optim_eval_strategy(
                    current_speaker_name, df_speaker, current_optim_config, use_score
                )
                logger.debug(
                    "strategy2: %s %s %s %s %s",
                    auto_status2,
                    auto_score2,
                    auto_results2,
                    auto_peq2,
                    auto_slope_lw2,
                )
                logger.info(
                    "strategy2: %s %2.2f", auto_status2, auto_score2.get("pref_score", -1000.0)
                )
                if auto_status2 is False:
                    continue
                slope_is_admissible = (
                    auto_slope_lw2 * 11 / 3 > -0.5 and auto_slope_lw2 * 11 / 3 < 0.2
                )
                if not slope_is_admissible:
                    logger.info(
                        "debug slope is not admissible %s auto slope lw %f",
                        slope_is_admissible,
                        auto_slope_lw2 * 11 / 3,
                    )
                score_improved = False
                if auto_score2.get("pref_score", -1000.0) > auto_score.get("pref_score", -1000.0):
                    score_improved = True
                if not score_improved:
                    logger.debug("score didn't improved")
                    continue

                auto_score = deepcopy(auto_score2)
                auto_results = deepcopy(auto_results2)
                auto_peq = deepcopy(auto_peq2)
                auto_slope_lw = auto_slope_lw2
                logger.debug(
                    "new slope %1.1f init target %1.1f corrected target is %1.1f loop=%d score=%1.2f",
                    auto_slope_lw * 11 / 3,
                    optim_config["slope_listening_window"],
                    delta,
                    loop,
                    auto_score["pref_score"],
                )
                logger.info("end of loop %2.2f", auto_score["pref_score"])

        # store score
        if use_score and auto_score is not None:
            pref_score = auto_score.get("pref_score", -1000)
            if pref_score > best_score:
                best_score = pref_score
                results = auto_score, auto_results, auto_peq, current_optim_config
        else:
            print("DEBUG auto_results {}".format(auto_results))
            loss_score = auto_results[1]
            if loss_score > best_score:
                best_score = loss_score
                results = auto_score, auto_results, auto_peq, current_optim_config
            print("DEBUG results {}".format(results))

    if results:
        logger.info("stategy returns best score of %s", results[0])
        return True, (results[0], results[1], results[2], results[3])
    return False, ({}, (0, 0, 0), [], {})
