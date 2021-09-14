#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flammkuchen as fl
from ray import tune

import sys, os, os.path

sys.path.append(os.path.expanduser("./src"))
from spinorama.filter_scores import scores_loss, lw_loss
from spinorama.filter_iir import Biquad


def config2peq(config):
    current_peq = [
        (
            1.0,
            Biquad(
                Biquad.PEAK, config["1_freq"], 48000, config["1_Q"], config["1_dbGain"]
            ),
        ),
        (
            1.0,
            Biquad(
                Biquad.PEAK, config["2_freq"], 48000, config["2_Q"], config["2_dbGain"]
            ),
        ),
        (
            1.0,
            Biquad(
                Biquad.PEAK, config["3_freq"], 48000, config["3_Q"], config["3_dbGain"]
            ),
        ),
        (
            1.0,
            Biquad(
                Biquad.PEAK, config["4_freq"], 48000, config["4_Q"], config["4_dbGain"]
            ),
        ),
        (
            1.0,
            Biquad(
                Biquad.PEAK, config["5_freq"], 48000, config["5_Q"], config["5_dbGain"]
            ),
        ),
        (
            1.0,
            Biquad(
                Biquad.PEAK, config["6_freq"], 48000, config["6_Q"], config["6_dbGain"]
            ),
        ),
        #        (1.0, Biquad(Biquad.PEAK, config['7_freq'], 48000, config['7_Q'], config['7_dbGain'])),
        #        (1.0, Biquad(Biquad.PEAK, config['8_freq'], 48000, config['8_Q'], config['8_dbGain'])),
        #        (1.0, Biquad(Biquad.PEAK, config['9_freq'], 48000, config['9_Q'], config['9_dbGain'])),
        #        (1.0, Biquad(Biquad.PEAK, config['10_freq'], 48000, config['10_Q'], config['10_dbGain'])),
    ]
    return current_peq


def autoEQ_lw(config, checkpoint_dir=None):
    current_peq = config2peq(config)
    score = lw_loss(df_speaker, current_peq)
    tune.report(mean_loss=score)


def autoEQ_score(config, checkpoint_dir=None):
    current_peq = config2peq(config)
    score = scores_loss(df_speaker, current_peq)
    tune.report(mean_loss=score)


if __name__ == "__main__":

    df = fl.load("./cache.parse_all_speakers.h5")
    df_speaker = df["Adam S2V"]["ASR"]["asr"]
    df_speaker.keys()
    original_mean = df_speaker["CEA2034_original_mean"]

    print("Optim start")
    analysis = tune.run(
        autoEQ_lw,
        num_samples=10000,
        config={
            "1_freq": tune.uniform(200, 400),
            "2_freq": tune.uniform(400, 1000),
            "3_freq": tune.uniform(1000, 2000),
            "4_freq": tune.uniform(2000, 4000),
            "5_freq": tune.uniform(4000, 8000),
            "6_freq": tune.uniform(8000, 16000),
            #           "7_freq": tune.grid_search([8000, 10000, 50]),
            #           "8_freq": tune.grid_search([1000, 12000, 100]),
            #           "9_freq": tune.grid_search([12000, 15000, 100]),
            #           "10_freq": tune.grid_search([15000, 20000, 100]),
            "1_Q": tune.uniform(1, 40),
            "2_Q": tune.uniform(1, 40),
            "3_Q": tune.uniform(1, 40),
            "4_Q": tune.uniform(1, 40),
            "5_Q": tune.uniform(1, 40),
            "6_Q": tune.uniform(1, 40),
            #           "7_Q": tune.grid_search([0.1, 10]),
            #           "8_Q": tune.grid_search([0.1, 10]),
            #           "9_Q": tune.grid_search([0.1, 10]),
            #           "10_Q": tune.grid_search([0.1, 10]),
            "1_dbGain": tune.uniform(-5, 5),
            "2_dbGain": tune.uniform(-5, 5),
            "3_dbGain": tune.uniform(-5, 5),
            "4_dbGain": tune.uniform(-5, 5),
            "5_dbGain": tune.uniform(-5, 5),
            "6_dbGain": tune.uniform(-5, 5),
            #           "7_dbGain": tune.grid_search([0.1, 10]),
            #           "8_dbGain": tune.grid_search([0.1, 10]),
            #           "9_dbGain": tune.grid_search([0.1, 10]),
            #           "10_dbGain": tune.grid_search([0.1, 10]),
            # "n_peq": tune.choice([2])
        },
        resources_per_trial={"cpu": 0.5},
    )

    print("Best config: ", analysis.get_best_config(metric="mean_loss", mode="max"))

    # Get a dataframe for analyzing trial results.
    print(analysis.dataframe())
