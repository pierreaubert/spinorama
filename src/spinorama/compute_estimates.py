# -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd

from .graph_contour import compute_directivity_deg, compute_contour

pd.set_option("display.max_rows", 1000)

logger = logging.getLogger("spinorama")


def estimates(
    spin: pd.DataFrame, splH: pd.DataFrame, splV: pd.DataFrame
) -> dict[str, float]:
    onaxis = pd.DataFrame()
    est = {}
    try:
        if "Measurements" in spin.keys():
            onaxis = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
        else:
            onaxis = spin.get("On Axis", None)

        if onaxis.empty:
            logger.debug("On Axis measurement not found!")
            return {}

        freq_min = onaxis.Freq.min()
        logger.debug("Freq min: {0}".format(freq_min))
        if math.isnan(freq_min):
            logger.warning("Estimates failed for onaxis {0}".format(onaxis.shape))
            return {}
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
                "ref_from": 300.0,
                "ref_to": 10000.0,
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
                "ref_to": 10000.0,
            }
            if not math.isnan(y_ref):
                est["ref_level"] = round(y_ref, 0)
            if not math.isnan(band):
                est["ref_band"] = round(band, 1)

        for orientation in ("horizontal", "vertical"):
            spl = splH
            if orientation == "vertical":
                spl = splV
            if spl is not None and not spl.empty:
                af, am, az = compute_contour(spl)
                dir_deg_p, dir_deg_m, dir_deg = compute_directivity_deg(af, am, az)
                est["dir_{}_p".format(orientation)] = dir_deg_p
                est["dir_{}_m".format(orientation)] = dir_deg_m
                est["dir_{}".format(orientation)] = dir_deg

        logger.debug("Estimates: {0}".format(est))
        return est
    except TypeError as te:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, te))
    except ValueError as ve:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, ve))
    return {}
