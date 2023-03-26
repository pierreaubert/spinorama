#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2022 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import math
import unittest

import numpy as np
import numpy.testing as npt

from spinorama.filter_iir import Biquad


class SpinoramaFilterIIRTests(unittest.TestCase):
    def setUp(self):
        self.freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 200)
        self.peak = Biquad(3, 1000, 48000, 1, 3)

    def test_smoke1(self):
        peq_slow = np.array([20.0 * math.log10(self.peak.resultSlow(f)) for f in self.freq])
        peq_fast = np.array([20.0 * math.log10(self.peak.result(f)) for f in self.freq])
        peq_vec = self.peak.np_log_result(self.freq)
        with self.assertRaises(AssertionError):
            npt.assert_array_almost_equal_nulp(peq_slow, peq_fast)
            npt.assert_array_almost_equal_nulp(peq_slow, peq_vec)


if __name__ == "__main__":
    unittest.main()
