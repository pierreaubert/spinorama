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

import glob
import os
import sys

def process_on(speakername, on_spl_filename) -> list[tuple[float, float]]:
    on_spl = []

    with open(on_spl_filename) as fin:
        lines = fin.readlines()
        for line in lines:
            toparse = line
            if line[-2:] == '];':
                toparse = line[:-2]
            items = toparse.split()
            if len(items) == 2:
                try:
                    freq = float(items[0])
                    spl = float(items[1])
                    if freq >= 20.00 and freq <= 20000:
                        on_spl.append((freq, spl))
                except ValueError:
                    continue
    return on_spl

def process_spl(speakername, spl_filename) -> dict[int, list[tuple[float, float]]]:
    spl = {}
    for angle in range(-180, 190, 5):
        spl[angle] = []

    with open(spl_filename) as fin:
        lines = fin.readlines()
        for line in lines:
            toparse = line
            if line[-2:] == '];':
                toparse = line[:-2]
            items = toparse.split()
            if len(items) == 3:
                try:
                    freq = float(items[0])
                    fspl = float(items[1])
                    angle = int(items[2])
                    if freq >= 20.00 and freq <= 20000 and angle >= -180 and angle <= 180:
                        spl[angle].append((freq, fspl))
                except ValueError:
                    continue
    return spl


def process(speakername, on_spl_filename, h_spl_filename, v_spl_filename):
    on_spl = process_on(speakername, on_spl_filename)
    h_spl = process_spl(speakername, h_spl_filename)
    v_spl = None
    if os.path.exists(v_spl_filename):
        v_spl = process_spl(speakername, v_spl_filename)

    for orientation, spl_data in (
            ('_H', h_spl),
            ('_V', v_spl),
    ):
        if spl_data is None:
            continue
        for angle, spl_at_angle in spl_data.items():

            filename = '../{} {} {}.txt'.format(speakername, orientation, angle)

            with open(filename, "w") as fout:
                if angle == 0:
                    for freq, spl in on_spl:
                        fout.write('{} {} {};\n'.format(freq, spl, angle))
                elif len(spl_at_angle)>0:
                    for freq, spl in spl_at_angle:
                        fout.write('{} {} {};\n'.format(freq, spl, angle))


if __name__ == "__main__":
    speakername = sys.argv[1]
    process(speakername, '01_FR.txt', '02_Horizontal Contour Plot.txt', '03_Vertical Contour Plot.txt')
    sys.exit(0)
