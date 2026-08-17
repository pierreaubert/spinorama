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

import numpy as np
import pandas as pd

from datas import Parameters

from spinorama import logger, setup_logger
from spinorama.constant_paths import MEAN_MIN, MEAN_MAX

from spinorama.filter_peq import Peq, peq_apply_measurements
from spinorama.filter_scores import noscore_apply_filter

from spinorama.compute_misc import unify_freq
from spinorama.compute_estimates import compute_sensitivity, compute_sensitivity_details

from spinorama.measurements import Measurements, Sensitivity
from spinorama.misc import (
    graph_melt,
    graph_unmelt,
    check_nan,
    sort_angles,
    measurements_complete_freq,
    measurements_complete_spl,
)
from spinorama.loaders import (
    CURVE_LOADERS,
    HV_LOADERS,
    SpeakerLoadParams,
    UnknownMeasurementFormatError,
)
from spinorama.loaders.rew_eq import parse_eq_iir_rews

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


def _normalize_spl_unmelted(spl: pd.DataFrame, on: np.ndarray) -> pd.DataFrame:
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


def normalize_spl(spl: pd.DataFrame, on: pd.DataFrame | np.ndarray | None = None) -> pd.DataFrame:
    spl_unmelted = spl
    if "Measurements" in spl:
        spl_unmelted = graph_unmelt(spl)
    if on is None:
        if "On Axis" not in spl_unmelted:
            raise KeyError
        on = spl_unmelted["On Axis"].to_numpy()
    return _normalize_spl_unmelted(spl_unmelted, on)


# Below 20 dB the SPL value is most likely already normalised (e.g. for EQ
# speakers); don't record sensitivity in that case.
_SENSITIVITY_NORMALISED_THRESHOLD = 20.0


def _mean_in_band(spl: pd.DataFrame, mean_min: float, mean_max: float) -> float:
    """Return the average on-axis SPL inside the ``[mean_min, mean_max]`` band."""
    return float(np.mean(spl.loc[(spl.Freq > mean_min) & (spl.Freq < mean_max)]["On Axis"]))


def _sensitivity_if_meaningful(
    spl: pd.DataFrame, mformat: str, mdistance: float
) -> Sensitivity | None:
    spl_at_distance, spl_at_1m = compute_sensitivity(spl, mformat, mdistance)
    if spl_at_distance is None or spl_at_distance <= _SENSITIVITY_NORMALISED_THRESHOLD:
        return None
    return Sensitivity(spl=spl_at_distance, distance=mdistance, spl_at_1m=spl_at_1m)


def _try_compute(name: str, speaker_name: str, fn, *args) -> pd.DataFrame | None:
    """Run a compute step, returning ``None`` (with a log line) on ``KeyError``."""
    try:
        result = fn(*args)
    except KeyError as key_error:
        logger.warning(
            "%s computation failed with key:%s for speaker %s", name, key_error, speaker_name
        )
        return None
    if result is None:
        logger.info("%s computation is None for speaker %s", name, speaker_name)
    return result


