#!/usr/bin/env python3
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

"""
usage: generate_meta.py [--help] [--version] [--log-level=<level>]\
    [--metadata=<metadata>] [--parse-max=<max>] [--use-cache=<cache>]\
    [--morigin=<morigin>] [--speaker=<speaker>] [--mversion=<mversion>]\
    [--mformat=<mformat>]\
    [--dash-ip=<ip>] [--dash-port=<port>] [--ray-local] \
    [--smoke-test=<algo>]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --metadata=<metadata> metadata file to use (default is ./datas/metadata.py)
  --smoke-test=<algo> run a few speakers only (choice are random or default)
  --parse-max=<max> for debugging, set a max number of speakers to look at
  --speaker=<speaker> restrict to a specific speaker, usefull for debugging
  --morigin=<morigin> restrict to a specific origin, usefull for debugging
  --mversion=<mversion> restrict to a specific mversion (for a given origin you can have multiple measurements)
  --mformat=<mformat> restrict to a specific format (klippel, webplotdigitizer, etc)
  --dash-ip=<dash-ip>      IP for the ray dashboard to track execution
  --dash-port=<dash-port>  Port for the ray dashbboard
"""

import errno
from hashlib import md5
from itertools import groupby
import json
from glob import glob
import math
from pathlib import Path
import os
import sys
import time
import zipfile

import numpy as np

from docopt import docopt

from spinorama import ray_setup_logger
from spinorama.constant_paths import flags_ADD_HASH

try:
    import ray
except ModuleNotFoundError:
    try:
        import miniray as ray
    except ModuleNotFoundError:
        print("Did you run env.sh?")
        sys.exit(-1)

from generate_common import (
    get_custom_logger,
    args2level,
    cache_load,
    custom_ray_init,
    sort_metadata_per_date,
    #    find_metadata_file,
)
import spinorama.constant_paths as cpaths
from spinorama.compute_estimates import estimates
from spinorama.compute_scores import speaker_pref_rating
from spinorama.filter_peq import peq_preamp_gain
from spinorama.load_rew_eq import parse_eq_iir_rews

from datas import metadata

# activate some tracing
ACTIVATE_TRACING: bool = False

# number of speakers to put in the head file
METADATA_HEAD_SIZE = 20

# size of the md5 hash
KEY_LENGTH = 5

# size of years (2024 -> 4)
YEAR_LENGTH = 4


def tracing(msg: str):
    """debugging ray is sometimes painfull"""
    if ACTIVATE_TRACING:
        print(f"---- TRACING ---- {msg} ----")


def compute_scaled_pref_score(pref_score: float) -> float:
    scaled_pref_score = 0
    if pref_score > 7:
        scaled_pref_score = 100
    elif pref_score > 6.5:
        scaled_pref_score = 90
    elif pref_score > 6:
        scaled_pref_score = 80
    elif pref_score > 5.5:
        scaled_pref_score = 70
    elif pref_score > 5:
        scaled_pref_score = 60
    elif pref_score > 4.5:
        scaled_pref_score = 50
    elif pref_score > 4.0:
        scaled_pref_score = 40
    elif pref_score > 3.0:
        scaled_pref_score = 30
    elif pref_score > 2.0:
        scaled_pref_score = 20
    elif pref_score > 1.0:
        scaled_pref_score = 10
    return scaled_pref_score


def compute_scaled_flatness(flatness: float) -> float:
    scaled_flatness = 0
    if flatness < 2.0:
        scaled_flatness = 100
    elif flatness < 2.25:
        scaled_flatness = 90
    elif flatness < 2.5:
        scaled_flatness = 80
    elif flatness < 3:
        scaled_flatness = 70
    elif flatness < 4:
        scaled_flatness = 50
    elif flatness < 5:
        scaled_flatness = 30
    elif flatness < 6:
        scaled_flatness = 10
    return scaled_flatness


def compute_scaled_lfx_hz(lfx_hz: float) -> float:
    scaled_lfx_hz = 0
    if lfx_hz < 25:
        scaled_lfx_hz = 100
    elif lfx_hz < 30:
        scaled_lfx_hz = 90
    elif lfx_hz < 35:
        scaled_lfx_hz = 80
    elif lfx_hz < 40:
        scaled_lfx_hz = 70
    elif lfx_hz < 50:
        scaled_lfx_hz = 60
    elif lfx_hz < 60:
        scaled_lfx_hz = 50
    elif lfx_hz < 70:
        scaled_lfx_hz = 40
    elif lfx_hz < 80:
        scaled_lfx_hz = 30
    elif lfx_hz < 100:
        scaled_lfx_hz = 10
    return scaled_lfx_hz


