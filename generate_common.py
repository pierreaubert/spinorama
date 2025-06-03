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

from collections import defaultdict
import difflib
from functools import partial
from glob import glob
from hashlib import md5
import ipaddress
import logging
import multiprocessing
import os
import pathlib
import re
import sys
from typing import Callable, Any
import warnings

import flammkuchen as fl

import tables

import datas.metadata as metadata

import spinorama.constant_paths as cpaths
from spinorama.constant_paths import flags_ADD_HASH

CACHE_DIR = ".cache"


def get_similar_names(speakername):
    return difflib.get_close_matches(speakername, metadata.speakers_info.keys())


def get_custom_logger(level, duplicate):
    """Define properties of our logger"""
    custom = logging.getLogger("spinorama")
    custom_file_handler = logging.FileHandler("build/debug_optim.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    custom_file_handler.setFormatter(formatter)
    custom.addHandler(custom_file_handler)
    if duplicate is True:
        custom_stream_handler = logging.StreamHandler(sys.stdout)
        custom_stream_handler.setFormatter(formatter)
        custom.addHandler(custom_stream_handler)
    custom.setLevel(level)
    return custom


def args2level(args):
    """Transform an argument into a logger level"""
    level = logging.WARNING
    if hasattr(args, "log_level") and args.log_level is not None:
        check_level = args.log_level.upper()
        if check_level in ("INFO", "DEBUG", "WARNING", "ERROR"):
            if check_level == "INFO":
                level = logging.INFO
            elif check_level == "DEBUG":
                level = logging.DEBUG
            elif check_level == "WARNING":
                level = logging.WARNING
            elif check_level == "ERROR":
                level = logging.ERROR
    return level


def create_default_directories():
    for d in (
        CACHE_DIR,
        cpaths.CPATH_DIST,
        cpaths.CPATH_DIST_PICTURES,
        cpaths.CPATH_DIST_SPEAKERS,
        cpaths.CPATH_BUILD_EQ,
        cpaths.CPATH_BUILD_WEBSITE,
        cpaths.CPATH_BUILD_MAKO,
    ):
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)


def cache_key(name: str) -> str:
    # 256 partitions, use hashlib for stable hash
    key = md5(name.encode("utf-8"), usedforsecurity=False).hexdigest()
    short_key = key[0:2]
    return f"{short_key:2s}"


def cache_match(key: str, name: str) -> bool:
    return key == cache_key(name)


def cache_hash(df_all: dict) -> dict:
    df_hashed = {}
    for k, v in df_all.items():
        if k is None or len(k) == 0:
            continue
        h = cache_key(k)
        if h not in df_hashed:
            df_hashed[h] = {}
        df_hashed[h][k] = v
    return df_hashed


def cache_save_key(key: str, data):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", tables.NaturalNameWarning)
        # print('{} {}'.format(key, data.keys()))
        cache_name = "{}/{}.h5".format(CACHE_DIR, key)
        # print(cache_name)
        fl.save(path=cache_name, data=data)


def cache_save(df_all: dict):
    pathlib.Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    df_hashed = cache_hash(df_all)
    for key, data in df_hashed.items():
        cache_save_key(key, data)
    print("(saved {} speakers)".format(len(df_all)))


def is_filtered(speaker: str, filters: dict):
    if filters.get("speaker_name") is not None and filters.get("speaker_name") != speaker:
        return True

    current = None
    if speaker in metadata.speakers_info:
        if "default_measurement" not in metadata.speakers_info[speaker]:
            print("error no default measurement for {}".format(speaker))
            return True
        first = metadata.speakers_info[speaker]["default_measurement"]
        if first not in metadata.speakers_info[speaker]["measurements"]:
            # only happens when you change the metadata
            return False
        current = metadata.speakers_info[speaker]["measurements"][first]

    if (
        filters.get("origin") is not None
        and current is not None
        and current["origin"] != filters.get("origin")
    ):
        return True

    return (
        filters.get("format") is not None
        and current is not None
        and current["format"] != filters.get("format")
    )


