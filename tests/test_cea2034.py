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

# import os
import unittest

import numpy as np
import pandas as pd
import scipy.io

from spinorama.load import graph_melt
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.compute_cea2034 import (
    compute_cea2034,
    early_reflections,
    vertical_reflections,
    horizontal_reflections,
    estimated_inroom_hv,
)
from spinorama.auto_loss import score_loss


pd.set_option("display.max_rows", 202)


class SpinoramaSpinoramaKlippelTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        status, (self.title, self.spin_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        self.assertTrue(status)
        self.spin = graph_melt(self.spin_unmelted)
        # load spl vertical and horizontal
        status, (self.titleH, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (self.titleV, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        self.assertTrue(status)
        # computed graphs
        self.computed_spin_unmelted = compute_cea2034(self.splH, self.splV, method="standard")
        self.computed_spin = graph_melt(self.computed_spin_unmelted)

    def test_validate_cea2034(self):
        for measurement in [
            "On Axis",
            "Listening Window",
            "Sound Power",
            "Early Reflections",
        ]:
            # from klippel
            reference = self.spin.loc[self.spin["Measurements"] == measurement].reset_index(
                drop=True
            )
            # computed
            computed = self.computed_spin.loc[
                self.computed_spin["Measurements"] == measurement
            ].reset_index(drop=True)
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            print(computed.Freq, reference.Freq)
            self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            delta = (computed.dB - reference.dB).abs().max()
            # print(computed.dB - reference.dB, delta)
            # TODO(pierreaubert): that's a bit too high
            tolerance = 0.0001
            if measurement == "Early Reflections":
                # see here for explanations
                # https://www.audiosciencereview.com/forum/index.php?threads/spinorama-also-known-as-cta-cea-2034-but-that-sounds-dull-apparently.10862/
                tolerance = 1.0
            self.assertLess(delta, tolerance)


class SpinoramaEarlyReflectionsKlippelTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        status, (self.title, self.reference_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/Early Reflections.txt"
        )
        self.assertTrue(status)
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        status, (self.titleH, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (self.titleV, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        self.assertTrue(status)
        # computed graphs: use method == standard since it is an old klippel measurement
        self.computed_unmelted = early_reflections(self.splH, self.splV, method="standard")
        self.computed = graph_melt(self.computed_unmelted)

    def test_smoke(self):
        self.assertEqual(self.reference_unmelted.shape, self.computed_unmelted.shape)
        self.assertEqual(self.reference.shape, self.computed.shape)

    def test_validate_early_reflections(self):
        for measurement in [
            "Floor Bounce",
            "Ceiling Bounce",
            "Front Wall Bounce",
            "Side Wall Bounce",
            "Rear Wall Bounce",
            "Total Early Reflection",
        ]:
            # key check
            self.assertIn(measurement, self.computed_unmelted.keys())
            self.assertIn(measurement, self.reference_unmelted.keys())
            # from klippel
            reference = self.reference.loc[self.reference["Measurements"] == measurement]
            # computed
            computed = self.computed.loc[self.computed["Measurements"] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # TODO(pierreaubert): that's too high
            tolerance = 0.01
            if measurement == "Total Early Reflection":
                tolerance = 1
            self.assertLess((reference.dB - computed.dB).abs().max(), tolerance)


class SpinoramaVerticalReflectionsKlippelTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        status, (self.title, self.reference_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/Vertical Reflections.txt"
        )
        self.assertTrue(status)
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        status, (self.titleH, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (self.titleV, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        self.assertTrue(status)
        # computed graphs
        self.computed_unmelted = vertical_reflections(self.splV)
        self.computed = graph_melt(self.computed_unmelted)

    def test_smoke(self):
        self.assertEqual(self.reference_unmelted.shape, self.computed_unmelted.shape)
        self.assertEqual(self.reference.shape, self.computed.shape)

    def test_validate_vertical_reflections(self):
        for measurement in ["Floor Reflection", "Ceiling Reflection"]:
            # key check
            self.assertIn(measurement, self.computed_unmelted.keys())
            self.assertIn(measurement, self.reference_unmelted.keys())
            # from klippel
            reference = self.reference.loc[self.reference["Measurements"] == measurement]
            # computed
            computed = self.computed.loc[self.computed["Measurements"] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # 0.2 db tolerance?
            # TODO(pierreaubert): that's too high
            self.assertLess(abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.0001)


class SpinoramaHorizontalReflectionsKlippelTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        status, (self.title, self.reference_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/Horizontal Reflections.txt"
        )
        self.assertTrue(status)
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        status, (self.titleH, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (self.titleV, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        self.assertTrue(status)
        # computed graphs
        self.computed_unmelted = horizontal_reflections(self.splH)
        self.computed = graph_melt(self.computed_unmelted)

    def test_smoke(self):
        self.assertEqual(self.reference_unmelted.shape, self.computed_unmelted.shape)
        self.assertEqual(self.reference.shape, self.computed.shape)

    def test_validate_vertical_reflections(self):
        for measurement in ["Rear", "Side", "Front"]:
            # key check
            self.assertIn(measurement, self.computed_unmelted.keys())
            self.assertIn(measurement, self.reference_unmelted.keys())
            # from klippel
            reference = self.reference.loc[self.reference["Measurements"] == measurement]
            # computed
            computed = self.computed.loc[self.computed["Measurements"] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            self.assertLess(abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.0001)


class SpinoramaEstimatedInRoomKlippelTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        status, (self.title, self.reference_unmelted) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/Estimated In-Room Response.txt"
        )
        self.assertTrue(status)
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        status, (self.titleH, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.assertTrue(status)
        status, (self.titleV, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        self.assertTrue(status)
        # computed graphs
        self.computed_unmelted = estimated_inroom_hv(self.splH, self.splV, "standard")
        self.computed = graph_melt(self.computed_unmelted)

    def test_smoke(self):
        self.assertEqual(self.reference_unmelted.shape, self.computed_unmelted.shape)
        self.assertEqual(self.reference.shape, self.computed.shape)

    # See above. We diverge from the std (since it has a but for rear which impact ER and PIR)
    def test_validate_estimated_inroom(self):
        # key check
        self.assertIn("Estimated In-Room Response", self.computed_unmelted.keys())
        self.assertIn("Estimated In-Room Response", self.reference_unmelted.keys())
        # from klippel
        reference = self.reference.loc[
            self.reference["Measurements"] == "Estimated In-Room Response"
        ]
        # computed
        computed = self.computed.loc[self.computed["Measurements"] == "Estimated In-Room Response"]
        # should have the same Freq
        self.assertEqual(computed.Freq.size, reference.Freq.size)
        self.assertTrue(computed.Freq.eq(reference.Freq).all())
        # and should be equal or close in dB
        self.assertLess(abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.02)


class SpinoramaSpinoramaCorrectedERTests(unittest.TestCase):
    SPEAKERNAME = "Donner Dyna 4"

    def setUp(self):
        # load spl vertical and horizontal
        status, (self.titleH, self.splH) = parse_graph_freq_klippel(
            "datas/measurements/{}/asr/SPL Horizontal.txt".format(self.SPEAKERNAME)
        )
        self.assertTrue(status)
        status, (self.titleV, self.splV) = parse_graph_freq_klippel(
            "datas/measurements/{}/asr/SPL Vertical.txt".format(self.SPEAKERNAME)
        )
        self.assertTrue(status)
        # computed graphs
        self.computed_spin_unmelted = compute_cea2034(self.splH, self.splV, method="corrected")
        self.computed_spin = graph_melt(self.computed_spin_unmelted)
        # compute PIR
        self.computed_pir = estimated_inroom_hv(
            h_spl=self.splH, v_spl=self.splV, method="corrected"
        )
        # load mat file generated by Maiky's octave script
        mat = scipy.io.loadmat("./tests/datas/{}.mat".format(self.SPEAKERNAME))
        self.reference = {}
        for key, index in (
            ("Freq", 0),
            ("On Axis", 1),
            ("Listening Window", 2),
            ("Early Reflections", 3),
            ("Sound Power", 5),
            ("Estimated In-Room Response", 4),
            ("SPDI", 6),
            ("ERDI", 7),
            ("DI", 8),
        ):
            self.reference[key] = mat["Spininorama_corrected_F_ON_LW_ER_PIR_SP_SPDI_ERDI_DIoffset"][
                0
            ][0][0].T[index]
        # get data from Cython code
        self.df_spin = {
            "SPL Horizontal_unmelted": self.splH,
            "SPL Vertical_unmelted": self.splV,
        }

    def test_validate_cea2034(self):
        for measurement in [
            "On Axis",
            "Listening Window",
            "Sound Power",
            "Early Reflections",
        ]:
            # from klippel
            mreference = self.reference[measurement]
            # computed
            computed = self.computed_spin.loc[
                self.computed_spin["Measurements"] == measurement
            ].reset_index(drop=True)
            # should have the same Freq
            self.assertEqual(computed.Freq.size, len(self.reference["Freq"]))
            delta = np.max(np.abs(computed.Freq.to_numpy() - self.reference["Freq"]))
            tolerance = 1.0e-7
            self.assertLess(delta, tolerance)
            # same for spl
            computed_mean = np.mean(computed.dB)
            reference_mean = np.mean(mreference)
            delta = (computed.dB - computed_mean - mreference + reference_mean).abs().max()
            tolerance = 2 * 1.0e-7
            # print("processing {}".format(measurement))
            # print(computed.dB - computed_mean - mreference + reference_mean)
            self.assertLess(delta, tolerance)
        # now testing PIR
        computed_pir = self.computed_pir["Estimated In-Room Response"]
        reference_pir = self.reference["Estimated In-Room Response"]
        computed_pir_mean = np.mean(computed_pir)
        reference_pir_mean = np.mean(reference_pir)
        delta = (computed_pir - computed_pir_mean - reference_pir + reference_pir_mean).abs().max()
        tolerance = 2 * 1.0e-7
        self.assertLess(delta, tolerance)

    def test_validate_cython(self):
        empty_eq = ()
        _ = score_loss(self.df_spin, empty_eq)
        self.assertIn("pre_computed", self.df_spin.keys())
        cython = {
            "Freq": self.df_spin["pre_computed"]["freq"],
            "On Axis": self.df_spin["pre_computed"]["on"],
            "Listening Window": self.df_spin["pre_computed"]["spin"][0],
            "Early Reflections": self.df_spin["pre_computed"]["spin"][1],
            "Sound Power": self.df_spin["pre_computed"]["spin"][14],
            "Estimated In-Room Response": self.df_spin["pre_computed"]["spin"][15],
        }
        #
        for measurement in [
            "On Axis",
            "Listening Window",
            "Sound Power",
            "Early Reflections",
        ]:
            # from klippel
            mreference = self.reference[measurement]
            # computed
            computed = cython[measurement]
            # should have the same Freq
            self.assertEqual(len(cython["Freq"]), len(self.reference["Freq"]))
            delta = np.max(np.abs(cython["Freq"] - self.reference["Freq"]))
            tolerance = 1.0e-7
            self.assertLess(delta, tolerance)
            # same for spl
            computed_mean = np.mean(computed)
            reference_mean = np.mean(mreference)
            delta = np.max(np.abs((computed - computed_mean - mreference + reference_mean)))
            tolerance = 2 * 1.0e-7
            self.assertLess(delta, tolerance)
        # now testing PIR
        computed_pir = cython["Estimated In-Room Response"]
        reference_pir = self.reference["Estimated In-Room Response"]
        computed_pir_mean = np.mean(computed_pir)
        reference_pir_mean = np.mean(reference_pir)
        delta = np.max(
            np.abs(computed_pir - computed_pir_mean - reference_pir + reference_pir_mean)
        )
        tolerance = 2 * 1.0e-7
        self.assertLess(delta, tolerance)

    def test_validate_cython2(self):
        # testing cache effect
        self.test_validate_cython()
        self.test_validate_cython()
        self.test_validate_cython()


class SpinoramaSpinoramaCorrectedERTestsMLMB10(SpinoramaSpinoramaCorrectedERTests):
    SPEAKERNAME = "MartinLogan Motion B10"


if __name__ == "__main__":
    unittest.main()
