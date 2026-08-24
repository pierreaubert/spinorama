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
import os
from pathlib import Path
import tempfile
import typing
import unittest

import numpy as np
import pandas as pd

from spinorama.misc import (
    fingerprint_paths,
    graph_melt,
    measurements_complete_freq,
    measurements_complete_spl,
)

from spinorama.compute.misc import unify_freq
from spinorama.compute.misc import compute_slope_smoothness
from spinorama.compute.scores import sm

from spinorama.loaders.rew_text_dump import parse_graphs_speaker_rew_text_dump


class FingerprintPathsTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_tracks_file_changes(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "measurement.txt"
            input_path.write_text("one\n", encoding="utf-8")

            first = fingerprint_paths([temporary_dir], version="test-v1")
            self.assertEqual(first, fingerprint_paths([temporary_dir], version="test-v1"))

            input_path.write_text("two\n", encoding="utf-8")
            stats = input_path.stat()
            os.utime(input_path, ns=(stats.st_atime_ns, stats.st_mtime_ns + 1_000_000))
            self.assertNotEqual(first, fingerprint_paths([temporary_dir], version="test-v1"))
            self.assertNotEqual(first, fingerprint_paths([temporary_dir], version="test-v2"))


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


class SpinoramaSmoothnessTests(unittest.TestCase):
    def test_slope_smoothness_uses_normalized_sm(self):
        freq = np.geomspace(100.0, 12000.0, 200)
        db = 85.0 + 0.02 * np.sin(np.linspace(0.0, 12.0 * np.pi, freq.size))
        test_df = pd.DataFrame({"Freq": freq, "dB": db})

        _, _, slope, graph_sm = compute_slope_smoothness(test_df, "dB", False)

        self.assertLess(abs(slope), 0.01)
        self.assertGreater(graph_sm, 0.99)
        self.assertAlmostEqual(graph_sm, sm(test_df), places=12)


class SpinoramaMeasurementsQualitySPLTest(unittest.TestCase):
    def setUp(self):
        self.df_10 = pd.DataFrame({"Freq": [1, 2, 3], "On Axis": [0, 0, 0]})
        for iangle in range(-170, 190, 10):
            if iangle == 0:
                continue
            angle = "{}°".format(iangle)
            self.df_10[angle] = [iangle, iangle, iangle]
        self.df_5 = self.df_10.copy()
        for iangle in range(-175, 185, 10):
            if iangle == 0:
                continue
            angle = "{}°".format(iangle)
            self.df_5[angle] = [iangle, iangle, iangle]
        self.df_e1 = pd.DataFrame({"Freq": [1, 2, 3], "On Axis": [0, 0, 0]})
        for iangle in range(-175, 185, 10):
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
