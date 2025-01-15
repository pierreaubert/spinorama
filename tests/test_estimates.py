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

# import os
import unittest
import pandas as pd
from spinorama.misc import graph_melt
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.load_gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.compute_estimates import estimates, compute_sensitivity


pd.set_option("display.max_rows", 202)


class SpinoramaEstimatesNV2Tests(unittest.TestCase):
    def setUp(self):
        status, (self.title, self.df_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v2-20200208/CEA2034.txt"
        )
        self.assertTrue(status)
        self.df = graph_melt(self.df_unmelted)
        self.estimates = estimates(self.df, pd.DataFrame(), pd.DataFrame())

    def test_estimates(self):
        self.assertNotEqual(-1, self.estimates["ref_level"])
        self.assertNotEqual(-1, self.estimates["ref_3dB"])
        self.assertNotEqual(-1, self.estimates["ref_6dB"])
        self.assertNotEqual(-1, self.estimates["ref_band"])
        #
        self.assertAlmostEqual(self.estimates["ref_level"], 105.9)
        self.assertAlmostEqual(self.estimates["ref_3dB"], 58.6)  # Hz
        self.assertAlmostEqual(self.estimates["ref_6dB"], 54.2)  # Hz
        self.assertAlmostEqual(self.estimates["ref_band"], 1.6)  # deviation in dB


class SpinoramaEstimatesNV3Tests(unittest.TestCase):
    def setUp(self):
        status, (self.title, self.spin_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        self.assertTrue(status)
        self.spin = graph_melt(self.spin_unmelted)
        status, (_, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (_, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        self.assertTrue(status)
        self.estimates = estimates(self.spin, self.splH, self.splV)

    def test_estimates(self):
        self.assertNotEqual(-1, self.estimates["ref_level"])
        self.assertNotEqual(-1, self.estimates["ref_3dB"])
        self.assertNotEqual(-1, self.estimates["ref_6dB"])
        self.assertNotEqual(-1, self.estimates["ref_band"])
        #
        self.assertAlmostEqual(self.estimates["ref_level"], 80.8)
        self.assertAlmostEqual(self.estimates["ref_3dB"], 58.6)  # Hz
        self.assertAlmostEqual(self.estimates["ref_6dB"], 52.7)  # Hz
        self.assertAlmostEqual(self.estimates["ref_band"], 1.4)  # deviation in dB

    def test_directivity(self):
        self.assertAlmostEqual(self.estimates["dir_horizontal_p"], 50)
        self.assertAlmostEqual(self.estimates["dir_horizontal_m"], -50)
        self.assertAlmostEqual(self.estimates["dir_vertical_p"], 40)
        self.assertAlmostEqual(self.estimates["dir_vertical_m"], -40)


class SpinoramaEstimatesNV4Tests(unittest.TestCase):
    def setUp(self):
        status, (self.title, self.spin_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Revel C52/asr-vertical/CEA2034.txt"
        )
        self.assertTrue(status)
        self.spin = graph_melt(self.spin_unmelted)
        status, (_, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Revel C52/asr-vertical/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (_, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Revel C52/asr-vertical/SPL Vertical.txt"
        )
        self.assertTrue(status)
        self.estimates = estimates(self.spin, self.splH, self.splV)

    def test_estimates(self):
        self.assertNotEqual(-1, self.estimates["ref_level"])
        self.assertNotEqual(-1, self.estimates["ref_3dB"])
        self.assertNotEqual(-1, self.estimates["ref_6dB"])
        self.assertNotEqual(-1, self.estimates["ref_band"])
        #
        self.assertAlmostEqual(self.estimates["ref_level"], 88.9)
        self.assertAlmostEqual(self.estimates["ref_3dB"], 76.9)  # Hz
        self.assertAlmostEqual(self.estimates["ref_6dB"], 62.3)  # Hz
        self.assertAlmostEqual(self.estimates["ref_band"], 3.0)  # deviation in dB

    def test_directivity(self):
        self.assertAlmostEqual(self.estimates["dir_horizontal_p"], 50)
        self.assertAlmostEqual(self.estimates["dir_horizontal_m"], -50)
        self.assertAlmostEqual(self.estimates["dir_vertical_p"], 40)
        self.assertAlmostEqual(self.estimates["dir_vertical_m"], -20)


class SpinoramaEstimatesSensitivityGLLTests(unittest.TestCase):
    def test_1(self):
        status, (self.title, self.df_unmelted) = parse_graphs_speaker_gll_hv_txt(
            speaker_path="datas/measurements",
            speaker_name="Danley SH-50",
            version="vendor-pattern-50x50",
        )
        self.assertTrue(status)
        self.sensitivity, self.sensitivity_1m = compute_sensitivity(
            self.df_unmelted, "gll_hv_txt", 10.0
        )
        self.assertAlmostEqual(self.sensitivity, 81, delta=1)
        self.assertAlmostEqual(self.sensitivity_1m, 101, delta=1)

    def test_2(self):
        status, (self.title, self.df_unmelted) = parse_graphs_speaker_gll_hv_txt(
            speaker_path="datas/measurements",
            speaker_name="Martin Audio Flexpoint FP12",
            version="vendor",
        )
        self.assertTrue(status)
        self.sensitivity, self.sensitivity_1m = compute_sensitivity(
            self.df_unmelted, "gll_hv_txt", 10.0
        )
        self.assertAlmostEqual(self.sensitivity, 76.8, delta=1)
        self.assertAlmostEqual(self.sensitivity_1m, 96.8, delta=1)


if __name__ == "__main__":
    unittest.main()
