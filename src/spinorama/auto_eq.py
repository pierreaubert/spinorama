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

import contextlib
from copy import deepcopy
from datetime import datetime
import json
import os
import re
import pathlib

import numpy as np
import ray

from spinorama import logger, ray_setup_logger
from spinorama.constant_paths import CPATH_DOCS_SPEAKERS, MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ
from spinorama.pict import write_multiformat
from spinorama.compute_estimates import estimates_spin
from spinorama.compute_misc import compute_statistics
from spinorama.filter_peq import peq_format_apo, peq_print
from spinorama.filter_scores import (
    scores_apply_filter,
    noscore_apply_filter,
    scores_print,
)
from spinorama.auto_target import get_freq, get_target
from spinorama.auto_msteps import optim_multi_steps
from spinorama.auto_graph import graph_results as auto_graph_results


def get3db(spin, db_point):
    """Get -3dB point"""
    est = {}
    if "CEA2034_unmelted" in spin:
        est = estimates_spin(spin["CEA2034_unmelted"])
    elif "CEA2034" in spin and "Measurements" in spin:
        est = estimates_spin(spin["CEA2034"])
    return est.get("ref_3dB", None)


def optim_eval_strategy(
    current_speaker_name,
    df_speaker,
    optim_config,
    use_score,
):
    """Find the best EQ for this speaker"""
    # shortcut
    curves = optim_config["curve_names"]

    # get freq and targets
    data_frame, freq, auto_target = get_freq(df_speaker, optim_config)
    if data_frame is None or freq is None or auto_target is None:
        logger.error("Cannot compute freq for %s", current_speaker_name)
        return None, None, None, None

    auto_target_interp = []
    for curve in curves:
        target = get_target(data_frame, freq, curve, optim_config)
        auto_target_interp.append(target)

    auto_results, auto_peq = optim_multi_steps(
        current_speaker_name,
        df_speaker,
        freq,
        auto_target,
        auto_target_interp,
        optim_config,
        use_score,
    )

    auto_score = None
    auto_slope_lw = None
    if use_score:
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

    print("debug eval strategy")
    print("  auto score {}".format(auto_score))
    print("  auto results {}".format(auto_results))
    print("  auto peq")
    print(peq_print(auto_peq))
    print("  auto slope lw {}".format(auto_slope_lw))
    print("end debug eval strategy")
    return auto_score, auto_results, auto_peq, auto_slope_lw


