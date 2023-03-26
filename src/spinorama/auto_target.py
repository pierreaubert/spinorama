# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
from scipy.stats import linregress

from spinorama import logger
from spinorama.ltype import Peq, Vector
from spinorama.filter_peq import peq_build
from spinorama.compute_misc import savitzky_golay


# ------------------------------------------------------------------------------
# compute freq and targets
# ------------------------------------------------------------------------------


def limit_before_freq(freq: Vector, curve: list[Vector], min_freq: float) -> list[Vector]:
    i_min = 0
    while i_min < len(freq) and freq[i_min] < min_freq:
        i_min += 1
    db_cut = np.sign(curve[i_min]) * min(3, abs(curve[i_min]))
    return [curve[i] if i > i_min else db_cut for i in range(0, len(curve))]


def get_selector(df, optim_config):
    return (df["Freq"] > optim_config["freq_reg_min"]) & (df["Freq"] < optim_config["freq_reg_max"])


def get_freq(df_speaker_data, optim_config):
    """extract freq and one curve"""
    curves = optim_config["curve_names"]
    with_pir = False
    local_curves = []
    if "Estimated In-Room Response" in curves:
        local_curves = [c for c in curves if c != "Estimated In-Room Response"]
        if "Listening Window" not in set(local_curves):
            local_curves.append("Listening Window")
        with_pir = True
    else:
        local_curves = curves

    # extract LW
    local_df = pd.DataFrame()
    if len(curves) > 0:
        columns = {"Freq"}.union(local_curves)
        if "CEA2034_unmelted" in df_speaker_data:
            local_df = df_speaker_data["CEA2034_unmelted"].loc[:, list(columns)]
        else:
            df_tmp = df_speaker_data["CEA2034"]
            try:
                df_pivoted = df_tmp.pivot_table(
                    index="Freq", columns="Measurements", values="dB", aggfunc=max
                ).reset_index()
                local_df = df_pivoted.loc[:, columns]
            except ValueError as value_error:
                logger.debug("%s %s", df_tmp.keys(), value_error)
                return None, None, None
            except KeyError as key_error:
                logger.debug("columns %s %s", columns, key_error)
                return None, None, None

    if with_pir:
        pir_source = df_speaker_data["Estimated In-Room Response"]
        if local_df.empty:
            local_df = pd.DataFrame(
                {"Freq": pir_source.Freq, "Estimated In-Room Response": pir_source.dB}
            )
        else:
            local_df["Estimated In-Room Response"] = pir_source.dB.to_numpy()

    # sselector
    selector = get_selector(local_df, optim_config)
    local_freq = local_df.loc[selector, "Freq"].to_numpy()

    # freq
    local_target = []
    for curve in curves:
        data = local_df.loc[selector, curve].to_numpy()
        data = limit_before_freq(local_freq, data, optim_config["target_min_freq"])
        local_target.append(data)

    return local_df, local_freq, local_target


def get_target(df_speaker_data, freq, current_curve_name, optim_config):
    # freq
    selector = get_selector(df_speaker_data, optim_config)
    current_curve = df_speaker_data.loc[selector, current_curve_name].to_numpy()
    # compute linear reg on current_curve
    slope, intercept, r_value, p_value, std_err = linregress(np.log10(freq), current_curve)
    # possible correction to have a LW not too bright
    if current_curve_name == "Estimated In-Room Response":
        lw_curve = df_speaker_data.loc[selector, "Listening Window"].to_numpy()
        slope_lw, _, _, _, _r = linregress(np.log10(freq), lw_curve)
        if slope_lw > -0.5:
            slope -= slope_lw + 0.5

    # normalise to have a flat target (primarly for bright speakers)
    if current_curve_name == "On Axis":
        slope = optim_config["slope_on_axis"]
    elif current_curve_name == "Listening Window":
        # slighlithy downward
        slope = optim_config["slope_listening_window"]
    elif current_curve_name == "Early Reflections":
        slope = optim_config["slope_early_reflections"]
    elif current_curve_name == "Sound Power":
        slope = optim_config["slope_sound_power"]
    elif current_curve_name == "Estimated In-Room Response":
        slope = optim_config["slope_estimated_inroom"]
    else:
        logger.error("No match for getTarget")
        return None

    # find target min and max
    first_freq = 0
    last_freq = -1

    for i, f in enumerate(freq):
        if f >= optim_config["target_min_freq"]:
            first_freq = i
            break
    for i, f in enumerate(reversed(freq)):
        if f <= optim_config["target_max_freq"]:
            last_freq = -(i + 1)
            break

    if current_curve_name is None:
        return None

    slope /= math.log10(freq[last_freq]) - math.log10(freq[first_freq])
    intercept = -slope * math.log10(freq[first_freq])
    flat = slope * math.log10(freq[first_freq])
    line = (
        np.array([flat if i < first_freq else slope * math.log10(f) for i, f in enumerate(freq)])
        + intercept
    )
    return line


def optim_compute_auto_target(
    freq: Vector,
    target: list[Vector],
    auto_target_interp: list[Vector],
    peq: Peq,
    optim_config: dict,
) -> list[Vector]:
    """Define the target for the optimiser with potentially some smoothing"""
    peq_freq = peq_build(freq, peq)
    diff = [np.subtract(target[i], auto_target_interp[i]) for i, _ in enumerate(target)]
    if optim_config.get("smooth_measurements"):
        window_size = optim_config.get("smooth_window_size")
        order = optim_config.get("smooth_order")
        smoothed = [savitzky_golay(d, window_size, order) for d in diff]
        diff = smoothed
    delta = [np.add(diff[i], peq_freq).tolist() for i, _ in enumerate(target)]
    return delta
