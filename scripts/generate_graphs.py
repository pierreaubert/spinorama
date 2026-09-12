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
import glob
import hashlib
import os
import random
import sys
import logging
import types
from typing import Any, Optional
from multiprocessing import Pool, cpu_count


def _reexec_project_venv() -> None:
    """Use the project virtualenv when this executable is run directly."""
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return
    if os.environ.get("SPINORAMA_VENV_REEXEC") == "1":
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = (
        os.path.join(project_root, ".venv", "bin", "python3"),
        os.path.join(project_root, ".venv", "Scripts", "python.exe"),
    )
    venv_python = next((path for path in candidates if os.path.isfile(path)), None)
    if venv_python is None:
        return

    environment = os.environ.copy()
    environment["SPINORAMA_VENV_REEXEC"] = "1"
    os.execve(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]], environment)


_reexec_project_venv()


def _ensure_repo_syspath() -> None:
    """Allow direct execution (``./scripts/generate_graphs.py``) without PYTHONPATH.

    The supported entry point (``update_website.sh``) exports a PYTHONPATH
    covering the repo root, but a bare run only has the script directory on
    ``sys.path`` and dies with ``ModuleNotFoundError: No module named
    'datas'``. Prepend the repo root (and scripts dir) when needed so the
    failure mode is a real build, not a confusing instant traceback.
    """
    try:
        import datas  # noqa: F401, PLC0415
        import spinorama  # noqa: F401, PLC0415
    except ImportError:
        # Same entries as update_website.sh's PYTHONPATH
        # (src:src/website:src/spinorama:.), scripts dir included for safety.
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for entry in ("scripts", "src", "src/website", "src/spinorama", "."):
            path = os.path.join(repo_root, entry) if entry != "." else repo_root
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)


_ensure_repo_syspath()

from generate_common import (
    args2level,
    cache_find_complete,
    cache_key,
    cache_update,
    cache_save_incremental,
    get_custom_logger,
    load_cache_manifest,
    save_cache_manifest,
)
from datas import speaker as metadata, Symmetry, Parameters
from datas.helpers import measurement2distance
from spinorama.load import parse_graphs_speaker, parse_eq_speaker
from spinorama.speaker import print_graphs, set_dist_speakers_root
from spinorama.plot import plot_params_default
from spinorama.misc import fingerprint_paths, sanitize_filename
import spinorama.constant_paths as cpaths
from spinorama.constant_paths import MEAN_MIN, MEAN_MAX
from spinorama.filters.peq import peq_preamp_gain, peq_spl
from spinorama.loaders.rew_eq import parse_eq_iir_rews

VERSION = "2.07"  # Updated version
GRAPH_CACHE_SCHEMA = "speaker-graph-cache-v4"
# Generator mechanism tag. Bump when the generator VALUE computation changes
# incompatibly; manifests carrying an older mechanism take the one-time
# date-gated bridge in _main_full_build instead of a full rebuild.
GENERATOR_MECHANISM = "code-v1"
# Bump this for a downstream rendering dependency that is not covered by the
# focused rendering-function source below.
GRAPH_OUTPUT_CACHE_VERSION = "graphs-v1"
ACTIVATE_TRACING: bool = True

# Set up logger
logger = logging.getLogger("spinorama")


def tracing(msg: str):
    """Debugging utility for tracing execution"""
    if ACTIVATE_TRACING:
        print(f"---- TRACING ---- {msg} ----")


def get_speaker_list(speakerpath: str) -> set[str]:
    """Return a list of speakers from data subdirectory"""
    speakers = []
    dirs = glob.glob(speakerpath + "/*")
    for current_dir in dirs:
        shortname = os.path.basename(current_dir)
        if os.path.isdir(current_dir) and shortname not in (
            "assets",
            "compare",
            "stats",
            "pictures",
            "tmp",
        ):
            speakers.append(shortname)
    return set(speakers)


def find_original_speaker_name(sanitized_name: str) -> str | None:
    """Find original speaker name from metadata given a sanitized filesystem name.

    Speakers with | in their name get sanitized to _ in directory names.
    This function does a reverse lookup to find the original metadata key.
    """
    for speaker_name in metadata.speakers_info:
        if sanitize_filename(speaker_name) == sanitized_name:
            return speaker_name
    return None


def _code_root() -> str:
    """Return the repository root of the running code (anchor for source hashing)."""
    import spinorama  # noqa: PLC0415

    return os.path.dirname(os.path.dirname(os.path.abspath(spinorama.__file__)))


def _rendering_code_files() -> list[str]:
    """List every Python module whose content can change graph bytes.

    This controller script is deliberately excluded: only the task/worker
    builders below shape rendered output (hashed as bytecode), so manifest
    IO, migration, pool plumbing, and logging edits must never invalidate
    every graph.
    """
    root = _code_root()
    pattern = os.path.join(root, "src", "spinorama", "**", "*.py")
    files = sorted(glob.glob(pattern, recursive=True))
    files.append(os.path.join(root, "datas", "helpers.py"))
    return [path for path in files if os.path.isfile(path)]


def _feed_code(digest, code: types.CodeType) -> None:
    """Feed a code object's logic (opcodes, names, constants) into a digest.

    Formatting, comments, and docstrings never reach bytecode, so cosmetic
    edits do not invalidate the cache; any logic change does. A different
    interpreter may compile different bytecode, which conservatively
    invalidates as well.
    """
    digest.update(code.co_code)
    digest.update(code.co_argcount.to_bytes(4, "little"))
    digest.update(b"\0".join(name.encode("utf-8") for name in code.co_names))
    digest.update(b"\0".join(name.encode("utf-8") for name in code.co_varnames))
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            _feed_code(digest, const)
        else:
            try:
                digest.update(repr(const).encode("utf-8"))
            except Exception:  # noqa: BLE001 -- exotic constants fall back to their type
                digest.update(type(const).__name__.encode("utf-8"))
        digest.update(b"\0")


def _controller_code_fingerprint() -> str:
    """Bytecode hash of the task/worker builders that shape graph bytes."""
    digest = hashlib.sha256()
    for func in (process_single_measurement, build_graph_tasks):
        _feed_code(digest, func.__code__)
    return digest.hexdigest()


def graph_generator_fingerprint(data_dir: str, width: int, height: int) -> str:
    """Fingerprint graph-output settings shared by every speaker.

    This combines the *contents* of every rendering module (loaders,
    derived-curve computation, EQ application, plot code) with the *bytecode*
    of the task/worker builders, so a rendering or parameter-logic change
    reliably invalidates the cache while a mere ``touch``, checkout, or
    controller-plumbing edit does not. Hashed names are relative to the code
    root so identical checkouts fingerprint identically. ``data_dir`` is kept
    for backward compatibility and is not hashed here; measurement bytes are
    covered per version by :func:`version_graph_fingerprint`.
    """
    del data_dir  # anchored on the code tree, not the data tree (see above)
    rendering = fingerprint_paths(
        _rendering_code_files(),
        version="rendering-modules-v1",
        relative_to=_code_root(),
        hash_contents=True,
    )
    config = "\0".join(
        (
            f"{width}x{height}",
            VERSION,
            GRAPH_OUTPUT_CACHE_VERSION,
            repr(metadata.origins_info),
        )
    )
    digest = hashlib.sha256()
    for part in (rendering, _controller_code_fingerprint(), config):
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return (
        f"{GRAPH_CACHE_SCHEMA}:{GRAPH_OUTPUT_CACHE_VERSION}:"
        f"{VERSION}:{GENERATOR_MECHANISM}:{width}x{height}:{digest.hexdigest()}"
    )