def compute_scaled_sm_pir(sm_pir: float) -> float:
    scaled_sm_pir = 0
    if sm_pir > 0.95:
        scaled_sm_pir = 100
    elif sm_pir > 0.9:
        scaled_sm_pir = 90
    elif sm_pir > 0.85:
        scaled_sm_pir = 80
    elif sm_pir > 0.8:
        scaled_sm_pir = 70
    elif sm_pir > 0.7:
        scaled_sm_pir = 60
    elif sm_pir > 0.6:
        scaled_sm_pir = 50
    elif sm_pir > 0.5:
        scaled_sm_pir = 25
    return scaled_sm_pir


def reject(filters: dict, speaker_name: str) -> bool:
    return filters["speaker_name"] is not None and filters["speaker_name"] != speaker_name


@ray.remote(num_cpus=1)
def queue_score(speaker_name, speaker_data):
    ray_setup_logger(level)
    logger.debug("Level of debug is %d", level)
    logger.info("Processing %s", speaker_name)
    results = []
    for origin, measurements in speaker_data.items():
        default_key = None
        try:
            default_key = metadata.speakers_info[speaker_name]["default_measurement"]
        except KeyError:
            logger.exception(
                "Got an key error exception for speaker_name %s default measurement",
                speaker_name,
            )
            continue

        for key, dfs in measurements.items():
            tracing("speaker_name={} version={} origin={}".format(speaker_name, key, origin))
            result = {
                "speaker": speaker_name,
                "version": key,
                "origin": origin,
            }
            try:
                if dfs is None or "CEA2034" not in dfs:
                    continue

                spin = dfs["CEA2034"]
                if spin is None or "Estimated In-Room Response" not in dfs:
                    continue

                # sensitivity
                sensitivity = dfs.get("sensitivity")
                if (
                    sensitivity is not None
                    and metadata.speakers_info[speaker_name].get("type") == "passive"
                    and key == default_key
                ):
                    result["sensitivity"] = {
                        "computed": sensitivity,
                        "distance": dfs.get("sensitivity_distance", 1.0),
                        "sensitivity_1m": dfs.get("sensitivity_1m"),
                    }

                # basic math
                logger.debug("Compute score for speaker %s key %s", speaker_name, key)
                spl_h = dfs.get("SPL Horizontal_unmelted", None)
                spl_v = dfs.get("SPL Vertical_unmelted", None)
                est = estimates(spin, spl_h, spl_v)
                if est is not None:
                    result["estimates"] = est

                inroom = dfs["Estimated In-Room Response"]
                if inroom is not None:
                    pref_rating = speaker_pref_rating(cea2034=spin, pir=inroom, rounded=True)
                    score_penalty = 0.0
                    current = metadata.speakers_info[speaker_name]["measurements"].get(key)
                    if current is not None and current.get("extras") is not None:
                        score_penalty = current["extras"].get("score_penalty", 0.0)
                        pref_rating["pref_score"] += score_penalty
                        pref_rating["pref_score_wsub"] += score_penalty

                    if pref_rating is not None:
                        result["pref_rating"] = pref_rating

            except KeyError:
                logger.exception("%s", speaker_name)

            results.append(result)
    return results


def queue_scores(dataframe, parse_max, filters):
    parsed = 0
    refs = []
    for speaker_name, speaker_data in dataframe.items():
        if reject(filters, speaker_name) or (parse_max is not None and parsed > parse_max):
            break
        parsed = parsed + 1
        ref = queue_score.remote(speaker_name, speaker_data)
        refs.append(ref)
    return refs


