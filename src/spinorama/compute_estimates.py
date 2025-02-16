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
import numpy as np
import pandas as pd

from spinorama import logger
from spinorama.constant_paths import (
    MIDRANGE_MIN_FREQ,
    MIDRANGE_MAX_FREQ,
    SENSITIVITY_MIN_FREQ,
    SENSITIVITY_MAX_FREQ,
)
from spinorama.compute_misc import compute_directivity_deg_v2, compute_slope_smoothness

pd.set_option("display.max_rows", 1000)


def estimates_slopes(spin: pd.DataFrame) -> dict[str, dict[str, dict[str, float]]]:
    est = {}
    if "Measurements" not in spin:
        logger.info("Measurements not in spin (%s)", ", ".join(spin.keys()))
        return est
    for measurement in (
        "On Axis",
        "Listening Window",
        "Sound Power",
        "Early Reflections",
        "Sound Power DI",
        "Early Reflections DI",
    ):
        _, _, slope, sm = compute_slope_smoothness(
            data_frame=spin, measurement=measurement, is_normalized=False
        )
        est[measurement] = {
            "slope": slope,
            "smoothness": sm,
        }
    return {"slopes": est}


def estimates_spin(spin: pd.DataFrame) -> dict[str, float]:
    """Compute values that you can derive from the spinorama"""
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

        midrange = (onaxis.Freq >= max(freq_min, MIDRANGE_MIN_FREQ)) & (
            onaxis.Freq <= min(freq_max, MIDRANGE_MAX_FREQ)
        )

        logger.debug("Freq min: %f", freq_min)
        if math.isnan(freq_min) or math.isnan(freq_max):
            logger.error("Estimates failed for onaxis %s", onaxis.shape)
            return {}

        # mean over 300-10k
        y_data = onaxis.loc[midrange].dB

        y_ref = np.mean(y_data) if not y_data.empty else 0.0
        logger.debug("mean over %f-%f Hz = %f", MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ, y_ref)
        restricted_onaxis = onaxis.loc[(onaxis.Freq < MIDRANGE_MIN_FREQ)]
        # note that this is not necessary the max
        for y_name, y_delta in (
            ("ref_3dB", 3),
            ("ref_6dB", 6),
            ("ref_9dB", 9),
            ("ref_12dB", 12),
        ):
            y_val = None
            restricted_onaxis_y = restricted_onaxis.dB < (y_ref - y_delta)
            if len(restricted_onaxis_y) > 0:
                y_idx = np.argmin(restricted_onaxis_y)
                y_val = restricted_onaxis.Freq[y_idx]
            if y_val is not None and not math.isnan(y_val):
                est[y_name] = round(y_val, 1)
            logger.debug(
                "-%fdB : %fHz",
                y_delta,
                y_val if y_val is not None else -1.0,
            )

        #
        up: float = onaxis.loc[midrange].dB.max()
        down: float = onaxis.loc[midrange].dB.min()
        band = max(abs(up - y_ref), abs(y_ref - down))
        logger.debug("band [%s]", band)
        est["ref_from"] = float(MIDRANGE_MIN_FREQ)
        est["ref_to"] = float(MIDRANGE_MAX_FREQ)
        if not math.isnan(y_ref):
            est["ref_level"] = round(y_ref, 1)
        if not math.isnan(band):
            est["ref_band"] = round(band, 1)

        logger.debug("est v1 %s", est)

        # estimate sensivity for passive speakers
        if onaxis is not None:
            est["sensitivity_delta"] = onaxis.loc[
                (onaxis.Freq >= SENSITIVITY_MIN_FREQ) & (onaxis.Freq <= SENSITIVITY_MAX_FREQ)
            ].dB.mean()

        logger.debug("est v2 %s", est)

        # estimate how constant the directivity is
        # see https://3d3a.princeton.edu/sites/g/files/toruqf931/files/documents/Sridhar_AES140_CDMetrics.pdf
        if "Measurements" in spin:
            spdi = spin.loc[spin["Measurements"] == "Sound Power DI"].reset_index(drop=True)
            if spdi is not None:
                est["dir_constant"] = spdi.dB.std()
                logger.debug("Constant directivity %d", est["dir_constant"])

    except TypeError:
        logger.exception("Estimates failed for %s", onaxis.shape)
        return {}
    except ValueError:
        logger.exception("Estimates failed for %s", onaxis.shape)
        return {}

    return est


def estimates(spin: pd.DataFrame, spl_h: pd.DataFrame, spl_v: pd.DataFrame) -> dict[str, float]:
    """Compute values when you do not necessary have all the 72 measurements"""
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
                except KeyError as error:
                    # missing data
                    logger.debug("Computing %s directivity failed! %s", orientation, error)
                except Exception as error:
                    logger.warning("Computing %s directivity failed! %s", orientation, error)

        slopes = estimates_slopes(spin)
        if "slopes" in slopes:
            for k, v in slopes["slopes"].items():
                est["slope_{}".format(k.replace(" ", "_").lower())] = v["slope"]
                est["smoothness_{}".format(k.replace(" ", "_").lower())] = v["smoothness"]

        logger.debug("Estimates v3: %s", est)
    except TypeError as type_error:
        logger.warning("Estimates failed with %s", type_error)
        return {}
    except ValueError as value_error:
        logger.warning("Estimates failed with %s", value_error)
        return {}

    return est


def compute_sensitivity_distance(sensitivity: float, mformat: str, distance: float) -> float:
    """Compute sensitivity as a function of the measurement distance"""
    sensitivity_delta = 0.0
    # assume monopole dispersion, can do better since we know the dispersion
    # at least horizontally and vertically
    if distance == 2.0:
        sensitivity_delta = 6.0
    elif distance == 2.5:
        sensitivity_delta = 8.0
    elif distance == 3.0:
        sensitivity_delta = 9.5
    elif distance == 4.0:
        sensitivity_delta = 12.0
    elif distance == 5.0:
        sensitivity_delta = 14.0
    elif distance == 10.0:
        sensitivity_delta = 20.0
    elif distance != 1.0:
        logger.warning("%s distance is unknown", distance)
    return sensitivity + sensitivity_delta


def compute_sensitivity(spl, mformat: str, distance: float) -> tuple[float, float]:
    """Compute sensitivity

    By default, distance is 1 meter. If not, you will have 2 different values:
    - a computed value at the measurement distance
    - an estimated value at 1 meter
    """
    sensitivity = np.mean(
        spl.loc[(spl.Freq > SENSITIVITY_MIN_FREQ) & (spl.Freq < SENSITIVITY_MAX_FREQ)]["On Axis"]
    )
    sensitivity_1m = compute_sensitivity_distance(sensitivity, mformat, distance)
    return sensitivity, sensitivity_1m


def compute_sensitivity_details(
    spl, curve: str, mformat: str, distance: float
) -> tuple[float, float]:
    """Compute sensitivity for a specific curve. It could be on axis or listening window for example"""
    sensitivity = np.mean(
        spl.loc[
            (spl.Freq > SENSITIVITY_MIN_FREQ)
            & (spl.Freq < SENSITIVITY_MAX_FREQ)
            & (spl.Measurements == curve)
        ].dB
    )

    sensitivity_1m = compute_sensitivity_distance(sensitivity, mformat, distance)
    return sensitivity, sensitivity_1m