def speaker_graph_fingerprint(
    data_dir: str,
    sanitized_name: str,
    width: int,
    height: int,
    generator_fingerprint: str | None = None,
) -> str:
    """Fingerprint the inputs that can change one speaker's graph output."""
    data_root = os.path.abspath(data_dir)
    measurement_dir = os.path.join(data_root, "datas", "measurements", sanitized_name)
    eq_dir = os.path.join(data_root, "datas", "eq", sanitized_name)
    original_name = find_original_speaker_name(sanitized_name)
    speaker_metadata = (
        metadata.speakers_info.get(original_name) if original_name is not None else None
    )
    if generator_fingerprint is None:
        generator_fingerprint = graph_generator_fingerprint(data_dir, width, height)
    return fingerprint_paths(
        [measurement_dir, eq_dir],
        version=generator_fingerprint,
        extra=f"{sanitized_name!s}\0{speaker_metadata!r}",
        relative_to=data_root,
        hash_contents=True,
    )


# Measurement metadata fields that never reach the graph pipeline (reviews,
# publication dates, ...). Excluding them keeps display-only metadata edits
# from invalidating graph output.
_VERSION_META_IGNORED = frozenset({"review", "review_published"})


def version_input_paths(data_root: str, sanitized_name: str, mversion: str) -> tuple[str, str]:
    """Return the ``(version_dir, eq_file)`` inputs of one measurement version.

    Every loader reads its measurement files from
    ``datas/measurements/<speaker>/<mversion>/``, and the EQ stage reads only
    ``datas/eq/<speaker>/iir.txt``. Fingerprinting exactly these inputs (plus
    a focused metadata slice) means one changed version no longer reprocesses
    the speaker's other versions, and unrelated files in ``datas/eq`` do not
    invalidate anything.
    """
    version_dir = os.path.join(data_root, "datas", "measurements", sanitized_name, mversion)
    eq_file = os.path.join(data_root, "datas", "eq", sanitized_name, "iir.txt")
    return version_dir, eq_file


def version_graph_fingerprint(
    data_root: str,
    sanitized_name: str,
    mversion: str,
    measurement: Any,  # Measurement TypedDict at runtime; untyped .get() defaults flow in
    brand: str,
    shape: str,
    generator_fingerprint: str,
) -> str:
    """Fingerprint the inputs that can change one measurement version's graphs."""
    version_dir, eq_file = version_input_paths(data_root, sanitized_name, mversion)
    focused = {
        "brand": brand,
        "shape": shape,
        "measurement": {
            key: value for key, value in measurement.items() if key not in _VERSION_META_IGNORED
        },
    }
    return fingerprint_paths(
        [version_dir, eq_file],
        version=generator_fingerprint,
        extra=f"{sanitized_name!s}\0{mversion!s}\0{focused!r}",
        relative_to=data_root,
        hash_contents=True,
    )


def build_sanitized_map() -> dict[str, str]:
    """Map each sanitized filesystem name back to its original metadata name."""
    mapping: dict[str, str] = {}
    for original_name in metadata.speakers_info:
        sanitized = sanitize_filename(original_name)
        if sanitized in mapping and mapping[sanitized] != original_name:
            logger.warning(
                "Sanitized name collision: %s and %s both map to %s; keeping %s",
                mapping[sanitized],
                original_name,
                sanitized,
                mapping[sanitized],
            )
            continue
        mapping[sanitized] = original_name
    return mapping


def _directory_has_json(path: str) -> bool:
    """Check that a graph output directory holds at least one non-empty JSON file."""
    try:
        with os.scandir(path) as entries:
            return any(
                entry.is_file()
                and entry.name.endswith(".json")
                and entry.stat().st_size > 0
                for entry in entries
            )
    except OSError:
        return False


def version_output_fresh(
    dist_speakers_root: str, sanitized_name: str, origin: str, mversion: str, needs_eq: bool
) -> bool:
    """Check that a version's graph JSON output exists (mirrors ``build_filename``).

    ``print_graphs`` writes the base graphs to
    ``<root>/<speaker>/<origin>/<mversion>/`` and the EQ variant to
    ``<root>/<speaker>/<origin>/<mversion>_eq/``. A version is fresh only when
    the expected directories hold JSON output.
    """
    version_dir = os.path.join(
        dist_speakers_root, sanitized_name, origin.replace("Vendors-", ""), mversion
    )
    if not _directory_has_json(version_dir):
        return False
    return not needs_eq or _directory_has_json(f"{version_dir}_eq")


def speaker_cache_complete(speaker: str, cached_speaker: dict[str, Any]) -> bool:
    """Check that every graph-cache measurement and its EQ variant exist."""
    if not isinstance(cached_speaker, dict):
        return False
    for mversion, measurement in metadata.speakers_info[speaker]["measurements"].items():
        origin = measurement["origin"]
        cached_origin = cached_speaker.get(origin, {})
        if not isinstance(cached_origin, dict):
            return False
        if mversion not in cached_origin or f"{mversion}_eq" not in cached_origin:
            return False
    return True


# Worker task: everything the child process needs crosses the process boundary
# explicitly. Reading ``plot_params_default`` or metadata globals here would
# silently use default values under ``spawn`` (the macOS default), so width,
# height, brand, shape, and the output root travel in the tuple.
GraphTask = tuple[
    str,  # speaker (original metadata name)
    str,  # sanitized filesystem name
    str,  # origin
    str,  # mversion
    str,  # mformat
    str,  # brand
    str,  # shape
    Any,  # symmetry (str | None)
    Any,  # mparameters (dict | None)
    float,  # distance
    int,  # width
    int,  # height
    int,  # log_level
    str,  # data_dir
    str,  # dist_speakers_root
    bool,  # force
]