def add_scores(dataframe, parse_max, filters):
    """Compute some values per speaker and add them to metadata"""
    refs = queue_scores(dataframe, parse_max, filters)
    while 1:
        done_refs, remain_refs = ray.wait(refs, num_returns=min(len(refs), 64))

        for ids in done_refs:
            results = ray.get(ids)
            for result in results:
                speaker_name = result["speaker"]
                version = result["version"]
                sensitivity = result.get("sensitivity")
                computed_estimates = result.get("estimates")
                pref_rating = result.get("pref_rating")
                is_eq = version[-3:] == "_eq"

                logger.debug(
                    "%s (%s): is_eq=%s estimates=%s",
                    speaker_name,
                    version,
                    "true" if is_eq else "false",
                    "computed" if computed_estimates is not None else "failed",
                )

                if is_eq:
                    version_neq = version[:-3]
                    if computed_estimates is not None:
                        metadata.speakers_info[speaker_name]["measurements"][version_neq][
                            "estimates_eq"
                        ] = computed_estimates
                    if pref_rating is not None:
                        metadata.speakers_info[speaker_name]["measurements"][version_neq][
                            "pref_rating_eq"
                        ] = pref_rating
                    continue

                if computed_estimates is not None:
                    metadata.speakers_info[speaker_name]["measurements"][version]["estimates"] = (
                        computed_estimates
                    )
                if (
                    sensitivity is not None
                    and metadata.speakers_info[speaker_name].get("type") == "passive"
                ):
                    metadata.speakers_info[speaker_name]["measurements"][version]["sensitivity"] = (
                        sensitivity
                    )
                if pref_rating is not None:
                    metadata.speakers_info[speaker_name]["measurements"][version]["pref_rating"] = (
                        pref_rating
                    )

        if len(remain_refs) == 0:
            break
        refs = remain_refs

    # compute min and max
    min_pref_score = +100
    max_pref_score = -100
    min_pref_score_wsub = +100
    max_pref_score_wsub = -100
    min_lfx_hz = 1000
    max_lfx_hz = 0
    min_nbd_on = 1
    max_nbd_on = 0
    min_flatness = 100
    max_flatness = 1
    min_sm_sp = 1
    max_sm_sp = 0
    min_sm_pir = 1
    max_sm_pir = 0
    min_spl_peak = 1000
    max_spl_peak = 0
    min_spl_continuous = 1000
    max_spl_continuous = 0

    for speaker_name, speaker_data in dataframe.items():
        for _, measurements in speaker_data.items():
            for version in measurements:
                if speaker_name not in metadata.speakers_info:
                    # should not happen. If you mess up with names of speakers
                    # and change them, then you can have inconsistent data.
                    continue
                if version[-3:] == "_eq":
                    continue
                current = metadata.speakers_info[speaker_name]["measurements"][version]
                if "specifications" in current and "SPL" in current["specifications"]:
                    current_peak = current["specifications"]["SPL"].get("peak", None)
                    current_continuous = current["specifications"]["SPL"].get("continuous", None)
                    if current_peak:
                        min_spl_peak = min(min_spl_peak, current_peak)
                        max_spl_peak = max(max_spl_peak, current_peak)
                    if current_continuous:
                        min_spl_continuous = min(min_spl_continuous, current_continuous)
                        max_spl_continuous = max(max_spl_continuous, current_continuous)
                if "pref_rating" not in current:
                    continue
                pref_rating = current.get("pref_rating", {})
                # pref score
                pref_score = pref_rating.get("pref_score")
                if pref_score and not math.isnan(pref_score):
                    min_pref_score = min(min_pref_score, pref_score)
                    max_pref_score = max(max_pref_score, pref_score)
                # pref lfx_hz
                pref_lfx_hz = pref_rating.get("pref_lfx_hz")
                if pref_lfx_hz is not None and not math.isnan(pref_lfx_hz):
                    min_lfx_hz = min(min_lfx_hz, pref_lfx_hz)
                    max_lfx_hz = max(max_lfx_hz, pref_lfx_hz)
                # pref nbd_on
                pref_nbd_on = pref_rating.get("pref_nbd_on")
                if pref_nbd_on is not None and not math.isnan(pref_nbd_on):
                    min_nbd_on = min(min_nbd_on, pref_nbd_on)
                    max_nbd_on = max(max_nbd_on, pref_nbd_on)
                # pref sm_pir
                pref_sm_pir = pref_rating.get("pref_sm_pir")
                if pref_sm_pir is not None and not math.isnan(pref_sm_pir):
                    min_sm_pir = min(min_sm_pir, pref_sm_pir)
                    max_sm_pir = max(max_sm_pir, pref_sm_pir)
                # pref sm_sp
                pref_sm_sp = pref_rating.get("pref_sm_sp")
                if pref_sm_sp is not None and not math.isnan(pref_sm_sp):
                    min_sm_sp = min(min_sm_sp, pref_sm_sp)
                    max_sm_sp = max(max_sm_sp, pref_sm_sp)
                # pref score w/sub
                pref_score_wsub = pref_rating.get("pref_score_wsub")
                if pref_score_wsub is not None and not math.isnan(pref_score_wsub):
                    min_pref_score_wsub = min(min_pref_score_wsub, pref_score_wsub)
                    max_pref_score_wsub = max(max_pref_score_wsub, pref_score_wsub)
                # flatness
                if "estimates" not in current:
                    continue
                flatness = current["estimates"].get("ref_band")
                if flatness is not None and not math.isnan(flatness):
                    min_flatness = min(min_flatness, flatness)
                    max_flatness = max(max_flatness, flatness)

    # print("info: spl continuous [{}, {}]".format(min_spl_continuous, max_spl_continuous))
    # print("info: spl       peak [{}, {}]".format(min_spl_peak, max_spl_peak))

    # if we are looking only after 1 speaker, return
    if len(dataframe.items()) == 1:
        logger.info("skipping normalization with only one speaker")
        return

    # add normalized value to metadata
    parsed = 0
    for speaker_name, speaker_data in dataframe.items():
        if parse_max is not None and parsed > parse_max:
            break
        parsed = parsed + 1
        logger.info("Normalize data for %s", speaker_name)
        if speaker_name not in metadata.speakers_info:
            # should not happen. If you mess up with names of speakers
            # and change them, then you can have inconsistent data.
            continue
        for _, measurements in speaker_data.items():
            for version, measurement in measurements.items():
                if version not in metadata.speakers_info[speaker_name]["measurements"]:
                    if len(version) > 4 and version[-3:] != "_eq":
                        logger.error(
                            "Confusion in metadata, did you edit a speaker recently? %s should be in metadata for %s",
                            version,
                            speaker_name,
                        )
                    continue

                if measurement is None or "CEA2034" not in measurement:
                    logger.debug("skipping normalization no spinorama for %s", speaker_name)
                    continue

                spin = measurement["CEA2034"]
                if spin is None:
                    logger.debug("skipping normalization no spinorama for %s", speaker_name)
                    continue
                if version[-3:] == "_eq":
                    logger.debug("skipping normalization for eq for %s", speaker_name)
                    continue
                if "estimates" not in metadata.speakers_info[speaker_name]["measurements"][version]:
                    logger.debug(
                        "skipping normalization no estimates in %s for %s",
                        version,
                        speaker_name,
                    )
                    continue
                logger.debug("Compute relative score for speaker %s", speaker_name)
                if (
                    "pref_rating"
                    not in metadata.speakers_info[speaker_name]["measurements"][version]
                ):
                    logger.debug(
                        "skipping normalization no pref_rating in %s for %s",
                        version,
                        speaker_name,
                    )
                    continue
                # get values
                pref_rating = metadata.speakers_info[speaker_name]["measurements"][version][
                    "pref_rating"
                ]
                pref_score_wsub = pref_rating["pref_score_wsub"]
                nbd_on = pref_rating["nbd_on_axis"]
                sm_sp = pref_rating["sm_sound_power"]
                sm_pir = pref_rating["sm_pred_in_room"]
                flatness = metadata.speakers_info[speaker_name]["measurements"][version][
                    "estimates"
                ]["ref_band"]
                pref_score = -1
                lfx_hz = -1
                if "pref_score" in pref_rating:
                    pref_score = pref_rating["pref_score"]
                if "lfx_hz" in pref_rating:
                    lfx_hz = pref_rating["lfx_hz"]

                # normalize min and max
                def percent(val, vmin, vmax):
                    if math.isnan(val) or math.isnan(vmin) or math.isnan(vmax):
                        logger.debug("data is NaN")
                        return 0
                    if vmax == vmin:
                        logger.debug("max == min")
                        return 0
                    p = math.floor(100 * (val - vmin) / (vmax - vmin))
                    return min(max(0, p), 100)

                scaled_pref_score = None
                scaled_pref_score_wsub = percent(
                    pref_score_wsub, min_pref_score_wsub, max_pref_score_wsub
                )
                scaled_pref_score = None
                scaled_lfx_hz = None
                if "pref_score" in pref_rating:
                    scaled_pref_score = percent(pref_score, min_pref_score, max_pref_score)
                    scaled_lfx_hz = 100 - percent(lfx_hz, min_lfx_hz, max_lfx_hz)
                scaled_nbd_on = 100 - percent(nbd_on, min_nbd_on, max_nbd_on)
                scaled_sm_sp = percent(sm_sp, min_sm_sp, max_sm_sp)
                scaled_sm_pir = percent(sm_pir, min_sm_pir, max_sm_pir)
                scaled_flatness = 100 - percent(flatness, min_flatness, max_flatness)
                # bucket score instead of a linear scale
                if scaled_pref_score is not None:
                    scaled_pref_score = compute_scaled_pref_score(pref_score)
                # bucket flatness instead of a linear scale
                scaled_flatness = compute_scaled_flatness(flatness)
                # bucked lfx too
                if scaled_lfx_hz is not None:
                    scaled_lfx_hz = compute_scaled_lfx_hz(lfx_hz)
                # bucket sm_pir too
                scaled_sm_pir = compute_scaled_sm_pir(sm_pir)
                # add normalized values
                scaled_pref_rating: dict[str, float] = {
                    "scaled_pref_score_wsub": scaled_pref_score_wsub,
                    "scaled_nbd_on_axis": scaled_nbd_on,
                    "scaled_flatness": scaled_flatness,
                    "scaled_sm_sound_power": scaled_sm_sp,
                    "scaled_sm_pred_in_room": scaled_sm_pir,
                }
                if "pref_score" in pref_rating and scaled_pref_score is not None:
                    scaled_pref_rating["scaled_pref_score"] = scaled_pref_score
                if "lfx_hz" in pref_rating and scaled_lfx_hz is not None:
                    scaled_pref_rating["scaled_lfx_hz"] = scaled_lfx_hz
                logger.info("Adding %s", scaled_pref_rating)
                metadata.speakers_info[speaker_name]["measurements"][version][
                    "scaled_pref_rating"
                ] = scaled_pref_rating


