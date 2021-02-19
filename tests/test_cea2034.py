# import os
import unittest
import pandas as pd
from spinorama.load import graph_melt
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.compute_cea2034 import (
    compute_cea2034,
    early_reflections,
    vertical_reflections,
    horizontal_reflections,
    estimated_inroom_HV,
)


pd.set_option("display.max_rows", 202)


class SpinoramaSpinoramaTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        self.title, self.spin_unmelted = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/CEA2034.txt"
        )
        self.spin = graph_melt(self.spin_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.titleV, self.splV = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        # computed graphs
        self.computed_spin_unmelted = compute_cea2034(self.splH, self.splV)
        self.computed_spin = graph_melt(self.computed_spin_unmelted)

    def test_validate_cea2034(self):
        for measurement in [
            "On Axis",
            "Listening Window",
            "Sound Power",
        ]:  # , 'Early Reflections']:
            # from klippel
            reference = self.spin.loc[
                self.spin["Measurements"] == measurement
            ].reset_index(drop=True)
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
            print(computed.dB - reference.dB, delta)
            # TODO(pierreaubert): that's a bit too high
            self.assertLess(delta, 0.0001)


class SpinoramaEarlyReflectionsTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/Early Reflections.txt"
        )
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.titleV, self.splV = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        # computed graphs
        self.computed_unmelted = early_reflections(self.splH, self.splV)
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
            reference = self.reference.loc[
                self.reference["Measurements"] == measurement
            ]
            # computed
            computed = self.computed.loc[self.computed["Measurements"] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # TODO(pierreaubert): that's too high
            self.assertLess(
                abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.02
            )


class SpinoramaVerticalReflectionsTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/Vertical Reflections.txt"
        )
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.titleV, self.splV = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        # computed graphs
        self.computed_unmelted = vertical_reflections(self.splH, self.splV)
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
            reference = self.reference.loc[
                self.reference["Measurements"] == measurement
            ]
            # computed
            computed = self.computed.loc[self.computed["Measurements"] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # 0.2 db tolerance?
            # TODO(pierreaubert): that's too high
            self.assertLess(
                abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.0001
            )


class SpinoramaHorizontalReflectionsTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/Horizontal Reflections.txt"
        )
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.titleV, self.splV = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        # computed graphs
        self.computed_unmelted = horizontal_reflections(self.splH, self.splV)
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
            reference = self.reference.loc[
                self.reference["Measurements"] == measurement
            ]
            # computed
            computed = self.computed.loc[self.computed["Measurements"] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size, reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            self.assertLess(
                abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.0001
            )


class SpinoramaEstimatedInRoomTests(unittest.TestCase):
    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/Estimated In-Room Response.txt"
        )
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt"
        )
        self.titleV, self.splV = parse_graph_freq_klippel(
            "datas/ASR/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt"
        )
        # computed graphs
        self.computed_unmelted = estimated_inroom_HV(self.splH, self.splV)
        self.computed = graph_melt(self.computed_unmelted)

    def test_smoke(self):
        self.assertEqual(self.reference_unmelted.shape, self.computed_unmelted.shape)
        self.assertEqual(self.reference.shape, self.computed.shape)

    def test_validate_estimated_inroom(self):
        # key check
        self.assertIn("Estimated In-Room Response", self.computed_unmelted.keys())
        self.assertIn("Estimated In-Room Response", self.reference_unmelted.keys())
        # from klippel
        reference = self.reference.loc[
            self.reference["Measurements"] == "Estimated In-Room Response"
        ]
        # computed
        computed = self.computed.loc[
            self.computed["Measurements"] == "Estimated In-Room Response"
        ]
        # should have the same Freq
        self.assertEqual(computed.Freq.size, reference.Freq.size)
        # self.assertTrue(computed.Freq.eq(reference.Freq).all())
        # and should be equal or close in dB
        self.assertLess(abs(reference.dB.abs().max() - computed.dB.abs().max()), 0.005)
