#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
import tables
import warnings
import flammkuchen as fl

if __name__ == "__main__":
    df = fl.load("cache.parse_all_speakers.h5")
    df_small = {}
    for speaker in (
        "Genelec 8030C",
        "KEF LS50",
        "KRK Systems Classic 5",
        "Verdant Audio Bambusa MG 1",
    ):
        if speaker in df.keys():
            df_small[speaker] = df[speaker]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", tables.NaturalNameWarning)
        fl.save("cache.smoketest_speakers.h5", df_small)
