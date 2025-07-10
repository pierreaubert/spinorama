#!/usr/bin/env python3
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

import sys
import argparse
import pandas as pd

from datas.metadata import speakers_info as metadata
from datas.grapheq import vendor_info as grapheq_info

from generate_common import (
    get_custom_logger,
    args2level,
    cache_load,
)
from autoeq.auto_save import optim_save_peq


VERSION = "0.27"


def print_items(aggregated_results):
    """Print all results of optimisation in a csv file"""
    v_sn = []
    v_iter = []
    v_loss = []
    v_score = []
    for speaker, result in aggregated_results.items():
        if result is not None and len(result) > 2:
            v_sn.append("{}".format(speaker))
            v_iter.append(result[0])
            v_loss.append(result[1])
            v_score.append(result[2])
    df_results = pd.DataFrame(
        {"speaker_name": v_sn, "iter": v_iter, "loss": v_loss, "score": v_score}
    )
    df_results.to_csv("build/results_iter.csv", index=False)


def print_scores(aggregated_scores):
    """Print all scores in a csv file"""
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
    df_scores.to_csv("build/results_scores.csv", index=False)


def compute_eqs(df_all_speakers, optim_config, speaker_name=None, filters=None):
    """Queue all speakers for EQ computation"""
    if filters is None:
        filters = {}

    results = {}
    for current_speaker_name in df_all_speakers:
        # Skip if speaker_name is specified and doesn't match
        if speaker_name is not None and current_speaker_name != speaker_name:
            continue

        # Skip if speaker is filtered out by any filter criteria
        skip = False
        for key, value in filters.items():
            if key == "speaker_name" and current_speaker_name != value:
                skip = True
                break
        if skip:
            logger.debug("Skipping %s because of filter criteria", current_speaker_name)
            continue

        # skip
        if (
            current_speaker_name not in metadata
            or "default_measurement" not in metadata[current_speaker_name]
        ):
            logger.error("no default_measurement for %s", current_speaker_name)
            continue

        default = metadata[current_speaker_name]["default_measurement"]
        default_origin = metadata[current_speaker_name]["measurements"][default]["origin"]

        if default_origin not in df_all_speakers[current_speaker_name]:
            logger.error(
                "default origin %s not in %s (known origins are: %s)",
                default_origin,
                current_speaker_name,
                ", ".join(df_all_speakers[current_speaker_name]),
            )
            continue
        else:
            logger.debug(
                "default origin %s for %s is %s",
                default_origin,
                current_speaker_name,
                df_all_speakers[current_speaker_name][default_origin],
            )

        if default not in df_all_speakers[current_speaker_name][default_origin]:
            logger.error(
                "default %s not in default origin %s for %s",
                default,
                default_origin,
                current_speaker_name,
            )
            continue
        else:
            logger.debug(
                "default %s for %s is %s",
                default,
                current_speaker_name,
                df_all_speakers[current_speaker_name][default_origin][default],
            )

        df_speaker = df_all_speakers[current_speaker_name][default_origin][default]

        if not (
            ("SPL Horizontal_unmelted" in df_speaker and "SPL Vertical_unmelted" in df_speaker)
            or ("CEA2034" in df_speaker and "Estimated In-Room Response" in df_speaker)
        ):
            logger.info(
                "not enough data for %s known measurements are (%s)",
                current_speaker_name,
                ", ".join(df_speaker),
            )
            continue
        else:
            logger.debug("processing %s", current_speaker_name)

        # Process EQ computation directly
        results[current_speaker_name] = optim_save_peq(
            current_speaker_name,
            default_origin,
            df_speaker,
            optim_config,
        )

    logger.info("Processed %d speakers for EQ computations", len(results))
    return results


def compute_stats(results):
    """Process EQ results and generates some statistic"""
    aggregated_results = {}
    aggregated_scores = {}
    processed = 0
    total = len(results)

    for current_speaker_name, result in results.items():
        if result is None:
            continue

        status, (speaker_name, results_iter, scores) = result
        if status and results_iter is not None:
            aggregated_results[speaker_name] = results_iter
        if status and scores is not None:
            aggregated_scores[current_speaker_name] = scores

        processed += 1
        if processed % 10 == 0 or processed == total:
            logger.info("Processed %d/%d speakers", processed, total)

    print_items(aggregated_results)
    print_scores(aggregated_scores)

    return 0


