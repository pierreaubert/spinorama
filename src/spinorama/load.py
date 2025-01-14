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

# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import numpy as np
import pandas as pd

from spinorama import logger
from spinorama.compute_estimates import compute_sensitivity, compute_sensitivity_details
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
from spinorama.load_misc import graph_melt, graph_unmelt, sort_angles
from spinorama.compute_misc import unify_freq


def shift_spl(spl, mean):
    """Shift all measurement by means"""
    spl_copy = pd.DataFrame()
    for k in spl:
        if k == "Freq":
            spl_copy[k] = spl[k]
        else:
            spl_copy[k] = spl[k] - mean
        # too many side effects
        # if k == "180°" and "-180°" not in spl_copy.keys():
        #     spl_copy.insert(1, "-180°", spl["180°"] - mean)
    return spl_copy


def shift_spl_melted(spl, mean):
    """Shift one measurement by means"""
    df_copy = spl.copy()
    df_copy.dB -= mean
    return df_copy


def shift_spl_melted_cea2034(spl, mean):
    """Shift all measurements by means"""
    logger.debug("DEBUG shift_spl_melted_cea2034")
    # logger.debug(spl.head())
    # shift all measurement by means
    spl_copy = None
    # for the rare case we do not have ON curve
    for curve in ("On Axis", "Listening Window"):
        if curve not in set(spl.Measurements):
            continue
        spl_copy = pd.DataFrame({"Freq": spl.loc[spl.Measurements == curve].Freq}).reset_index()
    if spl_copy is None:
        logger.error("CEA2034 is empty: known columns are (%s)", ", ".join(set(spl.Measurements)))
        return spl

    for col in set(spl.Measurements):
        logger.debug("shifting col %s", col)
        logger.debug(spl.loc[spl.Measurements == col].dB.iloc[0:10])
        if "DI" in col:
            spl_copy[col] = spl.loc[spl.Measurements == col].dB.to_numpy()
        else:
            spl_copy[col] = spl.loc[spl.Measurements == col].dB.to_numpy() - mean
    logger.debug("melted_cea %f (%s)", mean, ", ".join(spl_copy.keys()))
    logger.debug(spl_copy.head())
    for k in spl_copy:
        count = spl_copy[k].isna().sum().sum()
        logger.debug("%s %d", k, count)
    logger.debug("DEBUG END shift_spl_melted_cea2034")
    return graph_melt(spl_copy)


def norm_spl(spl):
    """Normalize SPL for a set of measurements"""
    # check
    if "dB" in spl:
        raise KeyError
    # nornalize v.s. on axis
    df_normalized = pd.DataFrame({"Freq": spl.Freq})
    on = spl["On Axis"].to_numpy()
    for k in spl:
        if k != "Freq":
            df_normalized[k] = spl[k] - on
    return df_normalized


def norm_spl_unmelted(spl):
    """Normalize SPL for a set of measurements"""
    # nornalize v.s. on axis
    return graph_melt(norm_spl(graph_unmelt(spl)))


def filter_graphs(
    speaker_name: str,
    h_spl,
    v_spl,
    mean_min: float,
    mean_max: float,
    mformat: str,
    mdistance: float,
) -> dict[str, pd.DataFrame]:
    """Filter a set of graphs defined by h_spl and v_spl.

    mean_min and max_min denote the range of frequencies on which you compute the mean SPL.
    This mean SPL is then substracted from all measurements
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
        dfs["SPL Horizontal_normalized_unmelted"] = norm_spl(sh_spl)
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
        dfs["SPL Vertical_normalized_unmelted"] = norm_spl(sv_spl)
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
            elif title == "CEA2034 Normalized":
                df_funct = functor(norm_spl(sh_spl), norm_spl(sv_spl))
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

    return dfs


def filter_graphs_eq(
    speaker_name,
    h_spl,
    v_spl,
    h_eq_spl,
    v_eq_spl,
    mean_min,
    mean_max,
    mformat,
    mdistance,
) -> dict[str, pd.DataFrame]:
    """Filter a set of graphs defined by h_spl and v_spl.

    mean_min and max_min denote the range of frequencies on which you compute the mean SPL.
    This mean SPL is then substracted from all measurements
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
        mean_sensitivity, mean_sensitivity_1m = compute_sensitivity(h_eq_spl, mformat, mdistance)
        sh_spl = shift_spl(h_eq_spl, mean_min_max)
        dfs["SPL Horizontal"] = graph_melt(sh_spl)
        dfs["SPL Horizontal_unmelted"] = sh_spl
        dfs["SPL Horizontal_normalized_unmelted"] = norm_spl(sh_spl)
    else:
        logger.info("h_spl is None for speaker %s", speaker_name)

    if v_spl is not None:
        if mean_min_max is None:
            mean_min_max = np.mean(
                v_spl.loc[(v_spl.Freq > mean_min) & (v_spl.Freq < mean_max)]["On Axis"]
            )
        if mean_sensitivity is None:
            mean_sensitivity, mean_sensitivity_1m = compute_sensitivity(
                v_eq_spl, mformat, mdistance
            )

        sv_spl = shift_spl(v_eq_spl, mean_min_max)
        dfs["SPL Vertical"] = graph_melt(sv_spl)
        dfs["SPL Vertical_unmelted"] = sv_spl
        dfs["SPL Vertical_normalized_unmelted"] = norm_spl(sv_spl)
    else:
        logger.info("v_spl is None for speaker %s", speaker_name)

    # horrible hack for EQ speakers which are already normalized
    if mean_sensitivity is not None and mean_sensitivity > 20:
        dfs["sensitivity"] = mean_sensitivity
        dfs["sensitivity_distance"] = mdistance
        dfs["sensitivity_1m"] = mean_sensitivity_1m

    # add computed graphs
    table = [
        ["Early Reflections", early_reflections],
        ["Horizontal Reflections", horizontal_reflections],
        ["Vertical Reflections", vertical_reflections],
        ["Estimated In-Room Response", estimated_inroom_hv],
        ["On Axis", compute_onaxis],
        ["CEA2034", compute_cea2034],
        ["CEA2034 Normalized", compute_cea2034],
    ]

    if sh_spl is None or sv_spl is None:
        #
        df_on = compute_onaxis(sh_spl, sv_spl)
        dfs["On Axis_unmelted"] = df_on
        dfs["On Axis"] = graph_melt(df_on)
        # SPL H
        if sh_spl is not None:
            df_hr = horizontal_reflections(sh_spl)
            dfs["Horizontal Reflections_unmelted"] = df_hr
            dfs["Horizontal Reflections"] = graph_melt(df_hr)
        # SPL V
        if sv_spl is not None:
            df_vr = vertical_reflections(sv_spl)
            dfs["Vectical Reflections_unmelted"] = df_vr
            dfs["Vectical Reflections"] = graph_melt(df_vr)
        # that's all folks
        return dfs

    for title, functor in table:
        try:
            df_funct = None
            if title == "Horizontal Reflections":
                df_funct = functor(sh_spl)
            elif title == "Vertical Reflections":
                df_funct = functor(sv_spl)
            elif title == "CEA2034 Normalized":
                df_funct = functor(norm_spl(sh_spl), norm_spl(sv_spl))
            else:
                df_funct = functor(sh_spl, sv_spl)
            if df_funct is not None:
                dfs[title + "_unmelted"] = df_funct
                dfs[title] = graph_melt(df_funct)
            else:
                logger.info("%s computation is None for speaker %s", title, speaker_name)
        except KeyError as ke:
            logger.warning(
                "%s computation failed with key %s for speaker %s", title, ke, speaker_name
            )

    return dfs