def optim_strategy(current_speaker_name, df_speaker, optim_config, use_score):
    # do we use -3dB point for target?
    if optim_config["target_min_freq"] is None:
        spl = get3db(df_speaker, 3.0)
        if spl is None:
            logger.error("error: cannot get -3dB point for %s", current_speaker_name)
            return None, None, None, None
        optim_config["target_min_freq"] = spl

    logger.debug("set target_min_freq to %.0fHz", optim_config["target_min_freq"])

    # create a few options for controling the optimiser
    configs = []
    # add a default config
    configs.append(
        {
            "curve_names": ["Listening Window"],
            "full_biquad_optim": False,
            "smooth_measurements": True,
            "smooth_window_size": 21,
            "smooth_order": 3,
        }
    )

    constraint_optim = False
    if (
        optim_config["curve_names"] is not None
        or optim_config["full_biquad_optim"] is not None
        or optim_config["smooth_measurements"] is not None
        or optim_config["smooth_window_size"] is not None
        or optim_config["smooth_order"] is not None
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
            }
        )
        configs.append(
            {
                "curve_names": ["Estimated In-Room Response"],
                "full_biquad_optim": False,
                "smooth_measurements": True,
                "smooth_window_size": 21,
                "smooth_order": 3,
            }
        )
        configs.append(
            {
                "curve_names": ["Estimated In-Room Response"],
                "full_biquad_optim": True,
                "smooth_measurements": True,
                "smooth_window_size": 21,
                "smooth_order": 3,
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
            continue
        # compute
        auto_score, auto_results, auto_peq, auto_slope_lw = optim_eval_strategy(
            current_speaker_name, df_speaker, current_optim_config, use_score
        )
        if auto_peq is None or len(auto_peq) == 0:
            logger.error(
                "optim_eval_strategy failed for %s with %s",
                current_speaker_name,
                current_optim_config,
            )
            continue
        if "CEA2034_unmelted" in df_speaker and auto_slope_lw is not None:
            for loop in range(1, 6):
                # slope 20Hz-20kHz
                auto_slope_lw = auto_slope_lw * 11 / 3
                if auto_slope_lw > -1 and auto_slope_lw < -0.2:
                    # admissible range 0 means that On Axis will be (usually too hot)
                    break
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
                auto_score2, auto_results2, auto_peq2, auto_slope_lw2 = optim_eval_strategy(
                    current_speaker_name, df_speaker, current_optim_config, use_score
                )
                slope_is_admissible = (
                    auto_slope_lw2 * 11 / 3 > -1 and auto_slope_lw2 * 11 / 3 < -0.2
                )
                if not slope_is_admissible:
                    print(
                        "debug slope_is_admissible {} auto slope lw {}".format(
                            slope_is_admissible, auto_slope_lw2 * 11 / 3
                        )
                    )
                    continue
                score_improved = False
                if auto_score2.get("pref_score", -1000.0) > auto_score.get("pref_score", -1000.0):
                    score_improved = True
                if not score_improved:
                    print("debug score improved {}".format(score_improved))
                    continue

                auto_score = auto_score2
                auto_results = auto_results2
                auto_peq = auto_peq2
                auto_slope_lw = auto_slope_lw2
                logger.warning(
                    "new slope %1.1f init target %1.1f corrected target is %1.1f loop=%d score=%1.2f",
                    auto_slope_lw * 11 / 3,
                    optim_config["slope_listening_window"],
                    delta,
                    loop,
                    auto_score["pref_score"],
                )

        # store score
        if auto_score is not None:
            print("debug auto score {}".format(auto_score))
            print("debug auto results {}".format(auto_results))
            pref_score = auto_score.get("pref_score", -1000)
            if pref_score > best_score:
                best_score = pref_score
                results = auto_score, auto_results, auto_peq, current_optim_config
                print(
                    "debug score BEST pref_score {} best_score {} results_score {}".format(
                        pref_score, best_score, auto_results[2]
                    )
                )
            else:
                print(
                    "debug score NOT BETTER pref_score {} best_score {} results_score {}".format(
                        pref_score, best_score, auto_results[2]
                    )
                )

        else:
            loss_score = auto_results[1]
            if loss_score > best_score:
                best_score = loss_score
                results = auto_score, auto_results, auto_peq, current_optim_config
                print(
                    "debug loss pref_loss {} best_loss {} results_loss {}".format(
                        pref_score, best_score, auto_results[1]
                    )
                )
    if results:
        print(results[0]["pref_score"])
        print(results[1])
        print(results[2])
        print(results[3])
    return results


@ray.remote
def optim_save_peq(
    current_speaker_name,
    current_speaker_origin,
    df_speaker,
    df_speaker_eq,
    optim_config,
):
    """Compute and then save PEQ for this speaker"""
    ray_setup_logger(optim_config["level"])
    eq_dir = "datas/eq/{}".format(current_speaker_name)
    pathlib.Path(eq_dir).mkdir(parents=True, exist_ok=True)
    eq_name = "{}/iir-autoeq.txt".format(eq_dir)
    if optim_config["use_grapheq"]:
        grapheq_name = optim_config["grapheq_name"]
        short_name = grapheq_name.lower().replace(" ", "-")
        eq_name = "{}/iir-autoeq-{}.txt".format(eq_dir, short_name)
    if not optim_config["force"] and os.path.exists(eq_name):
        if optim_config["verbose"]:
            logger.info("eq %s already exist!", eq_name)
        return None, None, None

    # do we have CEA2034 data
    if "CEA2034_unmelted" not in df_speaker and "CEA2034" not in df_speaker:
        # this should not happen
        logger.error(
            "%s %s doesn't have CEA2034 data", current_speaker_name, current_speaker_origin
        )
        return None, None, None

    # do we have the full data?
    use_score = True
    if "SPL Horizontal_unmelted" not in df_speaker or "SPL Vertical_unmelted" not in df_speaker:
        use_score = False

    if current_speaker_origin == "Princeton":
        # we have SPL H and V but they are only above 500Hz so score computation fails.
        use_score = False
        # set EQ min to 500
        optim_config["freq_reg_min"] = max(500, optim_config["freq_reg_min"])

    score = None
    if use_score:
        _, _, score = scores_apply_filter(df_speaker, [])
    else:
        score = -1.0

    # compute pref score from speaker if possible
    auto_score, auto_results, auto_peq, auto_config = optim_strategy(
        current_speaker_name, df_speaker, optim_config, use_score
    )
    if auto_peq is None:
        logger.error("EQ generation failed for %s", current_speaker_name)
        return
    optim_config = deepcopy(auto_config)

    # compute new score with this PEQ
    auto_spin = None
    auto_pir = None
    auto_score = None
    scores = []
    if use_score:
        auto_spin, auto_pir, auto_score = scores_apply_filter(df_speaker, auto_peq)
        # store the 3 different scores
        scores = [
            score.get("pref_score", -1),
            auto_score["pref_score"],
        ]
    else:
        auto_spin, auto_pir, _ = noscore_apply_filter(df_speaker, auto_peq)

    # print peq
    comments = [f"EQ for {current_speaker_name} computed from {current_speaker_origin} data"]
    if use_score:
        comments.append(
            "Preference Score {:2.2f} with EQ {:2.2f}".format(
                score["pref_score"], auto_score["pref_score"]
            )
        )

    version = optim_config["version"]
    comments += [
        f"Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v{version}",
        f"Dated: {datetime.today().strftime('%Y-%m-%d-%H:%M:%S')}",
        "",
    ]
    eq_apo = peq_format_apo("\n".join(comments), auto_peq)

    # do we have a previous score?
    previous_score = None
    if os.path.exists(eq_name):
        with open(eq_name, "r", encoding="utf8") as read_fd:
            lines = read_fd.readlines()
            if len(lines) > 1:
                line_pref = lines[1]
                parsed = re.findall(r"[-+]?\d+(?:\.\d+)?", line_pref)
                if len(parsed) > 1:
                    previous_score = float(parsed[1])
                    logger.info(
                        "EQ prev_score %0.2f > %0.2f", previous_score, auto_score["pref_score"]
                    )

    skip_write_eq = False
    if optim_config["smoke_test"]:
        skip_write_eq = True
    elif use_score and previous_score is not None and previous_score > auto_score["pref_score"]:
        skip_write_eq = True

    if not skip_write_eq:
        with open(eq_name, "w", encoding="utf8") as write_fd:
            iir_txt = "iir.txt"
            iir_name = f"{eq_dir}/{iir_txt}"
            write_fd.write(eq_apo)
            if not os.path.exists(iir_name):
                with contextlib.suppress(OSError):
                    os.symlink("iir-autoeq.txt", iir_name)
                eq_conf = f"{eq_dir}/conf-autoeq.json"
                with open(eq_conf, "w", encoding="utf8") as write_fd:
                    conf_json = json.dumps(optim_config, indent=4)
                    write_fd.write(conf_json)
    else:
        logger.info(
            "skipping writing EQ prev_score %0.2f > %0.2f",
            previous_score,
            auto_score["pref_score"],
        )

    # print results
    curves = optim_config["curve_names"]
    if auto_peq is not None and len(auto_peq) > 0:
        data_frame, freq, auto_target = get_freq(df_speaker, optim_config)
        auto_target_interp = []
        for curve in curves:
            auto_target_interp.append(get_target(data_frame, freq, curve, optim_config))

        graphs = auto_graph_results(
            current_speaker_name,
            current_speaker_origin,
            freq,
            auto_peq,
            auto_target,
            auto_target_interp,
            df_speaker["CEA2034"],
            auto_spin,
            df_speaker["Estimated In-Room Response"],
            auto_pir,
            optim_config,
            score,
            auto_score,
        )

        for name, graph in graphs:
            origin = current_speaker_origin
            if "Vendors-" in origin:
                origin = origin[8:]
            graph_filename = "{}/{}/{}/filters_{}".format(
                CPATH_DOCS_SPEAKERS, current_speaker_name, origin, name
            )
            if optim_config["use_grapheq"]:
                grapheq_name = optim_config["grapheq_name"]
                short_name = grapheq_name.lower().replace(" ", "-")
                graph_filename += short_name
            if optim_config["smoke_test"]:
                graph_filename += "_smoketest"
            graph_filename += ".png"
            write_multiformat(chart=graph, filename=graph_filename, force=True)

    # print a compact table of results
    if optim_config["verbose"] and use_score:
        logger.info("%30s ---------------------------------------", current_speaker_name)
        if not skip_write_eq:
            logger.info(peq_format_apo("\n".join(comments), auto_peq))
            logger.info("----------------------------------------------------------------------")
        logger.info("ITER  LOSS SCORE -----------------------------------------------------")
        logger.info("  %2d %+2.2f %+2.2f", auto_results[0], auto_results[1], auto_results[2])
        logger.info("----------------------------------------------------------------------")
        logger.info("%30s ---------------------------------------", current_speaker_name)
        if score is not None and auto_score is not None and "nbd_on_axis" in auto_score:
            logger.info(scores_print(score, auto_score))
        logger.info("----------------------------------------------------------------------")
        if use_score:
            logger.info(
                "%+2.2f %+2.2f %s",
                score["pref_score"],
                auto_score["pref_score"],
                current_speaker_name,
            )

    return current_speaker_name, auto_results, scores
