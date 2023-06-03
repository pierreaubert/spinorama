# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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
import numpy as np
import pandas as pd

from spinorama import logger
from spinorama.constant_paths import (
    MIDRANGE_MIN_FREQ,
    MIDRANGE_MAX_FREQ,
    SENSITIVITY_MIN_FREQ,
    SENSITIVITY_MAX_FREQ,
)
from spinorama.compute_misc import (
    compute_directivity_deg_v2,
)

pd.set_option("display.max_rows", 1000)


def estimates_spin(spin: pd.DataFrame) -> dict[str, float]:
    onaxis = pd.DataFrame()
    est = {}
    try:
        if "Measurements" in spin:
            onaxis = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
        elif "On Axis" in spin:
            onaxis["Freq"] = spin.Freq
            onaxis["dB"] = spin["On Axis"]

        if onaxis.empty:
            logger.error("On Axis measurement not found!")
            return {}

        freq_min = onaxis.Freq.min()
        freq_max = onaxis.Freq.max()
        logger.debug("Freq min: %f", freq_min)
        if math.isnan(freq_min) or math.isnan(freq_max):
            logger.error("Estimates failed for onaxis %s", onaxis.shape)
            return {}

        # mean over 300-10k
        y_data = onaxis.loc[
            (onaxis.Freq >= max(freq_min, MIDRANGE_MIN_FREQ))
            & (onaxis.Freq <= min(freq_max, MIDRANGE_MAX_FREQ))
        ].dB

        y_ref = np.mean(y_data) if not y_data.empty else 0.0
        y_3 = None
        y_6 = None
        logger.debug("mean over %f-%f Hz = %f", MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ, y_ref)
        restricted_onaxis = onaxis.loc[(onaxis.Freq < MIDRANGE_MIN_FREQ)]
        # note that this is not necessary the max
        restricted_onaxis_3 = restricted_onaxis.dB < (y_ref - 3)
        if len(restricted_onaxis_3) > 0:
            y_3_idx = np.argmin(restricted_onaxis_3)
            y_3 = restricted_onaxis.Freq[y_3_idx]
        # note that this is not necessary the max
        restricted_onaxis_6 = restricted_onaxis.dB < (y_ref - 6)
        if len(restricted_onaxis_6) > 0:
            y_6_idx = np.argmin(restricted_onaxis_6)
            y_6 = restricted_onaxis.Freq[y_6_idx]
        logger.debug("-3 and -6: %fHz and %fHz", y_3, y_6)
        #
        up: float = onaxis.loc[
            (onaxis.Freq >= MIDRANGE_MIN_FREQ) & (onaxis.Freq <= MIDRANGE_MAX_FREQ)
        ].dB.max()
        down: float = onaxis.loc[(onaxis.Freq >= 100) & (onaxis.Freq <= 10000)].dB.min()
        band = max(abs(up - y_ref), abs(y_ref - down))
        logger.debug("band [%s]", band)
        est = {
            "ref_from": float(MIDRANGE_MIN_FREQ),
            "ref_to": float(MIDRANGE_MAX_FREQ),
        }
        if not math.isnan(y_ref):
            est["ref_level"] = round(y_ref, 1)
        if y_3 is not None and not math.isnan(y_3):
            est["ref_3dB"] = round(y_3, 1)
        if y_6 is not None and not math.isnan(y_6):
            est["ref_6dB"] = round(y_6, 1)
        if not math.isnan(band):
            est["ref_band"] = round(band, 1)

        logger.debug("est v1 %s", est)

        # estimate sensivity for passive speakers
        if onaxis is not None:
            est["sensitivity_delta"] = onaxis.loc[
                (onaxis.Freq >= SENSITIVITY_MIN_FREQ) & (onaxis.Freq <= SENSITIVITY_MAX_FREQ)
            ].dB.mean()

        logger.debug("est v2 %s", est)

    except TypeError:
        logger.exception("Estimates failed for %s", onaxis.shape)
        return {}
    except ValueError:
        logger.exception("Estimates failed for %s", onaxis.shape)
        return {}

    return est


def estimates(spin: pd.DataFrame, spl_h: pd.DataFrame, spl_v: pd.DataFrame) -> dict[str, float]:
    onaxis = pd.DataFrame()
    est = estimates_spin(spin)
    try:
        for orientation in ("horizontal", "vertical"):
            spl = spl_h
            if orientation == "vertical":
                spl = spl_v
            if spl is not None and not spl.empty:
                try:
                    dir_deg_p, dir_deg_m, dir_deg = compute_directivity_deg_v2(spl)
                    est["dir_{}_p".format(orientation)] = dir_deg_p
                    est["dir_{}_m".format(orientation)] = dir_deg_m
                    est["dir_{}".format(orientation)] = dir_deg
                except Exception as error:
                    logger.warning("Computing directivity failed! %s", error)

        logger.debug("Estimates v3: %s", est)
    except TypeError as type_error:
        logger.warning("Estimates failed for %s with %s", onaxis.shape, type_error)
        return {}
    except ValueError as value_error:
        logger.warning("Estimates failed for %s with %s", onaxis.shape, value_error)
        return {}

    return est
