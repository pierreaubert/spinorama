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

import bisect
import math

import numpy as np
import pandas as pd
import scipy.optimize as opt

from spinorama import logger
from spinorama.constant_paths import MIDRANGE_MAX_FREQ
from spinorama.ltype import Vector
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import Peq, peq_spl
from spinorama.auto_misc import get3db
from spinorama.auto_loss import score_loss

# from spinorama.auto_target import optim_compute_auto_target
from spinorama.auto_preflight import optim_preflight

FREQ_NB_POINTS = 200


def optim_global(
    df_speaker: dict[str, pd.DataFrame],
    freq: Vector,
    auto_target: list[Vector],
    auto_target_interp: list[Vector],
    optim_config: dict,
) -> tuple[bool, tuple[tuple[int, float, float], Peq]]:
    """Main optimiser: follow a greedy strategy"""

    # get min/max
    freq_min = optim_config["target_min_freq"]
    if freq_min is None:
        status, freq_min = get3db(df_speaker, 3.0)
        if not status:
            freq_min = 80
    freq_max = optim_config.get("target_max_freq", 16000)

    # Freq (hz)
    # ---|----------|-------------------------------------------|-----|
    #   20       -3dB                                       16000 20000
    # ---|----------|-------------------------------------------|-----|
    #  min      first                                        last   max
    #  low      first                                        last  high

    # get range for target
    freq_first = max(freq_min, 20)
    freq_last = min(freq_max, 20000)
    freq_low = bisect.bisect(freq, freq_first)
    freq_high = bisect.bisect(freq, freq_last)
    # a bit of black magic
    freq_midrange = bisect.bisect(freq, MIDRANGE_MAX_FREQ / 2)

    # get lw/on
    lw = df_speaker["CEA2034_unmelted"]["Listening Window"].to_numpy()

    # used for controlling optimisation of the score
    target = lw[freq_low:freq_high] - np.linspace(0, 0.5, len(lw[freq_low:freq_high]))

    # basic checks
    if not optim_preflight(freq, auto_target, auto_target_interp, df_speaker):
        logger.error("Preflight check failed!")
        return False, ((0, 0, 0), [])

    if optim_config.get("full_biquad_optim") is None:
        logger.error("optim_config is not properly configured")
        optim_config["full_biquad_optim"] = True

    log_freq = np.logspace(np.log10(20), np.log10(freq_max), FREQ_NB_POINTS + 1)
    min_db = optim_config["MIN_DBGAIN"]
    max_db = optim_config["MAX_DBGAIN"]
    min_q = optim_config["MIN_Q"]
    max_q = optim_config["MAX_Q"]
    max_peq = optim_config["MAX_NUMBER_PEQ"]
    max_iter = optim_config["MAX_ITER"]

    logger.info(
        "global optim: #peq=%d dB=[%1.1f, %1.1f] Q=[%1.1f, %1.1f] #iter=%d",
        max_peq,
        min_db,
        max_db,
        min_q,
        max_q,
        max_iter,
    )

    def x2peq(x: list[float | int]) -> Peq:
        l = len(x) // 4
        peq = []
        for i in range(l):
            ifreq = int(x[i * 4 + 1])
            peq_freq = log_freq[ifreq]
            peq_freq = max(freq_min, peq_freq)
            peq_freq = min(freq_max, peq_freq)
            peq.append(
                (1.0, Biquad(int(x[i * 4]), int(peq_freq), 48000, x[i * 4 + 2], x[i * 4 + 3]))
            )
        return peq

    def x2spl(x: list[float | int]) -> Vector:
        return peq_spl(freq, x2peq(x))

    def opt_peq_score(x) -> float:
        peq = x2peq(x)
        peq_freq = np.array(x2spl(x))[freq_low:freq_high]
        score = score_loss(df_speaker, peq)
        flat = np.add(target, peq_freq)
        # flatness_l2 = np.linalg.norm(flat, ord=2)
        # flatness_l1 = np.linalg.norm(flat, ord=1)
        flatness_bass_mid = np.linalg.norm(flat[0 : freq_midrange - freq_low], ord=2)
        flatness_mid_high = np.linalg.norm(flat[freq_midrange - freq_low :], ord=2)
        # this is black magic, why 10, 20, 40?
        # if you increase 20 you give more flexibility to the score (and less flat LW/ON)
        # without the constraint optimising the score get crazy results
        return score + float(flatness_bass_mid) / 5 + float(flatness_mid_high) / 50

    def opt_peq_flat(x) -> float:
        peq_freq = np.array(x2spl(x))[freq_low:freq_high]
        flat = np.add(target, peq_freq)
        flatness_l2 = np.linalg.norm(flat, ord=2)
        flatness_l1 = np.linalg.norm(flat, ord=1)
        return float(flatness_l2 + flatness_l1)

    def opt_peq(x) -> float:
        return opt_peq_score(x) if optim_config["loss"] == "score_loss" else opt_peq_flat(x)

    def opt_bounds_all(n: int) -> list[list[int | float]]:
        bounds0 = [
            [0, 6],
            [0, FREQ_NB_POINTS],  # algo does not support log scaling so I do it manually
            [min_q, 1.3],  # need to be computed from max_db
            [-max_db, max_db],
        ]
        bounds1 = [
            [3, 3],
            [0, FREQ_NB_POINTS],
            [min_q, max_q],
            [-max_db, max_db],
        ]
        return bounds0 + bounds1 * (n - 2) + bounds0

    def opt_bounds_pk(n: int) -> list[list[int | float]]:
        bounds0 = [
            [3, 3],
            [0, FREQ_NB_POINTS],
            [min_q, max_q],
            [-max_db, max_db],
        ]
        return bounds0 * n

    def opt_bounds(n: int) -> list[list[int | float]]:
        return opt_bounds_all(n) if optim_config["full_biquad_optim"] else opt_bounds_pk(n)

    def opt_integrality(n: int) -> list[bool]:
        return [True, True, False, False] * n

    def opt_constraints_linear(n: int):
        # Create some space between the various PEQ; if not the optimiser will add multiple PEQ
        # at more or less the same frequency and that will generate too much of a cut on the max
        # SPL. we have 200 points from 20Hz-20kHz, 5 give us 1/4 octave
        m = n
        mat = np.asarray([[0] * (n * 4)] * m)
        vec = np.asarray([0] * m)
        for i in range(m):
            if i == 0:
                # first freq can be as low as possible
                # second needs to be > freq_min
                mat[0][5] = -1
                vec[0] = -freq_min
                continue
            j = (i - 1) * 4 + 1
            mat[i][j] = 1
            j += 4
            mat[i][j] = -1
            vec[i] = -5
        # lb / uf can be float or array
        return opt.LinearConstraint(A=mat, lb=-np.inf, ub=vec, keep_feasible=False)

    def opt_constraints_nonlinear(n: int):
        # Create some space between the various PEQ; if not the optimiser will add multiple PEQ
        # at more or less the same frequency and that will generate too much of a cut on the max
        # SPL. we have 200 points from 20Hz-20kHz, 5 give us 1/4 octave

        # freq_min_first_peq = max(freq_low, freq_min // 2)

        def x2data(x, i):
            idx = i * 4 + 1
            f = int(x[idx])
            idx += 1
            q = float(x[idx])
            idx += 1
            db = float(x[idx])
            sign = int(math.copysign(1, db))
            return f, q, db, sign

        vec = np.asarray([0] * n)

        def freq_constraints(x):
            res = np.asarray([0] * n)
            l = len(x) // 4
            for i in range(l - 1):
                f1, q1, g1, s1 = x2data(x, i)
                f2, q2, g2, s2 = x2data(x, i + 1)
                # first peq
                if i == 0:
                    # should be the index of that frequency, 1/2 octave
                    vec[0] = -10
                # if the sign is the same, then make some space between frequencies
                if s1 == s2:
                    vec[i] = -5
                # you want increasing frequencies
                res[i] = f1 - f2
            return res

        return opt.NonlinearConstraint(
            fun=freq_constraints, lb=-np.inf, ub=vec, keep_feasible=False
        )

    def opt_display(xk, convergence):
        # comment if you want to print verbose traces
        l = len(xk) // 4
        print(f"IIR    Hz.  Q.   dB [{convergence}] iir={optim_config['full_biquad_optim']}")
        for i in range(l):
            t = int(xk[i * 4 + 0])
            f = int(log_freq[int(xk[i * 4 + 1])])
            q = xk[i * 4 + 2]
            db = xk[i * 4 + 3]
            print(f"{t:3d} {f:5d} {q:1.1f} {db:+1.2f}")

    res = opt.differential_evolution(
        func=opt_peq,
        bounds=opt_bounds(max_peq),
        maxiter=max_iter,
        # workers=32,
        init="sobol",
        polish=False,
        integrality=opt_integrality(max_peq),
        callback=opt_display,
        constraints=opt_constraints_nonlinear(max_peq),
        disp=True,
        tol=0.01,
    )

    auto_peq = x2peq(res.x)
    auto_score = score_loss(df_speaker, auto_peq)

    return True, ((0, res.fun, auto_score), auto_peq)
