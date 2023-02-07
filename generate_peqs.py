#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2022 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
"""
usage: generate_peqs.py [--help] [--version] [--log-level=<level>] \
 [--force] [--smoke-test] [-v|--verbose] [--origin=<origin>] \
 [--speaker=<speaker>] [--mversion=<mversion>] [--mformat=<mformat>]\
 [--max-peq=<count>] [--min-Q=<minQ>] [--max-Q=<maxQ>] \
 [--min-dB=<mindB>] [--max-dB=<maxdB>] \
 [--min-freq=<minFreq>] [--max-freq=<maxFreq>] \
 [--max-iter=<maxiter>] [--use-all-biquad] [--curve-peak-only] \
 [--target-min-freq=<tminf>] [--target-max-freq=<tmaxf>] \
 [--slope-on-axis=<s_on>] \
 [--slope-on=<s_on>] \
 [--slope-listening-window=<s_lw>] \
 [--slope-lw=<s_lw>] \
 [--slope-early-reflections=<s_er>] \
 [--slope-er=<s_lw>] \
 [--slope-sound-power=<s_sp>] \
 [--slope-sp=<s_sp>] \
 [--slope-estimated-inroom=<s_pir>] \
 [--slope-pir=<s_pir>] \
 [--loss=<pick>] \
 [--dash-ip=<ip>] [--dash-port=<port>] [--ray-local] \
 [--smooth-measurements=<window_size>] \
 [--smooth-order=<order>] \
 [--second-optimiser=<sopt>] \
 [--curves=<curve_name>] \
 [--fitness=<function>] \
 [--graphic_eq=<eq_name>] \
 [--graphic_eq_list]

Options:
  --help                   Display usage()
  --version                Script version number
  --force                  Force generation of eq even if already computed
  --verbose                Print some informations
  --smoke-test             Test the optimiser with a small amount of variables
  --log-level=<level>      Default is WARNING, options are DEBUG or INFO or ERROR.
  --origin=<origin>        Restrict to a specific origin
  --speaker=<speaker>      Restrict to a specific speaker, if not specified it will optimise all speakers
  --mversion=<mversion>    Restrict to a specific mversion (for a given origin you can have multiple measurements)
  --mformat=<mformat>      Restrict to a specifig format (klippel, splHVtxt, gllHVtxt, webplotdigitizer, ...)
  --max-peq=<count>        Maximum allowed number of Biquad
  --min-Q=<minQ>           Minumum value for Q
  --max-Q=<maxQ>           Maximum value for Q
  --min-dB=<mindB>         Minumum value for dBGain
  --max-dB=<maxdB>         Maximum value for dBGain
  --min-freq=<minFreq>     Optimisation will happen above min freq
  --max-freq=<maxFreq>     Optimisation will happen below max freq
  --max-iter=<maxiter>     Maximum number of iterations
  --use-all-biquad         PEQ can be any kind of biquad (by default it uses only PK, PeaK)
  --curve-peak-only        Optimise both for peaks and valleys on a curve
  --dash-ip=<dash-ip>      IP for the ray dashboard to track execution
  --dash-port=<dash-port>  Port for the ray dashbboard
  --ray-local              If present, ray will run locally, it is usefull for debugging
  --target-min-freq=<tminf> targets will be flat up to min freq
  --target-max-freq=<tmaxf> targets will not be important after max freq
  --slope-on-axis=<s_on>   Slope of the ideal target for On Axis, default is 0, as in flat anechoic
  --slope-on=<s_lw>        Same as above (shortcut)
  --slope-listening-window=<s_lw> Slope of listening window, default is -0.5dB
  --slope-lw=<s_lw>        Same as above (shortcut)
  --slope-early-reflections=<s_er> Slope of early reflections, default is -5dB
  --slopw-er=<s_er>        Same as above (shortcut)
  --slope-sound-power=<s_sp> Slope of sound power, default is -8dB
  --slope-sp=<s_sp>        Same as above (shortcut)
  --slope-estimated-inroom=<s_pir> Slope of estimated in-room response, default is -8dB
  --slope-pir=<s_pir>      Same as above (shortcut)
  --second-optimiser=<sopt>
  --smooth-measurements=<window_size> If present the measurements will be smoothed before optimisation, window_size is the size of the window use for smoothing
  --smooth-order=<order>   Order of the interpolation, 3 by default for Savitzky-Golay filter.
  --curves=<curve_name>    Curve name: must be one of "ON", "LW", "PIR", "ER" or "SP" or a combinaison separated by a ,. Ex: 'PIR,LW' is valid
  --fitness=<function>     Fit function: must be one of "Flat", "Score", "LeastSquare", "FlatPir", "Combine".
  --graphic_eq=<eq_name>   Result is tailored for graphic_eq "name".
  --graphic_eq_list        List the known graphic eq and exit
"""
from datetime import datetime
from copy import deepcopy
import json
import os
import pathlib
import re
import sys


