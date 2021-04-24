#                                                  -*- coding: utf-8 -*-
import os
import logging
import sys

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray


from .load import filter_graphs, load_normalize
from .load_klippel import parse_graphs_speaker_klippel
from .load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from .load_princeton import parse_graphs_speaker_princeton
from .load_rewstextdump import parse_graphs_speaker_rewstextdump
from .load_rewseq import parse_eq_iir_rews
from .load_splHVtxt import parse_graphs_speaker_splHVtxt
from .filter_peq import peq_apply_measurements


logger = logging.getLogger("spinorama")


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
    if mformat == "klippel":
        df = parse_graphs_speaker_klippel(
            measurement_path, speaker_brand, speaker_name, mversion
        )
    elif mformat == "webplotdigitizer":
        df = parse_graphs_speaker_webplotdigitizer(
            measurement_path, speaker_brand, speaker_name, morigin, mversion
        )
    elif mformat == "princeton":
        df = parse_graphs_speaker_princeton(
            measurement_path, speaker_brand, speaker_name, mversion, msymmetry
        )
    elif mformat == "splHVtxt":
        df = parse_graphs_speaker_splHVtxt(
            measurement_path, speaker_brand, speaker_name, mversion
        )
    elif mformat == "rewstextdump":
        df = parse_graphs_speaker_rewstextdump(
            measurement_path, speaker_brand, speaker_name, morigin, mversion
        )
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
    df_normalized = load_normalize(df)
    if df_normalized is None:
        logger.warning(
            "Normalisation failed for {0} {1} {2}".format(
                measurement_path, speaker_name, mversion
            )
        )
        return None
    return df_normalized
