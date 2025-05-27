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
import os
import random
import sys
import logging
from typing import Dict, List, Tuple, Any, Set, Optional
from multiprocessing import Pool, cpu_count
from functools import partial

from generate_common import (
    args2level,
    cache_save,
    cache_update,
    get_custom_logger,
)
from datas import metadata, Symmetry, Parameters
from datas.helpers import measurement2distance
from spinorama.load import parse_graphs_speaker, parse_eq_speaker
from spinorama.speaker import print_graphs
from spinorama.plot import plot_params_default

VERSION = "2.07"  # Updated version
ACTIVATE_TRACING: bool = True

# Global variables for parallel processing
global logger, data_dir, force, args

# Set up logger
logger = logging.getLogger("spinorama")

def tracing(msg: str):
    """Debugging utility for tracing execution"""
    if ACTIVATE_TRACING:
        print(f"---- TRACING ---- {msg} ----")

def get_speaker_list(speakerpath: str) -> Set[str]:
    """Return a list of speakers from data subdirectory"""
    speakers = []
    dirs = glob.glob(speakerpath + "/*")
    for current_dir in dirs:
        shortname = os.path.basename(current_dir)
        if os.path.isdir(current_dir) and shortname not in (
            "assets", "compare", "stats", "pictures", "tmp",
        ):
            speakers.append(shortname)
    return set(speakers)

def process_single_measurement(
    speaker_info: Tuple[str, str, Dict[str, Any], int, str, bool]
) -> Tuple[bool, str, str, Dict[str, Any], Optional[Exception]]:
    """Process a single measurement (worker function for parallel processing)"""
    speaker, mversion, measurement, level, data_dir, force = speaker_info
    
    try:
        # Extract parameters
        mformat = measurement["format"]
        morigin = measurement["origin"]
        brand = metadata.speakers_info[speaker]["brand"]
        shape = metadata.speakers_info[speaker]["shape"]
        msymmetry = measurement.get("symmetry", None)
        mparameters = measurement.get("parameters", None)
        distance = measurement2distance(speaker, measurement)
        
        parameters = {
            "mformat": mformat,
            "morigin": morigin,
            "mversion": mversion,
            "msymmetry": msymmetry,
            "mparameters": mparameters,
            "level": level,
            "distance": distance,
            "shape": shape,
            "width": int(plot_params_default["width"]),
            "height": int(plot_params_default["height"]),
        }
        
        # Process graphs
        df = parse_graphs_speaker(
            speaker_path=f"{data_dir}/datas/measurements",
            speaker_brand=brand,
            speaker_name=speaker,
            speaker_parameters=parameters,
        )
        
        # Process EQ
        eq = parse_eq_speaker(
            speaker_path=f"{data_dir}/datas",
            speaker_name=speaker,
            df_ref=df,
            speaker_parameters=parameters,
        )
        
        # Generate graphs
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Generating graphs for %s / %s", speaker, mversion)
        
        g1 = print_graphs(
            df,
            speaker,
            parameters,
            metadata.origins_info,
            force,
        )
        
        # Generate EQ graphs
        parameters_eq = parameters.copy()
        parameters_eq["mversion_key"] = mversion + "_eq"
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Generating EQ graphs for %s / %s", speaker, parameters_eq["mversion_key"])
        
        g2 = print_graphs(
            eq,
            speaker,
            parameters_eq,
            metadata.origins_info,
            force,
        )
        
        return True, speaker, mversion, {"df": df, "eq": eq}, None
        
    except Exception as e:
        logger.error("Error processing %s/%s: %s", speaker, mversion, str(e))
        return False, speaker, mversion, {}, e

def process_measurements_parallel(
    speakerlist: Set[str], 
    filters: Dict[str, str], 
    level: int,
    num_processes: Optional[int] = None
) -> Dict[str, Any]:
    """Process measurements in parallel using multiprocessing"""
    if num_processes is None:
        num_processes = max(1, cpu_count() - 1)
    
    # Prepare tasks
    tasks = []
    for speaker in speakerlist:
        if "speaker" in filters and speaker != filters["speaker"]:
            logger.debug("skipping %s", speaker)
            continue
            
        if speaker not in metadata.speakers_info:
            logger.error("Metadata error: %s", speaker)
            continue
            
        for mversion, measurement in metadata.speakers_info[speaker]["measurements"].items():
            # Apply filters
            if "mversion" in filters and not (
                mversion == filters["mversion"] or mversion == "{}_eq".format(filters["mversion"])
            ):
                logger.debug("skipping %s/%s", speaker, mversion)
                continue
                
            mformat = measurement["format"]
            if "format" in filters and mformat != filters["format"]:
                logger.debug("skipping %s/%s/%s", speaker, mformat, mversion)
                continue
                
            morigin = measurement["origin"]
            if "origin" in filters and morigin != filters["origin"]:
                logger.debug("skipping %s/%s/%s/%s", speaker, morigin, mformat, mversion)
                continue
                
            tasks.append((speaker, mversion, measurement, level, data_dir, force))
    
    logger.info("Processing %d measurements using %d processes", len(tasks), num_processes)
    
    # Process tasks in parallel
    data_frame = {}
    success_count = 0
    error_count = 0
    
    with Pool(processes=num_processes) as pool:
        for i, (success, speaker, mversion, result, error) in enumerate(
            pool.imap_unordered(process_single_measurement, tasks, chunksize=1)
        ):
            if success:
                if speaker not in data_frame:
                    data_frame[speaker] = {}
                
                morigin = result["df"].get("morigin", "unknown")
                if morigin not in data_frame[speaker]:
                    data_frame[speaker][morigin] = {}
                
                data_frame[speaker][morigin][mversion] = result["df"]
                data_frame[speaker][morigin][f"{mversion}_eq"] = result["eq"]
                success_count += 1
            else:
                logger.error("Failed to process %s/%s: %s", speaker, mversion, str(error))
                error_count += 1
            
            # Log progress
            if (i + 1) % 10 == 0 or (i + 1) == len(tasks):
                logger.info("Processed %d/%d measurements (%d errors)", 
                           i + 1, len(tasks), error_count)
    
    logger.info("Completed processing: %d succeeded, %d failed", success_count, error_count)
    return data_frame

def main(level):
    """Main function to process speakers and generate graphs"""
    global data_dir, force
    
    # Set global variables
    data_dir = args.data_dir
    force = args.force
    
    # Get speaker list
    speakerlist = get_speaker_list(f"{data_dir}/datas/measurements")
    
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
    for ifilter_key in ("speaker", "origin", "mversion", "brand"):
        value = getattr(args, ifilter_key, None)
        if value is not None:
            filters[ifilter_key] = value

    # Process measurements in parallel
    df_new = process_measurements_parallel(speakerlist, filters, level)

    # Update cache if needed
    if not filters:  # Only update cache if no filters are applied
        cache_save(df_new)
    elif args.update_cache:
        cache_update(df_new, filters, level)
    
    logger.info("Graph generation completed successfully")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate spinorama graphs from measurement data.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--version", action="version", version=f"generate_graphs_mp.py v{VERSION}")
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
    parser.add_argument("--data-dir", default=".", help="Directory where data is stored (default: .)")
    parser.add_argument("--update-cache", action="store_true", help="Force updating the cache")
    parser.add_argument("--processes", type=int, help="Number of processes to use (default: CPU count - 1)")

    args = parser.parse_args()
    
    # Set up logging
    LEVEL = args2level(args)
    logger = get_custom_logger(level=LEVEL, duplicate=True)
    
    # Run main function
    sys.exit(main(LEVEL))
