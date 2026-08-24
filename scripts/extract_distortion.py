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

"""CLI entry point for extracting distortion curves from Klippel graph images.

Usage:
    python scripts/extract_distortion.py input.png [-o output.json] [--debug] [--validate]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from spinorama import logger, setup_logger
from spinorama.extract.distortion import extract_curves


def validate_results(wpd_json: dict) -> bool:
    """Print consistency checks on extracted curves."""
    datasets = wpd_json.get("datasetColl", [])
    if not datasets:
        print("VALIDATION FAIL: No datasets extracted")
        return False

    print(f"\nValidation: {len(datasets)} curve(s) extracted")

    curve_means: dict[str, float] = {}
    for ds in datasets:
        name = ds["name"]
        data = ds["data"]
        if not data:
            print(f"  WARNING: '{name}' has no data points")
            continue

        dbs = [d["value"][1] for d in data]
        freqs = [d["value"][0] for d in data]
        mean_db = sum(dbs) / len(dbs)
        curve_means[name] = mean_db
        print(
            f"  '{name}': {len(data)} points, "
            f"freq=[{min(freqs):.0f}, {max(freqs):.0f}] Hz, "
            f"dB=[{min(dbs):.1f}, {max(dbs):.1f}], mean={mean_db:.1f}"
        )

    # Check: Fundamental should be louder than THD
    fundamental_names = [n for n in curve_means if "Fundamental" in n]
    thd_names = [n for n in curve_means if "THD" in n]

    if fundamental_names and thd_names:
        fund_mean = curve_means[fundamental_names[0]]
        thd_mean = curve_means[thd_names[0]]
        if fund_mean <= thd_mean:
            print(f"  WARNING: Fundamental ({fund_mean:.1f} dB) <= THD ({thd_mean:.1f} dB)")
        else:
            print(f"  OK: Fundamental ({fund_mean:.1f} dB) > THD ({thd_mean:.1f} dB)")

    # Check: THD should be louder than individual harmonics
    harmonic_names = [n for n in curve_means if "Harmonic" in n]
    if thd_names and harmonic_names:
        thd_mean = curve_means[thd_names[0]]
        for hname in harmonic_names:
            hmean = curve_means[hname]
            if thd_mean < hmean:
                print(f"  WARNING: THD ({thd_mean:.1f} dB) < {hname} ({hmean:.1f} dB)")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract distortion curves from Klippel graph images to WPD JSON."
    )
    parser.add_argument("input", type=Path, help="Input image file (PNG/JPEG)")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON file (default: input.json)")
    parser.add_argument("--debug", action="store_true", help="Save intermediate debug images")
    parser.add_argument("--debug-dir", type=Path, help="Directory for debug images")
    parser.add_argument("--validate", action="store_true", help="Print consistency checks")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    output = args.output if args.output else args.input.with_suffix(".json")

    try:
        wpd_json = extract_curves(args.input, debug=args.debug)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    with open(output, "w") as f:
        json.dump(wpd_json, f, indent=2)

    print(f"Wrote {output}")

    datasets = wpd_json.get("datasetColl", [])
    total_points = sum(len(ds["data"]) for ds in datasets)
    print(f"Extracted {len(datasets)} curve(s), {total_points} total points")

    if args.validate:
        validate_results(wpd_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
