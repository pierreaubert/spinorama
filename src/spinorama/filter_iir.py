# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
import numpy as np


class Biquad:
    # pretend enumeration
    LOWPASS, HIGHPASS, BANDPASS, PEAK, NOTCH, LOWSHELF, HIGHSHELF = range(7)

    type2name = {
        LOWPASS: ["Lowpass", "LP"],
        HIGHPASS: ["Highpass", "HP"],
        BANDPASS: ["Bandpath", "BP"],
        PEAK: ["Peak", "PK"],
        NOTCH: ["Notch", "NO"],
        LOWSHELF: ["Lowshelf", "LS"],
        HIGHSHELF: ["Highshelf", "HS"],
    }

    def __init__(self, typ, freq, srate, Q, dbGain=0):
        types = {
            Biquad.LOWPASS: Biquad.lowpass,
            Biquad.HIGHPASS: Biquad.highpass,
            Biquad.BANDPASS: Biquad.bandpass,
            Biquad.PEAK: Biquad.peak,
            Biquad.NOTCH: Biquad.notch,
            Biquad.LOWSHELF: Biquad.lowshelf,
            Biquad.HIGHSHELF: Biquad.highshelf,
        }
        if typ not in types:
            raise AssertionError
        self.typ = typ
        self.freq = float(freq)
        self.srate = float(srate)
        self.Q = float(Q)
        self.dbGain = float(dbGain)
        self.a0 = self.a1 = self.a2 = 0
        self.b0 = self.b1 = self.b2 = 0
        self.x1 = self.x2 = 0
        self.y1 = self.y2 = 0
        # only used for peaking and shelving filter types
        A = math.pow(10, dbGain / 40)
        omega = 2 * math.pi * self.freq / self.srate
        sn = math.sin(omega)
        cs = math.cos(omega)
        alpha = sn / (2 * Q)
        beta = math.sqrt(A + A)
        types[typ](self, A, omega, sn, cs, alpha, beta)
        # prescale constants
        self.b0 /= self.a0
        self.b1 /= self.a0
        self.b2 /= self.a0
        self.a1 /= self.a0
        self.a2 /= self.a0

        # precompute other parameters
        self.r_up0 = (self.b0 + self.b1 + self.b2) ** 2
        self.r_up1 = -4 * (self.b0 * self.b1 + 4 * self.b0 * self.b2 + self.b1 * self.b2)
        self.r_up2 = 16 * self.b0 * self.b2
        self.r_dw0 = (1 + self.a1 + self.a2) ** 2
        self.r_dw1 = -4 * (self.a1 + 4 * self.a2 + self.a1 * self.a2)
        self.r_dw2 = 16 * self.a2

    def lowpass(self, A, omega, sn, cs, alpha, beta):
        self.b0 = (1 - cs) / 2
        self.b1 = 1 - cs
        self.b2 = (1 - cs) / 2
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def highpass(self, A, omega, sn, cs, alpha, beta):
        self.b0 = (1 + cs) / 2
        self.b1 = -(1 + cs)
        self.b2 = (1 + cs) / 2
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def bandpass(self, A, omega, sn, cs, alpha, beta):
        self.b0 = alpha
        self.b1 = 0
        self.b2 = -alpha
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def notch(self, A, omega, sn, cs, alpha, beta):
        self.b0 = 1
        self.b1 = -2 * cs
        self.b2 = 1
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def peak(self, A, omega, sn, cs, alpha, beta):
        self.b0 = 1 + (alpha * A)
        self.b1 = -2 * cs
        self.b2 = 1 - (alpha * A)
        self.a0 = 1 + (alpha / A)
        self.a1 = -2 * cs
        self.a2 = 1 - (alpha / A)

    def lowshelf(self, A, omega, sn, cs, alpha, beta):
        self.b0 = A * ((A + 1) - (A - 1) * cs + beta * sn)
        self.b1 = 2 * A * ((A - 1) - (A + 1) * cs)
        self.b2 = A * ((A + 1) - (A - 1) * cs - beta * sn)
        self.a0 = (A + 1) + (A - 1) * cs + beta * sn
        self.a1 = -2 * ((A - 1) + (A + 1) * cs)
        self.a2 = (A + 1) + (A - 1) * cs - beta * sn

    def highshelf(self, A, omega, sn, cs, alpha, beta):
        self.b0 = A * ((A + 1) + (A - 1) * cs + beta * sn)
        self.b1 = -2 * A * ((A - 1) + (A + 1) * cs)
        self.b2 = A * ((A + 1) + (A - 1) * cs - beta * sn)
        self.a0 = (A + 1) - (A - 1) * cs + beta * sn
        self.a1 = 2 * ((A - 1) - (A + 1) * cs)
        self.a2 = (A + 1) - (A - 1) * cs - beta * sn

    # perform filtering function
    def __call__(self, x):
        y = (
            self.b0 * x
            + self.b1 * self.x1
            + self.b2 * self.x2
            - self.a1 * self.y1
            - self.a2 * self.y2
        )
        self.x2 = self.x1
        self.x1 = x
        self.y2 = self.y1
        self.y1 = y
        return y

    # provide a static result for a given frequency f
    def resultSlow(self, f):
        phi = (math.sin(math.pi * f * 2 / (2 * self.srate))) ** 2
        r = (
            (self.b0 + self.b1 + self.b2) ** 2
            - 4 * (self.b0 * self.b1 + 4 * self.b0 * self.b2 + self.b1 * self.b2) * phi
            + 16 * self.b0 * self.b2 * phi * phi
        ) / (
            (1 + self.a1 + self.a2) ** 2
            - 4 * (self.a1 + 4 * self.a2 + self.a1 * self.a2) * phi
            + 16 * self.a2 * phi * phi
        )
        r = max(0, r)
        return r ** (0.5)

    def result(self, f):
        phi = (math.sin(math.pi * f * 2 / (2 * self.srate))) ** 2
        phi2 = phi * phi
        r = (self.r_up0 + self.r_up1 * phi + self.r_up2 * phi2) / (
            self.r_dw0 + self.r_dw1 * phi + self.r_dw2 * phi2
        )
        r = max(0, r)
        return r ** (0.5)

    # provide a static log result for a given frequency f
    def log_result(self, f):
        try:
            r = 20 * math.log10(self.result(f))
        except:
            r = -200
        return r

    # return computed constants
    def constants(self):
        return self.a1, self.a2, self.b0, self.b1, self.b2

    def type2str(self, short=True):
        if short is True:
            return self.type2name[self.typ][1]
        return self.type2name[self.typ][0]

    def __str__(self):
        return "Type:%s,Freq:%.1f,Rate:%.1f,Q:%.1f,Gain:%.1f" % (
            self.type2str(),
            self.freq,
            self.srate,
            self.Q,
            self.dbGain,
        )

    # vector version (10x faster)
    def np_log_result(self, freq):
        phi = np.sin(math.pi * freq * 2 / (2 * self.srate)) ** 2
        phi2 = phi**2
        r = (self.r_up0 + self.r_up1 * phi + self.r_up2 * phi2) / (
            self.r_dw0 + self.r_dw1 * phi + self.r_dw2 * phi2
        )
        return np.where(r <= 0.0, -200, 20.0 * np.log10(np.sqrt(r)))