def process_single_measurement(
    task: GraphTask,
) -> tuple[bool, str, str, str, dict[str, Any], Optional[Exception]]:
    """Process a single measurement (worker function for parallel processing).

    Never returns ``None``: success yields ``(True, ...)`` with the parsed
    measurements, failure yields ``(False, ...)`` carrying the exception, so
    the parent can count errors and keep the cache manifest honest.
    """
    (
        speaker,
        sanitized_name,
        origin,
        mversion,
        mformat,
        brand,
        shape,
        msymmetry,
        mparameters,
        distance,
        width,
        height,
        log_level,
        data_dir,
        dist_speakers,
        force,
    ) = task

    try:
        set_dist_speakers_root(dist_speakers)

        parameters = {
            "mformat": mformat,
            "morigin": origin,
            "mversion": mversion,
            "msymmetry": msymmetry,
            "mparameters": mparameters,
            "distance": distance,
            "shape": shape,
            "width": int(width),
            "height": int(height),
        }

        # Process graphs (use sanitized name for filesystem paths)
        results = parse_graphs_speaker(
            speaker_path=f"{data_dir}/datas/measurements",
            speaker_brand=brand,
            speaker_name=sanitized_name,
            speaker_parameters=parameters,
            log_level=log_level,
        )

        # Process EQ (use sanitized name for filesystem paths)
        results_eq = parse_eq_speaker(
            speaker_path=f"{data_dir}/datas",
            speaker_name=sanitized_name,
            ref=results,
            speaker_parameters=parameters,
            log_level=log_level,
        )

        logger.debug("Generating graphs for %s / %s", speaker, mversion)

        # Generate graphs
        graphs = print_graphs(
            results,
            speaker,
            parameters,
            metadata.origins_info,
            force,
            log_level=log_level,
        )

        # Generate EQ graphs
        parameters_eq = parameters.copy()
        parameters_eq["mversion_key"] = mversion + "_eq"

        logger.debug("Generating EQ graphs for %s / %s", speaker, parameters_eq["mversion_key"])

        graphs_eq = print_graphs(
            results_eq,
            speaker,
            parameters_eq,
            metadata.origins_info,
            force,
            log_level=log_level,
        )
        payload = {"df": results, "eq": results_eq}
    except Exception as error:
        logger.exception(
            "Error processing speaker [%s] origin [%s] version [%s]", speaker, origin, mversion
        )
        return False, speaker, origin, mversion, {}, error
    else:
        return True, speaker, origin, mversion, payload, None


def _speaker_filter_match(original_name: str, sanitized_name: str, filter_name: str) -> bool:
    """Match a ``--speaker`` filter against the original or sanitized name."""
    return filter_name == original_name or sanitize_filename(filter_name) == sanitized_name


def build_graph_tasks(
    speakerlist: set[str],
    name_map: dict[str, str],
    filters: dict[str, str],
    log_level: int,
    data_root: str,
    dist_speakers_root: str,
    width: int,
    height: int,
    force: bool,
    skip_version=None,
) -> tuple[list[GraphTask], set[tuple[str, str]]]:
    """Build one worker task per measurement version passing the CLI filters.

    ``skip_version(speaker, sanitized, origin, mversion, measurement, brand,
    shape)`` returns True for versions the full-build cache already covers, so
    they are never parsed or rendered. Returns ``(tasks, queued)`` where
    ``queued`` holds the ``(speaker, mversion)`` keys that were queued, for
    failure bookkeeping.
    """
    tasks: list[GraphTask] = []
    queued: set[tuple[str, str]] = set()
    for sanitized_name in speakerlist:
        # Map sanitized filesystem name back to original metadata name
        original_name = name_map.get(sanitized_name)
        if original_name is None:
            logger.error("Metadata error: no metadata entry for %s", sanitized_name)
            continue

        # Check if speaker filter matches
        if "speaker" in filters and not _speaker_filter_match(
            original_name, sanitized_name, filters["speaker"]
        ):
            logger.debug("skipping %s (doesn't match filter %s)", sanitized_name, filters["speaker"])
            continue

        speaker_info = metadata.speakers_info.get(original_name)
        if speaker_info is None:
            logger.error("Metadata error: %s", original_name)
            continue

        brand = speaker_info.get("brand", "")
        shape = speaker_info.get("shape", "")
        for mversion, measurement in speaker_info.get("measurements", {}).items():
            if "mversion" in filters and not (
                mversion == filters["mversion"] or mversion == "{}_eq".format(filters["mversion"])
            ):
                logger.debug("skipping %s/%s", original_name, mversion)
                continue

            mformat = measurement.get("format")
            if "format" in filters and mformat != filters["format"]:
                logger.debug("skipping %s/%s/%s", original_name, mformat, mversion)
                continue

            morigin = measurement.get("origin")
            if "origin" in filters and morigin != filters["origin"]:
                logger.debug("skipping %s/%s/%s/%s", original_name, morigin, mformat, mversion)
                continue

            if "brand" in filters and speaker_info.get("brand") != filters["brand"]:
                logger.debug("skipping %s (brand %s filtered)", original_name, brand)
                continue

            if skip_version is not None and skip_version(
                original_name, sanitized_name, morigin, mversion, measurement, brand, shape
            ):
                continue

            distance = measurement2distance(original_name, measurement)
            tasks.append(
                (
                    original_name,
                    sanitized_name,
                    morigin,
                    mversion,
                    mformat,
                    brand,
                    shape,
                    measurement.get("symmetry", None),
                    measurement.get("parameters", None),
                    distance,
                    width,
                    height,
                    log_level,
                    data_root,
                    dist_speakers_root,
                    force,
                )
            )
            queued.add((original_name, mversion))

    return tasks, queued


def _accumulate_pool_results(
    results, total_tasks: int
) -> tuple[dict[str, Any], int, int, bool]:
    """Fold worker answers into the cache frame, surviving Ctrl+C.

    Returns ``(data_frame, succeeded, errors, interrupted)``. A
    KeyboardInterrupt mid-iteration keeps every result received so far so the
    caller can persist partial progress instead of losing the whole build.
    """
    data_frame: dict[str, Any] = {}
    success_count = 0
    error_count = 0
    interrupted = False
    try:
        for i, answer in enumerate(results):
            success, speaker, origin, mversion, result, error = answer
            if success:
                if speaker not in data_frame:
                    data_frame[speaker] = {}

                if origin not in data_frame[speaker]:
                    data_frame[speaker][origin] = {}

                data_frame[speaker][origin][mversion] = result["df"]
                data_frame[speaker][origin][f"{mversion}_eq"] = result["eq"]
                success_count += 1
            else:
                logger.error(
                    "Failed to process %s/%s/%s: %s", speaker, origin, mversion, str(error)
                )
                error_count += 1

            # Log progress
            if (i + 1) % 10 == 0 or (i + 1) == total_tasks:
                logger.info(
                    "Processed %d/%d measurements (%d errors)", i + 1, total_tasks, error_count
                )
    except KeyboardInterrupt:
        interrupted = True
        logger.warning(
            "Interrupted by user; keeping %d/%d completed results",
            success_count + error_count,
            total_tasks,
        )
    return data_frame, success_count, error_count, interrupted


def process_measurements_parallel(
    tasks: list[GraphTask],
    log_level: int,
    num_processes: int,
) -> tuple[dict[str, Any], bool]:
    """Process measurement tasks in parallel using multiprocessing.

    Returns ``(data_frame, interrupted)``; exiting the pool context
    terminates the workers, and the caller persists whatever completed.
    """
    del log_level  # carried inside each task for the worker's own logger setup
    if not tasks:
        logger.info("No measurements to process")
        return {}, False

    num_process = max(1, min(num_processes, len(tasks)))
    logger.info("Processing %d measurements using %d processes", len(tasks), num_process)

    # Process tasks in parallel
    with Pool(processes=num_process) as pool:
        results = pool.imap_unordered(process_single_measurement, tasks, chunksize=1)
        data_frame, success_count, error_count, interrupted = _accumulate_pool_results(
            results, len(tasks)
        )

    logger.info(
        "Completed processing: %d succeeded, %d failed%s",
        success_count,
        error_count,
        " (interrupted)" if interrupted else "",
    )
    return data_frame, interrupted


