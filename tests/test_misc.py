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

import typing
import unittest

from spinorama.misc import graph_melt

from spinorama.compute_misc import unify_freq

from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump


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


if __name__ == "__main__":
    unittest.main()
