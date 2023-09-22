#!/usr/bin/env python3
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
"""
usage: generate_peqs.py [--help] [--version] [--log-level=<level>] \
 [--force] [--smoke-test] [-v|--verbose] [--origin=<origin>] \
 [--speaker=<speaker>] [--mversion=<mversion>] [--mformat=<mformat>]\
 [--max-peq=<count>] [--min-Q=<minQ>] [--max-Q=<maxQ>] \
 [--min-dB=<mindB>] [--max-dB=<maxdB>] \
 [--min-freq=<minFreq>] [--max-freq=<maxFreq>] \
 [--max-iter=<maxiter>] [--use-all-biquad] \
 [--use-only-pk] [--curve-peak-only] \
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
 [--dash-ip=<ip>] [--dash-port=<port>] [--ray-local] \
 [--smooth-measurements=<window_size>] \
 [--smooth-order=<order>] \
 [--curves=<curve_name>] \
 [--fitness=<function>] \
 [--optimisation=<options>] \
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
  --mformat=<mformat>      Restrict to a specifig format (klippel, spl_hv_txt, gll_hv_txt, webplotdigitizer, ...)
  --max-peq=<count>        Maximum allowed number of Biquad
  --min-Q=<minQ>           Minumum value for Q
  --max-Q=<maxQ>           Maximum value for Q
  --min-dB=<mindB>         Minumum value for dBGain
  --max-dB=<maxdB>         Maximum value for dBGain
  --min-freq=<minFreq>     Optimisation will happen above min freq
  --max-freq=<maxFreq>     Optimisation will happen below max freq
  --max-iter=<maxiter>     Maximum number of iterations
  --use-all-biquad         PEQ can be any kind of biquad (by default it uses only PK, PeaK)
  --use-only-pk            force PEQ to be only PK / Peak
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
  --smooth-measurements=<window_size> If present the measurements will be smoothed before optimisation, window_size is the size of the window use for smoothing
  --smooth-order=<order>   Order of the interpolation, 3 by default for Savitzky-Golay filter.
  --curves=<curve_name>    Curve name: must be one of "ON", "LW", "PIR", "ER" or "SP" or a combinaison separated by a ,. Ex: 'PIR,LW' is valid
  --fitness=<function>     Fit function: must be one of "Flat", "Score", "LeastSquare", "FlatPir", "Combine".
  --graphic_eq=<eq_name>   Result is tailored for graphic_eq "name".
  --graphic_eq_list        List the known graphic eq and exit
  --optimisation=<options> Choose an algorithm: options are greedy or global. Greedy is fast, Global is much slower but could find better solutions.
"""
import sys

from docopt import docopt
import pandas as pd

try:
    import ray
except ModuleNotFoundError:
    try:
        import src.miniray as ray
    except ModuleNotFoundError:
        print("Did you run env.sh?")
        sys.exit(-1)

from datas.metadata import speakers_info as metadata
from datas.grapheq import vendor_info as grapheq_info

from generate_common import get_custom_logger, args2level, custom_ray_init, cache_load
from spinorama.auto_save import optim_save_peq


VERSION = "0.25"


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
    df_results.to_csv("results_iter.csv", index=False)


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
    df_scores.to_csv("results_scores.csv", index=False)


def queue_speakers(df_all_speakers, optim_config, speaker_name):
    """Add all speakers to the queue"""
    ray_ids = {}
    for current_speaker_name in df_all_speakers:
        if speaker_name is not None and current_speaker_name != speaker_name:
            continue
        default = None
        default_origin = None
        if (
            current_speaker_name in metadata
            and "default_measurement" in metadata[current_speaker_name]
        ):
            default = metadata[current_speaker_name]["default_measurement"]
            default_origin = metadata[current_speaker_name]["measurements"][default]["origin"]
        else:
            logger.error("no default_measurement for %s", current_speaker_name)
            continue
        if default_origin not in df_all_speakers[current_speaker_name]:
            logger.error("default origin %s not in %s", default_origin, current_speaker_name)
            continue
        if default not in df_all_speakers[current_speaker_name][default_origin]:
            logger.error(
                "default %s not in default origin %s for %s",
                default,
                default_origin,
                current_speaker_name,
            )
            continue
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

        current_id = optim_save_peq.remote(
            current_speaker_name,
            default_origin,
            df_speaker,
            optim_config,
        )
        ray_ids[current_speaker_name] = current_id

    logger.info("Queing %d speakers for EQ computations", len(ray_ids))
    return ray_ids


