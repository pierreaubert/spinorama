# -*- coding: utf-8 -*-
import logging
import math
from .filter_iir import Biquad

# TODO(pierre): max rgain and max Q should be in parameters
# https://www.roomeqwizard.com/help/help_en-GB/html/eqfilters.html

logger = logging.getLogger("spinorama")


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

    if len(line) > 0 and line[0] == "*":
        return None, None

    words = line.split()
    len_words = len(words)

    if len_words <= 3 or words[0] != "Filter":
        return None, None

    if words[2] == "ON":
        status = 1
    else:
        status = 0

    if len_words == 12:
        kind = words[3]
        freq = words[5]
        gain = words[8]
        q = words[11]
    elif len_words == 10:
        kind = words[3]
        freq = words[5]
        gain = words[8]
    elif len_words == 8:  # APO format
        kind = words[3]
        freq = words[5][:-1]
        gain = words[6][:-1]
        q = words[7]
    elif len_words == 7:
        kind = words[3]
        freq = words[5]

    if freq:
        ifreq = int(float(freq))
        if ifreq < 0 or ifreq > srate / 2:
            logger.debug("IIR peq freq {0}Hz out of bounds (srate={1}".format(freq, srate))
            return None, None

    if gain:
        rgain = float(gain)
        if rgain < -10 or rgain > 30:
            logger.debug("IIR peq gain {0} is large!".format(rgain))
            return None, None

    if q:
        rq = float(q)
        if rq < 0 or rq > 20:
            logger.debug("IIR peq Q {0} is out of bounds!".format(rq))
            return None, None

    if kind in ("PK", "PEQ", "Modal"):
        iir = Biquad(Biquad.PEAK, ifreq, srate, rq, rgain)
        logger.debug("add IIR peq PEAK freq {0}Hz srate {1} Q {2} Gain {3}".format(ifreq, srate, rq, rgain))
    elif kind == "NO":
        iir = Biquad(Biquad.NOTCH, ifreq, srate, rq, rgain)
        logger.debug("add IIR peq NOTCH freq {0}Hz srate {1} Q {2} Gain {3}".format(ifreq, srate, rq, rgain))
    elif kind == "BP":
        iir = Biquad(Biquad.BANDPASS, ifreq, srate, rq, rgain)
        logger.debug("add IIR peq BANDPASS freq {0}Hz srate {1} Q {2} Gain {3}".format(ifreq, srate, rq, rgain))
    elif kind in ("HP", "HPQ"):
        iir = Biquad(Biquad.HIGHPASS, ifreq, srate, 1.0 / math.sqrt(2.0), 1.0)
        logger.debug("add IIR peq LOWPASS freq {0}Hz srate {1}".format(ifreq, srate))
    elif kind in ("LP", "LPQ"):
        iir = Biquad(Biquad.LOWPASS, ifreq, srate, 1.0 / math.sqrt(2.0), 1.0)
        logger.debug("add IIR peq LOWPASS freq {0}Hz srate {1}".format(ifreq, srate))
    elif kind in ("LS", "LSC"):
        iir = Biquad(Biquad.LOWSHELF, ifreq, srate, 1.0, rgain)
        logger.debug("add IIR peq LOWSHELF freq {0}Hz srate {1} Gain {2}".format(ifreq, srate, rgain))
    elif kind in ("HS", "HSC"):
        iir = Biquad(Biquad.HIGHSHELF, ifreq, srate, 1.0, rgain)
        logger.debug("add IIR peq HIGHSHELF freq {0}Hz srate {1} Gain {2}".format(ifreq, srate, rgain))
    else:
        logger.warning("kind {0} is unknown".format(kind))
        return None, None

    return status, iir


def parse_eq_iir_rews(filename, srate):
    peq = []
    try:
        with open(filename, "r") as f:
            lines = f.readlines()
            for l in lines:
                status, iir = parse_eq_line(l, srate)
                if status is not None and iir is not None:
                    peq.append((status, iir))
    except FileNotFoundError:
        logger.info("Loading filter: eq file {0} not found".format(filename))
    return peq