def _succeeded_versions(df_new: dict[str, Any]) -> set[tuple[str, str]]:
    """Return the ``(speaker, mversion)`` keys present in worker results."""
    succeeded: set[tuple[str, str]] = set()
    for speaker, origins in df_new.items():
        if not isinstance(origins, dict):
            continue
        for measurements in origins.values():
            if not isinstance(measurements, dict):
                continue
            for key in measurements:
                if not key.endswith("_eq"):
                    succeeded.add((speaker, key))
    return succeeded


def _tree_newest_mtime_ns(paths: list[str]) -> int | None:
    """Return the newest mtime (ns) under ``paths``, or ``None`` when empty."""
    newest: int | None = None
    for raw_path in paths:
        if os.path.isdir(raw_path):
            for dirpath, _, filenames in os.walk(raw_path):
                for filename in filenames:
                    try:
                        mtime = os.stat(os.path.join(dirpath, filename)).st_mtime_ns
                    except OSError:
                        continue
                    if newest is None or mtime > newest:
                        newest = mtime
        elif os.path.isfile(raw_path):
            try:
                mtime = os.stat(raw_path).st_mtime_ns
            except OSError:
                continue
            if newest is None or mtime > newest:
                newest = mtime
    return newest


def _metadata_source_files() -> list[str]:
    """Return the metadata module files consumed by the graph pipeline.

    Only the speaker database (``datas/speaker*.py``), the package init
    (types), and ``datas/helpers.py`` (distances, valid frequency ranges)
    feed graph output; headphone metadata and validation helpers do not.
    """
    package_dir = os.path.dirname(os.path.abspath(metadata.__file__))
    files = sorted(glob.glob(os.path.join(package_dir, "speaker*.py")))
    for extra in ("__init__.py", "helpers.py"):
        candidate = os.path.join(package_dir, extra)
        if os.path.isfile(candidate):
            files.append(candidate)
    return sorted(set(files))


def _inputs_unchanged_since(manifest_mtime_ns: int | None) -> bool:
    """Check that no rendering/metadata code changed since the manifest write.

    Version fingerprints already prove data and metadata *values* are
    current; this covers the remaining input dimension (rendering and
    metadata *code*) for one-time cache adoptions across generator
    mechanisms, where stored fingerprints are incomparable.
    """
    if manifest_mtime_ns is None:
        return False
    newest = _tree_newest_mtime_ns(_rendering_code_files() + _metadata_source_files())
    return newest is not None and newest <= manifest_mtime_ns


def _version_cache_entry(
    data_root: str,
    sanitized_name: str,
    mversion: str,
    measurement: Any,  # Measurement TypedDict at runtime; untyped .get() defaults flow in
    brand: str,
    shape: str,
    generator: str,
) -> tuple[str, bool]:
    """Compute a version fingerprint and whether its EQ output is required."""
    fingerprint = version_graph_fingerprint(
        data_root, sanitized_name, mversion, measurement, brand, shape, generator
    )
    _, eq_file = version_input_paths(data_root, sanitized_name, mversion)
    return fingerprint, os.path.isfile(eq_file)


def _refresh_manifest_entries(
    manifest_path: str,
    data_root: str,
    name_map: dict[str, str],
    width: int,
    height: int,
    df_new: dict[str, Any],
) -> None:
    """Record freshly processed versions in an existing v4 manifest.

    Gives ``--update-cache`` a job on filtered builds: the HDF5 entries are
    updated by ``cache_update``, and this updates the matching manifest
    entries so the next full build can reuse them. Unknown-schema manifests
    are left alone; the next full build migrates them.
    """
    manifest = load_cache_manifest(manifest_path)
    if manifest.get("schema") != GRAPH_CACHE_SCHEMA:
        logger.warning("Not updating cache manifest with schema %s", manifest.get("schema"))
        return
    generator = graph_generator_fingerprint(data_root, width, height)
    manifest["generator"] = generator
    manifest_speakers = manifest.setdefault("speakers", {})
    updated = 0
    for speaker, mversion in _succeeded_versions(df_new):
        sanitized_name = next(
            (san for san, orig in name_map.items() if orig == speaker), sanitize_filename(speaker)
        )
        speaker_info = metadata.speakers_info.get(speaker, {})
        measurement = speaker_info.get("measurements", {}).get(mversion)
        if measurement is None:
            continue
        fingerprint, _ = _version_cache_entry(
            data_root,
            sanitized_name,
            mversion,
            measurement,
            speaker_info.get("brand", ""),
            speaker_info.get("shape", ""),
            generator,
        )
        entry = manifest_speakers.setdefault(speaker, {})
        entry["sanitized"] = sanitized_name
        entry.setdefault("versions", {})[mversion] = {
            "fingerprint": fingerprint,
            "complete": True,
        }
        updated += 1
    save_cache_manifest(manifest, manifest_path)
    logger.info("Updated cache manifest for %d versions", updated)


def main(log_level, args):
    """Main function to process speakers and generate graphs"""
    # Set global variables
    data_dir = args.data_dir
    force = args.force

    # Anchor every derived location on the data directory. The cache, the
    # manifest, and the graph output previously resolved against the current
    # working directory, so the same build from another directory (or with a
    # ``--data-dir`` pointing elsewhere) silently used a cold cache and
    # recomputed everything.
    data_root = os.path.abspath(data_dir)
    cache_dir = os.path.join(data_root, ".cache")
    manifest_path = os.path.join(cache_dir, "manifest.json")
    dist_speakers_root = os.path.join(data_root, "dist", "speakers")
    set_dist_speakers_root(dist_speakers_root)

    # Get speaker list
    speakerlist = get_speaker_list(os.path.join(data_root, "datas", "measurements"))

    # Handle smoke test
    if args.smoke_test is not None:
        if args.smoke_test == "random":
            speakerlist = set(random.sample(list(speakerlist), min(15, len(speakerlist))))
        else:
            speakerlist = {
                "Genelec 8030C",
                "KEF LS50",
                "KRK Systems Classic 5",
                "Verdant Audio Bambusa MG 1",
            }
        logger.info("Running smoke test with speakers: %s", speakerlist)

    # Update plot parameters if specified
    if args.width is not None:
        plot_params_default["width"] = int(args.width)
    if args.height is not None:
        plot_params_default["height"] = int(args.height)

    # Set up filters
    filters = {}
    for ifilter_key in ("speaker", "origin", "mversion", "brand", "format"):
        value = getattr(args, ifilter_key, None)
        if value is not None:
            filters[ifilter_key] = value

    # num_procs
    num_processes = cpu_count() - 1
    param_processes = num_processes
    if args.processes is not None:
        param_processes = int(args.processes)
    num_processes = max(1, min(param_processes, num_processes))

    width = int(plot_params_default["width"])
    height = int(plot_params_default["height"])
    name_map = build_sanitized_map()

    # A full build reuses complete measurement versions whose inputs have not
    # changed. Filtered and smoke-test builds retain the historical behavior:
    # they only update the requested subset and never prune the full cache.
    if not filters and args.smoke_test is None:
        return _main_full_build(
            log_level,
            args,
            data_root,
            cache_dir,
            manifest_path,
            dist_speakers_root,
            speakerlist,
            name_map,
            width,
            height,
            force,
            num_processes,
        )

    tasks, _ = build_graph_tasks(
        speakerlist,
        name_map,
        filters,
        log_level,
        data_root,
        dist_speakers_root,
        width,
        height,
        force,
    )
    df_new, interrupted = process_measurements_parallel(tasks, log_level, num_processes)
    cache_update(df_new, filters, log_level, cache_dir=cache_dir)
    if args.update_cache and df_new:
        _refresh_manifest_entries(manifest_path, data_root, name_map, width, height, df_new)

    if interrupted:
        logger.warning("Graph generation interrupted; partial results were saved")
        return 130
    logger.info("Graph generation completed successfully")
    return 0