def add_quality(parse_max: int, filters: dict):
    """Compute quality of data and add it to metadata
    Rules:
    - Independant measurements from ASR or EAC : high quality
    - Most measurements from Harmann group: medium quality
    - Most measurements quasi anechoic: low quality
    This can be overriden by setting the correct value in the metadata file
    """
    parsed = 0
    for speaker_name, speaker_data in metadata.speakers_info.items():
        if reject(filters, speaker_name) or (parse_max is not None and parsed > parse_max):
            break
        parsed = parsed + 1
        logger.info("Processing %s", speaker_name)
        for version, m_data in speaker_data["measurements"].items():
            quality = m_data.get("quality", "unknown")
            if "quality" not in m_data:
                origin = m_data.get("origin")
                measurement_format = m_data.get("format")
                if measurement_format == "klippel":
                    quality = "high"
                elif origin == "Princeton":
                    quality = "low"
                elif origin == "Misc":
                    if "napilopez" in version or "audioholics" in version:
                        quality = "low"
                elif "Vendor" in origin:
                    brand = speaker_data["brand"]
                    # Harman group provides spin from an anechoic room
                    if brand in ("JBL", "Revel", "Infinity"):
                        quality = "medium"
                logger.debug("Setting quality %s %s to %s", speaker_name, version, quality)
            metadata.speakers_info[speaker_name]["measurements"][version]["quality"] = quality