def get_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--curve-peak-only",
        action="store_true",
        help="Optimise both for peaks and valleys on a curve",
    )
    parser.add_argument(
        "--curves",
        type=str,
        help="Curve name: must be one of 'ON', 'LW', 'PIR', 'ER' or 'SP' or a combination separated by a comma. Ex: 'PIR,LW' is valid",
    )

    parser.add_argument(
        "--fitness",
        type=str,
        help="Fit function: must be one of 'Flat', 'Score', 'LeastSquare', 'FlatPir', 'Combine'.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force generation of eq even if already computed",
    )
    parser.add_argument(
        "--generate-images-only",
        action="store_true",
        help="Do not compute EQs but use the current ones to generate the various pictures",
    )
    parser.add_argument(
        "--graphic-eq-list",
        action="store_true",
        help="List the known graphic eq and exit",
    )
    parser.add_argument(
        "--graphic-eq",
        type=str,
        help="Result is tailored for graphic_eq 'name'.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        help="Default is WARNING, options are DEBUG or INFO or ERROR.",
    )
    parser.add_argument(
        "--max-Q",
        type=float,
        help="Maximum value for Q",
    )
    parser.add_argument(
        "--max-dB",
        type=float,
        help="Maximum value for dBGain",
    )
    parser.add_argument(
        "--max-freq",
        type=int,
        help="Optimisation will happen below max freq",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        help="Maximum number of iterations",
    )
    parser.add_argument(
        "--max-peq",
        type=int,
        help="Maximum allowed number of Biquad",
    )
    parser.add_argument(
        "--mformat",
        type=str,
        help="Restrict to a specific format (klippel, spl_hv_txt, gll_hv_txt, webplotdigitizer, ...)",
    )
    parser.add_argument(
        "--min-Q",
        type=float,
        help="Minimum value for Q",
    )
    parser.add_argument(
        "--min-dB",
        type=float,
        help="Minimum value for dBGain",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        help="Optimisation will happen above min freq",
    )
    parser.add_argument(
        "--mversion",
        type=str,
        help="Restrict to a specific mversion (for a given origin you can have multiple measurements)",
    )
    parser.add_argument(
        "--optimisation",
        type=str,
        help="Choose an algorithm: options are greedy or global. Greedy is fast, Global is much slower but could find better solutions.",
    )
    parser.add_argument(
        "--origin",
        type=str,
        help="Restrict to a specific origin",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="If specified all the pictures and eq txt files will be generated there",
    )

    parser.add_argument(
        "--slope-early-reflections",
        type=float,
        help="Slope of early reflections, default is -5dB",
    )
    parser.add_argument(
        "--slope-estimated-inroom",
        type=float,
        help="Slope of estimated in-room response, default is -8dB",
    )
    parser.add_argument(
        "--slope-listening-window",
        type=float,
        help="Slope of listening window, default is -0.5dB",
    )
    parser.add_argument(
        "--slope-on-axis",
        type=float,
        dest="slope_on_axis",
        help="Slope of the ideal target for On Axis, default is 0, as in flat anechoic",
    )

    # Aliases for named slope flags (all take a float value)
    parser.add_argument(
        "--slope-on",
        dest="slope_on_axis",
        type=float,
        help="Alias for --slope-on-axis. Slope of the ideal target for On Axis.",
    )
    parser.add_argument(
        "--slope-lw",
        dest="slope_listening_window",
        type=float,
        help="Alias for --slope-listening-window. Slope of listening window.",
    )
    parser.add_argument(
        "--slope-er",
        dest="slope_early_reflections",
        type=float,
        help="Alias for --slope-early-reflections. Slope of early reflections.",
    )
    parser.add_argument(
        "--slope-pir",
        dest="slope_estimated_inroom",
        type=float,
        help="Alias for --slope-estimated-inroom. Slope of estimated in-room response.",
    )
    parser.add_argument(
        "--slope-sp",
        dest="slope_sound_power",
        type=float,
        help="Alias for --slope-sound-power. Slope of sound power.",
    )

    parser.add_argument(
        "--slope-sound-power",
        type=float,
        dest="slope_sound_power",
        help="Slope of sound power, default is -8dB",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Test the optimiser with a small amount of variables",
    )
    parser.add_argument(
        "--smooth-measurements",
        type=int,
        help="If present the measurements will be smoothed before optimisation, window_size is the size of the window use for smoothing",
    )
    parser.add_argument(
        "--smooth-order",
        type=int,
        help="Order of the interpolation, 3 by default for Savitzky-Golay filter.",
    )
    parser.add_argument(
        "--speaker",
        type=str,
        help="Restrict to a specific speaker, if not specified it will optimise all speakers",
    )
    parser.add_argument(
        "--target-max-freq",
        type=int,
        help="targets will not be important after max freq",
    )
    parser.add_argument(
        "--target-min-freq",
        type=int,
        help="targets will be flat up to min freq",
    )
    parser.add_argument(
        "--use-all-biquad",
        action="store_true",
        help="PEQ can be any kind of biquad (by default it uses only PK, PeaK)",
    )
    parser.add_argument(
        "--use-only-pk",
        action="store_true",
        help="force PEQ to be only PK / Peak",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print some informations",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Script version number",
    )
    return parser