def _decide_stale_versions(
    current_speakers: dict[str, str],
    manifest_speakers: dict[str, Any],
    generator: str,
    generator_changed: bool,
    data_root: str,
    dist_speakers_root: str,
    cache_dir: str,
    force: bool,
    migrating_v3: bool,
    manifest_mtime_ns: int | None,
    verified_versions: set[tuple[str, str]] | None = None,
    legacy_bridge: bool = False,
    legacy_generator: str | None = None,
) -> tuple[
    dict[tuple[str, str], str],
    set[tuple[str, str]],
    dict[tuple[str, str], bool],
    dict[str, int],
    list[str],
]:
    """Decide per measurement version whether it must be reprocessed.

    Returns ``(fingerprints, stale, old_complete, invalidations,
    stale_examples)``. A version is reused only when its fingerprint matches
    the manifest, the manifest marks it complete, its graph JSON output
    exists, and its HDF5 shard file exists. ``verified_versions`` carries the
    one-time v3 verification result for unverified v3 manifests; ``None``
    disables that adoption path. ``legacy_bridge``/``legacy_generator``
    re-prove v4 entries stored under a previous generator mechanism, using
    the stored generator as salt (version fingerprints chain it, so stored
    entries can only be re-derived, never compared, across mechanisms).
    """
    fingerprints: dict[tuple[str, str], str] = {}
    needs_eq: dict[tuple[str, str], bool] = {}
    for speaker, sanitized_name in current_speakers.items():
        speaker_info = metadata.speakers_info.get(speaker, {})
        brand = speaker_info.get("brand", "")
        shape = speaker_info.get("shape", "")
        for mversion, measurement in speaker_info.get("measurements", {}).items():
            fingerprint, with_eq = _version_cache_entry(
                data_root, sanitized_name, mversion, measurement, brand, shape, generator
            )
            fingerprints[(speaker, mversion)] = fingerprint
            needs_eq[(speaker, mversion)] = with_eq

    stale: set[tuple[str, str]] = set()
    old_complete: dict[tuple[str, str], bool] = {}
    invalidations = {
        "missing_manifest": 0,
        "fingerprint": 0,
        "incomplete": 0,
        "output": 0,
        "shard": 0,
    }
    stale_examples: list[str] = []
    for (speaker, mversion), fingerprint in fingerprints.items():
        sanitized_name = current_speakers[speaker]
        speaker_info = metadata.speakers_info.get(speaker, {})
        measurement = speaker_info.get("measurements", {}).get(mversion, {})
        origin = measurement.get("origin", "")
        brand = speaker_info.get("brand", "")
        shape = speaker_info.get("shape", "")
        reason: str | None = None
        old_entry_versions: dict[str, Any] = {}
        # Entries are read even on a generator mismatch: every branch below
        # revalidates them (fingerprint compare, completeness, outputs,
        # shards, or the one-time legacy bridge), so reading alone trusts
        # nothing.
        if isinstance(manifest_speakers.get(speaker), dict) and isinstance(
            manifest_speakers[speaker].get("versions"), dict
        ):
            old_entry_versions = manifest_speakers[speaker]["versions"]
        old_version = old_entry_versions.get(mversion)
        if not isinstance(old_version, dict):
            old_version = None

        if force:
            reason = "fingerprint"
        elif old_version is None:
            v3_entry = isinstance(manifest_speakers.get(speaker), dict)
            adoptable = migrating_v3 or (
                v3_entry
                and verified_versions is not None
                and (speaker, mversion) in verified_versions
            )
            if (
                v3_entry
                and adoptable
                and _adopt_v3_version(
                    data_root,
                    sanitized_name,
                    mversion,
                    manifest_mtime_ns,
                    dist_speakers_root,
                    origin,
                    needs_eq[(speaker, mversion)],
                    cache_dir,
                    speaker,
                )
            ):
                old_complete[(speaker, mversion)] = True
            elif generator_changed:
                reason = "fingerprint"
            else:
                reason = "missing_manifest"
        elif (
            legacy_bridge
            and legacy_generator is not None
            and old_version.get("complete", False)
            and _version_cache_entry(
                data_root, sanitized_name, mversion, measurement, brand, shape,
                legacy_generator,
            )[0]
            == old_version.get("fingerprint")
            and version_output_fresh(
                dist_speakers_root,
                sanitized_name,
                origin,
                mversion,
                needs_eq[(speaker, mversion)],
            )
            and os.path.isfile(os.path.join(cache_dir, f"{cache_key(speaker)}.h5"))
        ):
            # One-time bridge: the stored generator predates component
            # fingerprints, so the entry is re-proven with the stored
            # generator as salt. Content, outputs, shards, and code dates
            # all prove this version current.
            old_complete[(speaker, mversion)] = True
        elif generator_changed or old_version.get("fingerprint") != fingerprint:
            reason = "fingerprint"
        elif not old_version.get("complete", False):
            reason = "incomplete"
        elif not version_output_fresh(
            dist_speakers_root,
            sanitized_name,
            origin,
            mversion,
            needs_eq[(speaker, mversion)],
        ):
            reason = "output"
        elif not os.path.isfile(os.path.join(cache_dir, f"{cache_key(speaker)}.h5")):
            reason = "shard"
        else:
            old_complete[(speaker, mversion)] = True

        if reason is not None:
            stale.add((speaker, mversion))
            invalidations[reason] += 1
            if len(stale_examples) < 20:
                stale_examples.append(f"{speaker}/{mversion} ({reason})")

    return fingerprints, stale, old_complete, invalidations, stale_examples


