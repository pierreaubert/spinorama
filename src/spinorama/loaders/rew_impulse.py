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

from spinorama import logger


def parse_impulse_rews(filename, srate):
    impulse = []
    try:
        with open(filename, "r") as f:
            lines = f.readlines()
            for l in lines:
                if len(l) > 0 and l[0] == "*":
                    continue
                words = l.split()
                if len(words) == 3:
                    freq = float(words[0])
                    spl = float(words[1])
                    phase = float(words[2]) / 360 * 2 * math.pi
                    impulse.append((freq, spl, phase))

    except FileNotFoundError:
        logger.exception("Loading filter failed file %s not found", filename)
    return impulse
