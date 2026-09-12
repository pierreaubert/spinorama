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
import json
import logging
import multiprocessing
import os
import pathlib
import re
import sys
import resource
from typing import Callable, Any
import warnings

import flammkuchen as fl
import numpy as _np

import tables


# flammkuchen 1.0.3 references ``np.unicode_``/``np.string_``, removed in
# NumPy 2.0 (``requirements.txt`` allows NumPy >1.26.4, so 2.x resolves).
# Without these aliases every HDF5 cache write crashes and no build ever
# persists its cache. They were exact aliases of ``np.str_``/``np.bytes_``,
# so restoring them is behavior-preserving; only applied when missing.
for _alias, _target in (("unicode_", "str_"), ("string_", "bytes_")):
    if not hasattr(_np, _alias):
        setattr(_np, _alias, getattr(_np, _target))
del _alias, _target

# Set file descriptor limit
try:
    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    desired_limit = 1000000
    new_soft_limit = min(desired_limit, hard_limit)
    if new_soft_limit > soft_limit:
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft_limit, hard_limit))
except Exception as e:
    print(f"Warning: Could not set file descriptor limit: {e}", file=sys.stderr)

import datas.speaker as metadata

import spinorama.constant_paths as cpaths
from spinorama.constant_paths import flags_ADD_HASH

CACHE_DIR = ".cache"
GRAPH_CACHE_MANIFEST = f"{CACHE_DIR}/manifest.json"


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
        cpaths.CPATH_DIST_HEADPHONES,
        cpaths.CPATH_BUILD_EQ,
        cpaths.CPATH_BUILD_WEBSITE,
        cpaths.CPATH_BUILD_MAKO,
    ):
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)


def cache_key(name: str) -> str:
    # 256 partitions, use hashlib for stable hash
    key = md5(name.replace('"', "").encode("utf-8"), usedforsecurity=False).hexdigest()
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


def _resolve_cache_dir(cache_dir: str | None) -> str:
    """Return the HDF5 cache directory, anchored by the caller when given.

    Historically every cache path was resolved against the current working
    directory, so running the same build from another directory (or with a
    ``--data-dir`` pointing elsewhere) silently used a different, cold cache.
    Callers now pass the data-directory-anchored location explicitly.
    """
    return cache_dir if cache_dir is not None else CACHE_DIR


def _shard_name(cache_path: str) -> str:
    """Return the shard key (``<key>.h5`` basename without suffix)."""
    return os.path.splitext(os.path.basename(cache_path))[0]


def cache_save_key(key: str, data, cache_dir: str | None = None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", tables.NaturalNameWarning)
        # print('{} {}'.format(key, data.keys()))
        cache_name = "{}/{}.h5".format(_resolve_cache_dir(cache_dir), key)
        # print(cache_name)
        fl.save(path=cache_name, data=data)


def load_cache_manifest(path: str = GRAPH_CACHE_MANIFEST) -> dict:
    """Load the incremental graph cache manifest, tolerating old/missing data."""
    try:
        with open(path, "r", encoding="utf-8") as manifest_fd:
            manifest = json.load(manifest_fd)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return manifest if isinstance(manifest, dict) else {}


def save_cache_manifest(manifest: dict, path: str = GRAPH_CACHE_MANIFEST) -> None:
    """Atomically save the incremental graph cache manifest."""
    manifest_path = pathlib.Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = manifest_path.with_name(f".{manifest_path.name}.tmp")
    temporary_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary_path, manifest_path)


def cache_save(df_all: dict, prune: bool = False, cache_dir: str | None = None):
    resolved = _resolve_cache_dir(cache_dir)
    pathlib.Path(resolved).mkdir(parents=True, exist_ok=True)
    df_hashed = cache_hash(df_all)
    for key, data in df_hashed.items():
        cache_save_key(key, data, cache_dir=resolved)
    if prune:
        expected = {f"{key}.h5" for key in df_hashed}
        for cache_path in pathlib.Path(resolved).glob("*.h5"):
            if cache_path.name not in expected:
                cache_path.unlink()
    print("(saved {} speakers)".format(len(df_all)))


