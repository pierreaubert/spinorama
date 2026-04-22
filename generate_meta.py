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

import argparse
import errno
from functools import partial
from glob import glob
import hashlib
from hashlib import md5
from itertools import groupby
import json
import logging
import math
import multiprocessing
import os
from pathlib import Path

# import pprint
import sys
import time
import zipfile

import numpy as np
import pandas as pd

# Set up logging
logger = logging.getLogger("spinorama")

# Spinorama specific imports
from generate_common import get_custom_logger, args2level, cache_load, sort_metadata_per_date
from spinorama.compute_scores import speaker_pref_rating
import spinorama.constant_paths as cpaths
from spinorama.compute_estimates import estimates

# Aliased imports to avoid name collisions for specific usages
from spinorama.compute_scores import speaker_pref_rating as compute_speaker_pref_rating
from spinorama.filter_peq import peq_preamp_gain as filter_peq_preamp_gain
from spinorama.load_rew_eq import parse_eq_iir_rews as load_parse_eq_iir_rews
from spinorama.misc import sanitize_filename

# Local application imports
from datas import (
    metadata,
    Peq,
    EQ,
    PrefRating,
    Measurement,
    DataAcquisition,
    Extras,
    Parameters,
    Specifications,
    SPL,
    Size,
    Dispersion,
    Symmetry,
    MeasurementQuality,
)

# Typing imports
from typing import Any, cast, Optional, TypedDict

# number of speakers to put in the head file
METADATA_HEAD_SIZE = 20

# size of the md5 hash
KEY_LENGTH = 5

# size of years (2024 -> 4)
YEAR_LENGTH = 4


def percent(val: float, vmin: float, vmax: float) -> float:
    if math.isnan(val) or math.isnan(vmin) or math.isnan(vmax):
        logger.debug("compute percent failed with data is NaN")
        return 0.0
    if vmax == vmin:
        logger.debug("conpute percent failed with vmax == min, returning 50.0 as neutral")
        return 50.0
    p = math.floor(100 * (val - vmin) / (vmax - vmin))
    return float(min(max(0, p), 100))


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


def version_is_eq(version: str) -> bool:
    return version[-3:] == "_eq"


def update_metadata(speaker_name, version, target, data):
    # this naming convention is a bad idea and should be change to something
    # more sensible in the future
    # changing it requires extensive changes in generate_html and the js code
    if data is None:
        logger.error("update metadata: nil")
        return

    key = version
    if version_is_eq(version):
        key = version[:-3]

    if key not in metadata.speakers_info[speaker_name]["measurements"]:
        # print("update metadata: create new key {}".format(key))
        metadata.speakers_info[speaker_name]["measurements"][key] = Measurement(
            {
                "origin": "unknown",
                "format": "klippel",
            }
        )

    if target not in Measurement.__optional_keys__ and target not in Measurement.__required_keys__:
        logger.exception("Got an unknown key %s for a measurement from %s", target, speaker_name)
        return

    # print("update metadata: update key {} with target {}".format(key, target))
    metadata.speakers_info[speaker_name]["measurements"][key][target] = data