def _main_full_build(
    log_level: int,
    args,
    data_root: str,
    cache_dir: str,
    manifest_path: str,
    dist_speakers_root: str,
    speakerlist: set[str],
    name_map: dict[str, str],
    width: int,
    height: int,
    force: bool,
    num_processes: int,
) -> int:
    """Run an unfiltered build, reprocessing only stale measurement versions."""
    old_manifest = load_cache_manifest(manifest_path)
    current_speakers: dict[str, str] = {}
    for sanitized_name in speakerlist:
        original_name = name_map.get(sanitized_name)
        if original_name is not None:
            current_speakers[original_name] = sanitized_name
        else:
            logger.error("Metadata error: no metadata entry for %s", sanitized_name)

    manifest_speakers = old_manifest.get("speakers", {})
    if not isinstance(manifest_speakers, dict):
        manifest_speakers = {}
    generator = graph_generator_fingerprint(data_root, width, height)
    # Manifests without a matching generator string cannot prove their outputs
    # match the current rendering code, so every version goes stale.
    generator_changed = not (
        old_manifest.get("schema") == GRAPH_CACHE_SCHEMA
        and old_manifest.get("generator") == generator
    )

    # A v3 manifest can seed the v4 per-version entries without reprocessing,
    # provided no input changed since it was written. With a verified cache
    # the manifest flag vouches for completeness; otherwise the HDF5 entries
    # are verified once (streamed shard by shard, unlike the old full-load).
    # The v3 generator string is incomparable with the v4 one, so adoption
    # additionally assumes the upgrade did not alter rendering bytes (true
    # for this change: only cache plumbing moved). Any doubt (missing cache
    # entries, touched inputs, missing outputs or shards) keeps the version
    # stale; pass --force to rebuild from scratch regardless.
    old_v3 = (
        not force
        and old_manifest.get("schema") == "speaker-graph-cache-v3"
        and bool(manifest_speakers)
    )
    migrating_v3 = old_v3 and old_manifest.get("cache_verified", False)
    verifying_v3 = old_v3 and not old_manifest.get("cache_verified", False)

    # One-time bridge for v4 manifests written before component fingerprints
    # existed: their generator is a bare content digest from the older
    # mechanism, incomparable with the new strings, but versions whose inputs
    # prove current by content, with rendering/metadata code proven untouched
    # by date, are still adoptable. Custom --width/--height always rebuild,
    # since legacy digests may predate the requested dimensions.
    stored_generator = old_manifest.get("generator")
    legacy_candidate = (
        not force
        and args.width is None
        and args.height is None
        and old_manifest.get("schema") == GRAPH_CACHE_SCHEMA
        and isinstance(stored_generator, str)
        and GENERATOR_MECHANISM not in stored_generator
        and bool(manifest_speakers)
    )

    manifest_mtime_ns: int | None = None
    if migrating_v3 or verifying_v3 or legacy_candidate:
        if migrating_v3:
            logger.warning(
                "Adopting verified v3 cache entries without reprocessing; "
                "pass --force to rebuild from scratch"
            )
        if legacy_candidate:
            logger.warning(
                "Previous manifest predates component fingerprints; adopting versions "
                "whose inputs prove current by content and date, pass --force to rebuild"
            )
        try:
            manifest_mtime_ns = os.stat(manifest_path).st_mtime_ns
        except OSError:
            manifest_mtime_ns = None
        if not _inputs_unchanged_since(manifest_mtime_ns):
            migrating_v3 = False
            verifying_v3 = False
            legacy_candidate = False
            logger.info("Code changed since previous manifest; revalidating versions")
    legacy_bridge = legacy_candidate

    verified_versions: set[tuple[str, str]] | None = None
    if verifying_v3 and manifest_mtime_ns is not None and not args.explain_cache:
        logger.warning("Verifying v3 HDF5 entries once to adopt complete versions")
        wanted: dict[str, dict[str, str]] = {}
        for speaker in current_speakers:
            speaker_info = metadata.speakers_info.get(speaker, {})
            versions = {
                mversion: measurement.get("origin", "")
                for mversion, measurement in speaker_info.get("measurements", {}).items()
            }
            if versions:
                wanted[speaker] = versions
        verified_versions = cache_find_complete(cache_dir, wanted)
        logger.info(
            "v3 verification: %d of %d versions complete in cache",
            len(verified_versions),
            sum(len(versions) for versions in wanted.values()),
        )
    elif verifying_v3 and args.explain_cache:
        logger.info(
            "Skipping one-time v3 verification in explain mode; "
            "unverified versions count as stale"
        )

    fingerprints, stale, old_complete, invalidations, stale_examples = _decide_stale_versions(
        current_speakers,
        manifest_speakers,
        generator,
        generator_changed,
        data_root,
        dist_speakers_root,
        cache_dir,
        force,
        migrating_v3,
        manifest_mtime_ns,
        verified_versions,
        legacy_bridge,
        stored_generator if legacy_bridge else None,
    )

    logger.info(
        "Incremental graph cache: reusing %d versions, processing %d "
        "(manifest missing: %d, fingerprint changed: %d, incomplete: %d, "
        "output missing: %d, shard missing: %d)",
        len(fingerprints) - len(stale),
        len(stale),
        invalidations["missing_manifest"],
        invalidations["fingerprint"],
        invalidations["incomplete"],
        invalidations["output"],
        invalidations["shard"],
    )
    for example in stale_examples:
        logger.info("Stale version: %s", example)

    if args.explain_cache:
        return 0

    if not stale:
        _save_full_manifest(
            manifest_path, generator, current_speakers, fingerprints,
            {key: True for key in fingerprints},
        )
        logger.info("Graph generation cache is up to date")
        return 0

    tasks, queued = build_graph_tasks(
        speakerlist,
        name_map,
        {},
        log_level,
        data_root,
        dist_speakers_root,
        width,
        height,
        force,
        skip_version=lambda sp, _san, _o, mv, _m, _b, _sh: (sp, mv) not in stale,
    )
    df_new, interrupted = process_measurements_parallel(tasks, log_level, num_processes)

    succeeded = _succeeded_versions(df_new)
    failed = queued - succeeded
    if failed:
        logger.warning(
            "Graph generation failed for %d versions; they will be retried next run",
            len(failed),
        )

    removed_speakers = set(manifest_speakers) - set(current_speakers)
    cache_save_incremental(
        df_new, set(current_speakers), removed_speakers, cache_dir=cache_dir, prune=True
    )

    complete = dict(old_complete)
    for key in fingerprints:
        if key in succeeded:
            complete[key] = True
        elif key in queued:
            complete[key] = False
        else:
            complete[key] = old_complete.get(key, False)
    _save_full_manifest(manifest_path, generator, current_speakers, fingerprints, complete)

    if interrupted:
        logger.warning("Graph generation interrupted; partial results were saved")
        return 130
    logger.info("Graph generation completed successfully")
    return 0


def _adopt_v3_version(
    data_root: str,
    sanitized_name: str,
    mversion: str,
    manifest_mtime_ns: int | None,
    dist_speakers_root: str,
    origin: str,
    with_eq: bool,
    cache_dir: str,
    speaker: str,
) -> bool:
    """Decide whether a v3-verified version can seed the v4 manifest as fresh."""
    if manifest_mtime_ns is None or not origin:
        return False
    version_dir, eq_file = version_input_paths(data_root, sanitized_name, mversion)
    if not os.path.isdir(version_dir):
        return False
    inputs = [version_dir]
    if os.path.isfile(eq_file):
        inputs.append(eq_file)
    newest = _tree_newest_mtime_ns(inputs)
    if newest is not None and newest > manifest_mtime_ns:
        return False
    if not version_output_fresh(dist_speakers_root, sanitized_name, origin, mversion, with_eq):
        return False
    return os.path.isfile(os.path.join(cache_dir, f"{cache_key(speaker)}.h5"))


