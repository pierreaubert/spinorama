#                                                  -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd

pd.set_option("display.max_rows", 1000)

logger = logging.getLogger("spinorama")


def estimates(onaxis: pd.DataFrame):
    try:
        freq_min = onaxis.Freq.min()
        logger.debug("Freq min: {0}".format(freq_min))
        if math.isnan(freq_min):
            logger.warning("Estimates failed for onaxis {0}".format(onaxis.shape))
            return None
        if freq_min < 300:
            # mean over 300-10k
            y_ref = np.mean(
                onaxis.loc[(onaxis.Freq >= 300) & (onaxis.Freq <= 10000)].dB
            )
            logger.debug("mean over 300-10k Hz = {0}".format(y_ref))
            # print(onaxis)
            y_3 = onaxis.loc[(onaxis.Freq < 150) & (onaxis.dB <= y_ref - 3)].Freq.max()
            y_6 = onaxis.loc[(onaxis.Freq < 150) & (onaxis.dB <= y_ref - 6)].Freq.max()
            # search band up/down
            up: float = onaxis.loc[
                (onaxis.Freq >= 100) & (onaxis.Freq <= 10000)
            ].dB.max()
            down: float = onaxis.loc[
                (onaxis.Freq >= 100) & (onaxis.Freq <= 10000)
            ].dB.min()
            band = max(abs(up - y_ref), abs(y_ref - down))
            est = {
                "ref_from": 300,
                "ref_to": 10000,
            }
            if not math.isnan(y_ref):
                est["ref_level"] = round(y_ref, 0)
            if not math.isnan(y_3):
                est["ref_3dB"] = round(y_3, 0)
            if not math.isnan(y_6):
                est["ref_6dB"] = round(y_6, 0)
            if not math.isnan(band):
                est["ref_band"] = round(band, 1)
        else:
            y_ref = np.mean(
                onaxis.loc[(onaxis.Freq >= freq_min) & (onaxis.Freq <= 10000)].dB
            )
            # search band up/down
            up: float = onaxis.loc[
                (onaxis.Freq >= freq_min) & (onaxis.Freq <= 10000)
            ].dB.max()
            down: float = onaxis.loc[
                (onaxis.Freq >= freq_min) & (onaxis.Freq <= 10000)
            ].dB.min()
            band = max(abs(up - y_ref), abs(y_ref - down))
            est = {
                "ref_from": round(freq_min, 0),
                "ref_to": 10000,
            }
            if not math.isnan(y_ref):
                est["ref_level"] = round(y_ref, 0)
            if not math.isnan(band):
                est["ref_band"] = round(band, 1)

        logger.debug("Estimates: {0}".format(est))
        return est
    except TypeError as te:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, te))
        return None
    except ValueError as ve:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, ve))
        return None