# def add_slopes(parse_max: int, filters: dict):
#     """Add slopes in db/oct for each curves and smoothness if available"""
#     parsed = 0
#     for speaker_name, speaker_data in metadata.speakers_info.items():
#         if reject(filters, speaker_name) or (parse_max is not None and parsed > parse_max):
#             break
#         parsed = parsed + 1
#         logger.info("Processing %s", speaker_name)
#         for version, m_data in speaker_data["measurements"].items():
#             for key, value in m_data.items():
#                 if 'slope_' in key or 'smoothness_' in key:
#                     print('accepted {}'.format(key))
#                     metadata.speakers_info[speaker_name]["measurements"][version][key] = value


def add_eq(speaker_path, dataframe, parse_max, filters):
    """Compute some values per speaker and add them to metadata"""
    parsed = 0
    for speaker_name in dataframe:
        if reject(filters, speaker_name) or (parse_max is not None and parsed > parse_max):
            break
        parsed = parsed + 1
        logger.info("Processing %s", speaker_name)

        if speaker_name not in metadata.speakers_info:
            logger.info("Error: %s is not in metadata", speaker_name)
            continue

        metadata.speakers_info[speaker_name]["eqs"] = {}
        for suffix, display in (
            ("autoeq", "AutomaticEQ (IIR)"),
            ("autoeq-lw", "AutomaticEQ LW (IIR)"),
            ("autoeq-score", "AutomaticEQ Score (IIR)"),
            ("amirm", "amirm@ASR (IIR)"),
            ("maiky76", "maiky76@ASR (IIR)"),
            ("maiky76-lw", "maiky76@ASR LW (IIR)"),
            ("maiky76-score", "maiky76@ASR (IIR)"),
            ("flipflop", "flipflop@ASR (IIR)"),
            ("autoeq-dbx-1215", "Graphic EQ 15 bands"),
            ("autoeq-dbx-1231", "Graphic EQ 31 bands"),
        ):
            eq_filename = "{}/eq/{}/iir-{}.txt".format(speaker_path, speaker_name, suffix)
            iir = parse_eq_iir_rews(eq_filename, 48000)
            if iir is not None and len(iir) > 0:
                if suffix == "autoeq":
                    metadata.speakers_info[speaker_name]["default_eq"] = "autoeq"
                eq_key = f"{suffix}".replace("-", "_")
                metadata.speakers_info[speaker_name]["eqs"][eq_key] = {}
                metadata.speakers_info[speaker_name]["eqs"][eq_key]["display_name"] = display
                metadata.speakers_info[speaker_name]["eqs"][eq_key]["filename"] = eq_filename
                metadata.speakers_info[speaker_name]["eqs"][eq_key]["preamp_gain"] = round(
                    peq_preamp_gain(iir), 1
                )
                metadata.speakers_info[speaker_name]["eqs"][eq_key]["type"] = "peq"
                metadata.speakers_info[speaker_name]["eqs"][eq_key]["peq"] = []
                for iir_weigth, iir_filter in iir:
                    if iir_weigth != 0.0:
                        metadata.speakers_info[speaker_name]["eqs"][eq_key]["peq"].append(
                            {
                                "type": iir_filter.biquad_type,
                                "freq": iir_filter.freq,
                                "srate": iir_filter.srate,
                                "Q": iir_filter.q,
                                "dbGain": iir_filter.db_gain,
                            }
                        )
                        logger.debug(
                            "adding eq: %s", metadata.speakers_info[speaker_name]["eqs"][eq_key]
                        )


