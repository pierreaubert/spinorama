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
generate_dotli.py — Blockchain-optimized static site generator for spinorama.

Produces a minimal, self-contained deployment:
  1 HTML + 1 JS + 1 index.json + ~500 compressed speaker data chunks

Output directory: dist-dotli/
"""

import argparse
import base64
import brotli
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from glob import glob

from generate_common import (
    args2level,
    find_metadata_file,
    get_custom_logger,
    sort_metadata_per_date,
)

import spinorama.constant_paths as cpaths
from spinorama.misc import sanitize_filename

DIST_DOTLI = "./dist-dotli"
DIST_DOTLI_CHUNKS = f"{DIST_DOTLI}/chunks"
DIST_DOTLI_MANIFEST = f"{DIST_DOTLI}/manifest.json"
SITEPROD = "https://www.spinorama.org"

DATA_CHUNK_MAX_UNCOMPRESSED_BYTES = 2_000_000
PICTURES_PER_CHUNK = 50

# Graph types to include in chunks (core subset — no SPL H/V full, no 3D)
GRAPH_TYPES = [
    "CEA2034",
    "CEA2034 Normalized",
    "On Axis",
    "Estimated In-Room Response",
    "Estimated In-Room Response Normalized",
    "Early Reflections",
    "Horizontal Reflections",
    "Vertical Reflections",
    "SPL Horizontal Contour",
    "SPL Vertical Contour",
    "SPL Horizontal Contour Normalized",
    "SPL Vertical Contour Normalized",
    "SPL Horizontal Radar",
    "SPL Vertical Radar",
]

TARGET_NUM_CHUNKS = 500


def load_manifest(logger):
    """Load an existing manifest from dist-dotli/manifest.json, or return None."""
    if not os.path.exists(DIST_DOTLI_MANIFEST):
        logger.info("No existing manifest found at %s", DIST_DOTLI_MANIFEST)
        return None
    with open(DIST_DOTLI_MANIFEST, "r") as f:
        manifest = json.load(f)
    if manifest.get("version") != 2:
        logger.warning("Manifest version mismatch, ignoring existing manifest")
        return None
    logger.info(
        "Loaded manifest: %d data chunks, %d pic chunks",
        len(manifest.get("data_chunks", {})),
        len(manifest.get("pic_chunks", {})),
    )
    return manifest


def save_manifest(manifest, logger):
    """Write manifest to disk."""
    with open(DIST_DOTLI_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Saved manifest to %s", DIST_DOTLI_MANIFEST)


def compute_initial_manifest(speaker_data_list, target_chunks, logger):
    """First build: use bin_pack_speakers for initial assignment, convert to manifest."""
    chunks = bin_pack_speakers(speaker_data_list, target_chunks)
    logger.info("Initial bin-packing produced %d chunks", len(chunks))

    manifest = {
        "version": 2,
        "data_chunk_max_uncompressed_bytes": DATA_CHUNK_MAX_UNCOMPRESSED_BYTES,
        "pic_chunk_max_count": PICTURES_PER_CHUNK,
        "data_chunks": {},
        "pic_chunks": {},
    }

    for chunk_idx, chunk in enumerate(chunks):
        speakers = [name for name, _ in chunk]
        sealed = chunk_idx < len(chunks) - 1
        manifest["data_chunks"][str(chunk_idx)] = {
            "sealed": sealed,
            "speakers": speakers,
        }

    return manifest


def compute_initial_pic_manifest(meta, manifest, logger):
    """First build: assign pictures to chunks in manifest."""
    pic_by_name = {}
    for pic_path in sorted(glob(f"{cpaths.CPATH_DIST_PICTURES}/*.webp")):
        speaker_name = os.path.basename(pic_path).replace(".webp", "")
        if speaker_name in meta:
            pic_by_name[speaker_name] = pic_path

    # Use insertion order from data chunks to determine picture assignment
    all_speakers_ordered = []
    data_chunks = manifest["data_chunks"]
    for idx in sorted(data_chunks.keys(), key=int):
        for name in data_chunks[idx]["speakers"]:
            if name in pic_by_name:
                all_speakers_ordered.append(name)

    # Also add any speakers with pictures not yet in data chunks
    data_speakers = {n for c in data_chunks.values() for n in c["speakers"]}
    for name in pic_by_name:
        if name not in data_speakers:
            all_speakers_ordered.append(name)

    pic_chunks = {}
    for i in range(0, len(all_speakers_ordered), PICTURES_PER_CHUNK):
        chunk_idx = i // PICTURES_PER_CHUNK
        batch = all_speakers_ordered[i : i + PICTURES_PER_CHUNK]
        sealed = (i + PICTURES_PER_CHUNK) < len(all_speakers_ordered)
        pic_chunks[str(chunk_idx)] = {
            "sealed": sealed,
            "speakers": batch,
        }

    manifest["pic_chunks"] = pic_chunks
    logger.info("Initial pic manifest: %d chunks for %d pictures", len(pic_chunks), len(all_speakers_ordered))


def assign_new_speakers(manifest, new_speakers, speaker_data_map, logger):
    """Append new speakers to the active (unsealed) data chunk.

    Returns set of dirty chunk indices that need rewriting.
    """
    if not new_speakers:
        return set()

    data_chunks = manifest["data_chunks"]
    dirty = set()

    # Find the active (unsealed) chunk — highest index
    if data_chunks:
        active_idx = max(int(k) for k in data_chunks.keys())
        active_chunk = data_chunks[str(active_idx)]
        if active_chunk["sealed"]:
            # All sealed — create a new one
            active_idx += 1
            data_chunks[str(active_idx)] = {"sealed": False, "speakers": []}
            active_chunk = data_chunks[str(active_idx)]
    else:
        active_idx = 0
        data_chunks["0"] = {"sealed": False, "speakers": []}
        active_chunk = data_chunks["0"]

    max_bytes = manifest["data_chunk_max_uncompressed_bytes"]

    for speaker_name in new_speakers:
        # Estimate current chunk uncompressed size
        chunk_size = _estimate_chunk_size(active_chunk["speakers"], speaker_data_map)
        speaker_size = _estimate_speaker_size(speaker_name, speaker_data_map)

        if chunk_size + speaker_size > max_bytes and len(active_chunk["speakers"]) > 0:
            # Seal current, create next
            active_chunk["sealed"] = True
            active_idx += 1
            data_chunks[str(active_idx)] = {"sealed": False, "speakers": []}
            active_chunk = data_chunks[str(active_idx)]
            logger.info("Data chunk %d sealed, created chunk %d", active_idx - 1, active_idx)

        active_chunk["speakers"].append(speaker_name)
        dirty.add(active_idx)

    logger.info("Assigned %d new speakers, %d dirty data chunks", len(new_speakers), len(dirty))
    return dirty


def assign_new_pic_speakers(manifest, new_pic_speakers, logger):
    """Append new speakers to the active (unsealed) picture chunk.

    Returns set of dirty pic chunk indices.
    """
    if not new_pic_speakers:
        return set()

    pic_chunks = manifest["pic_chunks"]
    dirty = set()

    if pic_chunks:
        active_idx = max(int(k) for k in pic_chunks.keys())
        active_chunk = pic_chunks[str(active_idx)]
        if active_chunk["sealed"]:
            active_idx += 1
            pic_chunks[str(active_idx)] = {"sealed": False, "speakers": []}
            active_chunk = pic_chunks[str(active_idx)]
    else:
        active_idx = 0
        pic_chunks["0"] = {"sealed": False, "speakers": []}
        active_chunk = pic_chunks["0"]

    max_count = manifest["pic_chunk_max_count"]

    for speaker_name in new_pic_speakers:
        if len(active_chunk["speakers"]) >= max_count:
            active_chunk["sealed"] = True
            active_idx += 1
            pic_chunks[str(active_idx)] = {"sealed": False, "speakers": []}
            active_chunk = pic_chunks[str(active_idx)]
            logger.info("Pic chunk %d sealed, created chunk %d", active_idx - 1, active_idx)

        active_chunk["speakers"].append(speaker_name)
        dirty.add(active_idx)

    logger.info("Assigned %d new pic speakers, %d dirty pic chunks", len(new_pic_speakers), len(dirty))
    return dirty


def _estimate_chunk_size(speaker_names, speaker_data_map):
    """Estimate uncompressed JSON size of a chunk's speakers."""
    total = 0
    for name in speaker_names:
        total += _estimate_speaker_size(name, speaker_data_map)
    return total


