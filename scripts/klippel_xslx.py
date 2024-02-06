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

import sys

import pandas as pd


def process(speakername, filename):
    data_speaker = pd.read_excel(
        io=filename,
        sheet_name=["Hor Contour", "Ver Contour"],
        header=2,
    )
    col_freq = "Frequency / Hz"
    col_spl = "Sound Pressure Level  / dB (re 20 µPa)"  # noqa: RUF001
    col_angle = "Theta / deg"

    spl_h = data_speaker["Hor Contour"].groupby(col_angle)
    spl_v = data_speaker["Ver Contour"].groupby(col_angle)

    for orientation, spls in [("_H", spl_h), ("_V", spl_v)]:
        for current_angle, current_spl in spls:
            if (current_angle % 10) != 0:
                continue
            filename = "{} {} {}.txt".format(speakername, orientation, current_angle)
            with open(filename, "w") as fd:
                fd.write("Freq SPL Phase\n")
                for freq, spl in zip(
                    current_spl[col_freq].values, current_spl[col_spl].values, strict=True
                ):
                    fd.write("{} {} 0.0\n".format(freq, spl))


if __name__ == "__main__":
    speakername = sys.argv[1]
    excelfile = sys.argv[2]
    process(speakername, excelfile)
    sys.exit(0)
