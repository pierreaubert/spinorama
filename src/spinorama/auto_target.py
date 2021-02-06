#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
from scipy.stats import linregress

logger = logging.getLogger("spinorama")

# ------------------------------------------------------------------------------
# compute freq and targets
# ------------------------------------------------------------------------------


def get_selector(df, optim_config):
    return (df["Freq"] > optim_config["freq_reg_min"]) & (
        df["Freq"] < optim_config["freq_reg_max"]
    )


def get_freq(df_speaker_data, optim_config):
    """extract freq and one curve"""
    curves = optim_config["curve_names"]
    # extract LW
    columns = {"Freq"}.union(curves)
    local_df = df_speaker_data["CEA2034_unmelted"].loc[:, columns]
    # selector
    selector = get_selector(local_df, optim_config)
    # freq
    local_freq = local_df.loc[selector, "Freq"].values
    local_target = []
    for curve in curves:
        local_target.append(local_df.loc[selector, curve].values)
    return local_df, local_freq, local_target


def get_target(df_speaker_data, freq, current_curve_name, optim_config):
    # freq
    selector = get_selector(df_speaker_data, optim_config)
    current_curve = df_speaker_data.loc[selector, current_curve_name].values
    # compute linear reg on lw
    slope, intercept, r_value, p_value, std_err = linregress(
        np.log10(freq), current_curve
    )
    # normalise to have a flat target (primarly for bright speakers)
    if current_curve_name == "On Axis":
        slope = 0
    elif current_curve_name == "Listening Window":
        # slighlithy downward
        slope = -2
    elif current_curve_name == "Early Reflections":
        slope = -5
    elif current_curve_name == "Sound Power":
        slope = -8
    else:
        logger.error("No match for getTarget")
        return None
    slope /= math.log10(freq[-1]) - math.log10(freq[0])
    intercept = current_curve[0] - slope * math.log10(freq[0])
    line = [slope * math.log10(f) for f in freq] + intercept
    logger.debug(
        "Slope {} Intercept {} R {} P {} err {}".format(
            slope, intercept, r_value, p_value, std_err
        )
    )
    logger.debug(
        "Target_interp from {:.1f}dB at {}Hz to {:.1f}dB at {}Hz".format(
            line[0], freq[0], line[-1], freq[-1]
        )
    )
    return line