def cache_load_seq(filters, smoke_test):
    df_all = defaultdict()
    cache_files = glob("./{}/*.h5".format(CACHE_DIR))
    if len(cache_files) == 0:
        cache_files = glob("../{}/*.h5".format(CACHE_DIR))
    if len(cache_files) == 0:
        print("Cannot find cache directory or files! Did you run ./generate_graphs.py ?")
        return df_all
    count = 0
    logging.debug("found %d cache files", len(cache_files))
    for cache in cache_files:
        speaker_name = filters.get("speaker_name")
        if speaker_name is not None and cache[-5:-3] != cache_key(speaker_name):
            logging.debug("skipping %s key=%s", speaker_name, cache_key(speaker_name))
            continue
        df_read = fl.load(path=cache)
        logging.debug("reading file %s found %d entries", cache, len(df_read) if df_read else 0)
        if not isinstance(df_read, dict):
            continue
        for speaker, data in df_read.items():
            if speaker in df_all:
                print("error in cache: {} is already in keys".format(speaker))
                continue
            if is_filtered(speaker, filters):
                # print(speaker, speaker_name)
                continue
            df_all[speaker] = data
            count += 1
        if smoke_test and count > 10:
            break

    print("(loaded {} speakers)".format(len(df_all)))
    return df_all


def _cache_fetch_worker(args):
    """Worker function for loading cache files in parallel"""
    cachepath, level = args
    logger = logging.getLogger("spinorama")
    logger.setLevel(level)
    logger.debug("Level of debug is %d", level)
    try:
        return fl.load(path=cachepath)
    except Exception as e:
        logger.exception("Error loading cache file %s", cachepath)
        return None


def cache_load_distributed(filters, smoke_test, level):
    """Load cache files in parallel using multiprocessing"""
    cache_files = glob("./{}/*.h5".format(CACHE_DIR))

    # Determine number of processes to use (leave one CPU free)
    num_processes = max(1, multiprocessing.cpu_count() - 1)

    # Filter cache files based on speaker_name if provided
    if filters.get("speaker_name") is not None:
        speaker_key = cache_key(filters.get("speaker_name"))
        cache_files = [f for f in cache_files if f[-5:-3] == speaker_key]
        num_processes = 1

    print(f"(processing {len(cache_files)} files in parallel x{num_processes})")

    df_all = {}
    count = 0

    # Process files in chunks
    chunk_size = 16
    for i in range(0, len(cache_files), chunk_size):
        chunk = cache_files[i : i + chunk_size]

        # Create a pool of workers
        with multiprocessing.Pool(processes=num_processes) as pool:
            # Map the worker function to the chunk of files
            results = pool.map(_cache_fetch_worker, [(cache, level) for cache in chunk])

            # Process results
            for df_read in results:
                if df_read is None:
                    continue

                if isinstance(df_read, dict):
                    for speaker, data in df_read.items():
                        if is_filtered(speaker, filters):
                            continue

                        if speaker in df_all:
                            print(f"Warning: {speaker} already exists in cache, overwriting")

                        df_all[speaker] = data
                        count += 1

                        if smoke_test and count > 10:
                            break

                if smoke_test and count > 10:
                    break

        if smoke_test and count > 10:
            break

    return df_all


def cache_load(filters, smoke_test, level):
    """Load cache using parallel processing if no specific speaker is requested"""
    if filters.get("speaker_name") is None:
        try:
            return cache_load_distributed(filters, smoke_test, level)
        except Exception as e:
            print(f"Parallel cache loading failed, falling back to sequential: {e}")

    # Fall back to sequential loading
    return cache_load_seq(filters, smoke_test)


def cache_update(df_new, filters, level):
    if not os.path.exists(CACHE_DIR) or len(df_new) == 0:
        return

    logger = logging.getLogger("spinorama")
    print("Updating cache ", end=" ", flush=True)
    count = 0
    for new_speaker, new_datas in df_new.items():
        if filters is not None and new_speaker != filters.get("speaker", ""):
            continue
        df_old = cache_load(filters={"speaker_name": new_speaker}, smoke_test=False, level=level)
        for new_origin, new_measurements in new_datas.items():
            logger.debug(
                "Updating %s %s %d measurements", new_speaker, new_origin, len(new_measurements)
            )
            for new_measurement, new_data in new_measurements.items():
                if new_speaker not in df_old:
                    logger.debug(
                        "Adding new origin %s %s %s", new_speaker, new_origin, new_measurement
                    )
                    df_old[new_speaker] = {new_origin: {new_measurement: new_data}}
                elif new_origin not in df_old[new_speaker]:
                    logger.debug(
                        "Adding first measurement %s %s %s",
                        new_speaker,
                        new_origin,
                        new_measurement,
                    )
                    df_old[new_speaker][new_origin] = {new_measurement: new_data}
                else:
                    logger.debug(
                        "Adding new measurement %s %s %s", new_speaker, new_origin, new_measurement
                    )
                    df_old[new_speaker][new_origin][new_measurement] = new_data
                count += 1
        cache_save_key(cache_key(new_speaker), df_old)
    print(f"(updated +{count}) ", end=" ", flush=True)
    print("(saved).")


