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

import pandas as pd

from ray import tune
from ray.tune.schedulers import (
    PopulationBasedTraining,
)


from spinorama.ltype import Peq, FloatVector1D
from spinorama.filter_iir import Biquad
from spinorama.auto_loss import score_loss


def optim_refine(
    speaker_name: str,
    df_speaker: dict[str, pd.DataFrame],
    freq: FloatVector1D,
    auto_target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    optim_config: dict,
    greedy_results,
    greedy_peq,
) -> tuple[list[tuple[int, float, float]], Peq]:
    # loss from previous optim algo
    init_loss = greedy_results[-1][2]

    low_cost_partial_config = {}
    config = {}
    for i, (_, i_peq) in enumerate(greedy_peq):
        f_i = int(i_peq.freq * 0.3)
        config[f"freq_{i}"] = tune.quniform(-f_i, f_i, 1)
        q_i = int(i_peq.Q * 6) / 10
        config[f"Q_{i}"] = tune.quniform(-q_i, q_i, 0.01)
        db_i = int(i_peq.dbGain * 6) / 10
        config[f"dbGain_{i}"] = tune.quniform(-db_i, db_i, 0.01)

    for i, _ in enumerate(greedy_peq):
        low_cost_partial_config[f"freq_{i}"] = 0.0
        low_cost_partial_config[f"Q_{i}"] = 0.0
        low_cost_partial_config[f"dbGain_{i}"] = 0.0

    def init_delta(current_config):
        return [
            (
                c,
                Biquad(
                    # p.typ,
                    p.typ,
                    # p.freq,
                    min(
                        optim_config["freq_reg_max"],
                        max(
                            optim_config["freq_reg_min"],
                            p.freq + current_config[f"freq_{i}"],
                        ),
                    ),
                    # p.srate,
                    p.srate,
                    # p.Q,
                    min(
                        optim_config["MAX_Q"],
                        max(
                            optim_config["MIN_Q"],
                            p.Q + current_config[f"Q_{i}"],
                        ),
                    ),
                    # p.dbGain,
                    min(
                        optim_config["MAX_DBGAIN"],
                        max(
                            optim_config["MIN_DBGAIN"],
                            p.dbGain + current_config[f"dbGain_{i}"],
                        ),
                    ),
                ),
            )
            for i, (c, p) in enumerate(greedy_peq)
        ]

    def evaluate_config(current_config, checkpoint_dir=None):
        eval_peq = init_delta(current_config)
        score = score_loss(df_speaker, eval_peq)
        tune.report(score=score)

    # possible schedulers
    pbt = PopulationBasedTraining(
        time_attr="training_iteration",
        perturbation_interval=2,
        metric="mean_accuracy",
        mode="min",
        hyperparam_mutations={
            # distribution for resampling
            "lr": tune.uniform(0.0001, 1),
            # allow perturbations within this set of categorical values
            "momentum": [0.8, 0.9, 0.99],
        },
    )

    analysis = tune.run(
        evaluate_config,
        config=config,
        metric="score",
        mode="min",
        local_dir="logs/",
        # search_alg=algo, # bos working well
        # scheduler=asha,
        # stop=stopper,
        fail_fast=True,
        scheduler=pbt,
        verbose=1,
    )

    print(analysis.best_trial.last_result)
    print(analysis.best_config)

    final_loss = -analysis.best_trial.last_result["score"]
    print(final_loss, init_loss)

    if final_loss > init_loss:
        final_results = greedy_results
        final_results.append([greedy_results[-1][0] + 1, final_loss, final_loss])
        final_peq = init_delta(analysis.best_config)
        return final_results, final_peq

    return greedy_results, greedy_peq