from docopt import docopt
import numpy as np
import pandas as pd

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray


from datas.metadata import speakers_info as metadata
from datas.grapheq import vendor_info as grapheq_info

from spinorama.constant_paths import CPATH_DOCS_SPEAKERS
from generate_common import get_custom_logger, args2level, custom_ray_init, cache_load
from spinorama.load_rewseq import parse_eq_iir_rews
from spinorama.compute_misc import compute_statistics
from spinorama.filter_peq import peq_format_apo
from spinorama.filter_scores import (
    scores_apply_filter,
    noscore_apply_filter,
    scores_print2,
    scores_print,
)
from spinorama.auto_target import get_freq, get_target
from spinorama.auto_optim import optim_multi_steps

from spinorama.auto_graph import graph_results as auto_graph_results


VERSION = "0.18"


def get3db(spin, db_point):
    onaxis = pd.DataFrame()
    if "Measurements" in spin.keys():
        onaxis = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
    else:
        onaxis = spin.get("On Axis", None)
    if onaxis is None or onaxis.empty:
        return None
    if onaxis.Freq.to_numpy()[0] > 150:
        return None

    y_ref = np.mean(onaxis.loc[(onaxis.Freq >= 300) & (onaxis.Freq <= 10000)].dB)
    y_3 = onaxis.loc[(onaxis.Freq < 150) & (onaxis.dB <= y_ref - db_point)].Freq.max()
    return y_3


def optim_find_peq(
    current_speaker_name,
    df_speaker,
    optim_config,
    use_score,
):
    # shortcut
    curves = optim_config["curve_names"]

    # get freq and targets
    data_frame, freq, auto_target = get_freq(df_speaker, optim_config)
    if data_frame is None or freq is None or auto_target is None:
        logger.error("Cannot compute freq for {}".format(current_speaker_name))
        return None, None, None

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
        unmelted_auto_spin = auto_spin.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max).reset_index()
        auto_slope_lw, _, _ = compute_statistics(unmelted_auto_spin, "Listening Window", 250, 10000, 300, 5000)

    return auto_score, auto_results, auto_peq, auto_slope_lw


def optim_strategy(current_speaker_name, df_speaker, optim_config, use_score):
    # do we use -3dB point for target?
    if optim_config["target_min_freq"] is None:
        spl = get3db(df_speaker, 6.0)
        if spl is None:
            return None, None, None, None
        optim_config["target_min_freq"] = spl

    # print("set target_min_freq to {}".format(optim_config["target_min_freq"]))

    # create a few options for controling the optimiser
    configs = []
    configs.append(
        {
            "curve_names": ["Listening Window"],
            "full_biquad_optim": False,
            "smooth_measurements": True,
            "smooth_window_size": 21,
            "smooth_order": 3,
        }
    )
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
    best_i = -1
    best_score = -1.0
    results = []
    for i, config in enumerate(configs):
        current_optim_config = deepcopy(optim_config)
        for k, v in config.items():
            # do not override if
            if k == "curve_names" and optim_config[k] is not None:
                continue
            # override config
            current_optim_config[k] = v
        # don't compute configs that do not match
        if optim_config["curve_names"] is not None and set(optim_config["curve_names"]) != set(config["curve_names"]):
            continue
        # compute
        auto_score, auto_results, auto_peq, auto_slope_lw = optim_find_peq(
            current_speaker_name, df_speaker, current_optim_config, use_score
        )
        if "CEA2034_unmelted" in df_speaker.keys() and auto_slope_lw is not None:
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

                if slope_name is not None:
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
                    if delta != 0.0:
                        current_optim_config[slope_name] = delta
                        auto_score2, auto_results2, auto_peq2, auto_slope_lw2 = optim_find_peq(
                            current_speaker_name, df_speaker, current_optim_config, use_score
                        )
                        if auto_slope_lw2 * 11 / 3 > -1 and auto_slope_lw2 * 11 / 3 < -0.2:
                            auto_score = auto_score2
                            auto_result = auto_results2
                            auto_peq = auto_peq2
                            auto_slope_lw = auto_slope_lw2
                            print(
                                "new slope {} init target {} corrected target is {} loop={} score={}".format(
                                    auto_slope_lw * 11 / 3,
                                    optim_config["slope_listening_window"],
                                    delta,
                                    loop,
                                    auto_score["pref_score"],
                                )
                            )

        # store score
        if auto_score is not None:
            pref_score = auto_score.get("pref_score", -1)
            if pref_score > best_score:
                best_score = pref_score
                best_i = len(results)
        else:
            loss_score = auto_results[-1][1]
            if loss_score > best_score:
                best_score = loss_score
                best_i = len(results)
        results.append((auto_score, auto_results, auto_peq, current_optim_config))

    if best_i >= 0:
        return results[best_i]
    return None, None, None, None


