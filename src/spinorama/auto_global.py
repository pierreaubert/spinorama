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
from spinorama.ltype import Vector, DataSpeaker, OptimResult
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import Peq, peq_spl
from spinorama.auto_misc import get3db
from spinorama.auto_loss import score_loss

FREQ_NB_POINTS = 200

# a type for variables to be optimised
Encoded = list[float | int]


class GlobalOptimizer(object):
    """Main optimiser: follow a greedy strategy"""

    def __init__(
        self,
        df_speaker: DataSpeaker,
        freq: Vector,
        optim_config: dict,
    ):
        self.df_speaker = df_speaker
        self.freq = freq
        self.optim_config = optim_config

        # get min/max
        self.freq_min = optim_config["target_min_freq"]
        if self.freq_min is None:
            status, self.freq_min = get3db(df_speaker, 3.0)
            if not status:
                self.freq_min = 80
        self.freq_max = optim_config.get("target_max_freq", 16000)

        # get range for target
        self.freq_min = max(self.freq_min, 20)
        self.freq_max = min(self.freq_max, 20000)

        # Freq (hz)
        # ---|----------|-------------------------------------------|-----|
        #   20       -3dB              |                        16000 20000
        # ---|----------|-------------------------------------------|-----|
        #             min              midrange                   max
        # ---|----------|-------------------------------------------|-----|

        self.log_freq = np.logspace(math.log10(20), math.log10(20000), FREQ_NB_POINTS + 1)
        # a bit of black magic
        self.freq_min_index = bisect.bisect(self.log_freq, self.freq_min)
        self.freq_midrange_index = bisect.bisect(self.log_freq, MIDRANGE_MAX_FREQ / 2)
        self.freq_max_index = bisect.bisect(self.log_freq, self.freq_max)

        # get lw/on
        self.lw = df_speaker["CEA2034_unmelted"]["Listening Window"].to_numpy()

        # used for controlling optimisation of the score
        self.target = self.lw[self.freq_min_index : self.freq_max_index] - np.linspace(
            0, 0.5, len(self.lw[self.freq_min_index : self.freq_max_index])
        )

        self.min_db = optim_config["MIN_DBGAIN"]
        self.max_db = optim_config["MAX_DBGAIN"]
        self.min_q = optim_config["MIN_Q"]
        self.max_q = optim_config["MAX_Q"]
        self.max_peq = optim_config["MAX_NUMBER_PEQ"]
        self.max_iter = optim_config["MAX_ITER"]

    def _x2params(self, x: Encoded, i: int) -> tuple[int, int, float, float, int]:
        # take an encoded Peq and return all values of the parameters of the filter
        # type
        idx = i * 4
        t = int(x[idx])
        # freq (encoded as an int)
        idx += 1
        f_pos = int(x[idx])
        # Q
        idx += 1
        q = float(x[idx])
        # SPL
        idx += 1
        spl = float(x[idx])
        # sign of SPL
        sign = int(math.copysign(1, spl))
        return t, f_pos, q, spl, sign

    def _x2peq(self, x: Encoded) -> Peq:
        # take a list of encoded filters and return a Peq
        l = len(x) // 4
        peq = []
        for i in range(l):
            t, f, q, spl, _ = self._x2params(x, i)
            f = self.log_freq[f]
            peq.append((1.0, Biquad(t, f, 48000, q, spl)))
        return peq

    def _x2spl(self, x: Encoded) -> Vector:
        # take a list of encoded filters and return the magnitude of the filter across the freq range
        return peq_spl(self.freq, self._x2peq(x))

    def _opt_peq_score(self, x: Encoded) -> float:
        # for  a given encoded peq, compute the score
        peq = self._x2peq(x)
        peq_freq = np.array(self._x2spl(x))[self.freq_min_index : self.freq_max_index]
        score = score_loss(self.df_speaker, peq)
        flat = np.add(self.target, peq_freq)
        flatness_bass_mid = np.linalg.norm(
            flat[0 : self.freq_midrange_index - self.freq_min_index], ord=2
        )
        flatness_mid_high = np.linalg.norm(
            flat[self.freq_midrange_index - self.freq_min_index :], ord=2
        )
        # this is black magic, why 10, 20, 40?
        # if you increase 20 you give more flexibility to the score (and less flat LW/ON)
        # without the constraint optimising the score get crazy results
        return score + float(flatness_bass_mid) / 5 + float(flatness_mid_high) / 50

    def _opt_peq_flat(self, x: list[float | int]) -> float:
        # for  a given encoded peq, compute a loss function based on flatness
        peq_freq = np.array(self._x2spl(x))[self.freq_min_index : self.freq_max_index]
        flat = np.add(self.target, peq_freq)
        flatness_l2 = np.linalg.norm(flat, ord=2)
        flatness_l1 = np.linalg.norm(flat, ord=1)
        return float(flatness_l2 + flatness_l1)

    def _opt_peq(self, x: list[float | int]) -> float:
        # for  a given encoded peq, compute a loss function
        return (
            self._opt_peq_score(x)
            if self.optim_config["loss"] == "score_loss"
            else self._opt_peq_flat(x)
        )

    def _opt_bounds_all(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        bounds0 = [
            [0, 6],
            [0, FREQ_NB_POINTS],  # algo does not support log scaling so I do it manually
            [self.min_q, self.max_q],  # max may be dependant on max_db
            [-self.max_db, self.max_db],
        ]
        bounds1 = [
            [3, 3],
            [self.freq_min_index, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db, self.max_db],
        ]
        bounds2 = [
            [0, 6],
            [
                self.freq_min_index,
                FREQ_NB_POINTS,
            ],  # algo does not support log scaling so I do it manually
            [self.min_q, 1.3],  # need to be computed from max_db
            [-self.max_db, self.max_db],
        ]
        return bounds0 + bounds1 * (n - 2) + bounds2

    def _opt_bounds_pk(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        bounds0 = [
            [3, 3],
            [0, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db, self.max_db],
        ]
        bounds1 = [
            [3, 3],
            [self.freq_min_index, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db, self.max_db],
        ]
        return bounds0 + bounds1 * (n - 1)

    def _opt_bounds(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        return (
            self._opt_bounds_all(n)
            if self.optim_config["full_biquad_optim"]
            else self._opt_bounds_pk(n)
        )

    def _opt_integrality(self, n: int) -> list[bool]:
        # True is a variable is an int and False if not
        return [True, True, False, False] * n

    def _opt_constraints_linear(self, n: int):
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
                vec[0] = -self.freq_min_index
                continue
            j = (i - 1) * 4 + 1
            mat[i][j] = 1
            j += 4
            mat[i][j] = -1
            vec[i] = -5
            # lb / uf can be float or array
        return opt.LinearConstraint(A=mat, lb=-np.inf, ub=vec, keep_feasible=False)

    def _opt_constraints_nonlinear(self, n: int):
        # Create some space between the various PEQ; if not the optimiser will add multiple PEQ
        # at more or less the same frequency and that will generate too much of a cut on the max
        # SPL. we have 200 points from 20Hz-20kHz, 5 give us 1/4 octave

        def _opt_constraints_freq(x):
            l = len(x) // 4
            for i in range(l - 1):
                t1, f1, q1, g1, s1 = self._x2params(x, i)
                t2, f2, q2, g2, s2 = self._x2params(x, i + 1)
                # if the sign is the same, then make some space between frequencies
                if s1 == s2:
                    if f1 - f2 > -5:
                        return 1
                else:
                    if f1 - f2 > -1:
                        return 1
                if f2 < self.freq_min_index:
                    return 1
            return -1

        return opt.NonlinearConstraint(
            fun=_opt_constraints_freq, lb=-np.inf, ub=0, keep_feasible=False
        )

    def _opt_display(self, xk, convergence):
        # comment if you want to print verbose traces
        l = len(xk) // 4
        print(f"IIR    Hz.  Q.   dB [{convergence}] iir={self.optim_config['full_biquad_optim']}")
        for i in range(l):
            t = int(xk[i * 4 + 0])
            f = int(self.log_freq[int(xk[i * 4 + 1])])
            q = xk[i * 4 + 2]
            db = xk[i * 4 + 3]
            print(f"{t:3d} {f:5d} {q:1.1f} {db:+1.2f}")

    def run(self):
        logger.info(
            "global optim: #peq=%d dB=[%1.1f, %1.1f] Q=[%1.1f, %1.1f] #iter=%d",
            self.max_peq,
            self.min_db,
            self.max_db,
            self.min_q,
            self.max_q,
            self.max_iter,
        )

        res = opt.differential_evolution(
            func=self._opt_peq,
            bounds=self._opt_bounds(self.max_peq),
            maxiter=self.max_iter,
            init="sobol",
            polish=False,
            integrality=self._opt_integrality(self.max_peq),
            callback=self._opt_display,
            constraints=self._opt_constraints_nonlinear(self.max_peq),
            disp=True,
            tol=0.01,
        )

        auto_peq = self._x2peq(res.x)
        auto_score = score_loss(self.df_speaker, auto_peq)

        return True, ((0, res.fun, auto_score), auto_peq)