def add_measurement(speaker_name, origin, version, dfs):
    result = {
        "speaker_name": speaker_name,
        "origin": origin,
        "version": version,
    }
    if dfs is None:
        return result

    default_version = metadata.speakers_info[speaker_name].get("default_measurement")
    if default_version is None:
        logger.exception(
            "Got an version error exception for speaker_name %s default measurement",
            speaker_name,
        )
        return result

    eq_tag = ""
    if version_is_eq(version):
        eq_tag = "_eq"

    sensitivity = dfs.get("sensitivity{}".format(eq_tag), None)
    if (
        sensitivity is not None
        and metadata.speakers_info[speaker_name].get("type") == "passive"
        and version == default_version
    ):
        result["computed_sensitivity{}".format(eq_tag)] = {
            "computed": sensitivity,
            "distance": dfs.get("sensitivity_distance", 1.0),
            "sensitivity_1m": dfs.get("sensitivity_1m"),
        }

    spin = dfs.get("CEA2034")
    if spin is None or "Estimated In-Room Response" not in dfs:
        return result

    spl_h = dfs.get("SPL Horizontal_unmelted", None)
    spl_v = dfs.get("SPL Vertical_unmelted", None)
    est = estimates(spin, spl_h, spl_v)
    scaled_flatness_val = None
    if est is not None:
        result["estimates{}".format(eq_tag)] = est
        flatness = est.get("ref_band")
        if flatness is not None and not math.isnan(flatness):
            scaled_flatness_val = compute_scaled_flatness(flatness)

    inroom = dfs["Estimated In-Room Response"]
    if inroom is not None:
        pref_rating = compute_speaker_pref_rating(cea2034=spin, pir=inroom, rounded=True)
        score_penalty = 0.0
        extras_dict = dfs.get("extras")
        score_penalty = extras_dict.get("score_penalty", 0.0) if extras_dict else 0.0
        pref_rating["pref_score"] += score_penalty

        if pref_rating is None:
            return result

        result["pref_rating{}".format(eq_tag)] = pref_rating
        result["scaled_pref_rating{}".format(eq_tag)] = {
            "scaled_flatness": scaled_flatness_val,
            "scaled_pref_score": compute_scaled_pref_score(pref_rating["pref_score"]),
            "scaled_pref_wsub": compute_scaled_pref_score(pref_rating["pref_score_wsub"]),
            "scaled_lfx_hz": compute_scaled_lfx_hz(pref_rating["lfx_hz"]),
            "scaled_sm_pred_in_room": compute_scaled_lfx_hz(pref_rating["sm_pred_in_room"]),
        }
    return result


def add_score(speaker_name, speaker_data):
    """Process a single speaker's data to compute scores"""
    logger.info("Processing %s", speaker_name)

    results = []
    for origin, measurements in speaker_data.items():
        for version, dfs in measurements.items():
            try:
                result = None
                if isinstance(dfs, dict):
                    result = add_measurement(speaker_name, origin, version, dfs)
                elif isinstance(dfs, tuple):
                    # could be other stuff like an EQ as a list
                    for i in dfs:
                        if isinstance(i, dict):
                            result = add_measurement(speaker_name, origin, version, i)
                if result:
                    results.append(result)
            except KeyError as ke:
                logger.exception("KeyError in processing %s", speaker_name)
                continue
            except Exception as e:
                logger.exception("Error processing %s", speaker_name)
                continue
    return results


def add_scores(dataframe, parse_max, filters):
    """Process speaker scores for processing using multiprocessing"""
    # Prepare the arguments for parallel processing
    args = []

    for parsed, (speaker_name, speaker_data) in enumerate(dataframe.items()):
        if reject(filters, speaker_name) or (parse_max is not None and parsed >= parse_max):
            break
        args.append((speaker_name, speaker_data))

    # Determine number of processes to use (leave one CPU free)
    num_processes = max(1, multiprocessing.cpu_count() - 1)

    # Process in chunks to manage memory usage
    chunk_size = 20
    results = []

    for i in range(0, len(args), chunk_size):
        chunk = args[i : i + chunk_size]
        with multiprocessing.Pool(processes=num_processes) as pool:
            chunk_results = pool.starmap(add_score, chunk)
            results.append(chunk_results)

    # save
    for chunk in results:
        for speakers in chunk:
            for speaker in speakers:
                for item in (
                    "computed_sensitivity",
                    "estimates",
                    "pref_rating",
                    "scaled_pref_rating",
                ):
                    item_eq = "{}_eq".format(item)
                    if item in speaker:
                        update_metadata(
                            speaker["speaker_name"],
                            speaker["version"],
                            item,
                            speaker[item],
                        )
                    elif item_eq in speaker:
                        update_metadata(
                            speaker["speaker_name"],
                            speaker["version"],
                            item_eq,
                            speaker[item_eq],
                        )
                    else:
                        logger.debug(
                            "Skipping metadata update for %s %s as %s is missing",
                            speaker["speaker_name"],
                            speaker["version"],
                            item,
                        )
                # print('--- DEBUG ---')
                # pprint.pp(metadata.speakers_info[speaker['speaker_name']])


