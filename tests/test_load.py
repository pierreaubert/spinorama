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
import unittest

import pandas as pd

from spinorama.misc import (
    graph_unmelt,
    measurements_complete_freq,
    measurements_complete_spl,
    measurements_valid_freq_range,
    sort_angles,
)
from spinorama.load_klippel import parse_graph_freq_klippel, parse_graphs_speaker_klippel
from spinorama.load_princeton import parse_graph_princeton, parse_graphs_speaker_princeton
from spinorama.load_spl_hv_txt import parse_graphs_speaker_spl_hv_txt
from spinorama.load_gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from spinorama.load import (
    symmetrise_speaker_measurements,
)
from tests.test_common import (
    parse_full_each_format,
    EXPECTED_FULL_SET,
    EXPECTED_PARTIAL_SET,
    EXPECTED_LIMITED_SET,
    parse_partial_each_format,
)

# ----------------------------------------------------------------------------------------------------
# KLIPPEL FORMAT PRE COMPUTED CEA2034
# ----------------------------------------------------------------------------------------------------


class SpinoramaKlippelCEA2034LoadTests(unittest.TestCase):
    def setUp(self):
        status, (self.title, self.df) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        self.assertTrue(status)

    def test_smoke1(self):
        self.assertEqual(self.title, "CEA2034")
        self.assertIsNotNone(self.df)

    def test_keys(self):
        self.assertNotIn("On-Axis", self.df.columns)
        self.assertNotIn("Early Reflextions", self.df.columns)
        self.assertNotIn("Predicted In-Room Response", self.df.columns)

    def test_most_graphs(self):
        self.assertIn("On Axis", self.df.columns)
        self.assertIn("Listening Window", self.df.columns)
        self.assertIn("Early Reflections", self.df.columns)
        self.assertIn("Sound Power", self.df.columns)
        self.assertIn("Early Reflections DI", self.df.columns)
        self.assertIn("Sound Power DI", self.df.columns)


# ----------------------------------------------------------------------------------------------------
# KLIPPEL FORMAT H/V
# ----------------------------------------------------------------------------------------------------


class SpinoramaKlippeHVLoadTests(unittest.TestCase):
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


class SpinoramaPrincetonSortAngleTests(unittest.TestCase):
    def setUp(self):
        status, self.df = parse_graph_princeton(
            "datas/measurements/Genelec 8351A/princeton/Genelec8351A_V_IR.mat", "V", pd.DataFrame()
        )
        self.assertTrue(status)

    def test_sort_angles_princeton(self):
        df_sa = sort_angles(self.df)
        self.assertListEqual(list(df_sa.columns), list(self.df.columns))


class SpinoramaPrincetonLoadMatTests(unittest.TestCase):
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


class SpinoramaPrincetonLoadTests(unittest.TestCase):
    def setUp(self):
        status, (self.h, self.v) = parse_graphs_speaker_princeton(
            "datas/measurements", "Genelec", "Genelec 8351A", "princeton", None
        )
        self.assertTrue(status)

    def test_spin(self):
        # horizontal symmetry
        self.assertEqual(self.h.shape, (208, 20))
        self.assertEqual(self.v.shape, (208, 37))


# ----------------------------------------------------------------------------------------------------
# SPL TXT FORMAT
# ----------------------------------------------------------------------------------------------------
class SpinoramaSPLHVLoadTests(unittest.TestCase):
    def setUp(self):
        status, (self.h, self.v) = parse_graphs_speaker_spl_hv_txt(
            "datas/measurements", "Andersson", "Andersson HIS 2.1", "misc-ageve"
        )
        self.assertTrue(status)

    def test_spin(self):
        # vertical symmetry
        self.assertEqual(self.h.shape, (479, 38))
        self.assertEqual(self.v.shape, (479, 21))
        self.assertTrue(measurements_complete_freq(self.h, self.v))
        self.assertFalse(measurements_complete_spl(self.h, self.v))

    def test_symmetry(self):
        # vertical symmetry
        h2, v2 = symmetrise_speaker_measurements(self.h, self.v, "vertical")
        self.assertIsNotNone(h2)
        self.assertIsNotNone(v2)
        if h2 is not None:
            self.assertEqual(h2.shape, (479, 38))
        if v2 is not None:
            self.assertEqual(v2.shape, (479, 38))
        if h2 is not None and v2 is not None:
            self.assertTrue(measurements_complete_spl(h2, v2))


# ----------------------------------------------------------------------------------------------------
# GLL TXT FORMAT
# ----------------------------------------------------------------------------------------------------
class SpinoramaGLLHVLoadTests(unittest.TestCase):
    def setUp(self):
        status, (self.h, self.v) = parse_graphs_speaker_gll_hv_txt(
            "datas/measurements", "RCF ART 708-A MK4", "vendor-pattern-90x70"
        )
        self.assertTrue(status)

    def test_spin(self):
        # vertical symmetry
        self.assertEqual(self.h.shape, (236, 37))
        self.assertEqual(self.v.shape, (236, 37))


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
# WEBPLOTDIGITIZER TAR FORMAT
# ----------------------------------------------------------------------------------------------------
class SpinoramaWebPlotDigitizerLoadTests(unittest.TestCase):
    def setUp(self):
        self.speaker_name = "RBH Sound R-5"
        status, (self.title, self.df_melted) = parse_graphs_speaker_webplotdigitizer(
            "datas/measurements",
            "RBH Sound",
            self.speaker_name,
            "",
            "misc-audioholics",
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
                "Sound Power DI",
                "Listening Window",
                # "DI Offset",
            ]
        )
        self.assertSetEqual(expected_set, set(self.df_unmelted.keys()))


# ----------------------------------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------------------------------


class SpinoramaFilterGraphsTests(unittest.TestCase):
    def setUp(self):
        self.dfs = parse_full_each_format()

    def test_keys(self):
        for res in self.dfs.values():
            full, df = res["full"], res["graphs"]
            if full:
                self.assertSetEqual(EXPECTED_FULL_SET, set(df.keys()))
            else:
                self.assertSetEqual(EXPECTED_LIMITED_SET, set(df.keys()))

    def test_freq_ranges(self):
        expected_freq_range = {
            "Neumann KH 80": (20, 20000),
            "Genelec 8351A": (500, 20000),
            "RCF ART 708-A MK4": (100, 16000),
            "Andersson HIS 2.1": (20, 20000),
        }
        for res in self.dfs.values():
            speaker_name = res["speaker_name"]
            valid_freq_range = measurements_valid_freq_range(
                speaker_name=speaker_name,
                version=res["speaker_version"],
                h_spl=res["h_spl"],
                v_spl=res["v_spl"],
            )
            min_error = (
                math.fabs(valid_freq_range[0] - expected_freq_range[speaker_name][0])
                / expected_freq_range[speaker_name][0]
                * 100.0
            )
            max_error = (
                math.fabs(valid_freq_range[1] - expected_freq_range[speaker_name][1])
                / expected_freq_range[speaker_name][1]
                * 100.0
            )
            self.assertLess(min_error, 5)  # 5%
            self.assertLess(max_error, 5)  # 5%


class SpinoramaFilterGraphsPartialTests(unittest.TestCase):
    def setUp(self):
        self.dfs = parse_partial_each_format()

    def test_keys(self):
        for df in self.dfs.values():
            self.assertSetEqual(EXPECTED_PARTIAL_SET, set(df.keys()))


if __name__ == "__main__":
    unittest.main()