def _save_full_manifest(
    manifest_path: str,
    generator: str,
    current_speakers: dict[str, str],
    fingerprints: dict[tuple[str, str], str],
    complete: dict[tuple[str, str], bool],
) -> None:
    """Write the v4 manifest with per-version fingerprints and completeness."""
    versions_by_speaker: dict[str, dict[str, Any]] = {}
    for (speaker, mversion), fingerprint in fingerprints.items():
        versions_by_speaker.setdefault(speaker, {})[mversion] = {
            "fingerprint": fingerprint,
            "complete": bool(complete.get((speaker, mversion), False)),
        }
    speakers: dict[str, Any] = {}
    for speaker, sanitized_name in current_speakers.items():
        versions = versions_by_speaker.get(speaker, {})
        speakers[speaker] = {"sanitized": sanitized_name, "versions": versions}
    cache_verified = all(
        entry["complete"] for speaker_entry in speakers.values() for entry in speaker_entry["versions"].values()
    )
    save_cache_manifest(
        {
            "schema": GRAPH_CACHE_SCHEMA,
            "cache_verified": cache_verified,
            "generator": generator,
            "speakers": speakers,
        },
        manifest_path,
    )


def generate_headphone_graphs(data_dir: str, force: bool):
    """Generate plotly JSON graphs for headphone measurements.

    Headphone graphs are simpler than speaker spinorama — just frequency
    response curves loaded from CSV files.
    """
    import json as json_module
    import numpy as np

    hp_measurements_dir = os.path.join(data_dir, "datas", "headphones")
    hp_targets_dir = os.path.join(data_dir, "datas", "headphone_targets")
    hp_dist_dir = os.path.join(data_dir, "dist", "headphones")

    if not os.path.isdir(hp_measurements_dir):
        logger.info("No headphone measurements directory, skipping")
        return

    try:
        from datas.headphones import headphones_info
    except ImportError:
        logger.info("No headphone metadata found, skipping graph generation")
        return

    from load_headphone_csv import parse_headphone_csv, average_headphone_channels

    def load_csv_curve(filepath):
        """Load a frequency,spl CSV file, averaging L+R channels if present."""
        df = parse_headphone_csv(filepath)
        if df is None:
            return np.array([]), np.array([])
        df_avg = average_headphone_channels(df)
        freq = np.asarray(df_avg["Freq"], dtype=float)
        spl = np.asarray(df_avg["dB"], dtype=float)
        return freq, spl

    def mean_in_band(freq, spl, fmin, fmax):
        """Compute mean SPL inside [fmin, fmax] Hz."""
        mask = (freq >= fmin) & (freq <= fmax)
        return float(np.mean(spl[mask])) if np.any(mask) else 0.0

    def make_plotly_json(traces, title, xaxis_title="Frequency (Hz)", yaxis_title="SPL (dB)"):
        """Create a plotly JSON spec."""
        return {
            "data": traces,
            "layout": {
                "title": {"text": title},
                "xaxis": {
                    "title": {"text": xaxis_title},
                    "type": "log",
                    "range": [np.log10(20), np.log10(20000)],
                },
                "yaxis": {
                    "title": {"text": yaxis_title},
                },
                "showlegend": True,
            },
        }

    # Load target curves
    targets = {}
    for tname, tfile in (
        ("harman_overear_2019", "harman_overear_2019.csv"),
        ("harman_inear_2019", "harman_inear_2019.csv"),
    ):
        tpath = os.path.join(hp_targets_dir, tfile)
        if os.path.isfile(tpath):
            freq, spl = load_csv_curve(tpath)
            targets[tname] = (freq, spl)

    target_for_shape = {
        "over-ear": "harman_overear_2019",
        "on-ear": "harman_overear_2019",
        "in-ear": "harman_inear_2019",
        "earbud": "harman_inear_2019",
    }

    count = 0
    for hp_name, hp_info in headphones_info.items():
        if hp_info.get("skip", False):
            continue

        brand = hp_info["brand"]
        model = hp_info["model"]
        shape = hp_info.get("shape", "over-ear")
        default_m = hp_info.get("default_measurement", "asr")

        hp_m_dir = os.path.join(hp_measurements_dir, hp_name)
        if not os.path.isdir(hp_m_dir):
            logger.debug("No measurement dir for %s", hp_name)
            continue

        # Find frequency response CSV (inside the measurement origin subdir)
        fr_file = None
        for origin_dir in (default_m, "asr"):
            for candidate in ("frequency_response.csv", "freq_response.csv", "fr.csv"):
                cpath = os.path.join(hp_m_dir, origin_dir, candidate)
                if os.path.isfile(cpath):
                    fr_file = cpath
                    break
            if fr_file is not None:
                break
        if fr_file is None:
            logger.debug("No frequency response CSV for %s", hp_name)
            continue

        # Determine origin
        origin = hp_info["measurements"].get(default_m, {}).get("origin", "ASR")

        # Output directory
        out_dir = os.path.join(hp_dist_dir, hp_name, origin, default_m)
        os.makedirs(out_dir, exist_ok=True)

        # Check if we need to regenerate
        fr_json = os.path.join(out_dir, "Frequency Response.json")
        if (
            not force
            and os.path.isfile(fr_json)
            and os.path.getmtime(fr_json) > os.path.getmtime(fr_file)
        ):
            logger.debug("Graphs up to date for %s", hp_name)
            continue

        freq, spl = load_csv_curve(fr_file)
        if len(freq) == 0:
            logger.warning("Empty frequency response for %s", hp_name)
            continue

        # Graph 1: Frequency Response
        traces_fr = [
            {
                "x": freq.tolist(),
                "y": spl.tolist(),
                "type": "scatter",
                "mode": "lines",
                "name": "Frequency Response",
                "line": {"color": "#1f77b4"},
            }
        ]
        spec_fr = make_plotly_json(traces_fr, f"{brand} {model} - Frequency Response")
        with open(fr_json, "w") as f:
            json_module.dump(spec_fr, f)

        # Graph 2: Frequency Response Compensated (with target)
        target_key = target_for_shape.get(shape, "harman_overear_2019")
        if target_key in targets:
            t_freq, t_spl = targets[target_key]
            # Interpolate target to measurement frequency grid
            t_interp = np.interp(freq, t_freq, t_spl)

            # Normalize measurement and target over [MEAN_MIN, MEAN_MAX] Hz
            mean_spl = mean_in_band(freq, spl, MEAN_MIN, MEAN_MAX)
            mean_target = mean_in_band(freq, t_interp, MEAN_MIN, MEAN_MAX)
            spl_norm = spl - mean_spl
            target_norm = t_interp - mean_target

            traces_comp = [
                {
                    "x": freq.tolist(),
                    "y": spl_norm.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Measurement",
                    "line": {"color": "#1f77b4"},
                },
                {
                    "x": freq.tolist(),
                    "y": target_norm.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": f"Harman Target ({shape})",
                    "line": {"color": "#ff7f0e", "dash": "dash"},
                },
            ]
            spec_comp = make_plotly_json(traces_comp, f"{brand} {model} - vs Harman Target")
            comp_json = os.path.join(out_dir, "Frequency Response Compensated.json")
            with open(comp_json, "w") as f:
                json_module.dump(spec_comp, f)

            # Graph 3: Target Deviation
            deviation = spl_norm - target_norm
            mean_deviation = mean_in_band(freq, deviation, MEAN_MIN, MEAN_MAX)
            deviation = deviation - mean_deviation
            traces_dev = [
                {
                    "x": freq.tolist(),
                    "y": deviation.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Deviation from Target",
                    "line": {"color": "#d62728"},
                },
                {
                    "x": [20, 20000],
                    "y": [0, 0],
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Zero",
                    "line": {"color": "#888888", "dash": "dot"},
                    "showlegend": False,
                },
            ]
            spec_dev = make_plotly_json(traces_dev, f"{brand} {model} - Target Deviation")
            dev_json = os.path.join(out_dir, "Target Deviation.json")
            with open(dev_json, "w") as f:
                json_module.dump(spec_dev, f)

        # Generate EQ graphs if corresponding EQ files exist
        eq_dir = os.path.join(cpaths.CPATH_DATAS_HEADPHONE_EQ, hp_name)
        if target_key in targets and os.path.isdir(eq_dir):
            t_freq, t_spl = targets[target_key]
            t_interp = np.interp(freq, t_freq, t_spl)
            mean_spl = mean_in_band(freq, spl, MEAN_MIN, MEAN_MAX)
            mean_target = mean_in_band(freq, t_interp, MEAN_MIN, MEAN_MAX)
            spl_norm = spl - mean_spl
            target_norm = t_interp - mean_target
            for eq_key, filename, display in (
                ("autoeq_score", "iir-autoeq-score", "Harman Score EQ (IIR)"),
                ("autoeq_flat", "iir-autoeq-flat", "Flat Target EQ (IIR)"),
            ):
                eq_file = os.path.join(eq_dir, "{}.txt".format(filename))
                if not os.path.isfile(eq_file):
                    continue
                iir = parse_eq_iir_rews(eq_file, 48000)
                peq = [(w, b) for w, b in iir if w != 0.0]
                if not peq:
                    continue
                eq_out_dir = "{}_eq_{}".format(out_dir, eq_key)
                os.makedirs(eq_out_dir, exist_ok=True)
                fr_eq_json = os.path.join(eq_out_dir, "Frequency Response.json")
                if (
                    not force
                    and os.path.isfile(fr_eq_json)
                    and os.path.getmtime(fr_eq_json) > os.path.getmtime(eq_file)
                ):
                    logger.debug("EQ graphs up to date for %s %s", hp_name, eq_key)
                    continue
                preamp = peq_preamp_gain(peq)
                eq_response = np.array(peq_spl(freq, peq)) + preamp
                spl_eq = spl + eq_response
                mean_spl_eq = mean_in_band(freq, spl_eq, MEAN_MIN, MEAN_MAX)
                spl_eq_norm = spl_eq - mean_spl_eq
                traces_fr_eq = [
                    {
                        "x": freq.tolist(),
                        "y": spl_norm.tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "Frequency Response",
                        "line": {"color": "#1f77b4"},
                    },
                    {
                        "x": freq.tolist(),
                        "y": target_norm.tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": f"Harman Target ({shape})",
                        "line": {"color": "#ff7f0e", "dash": "dash"},
                    },
                    {
                        "x": freq.tolist(),
                        "y": spl_eq_norm.tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "With EQ",
                        "line": {"color": "#2ca02c"},
                    },
                ]
                spec_fr_eq = make_plotly_json(
                    traces_fr_eq,
                    f"{brand} {model} - Frequency Response ({display})",
                )
                with open(fr_eq_json, "w") as f:
                    json_module.dump(spec_fr_eq, f)
                deviation = spl_norm - target_norm
                mean_deviation = mean_in_band(freq, deviation, MEAN_MIN, MEAN_MAX)
                deviation = deviation - mean_deviation
                deviation_eq = spl_eq_norm - target_norm
                mean_deviation_eq = mean_in_band(freq, deviation_eq, MEAN_MIN, MEAN_MAX)
                deviation_eq = deviation_eq - mean_deviation_eq
                traces_dev_eq = [
                    {
                        "x": freq.tolist(),
                        "y": deviation.tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "Deviation",
                        "line": {"color": "#d62728"},
                    },
                    {
                        "x": freq.tolist(),
                        "y": deviation_eq.tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "With EQ",
                        "line": {"color": "#2ca02c"},
                    },
                    {
                        "x": [20, 20000],
                        "y": [0, 0],
                        "type": "scatter",
                        "mode": "lines",
                        "name": "Zero",
                        "line": {"color": "#888888", "dash": "dot"},
                        "showlegend": False,
                    },
                ]
                spec_dev_eq = make_plotly_json(
                    traces_dev_eq,
                    f"{brand} {model} - Target Deviation ({display})",
                )
                dev_eq_json = os.path.join(eq_out_dir, "Target Deviation.json")
                with open(dev_eq_json, "w") as f:
                    json_module.dump(spec_dev_eq, f)
                logger.info("Generated EQ graphs for %s %s", hp_name, eq_key)

        count += 1
        logger.info("Generated graphs for %s", hp_name)

    logger.info("Generated headphone graphs for %d headphones", count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate spinorama graphs from measurement data.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--version", action="version", version=f"./scripts/generate_graphs.py v{VERSION}"
    )
    parser.add_argument("--width", type=int, help="Width size in pixel for graphs")
    parser.add_argument("--height", type=int, help="Height size in pixel for graphs")
    parser.add_argument("--force", action="store_true", help="Force regeneration of all graphs")
    parser.add_argument(
        "--smoke-test",
        choices=["random", "default"],
        metavar="ALGO",
        help="Run a few speakers only (choices: random, default)",
    )
    parser.add_argument(
        "--type",
        metavar="EXT",
        help="Output graph file type (e.g., png, svg) - currently informational",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set log level (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument("--origin", help="Filter by origin")
    parser.add_argument("--speaker", help="Filter by speaker")
    parser.add_argument("--mversion", help="Filter by measurement version")
    parser.add_argument("--brand", help="Filter by brand")
    parser.add_argument(
        "--format",
        metavar="FORMAT",
        help="Filter by measurement format (e.g. klippel, princeton, webplotdigitizer)",
    )
    parser.add_argument(
        "--data-dir", default=".", help="Directory where data is stored (default: .)"
    )
    parser.add_argument(
        "--update-cache",
        action="store_true",
        help="Update the cache manifest for filtered builds "
        "(full builds reuse unchanged versions automatically)",
    )
    parser.add_argument(
        "--explain-cache",
        action="store_true",
        help="Report full-build cache invalidations without generating graphs",
    )
    parser.add_argument(
        "--processes", type=int, help="Number of processes to use (default: CPU count - 1)"
    )
    parser.add_argument("--headphones", action="store_true", help="Generate headphone graphs only")

    args = parser.parse_args()

    # Set up logging
    LEVEL = args2level(args)
    logger = get_custom_logger(level=LEVEL, duplicate=True)

    if args.headphones:
        generate_headphone_graphs(data_dir=args.data_dir, force=args.force)
        sys.exit(0)

    # Run main function
    sys.exit(main(log_level=LEVEL, args=args))
