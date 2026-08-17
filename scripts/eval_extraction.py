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

"""CLI: Evaluate extraction pipeline quality against Plotly ground truth.

Usage:
    python scripts/eval_extraction.py \\
        --data-dir /Volumes/data/Binaries/spinorama/dist/speakers \\
        --graph-types CEA2034 "On Axis" \\
        --sample-size 100 \\
        --seed 42 \\
        --calibration-mode oracle \\
        --output eval_results.json \\
        -v
"""

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from graphextract.eval_extraction import (
    compute_aggregate_stats,
    evaluate_batch,
    generate_html_report,
)


# Map graph type to JSON filename
GRAPH_TYPE_FILES: dict[str, str] = {
    "CEA2034": "CEA2034.json",
    "On Axis": "On Axis.json",
    "Early Reflections": "Early Reflections.json",
    "Estimated In-Room Response": "Estimated In-Room Response.json",
}


def discover_files(data_dir: Path, graph_types: list[str]) -> list[tuple[Path, str]]:
    """Find all Plotly JSON files for the given graph types under data_dir."""
    files: list[tuple[Path, str]] = []
    for gt in graph_types:
        filename = GRAPH_TYPE_FILES.get(gt)
        if filename is None:
            print(f"Warning: unknown graph type '{gt}', skipping", file=sys.stderr)
            continue
        for p in sorted(data_dir.rglob(filename)):
            files.append((p, gt))
    return files


def print_summary(aggregate: dict) -> None:
    """Print a human-readable summary table to stdout."""
    print("\n" + "=" * 80)
    print("EXTRACTION EVALUATION SUMMARY")
    print("=" * 80)

    # By graph type
    print("\n--- By Graph Type ---")
    for gt, stats in aggregate["by_graph_type"].items():
        print(f"\n  {gt}:")
        print(
            f"    Success rate: {stats['success_rate']:.1%} ({stats['success']}/{stats['total']})"
        )
        if stats["rms_error_db"]:
            rms = stats["rms_error_db"]
            print(
                f"    RMS error (dB):  median={rms['median']:.2f}  mean={rms['mean']:.2f}  p95={rms['p95']:.2f}  max={rms['max']:.2f}"
            )
        if stats["correlation"]:
            corr = stats["correlation"]
            print(
                f"    Correlation:     median={corr['median']:.4f}  mean={corr['mean']:.4f}  p95={corr['p95']:.4f}"
            )
        if stats["frequency_coverage"]:
            cov = stats["frequency_coverage"]
            print(
                f"    Coverage:        median={cov['median']:.1%}  mean={cov['mean']:.1%}  p95={cov['p95']:.1%}"
            )

    # By curve name
    print("\n--- By Curve Name ---")
    for cn, stats in aggregate["by_curve_name"].items():
        rms = stats["rms_error_db"]
        if not rms:
            continue
        print(
            f"  {cn:30s}  RMS median={rms['median']:.2f}  mean={rms['mean']:.2f}  n={rms['count']}"
        )

    # Worst cases
    print("\n--- Worst Cases (by RMS) ---")
    for i, wc in enumerate(aggregate["worst_cases"]):
        print(
            f"  {i + 1:2d}. RMS={wc['rms_error_db']:.2f} dB  max={wc['max_abs_error_db']:.2f} dB  "
            f"curve={wc['curve_name']}  file={Path(wc['file_path']).parent.name}"
        )

    print("\n" + "=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate extraction pipeline quality")
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to speakers directory with Plotly JSON files",
    )
    parser.add_argument(
        "--graph-types",
        nargs="+",
        default=["CEA2034"],
        help="Graph types to evaluate (default: CEA2034)",
    )
    parser.add_argument(
        "--sample-size", type=int, default=0, help="Number of files to sample (0=all)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument(
        "--calibration-mode",
        choices=["oracle", "auto"],
        default="oracle",
        help="Calibration mode (default: oracle)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Output JSON file for results")
    parser.add_argument("--html", type=Path, default=None, help="Output HTML report file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Discover files
    all_files = discover_files(args.data_dir, args.graph_types)
    print(f"Found {len(all_files)} files across {args.graph_types}")

    if not all_files:
        print("No files found, exiting.", file=sys.stderr)
        sys.exit(1)

    # Sample
    if args.sample_size > 0 and args.sample_size < len(all_files):
        all_files.sort(key=lambda x: str(x[0]))
        sampled = random.Random(args.seed).sample(all_files, args.sample_size)
    else:
        sampled = all_files

    print(f"Evaluating {len(sampled)} files (seed={args.seed}, mode={args.calibration_mode})")

    # Count per graph type
    counts: dict[str, int] = {}
    for _, gt in sampled:
        counts[gt] = counts.get(gt, 0) + 1
    for gt, n in counts.items():
        print(f"  {gt}: {n} files")

    # Run evaluation
    t0 = time.monotonic()
    results = evaluate_batch(sampled, calibration_mode=args.calibration_mode)
    elapsed = time.monotonic() - t0

    print(f"\nEvaluation completed in {elapsed:.1f}s ({elapsed / len(sampled):.2f}s/file)")

    # Aggregate stats
    aggregate = compute_aggregate_stats(results)

    # Print summary
    print_summary(aggregate)

    # Save JSON results
    if args.output:
        output_data = {
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "seed": args.seed,
                "sample_size": len(sampled),
                "calibration_mode": args.calibration_mode,
                "graph_types": args.graph_types,
                "counts": counts,
                "elapsed_seconds": round(elapsed, 2),
            },
            "per_file_results": [r.to_dict() for r in results],
            "aggregate": aggregate,
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults written to {args.output}")

    # Save HTML report
    if args.html:
        generate_html_report(results, args.html, aggregate=aggregate)
        print(f"HTML report written to {args.html}")


if __name__ == "__main__":
    main()
