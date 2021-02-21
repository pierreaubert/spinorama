#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
usage: generate_peqs.py [--help] [--version] [--log-level=<level>] [--force] [--smoke-test] [-v|--verbose] [--origin=<origin>] [--speaker=<speaker>] [--mversion=<mversion>] [--max-peq=<count>] [--min-Q=<minQ>] [--max-Q=<maxQ>] [--min-dB=<mindB>] [--max-dB=<maxdB>]  [--min-freq=<minFreq>] [--max-freq=<maxFreq>][--max-iter=<maxiter>] [--use-all-biquad] [--curve-peak-only] [--loss=<pick>] [--dash-ip=<dash-ip>] [--dash-port=<dash-port>]

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
"""
from datetime import datetime
import os
import pathlib
import sys
from typing import Literal, List, Tuple

from docopt import docopt
import flammkuchen as fl
import pandas as pd
import ray

from generate_common import get_custom_logger, args2level, custom_ray_init
from datas.metadata import speakers_info as metadata
from spinorama.load_rewseq import parse_eq_iir_rews
from spinorama.filter_peq import peq_format_apo
from spinorama.filter_scores import scores_apply_filter, scores_print2
from spinorama.auto_target import get_freq, get_target
from spinorama.auto_optim import optim_greedy
from spinorama.auto_graph import graph_results as auto_graph_results


VERSION = 0.5


@ray.remote
def optim_save_peq(
    speaker_name, df_speaker, df_speaker_eq, optim_config, be_verbose, is_smoke_test
):
    """Compute ans save PEQ for this speaker """
    eq_dir = "datas/eq/{}".format(speaker_name)
    pathlib.Path(eq_dir).mkdir(parents=True, exist_ok=True)
    eq_name = "{}/iir-autoeq.txt".format(eq_dir)
    if not force and os.path.exists(eq_name):
        if be_verbose:
            logger.info("eq {} already exist!".format(eq_name))
        return None, None, None

    # extract current speaker
    _, _, score = scores_apply_filter(df_speaker, [])

    # compute an optimal PEQ
    curves = optim_config["curve_names"]
    df, freq, auto_target = get_freq(df_speaker, optim_config)
    auto_target_interp = []
    for curve in curves:
        auto_target_interp.append(get_target(df, freq, curve, optim_config))
    auto_results, auto_peq = optim_greedy(
        speaker_name, df_speaker, freq, auto_target, auto_target_interp, optim_config
    )

    # do we have a manual peq?
    score_manual = {}
    manual_peq = []
    manual_target = None
    manual_target_interp = None
    manual_spin, manual_pir = None, None
    if be_verbose:
        manual_peq_name = "./datas/eq/{}/iir.txt".format(speaker_name)
        manual_peq = parse_eq_iir_rews(manual_peq_name, optim_config["fs"])
        manual_spin, manual_pir, score_manual = scores_apply_filter(
            df_speaker, manual_peq
        )
        if df_speaker_eq is not None:
            manual_df, manual_freq, manual_target = get_freq(
                df_speaker_eq, optim_config
            )
            manual_target_interp = []
            for curve in curves:
                manual_target_interp.append(
                    get_target(manual_df, manual_freq, curve, optim_config)
                )

    # compute new score with this PEQ
    spin_auto, pir_auto, score_auto = scores_apply_filter(df_speaker, auto_peq)

    # store the 3 different scores
    scores = [score["pref_score"], score["pref_score"], score_auto["pref_score"]]
    if be_verbose:
        scores[1] = score_manual["pref_score"]

    # print peq
    comments = [
        "EQ for {:s} computed from ASR data".format(speaker_name),
        "Preference Score {:2.1f} with EQ {:2.1f}".format(
            score["pref_score"], score_auto["pref_score"]
        ),
        "Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v{}".format(
            VERSION
        ),
        "Dated: {}".format(datetime.today().strftime("%Y-%m-%d-%H:%M:%S")),
        "",
    ]
    eq_apo = peq_format_apo("\n".join(comments), auto_peq)

    # print eq
    if not is_smoke_test:
        with open(eq_name, "w") as fd:
            fd.write(eq_apo)
            iir_txt = "iir.txt"
            iir_name = "{}/{}".format(eq_dir, iir_txt)
            if not os.path.exists(iir_name):
                try:
                    os.symlink("iir-autoeq.txt", iir_name)
                except OSError:
                    pass

    # print results
    if len(manual_peq) > 0 and len(auto_peq) > 0:
        graphs = auto_graph_results(
            speaker_name,
            freq,
            manual_peq,
            auto_peq,
            auto_target,
            auto_target_interp,
            manual_target,
            manual_target_interp,
            df_speaker["CEA2034"],
            manual_spin,
            spin_auto,
            df_speaker["Estimated In-Room Response"],
            manual_pir,
            pir_auto,
            optim_config,
        )
        for i, graph in enumerate(graphs):
            graph_filename = "docs/{}/ASR/filters{}".format(speaker_name, i)
            if is_smoke_test:
                graph_filename += "_smoketest"
            graph_filename += ".png"
            graph.save(graph_filename)

    # print a compact table of results
    if be_verbose:
        logger.info(
            "{:30s} ---------------------------------------".format(speaker_name)
        )
        logger.info(peq_format_apo("\n".join(comments), auto_peq))
        logger.info(
            "----------------------------------------------------------------------"
        )
        logger.info(
            "ITER  LOSS SCORE -----------------------------------------------------"
        )
        logger.info(
            "\n".join(
                [
                    "  {:2d} {:+2.2f} {:+2.2f}".format(r[0], r[1], r[2])
                    for r in auto_results
                ]
            )
        )
        logger.info(
            "----------------------------------------------------------------------"
        )
        logger.info(
            "{:30s} ---------------------------------------".format(speaker_name)
        )
        logger.info(scores_print2(score, score_manual, score_auto))
        logger.info(
            "----------------------------------------------------------------------"
        )
        print(
            "{:+2.2f} {:+2.2f} {:+2.2f} {:+2.2f} {:s}".format(
                score["pref_score"],
                score_manual["pref_score"],
                score_auto["pref_score"],
                score_manual["pref_score"] - score_auto["pref_score"],
                speaker_name,
            )
        )

    return speaker_name, auto_results, scores


def queue_speakers(df_all_speakers, optim_config, be_verbose, is_smoke_test):
    ray_ids = {}
    for speaker_name in df_all_speakers.keys():
        if "ASR" not in df_all_speakers[speaker_name].keys():
            # currently doing only ASR but should work for the others
            # Princeton start around 500hz
            continue
        default = "asr"
        default_eq = "asr_eq"
        if (
            speaker_name in metadata.keys()
            and "default_measurement" in metadata[speaker_name].keys()
        ):
            default = metadata[speaker_name]["default_measurement"]
            default_eq = "{}_eq".format(default)
        if default not in df_all_speakers[speaker_name]["ASR"].keys():
            logger.error("no {} for {}".format(default, speaker_name))
            continue
        df_speaker = df_all_speakers[speaker_name]["ASR"][default]
        if (
            "SPL Horizontal_unmelted" not in df_speaker.keys()
            or "SPL Vertical_unmelted" not in df_speaker.keys()
        ):
            logger.error(
                "no Horizontal or Vertical measurement for {}".format(speaker_name)
            )
            continue
        df_speaker_eq = None
        if default_eq in df_all_speakers[speaker_name]["ASR"].keys():
            df_speaker_eq = df_all_speakers[speaker_name]["ASR"][default_eq]

        id = optim_save_peq.remote(
            speaker_name,
            df_speaker,
            df_speaker_eq,
            optim_config,
            be_verbose,
            is_smoke_test,
        )
        ray_ids[speaker_name] = id

    print("Queing {} speakers for EQ computations".format(len(ray_ids)))
    return ray_ids


def compute_peqs(ray_ids):
    done_ids = set()
    aggregated_results = {}
    aggregated_scores = {}
    while 1:
        ids = [id for id in ray_ids.values() if id not in done_ids]
        num_returns = min(len(ids), 16)
        ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)

        for id in ready_ids:
            speaker_name, results_iter, scores = ray.get(id)
            if results_iter is not None:
                aggregated_results[speaker_name] = results_iter
            if scores is not None:
                aggregated_scores[speaker_name] = scores
            done_ids.add(id)

        if len(remaining_ids) == 0:
            break

        logger.info(
            "State: {0} ready IDs {1} remainings IDs ".format(
                len(ready_ids), len(remaining_ids)
            )
        )

    v_sn = []
    v_iter = []
    v_loss = []
    v_score = []
    for speaker, results in aggregated_results.items():
        for r in results:
            v_sn.append("{}".format(speaker))
            v_iter.append(r[0])
            v_loss.append(r[1])
            v_score.append(r[2])
    df_results = pd.DataFrame(
        {"speaker_name": v_sn, "iter": v_iter, "loss": v_loss, "score": v_score}
    )
    df_results.to_csv("results_iter.csv", index=False)

    s_sn = []
    s_ref = []
    s_manual = []
    s_auto = []
    for speaker, scores in aggregated_scores.items():
        s_sn.append("{}".format(speaker))
        s_ref.append(scores[0])
        s_manual.append(scores[1])
        s_auto.append(scores[2])
    df_scores = pd.DataFrame(
        {"speaker_name": s_sn, "reference": s_ref, "manual": s_manual, "auto": s_auto}
    )
    df_scores.to_csv("results_scores.csv", index=False)

    return 0


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="generate_peqs.py version {}".format(VERSION),
        options_first=True,
    )

    force = args["--force"]
    verbose = args["--verbose"]
    ptype = None
    smoke_test = args["--smoke-test"]

    level = args2level(args)
    logger = get_custom_logger(True)
    logger.setLevel(level)

    # read optimisation parameter
    current_optim_config = {
        # name of the loss function
        "loss": "flat_loss",
        # if you have multiple loss functions, define the weigth for each
        "loss_weigths": [1.0, 1.0],
        # do you optimise only peaks or both peaks and valleys?
        "plus_and_minus": True,
        # do you optimise for all kind of biquad or do you want only Peaks?
        "full_biquad_optim": False,
        # lookup around a value is [value*elastic, value/elastic]
        "elastic": 0.8,
        # cut frequency
        "fs": 48000,
        # optimise the curve above the Schroeder frequency (here default is
        # 300hz)
        "freq_reg_min": 300,
        # do not try to optimise above:
        "freq_reg_max": 16000,
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
        # 'curve_names': ['Listening Window', 'Sound Power'],
        "curve_names": ["Listening Window", "Early Reflections"],
        # 'curve_names': ['Listening Window', 'On Axis', 'Early Reflections'],
        # 'curve_names': ['On Axis', 'Early Reflections'],
        # 'curve_names': ['Early Reflections', 'Sound Power'],
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
        current_optim_config["MAX_NUMBER_PEQ"] = 20
        current_optim_config["MAX_STEPS_FREQ"] = 5
        current_optim_config["MAX_STEPS_DBGAIN"] = 5
        current_optim_config["MAX_STEPS_Q"] = 5
        # max iterations (if algorithm is iterative)
        current_optim_config["maxiter"] = 500

    # MIN or MAX_Q or MIN or MAX_DBGAIN control the shape of the biquad which
    # are admissible.
    current_optim_config["MIN_DBGAIN"] = 0.2
    current_optim_config["MAX_DBGAIN"] = 12
    current_optim_config["MIN_Q"] = 0.1
    current_optim_config["MAX_Q"] = 12

    # do we override optim default?
    if args["--max-peq"] is not None:
        max_number_peq = int(args["--max-peq"])
        current_optim_config["MAX_NUMBER_PEQ"] = max_number_peq
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
    if args["--max-iter"] is not None:
        max_iter = int(args["--max-iter"])
        current_optim_config["maxiter"] = max_iter
    if args["--min-freq"] is not None:
        min_freq = int(args["--min-freq"])
        current_optim_config["freq_req_min"] = min_freq
    if args["--max-freq"] is not None:
        max_freq = int(args["--max-freq"])
        current_optim_config["freq_req_max"] = max_freq
    if args["--use-all-biquad"] is not None:
        if args["--use-all-biquad"] is True:
            current_optim_config["full_biquad_optim"] = True
    if args["--curve-peak-only"] is not None:
        if args["--curve-peak-only"] is True:
            current_optim_config["plus_and_minus"] = False

    # name of speaker
    speaker_name = None
    if args["--speaker"] is not None:
        speaker_name = args["--speaker"]

    # load data
    print("Reading cache ...", end=" ", flush=True)
    df_all_speakers = {}
    if smoke_test is True:
        df_all_speakers = fl.load(path="./cache.smoketest_speakers.h5")
    else:
        if speaker_name is None:
            df_all_speakers = fl.load(path="./cache.parse_all_speakers.h5")
        else:
            df_speaker = fl.load(
                path="./cache.parse_all_speakers.h5", group="/{}".format(speaker_name)
            )
            df_all_speakers[speaker_name] = df_speaker
    print("Done")

    # start ray
    custom_ray_init(args)

    # select all speakers
    if speaker_name is None:
        ids = queue_speakers(df_all_speakers, current_optim_config, verbose, smoke_test)
        compute_peqs(ids)
    else:
        if speaker_name not in df_all_speakers.keys():
            logger.error("{} is not known!".format(speaker_name))
            sys.exit(1)
        if "ASR" not in df_all_speakers[speaker_name].keys():
            sys.exit(0)
        default = "asr"
        if (
            speaker_name in metadata.keys()
            and "default_measurement" in metadata[speaker_name].keys()
        ):
            default = metadata[speaker_name]["default_measurement"]
        df_speaker = df_all_speakers[speaker_name]["ASR"][default]
        df_speaker_eq = None
        key_eq = "{}_eq".format(default)
        if key_eq in df_all_speakers[speaker_name]["ASR"].keys():
            df_speaker_eq = df_all_speakers[speaker_name]["ASR"][key_eq]
        # compute
        current_id = optim_save_peq.remote(
            speaker_name,
            df_speaker,
            df_speaker_eq,
            current_optim_config,
            verbose,
            smoke_test,
        )
        while 1:
            ready_ids, remaining_ids = ray.wait([current_id], num_returns=1)
            if len(ready_ids) == 1:
                _, _, _ = ray.get(ready_ids[0])
                break
            if len(remaining_ids) == 0:
                break

    sys.exit(0)
