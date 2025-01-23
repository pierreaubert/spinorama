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
import time
import unittest
import warnings

import pandas as pd

from spinorama.load import parse_graphs_speaker, parse_eq_speaker

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

import ray


class SpinoramaKlippelParseTests(unittest.TestCase):
    def setUp(self):
        self.dfs_full = {}
        self.dfs_partial = {}
        if not ray.is_initialized():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                ray.init(num_cpus=1, include_dashboard=False)

        self.dfs_full["klippel_eac"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="Neumann",
                speaker_name="Neumann KH 80",
                mformat="klippel",
                morigin="ErinsAudioCorner",
                mversion="eac",
                msymmetry="None",
                mparameters=None,
                level=logging.INFO,
                distance=1.0,
            )
        )

        self.dfs_full["klippel_asr"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="Genelec",
                speaker_name="Genelec 8341A",
                mformat="klippel",
                morigin="ASR",
                mversion="asr-vertical",
                msymmetry="None",
                mparameters=None,
                level=logging.INFO,
                distance=1.0,
            )
        )

        self.dfs_full["princeton"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="Genelec",
                speaker_name="Genelec 8351A",
                mformat="princeton",
                morigin="princeton",
                mversion="princeton",
                msymmetry="None",
                mparameters=None,
                level=logging.INFO,
                distance=1.0,
            )
        )

        self.dfs_full["spl_hv_txt"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="Andersson",
                speaker_name="Andersson HIS 2.1",
                mformat="spl_hv_txt",
                morigin="Misc",
                mversion="misc-ageve",
                msymmetry="Vertical",
                mparameters=None,
                level=logging.INFO,
                distance=1.0,
            )
        )

        self.dfs_full["gll_hv_txt"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="RCF",
                speaker_name="RCF ART 708-A MK4",
                mformat="gll_hv_txt",
                morigin="Vendors-RCF",
                mversion="vendor-pattern-90x70",
                msymmetry="None",
                mparameters=None,
                level=logging.INFO,
                distance=10.0,
            )
        )

        self.dfs_partial["rew_text_dump"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="BIC America",
                speaker_name="BIC America Venturi DV62si",
                mformat="rew_text_dump",
                morigin="Vendors-BIC America",
                mversion="vendor",
                msymmetry="None",
                mparameters=None,
                level=logging.INFO,
                distance=10.0,
            )
        )

        self.dfs_partial["webplotdigitizer"] = ray.get(
            parse_graphs_speaker.remote(
                speaker_path="datas/measurements",
                speaker_brand="Revel",
                speaker_name="Revel F208",
                mformat="webplotdigitizer",
                morigin="Vendors-Revel",
                mversion="vendor",
                msymmetry="None",
                mparameters=None,
                level=logging.INFO,
                distance=10.0,
            )
        )

        # while True:
        #     ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)
        #     if remaining_ids == 0:
        #         break
        #     time.sleep(1)

        if ray.is_initialized():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                ray.shutdown()

    def test_dfs_full(self):
        full_set = set(
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
                "Estimated In-Room Response Normalized_unmelted",
                "Estimated In-Room Response Normalized",
                "On Axis_unmelted",
                "On Axis",
                "CEA2034_unmelted",
                "CEA2034",
                "CEA2034 Normalized_unmelted",
                "CEA2034 Normalized",
            ]
        )
        for method, df in self.dfs_full.items():
            self.assertIsNotNone(df)
            self.assertSetEqual(full_set, set(df.keys()))

            for k in df.keys():
                if isinstance(df[k], pd.DataFrame):
                    if "_unmelted" in k:
                        self.assertIn("Freq", df[k])
                    else:
                        self.assertIn("Freq", df[k])
                        self.assertIn("Measurements", df[k])
                        self.assertIn("dB", df[k])

            # check all spin graphs
            for op_title, op_call in (
                ("CEA2034", display_spinorama),
                ("CEA2034 Normalized", display_spinorama_normalized),
                ("On Axis", display_onaxis),
                ("Estimated In-Room Response", display_inroom),
                ("Estimated In-Room Response Normalized", display_inroom_normalized),
                ("Early Reflections", display_reflection_early),
                ("Horizontal Reflections", display_reflection_horizontal),
                ("Vertical Reflections", display_reflection_vertical),
                ("SPL Horizontal", display_spl_horizontal),
                ("SPL Vertical", display_spl_vertical),
                ("SPL Horizontal Normalized", display_spl_horizontal_normalized),
                ("SPL Vertical Normalized", display_spl_vertical_normalized),
            ):
                graph = op_call(df, plot_params_default)
                self.assertIsNotNone(graph)

            # check all contour graphs
            for op_title, op_call in (
                ("SPL Horizontal Contour", display_contour_horizontal),
                ("SPL Horizontal Contour Normalized", display_contour_horizontal_normalized),
                ("SPL Horizontal Contour 3D", display_contour_horizontal_3d),
                ("SPL Horizontal Contour Normalized 3D", display_contour_horizontal_normalized_3d),
                ("SPL Vertical Contour", display_contour_vertical),
                ("SPL Vertical Contour Normalized", display_contour_vertical_normalized),
                ("SPL Vertical Contour 3D", display_contour_vertical_3d),
                ("SPL Vertical Contour Normalized 3D", display_contour_vertical_normalized_3d),
            ):
                graph = op_call(df, contour_params_default)
                self.assertIsNotNone(graph)

            # check all radar graphs
            for op_title, op_call in (
                ("SPL Horizontal Radar", display_radar_horizontal),
                ("SPL Vertical Radar", display_radar_vertical),
            ):
                graph = op_call(df, radar_params_default)
                self.assertIsNotNone(graph)

    def test_dfs_partial(self):
        partial_set = set(
            [
                "sensitivity",
                "sensitivity_distance",
                "sensitivity_1m",
                "Estimated In-Room Response_unmelted",
                "Estimated In-Room Response",
                "Estimated In-Room Response Normalized_unmelted",
                "Estimated In-Room Response Normalized",
                "On Axis_unmelted",
                "On Axis",
                "CEA2034_unmelted",
                "CEA2034",
                "CEA2034 Normalized_unmelted",
                "CEA2034 Normalized",
            ]
        )
        for method, df in self.dfs_partial.items():
            self.assertIsNotNone(df)
            self.assertSetEqual(partial_set, set(df.keys()))

        for method, df in self.dfs_full.items():
            self.assertIsNotNone(df)
            # Full measurements should contain all partial measurements plus additional ones
            self.assertTrue(
                partial_set.issubset(set(df.keys())),
                f"Full measurements should contain all partial measurements. Missing: {partial_set - set(df.keys())}",
            )

            for k in df.keys():
                if isinstance(df[k], pd.DataFrame):
                    if "_unmelted" in k:
                        self.assertIn("Freq", df[k])
                    else:
                        self.assertIn("Freq", df[k])
                        self.assertIn("Measurements", df[k])
                        self.assertIn("dB", df[k])

            # check all spin graphs
            for op_title, op_call in (
                ("CEA2034", display_spinorama),
                ("CEA2034 Normalized", display_spinorama_normalized),
                ("On Axis", display_onaxis),
                ("Estimated In-Room Response", display_inroom),
                ("Estimated In-Room Response Normalized", display_inroom_normalized),
            ):
                graph = op_call(df, plot_params_default)
                self.assertIsNotNone(graph)


if __name__ == "__main__":
    unittest.main()