def main():
    parameter_error = False

    # read optimisation parameter
    current_optim_config = {
        # name of the loss function
        # "loss": "flat_loss",
        # "loss": "score_loss",
        # "loss": "combine_loss",
        # "loss": "leastsquare_loss",
        # "loss": "flat_pir",
        "loss": None,
        # if you have multiple loss functions, define the weigth for each
        "loss_weigths": [100.0, 1.0],
        # do you optimise only peaks or both peaks and valleys?
        "plus_and_minus": True,
        # do you optimise for all kind of biquad or do you want only Peaks?
        "use_all_biquad": None,
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
        "smooth_measurements": None,
        # size of the window to smooth (currently in number of data points but could be in octave)
        "smooth_window_size": None,
        # order of interpolation (you can try 1 (linear), 2 (quadratic) etc)
        "smooth_order": None,
        # graph eq?
        "use_grapheq": False,
        "grapheq_name": None,
        # use -3dB point as a starting point for target
        "use_3dB_target": True,
        # optimisation algorithm (greedy or global)
        "optimisation": "greedy",
    }

    # define other parameters for the optimisation algorithms
    # MAX_STEPS_XXX are usefull for grid search when the algorithm is looking
    # for random values (or trying all) across a range
    if args.smoke_test:
        current_optim_config["MAX_NUMBER_PEQ"] = 5
        current_optim_config["MAX_STEPS_FREQ"] = 3
        current_optim_config["MAX_STEPS_DBGAIN"] = 3
        current_optim_config["MAX_STEPS_Q"] = 3
        # max iterations (if algorithm is iterative)
        current_optim_config["MAX_ITER"] = 20
    else:
        current_optim_config["MAX_NUMBER_PEQ"] = 7
        current_optim_config["MAX_STEPS_FREQ"] = 6
        current_optim_config["MAX_STEPS_DBGAIN"] = 6
        current_optim_config["MAX_STEPS_Q"] = 6
        # max iterations (if algorithm is iterative)
        current_optim_config["MAX_ITER"] = 150

    # MIN or MAX_Q or MIN or MAX_DBGAIN control the shape of the biquad which
    # are admissible.
    current_optim_config["MIN_DBGAIN"] = 0.75
    current_optim_config["MAX_DBGAIN"] = 3
    current_optim_config["MIN_Q"] = 0.25
    current_optim_config["MAX_Q"] = 3

    # do we override optim default?
    if args.max_peq is not None:
        max_number_peq = int(args.max_peq)
        current_optim_config["MAX_NUMBER_PEQ"] = max_number_peq
        if max_number_peq < 1:
            print("ERROR: max_number_peq is {} which is below 1".format(max_number_peq))
            parameter_error = True
    if args.max_iter is not None:
        max_iter = int(args.max_iter)
        current_optim_config["MAX_ITER"] = max_iter
        if max_iter < 1:
            print("ERROR: max_iter is {} which is below 1".format(max_iter))
            parameter_error = True
    if args.min_freq is not None:
        min_freq = int(args.min_freq)
        current_optim_config["freq_reg_min"] = min_freq
        if min_freq <= 20:
            print("ERROR: min_freq is {} which is below 20Hz".format(min_freq))
            parameter_error = True
    if args.max_freq is not None:
        max_freq = int(args.max_freq)
        current_optim_config["freq_reg_max"] = max_freq
        if max_freq >= 20000:
            print("ERROR: max_freq is {} which is above 20kHz".format(max_freq))
            parameter_error = True

    if args.min_Q is not None:
        min_q = float(args.min_Q)
        current_optim_config["MIN_Q"] = min_q
    if args.max_Q is not None:
        max_q = float(args.max_Q)
        current_optim_config["MAX_Q"] = max_q
    if args.min_dB is not None:
        min_db = float(args.min_dB)
        current_optim_config["MIN_DBGAIN"] = min_db
    if args.max_dB is not None:
        max_db = float(args.max_dB)
        current_optim_config["MAX_DBGAIN"] = max_db

    if args.use_all_biquad:
        current_optim_config["use_all_biquad"] = True
    if args.use_only_pk:
        current_optim_config["use_all_biquad"] = False
    if args.curve_peak_only:
        current_optim_config["plus_and_minus"] = False

    if args.target_min_freq is not None:
        target_min_freq = int(args.target_min_freq)
        current_optim_config["target_min_freq"] = target_min_freq
    if args.target_max_freq is not None:
        target_max_freq = int(args.target_max_freq)
        current_optim_config["target_max_freq"] = target_max_freq

    slope_params = (
        # Numeric flags (value derived from name if arg is True)
        ("--0.5", "slope_0_5"),
        ("--0.6", "slope_0_6"),
        ("--0.9", "slope_0_9"),
        ("--1.2", "slope_1_2"),
        # Primary named flags (value is float from arg)
        ("--slope-on-axis", "slope_on_axis"),
        ("--slope-listening-window", "slope_listening_window"),
        ("--slope-early-reflections", "slope_early_reflections"),
        ("--slope-estimated-inroom", "slope_estimated_inroom"),
        ("--slope-sound-power", "slope_sound_power"),
        # Aliases for named flags (value is float from arg, dest matches primary)
        # Included here if we want to iterate them by their alias name, though argparse handles the dest mapping.
        # The processing loop's is_numeric_style_flag correctly distinguishes these from true numeric flags.
        ("--slope-on", "slope_on_axis"),
        ("--slope-lw", "slope_listening_window"),
        ("--slope-er", "slope_early_reflections"),
        ("--slope-pir", "slope_estimated_inroom"),
        ("--slope-sp", "slope_sound_power"),
    )

    for slope_name, slope_key in slope_params:
        arg_value = getattr(args, slope_key, None)

        if arg_value is not None:
            actual_slope_value = None
            is_numeric_style_flag = (
                slope_name.startswith("--") and len(slope_name) > 2 and slope_name[2].isdigit()
            )

            if arg_value is True:
                if is_numeric_style_flag:
                    try:
                        actual_slope_value = -float(slope_name[2:])  # e.g., "--0.5" -> -0.5
                    except ValueError:
                        logger.exception("Cannot parse slope from numeric flag name %s", slope_name)
                        sys.exit(1)
                else:
                    logger.warning(
                        "Flag %s (dest: %s) resolved to True but is not a numeric-style flag. Check argparse definition. Skipping this slope argument.",
                        slope_name,
                        slope_key,
                    )
                    continue
            elif isinstance(arg_value, (float, int)):
                actual_slope_value = float(arg_value)
            else:
                logger.error(
                    "Unexpected type for argument %s: %s. Value: %s. Check argparse definition.",
                    slope_key,
                    type(arg_value),
                    arg_value,
                )
                sys.exit(1)

            if actual_slope_value is not None:
                current_optim_config[slope_key] = actual_slope_value
                if "slope" not in current_optim_config:
                    current_optim_config["slope"] = actual_slope_value

    if "slope" not in current_optim_config:
        current_optim_config["slope"] = -0.5
        default_slope_key = f"slope_{str(abs(-0.5)).replace('.', '_')}"
        if default_slope_key not in current_optim_config:
            current_optim_config[default_slope_key] = -0.5

    if args.smooth_measurements is not None:
        window_size = int(args.smooth_measurements)
        current_optim_config["smooth_measurements"] = True
        current_optim_config["smooth_window_size"] = window_size
        current_optim_config["smooth_window_order"] = 3
        if window_size < 2:
            print("ERROR: window size is {} which is below 2".format(window_size))
            parameter_error = True

    if args.smooth_order is not None:
        order = int(args.smooth_order)
        current_optim_config["smooth_order"] = order
        if order < 1 or order > 5:
            print("ERROR: Polynomial order {} is not between  is 1 and 5".format(order))
            parameter_error = True

    # which curve (measurement) to target?
    if args.curves is not None:
        param_curve_names = args.curves.replace(" ", "").split(",")
        param_curve_name_valid = {
            "ON": "On Axis",
            "LW": "Listening Window",
            "ER": "Early Reflections",
            "SP": "Sound Power",
            "PIR": "Estimated In-Room Response",
        }
        current_optim_config["curve_names"] = []
        for current_curve_name in param_curve_names:
            if current_curve_name not in param_curve_name_valid:
                print(
                    "ERROR: {} is not known, acceptable values are {}. You can add multiple curves by separating them with a comma. Ex: --curve-names=LW,PIR".format(
                        current_curve_name,
                        list(param_curve_name_valid.keys()),
                    )
                )
                parameter_error = True
            else:
                current_optim_config["curve_names"].append(
                    param_curve_name_valid[current_curve_name]
                )

    # do we build EQ for a HW graphic one?
    if args.graphic_eq is not None:
        grapheq_name = args.graphic_eq
        if grapheq_name not in grapheq_info:
            print(
                "ERROR: EQ name {} is not known. Please select on in {}".format(
                    grapheq_name, grapheq_info.keys()
                )
            )
            sys.exit(1)
        current_optim_config["use_grapheq"] = True
        current_optim_config["grapheq_name"] = grapheq_name

    # which optimisation algo?
    if args.optimisation is not None:
        optimisation_name = args.optimisation
        if optimisation_name == "greedy":
            current_optim_config["optimisation"] = "greedy"
        elif optimisation_name == "global":
            current_optim_config["optimisation"] = "global"
            # default is too low for global optim
            if args.max_iter is None:
                current_optim_config["MAX_ITER"] = 2500
    elif not args.generate_images_only:
        print("ERROR: Optimisation algorithm needs to be either 'greedy' or 'global'.")
        sys.exit(1)

    # which fitness function?
    param_fitness_name_valid = {
        "Flat": "flat_loss",
        "Score": "score_loss",
        "Combine": "combine_loss",
        "LeastSquare": "leastsquare_loss",
        "FlatPir": "flat_pir",
    }
    if args.fitness is not None:
        current_fitness_name = args.fitness
        if current_fitness_name not in param_fitness_name_valid:
            print(
                "ERROR: {} is not known, acceptable values are {}".format(
                    current_fitness_name, list(param_fitness_name_valid.keys())
                )
            )
            parameter_error = True
        else:
            current_optim_config["loss"] = param_fitness_name_valid[current_fitness_name]
    elif not args.generate_images_only:
        print(
            "ERROR: fitness function is required: options are {}".format(
                list(param_fitness_name_valid.keys())
            )
        )
        sys.exit(1)

    # name of speaker
    speaker_name = None
    if args.speaker is not None:
        speaker_name = args.speaker.replace('"', "")

    origin = None
    if args.origin is not None:
        origin = args.origin

    mversion = None
    if args.mversion is not None:
        mversion = args.mversion

    mformat = None
    if args.mformat is not None:
        mformat = args.mformat

    # error in parameters
    if parameter_error:
        print("ERROR: please check for errors in parameters above!")
        sys.exit(1)

    logger.debug("parameters: speaker_name=%s", speaker_name)
    logger.debug("parameters:       origin=%s", origin)
    logger.debug("parameters:     mversion=%s", mversion)
    logger.debug("parameters:      mformat=%s", mformat)

    # load data
    print("Reading cache ...", end=" ", flush=True)
    df_all_speakers = {}
    try:
        do_filters = {
            "speaker_name": speaker_name,
            "format": mformat,
            "origin": origin,
            "version": mversion,
        }
        df_all_speakers = cache_load(filters=do_filters, smoke_test=args.smoke_test, level=level)
        # print(df_all_speakers.keys())
        # print(df_all_speakers[speaker_name].keys())
        # print(df_all_speakers[speaker_name]["unknown"].keys())
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

    # add global parameters into the config
    current_optim_config["verbose"] = args.verbose
    current_optim_config["smoke_test"] = args.smoke_test
    current_optim_config["force"] = args.force
    current_optim_config["version"] = VERSION
    current_optim_config["level"] = level
    current_optim_config["generate_images_only"] = args.generate_images_only
    current_optim_config["output_dir"] = args.output_dir

    results = compute_eqs(df_all_speakers, current_optim_config, speaker_name)
    compute_stats(results)

    sys.exit(0)


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()

    level = args2level(args)
    logger = get_custom_logger(level=level, duplicate=True)

    if args.graphic_eq_list:
        print("INFO: The list of known graphical EQ is: {}".format(list(grapheq_info.keys())))
        sys.exit(0)

    main()
