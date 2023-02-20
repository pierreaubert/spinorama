# -*- coding: utf-8 -*-
import logging
import numpy as np
import pandas as pd

from .constant_paths import (
    MIDRANGE_MIN_FREQ,
    MIDRANGE_MAX_FREQ,
    SENSITIVITY_MIN_FREQ,
    SENSITIVITY_MAX_FREQ,
)
from .compute_cea2034 import (
    early_reflections,
    vertical_reflections,
    horizontal_reflections,
    compute_cea2034,
    compute_onaxis,
    estimated_inroom,
    estimated_inroom_hv,
)

from .load_misc import graph_melt, sort_angles
from .compute_misc import unify_freq

logger = logging.getLogger("spinorama")


def shift_spl(spl, mean):
    # shift all measurement by means
    df = pd.DataFrame()
    for k in spl.keys():
        if k == "Freq":
            df[k] = spl[k]
        else:
            df[k] = spl[k] - mean
        # too many side effects
        # if k == "180°" and "-180°" not in df.keys():
        #     df.insert(1, "-180°", spl["180°"] - mean)
    return df


def shift_spl_melted(spl, mean):
    # shift all measurement by means
    df = spl.copy()
    df.dB -= mean
    return df


def shift_spl_melted_cea2034(spl, mean):
    # spl
    logger.debug("DEBUG shift_spl_melted_cea2034")
    # logger.debug(spl.head())
    # shift all measurement by means
    df = None
    # for the rare case we do not have ON curve
    for curve in ("On Axis", "Listening Window"):
        if curve not in set(spl.Measurements):
            continue
        df = pd.DataFrame({"Freq": spl.loc[spl.Measurements == curve].Freq}).reset_index()
    if df is None:
        logger.error("CEA2034 is empty: known columns are (%s)", ", ".join(set(spl.Measurements)))
        return spl

    for col in set(spl.Measurements):
        logger.debug("shifting col %s", col)
        logger.debug(spl.loc[spl.Measurements == col].dB.iloc[0:10])
        if "DI" in col:
            df[col] = spl.loc[spl.Measurements == col].dB.values
        else:
            df[col] = spl.loc[spl.Measurements == col].dB.values - mean
    logger.debug("melted_cea %f (%s)", mean, ", ".join(df.keys()))
    logger.debug(df.head())
    for k in df.keys():
        count = df[k].isna().sum().sum()
        logger.debug("%s %d", k, count)
    logger.debug("DEBUG END shift_spl_melted_cea2034")
    return graph_melt(df)


def norm_spl(spl):
    # check
    if "dB" in spl.keys():
        raise KeyError
    # nornalize v.s. on axis
    df = pd.DataFrame({"Freq": spl.Freq})
    on = spl["On Axis"].values
    for k in spl.keys():
        if k != "Freq":
            df[k] = spl[k] - on
    return df


def filter_graphs(
    speaker_name, h_spl, v_spl, mean_min=MIDRANGE_MIN_FREQ, mean_max=MIDRANGE_MAX_FREQ
):
    dfs = {}
    # add H and V SPL graphs
    mean_min_max = None
    mean_sensitivity = None
    sv_spl = None
    sh_spl = None

    if h_spl is not None:
        mean_min_max = np.mean(
            h_spl.loc[(h_spl.Freq > mean_min) & (h_spl.Freq < mean_max)]["On Axis"]
        )
        mean_sensitivity = np.mean(
            h_spl.loc[(h_spl.Freq > SENSITIVITY_MIN_FREQ) & (h_spl.Freq < SENSITIVITY_MAX_FREQ)][
                "On Axis"
            ]
        )
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
            mean_sensitivity = np.mean(
                v_spl.loc[
                    (v_spl.Freq > SENSITIVITY_MIN_FREQ) & (v_spl.Freq < SENSITIVITY_MAX_FREQ)
                ]["On Axis"]
            )
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

    # add computed graphs
    table = [
        ["Early Reflections", early_reflections],
        ["Horizontal Reflections", horizontal_reflections],
        ["Vertical Reflections", vertical_reflections],
        ["Estimated In-Room Response", estimated_inroom_hv],
        ["On Axis", compute_onaxis],
        ["CEA2034", compute_cea2034],
    ]

    if sh_spl is None or sv_spl is None:
        #
        df = compute_onaxis(sh_spl, sv_spl)
        dfs["On Axis_unmelted"] = df
        dfs["On Axis"] = graph_melt(df)
        # SPL H
        if sh_spl is not None:
            df = horizontal_reflections(sh_spl, sv_spl)
            dfs["Horizontal Reflections_unmelted"] = df
            dfs["Horizontal Reflections"] = graph_melt(df)
        # SPL V
        if sv_spl is not None:
            df = vertical_reflections(sh_spl, sv_spl)
            dfs["Vectical Reflections_unmelted"] = df
            dfs["Vectical Reflections"] = graph_melt(df)
        # that's all folks
        return dfs

    for title, functor in table:
        try:
            df = functor(sh_spl, sv_spl)
            if df is not None:
                dfs[title + "_unmelted"] = df
                dfs[title] = graph_melt(df)
            else:
                logger.info("%s computation is None for speaker %s", title, speaker_name)
        except KeyError as ke:
            logger.warning(
                "%s computation failed with key:%s for speaker %s", title, ke, speaker_name
            )

    return dfs