def interpolate(speaker_name, freq, freq1, data1):
    data = []
    len1 = len(freq1)
    i = 0
    for f in freq:
        try:
            while freq1[i] < f and i < len1:
                i += 1

            if i >= len1:
                data.append(0.0)
                continue

            if freq1[i] >= f:
                if i == 0:
                    data.append(0.0)
                    continue
                else:
                    i = i - 1

            j = i
            while freq1[j] < f and j < len1:
                j += 1
            if j >= len1:
                data.append(data1[i])
                continue

            interp = data1[i] + (data1[j] - data1[i]) * (f - freq1[i]) / (freq1[j] - freq1[i])
            data.append(interp)
        except IndexError:
            logger.exception("%s: for f=%f", speaker_name, f)
            data.append(0.0)

    return np.array(data)


def compute_near(fspin1, fspin2):
    lw1, er1, sp1 = fspin1
    lw2, er2, sp2 = fspin2

    lw = lw1 - lw2
    er = er1 - er2
    sp = sp1 - sp2

    near = np.mean([np.linalg.norm(lw), np.linalg.norm(sp), np.linalg.norm(er, 2)])
    if math.isnan(near):
        return 1000000.0
    return near


def get_spin_data(freq, speaker_name, speaker_data):
    default_key = None
    try:
        default_key = metadata.speakers_info[speaker_name]["default_measurement"]
        # default_origin = metadata.speakers_info[speaker_name]["measurements"][default_key]["origin"]
    except KeyError:
        return None

    default_format = metadata.speakers_info[speaker_name]["measurements"][default_key]["format"]
    if default_format != "klippel":
        return None

    for reviewer, measurements in speaker_data.items():
        if "asr" in default_key and reviewer != "ASR":
            continue
        if "eac" in default_key and reviewer != "ErinsAudioCorner":
            continue
        for key, dfs in measurements.items():
            if "_eq" in key:
                continue
            if dfs is None or "CEA2034" not in dfs:
                return None

            spin = dfs["CEA2034_unmelted"]
            if spin is None or "Listening Window" not in spin or "Sound Power" not in spin:
                return None

            lw = interpolate(speaker_name, freq, spin["Freq"], spin["Listening Window"])
            er = interpolate(speaker_name, freq, spin["Freq"], spin["Early Reflections"])
            sp = interpolate(speaker_name, freq, spin["Freq"], spin["Sound Power"])

            return lw, er, sp

        logger.warning("skipping %s no match", speaker_name)
    return None


