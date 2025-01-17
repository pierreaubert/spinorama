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

import numpy as np
import numpy.testing as npt

from spinorama.compute_misc import unify_freq
from spinorama.filter_iir import Biquad
from spinorama.filter_scores import scores_apply_filter, noscore_apply_filter
from spinorama.misc import graph_melt, graph_unmelt
from spinorama.load_rew_eq import parse_eq_iir_rews
from spinorama.load_klippel import parse_graphs_speaker_klippel
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load import (
    filter_graphs,
    filter_graphs_partial,
    spin_compute_di_eir,
)
from spinorama.load import (
    filter_graphs,
    filter_graphs_partial,
)


class SpinoramaFilterIIRTests(unittest.TestCase):
    def setUp(self):
        self.freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 200)
        self.peak = Biquad(3, 1000, 48000, 1, 3)

    def test_smoke1(self):
        peq_slow = np.array([20.0 * math.log10(self.peak.result_slow(f)) for f in self.freq])
        peq_fast = np.array([20.0 * math.log10(self.peak.result(f)) for f in self.freq])
        peq_vec = self.peak.np_log_result(self.freq)
        with self.assertRaises(AssertionError):
            npt.assert_array_almost_equal_nulp(peq_slow, peq_fast)
            npt.assert_array_almost_equal_nulp(peq_slow, peq_vec)


class SpinoramaFilterScoresTests(unittest.TestCase):
    def setUp(self):
        _, (h, v) = parse_graphs_speaker_klippel(
            "datas/measurements", "Neumann", "Neumann KH 80", "asr-v3-20200711", None
        )
        self.df = filter_graphs("Neumann KH 80", h, v, 100, 10000, "klippel", 1)
        self.peq = parse_eq_iir_rews("datas/eq/Neumann KH 80/iir.txt", 48000)

    def test_filtering(self):
        spin, pir, score = scores_apply_filter(self.df, self.peq)
        self.assertIsNotNone(spin)
        if spin is None:
            return
        keys = set(graph_unmelt(spin).keys())
        self.assertSetEqual(
            keys,
            set(
                [
                    "Listening Window",
                    "On Axis",
                    "Freq",
                    "Early Reflections",
                    "Early Reflections DI",
                    "Sound Power",
                    "DI offset",
                    "Sound Power DI",
                ]
            ),
        )
        self.assertIsNotNone(pir)
        if pir is None:
            return
        self.assertEqual(pir.shape, (194, 3))

        self.assertIsNotNone(score)
        if score is None:
            return
        self.assertAlmostEqual(score["pref_score"], 6.3657834989030615, 5)


class SpinoramaFilterNoScoresTests(unittest.TestCase):
    def setUp(self):
        self.peq = parse_eq_iir_rews("datas/eq/Neumann KH 80/iir.txt", 48000)

        speaker_name = "BIC America Venturi DV62si"
        status, (title, df_melted) = parse_graphs_speaker_rew_text_dump(
            "datas/measurements",
            "BIC America",
            speaker_name,
            "",
            "vendor",
        )
        self.assertTrue(status)
        self.assertEqual(title, "CEA2034")
        df_unmelted = graph_melt(unify_freq(df_melted))
        df_full = spin_compute_di_eir(speaker_name, title, df_unmelted)
        self.df = filter_graphs_partial(df_full, "rew_text_dump", 1.0)

    def test_filtering(self):
        self.assertIsNotNone(self.df)
        spin, pir, score = noscore_apply_filter(self.df, self.peq, False)
        self.assertIsNotNone(spin)
        if spin is None:
            return
        keys = set(list(spin.Measurements))
        self.assertSetEqual(
            keys,
            set(
                [
                    "level_0",  # TODO(pierre): where does that come from!
                    "Listening Window",
                    "On Axis",
                    "Early Reflections",
                    "Early Reflections DI",
                    "Sound Power",
                    "DI offset",
                    "Sound Power DI",
                ]
            ),
        )
        self.assertIsNotNone(pir)
        if pir is None:
            return
        self.assertEqual(pir.shape, (957, 3))
        self.assertIsNone(score)


if __name__ == "__main__":
    unittest.main()
