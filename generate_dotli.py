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
import gzip
import json
import os
import shutil
import subprocess
import sys
from glob import glob

from generate_common import (
    args2level,
    find_metadata_file,
    get_custom_logger,
    sort_metadata_per_date,
)

import spinorama.constant_paths as cpaths

DIST_DOTLI = "./dist-dotli"
DIST_DOTLI_CHUNKS = f"{DIST_DOTLI}/chunks"
SITEPROD = "https://www.spinorama.org"

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
        pic_path = f"{cpaths.CPATH_DIST_PICTURES}/{speaker_name}.{ext}"
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
    speaker_dir = f"{cpaths.CPATH_DIST_SPEAKERS}/{speaker_name}"
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
    """Greedy bin-packing: sort by size desc, assign each to smallest bin."""
    if not speaker_data_list:
        return []

    # Compute compressed size for each speaker
    sized = []
    for name, data in speaker_data_list:
        raw = json.dumps(data).encode("utf-8")
        compressed = gzip.compress(raw)
        sized.append((name, data, len(compressed)))

    # Sort by compressed size descending
    sized.sort(key=lambda x: x[2], reverse=True)

    num_chunks = min(target_chunks, len(sized))
    chunks = [[] for _ in range(num_chunks)]
    chunk_sizes = [0] * num_chunks

    for name, data, size in sized:
        # Find the chunk with the smallest current total
        min_idx = chunk_sizes.index(min(chunk_sizes))
        chunks[min_idx].append((name, data))
        chunk_sizes[min_idx] += size

    # Remove empty chunks
    chunks = [c for c in chunks if c]
    return chunks


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


def generate_chunks(meta, logger, target_chunks=TARGET_NUM_CHUNKS):
    """Collect graph data for all speakers and pack into gzipped chunks."""
    logger.info("Collecting speaker graph data...")
    speaker_data_list = []
    skipped = 0

    for speaker_name, speaker_data in meta.items():
        data = collect_speaker_graph_data(speaker_name, speaker_data)
        if data:
            speaker_data_list.append((speaker_name, data))
        else:
            skipped += 1

    logger.info("Collected %d speakers, skipped %d", len(speaker_data_list), skipped)

    logger.info("Bin-packing into ~%d chunks...", target_chunks)
    chunks = bin_pack_speakers(speaker_data_list, target_chunks)
    logger.info("Created %d chunks", len(chunks))

    # Build chunk map: speaker_name -> (chunk_idx, position_within_chunk)
    speaker_chunk_map = {}
    total_compressed = 0

    for chunk_idx, chunk in enumerate(chunks):
        chunk_data = []
        for pos, (name, data) in enumerate(chunk):
            speaker_chunk_map[name] = (chunk_idx, pos)
            chunk_data.append(data)

        chunk_json = json.dumps(chunk_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        compressed = gzip.compress(chunk_json, compresslevel=9)
        total_compressed += len(compressed)

        chunk_filename = f"{DIST_DOTLI_CHUNKS}/chunk-{chunk_idx:03d}.json.gz"
        with open(chunk_filename, "wb") as f:
            f.write(compressed)

    avg_size = total_compressed / len(chunks) if chunks else 0
    logger.info(
        "Chunks: total=%.1f MB, avg=%.1f KB, count=%d",
        total_compressed / (1024 * 1024),
        avg_size / 1024,
        len(chunks),
    )

    return speaker_chunk_map


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


PICTURES_PER_CHUNK = 50


def generate_picture_chunks(meta, logger):
    """Pack webp pictures into gzipped JSON chunks with base64 data URIs.

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

    # Group alphabetically into chunks
    sorted_names = sorted(pic_by_name.keys())
    pic_chunk_map = {}
    total_compressed = 0
    chunk_idx = 0

    for i in range(0, len(sorted_names), PICTURES_PER_CHUNK):
        batch = sorted_names[i : i + PICTURES_PER_CHUNK]
        chunk_data = {}
        for name in batch:
            pic_path = pic_by_name[name]
            with open(pic_path, "rb") as f:
                raw = f.read()
            chunk_data[name] = f"data:image/webp;base64,{base64.b64encode(raw).decode('ascii')}"
            pic_chunk_map[name] = chunk_idx

        chunk_json = json.dumps(chunk_data, separators=(",", ":")).encode("utf-8")
        compressed = gzip.compress(chunk_json, compresslevel=9)
        total_compressed += len(compressed)

        chunk_file = f"{pictures_dir}/pic-{chunk_idx:03d}.json.gz"
        with open(chunk_file, "wb") as f:
            f.write(compressed)

        chunk_idx += 1

    logger.info(
        "Picture chunks: %d pictures in %d chunks, total=%.1f MB",
        len(pic_by_name),
        chunk_idx,
        total_compressed / (1024 * 1024),
    )
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

    if os.path.exists(output):
        logger.info("app.js: %.1f KB", os.path.getsize(output) / 1024)
    else:
        logger.error("esbuild did not produce output")
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

    args = parser.parse_args()
    logger = get_custom_logger(level=args2level(args), duplicate=True)

    target_num_chunks = args.target_chunks

    # Create output directories
    for d in (DIST_DOTLI, DIST_DOTLI_CHUNKS):
        os.makedirs(d, mode=0o755, exist_ok=True)

    # Step 1: Load metadata
    logger.info("Step 1: Loading metadata...")
    meta = load_metadata(logger)
    logger.info("Loaded %d speakers", len(meta))

    # Step 2: Extract layout presets from existing graphs
    logger.info("Step 2: Extracting layout presets...")
    layout_presets, plotly_template = extract_layout_presets(logger)

    # Step 3: Generate data chunks
    logger.info("Step 3: Generating data chunks...")
    speaker_chunk_map = generate_chunks(meta, logger, target_chunks=target_num_chunks)

    # Step 4: Generate picture chunks
    logger.info("Step 4: Generating picture chunks...")
    pic_chunk_map = generate_picture_chunks(meta, logger)

    # Step 5: Generate index.json (needs both chunk maps)
    logger.info("Step 5: Generating index.json...")
    generate_index_json(meta, speaker_chunk_map, pic_chunk_map, logger)

    # Step 6: Generate HTML shell
    logger.info("Step 6: Generating HTML shell...")
    generate_html(logger)

    # Step 7: Bundle JS
    if not args.skip_bundle:
        logger.info("Step 7: Bundling JS...")
        generate_js_bundle(logger, layout_presets, plotly_template)
    else:
        logger.info("Step 7: Skipping JS bundle (--skip-bundle)")

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
