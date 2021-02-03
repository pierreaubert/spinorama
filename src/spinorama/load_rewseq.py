#                                                  -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd
from .filter_iir import Biquad

# TODO(pierre): max rgain and max Q should be in parameters
# https://www.roomeqwizard.com/help/help_en-GB/html/eqfilters.html

logger = logging.getLogger("spinorama")


def parse_eq_iir_rews(filename, srate):
    peq = []
    try:
        with open(filename, "r") as f:
            lines = f.readlines()
            for l in lines:
                if len(l) > 0 and l[0] == "*":
                    continue
                words = l.split()
                len_words = len(words)
                if len_words == 12 and words[0] == "Filter":
                    if words[2] == "ON":
                        status = 1
                    else:
                        status = 0

                    kind = words[3]
                    freq = words[5]
                    gain = words[8]
                    q = words[11]

                    ifreq = int(float(freq))
                    if ifreq < 0 or ifreq > srate / 2:
                        logger.info(
                            "IIR peq freq {0}Hz out of bounds (srate={1}".format(
                                freq, srate
                            )
                        )
                        continue

                    rgain = float(gain)
                    if rgain < -10 or rgain > 30:
                        logger.info("IIR peq gain {0} is large!".format(rgain))
                        # continue

                    rq = float(q)
                    if rq < 0 or rq > 20:
                        logger.info("IIR peq Q {0} is out of bounds!".format(rq))
                        # continue

                    # TODO: factor code
                    if kind == "PK" or kind == "PEQ" or kind == "Modal":
                        iir = Biquad(Biquad.PEAK, ifreq, srate, rq, rgain)
                        logger.debug(
                            "add IIR peq PEAK freq {0}Hz srate {1} Q {2} Gain {3}".format(
                                ifreq, srate, rq, rgain
                            )
                        )
                        peq.append((status, iir))
                    elif kind == "NO":
                        iir = Biquad(Biquad.NOTCH, ifreq, srate, rq, rgain)
                        logger.debug(
                            "add IIR peq NOTCH freq {0}Hz srate {1} Q {2} Gain {3}".format(
                                ifreq, srate, rq, rgain
                            )
                        )
                        peq.append((status, iir))
                    elif kind == "BP":
                        iir = Biquad(Biquad.BANDPASS, ifreq, srate, rq, rgain)
                        logger.debug(
                            "add IIR peq BANDPASS freq {0}Hz srate {1} Q {2} Gain {3}".format(
                                ifreq, srate, rq, rgain
                            )
                        )
                        peq.append((status, iir))
                    else:
                        logger.warning("kind {0} is unknown".format(kind))
                elif len_words == 7 and words[0] == "Filter":
                    if words[2] == "ON":
                        status = 1
                    else:
                        status = 0

                    kind = words[3]
                    freq = words[5]

                    ifreq = int(freq)
                    if ifreq < 0 or ifreq > srate / 2:
                        logger.info(
                            "IIR peq freq {0}Hz out of bounds (srate={1}".format(
                                freq, srate
                            )
                        )
                        continue

                    # TODO: factor code
                    if kind == "HP" or kind == "HPQ":
                        iir = Biquad(
                            Biquad.HIGHPASS, ifreq, srate, 1.0 / math.sqrt(2.0), 1.0
                        )
                        logger.debug(
                            "add IIR peq LOWPASS freq {0}Hz srate {1}".format(
                                ifreq, srate
                            )
                        )
                        peq.append((status, iir))
                    elif kind == "LP" or kind == "LPQ":
                        iir = Biquad(
                            Biquad.LOWPASS, ifreq, srate, 1.0 / math.sqrt(2.0), 1.0
                        )
                        logger.debug(
                            "add IIR peq LOWPASS freq {0}Hz srate {1}".format(
                                ifreq, srate
                            )
                        )
                        peq.append((status, iir))
                    else:
                        logger.warning("kind {0} is unknown".format(kind))
                elif len_words == 10 and words[0] == "Filter":
                    if words[2] == "ON":
                        status = 1
                    else:
                        status = 0

                    kind = words[3]
                    freq = words[5]
                    gain = words[8]

                    rgain = float(gain)
                    if rgain < -10 or rgain > 30:
                        logger.info("IIR peq gain {0} is large!".format(rgain))
                        # continue

                    ifreq = int(freq)
                    if ifreq < 0 or ifreq > srate / 2:
                        logger.info(
                            "IIR peq freq {0}Hz out of bounds (srate={1}".format(
                                freq, srate
                            )
                        )
                        continue

                    if kind == "LS" or kind == "LSC":
                        iir = Biquad(Biquad.LOWSHELF, ifreq, srate, 1.0, rgain)
                        logger.debug(
                            "add IIR peq LOWSHELF freq {0}Hz srate {1} Gain {2}".format(
                                ifreq, srate, rgain
                            )
                        )
                        peq.append((status, iir))
                    elif kind == "HS" or kind == "HSC":
                        iir = Biquad(Biquad.HIGHSHELF, ifreq, srate, 1.0, rgain)
                        logger.debug(
                            "add IIR peq HIGHSHELF freq {0}Hz srate {1} Gain {2}".format(
                                ifreq, srate, rgain
                            )
                        )
                        peq.append((status, iir))
                    else:
                        logger.warning("kind {0} is unknown".format(kind))

    except FileNotFoundError:
        logger.info("Loading filter: eq file {0} not found".format(filename))
    return peq
