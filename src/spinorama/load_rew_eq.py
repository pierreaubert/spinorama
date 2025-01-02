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
from spinorama.filter_iir import bw2q, Biquad
from spinorama.filter_peq import Peq

# TODO(pierre): max rgain and max Q should be in parameters
INPUT_MAX_GAIN = 30
INPUT_MAX_Q = 30


# https://www.roomeqwizard.com/help/help_en-GB/html/eqfilters.html


def parse_eq_line(line, srate):
    status = None
    iir = None
    kind = None
    freq = None
    ifreq = None
    gain = None
    rgain = None
    q = None
    rq = None
    bw = None

    if len(line) > 0 and line[0] == "*":
        return None, None

    words = line.split()
    len_words = len(words)

    if len_words <= 3 or words[0] != "Filter":
        return None, None

    status = 1 if words[2] == "ON" else 0

    # reference is https://sourceforge.net/p/equalizerapo/wiki/Configuration%20reference/
    #
    # Filter: ON|OFF Type Fc float_freq Hz Gain float_db dB Q float_q
    # Filter: ON|OFF Type Fc float_freq Hz Gain float_db dB BW Oct float_octave
    # Filter: ON|OFF Type Fc float_freq Hz Gain float_db dB
    # Filter: ON|OFF Type Fc float_freq Hz Q float_q
    #
    # Other models are the same without Fc / Gain / dB Q
    # This is very error prone and needs more testing

    if len_words == 13:
        # APO case with BW Oct
        kind = words[3]
        freq = words[5]
        gain = words[8]
        bw = words[12]
    elif len_words == 12:
        # APO case with Q
        kind = words[3]
        freq = words[5]
        gain = words[8]
        q = words[11]
    elif len_words == 10:
        # APO case with gain but no Q
        kind = words[3]
        freq = words[5]
        gain = words[8]
    elif len_words == 9:
        # APO case without gain but with Q
        kind = words[3]
        freq = words[5][:-1]
        q = words[8]
    elif len_words == 8:
        # APO case with gain and Q but no legend and a comma after the field
        kind = words[3]
        freq = words[5][:-1]
        gain = words[6][:-1]
        q = words[7]
    elif len_words == 7:
        # APO case with only freq like a notch filter
        kind = words[3]
        freq = words[5]

    ffreq = 0.0
    if freq:
        ifreq = int(float(freq))
        if ifreq < 0 or ifreq > srate / 2:
            logger.debug("IIR peq freq %sHz out of bounds (srate=%d)", freq, srate)
            return None, None
        ffreq = float(freq)

    rgain = 0.0
    if gain:
        rgain = float(gain)
        if abs(rgain) > INPUT_MAX_GAIN:
            logger.debug("IIR peq gain %f is large!", rgain)
            return None, None

    rq = 0.0
    if q:
        rq = float(q)
        if rq < 0 or rq > INPUT_MAX_Q:
            logger.debug("IIR peq Q %f is out of bounds!", rq)
            return None, None

    if bw:
        if q:
            logger.debug("both Q and BW are defined")
            return None, None
        q = bw2q(float(bw))

    # print(line)
    # print("add IIR peq {} freq {}Hz srate {} Q {} Gain {}".format(kind, ffreq, srate, rq, rgain))

    if kind in ("PK", "PEQ", "Modal"):
        iir = Biquad(Biquad.PEAK, ffreq, srate, rq, rgain)
        logger.debug("add IIR peq PEAK freq %.0fHz srate %d Q %f Gain %f", ifreq, srate, rq, rgain)
    elif kind == "NO":
        rq = 30.0
        iir = Biquad(Biquad.NOTCH, ffreq, srate, rq, rgain)
        logger.debug("add IIR peq NOTCH freq %.0fHz srate %d Q %f Gain %f", ifreq, srate, rq, rgain)
    elif kind == "BP":
        if rq == 0.0:
            rq = 1 / math.sqrt(2.0)
        iir = Biquad(Biquad.BANDPASS, ffreq, srate, rq, rgain)
        logger.debug(
            "add IIR peq BANDPASS freq %.0fHz srate %d Q %d Gain %f", ffreq, srate, rq, rgain
        )
    elif kind in ("HP", "HPQ"):
        iir = Biquad(Biquad.HIGHPASS, ffreq, srate, rq, rgain)
        logger.debug(
            "add IIR peq HIGHPASS freq %.0fHz srate %d Q %f Gain %f", ifreq, srate, rq, rgain
        )
    elif kind in ("LP", "LPQ"):
        iir = Biquad(Biquad.LOWPASS, ffreq, srate, rq, rgain)
        logger.debug("add IIR peq LOWPASS freq %.0fHz srate %d", ffreq, srate)
    elif kind in ("LS", "LSQ", "LSC"):
        # need to deal with last case when slope is given (6db/oct, 12db/oct, 24db/oct)
        iir = Biquad(Biquad.LOWSHELF, ffreq, srate, rq, rgain)
        logger.debug("add IIR peq LOWSHELF freq %.0fHz srate %d Gain %f", ffreq, srate, rgain)
    elif kind in ("HS", "HSQ", "HSC"):
        # need to deal with last case when slope is given (6db/oct, 12db/oct, 24db/oct)
        iir = Biquad(Biquad.HIGHSHELF, ffreq, srate, rq, rgain)
        logger.debug("add IIR peq HIGHSHELF freq %.0fHz srate %d Gain %f", ffreq, srate, rgain)
    else:
        logger.warning("kind %s is unknown (line: %s)", kind, line)
        return None, None

    return status, iir


def parse_eq_iir_rews(filename: str, srate: int) -> Peq:
    peq = []
    try:
        with open(filename, "r", encoding="utf8") as f:
            lines = f.readlines()
            for i, l in enumerate(lines):
                status, iir = parse_eq_line(l, srate)
                if status is not None and iir is not None:
                    peq.append((status, iir))
                else:
                    logger.debug("Unknown iir on line %s in file %s:%d", l, filename, i)
    except FileNotFoundError:
        logger.info("Loading filter: eq file %s not found", filename)
    return peq
