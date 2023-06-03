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

import numpy as np
import pandas as pd
import scipy.optimize as opt

from spinorama import logger
from spinorama.ltype import Vector
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import Peq, peq_spl
from spinorama.auto_misc import get3db
from spinorama.auto_loss import score_loss

# from spinorama.auto_target import optim_compute_auto_target
from spinorama.auto_preflight import optim_preflight


def optim_global(
    df_speaker: dict[str, pd.DataFrame],
    freq: Vector,
    auto_target: list[Vector],
    auto_target_interp: list[Vector],
    optim_config: dict,
) -> tuple[bool, tuple[tuple[int, float, float], Peq]]:
    """Main optimiser: follow a greedy strategy"""

    lw = df_speaker["CEA2034_unmelted"]["On Axis"].to_numpy()
    freq_low = bisect.bisect(freq, 100)
    freq_high = bisect.bisect(freq, 16000)

    # used for controlling optimisation of the score
    target = lw[freq_low:freq_high] - np.linspace(0, 0.5, len(lw[freq_low:freq_high]))

    # basic checks
    if not optim_preflight(freq, auto_target, auto_target_interp, df_speaker):
        logger.error("Preflight check failed!")
        return False, ((0, 0, 0), [])

    freq_min = optim_config["target_min_freq"]
    if freq_min is None:
        status, freq_min = get3db(df_speaker, 3.0)
        if status is None:
            freq_min = 80
    freq_max = optim_config["target_max_freq"]
    log_freq = np.logspace(np.log10(20), np.log10(20000), 200 + 1)
    max_db = optim_config["MAX_DBGAIN"]
    min_q = optim_config["MIN_Q"]
    max_q = optim_config["MAX_Q"]
    max_peq = optim_config["MAX_NUMBER_PEQ"]
    max_iter = optim_config["MAX_ITER"]

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
        flatness = np.linalg.norm(np.add(target, peq_freq))
        return score + float(flatness) / 20.0

    def opt_bounds(n: int) -> list[list[int | float]]:
        bounds0 = [
            [0, 6],
            [0, 200],  # algo does not support log scaling so I do it manually
            [min_q, 1.3],  # need to be computed from max_db
            [-max_db, max_db],
        ]
        bounds1 = [
            [3, 3],
            [0, 200],
            [min_q, max_q],
            [-max_db, max_db],
        ]
        return bounds0 + bounds1 * (n - 1)

    def opt_integrality(n: int) -> list[bool]:
        return [True, True, False, False] * n

    def opt_constraints(n: int):
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
        return opt.LinearConstraint(mat, -np.inf, vec)

    def opt_display(xk, convergence):
        # comment if you want to print verbose traces
        l = len(xk) // 4
        print(f"IIR    Hz.  Q.   dB [{convergence}]")
        for i in range(l):
            t = int(xk[i * 4 + 0])
            f = int(log_freq[int(xk[i * 4 + 1])])
            q = xk[i * 4 + 2]
            db = xk[i * 4 + 3]
            print(f"{t:3d} {f:5d} {q:1.1f} {db:+1.2f}")

    res = opt.differential_evolution(
        func=opt_peq_score,
        bounds=opt_bounds(max_peq),
        maxiter=max_iter,
        polish=False,
        integrality=opt_integrality(max_peq),
        callback=opt_display,
        constraints=opt_constraints(max_peq),
        disp=True,
        tol=0.01,
    )

    auto_peq = x2peq(res.x)
    auto_score = score_loss(df_speaker, auto_peq)

    return True, ((0, res.fun, auto_score), auto_peq)