def _estimate_speaker_size(speaker_name, speaker_data_map):
    """Estimate uncompressed JSON size for a single speaker."""
    data = speaker_data_map.get(speaker_name)
    if data is None:
        return 0
    return len(json.dumps(data, separators=(",", ":")).encode("utf-8"))


def load_metadata(logger):
    """Load full metadata + eqdata, same as generate_html.py."""
    metadata_json_filename, eqdata_json_filename = find_metadata_file()

    for radical, json_check in (
        ("metadata", metadata_json_filename),
        ("eqdata", eqdata_json_filename),
    ):
        if json_check is None:
            logger.error("Cannot find %s, run generate_meta.py first!", radical)
            sys.exit(1)

    with open(metadata_json_filename, "r") as f:
        meta = json.load(f)

    with open(eqdata_json_filename, "r") as f:
        meta_eqs = json.load(f)
        for k, v in meta_eqs.items():
            if "eqs" in v:
                meta[k]["eqs"] = v["eqs"]

    return meta


def get_thumbnail_base64(speaker_name, max_size_kb=5):
    """Get base64 encoded thumbnail for a speaker. Returns None if not found."""
    for ext in ("webp", "jpg", "png"):
        pic_path = f"{cpaths.CPATH_DIST_PICTURES}/{sanitize_filename(speaker_name)}.{ext}"
        if os.path.exists(pic_path):
            file_size = os.path.getsize(pic_path)
            if file_size <= max_size_kb * 1024:
                with open(pic_path, "rb") as f:
                    data = f.read()
                mime = {"webp": "image/webp", "jpg": "image/jpeg", "png": "image/png"}[ext]
                return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
            # File too large — skip embedding
            return None
    return None


