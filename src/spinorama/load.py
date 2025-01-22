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

import os
import sys

import numpy as np
import pandas as pd

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray

from datas import Symmetry, Parameters

from spinorama import logger, ray_setup_logger
from spinorama.ltype import DataSpeaker
from spinorama.constant_paths import MEAN_MIN, MEAN_MAX

from spinorama.filter_peq import Peq, peq_apply_measurements
from spinorama.filter_scores import noscore_apply_filter

from spinorama.compute_misc import unify_freq
from spinorama.compute_estimates import compute_sensitivity, compute_sensitivity_details

from spinorama.misc import graph_melt, graph_unmelt, check_nan, sort_angles
from spinorama.load_klippel import parse_graphs_speaker_klippel
from spinorama.load_princeton import parse_graphs_speaker_princeton
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load_rew_eq import parse_eq_iir_rews
from spinorama.load_spl_hv_txt import parse_graphs_speaker_spl_hv_txt
from spinorama.load_gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer

from spinorama.constant_paths import (
    MIDRANGE_MIN_FREQ,
    MIDRANGE_MAX_FREQ,
)
from spinorama.compute_cea2034 import (
    early_reflections,
    vertical_reflections,
    horizontal_reflections,
    compute_cea2034,
    compute_onaxis,
    estimated_inroom,
    estimated_inroom_hv,
)


def _shift_spl_unmelted(spl: pd.DataFrame, mean: float) -> pd.DataFrame:
    """Shift all measurements in a DataFrame by a mean value.

    Args:
        spl: DataFrame containing SPL measurements with 'Freq' and measurement columns
        mean: Mean value to subtract from all measurements

    Returns:
        DataFrame with all measurements shifted by the mean value
    """
    spl_copy = spl.copy()
    for c in spl.columns:
        if c == "Freq":
            continue
        if "DI" in c:
            spl_copy[c] = spl[c]
        else:
            spl_copy[c] = spl[c] - mean
    return spl_copy


def shift_spl(spl: pd.DataFrame, mean: float) -> pd.DataFrame:
    """Shift a single melted SPL measurement by a mean value.

    Args:
        spl: Melted DataFrame with columns ['Freq', 'Measurements', 'dB']
        mean: Mean value to subtract from the dB values

    Returns:
        DataFrame with dB values shifted by the mean value
    """
    if "Measurements" in spl:
        return _shift_spl_unmelted(graph_unmelt(spl), mean)
    return _shift_spl_unmelted(spl, mean)


def _normalize_spl_unmelted(spl: pd.DataFrame, on: np.array) -> pd.DataFrame:
    """Normalize SPL measurements relative to the On Axis measurement.

    Args:
        spl: DataFrame with SPL measurements including 'On Axis' measurement

    Returns:
        DataFrame with all measurements normalized relative to On Axis

    Notes:
        All measurements including DI (Directivity Index) are normalized
    """
    # check
    if "dB" in spl:
        raise KeyError
    # nornalize v.s. on axis
    df_normalized = pd.DataFrame({"Freq": spl.Freq})
    for k in spl:
        if k == "Freq":
            continue
        if "DI" in k:
            df_normalized[k] = spl[k]
        else:
            df_normalized[k] = spl[k] - on
    return df_normalized


def normalize_spl(spl: pd.DataFrame, on: pd.DataFrame | None = None) -> pd.DataFrame:
    spl_unmelted = spl
    if "Measurements" in spl:
        spl_unmelted = graph_unmelt(spl)
    if on is None:
        if "On Axis" not in spl_unmelted:
            raise KeyError
        on = spl_unmelted["On Axis"].to_numpy()
    return _normalize_spl_unmelted(spl_unmelted, on)