def compute_peqs(ray_ids):
    """Process EQ when it is available from the queue"""
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
            status, (current_speaker_name, results_iter, scores) = get_results
            if status and results_iter is not None:
                aggregated_results[current_speaker_name] = results_iter
            if status and scores is not None:
                aggregated_scores[current_speaker_name] = scores
            done_ids.add(current_id)

        if len(remaining_ids) == 0:
            break

        logger.info("State: %d ready IDs %d remainings IDs ", len(ready_ids), len(remaining_ids))

    print_items(aggregated_results)
    print_scores(aggregated_scores)

    return 0


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
        "full_biquad_optim": None,
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
    if smoke_test:
        current_optim_config["MAX_NUMBER_PEQ"] = 5
        current_optim_config["MAX_STEPS_FREQ"] = 3
        current_optim_config["MAX_STEPS_DBGAIN"] = 3
        current_optim_config["MAX_STEPS_Q"] = 3
        # max iterations (if algorithm is iterative)
        current_optim_config["MAX_ITER"] = 20
    else:
        current_optim_config["MAX_NUMBER_PEQ"] = 9
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
    if args["--max-peq"] is not None:
        max_number_peq = int(args["--max-peq"])
        current_optim_config["MAX_NUMBER_PEQ"] = max_number_peq
        if max_number_peq < 1:
            print("ERROR: max_number_peq is {} which is below 1".format(max_number_peq))
            parameter_error = True
    if args["--max-iter"] is not None:
        max_iter = int(args["--max-iter"])
        current_optim_config["MAX_ITER"] = max_iter
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
        min_q = float(args["--min-Q"])
        current_optim_config["MIN_Q"] = min_q
    if args["--max-Q"] is not None:
        max_q = float(args["--max-Q"])
        current_optim_config["MAX_Q"] = max_q
    if args["--min-dB"] is not None:
        min_db = float(args["--min-dB"])
        current_optim_config["MIN_DBGAIN"] = min_db
    if args["--max-dB"] is not None:
        max_db = float(args["--max-dB"])
        current_optim_config["MAX_DBGAIN"] = max_db

    if args["--use-all-biquad"] is not None and args["--use-all-biquad"] is True:
        current_optim_config["full_biquad_optim"] = True
    if args["--use-only-pk"] is not None and args["--use-only-pk"] is True:
        current_optim_config["full_biquad_optim"] = False
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
        if current_fitness_name not in param_fitness_name_valid:
            print(
                "ERROR: {} is not known, acceptable values are {}".format(
                    current_fitness_name, list(param_fitness_name_valid.keys())
                )
            )
            parameter_error = True
        else:
            current_optim_config["loss"] = param_fitness_name_valid[current_fitness_name]

    # do we build EQ for a HW graphic one?
    if args["--graphic_eq"] is not None:
        grapheq_name = args["--graphic_eq"]
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
    if args["--optimisation"] is not None:
        optimisation_name = args["--optimisation"]
        if optimisation_name == "greedy":
            current_optim_config["optimisation"] = "greedy"
        elif optimisation_name == "global":
            current_optim_config["optimisation"] = "global"
        else:
            print("ERROR: Optimisation algorithm needs to be either 'greedy' or 'global'.")
            sys.exit(1)

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
        df_all_speakers = cache_load(filters=do_filters, smoke_test=smoke_test)
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

    # add global parameters into the config
    current_optim_config["verbose"] = verbose
    current_optim_config["smoke_test"] = smoke_test
    current_optim_config["force"] = force
    current_optim_config["version"] = VERSION
    current_optim_config["level"] = level

    ids = queue_speakers(df_all_speakers, current_optim_config, speaker_name)
    compute_peqs(ids)

    sys.exit(0)


if __name__ == "__main__":
    args = docopt(
        __doc__,
        version="generate_peqs.py version {}".format(VERSION),
        options_first=True,
    )

    level = args2level(args)
    logger = get_custom_logger(level=level, duplicate=True)

    force = args["--force"]
    verbose = args["--verbose"]
    smoke_test = args["--smoke-test"]

    if args["--graphic_eq_list"]:
        print("INFO: The list of know graphical EQ is: {}".format(list(grapheq_info.keys())))
        sys.exit(0)

    main()
