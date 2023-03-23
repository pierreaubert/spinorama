#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
from spinorama.auto_loss import loss


class LossTests(unittest.TestCase):
    def setUp(self):
        self.data = np.zeros(200)
        self.freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), len(self.data)).tolist()
        self.config = {
            "target_min_freq": 80,
            "target_max_freq": 16000,
            "plus_and_minus": True,
            "curves": ["Listening Window"],
            "loss_weigths": [100.0, 1.0],
            "loss": "leastsquare_loss",
            "maxiter": 100,
        }

    def test_loss(self):
        up_peq = [
            (1.0, Biquad(typ=Biquad.PEAK, freq=1000, srate=48000, Q=1, dbGain=3)),
        ]
        down_peq = [
            (1.0, Biquad(typ=Biquad.PEAK, freq=1000, srate=48000, Q=1, dbGain=-3)),
        ]
        auto_target = peq_build(self.freq, up_peq)

        self.assertAlmostEqual(np.linalg.norm(auto_target + peq_build(self.freq, down_peq)), 0.0)

        for func in ("leastsquare_loss", "flat_loss"):
            self.config["loss"] = func
            init_fun = loss({}, self.freq, [auto_target], down_peq, 0, self.config)
            self.assertAlmostEqual(init_fun, 0.0)


if __name__ == "__main__":
    unittest.main()
