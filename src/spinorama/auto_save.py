# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

import ray

from spinorama import logger, ray_setup_logger
from spinorama.ltype import DataSpeaker, OptimResult
from spinorama.constant_paths import CPATH_DOCS_SPEAKERS
from spinorama.load_rew_eq import parse_eq_iir_rews
from spinorama.pict import write_multiformat
from spinorama.filter_peq import peq_format_apo, Peq
from spinorama.filter_scores import (
    scores_apply_filter,
    scores_print,
)
from spinorama.auto_target import get_freq, get_target
from spinorama.auto_plot import graph_results as auto_graph_results
from spinorama.auto_strategy import optim_strategy


def get_previous_score(eq_name: str, auto_score: dict) -> None | float:
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
                        "EQ prev_score %0.2f new score %0.2f",
                        previous_score,
                        auto_score.get("pref_score", -1000.0),
                    )
    return previous_score


def write_eq_to_file(
    eq_dir: str,
    eq_name: str,
    speaker_name: str,
    speaker_origin: str,
    score: dict,
    auto_score: dict,
    auto_peq: Peq,
    optim_config: dict,
):
    comments = [f"EQ for {speaker_name} computed from {speaker_origin} data"]
    comments.append(
        "Preference Score {:2.2f} with EQ {:2.2f}".format(
            score.get("pref_score", -1000), auto_score.get("pref_score", -1000)
        )
    )

    version = optim_config["version"]
    comments += [
        f"Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v{version}",
        f"Dated: {datetime.today().strftime('%Y-%m-%d-%H:%M:%S')}",
        "",
    ]
    eq_apo = peq_format_apo("\n".join(comments), auto_peq)

    with open(eq_name, "w", encoding="utf8") as write_eq_fd:
        iir_txt = "iir.txt"
        iir_name = f"{eq_dir}/{iir_txt}"
        write_eq_fd.write(eq_apo)
        if not os.path.exists(iir_name):
            with contextlib.suppress(OSError):
                os.symlink("iir-autoeq.txt", iir_name)
            eq_conf = f"{eq_dir}/conf-autoeq.json"
            with open(eq_conf, "w", encoding="utf8") as write_conf_fd:
                conf_json = json.dumps(optim_config, indent=4)
                write_conf_fd.write(conf_json)