def extract_speaker_index_entry(speaker_name, speaker_data, chunk_idx, chunk_pos):
    """Extract all searchable/filterable fields for one speaker into the index."""
    brand = speaker_data.get("brand", "")
    model = speaker_data.get("model", "")
    dm = speaker_data.get("default_measurement", "")
    measurements = speaker_data.get("measurements", {})

    entry = {
        "n": speaker_name,
        "b": brand,
        "m": model,
        "t": speaker_data.get("type", ""),
        "s": speaker_data.get("shape", ""),
        "a": speaker_data.get("amount", "pair"),
        "dm": dm,
        "ms": list(measurements.keys()),
        "c": chunk_idx,
        "ci": chunk_pos,
    }

    # Price
    price_str = speaker_data.get("price", "")
    try:
        entry["p"] = float(price_str)
    except (ValueError, TypeError):
        entry["p"] = None

    # Default measurement data
    if dm and dm in measurements:
        meas = measurements[dm]
        entry["o"] = meas.get("origin", "")
        entry["q"] = meas.get("quality", "unknown")
        entry["dt"] = meas.get("review_published", "")

        # Pref rating
        pref = meas.get("pref_rating", {})
        if pref:
            entry["sc"] = pref.get("pref_score")
            entry["scw"] = pref.get("pref_score_wsub")
            entry["sm"] = pref.get("sm_pred_in_room")
            entry["fl_nbd_on"] = pref.get("nbd_on_axis")
            entry["fl_nbd_pir"] = pref.get("nbd_pred_in_room")
            entry["lfx"] = pref.get("lfx_hz")

        # Scaled pref rating
        scaled = meas.get("scaled_pref_rating", {})
        if scaled:
            entry["scs"] = scaled.get("scaled_pref_score")
            entry["lfxs"] = scaled.get("scaled_lfx_hz")
            entry["fls"] = scaled.get("scaled_flatness")
            entry["sms"] = scaled.get("scaled_sm_pred_in_room")

        # Estimates
        estimates = meas.get("estimates", {})
        if estimates:
            entry["fl"] = estimates.get("ref_band")
            entry["f3"] = estimates.get("ref_3dB")
            entry["f6"] = estimates.get("ref_6dB")

        # Specifications
        specs = meas.get("specifications", {})
        if specs:
            entry["sn"] = specs.get("sensitivity")
            entry["imp"] = specs.get("impedance")
            spl = specs.get("SPL", {})
            if spl:
                entry["spl"] = spl.get("peak") or spl.get("max") or spl.get("continuous")
            size = specs.get("size", {})
            if size:
                h = size.get("height")
                w = size.get("width")
                d = size.get("depth")
                if h or w or d:
                    entry["sz"] = [h, w, d]
            wt = specs.get("weight")
            if wt:
                entry["wt"] = wt

    # Nearest speakers
    nearest = speaker_data.get("nearest")
    if nearest:
        entry["near"] = nearest[:5]

    # Has EQ?
    entry["hasEq"] = "eqs" in speaker_data and len(speaker_data.get("eqs", {})) > 0

    return entry


