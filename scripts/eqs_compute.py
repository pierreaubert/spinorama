#!/usr/bin/env python3
#                                                   -*- coding: utf-8 -*-
# A script to compute EQs using multiprocessing
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
Usage: eqs_compute.py [speaker1 speaker2 ...]

This script computes EQs for the specified speakers using multiprocessing.
If no speakers are specified, it will compute EQs for all speakers.
"""

import os
import sys
import subprocess
import multiprocessing
from typing import Optional
import argparse
import platform
import shutil
from pathlib import Path

# Global configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
GENERATE_PEQS = os.path.join(ROOT_DIR, "generate_peqs.py")
LOG_LEVEL = "INFO"


def setup_directories() -> None:
    """Set up the necessary directories for temporary files."""
    temp_dir = os.path.join(ROOT_DIR, "build")
    os.makedirs(temp_dir, exist_ok=True)


def compute_eq(params: tuple[int, str, str, str, str]) -> tuple[bool, str]:
    """
    Compute EQ for a single configuration.

    Args:
        params: A tuple containing (max_peq, fitness, speaker, extra_args, output_dir)

    Returns:
        A tuple of (success, message)
    """
    max_peq, fitness, speaker, extra_args, output_dir = params

    # Build the command
    cmd = [
        sys.executable,
        GENERATE_PEQS,
        "--verbose",
        "--force",
        f"--log-level={LOG_LEVEL}",
        "--optimisation=global",
        "--max-iter=15000",
        f"--speaker={speaker}",
        f"--max-peq={max_peq}",
        f"--fitness={fitness}",
        f"--output-dir={output_dir}",
    ]

    # Add extra arguments if provided
    if extra_args:
        cmd.extend(extra_args.split())

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Run the command
    # Use Path for better cross-platform compatibility
    output_path = Path(output_dir)
    log_file = output_path.parent / f"{output_path.name}.log"
    try:
        with open(log_file, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=f, text=True, check=True)
            if result.returncode == 0:
                return (True, f"Successfully processed {speaker} with {fitness} and {max_peq} PEQs")
            else:
                return (
                    False,
                    f"Failed to process {speaker} with {fitness} and {max_peq} PEQs: return code {result.returncode}",
                )
    except subprocess.CalledProcessError as e:
        return (False, f"Failed to process {speaker} with {fitness} and {max_peq} PEQs: {e}")


def generate_workloads(speakers: list[str]) -> list[tuple[int, str, str, str, str]]:
    """
    Generate all the EQ computation workloads.

    Args:
        speakers: List of speaker names to process

    Returns:
        A list of tuples containing the parameters for each computation
    """
    workloads = []

    # Base output directory
    base_output_dir = os.path.join(ROOT_DIR, "build", "eqs")

    for speaker in speakers:
        # Generate all the different configurations for each speaker

        # Flat fitness
        for peq in [3, 4, 5, 6, 7]:
            # Flat with default settings
            output_dir = os.path.join(base_output_dir, speaker, f"Flat-{peq}-none-pk")
            workloads.append((peq, "Flat", speaker, "", output_dir))

            # Flat with smoothing 7,3
            output_dir = os.path.join(base_output_dir, speaker, f"Flat-{peq}-sw7o3-pk")
            workloads.append(
                (peq, "Flat", speaker, "--smooth-measurements=7 --smooth-order=3", output_dir)
            )

            # Flat with smoothing 11,3
            output_dir = os.path.join(base_output_dir, speaker, f"Flat-{peq}-sw11o3-pk")
            workloads.append(
                (peq, "Flat", speaker, "--smooth-measurements=11 --smooth-order=3", output_dir)
            )

            # Flat with smoothing 21,5
            output_dir = os.path.join(base_output_dir, speaker, f"Flat-{peq}-sw21o5-pk")
            workloads.append(
                (peq, "Flat", speaker, "--smooth-measurements=21 --smooth-order=5", output_dir)
            )

        # Score fitness
        for peq in [3, 4, 5, 6, 7]:
            # Score with default settings
            output_dir = os.path.join(base_output_dir, speaker, f"Score-{peq}-none-pk")
            workloads.append((peq, "Score", speaker, "", output_dir))

            # Score with smoothing 5,3
            output_dir = os.path.join(base_output_dir, speaker, f"Score-{peq}-sw5o3-pk")
            workloads.append(
                (peq, "Score", speaker, "--smooth-measurements=5 --smooth-order=3", output_dir)
            )

            # Score with smoothing 7,3
            output_dir = os.path.join(base_output_dir, speaker, f"Score-{peq}-sw7o3-pk")
            workloads.append(
                (peq, "Score", speaker, "--smooth-measurements=7 --smooth-order=3", output_dir)
            )

            # Score with smoothing 9,3
            output_dir = os.path.join(base_output_dir, speaker, f"Score-{peq}-sw9o3-pk")
            workloads.append(
                (peq, "Score", speaker, "--smooth-measurements=9 --smooth-order=3", output_dir)
            )

            # Score with smoothing 11,3
            output_dir = os.path.join(base_output_dir, speaker, f"Score-{peq}-sw11o3-pk")
            workloads.append(
                (peq, "Score", speaker, "--smooth-measurements=11 --smooth-order=3", output_dir)
            )

            # Score with smoothing 21,5 (only for peq 4-7)
            if peq >= 4:
                output_dir = os.path.join(base_output_dir, speaker, f"Score-{peq}-sw21o5-pk")
                workloads.append(
                    (peq, "Score", speaker, "--smooth-measurements=21 --smooth-order=5", output_dir)
                )

    return workloads


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Compute EQs using multiprocessing")
    parser.add_argument("speakers", nargs="*", help="List of speakers to process (default: all)")
    parser.add_argument(
        "--processes",
        type=int,
        default=multiprocessing.cpu_count(),
        help=f"Number of processes to use (default: {multiprocessing.cpu_count()})",
    )
    args = parser.parse_args()
    speakers = args.speakers if args.speakers else []
    setup_directories()

    # Generate all workloads
    workloads = generate_workloads(speakers)

    print(
        f"Starting processing of {len(workloads)} EQ configurations using {args.processes} processes..."
    )

    # Process workloads in parallel
    with multiprocessing.Pool(processes=args.processes) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(compute_eq, workloads), 1):
            success, message = result
            status = "✓" if success else "✗"
            print(f"[{i}/{len(workloads)}] {status} {message}")
            results.append((success, message))

    # Print summary
    success_count = sum(1 for success, _ in results if success)
    failure_count = len(results) - success_count

    print("\n=== Summary ===")
    print(f"Total tasks: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")

    if failure_count > 0:
        print("\nFailed tasks:")
        for success, message in results:
            if not success:
                print(f"  - {message}")

    print("\nAll tasks completed!")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
