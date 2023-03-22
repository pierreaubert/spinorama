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
import scipy.optimize as opt
import pandas as pd

from datas.grapheq import vendor_info as grapheq_db

from spinorama import logger
from spinorama.ltype import Peq, Vector
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import peq_build
from spinorama.auto_loss import score_loss
from spinorama.auto_target import optim_compute_auto_target
from spinorama.auto_preflight import optim_preflight


def optim_grapheq(
    speaker_name: str,
    df_speaker: dict[str, pd.DataFrame],
    freq: Vector,
    auto_target: list[Vector],
    auto_target_interp: list[Vector],
    optim_config: dict,
    use_score,
) -> tuple[bool, tuple[tuple[int, float, float], Peq]]:
    """Main optimiser for graphical EQ"""

    logger.debug("Starting optim graphEQ for %s", speaker_name)

    if not optim_preflight(freq, auto_target, auto_target_interp, df_speaker):
        logger.error("Preflight check failed!")
        return False, ((0, 0.0, -1000.0), [])

    # get current EQ
    grapheq = grapheq_db[optim_config.get("grapheq_name", "")]

    # PK
    auto_type = 3
    # freq is given as a list but cannot move, that's the center of the PK
    auto_freq = grapheq["bands"]
    # Q is fixed too
    auto_q = grapheq["fixed_q"]
    # dB are in a range with steps
    auto_max = grapheq["gain_p"]
    auto_min = grapheq["gain_m"]
    # auto_step = grapheq.get("steps", 1)

    # db is the only unknown, start with 0
    auto_db = np.zeros(len(auto_freq))
    auto_peq = [
        (1.0, Biquad(auto_type, float(f), 48000, auto_q, float(db)))
        for f, db in zip(auto_freq, auto_db, strict=False)
    ]

    # compute initial target
    current_auto_target = optim_compute_auto_target(
        freq, auto_target, auto_target_interp, auto_peq, optim_config
    )
    pref_score = 1.0
    if use_score:
        pref_score = score_loss(df_speaker, auto_peq)

    def fit(param: Vector) -> Peq:
        guess_db = []
        for f in auto_freq:
            if f < freq[0] or f > freq[-1]:
                db = 0.0
            else:
                db = np.interp(f, freq, np.negative(current_auto_target[0])) * param
                db = round(float(db) * 4) / 4
                db = max(auto_min, db)
                db = min(auto_max, db)
            guess_db.append(db)
        return [
            (1.0, Biquad(auto_type, float(f), 48000, auto_q, float(db)))
            for f, db in zip(auto_freq, guess_db, strict=False)
        ]

    def compute_delta(param: Vector) -> float:
        current_peq = fit(param)
        peq_values = peq_build(auto_freq, current_peq)
        peq_expend = [np.interp(f, auto_freq, peq_values) for f in freq]
        delta = np.array(peq_expend) - np.negative(current_auto_target[0])
        return float(delta)

    def compute_error(param: Vector) -> float:
        delta = compute_delta(param)
        error = np.linalg.norm(delta)
        return float(error)

    def find_best_param():
        res = opt.minimize(
            fun=lambda x: compute_error(x[0]),
            x0=0.2,
            bounds=[(0.1, 1.4)],
            method="Powell",
        )
        return res.x[0]

    opt_param = find_best_param()
    auto_peq = fit(opt_param)
    opt_error = compute_error(opt_param)

    if use_score:
        pref_score = score_loss(df_speaker, auto_peq)

    return True, ((1, opt_error, -pref_score), auto_peq)
