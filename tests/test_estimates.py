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

# import os
import unittest
import pandas as pd
from spinorama.load import graph_melt
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.compute_estimates import estimates


pd.set_option("display.max_rows", 202)


class SpinoramaEstimatesNV2Tests(unittest.TestCase):
    def setUp(self):
        self.title, self.df_unmelted = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v2-20200208/CEA2034.txt"
        )
        self.df = graph_melt(self.df_unmelted)
        self.estimates = estimates(self.df, None, None)

    def test_estimates(self):
        self.assertNotEqual(-1, self.estimates["ref_level"])
        self.assertNotEqual(-1, self.estimates["ref_3dB"])
        self.assertNotEqual(-1, self.estimates["ref_6dB"])
        self.assertNotEqual(-1, self.estimates["ref_band"])
        #
        self.assertAlmostEqual(self.estimates["ref_level"], 105.9)
        self.assertAlmostEqual(self.estimates["ref_3dB"], 58.6)  # Hz
        self.assertAlmostEqual(self.estimates["ref_6dB"], 54.2)  # Hz
        self.assertAlmostEqual(self.estimates["ref_band"], 1.9)  # deviation in dB


class SpinoramaEstimatesNV3Tests(unittest.TestCase):
    def setUp(self):
        self.title, self.spin_unmelted = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        self.spin = graph_melt(self.spin_unmelted)
        _, self.splH = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        _, self.splV = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
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
        self.assertAlmostEqual(self.estimates["dir_horizontal_m"], -60)
        self.assertAlmostEqual(self.estimates["dir_vertical_p"], 40)
        self.assertAlmostEqual(self.estimates["dir_vertical_m"], -40)


class SpinoramaEstimatesNV4Tests(unittest.TestCase):
    def setUp(self):
        self.title, self.spin_unmelted = parse_graph_freq_klippel(
            "datas/measurements/Revel C52/asr-vertical/CEA2034.txt"
        )
        self.spin = graph_melt(self.spin_unmelted)
        _, self.splH = parse_graph_freq_klippel(
            "datas/measurements/Revel C52/asr-vertical/SPL Horizontal.txt"
        )
        _, self.splV = parse_graph_freq_klippel(
            "datas/measurements/Revel C52/asr-vertical/SPL Vertical.txt"
        )
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
        self.assertAlmostEqual(self.estimates["dir_horizontal_p"], 70)
        self.assertAlmostEqual(self.estimates["dir_horizontal_m"], -80)
        self.assertAlmostEqual(self.estimates["dir_vertical_p"], 40)
        self.assertAlmostEqual(self.estimates["dir_vertical_m"], -20)


if __name__ == "__main__":
    unittest.main()