@ray.remote
def optim_save_peq(
    current_speaker_name,
    current_speaker_origin,
    df_speaker,
    df_speaker_eq,
    optim_config,
):
    """Compute and then save PEQ for this speaker"""
    eq_dir = "datas/eq/{}".format(current_speaker_name)
    pathlib.Path(eq_dir).mkdir(parents=True, exist_ok=True)
    eq_name = "{}/iir-autoeq.txt".format(eq_dir)
    if optim_config["use_grapheq"]:
        grapheq_name = optim_config["grapheq_name"]
        short_name = grapheq_name.lower().replace(" ", "-")
        eq_name = "{}/iir-autoeq-{}.txt".format(eq_dir, short_name)
    if not force and os.path.exists(eq_name):
        if verbose:
            logger.info(f"eq {eq_name} already exist!")
        return None, None, None

    # do we have CEA2034 data
    if "CEA2034_unmelted" not in df_speaker.keys() and "CEA2034" not in df_speaker.keys():
        # this should not happen
        logger.error("{} {} doesn't have CEA2034 data".format(current_speaker_name, current_speaker_origin))
        return None, None, None

    # do we have the full data?
    use_score = True
    if "SPL Horizontal_unmelted" not in df_speaker.keys() or "SPL Vertical_unmelted" not in df_speaker.keys():
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
    auto_score, auto_results, auto_peq, auto_config = optim_strategy(current_speaker_name, df_speaker, optim_config, use_score)
    if auto_peq is None:
        print("EQ generation failed for {}".format(current_speaker_name))
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
        comments.append("Preference Score {:2.2f} with EQ {:2.2f}".format(score["pref_score"], auto_score["pref_score"]))

    comments += [
        f"Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v{VERSION}",
        "Dated: {}".format(datetime.today().strftime("%Y-%m-%d-%H:%M:%S")),
        "",
    ]
    eq_apo = peq_format_apo("\n".join(comments), auto_peq)

    # print eq
    if not smoke_test:
        previous_score = None
        if os.path.exists(eq_name):
            with open(eq_name, "r", encoding="ascii") as read_fd:
                lines = read_fd.readlines()
                if len(lines) > 1:
                    line_pref = lines[1]
                    parsed = re.findall(r"[-+]?\d+(?:\.\d+)?", line_pref)
                    if len(parsed) > 1:
                        previous_score = float(parsed[1])

        skip = False
        if force is False and use_score and previous_score is not None and previous_score > auto_score["pref_score"]:
            skip = True

        # print('EQ prev_score {:0.2f} > {:0.2f}'.format(previous_score, auto_score["pref_score"]))

        if not skip:
            with open(eq_name, "w", encoding="ascii") as write_fd:
                iir_txt = "iir.txt"
                iir_name = f"{eq_dir}/{iir_txt}"
                write_fd.write(eq_apo)
                if not os.path.exists(iir_name):
                    try:
                        os.symlink("iir-autoeq.txt", iir_name)
                    except OSError:
                        pass
            eq_conf = f"{eq_dir}/conf-autoeq.json"
            with open(eq_conf, "w", encoding="ascii") as write_fd:
                conf_json = json.dumps(optim_config, indent=4)
                write_fd.write(conf_json)
        else:
            print("skipping writing EQ prev_score {:0.2f} > {:0.2f}".format(previous_score, auto_score["pref_score"]))

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

        for i, (name, graph) in enumerate(graphs):
            origin = current_speaker_origin
            if "Vendors-" in origin:
                origin = origin[8:]
            graph_filename = "{}/{}/{}/filters_{}".format(CPATH_DOCS_SPEAKERS, current_speaker_name, origin, name)
            if smoke_test:
                graph_filename += "_smoketest"
            graph_filename += ".png"
            graph.write_image(graph_filename)

    # print a compact table of results
    if verbose and use_score:
        logger.info("{:30s} ---------------------------------------".format(current_speaker_name))
        logger.info(peq_format_apo("\n".join(comments), auto_peq))
        logger.info("----------------------------------------------------------------------")
        logger.info("ITER  LOSS SCORE -----------------------------------------------------")
        logger.info("\n".join(["  {:2d} {:+2.2f} {:+2.2f}".format(r[0], r[1], r[2]) for r in auto_results]))
        logger.info("----------------------------------------------------------------------")
        logger.info("{:30s} ---------------------------------------".format(current_speaker_name))
        if score is not None and auto_score is not None and "nbd_on_axis" in auto_score:
            logger.info(scores_print(score, auto_score))
        logger.info("----------------------------------------------------------------------")
        if use_score:
            print(
                "{:+2.2f} {:+2.2f} {:s}".format(
                    score["pref_score"],
                    auto_score["pref_score"],
                    current_speaker_name,
                )
            )

    return current_speaker_name, auto_results, scores