def filter_graphs(
    speaker_name: str,
    h_spl: None | pd.DataFrame,
    v_spl: None | pd.DataFrame,
    mean_min: float,
    mean_max: float,
    mformat: str,
    mdistance: float,
) -> Measurements:
    """Build the per-axis :class:`Measurements` from raw H/V SPL sweeps.

    Every derived curve is computed once in wide form and stored on the
    returned :class:`Measurements`; downstream code accesses fields directly.
    """
    m = Measurements()

    sh_spl: pd.DataFrame | None = None
    sv_spl: pd.DataFrame | None = None
    mean_in_band: float | None = None
    sensitivity: Sensitivity | None = None

    if h_spl is not None:
        mean_in_band = _mean_in_band(h_spl, mean_min, mean_max)
        sensitivity = _sensitivity_if_meaningful(h_spl, mformat, mdistance)
        sh_spl = shift_spl(h_spl, mean_in_band)
        m.h_spl = sh_spl
        m.h_spl_normalized = normalize_spl(sh_spl)
    else:
        logger.info("h_spl is None for speaker %s", speaker_name)

    if v_spl is not None:
        if mean_in_band is None:
            mean_in_band = _mean_in_band(v_spl, mean_min, mean_max)
        if sensitivity is None:
            sensitivity = _sensitivity_if_meaningful(v_spl, mformat, mdistance)
        sv_spl = shift_spl(v_spl, mean_in_band)
        m.v_spl = sv_spl
        m.v_spl_normalized = normalize_spl(sv_spl)
    else:
        logger.info("v_spl is None for speaker %s", speaker_name)

    m.sensitivity = sensitivity
    if sensitivity is not None:
        logger.debug(
            "%s sensitivity: %f and sensitivity 1m: %f",
            speaker_name,
            sensitivity.spl,
            sensitivity.spl_at_1m,
        )

    complete_spl = measurements_complete_spl(h_spl, v_spl)
    complete = complete_spl and measurements_complete_freq(h_spl, v_spl)
    logger.info(
        "%s completeness %s SPL %s",
        speaker_name,
        str(complete),
        str(complete_spl),
    )

    # Partial path: at least one axis is missing — compute the minimum.
    if sh_spl is None or sv_spl is None:
        m.on_axis = compute_onaxis(sh_spl, sv_spl)
        if sh_spl is not None and complete_spl:
            m.horizontal_reflections = horizontal_reflections(sh_spl)
        if sv_spl is not None and complete_spl:
            m.vertical_reflections = vertical_reflections(sv_spl)
        return m

    # Full path: both axes present. On-axis is always computed.
    m.on_axis = _try_compute("On Axis", speaker_name, compute_onaxis, sh_spl, sv_spl)
    if not complete:
        return m

    m.early_reflections = _try_compute(
        "Early Reflections", speaker_name, early_reflections, sh_spl, sv_spl
    )
    m.horizontal_reflections = _try_compute(
        "Horizontal Reflections", speaker_name, horizontal_reflections, sh_spl
    )
    m.vertical_reflections = _try_compute(
        "Vertical Reflections", speaker_name, vertical_reflections, sv_spl
    )
    m.eir = _try_compute(
        "Estimated In-Room Response", speaker_name, estimated_inroom_hv, sh_spl, sv_spl
    )
    m.eir_normalized = _try_compute(
        "Estimated In-Room Response Normalized",
        speaker_name,
        estimated_inroom_hv,
        normalize_spl(sh_spl),
        normalize_spl(sv_spl),
    )
    m.cea2034 = _try_compute("CEA2034", speaker_name, compute_cea2034, sh_spl, sv_spl)
    m.cea2034_normalized = _try_compute(
        "CEA2034 Normalized",
        speaker_name,
        compute_cea2034,
        normalize_spl(sh_spl),
        normalize_spl(sv_spl),
    )

    return m


def filter_graphs_partial(df_in, mformat, mdistance):
    df_out = {}
    # normalize first
    mean_midrange = None
    sensitivity: Sensitivity | None = None
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
            spl_at_distance, spl_at_1m = compute_sensitivity_details(on, curve, mformat, mdistance)
            if spl_at_distance > _SENSITIVITY_NORMALISED_THRESHOLD:
                sensitivity = Sensitivity(
                    spl=spl_at_distance, distance=mdistance, spl_at_1m=spl_at_1m
                )

    if mean_midrange is None:
        mean_midrange = 0.0
    logger.debug("DEBUG: mean %f", mean_midrange)

    # add On Axis if missing
    if "On Axis" not in df_in and "CEA2034" in df_in:
        spin = df_in["CEA2034"]
        on = spin.loc[spin.Measurements == "On Axis"]
        if on.shape[0] > 10:
            df_in["On Axis"] = pd.DataFrame(
                {"Freq": on.Freq, "Measurements": ["On Axis"] * len(on.Freq), "dB": on.dB}
            )

    # add PIR if missing
    if "Estimated In-Room Response" not in df_in and "CEA2034" in df_in:
        spin = df_in["CEA2034"]
        lw = spin.loc[spin.Measurements == "Listening Window"]
        er = spin.loc[spin.Measurements == "Early Reflections"]
        sp = spin.loc[spin.Measurements == "Sound Power"]
        pir = estimated_inroom(lw, er, sp)
        if "Estimated In-Room Response" in pir:
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
    if "CEA2034" in df_in and "On Axis" in df_in:
        spin = df_in["CEA2034"]
        on = df_in["On Axis"].dB.to_numpy()
        normalized_spin = normalize_spl(spin, on)
        df_out["CEA2034 Normalized"] = graph_melt(normalized_spin)

    if "Estimated In-Room Response" in df_in and "On Axis" in df_in:
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
    if sensitivity is not None:
        df_out["sensitivity"] = sensitivity.spl
        df_out["sensitivity_distance"] = sensitivity.distance
        df_out["sensitivity_1m"] = sensitivity.spl_at_1m

    logger.debug("DEBUG filter_graphs_partial  IN (%s)", ", ".join(df_in.keys()))
    logger.debug("DEBUG filter_graphs_partial partial OUT (%s)", ", ".join(df_out.keys()))
    return Measurements.from_legacy_dict(df_out)


def parse_graph_freq_check(speaker_name: str, df_spin: pd.DataFrame) -> bool:
    status = True
    spin_cols = set(df_spin.Measurements.to_numpy())
    mandatory_cols = ("Listening Window", "On Axis", "Early Reflections", "Sound Power")
    other_cols = ("Early Reflections DI", "Sound Power DI", "DI Offset")
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
        logger.debug("parse graph failed for %s", speaker_name)
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


