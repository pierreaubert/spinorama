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

import unittest

import pandas as pd

from spinorama.constant_paths import MEAN_MIN, MEAN_MAX
from spinorama.compute_misc import unify_freq
from spinorama.load_misc import sort_angles, graph_melt, graph_unmelt
from spinorama.load_klippel import parse_graph_freq_klippel, parse_graphs_speaker_klippel
from spinorama.load_princeton import parse_graph_princeton
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load import filter_graphs, filter_graphs_partial, spin_compute_di_eir

# ----------------------------------------------------------------------------------------------------
# KLIPPEL FORMAT
# ----------------------------------------------------------------------------------------------------


class SpinoramaKlippelFreqLoadTests(unittest.TestCase):
    def setUp(self):
        status, (self.title, self.df) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        self.assertTrue(status)

    def test_smoke1(self):
        self.assertEqual(self.title, "CEA2034")
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn("On Axis", self.df.columns)
        self.assertNotIn("On-Axis", self.df.columns)


class SpinoramaKlippelLoadTests(unittest.TestCase):
    def setUp(self):
        status, (self.h, self.v) = parse_graphs_speaker_klippel(
            "datas/measurements", "Neumann", "Neumann KH 80", "asr-v3-20200711", None
        )
        self.assertTrue(status)

    def test_spin(self):
        self.assertEqual(self.h.shape, (194, 37))
        self.assertEqual(self.v.shape, (194, 37))


# ----------------------------------------------------------------------------------------------------
# PRINCETON FORMAT
# ----------------------------------------------------------------------------------------------------


class SpinoramaSortAnglePrincetonests(unittest.TestCase):
    def setUp(self):
        status, self.df = parse_graph_princeton(
            "datas/measurements/Genelec 8351A/princeton/Genelec8351A_V_IR.mat", "V", pd.DataFrame()
        )
        self.assertTrue(status)

    def test_sort_angles_princeton(self):
        df_sa = sort_angles(self.df)
        self.assertListEqual(list(df_sa.columns), list(self.df.columns))


class SpinoramaLoadSPLTests(unittest.TestCase):
    def setUp(self):
        status, (self.title, self.df) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)

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
        status, self.df = parse_graph_princeton(
            "datas/measurements/Genelec 8351A/princeton/Genelec8351A_V_IR.mat", "V", pd.DataFrame()
        )
        self.assertTrue(status)

    def test_smoke1(self):
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn("Freq", self.df.columns)
        self.assertIn("On Axis", self.df.columns)
        self.assertNotIn("On-Axis", self.df.columns)
        self.assertEqual(self.df.shape, (208, 2 * 18 + 1))
        self.assertLess(500, self.df.Freq.min())


# ----------------------------------------------------------------------------------------------------
# SPL TXT FORMAT
# ----------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------
# GLL TXT FORMAT
# ----------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------
# REW DUMP TXT FORMAT
# ----------------------------------------------------------------------------------------------------
class SpinoramaRewLoadTests(unittest.TestCase):
    def setUp(self):
        self.speaker_name = "BIC America Venturi DV62si"
        status, (self.title, self.df_melted) = parse_graphs_speaker_rew_text_dump(
            "datas/measurements",
            "BIC America",
            self.speaker_name,
            "",
            "vendor",
        )
        self.df_unmelted = graph_unmelt(self.df_melted)
        self.assertTrue(status)
        self.assertEqual(self.title, "CEA2034")

    def test_keys(self):
        expected_set = set(
            [
                "Freq",
                "On Axis",
                "Early Reflections",
                "Early Reflections DI",
                "Sound Power",
                # "Sound Power DI", (no data)
                "Listening Window",
                "DI Offset",
            ]
        )
        self.assertSetEqual(expected_set, set(self.df_unmelted.keys()))


# ----------------------------------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------------------------------


class SpinoramaFilterGraphsTests(unittest.TestCase):
    def setUp(self):
        status, (self.h, self.v) = parse_graphs_speaker_klippel(
            "datas/measurements", "Neumann", "Neumann KH 80", "asr-v3-20200711", None
        )
        self.assertTrue(status)
        self.df = filter_graphs("Neumann KH 80", self.h, self.v, MEAN_MIN, MEAN_MAX, "klippel", 1.0)
        self.assertIsNotNone(self.df)

    def test_keys(self):
        expected_set = set(
            [
                "SPL Horizontal",
                "SPL Horizontal_unmelted",
                "SPL Horizontal_normalized_unmelted",
                "SPL Vertical",
                "SPL Vertical_unmelted",
                "SPL Vertical_normalized_unmelted",
                "sensitivity",
                "sensitivity_distance",
                "sensitivity_1m",
                "Early Reflections_unmelted",
                "Early Reflections",
                "Horizontal Reflections_unmelted",
                "Horizontal Reflections",
                "Vertical Reflections_unmelted",
                "Vertical Reflections",
                "Estimated In-Room Response_unmelted",
                "Estimated In-Room Response",
                "On Axis_unmelted",
                "On Axis",
                "CEA2034_unmelted",
                "CEA2034",
                "CEA2034 Normalized_unmelted",
                "CEA2034 Normalized",
            ]
        )
        self.assertSetEqual(expected_set, set(self.df.keys()))


class SpinoramaFilterGraphsPartialTests(unittest.TestCase):
    def setUp(self):
        self.speaker_name = "BIC America Venturi DV62si"
        status, (self.title, self.df_melted) = parse_graphs_speaker_rew_text_dump(
            "datas/measurements",
            "BIC America",
            self.speaker_name,
            "",
            "vendor",
        )
        self.assertTrue(status)
        self.assertEqual(self.title, "CEA2034")
        self.df_unmelted = graph_melt(unify_freq(self.df_melted))
        self.df_full = spin_compute_di_eir(self.speaker_name, self.title, self.df_unmelted)
        self.df = filter_graphs_partial(self.df_full, "rew_text_dump", 1.0)
        self.assertIsNotNone(self.df)

    def test_keys(self):
        expected_set = set(
            [
                "CEA2034_unmelted",
                "sensitivity",
                "CEA2034 Normalized",
                "CEA2034 Normalized_unmelted",
                "CEA2034",
                "sensitivity_distance",
                "sensitivity_1m",
                "Estimated In-Room Response",
                "Estimated In-Room Response_unmelted",
            ]
        )
        self.assertSetEqual(expected_set, set(self.df.keys()))


if __name__ == "__main__":
    unittest.main()