def queue_speakers(df_all_speakers, optim_config, speaker_name):
    ray_ids = {}
    for current_speaker_name in df_all_speakers.keys():
        if speaker_name is not None and current_speaker_name != speaker_name:
            continue
        default = None
        default_eq = None
        default_origin = None
        if current_speaker_name in metadata.keys() and "default_measurement" in metadata[current_speaker_name].keys():
            default = metadata[current_speaker_name]["default_measurement"]
            default_eq = "{}_eq".format(default)
            default_origin = metadata[current_speaker_name]["measurements"][default]["origin"]
        else:
            logger.error("no default_measurement for {}".format(current_speaker_name))
            continue
        if default_origin not in df_all_speakers[current_speaker_name].keys():
            print("error: default origin {} not in {}".format(default_origin, current_speaker_name))
            continue
        if default not in df_all_speakers[current_speaker_name][default_origin].keys():
            print("error: default {} not in default origin {} for {}".format(default, default_origin, current_speaker_name))
            continue
        df_speaker = df_all_speakers[current_speaker_name][default_origin][default]
        if not (
            ("SPL Horizontal_unmelted" in df_speaker.keys() and "SPL Vertical_unmelted" in df_speaker.keys())
            or ("CEA2034" in df_speaker.keys() and "Estimated In-Room Response" in df_speaker.keys())
        ):
            logger.info("not enough data for {} known measurements are {}".format(current_speaker_name, df_speaker.keys()))
            continue
        df_speaker_eq = None
        if default_eq in df_all_speakers[current_speaker_name][default_origin].keys():
            df_speaker_eq = df_all_speakers[current_speaker_name][default_origin][default_eq]

        current_id = optim_save_peq.remote(
            current_speaker_name,
            default_origin,
            df_speaker,
            df_speaker_eq,
            optim_config,
        )
        ray_ids[current_speaker_name] = current_id

    print("Queing {} speakers for EQ computations".format(len(ray_ids)))
    return ray_ids