def _mirror_angle(col: str) -> str:
    """Return the opposite-sign angle column name (``"30°" → "-30°"``, ``"-40°" → "40°"``)."""
    return col[1:] if col[0] == "-" else "-{}".format(col)


def symmetrise_speaker_measurements(
    h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None, symmetry: str | None
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
            if col == "Freq" or col[0:5] == "Phase":
                continue
            angle = 0 if col == "On Axis" else int(col[:-1])
            min_angle = min(min_angle, angle)
            max_angle = max(max_angle, angle)

        # extend 0-180 to -170 0 180
        # extend 0-90  to -90 to 90
        new_spl = spl.copy()
        for col in cols:
            if col not in ("Freq", "On Axis", "180°") and "Phase" not in col:
                m_angle = _mirror_angle(col)
                if m_angle not in spl.columns:
                    new_spl[m_angle] = spl[col]
        return sort_angles(new_spl)

    if h_spl is None and v_spl is None:
        logger.error("Symmetrisation cannot work with no measurement")
        return (None, None)

    if symmetry is not None and symmetry.lower() not in (
        "coaxial",
        "vertical",
        "horizontal",
        "none",
    ):
        logger.error("symmetry %s is unknown", symmetry)
        return (None, None)

    if symmetry is None or symmetry.lower() == "none":
        return (
            h_spl.copy() if h_spl is not None else None,
            v_spl.copy() if v_spl is not None else None,
        )

    if symmetry == "coaxial":
        if h_spl is not None:
            h_spl2 = symmetrise_measurement(h_spl)
            v_spl2 = h_spl2.copy() if v_spl is None else symmetrise_measurement(v_spl)
        elif v_spl is not None:
            v_spl2 = symmetrise_measurement(v_spl)
            h_spl2 = v_spl2.copy()
        return (h_spl2, v_spl2)
    elif h_spl is not None and symmetry == "horizontal":
        h_spl2 = symmetrise_measurement(h_spl)
        return (h_spl2, v_spl.copy() if v_spl is not None else None)
    elif v_spl is not None and symmetry == "vertical":
        v_spl2 = symmetrise_measurement(v_spl)
        return (h_spl.copy() if h_spl is not None else None, v_spl2)


def get_mean_min_max(mparameters: Parameters | None) -> tuple[int, int]:
    # default works well for flatish speakers but not at all for line arrays for ex
    # where the mean is flat but usually high bass and low high
    mean_min = MEAN_MIN
    mean_max = MEAN_MAX
    if mparameters is not None:
        mean_min = mparameters.get("mean_min", mean_min)
        mean_max = mparameters.get("mean_max", mean_max)
    return mean_min, mean_max


def _parse_hv_speaker(
    params: SpeakerLoadParams,
    mean_min: float,
    mean_max: float,
) -> Measurements | None:
    """Run an HV loader, symmetrise, and assemble the per-axis :class:`Measurements`."""
    status, (h_spl, v_spl) = HV_LOADERS[params.mformat](params)

    if not status:
        logger.debug("Failed to load %s from measurement %s", params.speaker_name, params.mversion)
        if h_spl is not None and "Freq" not in h_spl:
            h_spl = None
        if v_spl is not None and "Freq" not in v_spl:
            v_spl = None
        if h_spl is None and v_spl is None:
            logger.error(
                "Failed to load %s from measurement %s", params.speaker_name, params.mversion
            )
            return None

    h_spl2, v_spl2 = symmetrise_speaker_measurements(h_spl, v_spl, params.msymmetry)
    if h_spl2 is None or v_spl2 is None:
        logger.error(
            "Failed to symmetrise %s from measurement %s",
            params.speaker_name,
            params.mversion,
        )
        return None

    return filter_graphs(
        params.speaker_name,
        h_spl2,
        v_spl2,
        mean_min,
        mean_max,
        params.mformat,
        params.distance,
    )


def _parse_curve_speaker(params: SpeakerLoadParams) -> Measurements | None:
    """Run a single-curve loader and pipe through the partial-graph pipeline."""
    status, (title, df_uneven) = CURVE_LOADERS[params.mformat](params)
    if not status:
        logger.info(
            "Load %s failed for %s %s %s",
            params.mformat,
            params.speaker_name,
            params.mversion,
            params.morigin,
        )
        return None

    df_even = graph_melt(unify_freq(df_uneven))
    nan_count = check_nan({"test": df_even})
    if nan_count > 0:
        logger.error("df_uneven %s has %d NaNs", params.speaker_name, nan_count)

    logger.debug("DEBUG title: %s", title)
    if df_even is None:
        logger.info("INFO df_even is None")
        return None
    logger.debug("DEBUG df_even keys (%s)", ", ".join(df_even.keys()))
    logger.debug("DEBUG df_even measurements (%s)", ", ".join(set(df_even.Measurements)))

    try:
        if title == "CEA2034":
            df_full = spin_compute_di_eir(params.speaker_name, title, df_even)
        else:
            df_full = {title: unify_freq(graph_melt(df_even))}
        nan_count = check_nan(df_full)
        if nan_count > 0:
            logger.error("df_full %s has %d NaNs", params.speaker_name, nan_count)
            for k in df_full:
                if isinstance(df_full[k], pd.DataFrame):
                    logger.error("------------ %s -----------", k)
                    logger.error(df_full[k].head())

        m_graph = filter_graphs_partial(df_full, params.mformat, params.distance)
        legacy_view = m_graph.to_legacy_dict()
        nan_count = check_nan(legacy_view)
        if nan_count > 0:
            logger.error("df_graph %s has %d NaNs", params.speaker_name, nan_count)
            for k, v in legacy_view.items():
                if isinstance(v, pd.DataFrame):
                    logger.error("------------ %s -----------", k)
                    logger.error(v.head())
        return m_graph
    except ValueError as ve:
        logger.exception("ValueError for speaker %s: %s", params.speaker_name, ve)
        return None
    except KeyError as ke:
        logger.exception("KeyError for speaker %s: %s", params.speaker_name, ke)
        return None


def parse_graphs_speaker(
    speaker_path: str,
    speaker_brand: str,
    speaker_name: str,
    speaker_parameters: dict,
    log_level: int,
) -> Measurements:
    setup_logger(level=log_level)

    params = SpeakerLoadParams.from_legacy(
        speaker_path, speaker_brand, speaker_name, speaker_parameters
    )
    mean_min, mean_max = get_mean_min_max(params.mparameters)

    if params.mformat in HV_LOADERS:
        m_graph = _parse_hv_speaker(params, mean_min, mean_max)
    elif params.mformat in CURVE_LOADERS:
        m_graph = _parse_curve_speaker(params)
    else:
        logger.fatal("Format %s is unkown", params.mformat)
        raise UnknownMeasurementFormatError(params.mformat)

    if m_graph is None or m_graph.is_empty():
        logger.warning(
            "Parsing failed for %s/%s/%s",
            params.measurement_path,
            params.speaker_name,
            params.mversion,
        )
        return Measurements()

    return m_graph


def parse_eq_speaker(
    speaker_path: str,
    speaker_name: str,
    ref: Measurements,
    speaker_parameters: dict,
    log_level: int,
) -> tuple[Peq, Measurements]:
    """Apply an on-disk PEQ to ``ref`` and return ``(peq, equalised_measurements)``."""
    setup_logger(level=log_level)
    mformat = speaker_parameters["mformat"]
    mparameters = speaker_parameters["mparameters"]
    distance = speaker_parameters["distance"]

    iirname = "{0}/eq/{1}/iir.txt".format(speaker_path, speaker_name)
    mean_min, mean_max = get_mean_min_max(mparameters)
    if ref is None or ref.is_empty() or not os.path.isfile(iirname):
        return [], Measurements()

    srate = 48000
    logger.debug("found IIR eq %s: applying to %s", iirname, speaker_name)
    iir = parse_eq_iir_rews(iirname, srate)

    # full measurement
    if ref.h_spl is not None and ref.v_spl is not None:
        eq_h_spl = peq_apply_measurements(ref.h_spl, iir)
        eq_v_spl = peq_apply_measurements(ref.v_spl, iir)
        return iir, filter_graphs(
            speaker_name,
            eq_h_spl,
            eq_v_spl,
            mean_min,
            mean_max,
            mformat,
            distance,
        )

    # partial_measurements: apply EQ to the pre-computed curves.
    m = Measurements(eq=iir)

    if ref.cea2034 is not None:
        spin_eq, eir_eq, on_eq = noscore_apply_filter(ref, iir, False)
        if spin_eq is not None:
            m.cea2034 = graph_unmelt(spin_eq)
        if eir_eq is not None:
            m.eir = graph_unmelt(eir_eq)
        if on_eq is not None:
            m.on_axis = graph_unmelt(on_eq)

    if ref.cea2034_normalized is not None:
        spin_eq, eir_eq, on_eq = noscore_apply_filter(ref, iir, True)
        if spin_eq is not None:
            m.cea2034_normalized = graph_unmelt(spin_eq)
        if eir_eq is not None:
            m.eir_normalized = graph_unmelt(eir_eq)
        if on_eq is not None:
            m.on_axis = graph_unmelt(on_eq)

    # An EQ with no curves to attach to is useless to the caller.
    if m.cea2034 is None and m.cea2034_normalized is None:
        return iir, Measurements()

    return iir, m
