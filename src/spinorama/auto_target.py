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


def get_selector(df, optim_config):
    return (df["Freq"] > optim_config["freq_reg_min"]) & (
        df["Freq"] < optim_config["freq_reg_max"]
    )


def get_freq(df_speaker_data, optim_config):
    """extract freq and one curve"""
    curves = optim_config["curve_names"]
    local_curves = curves
    with_pir = False
    if "Estimated In-Room Response" in curves:
        local_curves = [c for c in curves if c != "Estimated In-Room Response"]
        with_pir = True

    # extract LW
    local_df = None
    if len(local_curves) > 0:
        columns = {"Freq"}.union(local_curves)
        if "CEA2034_unmelted" in df_speaker_data.keys():
            local_df = df_speaker_data["CEA2034_unmelted"].loc[:, columns]
        else:
            df_tmp = df_speaker_data["CEA2034"]
            try:
                # df_pivoted = df_tmp.pivot(*df_tmp).rename_axis(columns=None).reset_index()
                df_pivoted = df_tmp.pivot_table(
                    index="Freq", columns="Measurements", values="dB", aggfunc=max
                ).reset_index()
                local_df = df_pivoted.loc[:, columns]
            except ValueError as ve:
                print("debug: {} {}".format(df_tmp.keys(), ve))
                print("{}".format(df_tmp.index.duplicated()))
                return None, None, None
            except KeyError as ke:
                print("debug: columns {} {}".format(columns, ke))
                print("debug: {}".format(df_tmp.keys()))
                return None, None, None

    if with_pir:
        pir_source = df_speaker_data["Estimated In-Room Response"]
        if local_df is None:
            local_df = pd.DataFrame(
                {"Freq": pir_source.Freq, "Estimated In-Room Response": pir_source.dB}
            )
        else:
            local_df["Estimated In-Room Response"] = pir_source.dB.values

    # sselector
    selector = get_selector(local_df, optim_config)
    local_freq = local_df.loc[selector, "Freq"].values

    # freq
    local_target = []
    for curve in curves:
        local_target.append(local_df.loc[selector, curve].values)

    # print(local_df, local_freq, local_target)
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

    if current_curve_name != None:  # "Estimated In-Room Response":
        slope /= math.log10(freq[last_freq]) - math.log10(freq[first_freq])
        intercept = current_curve[first_freq] - slope * math.log10(freq[first_freq])
        flat = slope * math.log10(freq[first_freq])
        line = [
            flat if i < first_freq else slope * math.log10(f)
            for i, f in enumerate(freq)
        ] + intercept
        # if current_curve_name == 'Listening Window':
        #    line = [flat for f in freq[:freq_1k5]] + \
        #        [slope*math.log10(f)-0.25 for f in freq[freq_1k5, freq_4k]] + \
        #        [slope*math.log10(f)-1 for f in freq[freq_4k:]]
        #    line += intercept

        logger.debug(
            "Slope {} Intercept {} R {} P {} err {}".format(
                slope, intercept, r_value, p_value, std_err
            )
        )
        logger.debug(
            "Target_interp from {:.1f}dB at {}Hz to {:.1f}dB at {}Hz".format(
                line[first_freq], freq[first_freq], line[last_freq], freq[last_freq]
            )
        )
        return line

    # experiment to see if another target for PIR would help
    # PIR data from https://www.audiosciencereview.com/forum/index.php?threads/erin-posted-the-emotiva-airmotiv-t2-tower-speaker-review.28360/page-3#post-990830
    pir_data = [
        (100.7, -0.0),
        (115.8, -0.3),
        (133.0, -0.6),
        (152.9, -0.9),
        (175.7, -1.2),
        (201.9, -1.5),
        (232.1, -1.7),
        (266.7, -2.0),
        (306.5, -2.2),
        (352.3, -2.4),
        (404.8, -2.6),
        (465.3, -2.7),
        (534.7, -2.9),
        (614.5, -3.0),
        (706.2, -3.2),
        (811.6, -3.3),
        (932.8, -3.4),
        (1072.0, -3.6),
        (1232.0, -3.7),
        (1415.8, -3.8),
        (1627.1, -3.9),
        (1870.0, -4.0),
        (2149.1, -4.0),
        (2469.9, -4.1),
        (2838.5, -4.2),
        (3262.1, -4.3),
        (3749.0, -4.4),
        (4308.6, -4.4),
        (4951.6, -4.5),
        (5690.7, -4.6),
        (6540.0, -4.6),
        (7516.1, -4.7),
        (8637.9, -4.7),
        (9927.1, -4.8),
        (11408.7, -4.8),
        (13111.5, -4.9),
        (15068.4, -5.0),
        (17317.4, -5.0),
        (18801.1, -5.0),
    ]

    target = np.interp(
        x=freq,
        xp=[p[0] for p in pir_data],
        fp=[p[1] for p in pir_data],
        left=0,
        right=-5.0,
    )
    # print(target)
    return target