def filter_graphs(
    speaker_name: str,
    h_spl: pd.DataFrame,
    v_spl: pd.DataFrame,
    mean_min: float,
    mean_max: float,
    mformat: str,
    mdistance: float,
) -> dict:
    """Filter and process a set of horizontal and vertical SPL measurements.

    Args:
        speaker_name: Name of the speaker being measured
        h_spl: DataFrame containing horizontal SPL measurements
        v_spl: DataFrame containing vertical SPL measurements
        mean_min: Minimum frequency for mean calculation
        mean_max: Maximum frequency for mean calculation
        mformat: Measurement format identifier
        mdistance: Measurement distance in meters

    Returns:
        Dictionary containing processed measurements including:
        - SPL Horizontal/Vertical
        - CEA2034
        - Estimated In-Room Response
        - Various normalized versions

    Notes:
        This function performs several operations:
        1. Filters the measurements
        2. Computes CEA2034 standard measurements
        3. Estimates in-room response
        4. Normalizes measurements relative to reference points
    """
    dfs = {}
    # add H and V SPL graphs
    mean_min_max = None
    mean_sensitivity = None
    mean_sensitivity_1m = None
    sv_spl = None
    sh_spl = None

    if h_spl is not None:
        mean_min_max = np.mean(
            h_spl.loc[(h_spl.Freq > mean_min) & (h_spl.Freq < mean_max)]["On Axis"]
        )
        mean_sensitivity, mean_sensitivity_1m = compute_sensitivity(h_spl, mformat, mdistance)
        sh_spl = shift_spl(h_spl, mean_min_max)
        dfs["SPL Horizontal"] = graph_melt(sh_spl)
        dfs["SPL Horizontal_unmelted"] = sh_spl
        dfs["SPL Horizontal_normalized_unmelted"] = normalize_spl(sh_spl)
    else:
        logger.info("h_spl is None for speaker %s", speaker_name)

    if v_spl is not None:
        if mean_min_max is None:
            mean_min_max = np.mean(
                v_spl.loc[(v_spl.Freq > mean_min) & (v_spl.Freq < mean_max)]["On Axis"]
            )
        if mean_sensitivity is None:
            mean_sensitivity, mean_sensitivity_1m = compute_sensitivity(v_spl, mformat, mdistance)
        sv_spl = shift_spl(v_spl, mean_min_max)
        dfs["SPL Vertical"] = graph_melt(sv_spl)
        dfs["SPL Vertical_unmelted"] = sv_spl
        dfs["SPL Vertical_normalized_unmelted"] = normalize_spl(sv_spl)
    else:
        logger.info("v_spl is None for speaker %s", speaker_name)

    # horrible hack for EQ speakers which are already normalized
    if mean_sensitivity is not None and mean_sensitivity > 20:
        logger.debug("%s sensitivity %f", speaker_name, mean_sensitivity)
        dfs["sensitivity"] = mean_sensitivity
        dfs["sensitivity_distance"] = mdistance
        dfs["sensitivity_1m"] = mean_sensitivity_1m
    logger.debug(
        "%s sensitivity: %f and sensitivity 1m: %f",
        speaker_name,
        mean_sensitivity,
        mean_sensitivity_1m,
    )

    # add computed graphs
    table = [
        ["Early Reflections", early_reflections],
        ["Horizontal Reflections", horizontal_reflections],
        ["Vertical Reflections", vertical_reflections],
        ["Estimated In-Room Response", estimated_inroom_hv],
        ["Estimated In-Room Response Normalized", estimated_inroom_hv],
        ["On Axis", compute_onaxis],
        ["CEA2034", compute_cea2034],
        ["CEA2034 Normalized", compute_cea2034],
    ]

    if sh_spl is None or sv_spl is None:
        #
        df_on_axis = compute_onaxis(sh_spl, sv_spl)
        dfs["On Axis_unmelted"] = df_on_axis
        dfs["On Axis"] = graph_melt(df_on_axis)
        # SPL H
        if sh_spl is not None:
            df_horizontals = horizontal_reflections(sh_spl)
            dfs["Horizontal Reflections_unmelted"] = df_horizontals
            dfs["Horizontal Reflections"] = graph_melt(df_horizontals)
        # SPL V
        if sv_spl is not None:
            df_verticals = vertical_reflections(sv_spl)
            dfs["Vectical Reflections_unmelted"] = df_verticals
            dfs["Vectical Reflections"] = graph_melt(df_verticals)
        # that's all folks
        return dfs

    for title, functor in table:
        try:
            df_funct = None
            if title == "Horizontal Reflections":
                df_funct = functor(sh_spl)
            elif title == "Vertical Reflections":
                df_funct = functor(sv_spl)
            elif "Normalized" in title:
                df_funct = functor(normalize_spl(sh_spl), normalize_spl(sv_spl))
            else:
                df_funct = functor(sh_spl, sv_spl)
            if df_funct is not None:
                dfs[title + "_unmelted"] = df_funct
                dfs[title] = graph_melt(df_funct)
            else:
                logger.info("%s computation is None for speaker %s", title, speaker_name)
        except KeyError as key_error:
            logger.warning(
                "%s computation failed with key:%s for speaker %s", title, key_error, speaker_name
            )

    df_out = {}
    for k in dfs:
        if not isinstance(dfs[k], pd.DataFrame):
            df_out[k] = dfs[k]
            continue
        if "unmelted" in k:
            if "Measurements" in dfs[k]:
                logging.error("Correct misshaped data for %s", k)
                df_out[k] = graph_unmelt(dfs[k])
            else:
                df_out[k] = dfs[k]
        else:
            if "Measurements" in dfs[k]:
                df_out[k] = dfs[k]
            else:
                logging.error("Correct misshaped data for %s", k)
                df_out[k] = graph_melt(dfs[k])
    return df_out


