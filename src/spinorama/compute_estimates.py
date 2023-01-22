# -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd

from .constant_paths import MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ
from .compute_misc import (
    compute_contour,
    compute_directivity_deg,
    compute_directivity_deg_v2,
)

pd.set_option("display.max_rows", 1000)

logger = logging.getLogger("spinorama")


def estimates_spin(spin: pd.DataFrame) -> dict[str, float]:
    onaxis = pd.DataFrame()
    est = {}
    try:
        if "Measurements" in spin.keys():
            onaxis = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
        elif "On Axis" in spin.keys():
            onaxis["Freq"] = spin.Freq
            onaxis["dB"] = spin["On Axis"]

        if onaxis.empty:
            print("On Axis measurement not found!")
            return {}

        freq_min = onaxis.Freq.min()
        freq_max = onaxis.Freq.max()
        print("Freq min: {0}".format(freq_min))
        if math.isnan(freq_min) or math.isnan(freq_max):
            print("Estimates failed for onaxis {0}".format(onaxis.shape))
            return {}

        # mean over 300-10k
        y_ref = np.mean(
            onaxis.loc[(onaxis.Freq >= max(freq_min, MIDRANGE_MIN_FREQ)) & (onaxis.Freq <= min(freq_max, MIDRANGE_MAX_FREQ))].dB
        )
        print("mean over {}-{} Hz = {}".format(MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ, y_ref))
        restricted_onaxis = onaxis.loc[(onaxis.Freq < MIDRANGE_MIN_FREQ)]
        # note that this is not necessary the max
        y_3_idx = np.argmin(restricted_onaxis.dB < y_ref - 3)
        y_3 = restricted_onaxis.Freq[y_3_idx]
        # note that this is not necessary the max
        y_6_idx = np.argmin(restricted_onaxis.dB < y_ref - 6)
        y_6 = restricted_onaxis.Freq[y_6_idx]
        print("-3 and -6: {}Hz and {}Hz".format(y_3, y_6))
        #
        up: float = onaxis.loc[(onaxis.Freq >= MIDRANGE_MIN_FREQ) & (onaxis.Freq <= MIDRANGE_MAX_FREQ)].dB.max()
        down: float = onaxis.loc[(onaxis.Freq >= 100) & (onaxis.Freq <= 10000)].dB.min()
        band = max(abs(up - y_ref), abs(y_ref - down))
        print("band {}".format(band))
        est = {
            "ref_from": MIDRANGE_MIN_FREQ,
            "ref_to": MIDRANGE_MAX_FREQ,
        }
        if not math.isnan(y_ref):
            est["ref_level"] = round(y_ref, 1)
        if not math.isnan(y_3):
            est["ref_3dB"] = round(y_3, 1)
        if not math.isnan(y_6):
            est["ref_6dB"] = round(y_6, 1)
        if not math.isnan(band):
            est["ref_band"] = round(band, 1)

        print("est v1 {}".format(est))

        # estimate sensivity for passive speakers
        if onaxis is not None:
            est["sensitivity_delta"] = onaxis.loc[
                (onaxis.Freq >= MIDRANGE_MIN_FREQ) & (onaxis.Freq <= MIDRANGE_MAX_FREQ)
            ].dB.mean()

        print("est v2 {}".format(est))

        return est
    except TypeError as te:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, te))
    except ValueError as ve:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, ve))
    return {}


def estimates(spin: pd.DataFrame, splH: pd.DataFrame, splV: pd.DataFrame) -> dict[str, float]:
    onaxis = pd.DataFrame()
    est = estimates_spin(spin)
    try:
        for orientation in ("horizontal", "vertical"):
            spl = splH
            if orientation == "vertical":
                spl = splV
            if spl is not None and not spl.empty:
                try:
                    dir_deg_p, dir_deg_m, dir_deg = compute_directivity_deg_v2(spl)
                    est["dir_{}_p".format(orientation)] = dir_deg_p
                    est["dir_{}_m".format(orientation)] = dir_deg_m
                    est["dir_{}".format(orientation)] = dir_deg
                except Exception as e:
                    logger.warning("Computing directivity failed! {}".format(e))

        logger.debug("Estimates v3: {0}".format(est))
        return est
    except TypeError as te:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, te))
    except ValueError as ve:
        logger.warning("Estimates failed for {0} with {1}".format(onaxis.shape, ve))
    return {}