def strip_plotly_graph(graph_data):
    """Strip template and layout from Plotly graph, keeping only data traces."""
    if not isinstance(graph_data, dict):
        return graph_data
    return {"data": graph_data.get("data", [])}


def collect_speaker_graph_data(speaker_name, speaker_data):
    """Collect all graph JSON data for a speaker from dist/speakers/."""
    speaker_dir = f"{cpaths.CPATH_DIST_SPEAKERS}/{sanitize_filename(speaker_name)}"
    if not os.path.isdir(speaker_dir):
        return None

    result = {"name": speaker_name, "measurements": {}}

    measurements = speaker_data.get("measurements", {})
    for version_key, meas_info in measurements.items():
        origin = meas_info.get("origin", "")
        # Determine the origin directory
        if origin in ("ASR", "Princeton", "ErinsAudioCorner", "Misc"):
            origin_dir = origin
        else:
            origin_dir = speaker_data.get("brand", "")

        version_dir = f"{speaker_dir}/{origin_dir}/{version_key}"
        if not os.path.isdir(version_dir):
            continue

        graphs = {}
        for graph_type in GRAPH_TYPES:
            graph_file = f"{version_dir}/{graph_type}.json"
            if os.path.exists(graph_file):
                try:
                    with open(graph_file, "r") as f:
                        graph_json = json.load(f)
                    graphs[graph_type] = strip_plotly_graph(graph_json)
                except (json.JSONDecodeError, OSError):
                    pass

        if graphs:
            result["measurements"][version_key] = {"graphs": graphs}

        # Also include _eq variant if it exists
        eq_version_dir = f"{speaker_dir}/{origin_dir}/{version_key}_eq"
        if os.path.isdir(eq_version_dir):
            eq_graphs = {}
            for graph_type in GRAPH_TYPES:
                graph_file = f"{eq_version_dir}/{graph_type}.json"
                if os.path.exists(graph_file):
                    try:
                        with open(graph_file, "r") as f:
                            graph_json = json.load(f)
                        eq_graphs[graph_type] = strip_plotly_graph(graph_json)
                    except (json.JSONDecodeError, OSError):
                        pass

            if eq_graphs:
                result["measurements"][f"{version_key}_eq"] = {"graphs": eq_graphs}

    # EQ filters from eqdata
    if "eqs" in speaker_data:
        result["filters"] = speaker_data["eqs"]

    # eq_compare.json
    eq_compare_file = f"{speaker_dir}/eq_compare.json"
    if os.path.exists(eq_compare_file):
        try:
            with open(eq_compare_file, "r") as f:
                result["eq_compare"] = strip_plotly_graph(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    # spider.json
    spider_file = f"{speaker_dir}/spider.json"
    if os.path.exists(spider_file):
        try:
            with open(spider_file, "r") as f:
                result["spider"] = strip_plotly_graph(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    if not result["measurements"]:
        return None

    return result


def extract_layout_presets(logger):
    """Extract one layout preset per graph type from the first speaker found."""
    presets = {}
    speakers = glob(f"{cpaths.CPATH_DIST_SPEAKERS}/*")
    for speaker_dir in speakers:
        if not os.path.isdir(speaker_dir):
            continue
        speaker_name = os.path.basename(speaker_dir)
        if speaker_name in ("score", "assets", "stats", "compare", "logos", "pictures"):
            continue

        # Find any measurement directory with graphs
        for origin_dir in glob(f"{speaker_dir}/*"):
            if not os.path.isdir(origin_dir):
                continue
            for version_dir in glob(f"{origin_dir}/*"):
                if not os.path.isdir(version_dir):
                    continue
                for graph_type in GRAPH_TYPES:
                    if graph_type in presets:
                        continue
                    graph_file = f"{version_dir}/{graph_type}.json"
                    if os.path.exists(graph_file):
                        try:
                            with open(graph_file, "r") as f:
                                graph_json = json.load(f)
                            layout = graph_json.get("layout", {})
                            # Remove template from the layout preset
                            layout_no_template = {k: v for k, v in layout.items() if k != "template"}
                            presets[graph_type] = layout_no_template
                        except (json.JSONDecodeError, OSError):
                            pass

        if len(presets) >= len(GRAPH_TYPES):
            break

    # Also extract the plotly template from any graph
    template = None
    for speaker_dir in speakers:
        if template:
            break
        if not os.path.isdir(speaker_dir):
            continue
        for json_file in glob(f"{speaker_dir}/*/*/*.json"):
            try:
                with open(json_file, "r") as f:
                    graph_json = json.load(f)
                t = graph_json.get("layout", {}).get("template")
                if t:
                    template = t
                    break
            except (json.JSONDecodeError, OSError):
                pass

    logger.info("Extracted %d layout presets and template=%s", len(presets), template is not None)
    return presets, template


def bin_pack_speakers(speaker_data_list, target_chunks):
    """Greedy bin-packing with rebalancing for uniform compressed chunk sizes."""
    if not speaker_data_list:
        return []

    # Use raw JSON byte length for initial assignment (fast, well-correlated)
    sized = []
    for name, data in speaker_data_list:
        raw_len = len(json.dumps(data).encode("utf-8"))
        sized.append((name, data, raw_len))

    # Sort by size descending — largest-first greedy produces balanced bins
    sized.sort(key=lambda x: x[2], reverse=True)

    num_chunks = min(target_chunks, len(sized))
    chunks: list[list[tuple[str, dict, int]]] = [[] for _ in range(num_chunks)]
    chunk_sizes = [0] * num_chunks

    for name, data, size in sized:
        min_idx = chunk_sizes.index(min(chunk_sizes))
        chunks[min_idx].append((name, data, size))
        chunk_sizes[min_idx] += size

    # Rebalance: move smallest speaker from largest chunk to smallest chunk
    # until the ratio max/min is acceptable
    for _ in range(len(sized)):
        max_idx = chunk_sizes.index(max(chunk_sizes))
        min_idx = chunk_sizes.index(min(chunk_sizes))
        if chunk_sizes[min_idx] == 0 or max_idx == min_idx:
            break
        ratio = chunk_sizes[max_idx] / chunk_sizes[min_idx]
        if ratio < 1.15:
            break
        # Move the smallest speaker from the largest chunk
        smallest_in_max = min(range(len(chunks[max_idx])), key=lambda i: chunks[max_idx][i][2])
        speaker = chunks[max_idx].pop(smallest_in_max)
        chunk_sizes[max_idx] -= speaker[2]
        chunks[min_idx].append(speaker)
        chunk_sizes[min_idx] += speaker[2]

    # Strip size field, remove empty chunks
    return [[(name, data) for name, data, _ in c] for c in chunks if c]


def generate_index_json(meta, speaker_chunk_map, pic_chunk_map, logger):
    """Generate the indirection table (index.json)."""
    meta_sorted = sort_metadata_per_date(meta)
    speakers = []

    for speaker_name, speaker_data in meta_sorted.items():
        chunk_idx, chunk_pos = speaker_chunk_map.get(speaker_name, (-1, -1))
        if chunk_idx < 0:
            continue

        entry = extract_speaker_index_entry(
            speaker_name, speaker_data, chunk_idx, chunk_pos
        )

        # Picture chunk index (-1 if no picture available)
        entry["pc"] = pic_chunk_map.get(speaker_name, -1)

        speakers.append(entry)

    index = {
        "version": 1,
        "speakers": speakers,
    }

    index_path = f"{DIST_DOTLI}/index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, separators=(",", ":"), ensure_ascii=False)

    raw_size = os.path.getsize(index_path)
    logger.info("index.json: %d speakers, %.1f KB raw", len(speakers), raw_size / 1024)
    return index_path


def _compress_and_write_chunk(args):
    """Worker: compress one data chunk with brotli and write to disk."""
    chunk_idx, chunk_data, output_path = args
    chunk_json = json.dumps(chunk_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    compressed = brotli.compress(chunk_json, quality=11)
    with open(output_path, "wb") as f:
        f.write(compressed)
    return chunk_idx, len(compressed)


def generate_chunks(meta, manifest, force_rebuild, logger, target_chunks=TARGET_NUM_CHUNKS):
    """Manifest-driven chunk generation. Only writes dirty chunks."""
    logger.info("Collecting speaker graph data...")
    speaker_data_map = {}
    skipped = 0

    for speaker_name, speaker_data in meta.items():
        data = collect_speaker_graph_data(speaker_name, speaker_data)
        if data:
            speaker_data_map[speaker_name] = data
        else:
            skipped += 1

    logger.info("Collected %d speakers, skipped %d", len(speaker_data_map), skipped)

    is_initial = manifest is None or not manifest.get("data_chunks") or force_rebuild
    if is_initial:
        logger.info("Initial build: bin-packing into ~%d chunks...", target_chunks)
        speaker_data_list = [(name, data) for name, data in speaker_data_map.items()]
        manifest = compute_initial_manifest(speaker_data_list, target_chunks, logger)
        compute_initial_pic_manifest(meta, manifest, logger)
        dirty_chunks = set(int(k) for k in manifest["data_chunks"].keys())
    else:
        # Identify new speakers: in metadata with graph data but not in manifest
        manifest_speakers = set()
        for chunk_info in manifest["data_chunks"].values():
            manifest_speakers.update(chunk_info["speakers"])

        new_speakers = [name for name in speaker_data_map if name not in manifest_speakers]
        if new_speakers:
            logger.info("Found %d new speakers to assign", len(new_speakers))
        dirty_chunks = assign_new_speakers(manifest, new_speakers, speaker_data_map, logger)

    # Build speaker_chunk_map from manifest and prepare work items for dirty chunks
    speaker_chunk_map = {}
    work_items = []

    for chunk_idx_str, chunk_info in manifest["data_chunks"].items():
        chunk_idx = int(chunk_idx_str)
        for pos, name in enumerate(chunk_info["speakers"]):
            # Only include speakers that have graph data and are in current metadata
            if name in speaker_data_map:
                speaker_chunk_map[name] = (chunk_idx, pos)

        if chunk_idx in dirty_chunks:
            chunk_data = []
            for name in chunk_info["speakers"]:
                data = speaker_data_map.get(name)
                if data:
                    chunk_data.append(data)
            output_path = f"{DIST_DOTLI_CHUNKS}/chunk-{chunk_idx:03d}.json.br"
            work_items.append((chunk_idx, chunk_data, output_path))

    if work_items:
        num_workers = multiprocessing.cpu_count()
        logger.info("Compressing %d dirty chunks using %d workers...", len(work_items), num_workers)
        chunk_compressed_sizes = {}

        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            for chunk_idx, compressed_len in pool.map(_compress_and_write_chunk, work_items):
                chunk_compressed_sizes[chunk_idx] = compressed_len

        total_compressed = sum(chunk_compressed_sizes.values())
        if chunk_compressed_sizes:
            sizes = list(chunk_compressed_sizes.values())
            logger.info(
                "Wrote %d chunks: total=%.1f MB, avg=%.1f KB, min=%.1f KB, max=%.1f KB",
                len(sizes),
                total_compressed / (1024 * 1024),
                total_compressed / len(sizes) / 1024,
                min(sizes) / 1024,
                max(sizes) / 1024,
            )
    else:
        logger.info("No dirty data chunks — all chunks up to date")

    return speaker_chunk_map, manifest


def generate_html(logger):
    """Generate the SPA shell HTML."""
    html_path = f"{DIST_DOTLI}/index.html"
    html_source = "./src/dotli/index.html"

    if os.path.exists(html_source):
        shutil.copy(html_source, html_path)
    else:
        logger.error("Missing %s", html_source)
        sys.exit(1)

    logger.info("index.html: %.1f KB", os.path.getsize(html_path) / 1024)


def _compress_and_write_pic_chunk(args):
    """Worker: build one picture chunk from file paths, compress, and write."""
    chunk_idx, name_path_pairs, output_path = args
    chunk_data = {}
    for name, pic_path in name_path_pairs:
        with open(pic_path, "rb") as f:
            raw = f.read()
        chunk_data[name] = f"data:image/webp;base64,{base64.b64encode(raw).decode('ascii')}"

    chunk_json = json.dumps(chunk_data, separators=(",", ":")).encode("utf-8")
    compressed = brotli.compress(chunk_json, quality=11)
    with open(output_path, "wb") as f:
        f.write(compressed)
    return chunk_idx, len(compressed)


def generate_picture_chunks(meta, manifest, force_rebuild, logger):
    """Manifest-driven picture chunk generation. Only writes dirty chunks.

    Returns a dict mapping speaker_name -> picture_chunk_index.
    """
    pictures_dir = f"{DIST_DOTLI}/pictures"
    os.makedirs(pictures_dir, mode=0o755, exist_ok=True)

    # Collect all available webp pictures, keyed by speaker name
    pic_by_name = {}
    for pic_path in sorted(glob(f"{cpaths.CPATH_DIST_PICTURES}/*.webp")):
        speaker_name = os.path.basename(pic_path).replace(".webp", "")
        if speaker_name in meta:
            pic_by_name[speaker_name] = pic_path

    is_initial = not manifest.get("pic_chunks") or force_rebuild
    if is_initial:
        # pic manifest was already computed during generate_chunks initial build
        # or needs to be computed now if force_rebuild only affects pics
        if not manifest.get("pic_chunks"):
            compute_initial_pic_manifest(meta, manifest, logger)
        dirty_pic_chunks = set(int(k) for k in manifest["pic_chunks"].keys())
    else:
        # Identify new speakers with pictures not in pic manifest
        manifest_pic_speakers = set()
        for chunk_info in manifest["pic_chunks"].values():
            manifest_pic_speakers.update(chunk_info["speakers"])

        new_pic_speakers = [name for name in pic_by_name if name not in manifest_pic_speakers]
        if new_pic_speakers:
            logger.info("Found %d new speakers with pictures", len(new_pic_speakers))
        dirty_pic_chunks = assign_new_pic_speakers(manifest, new_pic_speakers, logger)

    # Build pic_chunk_map from manifest and prepare work items for dirty chunks
    pic_chunk_map = {}
    work_items = []

    for chunk_idx_str, chunk_info in manifest["pic_chunks"].items():
        chunk_idx = int(chunk_idx_str)
        for name in chunk_info["speakers"]:
            if name in pic_by_name:
                pic_chunk_map[name] = chunk_idx

        if chunk_idx in dirty_pic_chunks:
            name_path_pairs = []
            for name in chunk_info["speakers"]:
                if name in pic_by_name:
                    name_path_pairs.append((name, pic_by_name[name]))
            if name_path_pairs:
                output_path = f"{pictures_dir}/pic-{chunk_idx:03d}.json.br"
                work_items.append((chunk_idx, name_path_pairs, output_path))

    if work_items:
        num_workers = multiprocessing.cpu_count()
        logger.info("Compressing %d dirty picture chunks using %d workers...", len(work_items), num_workers)
        total_compressed = 0

        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            for _, compressed_len in pool.map(_compress_and_write_pic_chunk, work_items):
                total_compressed += compressed_len

        logger.info(
            "Wrote %d picture chunks, total=%.1f MB",
            len(work_items),
            total_compressed / (1024 * 1024),
        )
    else:
        logger.info("No dirty picture chunks — all up to date")

    return pic_chunk_map


def generate_js_bundle(logger, layout_presets, plotly_template):
    """Bundle JS with esbuild, embedding layout presets and template."""
    # Write layout presets and template to a JSON file for the JS bundle to import
    presets_path = "./src/dotli/app/generated-presets.json"
    with open(presets_path, "w") as f:
        json.dump(
            {"layoutPresets": layout_presets, "plotlyTemplate": plotly_template},
            f,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    logger.info("Layout presets: %.1f KB", os.path.getsize(presets_path) / 1024)

    # Run esbuild
    esbuild_bin = "./src/dotli/dotli-starter/node_modules/.bin/esbuild"
    if not os.path.exists(esbuild_bin):
        logger.error("esbuild not found at %s. Run: cd src/dotli/dotli-starter && npm install", esbuild_bin)
        sys.exit(1)

    entry = "./src/dotli/app/main.js"
    output = f"{DIST_DOTLI}/app.js"

    cmd = [
        esbuild_bin,
        entry,
        "--bundle",
        "--format=esm",
        "--minify",
        f"--outfile={output}",
        "--target=es2020",
        "--loader:.json=json",
    ]

    env = {**os.environ, "NODE_PATH": "./src/dotli/app/node_modules"}
    logger.info("Bundling JS: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        logger.error("esbuild failed: %s", result.stderr)
        sys.exit(1)

    if not os.path.exists(output):
        logger.error("esbuild did not produce output")
        sys.exit(1)

    logger.info("app.js: %.1f KB", os.path.getsize(output) / 1024)

    # Copy brotli-dec-wasm WASM file next to app.js so the browser can load it
    wasm_src = "./src/dotli/app/node_modules/brotli-dec-wasm/pkg/brotli_dec_wasm_bg.wasm"
    wasm_dst = f"{DIST_DOTLI}/brotli_dec_wasm_bg.wasm"
    if os.path.exists(wasm_src):
        shutil.copy(wasm_src, wasm_dst)
        logger.info("Copied WASM: %.1f KB", os.path.getsize(wasm_dst) / 1024)
    else:
        logger.error("WASM file not found at %s", wasm_src)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate blockchain-optimized static site for spinorama."
    )
    parser.add_argument("--version", action="version", version="generate_dotli.py version 0.1")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: INFO).",
    )
    parser.add_argument(
        "--target-chunks",
        type=int,
        default=TARGET_NUM_CHUNKS,
        help=f"Target number of chunks (default: {TARGET_NUM_CHUNKS}).",
    )
    parser.add_argument(
        "--skip-bundle",
        action="store_true",
        help="Skip JS bundling (useful for debugging).",
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        default=0,
        help="Limit to N speakers (0 = all). Useful for fast test builds.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Ignore existing manifest, regenerate all chunks from scratch.",
    )

    args = parser.parse_args()
    logger = get_custom_logger(level=args2level(args), duplicate=True)

    target_num_chunks = args.target_chunks
    force_rebuild = args.force_rebuild

    # Create output directories
    for d in (DIST_DOTLI, DIST_DOTLI_CHUNKS):
        os.makedirs(d, mode=0o755, exist_ok=True)

    # Step 1: Load metadata
    logger.info("Step 1: Loading metadata...")
    meta = load_metadata(logger)
    if args.max_speakers > 0:
        meta_sorted = sort_metadata_per_date(meta)
        meta = dict(list(meta_sorted.items())[: args.max_speakers])
        target_num_chunks = min(target_num_chunks, max(1, len(meta) // 2))
    logger.info("Loaded %d speakers", len(meta))

    # Step 2: Extract layout presets from existing graphs
    logger.info("Step 2: Extracting layout presets...")
    layout_presets, plotly_template = extract_layout_presets(logger)

    # Step 3: Load or create manifest
    logger.info("Step 3: Loading manifest...")
    manifest = None if force_rebuild else load_manifest(logger)

    # Step 4: Generate data chunks (manifest-driven)
    logger.info("Step 4: Generating data chunks...")
    speaker_chunk_map, manifest = generate_chunks(
        meta, manifest, force_rebuild, logger, target_chunks=target_num_chunks
    )

    # Step 5: Generate picture chunks (manifest-driven)
    logger.info("Step 5: Generating picture chunks...")
    pic_chunk_map = generate_picture_chunks(meta, manifest, force_rebuild, logger)

    # Step 6: Save manifest
    logger.info("Step 6: Saving manifest...")
    save_manifest(manifest, logger)

    # Step 7: Generate index.json (needs both chunk maps)
    logger.info("Step 7: Generating index.json...")
    generate_index_json(meta, speaker_chunk_map, pic_chunk_map, logger)

    # Step 8: Generate HTML shell
    logger.info("Step 8: Generating HTML shell...")
    generate_html(logger)

    # Step 9: Bundle JS
    if not args.skip_bundle:
        logger.info("Step 9: Bundling JS...")
        generate_js_bundle(logger, layout_presets, plotly_template)
    else:
        logger.info("Step 9: Skipping JS bundle (--skip-bundle)")

    # Summary
    total_size = 0
    for dirpath, _, filenames in os.walk(DIST_DOTLI):
        for f in filenames:
            total_size += os.path.getsize(os.path.join(dirpath, f))

    logger.info("=== Done! ===")
    logger.info("Output: %s", DIST_DOTLI)
    logger.info("Total size: %.1f MB", total_size / (1024 * 1024))
    logger.info("Serve with: python -m http.server -d %s", DIST_DOTLI)


if __name__ == "__main__":
    main()
