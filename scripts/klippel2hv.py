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

import glob
import re
import shutil
import sys


def process(speakername, filename):
    numbers = re.compile(r"\d+")
    phi, theta = numbers.findall(filename)
    if phi == "0":
        orient = "_V"
    elif phi == "90":
        orient = "_H"
    else:
        print("phi is unknown {}".format(phi))
        return

    itheta = int(theta)
    if itheta == 360:
        return
    elif itheta > 180:
        itheta = itheta - 360

    newname = "{} {} {}.txt".format(speakername, orient, itheta)

    with open(filename) as fin:
        lines = fin.readlines()
        istart = -1
        for i in range(0, len(lines)):
            if lines[i][0:7] == "Curve=[":
                istart = i
                break
        with open(newname, "w") as fout:
            fout.write("Freq[Hz]     dBSPL  Phase[Deg]\n")
            # start after curve, stop before ];
            for l in lines[istart + 1 : -1]:
                fout.write(l)

    if itheta == 180:
        itheta = -180
        negname = "{} {} {}.txt".format(speakername, orient, itheta)
        shutil.copy(newname, negname)


if __name__ == "__main__":
    speakername = sys.argv[1]
    files = glob.glob("Phi*.txt")
    for filename in files:
        process(speakername, filename)
    sys.exit(0)
