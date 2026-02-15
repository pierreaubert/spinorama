#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple script to compute spinorama graphs and preference scores from speaker measurements.

Takes a directory with speaker data in any supported format and generates all graphs
in the same directory. Outputs the preference score with details.

Usage:
    python scripts/compute_spin.py /path/to/speaker/data [--format auto]

Supported formats:
    - klippel: Klippel format (SPL Horizontal/Vertical txt files)
    - princeton: Princeton 3D3A format (H_IR/V_IR .mat files)
    - spl_hv_txt: Generic text format (angle_H.txt / angle_V.txt)
    - gll_hv_txt: GLL format (zipped meridian/parallel txt files)
    - rew_text_dump: REW text export format (On Axis, LW, ER, SP, etc.)
    - webplotdigitizer: WebPlotDigitizer JSON format
"""

import argparse
import os
import sys
import glob
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spinorama import logger, setup_logger
from spinorama.load import filter_graphs, filter_graphs_partial
from spinorama.compute_scores import speaker_pref_rating
from spinorama.speaker import (
    display_spinorama,
    display_spinorama_normalized,
    display_onaxis,
    display_inroom,
    display_inroom_normalized,
    display_group_delay,
    display_contour_horizontal,
    display_contour_vertical,
    display_contour_horizontal_normalized,
    display_contour_vertical_normalized,
    display_contour_horizontal_3d,
    display_contour_vertical_3d,
    display_contour_horizontal_normalized_3d,
    display_contour_vertical_normalized_3d,
    display_spl_horizontal,
    display_spl_vertical,
    display_spl_horizontal_normalized,
    display_spl_vertical_normalized,
    display_reflection_early,
    display_reflection_horizontal,
    display_reflection_vertical,
    display_radar_horizontal,
    display_radar_vertical,
    plot_params_default,
    contour_params_default,
    radar_params_default,
)
from spinorama.misc import write_multiformat, measurements_valid_freq_range
from spinorama.ltype import DataSpeaker
from spinorama.constant_paths import DEFAULT_FREQ_RANGE

# Import format-specific loaders
from spinorama.load_klippel import parse_graphs_speaker_klippel
from spinorama.load_princeton import parse_graphs_speaker_princeton
from spinorama.load_spl_hv_txt import parse_graphs_speaker_spl_hv_txt
from spinorama.load_gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from spinorama.compute_misc import unify_freq
from spinorama.misc import graph_melt


VERSION = "1.0.1"

# Origins info for graph parameters (using generic defaults)
DEFAULT_ORIGIN_INFO = {
    "min hz": 20,
    "max hz": 20000,
    "min dB": -40,
    "max dB": 10,
}


def detect_format(data_dir: str, speaker_name: str) -> tuple[str, str] | None:
    """Auto-detect the format of speaker data in the directory.

    Returns tuple of (format, version) or None if cannot detect.
    """
    base_path = Path(data_dir)

    # Helper to check a directory for valid formats
    def check_dir(path: Path, version: str) -> tuple[str, str] | None:
        # Check for Klippel format (SPL Horizontal.txt / SPL Vertical.txt)
        if (path / "SPL Horizontal.txt").exists() and (
            path / "SPL Vertical.txt"
        ).exists():
            return ("klippel", version)

        # Check for Princeton format (*_H_IR.mat / *_V_IR.mat)
        mat_files = list(path.glob("*_H_IR.mat"))
        if mat_files and list(path.glob("*_V_IR.mat")):
            return ("princeton", version)

        # Check for GLL format (*.zip with txt files)
        zip_files = list(path.glob("*.zip"))
        if zip_files:
            return ("gll_hv_txt", version)

        # Check for spl_hv_txt format (*_H.txt / * _H.txt patterns)
        h_files = list(path.glob("*_H.txt")) + list(path.glob("*H*.txt"))
        v_files = list(path.glob("*_V.txt")) + list(path.glob("*V*.txt"))
        if h_files and v_files:
            return ("spl_hv_txt", version)

        # Check for REW text dump (On Axis.txt, LW.txt, ER.txt, SP.txt)
        rew_files = ["On Axis.txt", "LW.txt", "ER.txt", "SP.txt"]
        if all((path / f).exists() for f in rew_files):
            return ("rew_text_dump", version)

        # Check for WebPlotDigitizer (*.json or *.tar)
        json_files = list(path.glob("*.json"))
        tar_files = list(path.glob("*.tar"))
        if json_files or tar_files:
            return ("webplotdigitizer", version)

        return None

    # First, check the base directory itself (prefer direct files over subdirs)
    result = check_dir(base_path, base_path.name)
    if result is not None:
        return result

    # If no files in base, check subdirectories
    subdirs = [d for d in base_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    for version_dir in subdirs:
        result = check_dir(version_dir, version_dir.name)
        if result is not None:
            return result

    return None


def load_speaker_data(
    data_dir: str, speaker_name: str, fmt: str, version: str, symmetry: str | None = None
) -> tuple[bool, DataSpeaker, dict]:
    """Load speaker data from the specified directory and format.

    Returns (success, data_dict, parameters)
    """
    # When user points directly to a speaker directory (not a parent),
    # we need to construct the path correctly for the loaders.
    # Loaders expect: {speaker_path}/{speaker_name}/{version}/{file}
    # So if data_dir is the speaker dir, we use its parent as speaker_path
    parent_dir = os.path.dirname(os.path.abspath(data_dir))
    dir_name = os.path.basename(os.path.abspath(data_dir))

    # Use "default" as version if it's same as dir name (to avoid tmp/tmp/tmp)
    # If files are directly in the directory (no subdirs), use "." for version
    subdirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    actual_version = version if version != dir_name and subdirs else "."

    shape = "default"
    # Note: symmetry parameter is passed directly to loaders

    parameters = {
        "mformat": fmt,
        "morigin": "compute_spin",
        "mversion": actual_version,
        "msymmetry": symmetry,
        "mparameters": None,
        "distance": 1.0,  # Default measurement distance
        "shape": shape,
        "width": 800,
        "height": 600,
    }

    h_spl = None
    v_spl = None
    df_graph = {}

    try:
        if fmt == "klippel":
            status, (h_spl, v_spl) = parse_graphs_speaker_klippel(
                parent_dir, "", dir_name, actual_version, shape
            )
            if not status:
                return False, {}, parameters
            df_graph = filter_graphs(speaker_name, h_spl, v_spl, 300, 3000, fmt, 1.0)

        elif fmt == "princeton":
            status, (h_spl, v_spl) = parse_graphs_speaker_princeton(
                parent_dir, "", dir_name, actual_version, symmetry
            )
            if not status:
                return False, {}, parameters
            df_graph = filter_graphs(speaker_name, h_spl, v_spl, 300, 3000, fmt, 1.0)

        elif fmt == "spl_hv_txt":
            status, (h_spl, v_spl) = parse_graphs_speaker_spl_hv_txt(
                parent_dir, "", dir_name, actual_version, symmetry
            )
            if not status:
                return False, {}, parameters
            df_graph = filter_graphs(speaker_name, h_spl, v_spl, 300, 3000, fmt, 1.0)

        elif fmt == "gll_hv_txt":
            status, (h_spl, v_spl) = parse_graphs_speaker_gll_hv_txt(
                parent_dir, dir_name, actual_version
            )
            if not status:
                return False, {}, parameters
            df_graph = filter_graphs(speaker_name, h_spl, v_spl, 300, 3000, fmt, 1.0)

        elif fmt == "rew_text_dump":
            status, (title, df_uneven) = parse_graphs_speaker_rew_text_dump(
                parent_dir, "", dir_name, "compute_spin", actual_version
            )
            if not status:
                return False, {}, parameters
            df_even = graph_melt(unify_freq(df_uneven))
            # Minimal processing for REW format
            df_graph = {"CEA2034": df_even}
            # Compute additional graphs
            df_graph = filter_graphs_partial(df_graph, fmt, 1.0)

        elif fmt == "webplotdigitizer":
            status, (title, df_uneven) = parse_graphs_speaker_webplotdigitizer(
                parent_dir, "", dir_name, "compute_spin", actual_version
            )
            if not status:
                return False, {}, parameters
            df_even = graph_melt(unify_freq(df_uneven))
            df_graph = {"CEA2034": df_even}
            df_graph = filter_graphs_partial(df_graph, fmt, 1.0)

        else:
            logger.error(f"Unknown format: {fmt}")
            return False, {}, parameters

    except Exception as e:
        logger.exception(f"Error loading speaker data: {e}")
        return False, {}, parameters

    if not df_graph:
        logger.error("No data loaded - graph generation failed")
        return False, {}, parameters

    return True, df_graph, parameters


def compute_preference_score(df_graph: DataSpeaker) -> dict[str, Any]:
    """Compute preference score from the generated graphs."""
    cea2034 = df_graph.get("CEA2034")
    pir = df_graph.get("Estimated In-Room Response")

    if cea2034 is None:
        logger.warning("CEA2034 data not found - cannot compute preference score")
        return {}

    # Ensure data is in melted format
    if "Measurements" not in cea2034.columns:
        cea2034 = graph_melt(cea2034)

    if pir is not None and "Measurements" not in pir.columns:
        pir = graph_melt(pir)

    return speaker_pref_rating(cea2034, pir, rounded=True)


def generate_graphs(
    df_graph: DataSpeaker,
    speaker_name: str,
    output_dir: str,
    parameters: dict,
    force: bool = False,
) -> list[str]:
    """Generate all graphs and save them to the output directory.

    Returns list of generated file paths.
    """
    generated_files = []

    # Set up graph parameters
    graph_params = plot_params_default.copy()
    graph_params["width"] = parameters.get("width", 800)
    graph_params["height"] = parameters.get("height", 600)
    graph_params["layout"] = "compact"
    graph_params["xmin"] = DEFAULT_ORIGIN_INFO["min hz"]
    graph_params["xmax"] = DEFAULT_ORIGIN_INFO["max hz"]
    graph_params["ymin"] = DEFAULT_ORIGIN_INFO["min dB"]
    graph_params["ymax"] = DEFAULT_ORIGIN_INFO["max dB"]

    # Determine valid frequency range
    h_spl = df_graph.get("SPL Horizontal_unmelted")
    v_spl = df_graph.get("SPL Vertical_unmelted")
    valid_freq_range = (20.0, 20000.0)
    if h_spl is not None and "Freq" in h_spl:
        valid_freq_range = (
            max(valid_freq_range[0], h_spl.Freq.min()),
            min(valid_freq_range[1], h_spl.Freq.max()),
        )
    if v_spl is not None and "Freq" in v_spl:
        valid_freq_range = (
            max(valid_freq_range[0], v_spl.Freq.min()),
            min(valid_freq_range[1], v_spl.Freq.max()),
        )

    # Generate main graphs
    graphs_to_generate = [
        ("CEA2034", display_spinorama, False),
        ("CEA2034_Normalized", display_spinorama_normalized, False),
        ("On_Axis", display_onaxis, False),
        ("Group_Delay", display_group_delay, False),
    ]

    # Add in-room response if available
    if "Estimated In-Room Response" in df_graph:
        graphs_to_generate.extend([
            ("Estimated_In-Room_Response", display_inroom, False),
            ("Estimated_In-Room_Response_Normalized", display_inroom_normalized, False),
        ])

    # Generate and save each graph
    for graph_name, display_func, _is_contour in graphs_to_generate:
        try:
            fig = display_func(df_graph, graph_params, valid_freq_range)
            if fig is None:
                logger.debug(f"Failed to generate {graph_name} graph (data may not be available)")
                continue

            # Clean up filename
            filename = f"{speaker_name}_{graph_name}.png"
            filepath = os.path.join(output_dir, filename)

            # Save graph
            write_multiformat(fig, filepath, force)
            generated_files.append(filepath)
            print(f"  Generated: {filename}")

        except Exception as e:
            logger.debug(f"Error generating {graph_name}: {e}")

    # Generate contour plots if we have SPL data
    fmt = parameters.get("mformat", "")
    if fmt in ("klippel", "spl_hv_txt", "gll_hv_txt", "princeton"):
        contour_params = contour_params_default.copy()
        contour_params["width"] = graph_params["width"]
        contour_params["height"] = graph_params["height"]
        contour_params["layout"] = "compact"
        contour_params["xmin"] = DEFAULT_ORIGIN_INFO["min hz"]
        contour_params["xmax"] = DEFAULT_ORIGIN_INFO["max hz"]

        # Radar params
        radar_params = radar_params_default.copy()
        radar_params["width"] = int(graph_params["height"] * 4 / 5)
        radar_params["height"] = graph_params["height"]
        radar_params["layout"] = "compact"
        radar_params["xmin"] = DEFAULT_ORIGIN_INFO["min hz"]
        radar_params["xmax"] = DEFAULT_ORIGIN_INFO["max hz"]

        # Reflection graphs
        reflection_graphs = [
            ("Early_Reflections", display_reflection_early),
            ("Horizontal_Reflections", display_reflection_horizontal),
            ("Vertical_Reflections", display_reflection_vertical),
        ]

        for graph_name, display_func in reflection_graphs:
            try:
                fig = display_func(df_graph, graph_params, valid_freq_range)
                if fig is None:
                    continue

                filename = f"{speaker_name}_{graph_name}.png"
                filepath = os.path.join(output_dir, filename)
                write_multiformat(fig, filepath, force)
                generated_files.append(filepath)
                print(f"  Generated: {filename}")

            except Exception as e:
                logger.debug(f"Error generating {graph_name}: {e}")

        # SPL graphs (regular and normalized)
        spl_graphs = [
            ("SPL_Horizontal", display_spl_horizontal),
            ("SPL_Vertical", display_spl_vertical),
            ("SPL_Horizontal_Normalized", display_spl_horizontal_normalized),
            ("SPL_Vertical_Normalized", display_spl_vertical_normalized),
        ]

        for graph_name, display_func in spl_graphs:
            try:
                fig = display_func(df_graph, graph_params, valid_freq_range, include_all_angles=True)
                if fig is None:
                    continue

                filename = f"{speaker_name}_{graph_name}.png"
                filepath = os.path.join(output_dir, filename)
                write_multiformat(fig, filepath, force)
                generated_files.append(filepath)
                print(f"  Generated: {filename}")

            except Exception as e:
                logger.debug(f"Error generating {graph_name}: {e}")

        # Contour graphs (regular, normalized, and 3D)
        contour_graphs = [
            ("SPL_Horizontal_Contour", display_contour_horizontal, False),
            ("SPL_Vertical_Contour", display_contour_vertical, False),
            ("SPL_Horizontal_Contour_Normalized", display_contour_horizontal_normalized, False),
            ("SPL_Vertical_Contour_Normalized", display_contour_vertical_normalized, False),
            ("SPL_Horizontal_Contour_3D", display_contour_horizontal_3d, True),
            ("SPL_Vertical_Contour_3D", display_contour_vertical_3d, True),
            ("SPL_Horizontal_Contour_Normalized_3D", display_contour_horizontal_normalized_3d, True),
            ("SPL_Vertical_Contour_Normalized_3D", display_contour_vertical_normalized_3d, True),
        ]

        for graph_name, display_func, is_3d in contour_graphs:
            try:
                fig = display_func(df_graph, contour_params, valid_freq_range)
                if fig is None:
                    continue

                filename = f"{speaker_name}_{graph_name}.png"
                filepath = os.path.join(output_dir, filename)
                write_multiformat(fig, filepath, force)
                generated_files.append(filepath)
                print(f"  Generated: {filename}")

            except Exception as e:
                logger.debug(f"Error generating {graph_name}: {e}")

        # Radar graphs
        radar_graphs = [
            ("SPL_Horizontal_Radar", display_radar_horizontal),
            ("SPL_Vertical_Radar", display_radar_vertical),
        ]

        for graph_name, display_func in radar_graphs:
            try:
                fig = display_func(df_graph, radar_params, valid_freq_range)
                if fig is None:
                    continue

                filename = f"{speaker_name}_{graph_name}.png"
                filepath = os.path.join(output_dir, filename)
                write_multiformat(fig, filepath, force)
                generated_files.append(filepath)
                print(f"  Generated: {filename}")

            except Exception as e:
                logger.debug(f"Error generating {graph_name}: {e}")

    return generated_files


def print_preference_score(scores: dict[str, Any]):
    """Print preference score details in a user-friendly format."""
    if not scores:
        print("\nPreference Score: Unable to compute (insufficient data)")
        return

    print("\n" + "=" * 60)
    print("PREFERENCE SCORE")
    print("=" * 60)

    pref_score = scores.get("pref_score")
    pref_score_wsub = scores.get("pref_score_wsub")

    if pref_score is not None:
        print(f"\n  Overall Score: {pref_score}/10")
    if pref_score_wsub is not None:
        print(f"  With Subwoofer: {pref_score_wsub}/10")

    print("\n  Components:")
    print(f"    - NBD On Axis:     {scores.get('nbd_on_axis', 'N/A'):>8}")
    print(f"    - NBD PIR:         {scores.get('nbd_pred_in_room', 'N/A'):>8}")
    print(f"    - Smoothness PIR:  {scores.get('sm_pred_in_room', 'N/A'):>8}")

    lfx = scores.get("lfx_hz")
    if lfx is not None:
        print(f"    - Low Freq Ext:    {lfx:>7} Hz")

    lfq = scores.get("lfq")
    if lfq is not None:
        print(f"    - Low Freq Qual:   {lfq:>8}")

    aad = scores.get("aad_on_axis")
    if aad is not None:
        print(f"    - AAD On Axis:     {aad:>8}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Compute spinorama graphs and preference scores from speaker measurements.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s /path/to/speaker/data
    %(prog)s /path/to/speaker/data --format klippel
    %(prog)s /path/to/speaker/data --output-dir ./graphs --force
        """,
    )
    parser.add_argument("directory", help="Directory containing speaker measurement data")
    parser.add_argument(
        "--format",
        choices=["auto", "klippel", "princeton", "spl_hv_txt", "gll_hv_txt", "rew_text_dump", "webplotdigitizer"],
        default="auto",
        help="Input format (default: auto-detect)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for graphs (default: same as input directory)",
    )
    parser.add_argument(
        "--speaker-name",
        help="Speaker name (default: derived from directory name)",
    )
    parser.add_argument(
        "--width", type=int, default=800, help="Graph width in pixels (default: 800)"
    )
    parser.add_argument(
        "--height", type=int, default=600, help="Graph height in pixels (default: 600)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing files"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--symmetry",
        choices=["auto", "mirror", "shift", "none"],
        default="auto",
        help="Speaker symmetry mode: auto (detect from files), mirror (copy + to -), shift (wrap 180-350 to -180-0), none (as-is). Affects horizontal angle handling. (default: auto)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)

    # Validate input directory
    data_dir = os.path.abspath(args.directory)
    if not os.path.exists(data_dir):
        print(f"Error: Directory not found: {data_dir}")
        return 1
    if not os.path.isdir(data_dir):
        print(f"Error: Not a directory: {data_dir}")
        return 1

    # Determine speaker name
    speaker_name = args.speaker_name or os.path.basename(data_dir)
    if not speaker_name:
        speaker_name = "speaker"

    # Determine output directory
    output_dir = args.output_dir or data_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nProcessing: {speaker_name}")
    print(f"Input directory: {data_dir}")
    print(f"Output directory: {output_dir}")

    # Determine format
    fmt = args.format
    version = "default"

    if fmt == "auto":
        print("\nAuto-detecting format...")
        detected = detect_format(data_dir, speaker_name)
        if detected is None:
            print("\nError: Could not auto-detect input format.")
            print("\nSupported formats:")
            print("  - Klippel: SPL Horizontal.txt + SPL Vertical.txt")
            print("  - Princeton: *_H_IR.mat + *_V_IR.mat")
            print("  - SPL HV TXT: *_H.txt + *_V.txt files")
            print("  - GLL: *.zip with meridian/parallel txt files")
            print("  - REW Text: On Axis.txt, LW.txt, ER.txt, SP.txt")
            print("  - WebPlotDigitizer: *.json or *.tar files")
            print("\nPlease specify format manually with --format")
            return 1
        fmt, version = detected
        print(f"  Detected: {fmt} (version: {version})")
    else:
        # For manual format, use the directory name as version if there's a subdirectory
        subdirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
        if subdirs:
            version = subdirs[0]

    # Determine symmetry setting
    symmetry: str | None
    if args.symmetry == "auto":
        symmetry = None  # Auto-detect from files
    else:
        symmetry = args.symmetry  # "mirror", "shift", or "none"

    # Load speaker data
    print(f"\nLoading speaker data (format: {fmt})...")
    success, df_graph, parameters = load_speaker_data(data_dir, speaker_name, fmt, version, symmetry)

    if not success or not df_graph:
        print("\nError: Failed to load speaker data.")
        print("Please check that:")
        print("  1. The directory contains valid measurement files")
        print("  2. The format is correctly specified or detected")
        print("  3. Files are not corrupted")
        return 1

    print("  Loaded successfully!")

    # Update parameters with CLI args
    parameters["width"] = args.width
    parameters["height"] = args.height

    # Compute preference score
    print("\nComputing preference score...")
    scores = compute_preference_score(df_graph)

    # Generate graphs
    print("\nGenerating graphs...")
    generated = generate_graphs(df_graph, speaker_name, output_dir, parameters, args.force)

    # Print results
    print_preference_score(scores)

    print(f"\nGenerated {len(generated)} graph(s) in: {output_dir}")

    # Save scores to JSON file
    if scores:
        scores_file = os.path.join(output_dir, f"{speaker_name}_scores.json")
        try:
            with open(scores_file, "w") as f:
                json.dump(scores, f, indent=2)
            print(f"Scores saved to: {scores_file}")
        except Exception as e:
            logger.warning(f"Could not save scores: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
