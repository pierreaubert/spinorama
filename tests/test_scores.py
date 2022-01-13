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
import numpy as np
import pandas as pd
from spinorama.compute_scores import octave, aad


pd.set_option("display.max_rows", 202)


class PrefRatingTests(unittest.TestCase):
    def setUp(self):
        self.octave2 = octave(2)
        self.octave3 = octave(3)
        self.octave20 = octave(20)

    def test_octave(self):
        self.assertEqual(len(self.octave2), 21)
        self.assertLess(self.octave2[0][0], 100)
        self.assertLess(20000, self.octave2[-1][1])

        self.assertEqual(len(self.octave3), 31)
        self.assertLess(self.octave3[0][0], 100)
        self.assertLess(20000, self.octave3[-1][1])

    def test_aad(self):
        freq = list(np.logspace(0.3, 4.3, 1000))
        db = [100 for i in np.logspace(0.3, 4.3, 1000)]
        df = pd.DataFrame({"Freq": freq, "dB": db})
        # expect 0 deviation from flat line
        self.assertEqual(aad(df), 0.0)


if __name__ == "__main__":
    unittest.main()
