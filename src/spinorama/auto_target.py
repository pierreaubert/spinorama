#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2022 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import logging
import math
import numpy as np
import pandas as pd
from scipy.stats import linregress

logger = logging.getLogger("spinorama")

# ------------------------------------------------------------------------------
# compute freq and targets
# ------------------------------------------------------------------------------


def limit_before_freq(freq, curve, min_freq):
    i_min = 0
    while i_min < len(freq) and freq[i_min] < min_freq:
        i_min += 1
    return [curve[i] if i > i_min else curve[i_min] for i in range(0, len(curve))]


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
    local_df = None
    if len(curves) > 0:
        columns = {"Freq"}.union(local_curves)
        if "CEA2034_unmelted" in df_speaker_data.keys():
            local_df = df_speaker_data["CEA2034_unmelted"].loc[:, list(columns)]
        else:
            df_tmp = df_speaker_data["CEA2034"]
            try:
                # df_pivoted = df_tmp.pivot(*df_tmp).rename_axis(columns=None).reset_index()
                df_pivoted = df_tmp.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max).reset_index()
                local_df = df_pivoted.loc[:, columns]
            except ValueError as ve:
                # print("debug: {} {}".format(df_tmp.keys(), ve))
                # print("{}".format(df_tmp.index.duplicated()))
                return None, None, None
            except KeyError as ke:
                # print("debug: columns {} {}".format(columns, ke))
                # print("debug: {}".format(df_tmp.keys()))
                return None, None, None

    if with_pir:
        pir_source = df_speaker_data["Estimated In-Room Response"]
        if local_df is None:
            local_df = pd.DataFrame({"Freq": pir_source.Freq, "Estimated In-Room Response": pir_source.dB})
        else:
            local_df["Estimated In-Room Response"] = pir_source.dB.values

    # sselector
    selector = get_selector(local_df, optim_config)
    local_freq = local_df.loc[selector, "Freq"].values

    # freq
    local_target = []
    for curve in curves:
        data = local_df.loc[selector, curve].values
        data = limit_before_freq(local_freq, data, optim_config["target_min_freq"])
        local_target.append(data)

    # print(local_df, local_freq, local_target)
    return local_df, local_freq, local_target


def get_target(df_speaker_data, freq, current_curve_name, optim_config):
    # freq
    selector = get_selector(df_speaker_data, optim_config)
    current_curve = df_speaker_data.loc[selector, current_curve_name].values
    # compute linear reg on current_curve
    slope, intercept, r_value, p_value, std_err = linregress(np.log10(freq), current_curve)
    # possible correction to have a LW not too bright
    if current_curve_name == "Estimated In-Room Response":
        lw_curve = df_speaker_data.loc[selector, "Listening Window"].values
        slope_lw, _, _, _, _r = linregress(np.log10(freq), lw_curve)
        if slope_lw > -0.5:
            # print('slope correction on LW by -{}'.format((slope_lw+0.5)))
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
    freq_1k5 = 0
    freq_4k = 0

    for i, f in enumerate(freq):
        if f >= optim_config["target_min_freq"]:
            first_freq = i
            break
    for i, f in enumerate(freq):
        if f >= 1500:
            freq_1k5 = i
            break
    for i, f in enumerate(freq):
        if f >= 4000:
            freq_4k = i
            break
    for i, f in enumerate(reversed(freq)):
        if f <= optim_config["target_max_freq"]:
            last_freq = -(i + 1)
            break

    if current_curve_name is None:
        return None

    # print('first freq[{}]={} last freq[{}]={}'.format(first_freq, freq[first_freq], last_freq, freq[last_freq]))
    slope /= math.log10(freq[last_freq]) - math.log10(freq[first_freq])
    # print('current curve {}'.format(current_curve[first_freq]))
    # intercept = current_curve[first_freq] - slope * math.log10(freq[first_freq])
    intercept = -slope * math.log10(freq[first_freq])
    # print("Slope {} Intercept {} R {} P {} err {}".format(slope, intercept, r_value, p_value, std_err))
    flat = slope * math.log10(freq[first_freq])
    # print('Flat {}'.format(flat))
    line = np.array([flat if i < first_freq else slope * math.log10(f) for i, f in enumerate(freq)]) + intercept
    # print('Line {}'.format(line))
    # print(
    #    "Target_interp from {:.1f}dB at {}Hz to {:.1f}dB at {}Hz".format(
    #        line[first_freq], freq[first_freq], line[last_freq], freq[last_freq]
    #    )
    # )
    return line