def _load_shard_file(cachepath: str):
    """Load one HDF5 shard, quarantining it when it is unreadable."""
    if not os.path.isfile(cachepath):
        return None
    try:
        return fl.load(path=cachepath)
    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        TypeError,
        EOFError,
        tables.HDF5ExtError,
    ) as error:
        if isinstance(error, FileNotFoundError):
            return None
        logger = logging.getLogger("spinorama")
        try:
            quarantined = _quarantine_corrupt_cache(cachepath)
        except OSError:
            logger.exception("Invalid cache file %s could not be quarantined", cachepath)
            return None
        logger.warning(
            "Ignoring invalid cache file %s (%s: %s); moved to %s",
            cachepath,
            type(error).__name__,
            error,
            quarantined,
        )
        return None
    except Exception:
        logger = logging.getLogger("spinorama")
        logger.exception("Error loading cache file %s", cachepath)
        return None


def cache_save_incremental(
    df_new: dict,
    current_speakers: set[str],
    removed_speakers: set[str],
    cache_dir: str | None = None,
    *,
    prune: bool = False,
) -> dict[str, int]:
    """Persist only the HDF5 shards affected by this build.

    A full build previously rewrote every ``*.h5`` shard even when a single
    speaker changed. Here only shards holding new/updated speakers, or
    speakers dropped from the metadata, are loaded, merged, and rewritten;
    untouched shards are never read. With ``prune=True``, shard files that
    hold no current speaker are deleted.
    """
    resolved = _resolve_cache_dir(cache_dir)
    pathlib.Path(resolved).mkdir(parents=True, exist_ok=True)

    new_by_shard: dict[str, dict] = {}
    for speaker, data in df_new.items():
        new_by_shard.setdefault(cache_key(speaker), {})[speaker] = data
    removed_by_shard: dict[str, set[str]] = {}
    for speaker in removed_speakers:
        removed_by_shard.setdefault(cache_key(speaker), set()).add(speaker)

    stats = {"shards_rewritten": 0, "shards_deleted": 0, "speakers_removed": 0}
    for key in new_by_shard.keys() | removed_by_shard.keys():
        shard_path = os.path.join(resolved, f"{key}.h5")
        existing = _load_shard_file(shard_path)
        if not isinstance(existing, dict):
            existing = {}
        for speaker in removed_by_shard.get(key, ()):
            if existing.pop(speaker, None) is not None:
                stats["speakers_removed"] += 1
        existing.update(new_by_shard.get(key, {}))
        if existing:
            cache_save_key(key, existing, cache_dir=resolved)
            stats["shards_rewritten"] += 1
        elif os.path.isfile(shard_path):
            os.unlink(shard_path)
            stats["shards_deleted"] += 1

    if prune:
        live_keys = {cache_key(speaker) for speaker in current_speakers}
        for cache_path in pathlib.Path(resolved).glob("*.h5"):
            if _shard_name(str(cache_path)) not in live_keys:
                cache_path.unlink()
                stats["shards_deleted"] += 1
    print(
        "(incrementally saved {} speakers: {} shards rewritten, {} deleted)".format(
            len(df_new), stats["shards_rewritten"], stats["shards_deleted"]
        )
    )
    return stats


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


def _select_cache_files(cache_dir: str, speakers: set[str] | None) -> list[str]:
    """List shard files, restricted to the shards holding ``speakers`` when given."""
    cache_files = glob(os.path.join(cache_dir, "*.h5"))
    if speakers is None:
        return sorted(cache_files)
    wanted = {cache_key(speaker) for speaker in speakers}
    return sorted(path for path in cache_files if _shard_name(path) in wanted)


