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

import logging
import unittest
import warnings

import pandas as pd

from spinorama.load import parse_graphs_speaker  # , parse_eq_speaker
from spinorama.measurements import Measurements
from tests.test_common import _count_filled

from spinorama.speaker import (
    display_spinorama,
    display_spinorama_normalized,
    display_onaxis,
    display_inroom,
    display_inroom_normalized,
    display_reflection_early,
    display_reflection_horizontal,
    display_reflection_vertical,
    display_spl_horizontal,
    display_spl_vertical,
    display_spl_horizontal_normalized,
    display_spl_vertical_normalized,
    display_contour_horizontal,
    display_contour_vertical,
    display_contour_horizontal_normalized,
    display_contour_vertical_normalized,
    display_contour_horizontal_3d,
    display_contour_vertical_3d,
    display_contour_horizontal_normalized_3d,
    display_contour_vertical_normalized_3d,
    display_radar_horizontal,
    display_radar_vertical,
)

from spinorama.plot import (
    plot_params_default,
    contour_params_default,
    radar_params_default,
)


class SpinoramaDisplayTests(unittest.TestCase):
    def setUp(self):
        self.dfs_full = {}
        self.dfs_limited = {}
        self.dfs_partial = {}
        self.log_level = logging.INFO

        parameters = {
            "mformat": "klippel",
            "morigin": "ErinsAudioCorner",
            "mversion": "eac",
            "msymmetry": "None",
            "mparameters": None,
            "distance": 1.0,
            "shape": "bookshelves",
        }
        self.dfs_full["klippel_eac"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="Neumann",
            speaker_name="Neumann KH 80",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

        parameters = {
            "mformat": "klippel",
            "morigin": "ASR",
            "mversion": "asr-vertical",
            "msymmetry": "None",
            "mparameters": None,
            "distance": 1.0,
            "shape": "bookshelves",
        }
        self.dfs_full["klippel_asr"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="Genelec",
            speaker_name="Genelec 8341A",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

        parameters = {
            "mformat": "princeton",
            "morigin": "princeton",
            "mversion": "princeton",
            "msymmetry": "None",
            "mparameters": None,
            "distance": 1.0,
            "shape": "bookshelves",
        }
        self.dfs_limited["princeton"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="Genelec",
            speaker_name="Genelec 8351A",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

        parameters = {
            "mformat": "spl_hv_txt",
            "morigin": "Misc",
            "mversion": "misc-ageve",
            "msymmetry": "vertical",
            "mparameters": None,
            "distance": 1.0,
            "shape": "bookshelves",
        }
        self.dfs_full["spl_hv_txt"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="Andersson",
            speaker_name="Andersson HIS 2.1",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

        parameters = {
            "mformat": "gll_hv_txt",
            "morigin": "Vendors-RCF",
            "mversion": "vendor-pattern-90x70",
            "msymmetry": "None",
            "mparameters": None,
            "distance": 10.0,
            "shape": "liveportable",
        }
        self.dfs_full["gll_hv_txt"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="RCF",
            speaker_name="RCF ART 708-A MK4",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

        parameters = {
            "mformat": "rew_text_dump",
            "morigin": "Vendors-BIC America",
            "mversion": "vendor",
            "msymmetry": "None",
            "mparameters": None,
            "distance": 10.0,
            "shape": "floorstanders",
        }
        self.dfs_partial["rew_text_dump"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="BIC America",
            speaker_name="BIC America Venturi DV62si",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

        parameters = {
            "mformat": "webplotdigitizer",
            "morigin": "Vendors-Revel",
            "mversion": "vendor",
            "msymmetry": "None",
            "mparameters": None,
            "distance": 10.0,
            "shape": "floorstanders",
        }
        self.dfs_partial["webplotdigitizer"] = parse_graphs_speaker(
            speaker_path="datas/measurements",
            speaker_brand="Revel",
            speaker_name="Revel F208",
            speaker_parameters=parameters,
            log_level=self.log_level,
        )

    _FULL_DISPLAYS = (
        display_spinorama,
        display_spinorama_normalized,
        display_onaxis,
        display_inroom,
        display_inroom_normalized,
        display_reflection_early,
        display_reflection_horizontal,
        display_reflection_vertical,
        display_spl_horizontal,
        display_spl_vertical,
        display_spl_horizontal_normalized,
        display_spl_vertical_normalized,
    )
    _CONTOUR_DISPLAYS = (
        display_contour_horizontal,
        display_contour_horizontal_normalized,
        display_contour_horizontal_3d,
        display_contour_horizontal_normalized_3d,
        display_contour_vertical,
        display_contour_vertical_normalized,
        display_contour_vertical_3d,
        display_contour_vertical_normalized_3d,
    )
    _RADAR_DISPLAYS = (display_radar_horizontal, display_radar_vertical)
    _LIMITED_DISPLAYS = (
        display_onaxis,
        display_spl_horizontal,
        display_spl_vertical,
        display_spl_horizontal_normalized,
        display_spl_vertical_normalized,
    )
    _PARTIAL_DISPLAYS = (
        display_spinorama,
        display_spinorama_normalized,
        display_onaxis,
        display_inroom,
        display_inroom_normalized,
    )

    def test_dfs_full(self):
        for m in self.dfs_full.values():
            self.assertIsNotNone(m)
            self.assertEqual(_count_filled(m), 13)
            for op_call in self._FULL_DISPLAYS:
                self.assertIsNotNone(op_call(m, plot_params_default))
            for op_call in self._CONTOUR_DISPLAYS:
                self.assertIsNotNone(op_call(m, contour_params_default))
            for op_call in self._RADAR_DISPLAYS:
                self.assertIsNotNone(op_call(m, radar_params_default))

    def test_dfs_limited(self):
        for m in self.dfs_limited.values():
            self.assertIsNotNone(m)
            self.assertEqual(_count_filled(m), 6)
            for op_call in self._LIMITED_DISPLAYS:
                self.assertIsNotNone(op_call(m, plot_params_default))
            for op_call in self._CONTOUR_DISPLAYS:
                self.assertIsNotNone(op_call(m, contour_params_default))
            for op_call in self._RADAR_DISPLAYS:
                self.assertIsNotNone(op_call(m, radar_params_default))

    def test_dfs_partial(self):
        for m in self.dfs_partial.values():
            self.assertIsNotNone(m)
            # cea2034 + normalized + on_axis + eir + normalized + sensitivity
            self.assertEqual(_count_filled(m), 6)
            for op_call in self._PARTIAL_DISPLAYS:
                self.assertIsNotNone(op_call(m, plot_params_default))

        # Full measurements should also satisfy the partial set of displays.
        for m in self.dfs_full.values():
            self.assertIsNotNone(m)
            for op_call in self._PARTIAL_DISPLAYS:
                self.assertIsNotNone(op_call(m, plot_params_default))


if __name__ == "__main__":
    unittest.main()