def add_near(dataframe, parse_max: int, filters: dict):
    """Compute nearest speaker"""
    parsed = 0
    distribution = []
    normalized = {}
    distances = {}
    freq = np.logspace(np.log10(25), np.log10(16000), 100)
    for speaker_name, speaker_data in dataframe.items():
        curves = get_spin_data(freq, speaker_name, speaker_data)
        if curves is not None:
            normalized[speaker_name] = curves
            distances[speaker_name] = {}

    for speaker_name1, speaker_data1 in normalized.items():
        if reject(filters, speaker_name1) or (parse_max is not None and parsed > parse_max):
            break
        parsed = parsed + 1
        deltas = []

        for speaker_name2, speaker_data2 in normalized.items():
            if speaker_name1 == speaker_name2:
                continue
            prev_delta = distances[speaker_name2].get(speaker_name1)
            delta = prev_delta
            if prev_delta is None:
                delta = compute_near(speaker_data1, speaker_data2)
                distances[speaker_name2][speaker_name1] = delta
                distances[speaker_name1][speaker_name2] = delta
            deltas.append((delta, speaker_name2))
            distribution.append(delta)

        closest = sorted(deltas, key=lambda x: x[0])[:3]
        metadata.speakers_info[speaker_name1]["nearest"] = closest

    # print some stats
    print_stats = False
    if print_stats:
        height = 20
        bins = 80
        h = np.histogram(distribution, bins=bins)
        hmin = np.min(h[0])
        hmax = np.max(h[0])
        print("distances [{}, {}]".format(hmin, hmax))
        val = [int(i * height / hmax) for i in h[0] if hmax != 0]

        def lign(v):
            return ["." if i < v else " " for i in range(height)]

        table = [lign(v) for v in val]
        ttable = ["".join(row) for row in np.array(table).T]
        print("\n".join(ttable))


def dump_metadata(meta):
    metadir = cpaths.CPATH_DOCS
    metafile = cpaths.CPATH_DOCS_METADATA_JSON
    eqfile = cpaths.CPATH_DOCS_EQDATA_JSON
    os.makedirs(metadir, mode=0o755, exist_ok=True)
    os.makedirs(cpaths.CPATH_DOCS_JSON, mode=0o755, exist_ok=True)

    def check_link(hashed_filename):
        # add a link to make it easier for other scripts to find the metadata
        if (
            "metadata" in hashed_filename
            and len(hashed_filename.split("-")) == 2
            and "head" not in hashed_filename
            and flags_ADD_HASH
        ):
            try:
                os.symlink(Path(hashed_filename).name, cpaths.CPATH_DOCS_METADATA_JSON)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    os.remove(cpaths.CPATH_DOCS_METADATA_JSON)
                    os.symlink(Path(hashed_filename).name, cpaths.CPATH_DOCS_METADATA_JSON)
                else:
                    print("print unlink/link didnt work for {} with {}".format(hashed_filename, e))
                    raise OSError from e

    def dict_to_json(filename, d):
        js = json.dumps(d)
        key = md5(js.encode("utf-8"), usedforsecurity=False).hexdigest()[0:KEY_LENGTH]
        hashed_filename = filename
        if flags_ADD_HASH:
            hashed_filename = "{}-{}.json".format(filename[:-KEY_LENGTH], key)
        if (
            os.path.exists(hashed_filename)
            and os.path.exists(hashed_filename + ".zip")
            and os.path.exists(hashed_filename + ".bz2")
        ):
            logger.debug("skipping %s", hashed_filename)
            check_link(hashed_filename)
            return

        # hash changed, remove old files
        if flags_ADD_HASH:
            old_hash_pattern = "{}-*.json".format(filename[:-KEY_LENGTH])
            old_hash_pattern_zip = "{}.zip".format(old_hash_pattern)
            old_hash_pattern_bz2 = "{}.bz2".format(old_hash_pattern)
            for pattern in (old_hash_pattern, old_hash_pattern_zip, old_hash_pattern_bz2):
                for old_filename in glob(pattern):
                    logger.debug("remove old file %s", old_filename)
                    # print("removed old file {}".format(old_filename))
                    os.remove(old_filename)

        # write the non zipped file
        with open(hashed_filename, "w", encoding="utf-8") as f:
            f.write(js)
            f.close()
            logger.debug("generated %s", hashed_filename)

        # write the zip and bz2 files
        for ext, method in (
            ("zip", zipfile.ZIP_DEFLATED),
            ("bz2", zipfile.ZIP_BZIP2),
        ):
            with zipfile.ZipFile(
                "{}.{}".format(hashed_filename, ext),
                "w",
                compression=method,
                allowZip64=True,
            ) as current_compressed:
                current_compressed.writestr(hashed_filename, js)
                logger.debug("generated %s and %s version", hashed_filename, ext)

        if flags_ADD_HASH:
            check_link(hashed_filename)

    # split eq data v.s. others as they are not required on the front page
    meta_full = {
        k: {k2: v2 for k2, v2 in v.items() if k2 != "eqs"}
        for k, v in meta.items()
        if not v.get("skip", False)
    }
    eq_full = {
        k: {k2: v2 for k2, v2 in v.items() if k2 in ("eqs", "brand", "model")}
        for k, v in meta.items()
        if not v.get("skip", False)
    }

    # first store a big file with all the data inside. It worked well up to 2023
    # when it became too large even compressed and slowed down the web frontend
    # too much
    dict_to_json(metafile, meta_full)
    dict_to_json(eqfile, eq_full)

    #    debugjs = find_metadata_file()
    #    debugmeta = None
    #    with open(debugjs, "r") as f:
    #        debugmeta = json.load(f)
    #    print('DEBUG: size of full ==> {}'.format(len(meta.keys())))
    #    print('DEBUG: size of meta ==> {}'.format(len(meta_full.keys())))
    #    print('DEBUG: size of   js ==> {}'.format(len(debugmeta.keys())))

    # generate a short head for rapid home page charging

    # TODO(pierre)
    # let's check if it is faster to load slices than the full file
    # partitionning is per year, each file is hashed and the hash
    # is stored in the name.

    # Warning: when reading the chunks you need to read them from recent to old and discard he keys you a#lready have seen,
    meta_sorted_date = list(sort_metadata_per_date(meta_full).items())
    meta_sorted_date_head = dict(meta_sorted_date[0:METADATA_HEAD_SIZE])
    meta_sorted_date_tail = dict(meta_sorted_date[METADATA_HEAD_SIZE:])

    filename = metafile[:-KEY_LENGTH] + "-head.json"
    dict_to_json(filename, meta_sorted_date_head)

    def by_year(key):
        m = meta_sorted_date_tail[key]
        def_m = m["default_measurement"]
        year = int(m["measurements"][def_m].get("review_published", "1970")[0:YEAR_LENGTH])
        # group together years without too many reviews
        if year > 1970 and year < 2020:
            return 2019
        return year

    grouped_by_year = groupby(meta_sorted_date_tail, by_year)
    for year, group in grouped_by_year:
        filename = "{}-{:4d}.json".format(metafile[:-KEY_LENGTH], year)
        dict_to_json(filename, {k: meta_sorted_date_tail[k] for k in list(group)})