def cache_load_seq(filters, smoke_test, cache_dir: str | None = None, speakers=None):
    df_all = defaultdict()
    resolved = _resolve_cache_dir(cache_dir)
    wanted = set(speakers) if speakers is not None else None
    cache_files = _select_cache_files(resolved, wanted)
    if len(cache_files) == 0:
        cache_files = glob("../{}/*.h5".format(CACHE_DIR))
    if len(cache_files) == 0:
        print("Cannot find cache directory or files! Did you run ./scripts/generate_graphs.py ?")
        return df_all
    count = 0
    print("Found {} cache files".format(len(cache_files)))
    logging.debug("found %d cache files", len(cache_files))
    for cache in cache_files:
        speaker_name = filters.get("speaker_name")
        if speaker_name is not None and _shard_name(cache) != cache_key(speaker_name):
            logging.debug("skipping %s key=%s", speaker_name, cache_key(speaker_name))
            continue
        df_read = fl.load(path=cache)
        print("Reading file {} found {} entries".format(cache, len(df_read) if df_read else 0))
        if not isinstance(df_read, dict):
            continue
        for speaker, data in df_read.items():
            if speaker in df_all:
                print("Error in cache: {} is already in keys".format(speaker))
                continue
            if is_filtered(speaker, filters):
                # print('Skipping filtered {} {}'.format(speaker, speaker_name))
                continue
            print("Found data for {}".format(speaker))
            df_all[speaker] = data
            count += 1
        if smoke_test and count > 10:
            break

    print("(loaded {} speakers)".format(len(df_all)))
    return df_all


def _quarantine_corrupt_cache(cachepath: str) -> pathlib.Path | None:
    """Move an unreadable derived cache shard aside for later inspection."""
    source = pathlib.Path(cachepath)
    if not source.is_file():
        return None

    target = source.with_name(f"{source.name}.corrupt")
    suffix = 1
    while target.exists():
        target = source.with_name(f"{source.name}.corrupt.{suffix}")
        suffix += 1
    source.replace(target)
    return target


def _cache_fetch_worker(args):
    """Worker function for loading cache files in parallel"""
    cachepath, level = args
    logger = logging.getLogger("spinorama")
    logger.setLevel(level)
    logger.debug("Level of debug is %d", level)
    try:
        return fl.load(path=cachepath)
    except (KeyError, ValueError, TypeError, EOFError, tables.HDF5ExtError) as error:
        try:
            quarantined = _quarantine_corrupt_cache(cachepath)
        except OSError:
            logger.exception("Invalid cache file %s could not be quarantined", cachepath)
            return None
        logger.warning(
            "Ignoring invalid cache file %s (%s: %s); moved to %s",
            cachepath,
            type(error).__name__,
            error,
            quarantined,
        )
        return None
    except Exception:
        logger.exception("Error loading cache file %s", cachepath)
        return None


def cache_load_distributed(filters, smoke_test, level, cache_dir: str | None = None, speakers=None):
    """Load cache files in parallel using multiprocessing.

    Uses a single worker pool for the whole file list; previously a new pool
    was created per 16-file chunk. When ``speakers`` is given, only the shards
    that can hold those speakers are read, so a small incremental build no
    longer deserializes the entire cache. When there are no more files than
    workers, the files are read inline: spawning a full pool (each child
    re-imports the scientific stack) to read a handful of shards is slower
    than reading them directly.
    """
    resolved = _resolve_cache_dir(cache_dir)
    wanted = set(speakers) if speakers is not None else None
    cache_files = _select_cache_files(resolved, wanted)

    # Determine number of processes to use (leave one CPU free)
    num_processes = max(1, multiprocessing.cpu_count() - 1)

    # Filter cache files based on speaker_name if provided
    if filters.get("speaker_name") is not None:
        speaker_key = cache_key(filters.get("speaker_name"))
        cache_files = [f for f in cache_files if _shard_name(f) == speaker_key]
        num_processes = 1

    df_all = {}
    count = 0

    if len(cache_files) <= num_processes:
        print(f"(processing {len(cache_files)} files sequentially)")
        results = [_cache_fetch_worker((cache, level)) for cache in cache_files]
    else:
        print(f"(processing {len(cache_files)} files in parallel x{num_processes})")
        # A single pool for all files; results stream back in file order.
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.map(_cache_fetch_worker, [(cache, level) for cache in cache_files])

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

    return df_all


