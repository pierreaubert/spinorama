# -*- coding: utf-8 -*-
import logging
import numpy as np
import pandas as pd
from .compute_misc import unify_freq
from .compute_cea2034 import estimated_inroom
from .load_misc import graph_melt
from .load import spin_compute_di_eir

logger = logging.getLogger("spinorama")


def parse_graphs_speaker_rewstextdump(
    speaker_path, speaker_brand, speaker_name, origin, version
):
    dfs = {}
    try:
        spin = None
        freqs = []
        spls = []
        msrts = []
        for txt, msrt in (
            ("On Axis", "On Axis"),
            ("ER", "Early Reflections"),
            ("LW", "Listening Window"),
            ("SP", "Sound Power"),
            # ('ERDI', 'Early Reflections DI'),
            # ('DI', 'Sound Power DI'),
        ):
            filename = "{0}/{1}/{2}/{3}.txt".format(
                speaker_path, speaker_name, version, txt
            )
            with open(filename, "r") as f:
                lines = f.readlines()
                logger.debug("read f {} found {}".format(f, len(lines)))
                for l in lines:
                    if len(l) > 0 and l[0] == "*":
                        continue
                    words = l.split()
                    if len(words) == 3:
                        freq = float(words[0])
                        spl = float(words[1])
                        # phase = float(words[2])
                    freqs.append(freq)
                    spls.append(spl)
                    msrts.append(msrt)

        return "CEA2034", pd.DataFrame(
            {"Freq": freqs, "dB": spls, "Measurements": msrts}
        )
    except FileNotFoundError:
        logger.error("Speaker: {0} Not found: {1}".format(speaker_brand, speaker_name))
        return {}
    return dfs