def print_auto_graphs(
    speaker_name,
    speaker_origin,
    df_speaker,
    auto_peq,
    auto_spin,
    auto_pir,
    score,
    auto_score,
    optim_config,
):
    curves = optim_config["curve_names"]
    if auto_peq is None or len(auto_peq) == 0:
        logger.debug("skipping printing graphs")

    data_frame, freq, auto_target = get_freq(df_speaker, optim_config)
    auto_target_interp = []
    for curve in curves:
        auto_target_interp.append(get_target(data_frame, freq, curve, optim_config))

        graphs = auto_graph_results(
            speaker_name,
            speaker_origin,
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
            origin = speaker_origin
            if "Vendors-" in origin:
                origin = origin[8:]
            graph_filename = "{}/{}/{}/filters_{}".format(
                CPATH_DOCS_SPEAKERS, speaker_name, origin, name
            )
            if optim_config["use_grapheq"]:
                grapheq_name = optim_config["grapheq_name"]
                short_name = grapheq_name.lower().replace(" ", "-")
                graph_filename += short_name
            if optim_config["smoke_test"]:
                graph_filename += "_smoketest"
            graph_filename += ".png"
            logger.debug("writing graph %s", graph_filename)
            write_multiformat(chart=graph, filename=graph_filename, force=True)


def print_small_summary(
    speaker_name,
    score,
    auto_score,
):
    logger.info("%30s ---------------------------------------", speaker_name)
    if score is not None and auto_score is not None and "nbd_on_axis" in auto_score:
        logger.info(scores_print(score, auto_score))
        logger.info("----------------------------------------------------------------------")
        logger.info(
            "%+2.2f %+2.2f %s",
            score["pref_score"],
            auto_score["pref_score"],
            speaker_name,
        )


def optim_save_peq_seq(
    current_speaker_name: str,
    current_speaker_origin: str,
    df_speaker: DataSpeaker,
    optim_config: dict,
) -> tuple[bool, tuple[str, OptimResult, list[dict]]]:
    """Compute and then save PEQ for this speaker"""
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
        logger.debug('Skipping %s since EQ already exist!', current_speaker_name)
        return False, ("", (0, 0, 0), [{}])

    # do we have CEA2034 data
    if "CEA2034_unmelted" not in df_speaker and "CEA2034" not in df_speaker:
        # this should not happen
        logger.error(
            "%s %s doesn't have CEA2034 data", current_speaker_name, current_speaker_origin
        )
        return False, ("", (0, 0, 0), [{}])

    # do we have the full data?
    use_score = True
    # EXPERIMENT
    # if "SPL Horizontal_unmelted" not in df_speaker or "SPL Vertical_unmelted" not in df_speaker:
    #    use_score = False
    # EXPERIMENT

    # don't optimise below the minimum freq found in measurements
    if current_speaker_origin == "Princeton":
        # we have SPL H and V but they are only above 500Hz so score computation fails.
        use_score = False
        # set EQ min to 500
        optim_config["freq_reg_min"] = max(500, optim_config["freq_reg_min"])
    else:
        min_freq = max(20, df_speaker["CEA2034_unmelted"].Freq.to_numpy().min())
        optim_config["freq_reg_min"] = max(min_freq, optim_config["freq_reg_min"])

    score = {}
    if use_score:
        logger.debug('Computing init score for %s', current_speaker_name)
        _, _, score = scores_apply_filter(df_speaker, [])

    # compute pref score from speaker if possible
    logger.debug('Calling strategy for %s', current_speaker_name)
    auto_status, (auto_score, auto_results, auto_peq, auto_config) = optim_strategy(
        current_speaker_name, df_speaker, optim_config, use_score
    )
    if auto_status is False:
        logger.error("EQ generation failed for %s", current_speaker_name)
        return False, ("", (0, 0, 0), [{}])
    optim_config = deepcopy(auto_config)

    # do we have a previous score?
    previous_score = get_previous_score(eq_name, auto_score)

    skip_write_eq = False
    if optim_config["smoke_test"] or (
        use_score and previous_score is not None and previous_score > auto_score["pref_score"]
    ):
        skip_write_eq = True

    if not skip_write_eq:
        write_eq_to_file(
            eq_dir,
            eq_name,
            current_speaker_name,
            current_speaker_origin,
            score,
            auto_score,
            auto_peq,
            optim_config,
        )
    else:
        logger.info(
            "skipping writing EQ prev_score %0.2f > %0.2f",
            previous_score,
            auto_score["pref_score"],
        )

    # compute new score with this PEQ
    auto_spin = None
    auto_pir = None
    scores = []
    if use_score:
        if previous_score is not None and previous_score > auto_score["pref_score"]:
            auto_peq = parse_eq_iir_rews(eq_name, 48000)

        if (
            previous_score is not None
            and previous_score < auto_score["pref_score"]
            and optim_config["verbose"]
        ):
            print("Current run is not a winner:")
            print_small_summary(current_speaker_name, score, auto_score)

        auto_spin, auto_pir, auto_score = scores_apply_filter(df_speaker, auto_peq)
        scores = [
            score.get("pref_score", -1000),
            auto_score.get("pref_score", -1000),
        ]
        if previous_score is not None and previous_score > auto_score["pref_score"]:
            scores[1] = previous_score

    if auto_spin is None or auto_pir is None:
        logger.error("Spin or PIR is none %s %s", current_speaker_name, current_speaker_origin)
    else:
        # print new best peq or re-print previous one
        print_auto_graphs(
            current_speaker_name,
            current_speaker_origin,
            df_speaker,
            auto_peq,
            auto_spin,
            auto_pir,
            score,
            auto_score,
            optim_config,
        )

    if optim_config["verbose"]:
        print_small_summary(current_speaker_name, score, auto_score)

    return True, (current_speaker_name, auto_results, scores)


@ray.remote
def optim_save_peq(
    current_speaker_name: str,
    current_speaker_origin: str,
    df_speaker: DataSpeaker,
    optim_config: dict,
) -> tuple[bool, tuple[str, OptimResult, list[dict]]]:
    """Compute and then save PEQ for this speaker"""
    ray_setup_logger(optim_config["level"])
    return optim_save_peq_seq(
        current_speaker_name, current_speaker_origin, df_speaker, optim_config
    )