def main():
    main_df = None
    speaker = args["--speaker"]
    mversion = args["--mversion"]
    morigin = args["--morigin"]
    mformat = args["--mformat"]
    parse_max = args["--parse-max"]
    if parse_max is not None:
        parse_max = int(parse_max)
    smoke_test = False
    if args["--smoke-test"] is not None:
        smoke_test = True

    steps: list[tuple[str, float]] = [("start", time.perf_counter())]
    custom_ray_init(args)
    steps.append(("ray init", time.perf_counter()))

    filters = {
        "speaker_name": speaker,
        "origin": morigin,
        "format": mformat,
        "version": mversion,
    }
    main_df = cache_load(filters=filters, smoke_test=smoke_test, level=level)
    steps.append(("loaded", time.perf_counter()))

    if main_df is None:
        logger.error("Load failed! Please run ./generate_graphs.py")
        sys.exit(1)

    # add computed data to metadata
    logger.info("Compute scores per speaker")
    add_quality(parse_max, filters)
    steps.append(("quality", time.perf_counter()))
    add_scores(main_df, parse_max, filters)
    steps.append(("scores", time.perf_counter()))
    add_eq("./datas", main_df, parse_max, filters)
    steps.append(("eq", time.perf_counter()))
    add_near(main_df, parse_max, filters)
    steps.append(("near", time.perf_counter()))
    # add_slopes(parse_max, filters)
    # steps.append(("slopes", time.perf_counter()))

    # write metadata in a json file for easy search
    logger.info("Write metadata")
    dump_metadata(metadata.speakers_info)
    steps.append(("dump", time.perf_counter()))

    ray.shutdown()
    logger.info("Bye")

    for i in range(0, len(steps) - 1):
        delta = steps[i + 1][1] - steps[i][1]
        print("{:5.2f}s {}->{}".format(delta, steps[i][0], steps[i + 1][0]))

    sys.exit(0)


if __name__ == "__main__":
    args = docopt(__doc__, version="generate_meta.py version 1.6", options_first=True)
    level = args2level(args)
    logger = get_custom_logger(level=level, duplicate=True)
    main()
