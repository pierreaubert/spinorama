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

import pandas as pd

from spinorama import logger


def parse_graphs_speaker_rewstextdump(speaker_path, speaker_brand, speaker_name, origin, version):
    """Parse text files with speaker measurements and return a dataframe.

    Mandatory files are ON, LW, ER and SP. ERDI and PSDI are ignored. PIR is optional.
    """
    freqs = []
    spls = []
    msrts = []
    for txt, msrt, is_mandatory in (
        ("On Axis", "On Axis", True),
        ("ER", "Early Reflections", True),
        ("LW", "Listening Window", True),
        ("SP", "Sound Power", True),
        ("DI", "DI Offset", False),
        ("ERDI", "Early Reflections DI", False),
        ("SPDI", "Sound Power DI", False),
        ("PIR", "Estimated In-Room Response", False),
    ):
        try:
            filename = f"{speaker_path}/{speaker_name}/{version}/{txt}.txt"
            with open(filename, "r") as text_measurements:
                lines = text_measurements.readlines()
                logger.debug("read file %s found %d", filename, len(lines))
                for l in lines:
                    if len(l) > 0 and l[0] == "*":
                        continue
                    words = l.split()
                    if len(words) == 3:
                        freq = float(words[0])
                        spl = float(words[1])
                        # phase = float(words[2])
                        if freq < 10.0 or freq > 20000:
                            continue
                        freqs.append(freq)
                        spls.append(spl)
                        msrts.append(msrt)
        except FileNotFoundError:
            if is_mandatory:
                logger.error("Speaker: %s File %s not found", speaker_brand, speaker_name)
                return "error", pd.DataFrame({})

    return "CEA2034", pd.DataFrame({"Freq": freqs, "dB": spls, "Measurements": msrts})
