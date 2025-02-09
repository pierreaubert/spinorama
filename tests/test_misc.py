#!/usr/bin/env python3
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

import math
import typing
import unittest

import numpy as np
import pandas as pd

from spinorama.misc import graph_melt, measurements_complete_freq, measurements_complete_spl

from spinorama.compute_misc import unify_freq

from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump


class SpinoramaUnifyFreqTests(unittest.TestCase):
    _measurements_set1: typing.ClassVar = set(
        [
            "Freq",
            "On Axis",
            "Listening Window",
            "Early Reflections",
            "Sound Power",
        ]
    )

    _measurements_set2: typing.ClassVar = set(
        [
            "On Axis",
            "Listening Window",
            "Early Reflections",
            "Sound Power",
        ]
    )

    def setUp(self):
        self.dfs = {}

        speaker_name = "BIC America Venturi DV62si"
        status, (title, self.df_melted) = parse_graphs_speaker_rew_text_dump(
            "datas/measurements",
            "BIC America",
            speaker_name,
            "",
            "vendor",
        )
        self.assertTrue(status)
        self.assertEqual(title, "CEA2034")

        self.unify = unify_freq(self.df_melted)
        self.df = graph_melt(self.unify)

    def test_properties(self):
        #
        self.assertEqual(self.df_melted.shape, (5742, 3))
        #
        ushape = self.unify.shape
        self.assertEqual(ushape, (957, 5))
        self.assertSetEqual(set(self.unify.keys()), self._measurements_set1)
        self.assertFalse(self.unify.isna().to_numpy().any())
        #
        self.assertEqual(self.df.shape, (ushape[0] * 4, 3))
        self.assertSetEqual(set(self.df.Measurements), self._measurements_set2)


class SpinoramaMeasurementsQualitySPLTest(unittest.TestCase):
    def setUp(self):
        self.df_10 = pd.DataFrame({"Freq": [1, 2, 3], "On Axis": [0, 0, 0]})
        for iangle in range(-170, 190, 10):
            if iangle == 0:
                continue
            angle = "{}°".format(iangle)
            self.df_10[angle] = [iangle, iangle, iangle]
        self.df_5 = self.df_10.copy()
        for iangle in range(-165, 185, 10):
            if iangle == 0:
                continue
            angle = "{}°".format(iangle)
            self.df_5[angle] = [iangle, iangle, iangle]
        self.df_e1 = pd.DataFrame({"Freq": [1, 2, 3], "On Axis": [0, 0, 0]})
        for iangle in range(-170, 180, 10):
            if iangle == 0:
                continue
            angle = "{}°".format(iangle)
            self.df_e1[angle] = [iangle, iangle, iangle]
        self.df_e2 = pd.DataFrame({"Freq": [1, 2, 3], "On Axis": [0, 0, 0]})
        for iangle in range(-180, 190, 10):
            angle = "{}°".format(iangle)
            self.df_e2[angle] = [iangle, iangle, iangle]

    def test_spl_full(self):
        self.assertTrue(measurements_complete_spl(self.df_10, self.df_10))
        self.assertTrue(measurements_complete_spl(self.df_5, self.df_5))
        self.assertFalse(measurements_complete_spl(self.df_e1, self.df_e1))
        self.assertFalse(measurements_complete_spl(self.df_10, self.df_e1))
        self.assertFalse(measurements_complete_spl(self.df_e1, self.df_10))
        self.assertNotIn("0°", self.df_10)
        self.assertIn("0°", self.df_e2.keys())


class SpinoramaMeasurementsQualityFreqTest(unittest.TestCase):
    def setUp(self):
        self.df_ok = pd.DataFrame({"Freq": np.logspace(1 + math.log10(2), 4 + math.log10(2), 200)})
        self.df_ko1 = pd.DataFrame({"Freq": np.logspace(1 + math.log10(2), 4 + math.log10(2), 50)})
        self.df_ko2 = pd.DataFrame({"Freq": np.logspace(2 + math.log10(2), 4 + math.log10(2), 200)})
        self.df_ko3 = pd.DataFrame({"Freq": np.logspace(1 + math.log10(2), 3 + math.log10(2), 200)})

    def test_spl_full(self):
        self.assertTrue(measurements_complete_freq(self.df_ok, self.df_ok))
        self.assertFalse(measurements_complete_freq(self.df_ko1, self.df_ko1))
        self.assertFalse(measurements_complete_freq(self.df_ko2, self.df_ko2))
        self.assertFalse(measurements_complete_freq(self.df_ko3, self.df_ko3))


if __name__ == "__main__":
    unittest.main()
