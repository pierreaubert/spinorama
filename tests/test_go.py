#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

# import os
import math
import random
import unittest

import numpy as np
import numpy.testing as npt
import pandas as pd

from spinorama.filter_peq import peq_print
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.auto_global import GlobalOptimizer, _resample

pd.set_option("display.max_rows", 202)


class ResampleTests(unittest.TestCase):
    def setUp(self):
        pass

    def test_basic(self):
        x1 = [1, 2, 3, 4, 5]
        y1 = [x * x for x in x1]
        x2 = [1.5, 2.5, 3.5, 4.5]
        y2 = _resample(x1, x2, y1)
        y2_expected = [x * x for x in x2]
        npt.assert_almost_equal(y2_expected, y2, decimal=0)

    def test_realistic(self):
        x1 = np.logspace(math.log10(20), math.log10(20000), 200)
        x2 = np.logspace(math.log10(20), math.log10(20000), 180)
        # ruff: noqa: S311
        y1 = [random.randrange(40, 80, 1) for x in x1]
        y2 = _resample(x1, x2, y1)
        error = np.sum(y1) / len(y1) - np.sum(y2) / len(y2)
        self.assertAlmostEqual(error, 0, 1)
        x2 = np.logspace(math.log10(20), math.log10(20000), 200)
        x1 = np.logspace(math.log10(20), math.log10(20000), 180)
        # ruff: noqa: S311
        y1 = [random.randrange(40, 80, 1) for x in x1]
        y2 = _resample(x1, x2, y1)
        error = np.sum(y1) / len(y1) - np.sum(y2) / len(y2)
        self.assertAlmostEqual(error, 0, 1)


class GlobalOptimizerTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        _, (self.title, self.spin_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        # configuration
        optim_config = {
            "target_min_freq": 80,
            "target_max_freq": 16000,
            "MIN_Q": 1.0,
            "MAX_Q": 3.0,
            "MIN_DBGAIN": 1.0,
            "MAX_DBGAIN": 3.0,
            "MAX_ITER": 500,
            "MAX_NUMBER_PEQ": 3,
            "use_all_biquad": False,
        }
        # speaker data
        df_speaker = {
            "CEA2034_unmelted": self.spin_unmelted,
        }
        # create an optimizer object
        self.go = GlobalOptimizer(df_speaker, optim_config)

    def test_smoke_test(self):
        self.assertEqual(self.go.freq_min, 80)
        self.assertEqual(self.go.freq_max, 16000)
        self.assertEqual(len(self.go.freq), 194)
        self.assertGreater(self.go.freq_space[0], 20)
        self.assertAlmostEqual(self.go.freq_space[-1], 20000)
        self.assertEqual(len(self.go.freq_space), 200)
        self.assertGreater(self.go.freq_min_index, 19)
        self.assertGreater(self.go.freq_max_index, 180)

    def test_freq2index(self):
        for f in [20, 10000, 16000, 20000]:
            self.assertLessEqual(f, self.go._index2freq(self.go._freq2index(f)))

    def test_index2freq(self):
        for idx in [0, 1, 50, 199]:
            self.assertAlmostEqual(idx, self.go._freq2index(self.go._index2freq(idx)))

    def test_x2params(self):
        x1 = [3, 20, 1, -5]
        t, f, q, spl, sign = self.go._x2params(x1, 0)
        self.assertEqual(t, 3)
        self.assertEqual(f, 20)
        self.assertEqual(q, 1)
        self.assertEqual(spl, -5)
        self.assertEqual(sign, -1)
        x2 = [1, 0, 1, 5]
        t, f, q, spl, sign = self.go._x2params(x2, 0)
        self.assertEqual(t, 1)
        self.assertEqual(f, 0)
        self.assertEqual(q, 1)
        self.assertEqual(spl, 5)
        self.assertEqual(sign, 1)

    def test_x2_peq(self):
        x1 = [3, 20, 1, -5]
        peq = self.go._x2peq(x1)
        self.assertEqual(len(peq), 1)
        iir = peq[0][1]
        self.assertEqual(iir.biquad_type, 3)
        self.assertAlmostEqual(iir.freq, self.go.freq_space[20])

    def test_x2_spl(self):
        x1 = [3, 20, 1, -5]
        spl = self.go._x2spl(x1)
        npt.assert_array_less(spl, 0)
        x2 = [3, 50, 1, 5]
        spl = self.go._x2spl(x2)
        npt.assert_array_less(0, spl)

    def test_bounds_all(self):
        b3 = self.go._opt_bounds_all(3)
        # first peq
        self.assertEqual(b3[0], [0, 6])
        self.assertEqual(b3[1], [0, 200])
        # second
        self.assertEqual(b3[4], [3, 3])
        self.assertEqual(b3[5], [40, 200])
        # third
        self.assertEqual(b3[8], [0, 6])
        self.assertEqual(b3[9], [40, 200])

    def test_bounds_pk(self):
        b3 = self.go._opt_bounds_pk(3)
        # first peq
        self.assertEqual(b3[0], [3, 3])
        self.assertEqual(b3[1], [0, 200])
        # second
        self.assertEqual(b3[4], [3, 3])
        self.assertEqual(b3[5], [40, 200])
        # third
        self.assertEqual(b3[8], [3, 3])
        self.assertEqual(b3[9], [40, 200])

    def test_linear_constraint(self):
        lc = self.go._opt_constraints_linear(3)
        # freq are going up, pass
        a = lc.A
        b = lc.ub
        x = np.array([0, 25, 0, 0, 0, 50, 0, 0, 0, 75, 0, 0])
        c = np.matmul(a, x) - b
        npt.assert_array_less(c, 0)
        # first freq above min failed
        x = np.array([0, 25, 0, 0, 0, 34, 0, 0, 0, 75, 0, 0])
        c = np.matmul(a, x) - b
        self.assertGreater(c[0], 0)
        # second > third failed
        x = np.array([0, 25, 0, 0, 0, 100, 0, 0, 0, 75, 0, 0])
        c = np.matmul(a, x) - b
        self.assertGreater(c[2], 0)

    def test_non_linear_constraint(self):
        nlc = self.go._opt_constraints_nonlinear(3)
        fun = nlc.fun
        x = np.array([0, 25, 2, 2, 1, 50, 2, -2, 2, 75, 2, 2])
        # self.go._x2print(x)
        c = fun(x)
        self.assertEqual(c, -1)  # true
        x = np.array([0, 25, 2, 2, 1, 34, 2, -2, 2, 75, 2, 2])
        # self.go._x2print(x)
        c = fun(x)
        self.assertEqual(c, 1)  # false
        x = np.array([0, 25, 2, 2, 1, 100, 2, -2, 2, 75, 2, 2])
        # self.go._x2print(x)
        c = fun(x)
        self.assertEqual(c, 1)  # false


if __name__ == "__main__":
    unittest.main()
