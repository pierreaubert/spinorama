# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

import pandas as pd

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray

from datas import Symmetry, Parameters

from spinorama import logger, ray_setup_logger
from spinorama.ltype import DataSpeaker
from spinorama.constant_paths import MEAN_MIN, MEAN_MAX

from spinorama.compute_misc import unify_freq

from spinorama.filter_peq import Peq, peq_apply_measurements
from spinorama.filter_scores import noscore_apply_filter

from spinorama.load_misc import graph_melt, graph_unmelt, check_nan
from spinorama.load_klippel import parse_graphs_speaker_klippel
from spinorama.load_princeton import parse_graphs_speaker_princeton
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load_rew_eq import parse_eq_iir_rews
from spinorama.load_spl_hv_txt import parse_graphs_speaker_spl_hv_txt
from spinorama.load_gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer

from spinorama.load import (
    filter_graphs,
    filter_graphs_eq,
    filter_graphs_partial,
    symmetrise_measurement,
    spin_compute_di_eir,
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
    logger.debug("Level of debug is %d", level)
    iirname = "{0}/eq/{1}/iir.txt".format(speaker_path, speaker_name)
    mean_min, mean_max = get_mean_min_max(mparameters)
    if df_ref is not None and isinstance(df_ref, dict) and os.path.isfile(iirname):
        srate = 48000
        logger.debug("found IIR eq %s: applying to %s", iirname, speaker_name)
        iir = parse_eq_iir_rews(iirname, srate)
        if "SPL Horizontal_unmelted" in df_ref and "SPL Vertical_unmelted" in df_ref:
            h_spl = df_ref["SPL Horizontal_unmelted"]
            v_spl = df_ref["SPL Vertical_unmelted"]
            eq_h_spl = peq_apply_measurements(h_spl, iir)
            eq_v_spl = peq_apply_measurements(v_spl, iir)
            df_eq = filter_graphs_eq(
                speaker_name,
                h_spl,
                v_spl,
                eq_h_spl,
                eq_v_spl,
                mean_min,
                mean_max,
                mformat,
                distance,
            )
            return iir, df_eq
        elif "CEA2034" in df_ref:
            spin_eq, eir_eq, on_eq = noscore_apply_filter(df_ref, iir)
            df_eq = {}
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
            return iir, df_eq
        elif "CEA2034 Normalized" in df_ref:
            spin_eq, eir_eq, on_eq = noscore_apply_filter(df_ref, iir)
            df_eq = {}
            if spin_eq is not None:
                df_eq["CEA2034 Normalized"] = spin_eq
                df_eq["CEA2034 Normalized_unmelted"] = graph_unmelt(spin_eq)
            df_eq["eq"] = iir
            return iir, df_eq

    logger.debug("no EQ for %s/eq/%s", speaker_path, speaker_name)
    return [], {}


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

        if h_spl is not None and msymmetry == "coaxial":
            h_spl2 = symmetrise_measurement(h_spl)
            v_spl2 = h_spl2.copy() if v_spl is None else symmetrise_measurement(v_spl)
            df_graph = filter_graphs(
                speaker_name, h_spl2, v_spl2, mean_min, mean_max, mformat, distance
            )
        elif h_spl is not None and msymmetry == "horizontal":
            h_spl2 = symmetrise_measurement(h_spl)
            df_graph = filter_graphs(
                speaker_name, h_spl2, v_spl, mean_min, mean_max, mformat, distance
            )
        else:
            df_graph = filter_graphs(
                speaker_name, h_spl, v_spl, mean_min, mean_max, mformat, distance
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

            for k in df_full:
                logger.debug("-- DF FULL ---------- %s -----------", k)
                if isinstance(df_full[k], pd.DataFrame):
                    logger.debug(df_full[k].head())

            df_graph = filter_graphs_partial(df_full, mformat, distance)
            nan_count = check_nan(df_graph)
            if nan_count > 0:
                logger.error("df_graph %s has %d NaNs", speaker_name, nan_count)
                for k in df_graph:
                    if isinstance(df_graph[k], pd.DataFrame):
                        logger.error("------------ %s -----------", k)
                        logger.error(df_graph[k].head())

            for k in df_graph:
                if isinstance(df_graph[k], pd.DataFrame):
                    logger.debug("-- DF ---------- %s -----------", k)
                    logger.debug(df_graph[k].head())
        except ValueError as ve:
            logger.exception("ValueError for speaker %s: %s", speaker_name, ve)
            raise
    else:
        logger.fatal("Format %s is unkown", mformat)
        sys.exit(1)

    if df_graph is None:
        logger.warning("Parsing failed for %s/%s/%s", measurement_path, speaker_name, mversion)
        return {}

    if "CEA2034" not in df_graph:
        logger.info("CEA2034 not in graph after parsing for %s, %s", speaker_name, mversion)

    # print("DEBUG {} {} : {}".format(speaker_name, mversion, df_graph.keys()))

    return df_graph
