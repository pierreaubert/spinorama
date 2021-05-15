#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
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

import unittest

from spinorama.load_misc import sort_angles
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.load_princeton import parse_graph_princeton


class SpinoramaLoadTests(unittest.TestCase):
    def setUp(self):
        self.title, self.df = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )

    def test_smoke1(self):
        self.assertEqual(self.title, "CEA2034")
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn("On Axis", self.df.columns)
        self.assertNotIn("On-Axis", self.df.columns)


class SpinoramaSortAngleKlippelTests(unittest.TestCase):
    def setUp(self):
        self.title, self.df = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )

    def test_sort_angles_klippel(self):
        df_sa = sort_angles(self.df)
        self.assertListEqual(list(df_sa.columns), list(self.df.columns))


class SpinoramaSortAnglePrincetonests(unittest.TestCase):
    def setUp(self):
        self.df = parse_graph_princeton(
            "datas/measurements/Genelec 8351A/princeton/Genelec8351A_V_IR.mat", "V"
        )

    def test_sort_angles_princeton(self):
        df_sa = sort_angles(self.df)
        self.assertListEqual(list(df_sa.columns), list(self.df.columns))


class SpinoramaLoadSPLTests(unittest.TestCase):
    def setUp(self):
        self.title, self.df = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )

    def test_smoke1(self):
        self.assertEqual(self.title, "SPL Horizontal")
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn("On Axis", self.df.columns)
        self.assertNotIn("On-Axis", self.df.columns)
        # 200 in Freq, -170 to 180 10 by 10
        self.assertEqual(self.df.shape, (194, 2 * 18 + 1))


class SpinoramaLoadPrinceton(unittest.TestCase):
    def setUp(self):
        self.df = parse_graph_princeton(
            "datas/measurements/Genelec 8351A/princeton/Genelec8351A_V_IR.mat", "V"
        )

    def test_smoke1(self):
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn("Freq", self.df.columns)
        self.assertIn("On Axis", self.df.columns)
        self.assertNotIn("On-Axis", self.df.columns)
        self.assertEqual(self.df.shape, (3328, 2 * 36 + 1))
        self.assertLess(500, self.df.Freq.min())


if __name__ == "__main__":
    unittest.main()
