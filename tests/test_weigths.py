#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
from spinorama.compute_cea2034 import (
    compute_area_Q,
    compute_weigths,
)


std_weigths = [
    0.000604486,
    0.004730189,
    0.008955027,
    0.012387354,
    0.014989611,
    0.016868154,
    0.018165962,
    0.019006744,
    0.019477787,
    0.019629373,
]


class WeigthsTests(unittest.TestCase):
    def setUp(self):
        pass

    def test_area_Q(self):
        # expect area of half sphere
        self.assertAlmostEqual(compute_area_Q(90, 90), 2.0 * math.pi)

    def test_weigths(self):
        weigths = np.array(compute_weigths())
        # check that they are the same expect the scaling
        scale = np.linalg.norm(weigths) / np.linalg.norm(std_weigths)
        scaled_weigths = weigths / scale

        with self.assertRaises(AssertionError):
            npt.assert_array_almost_equal_nulp(scaled_weigths, std_weigths)

        delta = np.max(np.abs(scaled_weigths - std_weigths))
        self.assertLess(delta, 1.0e-9)
