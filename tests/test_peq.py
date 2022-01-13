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
from spinorama.filter_peq import peq_butterworth_q, peq_linkwitzriley_q


class SpinoramaFilterPeqTests(unittest.TestCase):
    def test_butterworth(self):
        npt.assert_almost_equal(peq_butterworth_q(2), [0.707], 3)
        npt.assert_almost_equal(peq_butterworth_q(5), [1.618, 0.618, -1.0], 3)
        npt.assert_almost_equal(peq_butterworth_q(8), [2.563, 0.9, 0.601, 0.51], 3)

    def test_linkwitzriley(self):
        # lr4
        npt.assert_almost_equal(peq_linkwitzriley_q(4), [0.707, 0.707], 3)
        # lr6
        npt.assert_almost_equal(
            peq_linkwitzriley_q(10), [1.618, 0.618, 1.618, 0.618, 0.5], 3
        )


if __name__ == "__main__":
    unittest.main()