def filter_graphs_partial(df, mformat, mdistance):
    dfs = {}
    # normalize first
    mean_midrange = None
    mean_sensitivity = None
    mean_sensitivity_1m = None
    on = None
    if "CEA2034" in df:
        on = df["CEA2034"]
        if "Measurements" not in on:
            on = graph_melt(on)
    if on is None and "On Axis" in df and "On Axis" in df["On Axis"]:
        on = df["On Axis"]
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

    if mean_midrange is not None:
        logger.debug("DEBUG: mean %f", mean_midrange)
        if mean_sensitivity is not None and mean_sensitivity > 20:
            dfs["sensitivity"] = mean_sensitivity
            dfs["sensitivity_distance"] = mdistance
            dfs["sensitivity_1m"] = mean_sensitivity_1m
        for k in df:
            if k == "CEA2034":
                logger.debug("DEBUG %s pre shift cols=(%s)", k, ", ".join(set(df[k].Measurements)))
                shifted_spin = shift_spl_melted_cea2034(df[k], mean_midrange)
                dfs[k] = shifted_spin
                logger.debug("DEBUG %s post shift cols=(%s)", k, ", ".join(set(df[k].Measurements)))
                dfs["CEA2034 Normalized"] = norm_spl_unmelted(shifted_spin)
            else:
                dfs[k] = shift_spl_melted(df[k], mean_midrange)
    else:
        logger.debug("DEBUG: mean is unknown")
        for k in df:
            if k == "CEA2034":
                shifted_spin = shift_spl_melted_cea2034(df[k], 0.0)
                dfs[k] = shifted_spin
                dfs["CEA2034 Normalized"] = norm_spl_unmelted(shifted_spin)
            else:
                dfs[k] = df[k]

    for k in df:
        if "unmelted" in k:
            continue
        unmelted = "{}_unmelted".format(k)
        if unmelted not in dfs and isinstance(dfs[k], pd.DataFrame):
            dfs[unmelted] = graph_unmelt(dfs[k])
    # note: not in df but could be in dfs
    if "CEA2034 Normalized" in dfs and "CEA2034 Normalized_unmelted" not in dfs:
        dfs["CEA2034 Normalized_unmelted"] = graph_unmelt(dfs["CEA2034 Normalized"])

    logger.debug("DEBUG  filter_graphs partial (%s)", ", ".join(dfs.keys()))
    for k, v in dfs.items():
        if k not in ("sensitivity", "sensitivity_1m", "sensitivity_distance"):
            logger.debug(v.head())

    logger.debug(
        "filter in: keys=(%s) out: mean=%f keys=(%s)",
        ", ".join(df.keys()),
        mean_midrange,
        ", ".join(dfs.keys()),
    )
    logger.debug("DEBUG END of filter_graphs_partial")
    return dfs


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

        # sp_di = spin.loc[spin['Measurements'] == 'Sound Power DI'].reset_index(drop=True)
        # logger.debug(
        #    "Post treatment SP DI: shape={0} min={1} max={2}",
        #    sp_di.shape,
        #    sp_di_computed.min(),
        #    sp_di_computed.max(),
        # )
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