def compute_peqs(ray_ids):
    done_ids = set()
    aggregated_results = {}
    aggregated_scores = {}
    scores = None
    while 1:
        ids = [current_id for current_id in ray_ids.values() if current_id not in done_ids]
        num_returns = min(len(ids), 16)
        ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)

        for current_id in ready_ids:
            get_results = ray.get(current_id)
            if get_results is None:
                continue
            current_speaker_name, results_iter, scores = get_results
            if results_iter is not None:
                aggregated_results[current_speaker_name] = results_iter
            if scores is not None:
                aggregated_scores[current_speaker_name] = scores
            done_ids.add(current_id)

        if len(remaining_ids) == 0:
            break

        logger.info("State: {0} ready IDs {1} remainings IDs ".format(len(ready_ids), len(remaining_ids)))

    v_sn = []
    v_iter = []
    v_loss = []
    v_score = []
    for speaker, results in aggregated_results.items():
        for current_result in results:
            if current_result is not None and len(current_result) > 2:
                v_sn.append("{}".format(speaker))
                v_iter.append(current_result[0])
                v_loss.append(current_result[1])
                v_score.append(current_result[2])
    df_results = pd.DataFrame({"speaker_name": v_sn, "iter": v_iter, "loss": v_loss, "score": v_score})
    df_results.to_csv("results_iter.csv", index=False)

    if scores is not None and len(scores) == 3:
        s_sn = []
        s_ref = []
        s_manual = []
        s_auto = []
        for speaker, scores in aggregated_scores.items():
            if scores is not None and len(scores) > 2:
                s_sn.append("{}".format(speaker))
                s_ref.append(scores[0])
                s_manual.append(scores[1])
                s_auto.append(scores[2])
        df_scores = pd.DataFrame(
            {
                "speaker_name": s_sn,
                "reference": s_ref,
                "manual": s_manual,
                "auto": s_auto,
            }
        )
        df_scores.to_csv("results_scores.csv", index=False)

    return 0