def cache_load(filters, smoke_test, level, cache_dir: str | None = None, speakers=None):
    """Load cache using parallel processing if no specific speaker is requested"""
    if filters.get("speaker_name") is None:
        try:
            return cache_load_distributed(filters, smoke_test, level, cache_dir, speakers)
        except Exception as e:
            print(f"Parallel cache loading failed, falling back to sequential: {e}")

    # Fall back to sequential loading
    return cache_load_seq(filters, smoke_test, cache_dir, speakers)


def cache_find_complete(
    cache_dir: str | None, wanted: dict[str, dict[str, str]]
) -> set[tuple[str, str]]:
    """Return the ``(speaker, mversion)`` keys fully present in the HDF5 shards.

    Streams one shard at a time instead of deserializing the whole cache, for
    one-time verification of a previous build's output. ``wanted`` maps each
    speaker to its ``{mversion: origin}`` versions; a version counts as
    complete when both its plain and ``_eq`` entries exist under its origin,
    mirroring ``speaker_cache_complete`` in ``generate_graphs``.
    """
    resolved = _resolve_cache_dir(cache_dir)
    found: set[tuple[str, str]] = set()
    if not wanted or not os.path.isdir(resolved):
        return found
    wanted_shards: dict[str, list[str]] = {}
    for speaker in wanted:
        wanted_shards.setdefault(cache_key(speaker), []).append(speaker)
    for key, speakers in sorted(wanted_shards.items()):
        shard_path = os.path.join(resolved, f"{key}.h5")
        data = _load_shard_file(shard_path)
        if not isinstance(data, dict):
            continue
        for speaker in speakers:
            cached_speaker = data.get(speaker)
            if not isinstance(cached_speaker, dict):
                continue
            for mversion, origin in wanted[speaker].items():
                cached_origin = cached_speaker.get(origin)
                if (
                    isinstance(cached_origin, dict)
                    and mversion in cached_origin
                    and f"{mversion}_eq" in cached_origin
                ):
                    found.add((speaker, mversion))
    return found


def _speaker_matches_filter(new_speaker: str, filters: dict | None) -> bool:
    """Check a cache speaker name against the ``--speaker`` filter, if any.

    The filter value may be the original metadata name or its sanitized
    filesystem form; previously any build filtered by origin/version/brand
    compared against ``""`` and silently discarded every result.
    """
    if not filters or "speaker" not in filters or filters["speaker"] is None:
        return True
    wanted = filters["speaker"]
    if new_speaker == wanted:
        return True
    try:
        from spinorama.misc import sanitize_filename  # noqa: PLC0415
    except ImportError:
        return False
    return sanitize_filename(wanted) == sanitize_filename(new_speaker)


def cache_update(df_new, filters, level, cache_dir: str | None = None):
    resolved = _resolve_cache_dir(cache_dir)
    if not os.path.exists(resolved) or len(df_new) == 0:
        return

    logger = logging.getLogger("spinorama")
    print("Updating cache ", end=" ", flush=True)
    count = 0
    for new_speaker, new_datas in df_new.items():
        if not _speaker_matches_filter(new_speaker, filters):
            continue
        df_old = cache_load(
            filters={"speaker_name": new_speaker},
            smoke_test=False,
            level=level,
            cache_dir=resolved,
        )
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
        cache_save_key(cache_key(new_speaker), df_old, cache_dir=resolved)
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
