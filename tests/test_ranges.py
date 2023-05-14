#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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
import math
import numpy as np

from spinorama.filter_iir import Biquad
from spinorama.filter_peq import peq_build
from spinorama.auto_range import find_largest_area


class FreqRangeTests(unittest.TestCase):
    def setUp(self):
        self.data = np.zeros(200).tolist()
        self.freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), len(self.data)).tolist()
        self.config = {
            "target_min_freq": 80,
            "target_max_freq": 16000,
            "plus_and_minus": True,
        }

    def test_zero(self):
        peq = []
        _, freq = find_largest_area(self.freq, self.data, self.config, peq)
        self.assertEqual(freq, -1)

    def test_smokec(self):
        data = [
            0.14338937878176736,
            0.14156150201901072,
            0.13957344740990468,
            0.13741782704262331,
            0.1350865896045205,
            0.13257098786940272,
            0.12986153421651442,
            0.1269479716566794,
            0.12381922635251513,
            0.12046336984034602,
            0.11686756740635719,
            0.11301804973419814,
            0.10890006298021553,
            0.10449783551855771,
            0.09979453101420775,
            0.09477223746294478,
            0.08941193447363718,
            0.08369349023703285,
            0.0775956501289488,
            0.07109608322617203,
            0.056797306871272504,
            0.04894856131115122,
            0.040599298648438864,
            0.031723156730057156,
            0.012284151974521734,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.020871191901634112,
            0.0704535783972241,
            0.1078215743950256,
            0.13183027090708654,
            0.1307040512665757,
            0.11062495980746812,
            0.1134054763022555,
            0.08802052217615786,
            0.004622662556618917,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.046029040378511854,
            0.03853236927068439,
            0.01322012848818628,
            0.07292414274413418,
            0.19108838970807807,
            0.21351033515272316,
            0.1868130098977786,
            0.16678087992263155,
            0.16865045031291254,
            0.09187040950570367,
            0.0,
            0.028561206578068543,
            0.10863748560517444,
            0.08441037378392413,
            0.14124035364608342,
            0.17043940929699603,
            0.2091349476545471,
            0.16372574617833346,
            0.09776671503126746,
            0.048608290766641304,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.15742354795044636,
            0.5105524369519308,
            0.7532936657498185,
            0.9687357704461548,
            1.2152170362749692,
            1.3488852054168396,
            1.5346238416896034,
            1.6458766838476275,
            1.7125832926867361,
            1.7280455441237588,
            1.6602067400357017,
            1.567622988947557,
            1.5216036026617823,
            1.4270000149480444,
            1.3021603834753812,
            1.1318599934017157,
            0.935348759929941,
            0.6856549512656089,
            0.42678973326025116,
            0.20794417091924156,
            0.0330767955711861,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
        peq = []
        sign0, freq0 = find_largest_area(self.freq, data, self.config, peq)
        # we should have an answer
        self.assertNotEqual(freq0, -1)
        # freq should be around 600Hz
        self.assertTrue(freq0 > 550 and freq0 < 650)
        # if we remove the zone 500-600 we should get another freq
        peq.append((1.0, Biquad(Biquad.PEAK, freq0, 48000, 1, 3)))
        sign1, freq1 = find_largest_area(self.freq, data, self.config, peq)
        self.assertTrue(freq1 > 6500 or freq1 < 550)
        # if we send the negative of data, sign should change but not the freq
        peq = []
        sign1, freq1 = find_largest_area(self.freq, np.negative(data).tolist(), self.config, peq)
        self.assertNotEqual(sign0, sign1)
        self.assertAlmostEqual(freq1, freq0)

    def test_one_peak(self):
        empty_peq = []
        test_peq = [
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=1000, srate=48000, q=1, db_gain=3)),
        ]
        data = peq_build(self.freq, test_peq)

        # expect 1 peak
        sign, freq = find_largest_area(self.freq, data, self.config, empty_peq)
        self.assertEqual(sign, 1)
        self.assertTrue(abs(test_peq[0][1].freq - freq) < 50)

        # expect 0 answer since there is 1 peak only and we do not allow this zone
        sign, freq = find_largest_area(self.freq, data, self.config, test_peq)
        self.assertEqual(freq, -1)

    def test_two_peak_far(self):
        empty_peq = []
        # 2 very distincts peaks
        test_peq = [
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=100, srate=48000, q=3, db_gain=2)),
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=5000, srate=48000, q=3, db_gain=1)),
        ]
        data = peq_build(self.freq, test_peq)

        # expect first peak
        sign, freq = find_largest_area(self.freq, data, self.config, empty_peq)
        self.assertEqual(sign, 1)
        self.assertTrue(abs(test_peq[0][1].freq - freq) < 50)

        # expect second peak
        one_peq = [
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=100, srate=48000, q=3, db_gain=2)),
        ]
        sign, freq = find_largest_area(self.freq, data, self.config, one_peq)
        self.assertFalse(abs(test_peq[0][1].freq - freq) < 50)
        self.assertTrue(abs(test_peq[1][1].freq - freq) < 50)

    def test_two_peak_close(self):
        empty_peq = []
        # same test but with closer peaks
        test_peq = [
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=1000, srate=48000, q=1, db_gain=3)),
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=5000, srate=48000, q=1, db_gain=1)),
        ]
        data = peq_build(self.freq, test_peq)

        # expect first peak
        sign, freq = find_largest_area(self.freq, data, self.config, empty_peq)
        self.assertEqual(sign, 1)
        self.assertTrue(abs(test_peq[0][1].freq - freq) < 50)

        # expect second peak
        one_peq = [
            (1.0, Biquad(biquad_type=Biquad.PEAK, freq=1000, srate=48000, q=1, db_gain=3)),
        ]
        sign, freq = find_largest_area(self.freq, data, self.config, one_peq)
        self.assertFalse(abs(test_peq[0][1].freq - freq) < 50)
        self.assertTrue(abs(test_peq[1][1].freq - freq) < 250)


if __name__ == "__main__":
    unittest.main()
