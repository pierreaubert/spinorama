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

import bisect
import math

import numpy as np
import scipy.optimize as opt
from scipy.interpolate import InterpolatedUnivariateSpline

from spinorama import logger
from spinorama.constant_paths import MIDRANGE_MAX_FREQ
from spinorama.ltype import Vector, DataSpeaker
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import Peq, peq_spl, peq_print
from spinorama.auto_misc import get3db
from spinorama.auto_loss import score_loss

FREQ_NB_POINTS = 200
CONVERGENCE_TOLERANCE = 0.001

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
        self.config = optim_config
        logger.debug(
            "GlobalOptimizer config {%s}",
            ", ".join(["{}: {}".format(k, v) for k, v in optim_config.items()]),
        )

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
        self.freq_2k_index = self._freq2index(2000)
        self.freq_midrange_index = self._freq2index(MIDRANGE_MAX_FREQ / 2)
        self.freq_max_index = self._freq2index(self.freq_max)

        # get lw/on/pir & freq
        self.lw = df_speaker["CEA2034_unmelted"]["Listening Window"].to_numpy()
        self.on = df_speaker["CEA2034_unmelted"]["On Axis"].to_numpy()
        self.pir = None
        if "Estimated In-Room Response_unmelted" in df_speaker:
            self.pir = df_speaker["Estimated In-Room Response_unmelted"][
                "Estimated In-Room Response"
            ].to_numpy()
        self.freq = df_speaker["CEA2034_unmelted"]["Freq"].to_numpy()

        # used for controlling optimisation of the score
        lw_slope = self.config.get("slope_listening_window", -0.5)
        lw_target = self.lw - np.linspace(0, lw_slope, len(self.lw))
        pir_slope = self.config.get("slope_pred_in_room", -7)
        pir_target = None
        if self.pir is not None:
            pir_target = self.pir - np.linspace(0, pir_slope, len(self.pir))

        self.target_lw = _resample(self.freq, self.freq_space, lw_target)
        self.target_on = _resample(self.freq, self.freq_space, self.on)
        self.target_pir = None
        if pir_target is not None:
            self.target_pir = _resample(self.freq, self.freq_space, pir_target)

        self.min_db = self.config["MIN_DBGAIN"]
        self.max_db = self.config["MAX_DBGAIN"]
        self.min_q = self.config["MIN_Q"]
        self.max_q = self.config["MAX_Q"]
        self.max_peq = self.config["MAX_NUMBER_PEQ"]
        self.max_iter = self.config["MAX_ITER"]
        self.current_score = None

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

    def _x2print(self, x: Encoded) -> None:
        peq = self._x2peq(x)
        peq_print(peq)

    def _x2spl(self, x: Encoded) -> Vector:
        # take a list of encoded filters and return the magnitude of the filter across the freq range
        return peq_spl(self.freq_space, self._x2peq(x))

    def _opt_peq_score(self, x: Encoded) -> float:
        # for  a given encoded peq, compute the score
        peq = self._x2peq(x)
        peq_freq = np.array(self._x2spl(x))
        score = score_loss(self.df_speaker, peq)
        flat_on = np.add(self.target_on, peq_freq)
        # currently unsued
        # flat_lw = np.add(self.target_lw, peq_freq)
        # flat_pir = np.add(self.target_pir, peq_freq)
        # split flatness of ON on various ranges
        flatness_on_bass_mid = np.linalg.norm(
            flat_on[self.freq_min_index : self.freq_midrange_index], ord=2
        )
        flatness_on_mid_high = np.linalg.norm(flat_on[self.freq_midrange_index :], ord=2)
        # flatness_on_bass_mid = np.linalg.norm(flat_on[self.freq_min_index : self.freq_2k_index], ord=2)
        # flatness_on_mid_high = np.linalg.norm(flat_on[self.freq_2k_index :], ord=2)
        # not used but could be
        # flatness_pir = np.linalg.norm(flat_pir, ord=2)
        # flatness_pir_bass_mid = np.linalg.norm(flat_pir[self.freq_min_index : self.freq_midrange_index], ord=2)
        # flatness_pir_mid_high = np.linalg.norm(flat_pir[self.freq_midrange_index :], ord=2)
        # this is black magic, why 10, 20, 40?
        # if you increase 20 you give more flexibility to the score (and less flat LW/ON)
        # without the constraint optimising the score get crazy results
        return score + float(flatness_on_bass_mid) / 15 + float(flatness_on_mid_high) / 50

    def _opt_peq_flat(self, x: list[float | int]) -> float:
        # for  a given encoded peq, compute a loss function based on flatness
        peq_freq = np.array(self._x2spl(x))
        flat = None
        curves = self.config.get("curve_names")
        if curves is None or (len(curves) == 1 and curves[0] == "On Axis"):
            flat = np.add(self.target_on, peq_freq)[self.freq_min_index : self.freq_max_index]
        elif len(curves) == 1 and curves[0] == "Listening Window":
            flat = np.add(self.target_lw, peq_freq)[self.freq_min_index : self.freq_max_index]
        elif len(curves) == 1 and curves[0] == "Estimated In-Room Response":
            flat = np.add(self.target_pir, peq_freq)[self.freq_min_index : self.freq_max_index]
        else:
            logger.error("configuration is not yet supported")
            return 1000.0

        flatness_l2 = np.linalg.norm(flat, ord=2)
        flatness_l1 = np.linalg.norm(flat, ord=1)
        return float(flatness_l2 + flatness_l1)

    def _opt_peq(self, x: list[float | int]) -> float:
        # for  a given encoded peq, compute a loss function
        self.current_score = (
            self._opt_peq_score(x) if self.config["loss"] == "score_loss" else self._opt_peq_flat(x)
        )
        return self.current_score

    def _opt_bounds_all(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        bounds0 = [
            [0, 6],
            [0, FREQ_NB_POINTS],  # algo does not support log scaling so I do it manually
            [self.min_q, self.max_q],  # max may be dependant on max_db
            [-self.max_db * 3, self.max_db],
        ]
        bounds1 = [
            [3, 3],
            [self.freq_min_index, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db * 3, self.max_db],
        ]
        bounds2 = [
            [0, 6],
            [
                self.freq_min_index,
                FREQ_NB_POINTS,
            ],  # algo does not support log scaling so I do it manually
            [self.min_q, 1.3],  # need to be computed from max_db
            [-self.max_db * 3, self.max_db],
        ]
        return bounds0 + bounds1 * (n - 2) + bounds2

    def _opt_bounds_pk(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        bounds0 = [
            [3, 3],
            [0, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db * 3, self.max_db],
        ]
        bounds1 = [
            [3, 3],
            [self.freq_min_index, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db * 3, self.max_db],
        ]
        return bounds0 + bounds1 * (n - 1)

    # only allow negative amplitude
    def _opt_bounds_pk_neg(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        bounds0 = [
            [3, 3],
            [0, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db * 3, -self.min_db],
        ]
        bounds1 = [
            [3, 3],
            [self.freq_min_index, FREQ_NB_POINTS],
            [self.min_q, self.max_q],
            [-self.max_db * 3, -self.min_db],
        ]
        return bounds0 + bounds1 * (n - 1)

    def _opt_bounds(self, n: int) -> list[list[int | float]]:
        # compute bounds for variables
        if self.config["use_all_biquad"]:
            return self._opt_bounds_all(n)
        if self.config["plus_and_minus"]:
            return self._opt_bounds_pk(n)
        return self._opt_bounds_pk_neg(n)

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
        # SPL. If we have 200 points from 20Hz-20kHz, 5 points give us 1/4 octave.
        # Control various parameters and keep them under check.

        def _opt_constraints_q(x) -> int:
            # you don't need to re-check the Q since it done by the bounds
            # but we should reduce the Q with frequency since it is less and less detectable
            # 3400Hz => 340 m/s / 3400 Hz == 10 cm
            # assumption 10 cm movement -> above that very low q allowed only
            l = len(x) // 4
            for i in range(l):
                _, f, q, _, _ = self._x2params(x, i)
                if q > self.max_q or q < self.min_q:
                    return 1
                f_hz = self._index2freq(f)
                if (f_hz > 2000 and q > 1.0) or (f_hz > 3500 and q > 0.5):
                    return 1
            return -1

        def _opt_constraints_gain(x) -> int:
            # check that total gain at any point in lower that max_db
            l = len(x) // 4
            for i in range(l):
                _, f, _, g, _ = self._x2params(x, i)
                # ko if between -min and +min
                if ((g > 0.0 and (g < self.min_db)) or (g > self.max_db)) or (
                    g < 0.0 and g > -self.min_db
                ):
                    # print("gain {} = {} rejected".format(i, g))
                    return 1

            # check that we do not clip
            spl = self._x2spl(x)
            spl_max = np.max(np.clip(spl, 0, None))
            if spl_max > self.max_db:
                # print("max gain {} > {} rejected".format(spl_max, self.max_db))
                # print(spl)
                return 1
            return -1

        def _opt_constraints_freq(x) -> int:
            # check on frequencies
            l = len(x) // 4
            for i in range(l - 1):
                _, f1, _, _, s1 = self._x2params(x, i)
                _, f2, _, _, s2 = self._x2params(x, i + 1)
                # if the sign is the same, then make some space between frequencies
                if s1 == s2:
                    if f1 - f2 > -5:
                        return 1
                else:
                    if f1 - f2 > -1:
                        return 1
                # only 1 peq before min_index
                if f2 < self.freq_min_index or f2 > self.freq_max_index:
                    return 1
            return -1

        def _opt_constraints_all(x) -> int:
            c_freq = _opt_constraints_freq(x) == 1
            c_gain = _opt_constraints_gain(x) == 1
            c_q = _opt_constraints_q(x) == 1
            if c_freq or c_gain or c_q:
                # print("NL constraints: freq={} gain={} q={}".format(c_freq, c_gain, c_q))
                return 1
            return -1

        return opt.NonlinearConstraint(
            fun=_opt_constraints_all, lb=-np.inf, ub=0, keep_feasible=False
        )

    def _opt_display(self, xk, convergence):
        # comment if you want to print verbose traces
        iir_status = "*" if self.config["use_all_biquad"] else "pk"
        score_status = (
            "{:3.1f}".format(self.current_score) if self.current_score is not None else "?"
        )
        print(
            f"[f={1 - convergence}<{CONVERGENCE_TOLERANCE}] iir={iir_status} score={score_status}"
        )
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
            tol=CONVERGENCE_TOLERANCE,
        )

        auto_peq = self._x2peq(res.x)
        auto_score = score_loss(self.df_speaker, auto_peq)

        return True, ((0, res.fun, auto_score), auto_peq)