def sort_metadata_per_date(meta):
    def sort_meta_date(s):
        if s is not None:
            return s.get("review_published", "20170101")
        return "20170101"

    keys_sorted_date = sorted(
        meta,
        key=lambda a: sort_meta_date(
            meta[a]["measurements"].get(meta[a].get("default_measurement"))
        ),
        reverse=True,
    )
    return {k: meta[k] for k in keys_sorted_date}


def sort_metadata_per_score(meta):
    def sort_meta_score(s):
        if s is not None and "pref_rating" in s and "pref_score" in s["pref_rating"]:
            return s["pref_rating"]["pref_score"]
        return -1

    keys_sorted_score = sorted(
        meta,
        key=lambda a: sort_meta_score(
            meta[a]["measurements"].get(meta[a].get("default_measurement"))
        ),
        reverse=True,
    )
    return {k: meta[k] for k in keys_sorted_score}


def find_metadata_file():
    if not flags_ADD_HASH:
        return [cpaths.CPATH_DIST_METADATA_JSON, cpaths.CPATH_DIST_EQDATA_JSON]

    json_paths = []
    for radical, json_path in (
        ("metadata", cpaths.CPATH_DIST_METADATA_JSON),
        ("eqdata", cpaths.CPATH_DIST_EQDATA_JSON),
    ):
        pattern = "{}-[0-9a-f]*.json".format(json_path[:-5])
        json_filenames = glob(pattern)
        json_filename = None
        for json_maybe in json_filenames:
            regexp = ".*/{}[-][0-9a-f]{{5}}[.]json$".format(radical)
            check = re.match(regexp, json_maybe)
            if check is not None:
                json_filename = json_maybe
                break
        if json_filename is not None and os.path.exists(json_filename):
            json_paths.append(json_filename)
        else:
            json_paths.append(None)
    return json_paths


def find_metadata_chunks():
    json_paths = {}
    json_path = cpaths.CPATH_DIST_METADATA_JSON
    pattern = "{}*.json".format(json_path[:-5])
    regexp = "{}[-][0-9a-z]{{4}}[.]json$".format(json_path[:-5])
    if flags_ADD_HASH:
        regexp = "{}[-][0-9a-z]{{4}}[-][0-9a-f]{{5}}[.]json$".format(json_path[:-5])
    json_filenames = glob(pattern)
    for json_filename in json_filenames:
        check = re.search(regexp, json_filename)
        if not check:
            continue
        if os.path.exists(json_filename):
            span = check.span()
            if flags_ADD_HASH:
                tokens = json_filename[span[0] : span[1]].split("-")
                json_paths[tokens[1]] = json_filename
            else:
                tokens = json_filename[span[0] : span[1]].split("-")
                json_paths[tokens[1].split(".")[0]] = json_filename
    return json_paths


def run_in_parallel(
    func: Callable, tasks: list[tuple[Any, ...]], num_processes: int = -1, chunk_size: int = 1
) -> list[Any]:
    """
    Run a function in parallel on multiple processes.

    Args:
        func: The function to run in parallel
        tasks: List of argument tuples to pass to the function
        num_processes: Number of processes to use (default: cpu_count - 1)
        chunk_size: Number of tasks to process in each process (default: 1)

    Returns:
        List of results in the same order as tasks
    """
    logger = logging.getLogger("spinorama")
    if num_processes == -1:
        num_processes = max(1, multiprocessing.cpu_count() - 1)

    logger.info("Running %d tasks in parallel using {num_processes} processes", len(tasks))

    results = []
    try:
        with multiprocessing.Pool(processes=num_processes) as pool:
            # Use imap_unordered for better memory efficiency with large tasks
            for i, result in enumerate(pool.starmap(func, tasks, chunksize=chunk_size)):
                results.append(result)
                if i > 0 and i % 10 == 0:  # Log progress every 10 tasks
                    logger.info("Completed %d/%d tasks", i + 1, len(tasks))

    except Exception as e:
        logger.exception("Error in parallel execution")
        raise

    return results