def main():
    parameter_error = False

    # read optimisation parameter
    current_optim_config = {
        # name of the loss function
        # "loss": "flat_loss",
        # "loss": "score_loss",
        # "loss": "combine_loss",
        "loss": "leastsquare_loss",
        # "loss": "flat_pir",
        # if you have multiple loss functions, define the weigth for each
        "loss_weigths": [100.0, 1.0],
        # do you optimise only peaks or both peaks and valleys?
        "plus_and_minus": True,
        # do you optimise for all kind of biquad or do you want only Peaks?
        "full_biquad_optim": False,
        # lookup around a value is [value*elastic, value/elastic]
        # "elastic": 0.2,
        "elastic": 0.8,
        # cut frequency
        "fs": 48000,
        # freq range for EQ
        "freq_reg_min": 20,
        "freq_reg_max": 20000,
        # if an algorithm use a mean of frequency to find a reference level
        # compute it over [min, max]hz
        "freq_mean_min": 100,
        "freq_mean_max": 300,
        # optimisation is on both curves
        # depending on the algorithm it is not doing the same things
        # for example: with flat_loss (the default)
        # it will optimise for having a Listening Window as close as possible
        # the target and having a Sound Power as flat as possible (without a
        # target)
        "curve_names": None,
        # "curve_names": ["Listening Window"],
        # 'curve_names': ['Early Reflections'],
        # 'curve_names': ['Listening Window', 'Early Reflections'],
        # "curve_names": ["On Axis", "Listening Window", "Early Reflections"],
        # "curve_names": ["Listening Window", "Estimated In-Room Response"],
        # "curve_names": ["Listening Window", "Early Reflections", "Sound Power"],
        # 'curve_names': ['Listening Window', 'On Axis', 'Early Reflections'],
        # 'curve_names': ['On Axis', 'Early Reflections'],
        # 'curve_names': ['Early Reflections', 'Sound Power'],
        # "curve_names": ["Estimated In-Room Response", "Listening Window"],
        # "curve_names": ["Estimated In-Room Response"],
        # start and end freq for targets and optimise in this range
        "target_min_freq": None,  # by default it will be set to -3dB point if not given on the command line
        "target_max_freq": 16000,
        # slope of the target (in dB) for each curve
        "slope_on_axis": 0,  # flat on axis
        "slope_listening_window": -0.5,  # slighly lower if not on is too hot
        "slope_early_reflections": -4,
        "slope_estimated_inroom": -6.5,
        "slope_sound_power": -9,  # good for long distance, too dark for near field
        # do we want to smooth the targets?
        "smooth_measurements": False,
        # size of the window to smooth (currently in number of data points but could be in octave)
        "smooth_window_size": -1,
        # order of interpolation (you can try 1 (linear), 2 (quadratic) etc)
        "smooth_order": 3,
        # graph eq?
        "use_grapheq": False,
        "grapheq_name": None,
        # use -3dB point as a starting point for target
        "use_3dB_target": True,
    }

    # define other parameters for the optimisation algorithms
    # MAX_STEPS_XXX are usefull for grid search when the algorithm is looking
    # for random values (or trying all) across a range
    if smoke_test:
        current_optim_config["MAX_NUMBER_PEQ"] = 5
        current_optim_config["MAX_STEPS_FREQ"] = 3
        current_optim_config["MAX_STEPS_DBGAIN"] = 3
        current_optim_config["MAX_STEPS_Q"] = 3
        # max iterations (if algorithm is iterative)
        current_optim_config["maxiter"] = 20
    else:
        current_optim_config["MAX_NUMBER_PEQ"] = 9
        current_optim_config["MAX_STEPS_FREQ"] = 6
        current_optim_config["MAX_STEPS_DBGAIN"] = 6
        current_optim_config["MAX_STEPS_Q"] = 6
        # max iterations (if algorithm is iterative)
        current_optim_config["maxiter"] = 150

    # MIN or MAX_Q or MIN or MAX_DBGAIN control the shape of the biquad which
    # are admissible.
    current_optim_config["MIN_DBGAIN"] = 0.5
    current_optim_config["MAX_DBGAIN"] = 3
    current_optim_config["MIN_Q"] = 0.05
    current_optim_config["MAX_Q"] = 3

    # do we override optim default?
    if args["--max-peq"] is not None:
        max_number_peq = int(args["--max-peq"])
        current_optim_config["MAX_NUMBER_PEQ"] = max_number_peq
        if max_number_peq < 1:
            print("ERROR: max_number_peq is {} which is below 1".format(max_number_peq))
            parameter_error = True
    if args["--max-iter"] is not None:
        max_iter = int(args["--max-iter"])
        current_optim_config["maxiter"] = max_iter
        if max_iter < 1:
            print("ERROR: max_iter is {} which is below 1".format(max_iter))
            parameter_error = True
    if args["--min-freq"] is not None:
        min_freq = int(args["--min-freq"])
        current_optim_config["freq_reg_min"] = min_freq
        if min_freq <= 20:
            print("ERROR: min_freq is {} which is below 20Hz".format(min_freq))
            parameter_error = True
    if args["--max-freq"] is not None:
        max_freq = int(args["--max-freq"])
        current_optim_config["freq_reg_max"] = max_freq
        if max_freq >= 20000:
            print("ERROR: max_freq is {} which is above 20kHz".format(max_freq))
            parameter_error = True

    if args["--min-Q"] is not None:
        min_Q = float(args["--min-Q"])
        current_optim_config["MIN_Q"] = min_Q
    if args["--max-Q"] is not None:
        max_Q = float(args["--max-Q"])
        current_optim_config["MAX_Q"] = max_Q
    if args["--min-dB"] is not None:
        min_dB = float(args["--min-dB"])
        current_optim_config["MIN_DBGAIN"] = min_dB
    if args["--max-dB"] is not None:
        max_dB = float(args["--max-dB"])
        current_optim_config["MAX_DBGAIN"] = max_dB

    if args["--use-all-biquad"] is not None and args["--use-all-biquad"] is True:
        current_optim_config["full_biquad_optim"] = True
    if args["--curve-peak-only"] is not None and args["--curve-peak-only"] is True:
        current_optim_config["plus_and_minus"] = False

    if args["--target-min-freq"] is not None:
        target_min_freq = int(args["--target-min-freq"])
        current_optim_config["target_min_freq"] = target_min_freq
    if args["--target-max-freq"] is not None:
        target_max_freq = int(args["--target-max-freq"])
        current_optim_config["target_max_freq"] = target_max_freq

    for slope_name, slope_key in (
        ("--slope-on-axis", "slope_on_axis"),
        ("--slope-listening-window", "slope_listening_window"),
        ("--slope-early-reflections", "slope_early_reflections"),
        ("--slope-sound-power", "slope_sound_power"),
        ("--slope-estimated-inroom", "slope_estimated_inroom"),
        ("--slope-on", "slope_on_axis"),
        ("--slope-lw", "slope_listening_window"),
        ("--slope-er", "slope_early_reflections"),
        ("--slope-sp", "slope_sound_power"),
        ("--slope-pir", "slope_estimated_inroom"),
    ):
        if args[slope_name] is not None:
            try:
                slope = float(args[slope_name])
                current_optim_config[slope_key] = slope
            except ValueError:
                print("{} is not a float".format(args[slope_name]))
                sys.exit(1)

    if args["--smooth-measurements"] is not None:
        window_size = int(args["--smooth-measurements"])
        current_optim_config["smooth_measurements"] = True
        current_optim_config["smooth_window_size"] = window_size
        if window_size < 2:
            print("ERROR: window size is {} which is below 2".format(window_size))
            parameter_error = True

    if args["--smooth-order"] is not None:
        order = int(args["--smooth-order"])
        current_optim_config["smooth_order"] = order
        if order < 1 or order > 5:
            print("ERROR: Polynomial order {} is not between  is 1 and 5".format(order))
            parameter_error = True

    # do we run a second optimiser?
    current_optim_config["second_optimiser"] = False
    if args["--second-optimiser"] is not None:
        current_optim_config["second_optimiser"] = True

    # which curve (measurement) to target?
    if args["--curves"] is not None:
        param_curve_names = args["--curves"].replace(" ", "").split(",")
        param_curve_name_valid = {
            "ON": "On Axis",
            "LW": "Listening Window",
            "ER": "Early Reflections",
            "SP": "Sound Power",
            "PIR": "Estimated In-Room Response",
        }
        current_optim_config["curve_names"] = []
        for current_curve_name in param_curve_names:
            if current_curve_name not in param_curve_name_valid.keys():
                print(
                    "ERROR: {} is not known, acceptable values are {}",
                    current_curve_name,
                    param_curve_name_valid.keys(),
                )
                parameter_error = True
            else:
                current_optim_config["curve_names"].append(param_curve_name_valid[current_curve_name])

    # which fitness function?
    if args["--fitness"] is not None:
        current_fitness_name = args["--fitness"]
        param_fitness_name_valid = {
            "Flat": "flat_loss",
            "Score": "score_loss",
            "Combine": "combine_loss",
            "LeastSquare": "leastsquare_loss",
            "FlatPir": "flat_pir",
        }
        if current_fitness_name not in param_fitness_name_valid.keys():
            print(
                "ERROR: {} is not known, acceptable values are {}",
                current_fitness_name,
                param_fitness_name_valid.keys(),
            )
            parameter_error = True
        else:
            current_optim_config["loss"] = param_fitness_name_valid[current_fitness_name]

    # do we build EQ for a HW graphic one?
    if args["--graphic_eq"] is not None:
        grapheq_name = args["--graphic_eq"]
        if grapheq_name not in grapheq_info.keys():
            print("ERROR: EQ name {} is not known. Please select on in {}".format(grapheq_name, grapheq_info.keys()))
            sys.exit(1)
        current_optim_config["use_grapheq"] = True
        current_optim_config["grapheq_name"] = grapheq_name

    # name of speaker
    speaker_name = None
    if args["--speaker"] is not None:
        speaker_name = args["--speaker"]

    origin = None
    if args["--origin"] is not None:
        origin = args["--origin"]

    mversion = None
    if args["--mversion"] is not None:
        mversion = args["--mversion"]

    mformat = None
    if args["--mformat"] is not None:
        mformat = args["--mformat"]

    # error in parameters
    if parameter_error:
        print("ERROR: please check for errors in parameters above!")
        sys.exit(1)

    # load data
    print("Reading cache ...", end=" ", flush=True)
    df_all_speakers = {}
    try:
        filters = {
            "speaker_name": speaker_name,
            "format": mformat,
            "origin": origin,
            "version": mversion,
        }
        df_all_speakers = cache_load(filters=filters, smoke_test=smoke_test)
    except ValueError as v_e:
        if speaker_name is not None:
            print(
                "ERROR: Speaker {0} is not in the cache. Did you run ./generate_graphs.py --speaker='{0}' --update-cache ?".format(
                    speaker_name
                )
            )
        else:
            print(f"{v_e}")
        sys.exit(1)

    # start ray
    custom_ray_init(args)

    ids = queue_speakers(df_all_speakers, current_optim_config, speaker_name)
    compute_peqs(ids)

    sys.exit(0)


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="generate_peqs.py version {}".format(VERSION),
        options_first=True,
    )

    logger = get_custom_logger(True)
    logger.setLevel(args2level(args))

    force = args["--force"]
    verbose = args["--verbose"]
    smoke_test = args["--smoke-test"]

    if args["--graphic_eq_list"]:
        print("INFO: The list of know graphical EQ is: {}".format(grapheq_info.keys()))
        sys.exit(0)

    main()
