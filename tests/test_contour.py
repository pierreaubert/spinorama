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

import unittest
import numpy as np
import pandas as pd
from spinorama.load_misc import sort_angles
from spinorama.compute_misc import compute_contour, reshape


class SpinoramaContourSizeTests(unittest.TestCase):
    def setUp(self):
        freq = [20, 200, 2000, 20000]
        onaxis = [10, 10, 10, 10]
        d10 = [8, 7, 6, 5]
        self.df = pd.DataFrame({"Freq": freq, "On Axis": onaxis, "10°": d10})

    def test_smoke1(self):
        af, am, az = compute_contour(self.df.loc[self.df.Freq >= 10])
        self.assertEqual(af.size, am.size)
        self.assertEqual(af.size, az.size)


class SpinoramaContourTests(unittest.TestCase):
    def setUp(self):
        freq = [20, 100, 200, 1000, 2000, 10000, 20000]
        onaxis = [10, 10, 10, 10, 10, 10, 10]
        #
        d10p = [10, 10, 9, 9, 8, 8, 7]
        d20p = [10, 10, 8, 8, 7, 7, 6]
        d30p = [10, 10, 7, 7, 6, 6, 5]
        # decrease faster on the neg size
        d10m = [10, 10, 8, 8, 7, 7, 6]
        d20m = [10, 8, 6, 6, 4, 4, 2]
        d30m = [10, 6, 6, 4, 2, 2, 0]
        self.df = sort_angles(
            pd.DataFrame(
                {
                    "Freq": freq,
                    "On Axis": onaxis,
                    "10°": d10p,
                    "-10°": d10m,
                    "20°": d20p,
                    "-20°": d20m,
                    "30°": d30p,
                    "-30°": d30m,
                }
            )
        )

    def test_smoke_size(self):
        af, am, az = compute_contour(self.df.loc[self.df.Freq >= 10])
        self.assertEqual(af.size, am.size)
        self.assertEqual(af.size, az.size)

    def test_smoke_freq(self):
        af, _, _ = compute_contour(self.df.loc[self.df.Freq >= 100])
        self.assertAlmostEqual(np.min(af), 100)
        self.assertAlmostEqual(np.max(af), 20000)

    def test_smoke_angle(self):
        _, am, _ = compute_contour(self.df.loc[self.df.Freq >= 10])
        self.assertEqual(np.min(am), -30)
        self.assertEqual(np.max(am), 30)

    def test_smoke_db_normalized(self):
        _, _, az = compute_contour(self.df.loc[self.df.Freq >= 10])
        self.assertEqual(np.min(az), 0)
        self.assertEqual(np.max(az), 10)

    def test_smoke_preserve_angle(self):
        _, am, _ = compute_contour(self.df.loc[self.df.Freq >= 10])
        # check that value is constant
        self.assertTrue(all(a == am[0][0] for a in am[0]))
        # extract all angles in order
        angles = [am[i][0] for i in range(0, len(am))]
        # check it is decreasing
        self.assertTrue(all(i < j for i, j in zip(angles, angles[1:], strict=False)))


class SpinoramaReshapeTests(unittest.TestCase):
    def setUp(self):
        freq = [20, 100, 200, 1000, 2000, 10000, 20000]
        onaxis = [10, 10, 10, 10, 10, 10, 10]
        d10p = [10, 10, 9, 9, 8, 8, 7]
        d20p = [10, 10, 8, 8, 7, 7, 6]
        d30p = [10, 10, 7, 7, 6, 6, 5]
        # decrease faster on the neg size
        d10m = [10, 10, 8, 8, 7, 7, 6]
        d20m = [10, 8, 6, 6, 4, 4, 2]
        d30m = [10, 6, 6, 4, 2, 2, 0]
        self.df = sort_angles(
            pd.DataFrame(
                {
                    "Freq": freq,
                    "On Axis": onaxis,
                    "10°": d10p,
                    "-10°": d10m,
                    "20°": d20p,
                    "-20°": d20m,
                    "30°": d30p,
                    "-30°": d30m,
                }
            )
        )
        self.af, self.am, self.az = compute_contour(self.df.loc[self.df.Freq >= 20])

    def test_smoke_size(self):
        for scale in range(2, 10):
            raf, ram, raz = reshape(self.af, self.am, self.az, scale)
            self.assertEqual(raf.size, ram.size)
            self.assertEqual(raf.size, raz.size)

    def test_smoke_freq(self):
        for scale in range(2, 10):
            raf, _, _ = reshape(self.af, self.am, self.az, scale)
            self.assertAlmostEqual(np.min(raf), 20)
            self.assertAlmostEqual(np.max(raf), 20000)

    def test_smoke_angle(self):
        for scale in range(2, 10):
            _, ram, _ = reshape(self.af, self.am, self.az, scale)
            self.assertEqual(np.min(ram), -30)
            self.assertEqual(np.max(ram), 30)

    def test_smoke_db_normalized(self):
        for scale in range(2, 10):
            _, _, raz = reshape(self.af, self.am, self.az, scale)
            self.assertEqual(np.min(raz), 0)
            self.assertEqual(np.max(raz), 10)

    def test_smoke_preserve_angle(self):
        for scale in range(2, 10):
            _, ram, _ = reshape(self.af, self.am, self.az, scale)
            # check that value is constant
            self.assertTrue(all(a == ram[0][0] for a in ram[0]))
            # extract all angles in order
            angles = [ram[i][0] for i in range(0, len(ram))]
            # check it is decreasing
            self.assertTrue(all(i < j for i, j in zip(angles, angles[1:], strict=False)))


if __name__ == "__main__":
    unittest.main()
