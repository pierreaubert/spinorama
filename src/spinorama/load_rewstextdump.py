#                                                  -*- coding: utf-8 -*-
import logging
import numpy as np
import pandas as pd
from .compute_cea2034 import estimated_inroom
from .load import graph_melt

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
        for txt, msrt in (  # ('DI', 'Sound Power DI'),
            ("ER", "Early Reflections"),
            ("LW", "Listening Window"),
            ("On Axis", "On Axis"),
            ("SP", "Sound Power"),
            # ('ERDI', 'Early Reflections DI'),
        ):
            filename = "{0}/Vendors/{1}/{2}/{3}.txt".format(
                speaker_path, speaker_brand, speaker_name, txt
            )
            if origin == "Misc":
                filename = "{0}/Misc/{1}/{2}/{3}.txt".format(
                    speaker_path, speaker_brand, speaker_name, txt
                )
            # TODO :
            # if version is not None and version not in ('asr', 'princeton', 'vendor', 'rewstextdump'):
            #
            f = open(filename, "r")
            lines = f.readlines()
            # logger.info('read f {} found {}'.format(f, len(lines)))
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

        spin = pd.DataFrame({"Freq": freqs, "dB": spls, "Measurements": msrts})

        # TODO(pierre): should be factored out (same as in webplotdigitizer
        # compute ERDI and SPDI
        if spin is not None:
            # compute EIR
            on = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
            lw = spin.loc[spin["Measurements"] == "Listening Window"].reset_index(
                drop=True
            )
            er = spin.loc[spin["Measurements"] == "Early Reflections"].reset_index(
                drop=True
            )
            sp = spin.loc[spin["Measurements"] == "Sound Power"].reset_index(drop=True)

            # check DI index
            sp_di_computed = lw.dB - sp.dB
            sp_di = spin.loc[spin["Measurements"] == "Sound Power DI"].reset_index(
                drop=True
            )
            if sp_di.shape[0] == 0:
                logger.debug("No Sound Power DI curve!")
                df2 = pd.DataFrame(
                    {
                        "Freq": on.Freq,
                        "dB": sp_di_computed,
                        "Measurements": "Sound Power DI",
                    }
                )
                spin = spin.append(df2).reset_index(drop=True)
            else:
                delta = np.mean(sp_di) - np.mean(sp_di_computed)
                logger.debug("Sound Power DI curve: removing {0}".format(delta))
                spin.loc[spin["Measurements"] == "Sound Power DI", "dB"] -= delta

            # sp_di = spin.loc[spin['Measurements'] == 'Sound Power DI'].reset_index(drop=True)
            # print('Post treatment SP DI: shape={0} min={1} max={2}'.format(sp_di.shape, sp_di.dB.min(), sp_di.dB.max()))
            # print(sp_di)

            er_di_computed = lw.dB - er.dB
            er_di = spin.loc[
                spin["Measurements"] == "Early Reflections DI"
            ].reset_index(drop=True)
            if er_di.shape[0] == 0:
                logger.debug("No Early Reflections DI curve!")
                df2 = pd.DataFrame(
                    {
                        "Freq": on.Freq,
                        "dB": er_di_computed,
                        "Measurements": "Early Reflections DI",
                    }
                )
                spin = spin.append(df2).reset_index(drop=True)
            else:
                delta = np.mean(er_di) - np.mean(er_di_computed)
                logger.debug("Early Reflections DI curve: removing {0}".format(delta))
                spin.loc[spin["Measurements"] == "Early Reflections DI", "dB"] -= delta

            # er_di = spin.loc[spin['Measurements'] == 'Early Reflections DI'].reset_index(drop=True)
            # print('Post treatment ER DI: shape={0} min={1} max={2}'.format(er_di.shape, er_di.dB.min(), er_di.dB.max()))
            # print(er_di)

            di_offset = spin.loc[spin["Measurements"] == "DI offset"].reset_index(
                drop=True
            )
            if di_offset.shape[0] == 0:
                logger.debug("No DI offset curve!")
                df2 = pd.DataFrame(
                    {"Freq": on.Freq, "dB": 0, "Measurements": "DI offset"}
                )
                spin = spin.append(df2).reset_index(drop=True)

            # print(on.shape, lw.shape, er.shape, sp.shape)
            eir = estimated_inroom(lw, er, sp)
            # print('eir {0}'.format(eir.shape))
            # print(eir)
            logger.debug("eir {0}".format(eir.shape))
            dfs["Estimated In-Room Response"] = graph_melt(eir)

        #
        dfs["CEA2034"] = spin
    except FileNotFoundError:
        logger.error("Speaker: {0} Not found: {1}".format(speaker_brand, speaker_name))
        return {}
    return dfs