def filter_graphs_eq(
    speaker_name,
    h_spl,
    v_spl,
    h_eq_spl,
    v_eq_spl,
    mean_min=MIDRANGE_MIN_FREQ,
    mean_max=MIDRANGE_MAX_FREQ,
):
    dfs = {}
    # add H and V SPL graphs
    mean_min_max = None
    mean_sensitivity = None
    sv_spl = None
    sh_spl = None

    if h_spl is not None:
        mean_min_max = np.mean(
            h_spl.loc[(h_spl.Freq > mean_min) & (h_spl.Freq < mean_max)]["On Axis"]
        )
        mean_sensitivity = np.mean(
            h_spl.loc[(h_spl.Freq > SENSITIVITY_MIN_FREQ) & (h_spl.Freq < SENSITIVITY_MAX_FREQ)][
                "On Axis"
            ]
        )
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
            mean_sensitivity = np.mean(
                v_spl.loc[
                    (v_spl.Freq > SENSITIVITY_MIN_FREQ) & (v_spl.Freq < SENSITIVITY_MAX_FREQ)
                ]["On Axis"]
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

    # add computed graphs
    table = [
        ["Early Reflections", early_reflections],
        ["Horizontal Reflections", horizontal_reflections],
        ["Vertical Reflections", vertical_reflections],
        ["Estimated In-Room Response", estimated_inroom_hv],
        ["On Axis", compute_onaxis],
        ["CEA2034", compute_cea2034],
    ]

    if sh_spl is None or sv_spl is None:
        #
        df = compute_onaxis(sh_spl, sv_spl)
        dfs["On Axis_unmelted"] = df
        dfs["On Axis"] = graph_melt(df)
        # SPL H
        if sh_spl is not None:
            df = horizontal_reflections(sh_spl, sv_spl)
            dfs["Horizontal Reflections_unmelted"] = df
            dfs["Horizontal Reflections"] = graph_melt(df)
        # SPL V
        if sv_spl is not None:
            df = vertical_reflections(sh_spl, sv_spl)
            dfs["Vectical Reflections_unmelted"] = df
            dfs["Vectical Reflections"] = graph_melt(df)
        # that's all folks
        return dfs

    for title, functor in table:
        try:
            df = functor(sh_spl, sv_spl)
            if df is not None:
                dfs[title + "_unmelted"] = df
                dfs[title] = graph_melt(df)
            else:
                logger.info("%s computation is None for speaker %s", title, speaker_name)
        except KeyError as ke:
            logger.warning(
                "%s computation failed with key %s for speaker %s", title, ke, speaker_name
            )

    return dfs


def filter_graphs_partial(df):
    dfs = {}
    # normalize first
    mean_midrange = None
    mean_sensitivity = None
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
            mean_sensitivity = np.mean(
                on.loc[
                    (on.Freq > SENSITIVITY_MIN_FREQ)
                    & (on.Freq < SENSITIVITY_MAX_FREQ)
                    & (on.Measurements == curve)
                ].dB
            )
    if mean_midrange is not None:
        logger.debug("DEBUG: mean %f", mean_midrange)
        if mean_sensitivity > 20:
            dfs["sensitivity"] = mean_sensitivity
        for k in df.keys():
            if k == "CEA2034":
                logger.debug("DEBUG %s pre shift cols=(%s)", k, ", ".join(set(df[k].Measurements)))
                dfs[k] = shift_spl_melted_cea2034(df[k], mean_midrange)
                logger.debug("DEBUG %s post shift cols=(%s)", k, ", ".join(set(df[k].Measurements)))
            else:
                dfs[k] = shift_spl_melted(df[k], mean_midrange)
    else:
        for k in df.keys():
            dfs[k] = df[k]

    for k in df.keys():
        dfs["{}_unmelted".format(k)] = (
            dfs[k]
            .pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc=max)
            .reset_index()
        )

    logger.debug("DEBUG  filter_graphs partial (%s)", ", ".join(dfs.keys()))
    for k in dfs.keys():
        if k != "sensitivity":
            logger.debug(dfs[k].head())

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
    spin_cols = set(df_spin.Measurements.values)
    mandatory_cols = ("Listening Window", "On Axis", "Early Reflections", "Sound Power")
    other_cols = ("Early Reflections DI", "Sound Power DI")
    for col in mandatory_cols:
        if col not in spin_cols:
            logger.info("%s measurement doesn't have a %s column", speaker_name, col)
            status = False
        else:
            logging.debug(
                "Loading %s $s %.1f--%.1fHz %1f--%.1fdB",
                speaker_name,
                col,
                df_spin.loc[df_spin.Measurements == col].Freq.min(),
                df_spin.loc[df_spin.Measurements == col].Freq.max(),
                df_spin.loc[df_spin.Measurements == col].dB.min(),
                df_spin.loc[df_spin.Measurements == col].dB.max(),
            )
    for col in spin_cols:
        if col not in mandatory_cols and col not in other_cols:
            logger.warning("%s measurement have extra column %s", speaker_name, col)
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
    if "Measurements" not in spin_uneven.keys():
        spin_melted = graph_melt(spin_uneven)

    if not parse_graph_freq_check(speaker_name, spin_melted):
        dfs[title] = spin_melted
        return dfs

    # logger.debug("DEBUG before unify: spin_melted {}", spin_melted.keys())
    spin_even = unify_freq(spin_melted)
    # logger.debug("DEBUG before melt: spin_even {}", spin_even.keys())
    spin = graph_melt(spin_even)
    logger.debug("DEBUG after melt: spin {}", spin.keys())

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
    # else:
    #    logger.debug("Shape LW={0} SP={1}", lw.shape, sp.shape)

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

        # er_di = spin.loc[spin['Measurements'] == 'Early Reflections DI'].reset_index(drop=True)
        # logger.debug(
        #    "Post treatment ER DI: shape={0} min={1} max={2}",
        #    er_di.shape,
        #    er_di_computed.min(),
        #    er_di_computed.max(),
        # )
    # else:
    #    logger.debug("Shape LW={0} ER={1}", lw.shape, er.shape)

    di_offset = spin.loc[spin["Measurements"] == "DI offset"].reset_index(drop=True)
    if di_offset.shape[0] == 0:
        logger.debug("No DI offset curve!")
        df2 = pd.DataFrame({"Freq": on.Freq, "dB": 0, "Measurements": "DI offset"})
        spin = pd.concat([spin, df2]).reset_index(drop=True)

    # logger.debug("Shape ON {0} LW {1} ER {2} SP {3}", on.shape, lw.shape, er.shape, sp.shape)
    if 0 not in (lw.shape[0], er.shape[0], sp.shape[0]):
        eir = estimated_inroom(lw, er, sp)
        logger.debug("eir {0}", eir.shape)
        # logger.debug(eir)
        dfs["Estimated In-Room Response"] = graph_melt(eir)
    # else:
    #    logger.debug("Shape LW={0} ER={1} SP={2}", lw.shape, er.shape, sp.shape)

    # add spin (at the end because we could have modified DI curves
    dfs[title] = spin

    if on.isna().values.any():
        logger.error("On Axis has NaN values")

    return dfs


def symmetrise_measurement(spl: pd.DataFrame) -> pd.DataFrame:
    if spl.empty:
        return pd.DataFrame()

    # look for min and max
    cols = spl.columns
    min_angle = 180
    max_angle = -180
    for col in cols:
        if col != "Freq":
            angle = None
            if col == "On Axis":
                angle = 0
            else:
                angle = int(col[:-1])
            min_angle = min(min_angle, angle)
            max_angle = max(max_angle, angle)
    # logger.debug("min {} max {}", min_angle, max_angle)

    # extend 0-180 to -170 0 180
    # extend 0-90  to -90 to 90
    new_spl = spl.copy()
    for col in cols:
        if col not in ("Freq", "On Axis", "180°") and col[0] != "-":
            mangle = "-{}".format(col)
            if mangle not in spl.columns:
                new_spl[mangle] = spl[col]
    return sort_angles(new_spl)