def add_quality(parse_max: Optional[int], filters: dict):
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
            if version_is_eq(version):
                continue
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
                    if brand in ("JBL", "Revel", "Infinity", "Aalto Speakers"):
                        quality = "medium"
                    elif brand in ("Ascend Acoustics",):
                        quality = "high"
            logger.debug("Setting quality %s %s to %s", speaker_name, version, quality)
            update_metadata(speaker_name, version, "quality", quality)


def _eq_worker(speaker_path, speaker_name):
    """Worker: load EQ files for a speaker. Returns (name, default_eq_or_None, {eq_key: EQ_data})."""
    default_eq = None
    eqs = {}
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
        eq_filename = "{}/eq/{}/iir-{}.txt".format(speaker_path, sanitize_filename(speaker_name), suffix)
        iir = load_parse_eq_iir_rews(eq_filename, 48000)
        if iir is not None and len(iir) > 0:
            if suffix == "autoeq":
                default_eq = "autoeq"
            eq_key = f"{suffix}".replace("-", "_")

            peq_list: list[Peq] = []
            for iir_weight, iir_filter in iir:
                if iir_weight != 0.0:
                    peq_list.append(
                        Peq(
                            type=iir_filter.biquad_type,
                            freq=iir_filter.freq,
                            srate=iir_filter.srate,
                            Q=iir_filter.q,
                            dbGain=iir_filter.db_gain,
                        )
                    )

            current_eq_data: EQ = EQ(
                display_name=display,
                filename=eq_filename,
                preamp_gain=round(filter_peq_preamp_gain(iir), 1),
                type="peq",
                peq=peq_list,
            )
            eqs[eq_key] = current_eq_data

    return (speaker_name, default_eq, eqs)


def add_eq(speaker_path, dataframe, parse_max, filters):
    """Compute some values per speaker and add them to metadata"""
    tasks = []
    parsed = 0
    for speaker_name in dataframe:
        if reject(filters, speaker_name) or (parse_max is not None and parsed > parse_max):
            break
        parsed = parsed + 1
        if speaker_name not in metadata.speakers_info:
            logger.info("Error: %s is not in metadata", speaker_name)
            continue
        tasks.append((speaker_path, speaker_name))

    num_processes = max(1, multiprocessing.cpu_count() - 1)
    with multiprocessing.Pool(processes=num_processes) as pool:
        all_results = pool.starmap(_eq_worker, tasks)

    for speaker_name, default_eq, eqs in all_results:
        speaker_info = metadata.speakers_info[speaker_name]
        if "eqs" not in speaker_info or not isinstance(speaker_info["eqs"], dict):
            speaker_info["eqs"] = {}
        if default_eq is not None:
            speaker_info["default_eq"] = default_eq
        speaker_info["eqs"].update(eqs)


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


# Formats that provide full spin data for similarity computation
SPIN_DATA_FORMATS = {"klippel", "gll_hv_txt", "spl_hv_txt", "rew_text_dump"}


