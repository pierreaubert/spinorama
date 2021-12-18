# -*- coding: utf-8 -*-
import os
import logging
import sys

import numpy as np
import pandas as pd

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray


from .load_klippel import parse_graphs_speaker_klippel
from .load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from .load_princeton import parse_graphs_speaker_princeton
from .load_rewstextdump import parse_graphs_speaker_rewstextdump
from .load_rewseq import parse_eq_iir_rews
from .load_splHVtxt import parse_graphs_speaker_splHVtxt
from .load import (
    filter_graphs,
    filter_graphs_partial,
    symmetrise_measurement,
    spin_compute_di_eir,
)
from .filter_peq import peq_apply_measurements
from .filter_scores import noscore_apply_filter


logger = logging.getLogger("spinorama")


def checkNaN(df):
    for k in df.keys():
        for j in df[k].keys():
            if isinstance(df[k], pd.DataFrame):
                count = df[k][j].isna().sum()
                if count > 0:
                    logger.error("{} {} {}".format(k, j, count))
    return np.sum(
        [
            df[frame].isna().sum().sum()
            for frame in df.keys()
            if isinstance(df[frame], pd.DataFrame)
        ]
    )


@ray.remote(num_cpus=1)
def parse_eq_speaker(speaker_path: str, speaker_name: str, df_ref: dict) -> dict:
    iirname = "{0}/eq/{1}/iir.txt".format(speaker_path, speaker_name)
    if df_ref is not None and isinstance(df_ref, dict) and os.path.isfile(iirname):
        srate = 48000
        logger.debug("found IIR eq {0}: applying to {1}".format(iirname, speaker_name))
        iir = parse_eq_iir_rews(iirname, srate)
        if (
            "SPL Horizontal_unmelted" in df_ref.keys()
            and "SPL Vertical_unmelted" in df_ref.keys()
        ):
            h_spl = df_ref["SPL Horizontal_unmelted"]
            v_spl = df_ref["SPL Vertical_unmelted"]
            eq_h_spl = peq_apply_measurements(h_spl, iir)
            eq_v_spl = peq_apply_measurements(v_spl, iir)
            df_eq = filter_graphs(speaker_name, eq_h_spl, eq_v_spl)
            # normalize wrt to original measurement to make comparison easier
            # original_mean = df_ref.get('CEA2034_original_mean', None)
            # return load_normalize(df_eq, original_mean)
            return df_eq
        elif "CEA2034" in df_ref.keys():
            spin_eq, eir_eq = noscore_apply_filter(df_ref, iir)
            if spin_eq is None or eir_eq is None:
                logger.debug(
                    "Computation of spin and eir with EQ failed for {} {}".format(
                        speaker_path, speaker_name
                    )
                )
                return None

            df_eq = {
                "CEA2034": spin_eq,
                "Estimated In-Room Response": eir_eq,
            }
            return df_eq

    logger.debug("no EQ for {}/eq/{}".format(speaker_path, speaker_name))
    return None


@ray.remote(num_cpus=1)
def parse_graphs_speaker(
    speaker_path: str,
    speaker_brand: str,
    speaker_name: str,
    mformat="klippel",
    morigin="ASR",
    mversion="default",
    msymmetry=None,
) -> dict:
    df = None
    measurement_path = "{}".format(speaker_path)

    if mformat in ("klippel", "princeton", "splHVtxt"):
        if mformat == "klippel":
            h_spl, v_spl = parse_graphs_speaker_klippel(
                measurement_path, speaker_brand, speaker_name, mversion, msymmetry
            )
        elif mformat == "princeton":
            h_spl, v_spl = parse_graphs_speaker_princeton(
                measurement_path, speaker_brand, speaker_name, mversion, msymmetry
            )
        elif mformat == "splHVtxt":
            h_spl, v_spl = parse_graphs_speaker_splHVtxt(
                measurement_path, speaker_brand, speaker_name, mversion
            )

        df = None
        if msymmetry == "coaxial":
            h_spl2 = symmetrise_measurement(h_spl)
            if v_spl is None:
                v_spl2 = h_spl2.copy()
            else:
                v_spl2 = symmetrise_measurement(v_spl)
            df = filter_graphs(speaker_name, h_spl2, v_spl2)
        elif msymmetry == "horizontal":
            h_spl2 = symmetrise_measurement(h_spl)
            df = filter_graphs(speaker_name, h_spl2, v_spl)
        else:
            df = filter_graphs(speaker_name, h_spl, v_spl)
    elif mformat in ("webplotdigitizer", "rewstextdump"):
        title = None
        df_uneven = None
        if mformat == "webplotdigitizer":
            title, df_uneven = parse_graphs_speaker_webplotdigitizer(
                measurement_path, speaker_brand, speaker_name, morigin, mversion
            )
        elif mformat == "rewstextdump":
            title, df_uneven = parse_graphs_speaker_rewstextdump(
                measurement_path, speaker_brand, speaker_name, morigin, mversion
            )
        nan_count = checkNaN(df_uneven)
        if nan_count > 0:
            logger.error("df_uneven {} has {} NaNs".format(speaker_name, nan_count))
        extent_spin = spin_compute_di_eir(speaker_name, title, df_uneven)
        nan_count = checkNaN(extent_spin)
        if nan_count > 0:
            logger.error("extent_spin {} has {} NaNs".format(speaker_name, nan_count))

        df = filter_graphs_partial(extent_spin)
        nan_count = checkNaN(df)
        if nan_count > 0:
            logger.error("df {} has {} NaNs".format(speaker_name, nan_count))
            for k in df.keys():
                print("------------ {} -----------".format(k))
                print(df[k].head())

    else:
        logger.fatal("Format {:s} is unkown".format(mformat))
        sys.exit(1)

    if df is None:
        logger.warning(
            "Parsing failed for {0}/{1}/{2}".format(
                measurement_path, speaker_name, mversion
            )
        )
        return None

    return df