def filter_graphs_partial(df_in, mformat, mdistance):
    df_out = {}
    # normalize first
    mean_midrange = None
    mean_sensitivity = None
    mean_sensitivity_1m = None
    on = None
    if "CEA2034" in df_in:
        on = df_in["CEA2034"]
        if "Measurements" not in on:
            on = graph_melt(on)
    if on is None and "On Axis" in df_in and "On Axis" in df_in["On Axis"]:
        on = df_in["On Axis"]
    if on is not None:
        if "Measurements" not in on:
            on = graph_melt(on)
        logger.debug("DEBUG: filter_graph_partial")
        for curve in ("On Axis", "Listening Window"):
            if curve not in set(on.Measurements):
                continue
            mean_midrange = np.mean(
                on.loc[
                    (on.Freq > MIDRANGE_MIN_FREQ)
                    & (on.Freq < MIDRANGE_MAX_FREQ)
                    & (on.Measurements == curve)
                ].dB
            )
            mean_sensitivity, mean_sensitivity_1m = compute_sensitivity_details(
                on, curve, mformat, mdistance
            )

    if mean_midrange is None:
        mean_midrange = 0.0
    logger.debug("DEBUG: mean %f", mean_midrange)

    # add On Axis if missing
    if "On Axis" not in df_in and "CEA2034" in df_in:
        spin = df_in["CEA2034"]
        on = spin.loc[spin.Measurements == "On Axis"]
        df_in["On Axis"] = pd.DataFrame(
            {"Freq": on.Freq, "Measurements": ["On Axis"] * len(on.Freq), "dB": on.dB}
        )

    # add PIR if missing
    if "Estimated In-Room Response" not in df_in and "CEA2034" in df_in:
        logging.warning("Missing PIR for speaker %s", speaker_name)
        spin = df_in["CEA2034"]
        pir = estimated_inroom(spin)
        df_in["Estimated In-Room Response"] = graph_melt(pir)

    # check that On Axis and PIR are in the correct format
    if "On Axis" in df_in and "Measurements" not in df_in["On Axis"]:
        df_in["On Axis"] = graph_melt(df_in["On Axis"])

    if (
        "Estimated In-Room Response" in df_in
        and "Measurements" not in df_in["Estimated In-Room Response"]
    ):
        df_in["Estimated In-Room Response"] = graph_melt(df_in["Estimated In-Room Response"])

    # normalized CEA2034 and PIR wrt On-Axis
    if "CEA2034" in df_in:
        df_out["CEA2034 Normalized"] = graph_melt(normalize_spl(df_in["CEA2034"]))
        df_out["Estimated In-Room Response Normalized"] = graph_melt(
            normalize_spl(df_in["Estimated In-Room Response"], df_in["On Axis"].dB.to_numpy())
        )

    # normalized curves v.s. the mean of On-Axis
    for k in df_in:
        if isinstance(df_in[k], pd.DataFrame):
            shifted = shift_spl(df_in[k], mean_midrange)
            if "Measurements" in shifted:
                df_out[k] = shifted
            else:
                df_out[k] = graph_melt(shifted)

    # create unmelted ones for each entry in df_out (not df_in)
    previous_keys = list(df_out.keys())
    for k in previous_keys:
        unmelted = "{}_unmelted".format(k)
        if isinstance(df_out[k], pd.DataFrame):
            df_out[unmelted] = graph_unmelt(df_out[k])
        elif k not in df_out:
            df_out[k] = df_in[k]

    # update sensitivity
    if mean_sensitivity is not None and mean_sensitivity > 20:
        df_out["sensitivity"] = mean_sensitivity
        df_out["sensitivity_distance"] = mdistance
        df_out["sensitivity_1m"] = mean_sensitivity_1m

    logger.debug("DEBUG filter_graphs_partial  IN (%s)", ", ".join(df_in.keys()))
    logger.debug("DEBUG filter_graphs_partial partial OUT (%s)", ", ".join(df_out.keys()))
    return df_out


