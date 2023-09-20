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
from scipy.interpolate import InterpolatedUnivariateSpline

from spinorama import logger
from spinorama.constant_paths import MIDRANGE_MAX_FREQ
from spinorama.ltype import Vector, DataSpeaker, OptimResult
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import Peq, peq_spl, peq_print
from spinorama.auto_misc import get3db
from spinorama.auto_loss import score_loss

FREQ_NB_POINTS = 200

# a type for variables to be optimised
Encoded = list[float | int]


def _resample(x1: list[float], x2: list[float], y1: list[float]) -> list[float]:
    # resample
    #   x1 array of x values
    #   y1 array of y values
    #   x2 new array of x values
    #   return y2 which is a linear interpolation of
    # Note:
    # doesnt need to be fast since it is called only a few times
    #
    # x1    .   .   .  .  .
    # x2      .   .  ..  . ...
    # for x each element of x2
    #  find i such that x1[i] <= x < x1[i+1]
    #  y = linear interpolation of y1[i] and y1[i+1]
    # --------------
    # y2 = []
    # for x in x2:
    #    i = bisect.bisect_left(x1, x)
    #    j = bisect.bisect_right(x1, x)
    #    t = (y1[j]-y1[i])/(x1[j]-x1[i])
    #    y2.append(t)
    # return y2
    # --------------
    spline = InterpolatedUnivariateSpline(np.log10(x1), y1, k=3)
    return spline(np.log10(x2))


class GlobalOptimizer(object):
    """Main optimiser: follow a greedy strategy"""

    def __init__(
        self,
        df_speaker: DataSpeaker,
        optim_config: dict,
    ):
        self.df_speaker = df_speaker
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
        #             min              midrange                   max     |
        # ---|----------|-------------------------------------------|-----|
        #    |                    valid range (Hz)                        |
        #    | 0                     indexed_freq                     200 |
        # ---|------------------------------------------------------------|

        self.freq_space = np.logspace(1 + math.log10(2), 4 + math.log10(2), FREQ_NB_POINTS)

        # a bit of black magic
        self.freq_min_index = self._freq2index(self.freq_min)
        self.freq_midrange_index = self._freq2index(MIDRANGE_MAX_FREQ / 2)
        self.freq_max_index = self._freq2index(self.freq_max)

        # get lw/on
        self.lw = df_speaker["CEA2034_unmelted"]["Listening Window"].to_numpy()
        self.freq = df_speaker["CEA2034_unmelted"]["Freq"].to_numpy()

        # used for controlling optimisation of the score
        lw_target = self.lw - np.linspace(0, 0.5, len(self.lw))
        self.target = _resample(self.freq, self.freq_space, lw_target)

        self.min_db = optim_config["MIN_DBGAIN"]
        self.max_db = optim_config["MAX_DBGAIN"]
        self.min_q = optim_config["MIN_Q"]
        self.max_q = optim_config["MAX_Q"]
        self.max_peq = optim_config["MAX_NUMBER_PEQ"]
        self.max_iter = optim_config["MAX_ITER"]

    def _freq2index(self, f: float):
        return bisect.bisect_left(self.freq_space, f)

    def _index2freq(self, i: int):
        # TODO
        if i == 200:
            i = 199
        return self.freq_space[i]

    def _x2params(self, x: Encoded, i: int) -> tuple[int, int, float, float, int]:
        # take an encoded Peq and return all values of the parameters of the filter
        # type
        idx = i * 4
        t = int(x[idx])
        # freq (encoded as an int)
        idx += 1
        f_pos = int(x[idx])  # supposed to be an int but depending on the algo it may not be true
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
            iir_type, index_freq, q, spl, _ = self._x2params(x, i)
            freq = self._index2freq(index_freq)
            peq.append((1.0, Biquad(iir_type, freq, 48000, q, spl)))
        return peq

    def _x2spl(self, x: Encoded) -> Vector:
        # take a list of encoded filters and return the magnitude of the filter across the freq range
        return peq_spl(self.freq_space, self._x2peq(x))

    def _opt_peq_score(self, x: Encoded) -> float:
        # for  a given encoded peq, compute the score
        peq = self._x2peq(x)
        peq_freq = np.array(self._x2spl(x))
        score = score_loss(self.df_speaker, peq)
        flat = np.add(self.target, peq_freq)
        flatness_bass_mid = np.linalg.norm(
            flat[self.freq_min_index : self.freq_midrange_index], ord=2
        )
        flatness_mid_high = np.linalg.norm(flat[self.freq_midrange_index :], ord=2)
        # this is black magic, why 10, 20, 40?
        # if you increase 20 you give more flexibility to the score (and less flat LW/ON)
        # without the constraint optimising the score get crazy results
        return score + float(flatness_bass_mid) / 5 + float(flatness_mid_high) / 50

    def _opt_peq_flat(self, x: list[float | int]) -> float:
        # for  a given encoded peq, compute a loss function based on flatness
        peq_freq = np.array(self._x2spl(x))
        flat = np.add(self.target, peq_freq)[self.freq_min_index : self.freq_max_index]
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
                # only 1 peq before min_index
                if f2 < self.freq_min_index:
                    return 1
                # if pk = 1 or 5, check that the max is below max_db
                if t1 != 3: # PK
                    m = self._x2peq(x)[i][1].log_result(f1)
                    if abs(m) > self.max_db:
                        return 1
            return -1

        return opt.NonlinearConstraint(
            fun=_opt_constraints_freq, lb=-np.inf, ub=0, keep_feasible=False
        )

    def _opt_display(self, xk, convergence):
        # comment if you want to print verbose traces
        print(f"[f={convergence}] iir={self.optim_config['full_biquad_optim']}")
        peq_print(self._x2peq(xk))

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
