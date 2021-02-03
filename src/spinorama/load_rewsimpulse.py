#                                                  -*- coding: utf-8 -*-
import logging
import math


logger = logging.getLogger("spinorama")


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
        logger.error("Loading filter failed file {0} not found".format(filename))
    return impulse
