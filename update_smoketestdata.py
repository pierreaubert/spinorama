#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-21 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
from generate_common import cache_load, cache_save

if __name__ == "__main__":
    df = cache_load()
    df_small = {}
    for speaker in (
        "Genelec 8030C",
        "KEF LS50",
        "KRK Systems Classic 5",
        "Verdant Audio Bambusa MG 1",
    ):
        if speaker in df.keys():
            df_small[speaker] = df[speaker]

    cache_save(df_small, smoke_test=True)