def parse_graph_freq_check(speaker_name: str, df_spin: pd.DataFrame) -> bool:
    status = True
    spin_cols = set(df_spin.Measurements.to_numpy())
    mandatory_cols = ("Listening Window", "On Axis", "Early Reflections", "Sound Power")
    other_cols = ("Early Reflections DI", "Sound Power DI")
    for col in mandatory_cols:
        if col not in spin_cols:
            logger.info("%s measurement doesn't have a %s column", speaker_name, col)
            status = False
        else:
            logger.debug(
                "Loading %s %s %.1f--%.1fHz %.1f--%.1fdB",
                speaker_name,
                col,
                df_spin.loc[df_spin.Measurements == col].Freq.min(),
                df_spin.loc[df_spin.Measurements == col].Freq.max(),
                df_spin.loc[df_spin.Measurements == col].dB.min(),
                df_spin.loc[df_spin.Measurements == col].dB.max(),
            )
    for col in spin_cols:
        if col not in mandatory_cols and col not in other_cols:
            logger.info("%s measurement have extra column %s", speaker_name, col)
    return status


def spin_compute_di_eir(
    speaker_name: str, title: str, spin_uneven: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    dfs = {}
    # some checks
    if title != "CEA2034":
        logger.debug("title is %s", title)
        return {}

    spin_melted = spin_uneven
    if "Measurements" not in spin_uneven:
        spin_melted = graph_melt(spin_uneven)

    if not parse_graph_freq_check(speaker_name, spin_melted):
        logging.error("parse graph failed for %s", speaker_name)
        dfs[title] = spin_melted
        return dfs

    spin_even = unify_freq(spin_melted)
    spin = graph_melt(spin_even)
    logger.debug("DEBUG after melt: spin %s", ",".join(list(spin.keys())))

    if spin is None:
        logger.error("spin is None")
        return {}

    # compute EIR
    on = spin.loc[spin["Measurements"] == "On Axis"].reset_index(drop=True)
    lw = spin.loc[spin["Measurements"] == "Listening Window"].reset_index(drop=True)
    er = spin.loc[spin["Measurements"] == "Early Reflections"].reset_index(drop=True)
    sp = spin.loc[spin["Measurements"] == "Sound Power"].reset_index(drop=True)

    # check DI index
    if 0 not in (lw.shape[0], sp.shape[0]):
        sp_di_computed = lw.dB - sp.dB
        sp_di = spin.loc[spin["Measurements"] == "Sound Power DI"].reset_index(drop=True)
        if sp_di.shape[0] == 0:
            logger.debug("No Sound Power DI curve, computing one!")
            df2 = pd.DataFrame(
                {
                    "Freq": on.Freq,
                    "dB": sp_di_computed,
                    "Measurements": "Sound Power DI",
                }
            )
            spin = pd.concat([spin, df2]).reset_index(drop=True)
        else:
            delta = np.mean(sp_di) - np.mean(sp_di_computed)
            logger.debug("Sound Power DI curve: removing %f", delta)
            spin.loc[spin["Measurements"] == "Sound Power DI", "dB"] -= delta
    else:
        logger.debug("Shape LW=%s SP=%s", lw.shape, sp.shape)

    if 0 not in (lw.shape[0], er.shape[0]):
        er_di_computed = lw.dB - er.dB
        er_di = spin.loc[spin["Measurements"] == "Early Reflections DI"].reset_index(drop=True)
        if er_di.shape[0] == 0:
            logger.debug("No Early Reflections DI curve!")
            df2 = pd.DataFrame(
                {
                    "Freq": on.Freq,
                    "dB": er_di_computed,
                    "Measurements": "Early Reflections DI",
                }
            )
            spin = pd.concat([spin, df2]).reset_index(drop=True)
        else:
            delta = np.mean(er_di) - np.mean(er_di_computed)
            logger.debug("Early Reflections DI curve: removing %f", delta)
            spin.loc[spin["Measurements"] == "Early Reflections DI", "dB"] -= delta
    else:
        logger.debug("Shape LW=%s ER=%s", lw.shape, er.shape)

    di_offset = spin.loc[spin["Measurements"] == "DI offset"].reset_index(drop=True)
    if di_offset.shape[0] == 0:
        logger.debug("No DI offset curve!")
        df2 = pd.DataFrame({"Freq": on.Freq, "dB": 0, "Measurements": "DI offset"})
        spin = pd.concat([spin, df2]).reset_index(drop=True)

    logger.debug("Shape ON %s LW %s ER %s SP %s", on.shape, lw.shape, er.shape, sp.shape)
    if 0 not in (lw.shape[0], er.shape[0], sp.shape[0]):
        eir = estimated_inroom(lw, er, sp)
        logger.debug("eir %s", eir.shape)
        dfs["Estimated In-Room Response"] = graph_melt(eir)
    else:
        logger.debug("Shape LW=%s ER=%s SP=%s", lw.shape, er.shape, sp.shape)

    # add spin (at the end because we could have modified DI curves
    dfs[title] = spin

    if on.isna().to_numpy().any():
        logger.error("On Axis has NaN values")

    return dfs


def symmetrise_speaker_measurements(
    h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None, symmetry: str
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    def symmetrise_measurement(spl: pd.DataFrame) -> pd.DataFrame:
        """Apply a symmetry if any to the measurements"""
        if spl.empty:
            return pd.DataFrame()

        # look for min and max
        cols = spl.columns
        min_angle = 180
        max_angle = -180
        for col in cols:
            if col == "Freq":
                continue
            angle = 0 if col == "On Axis" else int(col[:-1])
            min_angle = min(min_angle, angle)
            max_angle = max(max_angle, angle)

        # extend 0-180 to -170 0 180
        # extend 0-90  to -90 to 90
        new_spl = spl.copy()
        for col in cols:
            if col not in ("Freq", "On Axis", "180°"):
                m_angle = "{}".format(col[1:]) if col[0] == "-" else "-{}".format(col)
                if m_angle not in spl.columns:
                    new_spl[m_angle] = spl[col]
        return sort_angles(new_spl)

    if h_spl is None and v_spl is None:
        logger.error("Symmetrisation cannot work with empty measurements")
        return (None, None)

    if symmetry == "coaxial":
        if h_spl is not None:
            h_spl2 = symmetrise_measurement(h_spl)
            v_spl2 = h_spl2.copy() if v_spl is None else symmetrise_measurement(v_spl)
        else:
            v_spl2 = symmetrise_measurement(v_spl)
            h_spl2 = v_spl2.copy()
        return (h_spl2, v_spl2)
    elif h_spl is not None and symmetry == "horizontal":
        h_spl2 = symmetrise_measurement(h_spl)
        return (h_spl2, v_spl.copy() if v_spl is not None else None)
    elif v_spl is not None and symmetry == "vertical":
        v_spl2 = symmetrise_measurement(v_spl)
        return (h_spl.copy() if h_spl is not None else None, v_spl2)
    return (
        h_spl.copy() if h_spl is not None else None,
        v_spl.copy() if v_spl is not None else None,
    )


def get_mean_min_max(mparameters: Parameters | None) -> tuple[int, int]:
    # default works well for flatish speakers but not at all for line arrays for ex
    # where the mean is flat but usually high bass and low high
    mean_min = MEAN_MIN
    mean_max = MEAN_MAX
    if mparameters is not None:
        mean_min = mparameters.get("mean_min", mean_min)
        mean_max = mparameters.get("mean_max", mean_max)
    return mean_min, mean_max


@ray.remote(num_cpus=1)
def parse_eq_speaker(
    speaker_path: str,
    speaker_name: str,
    mformat: str,
    df_ref: dict,
    mparameters: Parameters | None,
    level: int,
    distance: float,
) -> tuple[Peq, DataSpeaker]:
    ray_setup_logger(level)

    iirname = "{0}/eq/{1}/iir.txt".format(speaker_path, speaker_name)
    mean_min, mean_max = get_mean_min_max(mparameters)
    if df_ref is None or not isinstance(df_ref, dict) or not os.path.isfile(iirname):
        return [], {}

    srate = 48000
    logger.debug("found IIR eq %s: applying to %s", iirname, speaker_name)
    iir = parse_eq_iir_rews(iirname, srate)

    df_eq = {}

    # full measurement
    if "SPL Horizontal_unmelted" in df_ref and "SPL Vertical_unmelted" in df_ref:
        h_spl = df_ref["SPL Horizontal_unmelted"]
        v_spl = df_ref["SPL Vertical_unmelted"]
        eq_h_spl = peq_apply_measurements(h_spl, iir)
        eq_v_spl = peq_apply_measurements(v_spl, iir)
        df_eq = filter_graphs(
            speaker_name,
            eq_h_spl,
            eq_v_spl,
            mean_min,
            mean_max,
            mformat,
            distance,
        )
        return iir, df_eq

    # partial_measurements
    print("DEBUG {}".format(df_ref.keys()))
    if "CEA2034" in df_ref:
        spin_eq, eir_eq, on_eq = noscore_apply_filter(df_ref, iir, False)
        if spin_eq is not None:
            df_eq["CEA2034"] = spin_eq
            df_eq["CEA2034_unmelted"] = graph_unmelt(spin_eq)

        if eir_eq is not None:
            df_eq["Estimated In-Room Response"] = eir_eq
            df_eq["Estimated In-Room Response_unmelted"] = graph_unmelt(eir_eq)

        if on_eq is not None:
            df_eq["On Axis"] = on_eq
            df_eq["On Axis_unmelted"] = graph_unmelt(on_eq)

        df_eq["eq"] = iir

    if "CEA2034 Normalized" in df_ref:
        spin_eq, eir_eq, on_eq = noscore_apply_filter(df_ref, iir, True)
        if spin_eq is not None:
            df_eq["CEA2034 Normalized"] = spin_eq
            df_eq["CEA2034 Normalized_unmelted"] = graph_unmelt(spin_eq)

        if eir_eq is not None:
            df_eq["Estimated In-Room Response Normalized"] = eir_eq
            df_eq["Estimated In-Room Response Normalized_unmelted"] = graph_unmelt(eir_eq)

        if on_eq is not None:
            df_eq["On Axis"] = on_eq
            df_eq["On Axis_unmelted"] = graph_unmelt(on_eq)

    print("DEBUG {}".format(df_eq.keys()))
    return iir, df_eq


@ray.remote(num_cpus=1)
def parse_graphs_speaker(
    speaker_path: str,
    speaker_brand: str,
    speaker_name: str,
    mformat: str,
    morigin: str,
    mversion: str,
    msymmetry: Symmetry,
    mparameters: Parameters | None,
    level: int,
    distance: float,
) -> dict:
    ray_setup_logger(level)
    df_graph = None
    measurement_path = f"{speaker_path}"
    mean_min, mean_max = get_mean_min_max(mparameters)

    status = False
    h_spl = pd.DataFrame()
    v_spl = pd.DataFrame()
    if mformat in ("klippel", "princeton", "spl_hv_txt", "gll_hv_txt"):
        if mformat == "klippel":
            status, (h_spl, v_spl) = parse_graphs_speaker_klippel(
                measurement_path, speaker_brand, speaker_name, mversion, msymmetry
            )
        elif mformat == "princeton":
            status, (h_spl, v_spl) = parse_graphs_speaker_princeton(
                measurement_path, speaker_brand, speaker_name, mversion, msymmetry
            )
        elif mformat == "spl_hv_txt":
            status, (h_spl, v_spl) = parse_graphs_speaker_spl_hv_txt(
                measurement_path, speaker_brand, speaker_name, mversion
            )
        elif mformat == "gll_hv_txt":
            status, (h_spl, v_spl) = parse_graphs_speaker_gll_hv_txt(
                measurement_path, speaker_name, mversion
            )

        if not status:
            logger.info("Load %s failed for %s %s %s", mformat, speaker_name, mversion, morigin)
            return {}

        h_spl2, v_spl2 = symmetrise_speaker_measurements(h_spl, v_spl, msymmetry)
        df_graph = filter_graphs(
            speaker_name, h_spl2, v_spl2, mean_min, mean_max, mformat, distance
        )
    elif mformat in ("webplotdigitizer", "rew_text_dump"):
        title = None
        df_uneven = None
        if mformat == "webplotdigitizer":
            status, (title, df_uneven) = parse_graphs_speaker_webplotdigitizer(
                measurement_path, speaker_brand, speaker_name, morigin, mversion
            )
            if not status:
                logger.info("Load %s failed for %s %s %s", mformat, speaker_name, mversion, morigin)
                return {}
            # necessary to do first (most digitalize graphs are uneven in frequency)
            df_uneven = graph_melt(unify_freq(df_uneven))
        elif mformat == "rew_text_dump":
            status, (title, df_uneven) = parse_graphs_speaker_rew_text_dump(
                measurement_path, speaker_brand, speaker_name, morigin, mversion
            )
            if not status:
                logger.info("Load %s failed for %s %s %s", mformat, speaker_name, mversion, morigin)
                return {}

        nan_count = check_nan({"test": df_uneven})
        if nan_count > 0:
            logger.error("df_uneven %s has %d NaNs", speaker_name, nan_count)

        logger.debug("DEBUG title: %s", title)
        logger.debug("DEBUG df_uneven keys (%s)", ", ".join(df_uneven.keys()))
        logger.debug("DEBUG df_uneven measurements (%s)", ", ".join(set(df_uneven.Measurements)))
        try:
            if title == "CEA2034":
                df_full = spin_compute_di_eir(speaker_name, title, df_uneven)
            else:
                df_full = {title: unify_freq(graph_melt(df_uneven))}
            nan_count = check_nan(df_full)
            if nan_count > 0:
                logger.error("df_full %s has %d NaNs", speaker_name, nan_count)
                for k in df_full:
                    if isinstance(df_full[k], pd.DataFrame):
                        logger.error("------------ %s -----------", k)
                        logger.error(df_full[k].head())

            # for k in df_full:
            #     logger.debug("-- DF FULL ---------- %s -----------", k)
            #     if isinstance(df_full[k], pd.DataFrame):
            #         logger.debug(df_full[k].head())

            df_graph = filter_graphs_partial(df_full, mformat, distance)
            nan_count = check_nan(df_graph)
            if nan_count > 0:
                logger.error("df_graph %s has %d NaNs", speaker_name, nan_count)
                for k in df_graph:
                    if isinstance(df_graph[k], pd.DataFrame):
                        logger.error("------------ %s -----------", k)
                        logger.error(df_graph[k].head())

            # for k in df_graph:
            #     if isinstance(df_graph[k], pd.DataFrame):
            #         logger.debug("-- DF ---------- %s -----------", k)
            #         logger.debug(df_graph[k].head())
        except ValueError as ve:
            logger.exception("ValueError for speaker %s: %s", speaker_name, ve)
            raise
    else:
        logger.fatal("Format %s is unkown", mformat)
        sys.exit(1)

    if df_graph is None:
        logger.warning("Parsing failed for %s/%s/%s", measurement_path, speaker_name, mversion)
        return {}

    return df_graph