def get_spin_data(freq, speaker_name, speaker_data):
    default_key = None
    try:
        default_key = metadata.speakers_info[speaker_name]["default_measurement"]
    except KeyError:
        return None

    default_format = metadata.speakers_info[speaker_name]["measurements"][default_key]["format"]
    if default_format not in SPIN_DATA_FORMATS:
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

        closest = sorted(deltas, key=lambda x: x[0])[:10]
        metadata.speakers_info[speaker_name1]["nearest"] = closest

    # print some stats
    print_stats = True
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
    metadir = cpaths.CPATH_DIST
    metafile = cpaths.CPATH_DIST_METADATA_JSON
    eqfile = cpaths.CPATH_DIST_EQDATA_JSON
    os.makedirs(metadir, mode=0o755, exist_ok=True)
    os.makedirs(cpaths.CPATH_DIST_JSON, mode=0o755, exist_ok=True)

    def check_link(hashed_filename):
        # add a link to make it easier for other scripts to find the metadata
        if (
            "metadata" in hashed_filename
            and len(hashed_filename.split("-")) == 2
            and "head" not in hashed_filename
            and cpaths.flags_ADD_HASH
        ):
            try:
                os.symlink(Path(hashed_filename).name, cpaths.CPATH_DIST_METADATA_JSON)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    os.remove(cpaths.CPATH_DIST_METADATA_JSON)
                    os.symlink(Path(hashed_filename).name, cpaths.CPATH_DIST_METADATA_JSON)
                else:
                    print("print unlink/link didnt work for {} with {}".format(hashed_filename, e))
                    raise OSError from e

    def dict_to_json(filename, d):
        js = json.dumps(d)
        key = md5(js.encode("utf-8"), usedforsecurity=False).hexdigest()[0:KEY_LENGTH]
        hashed_filename = filename
        if cpaths.flags_ADD_HASH:
            hashed_filename = "{}-{}.json".format(filename[:-KEY_LENGTH], key)

        # hash changed, remove old files
        if cpaths.flags_ADD_HASH:
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

        if cpaths.flags_ADD_HASH:
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

    # Warning: when reading the chunks you need to read them from recent to old
    # and discard he keys you a#lready have seen,
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
    speaker = args.speaker
    mversion = args.mversion
    morigin = args.morigin
    mformat = args.mformat
    parse_max = args.parse_max
    smoke_test_is_active = args.smoke_test is not None

    steps: list[tuple[str, float]] = [("start", time.perf_counter())]
    steps.append(("init", time.perf_counter()))

    filters = {
        "speaker_name": speaker,
        "origin": morigin,
        "format": mformat,
        "version": mversion,
    }
    main_df = cache_load(filters=filters, smoke_test=smoke_test_is_active, level=level)
    steps.append(("loaded", time.perf_counter()))

    if main_df is None:
        logger.error("Load failed! Please run ./generate_graphs.py")
        sys.exit(1)

    # add computed data to metadata
    logger.info("Compute data for all speakers")

    add_quality(parse_max, filters)
    steps.append(("quality", time.perf_counter()))

    add_scores(main_df, parse_max, filters)
    steps.append(("scores", time.perf_counter()))

    add_eq("./datas", main_df, parse_max, filters)
    steps.append(("eq", time.perf_counter()))

    add_near(main_df, parse_max, filters)
    steps.append(("near", time.perf_counter()))

    # write metadata in a json file for easy search
    logger.info("Write metadata")
    dump_metadata(metadata.speakers_info)
    steps.append(("dump", time.perf_counter()))

    logger.info("Bye")

    for i in range(0, len(steps) - 1):
        delta = steps[i + 1][1] - steps[i][1]
        print("{:5.2f}s {}->{}".format(delta, steps[i][0], steps[i + 1][0]))

    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate metadata for spinorama speakers.")
    parser.add_argument("--version", action="version", version="generate_meta.py version 1.6")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: WARNING).",
    )
    parser.add_argument(
        "--metadata",
        default="./datas/metadata.py",
        help="Metadata file to use (default: ./datas/metadata.py).",
    )
    parser.add_argument(
        "--parse-max", type=int, help="For debugging, set a max number of speakers to look at."
    )
    parser.add_argument("--morigin", help="Restrict to a specific origin (for debugging).")
    parser.add_argument("--speaker", help="Restrict to a specific speaker (for debugging).")
    parser.add_argument(
        "--mversion", help="Restrict to a specific measurement version (for debugging)."
    )
    parser.add_argument(
        "--mformat", help="Restrict to a specific format (e.g., klippel, webplotdigitizer)."
    )
    parser.add_argument(
        "--smoke-test",
        choices=["random", "default"],
        nargs="?",
        const="default",
        help='Run with a few speakers only. Choices: random, default. If option is present without value, "default" is used.',
    )

    args = parser.parse_args()
    level = args2level(args)
    logger = get_custom_logger(level=level, duplicate=True)
    main()
