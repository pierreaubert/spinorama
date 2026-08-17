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

"""usage: check_meta.py [--help] [--version].

Options:
  --help            display usage()
  --version         script version number
"""

import logging
import sys
from pathlib import Path
from typing import cast, Dict, Any

from datas import speaker as metadata
from datas.checks import VALID_FORMATS, ValidationResult, validate_speaker_database
from datas.helpers import measurement2distance
from spinorama import constant_paths as cpaths
from spinorama._logging import close_logger
from spinorama.misc import sanitize_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def validate_measurement_files(
    speakers: Dict[str, Dict[str, Any]],
    measurements_dir: str = cpaths.CPATH_DATAS_SPEAKERS,
    loader: Any | None = None,
) -> ValidationResult:
    """Validate that every metadata measurement exists and can be loaded."""
    result = ValidationResult()
    measurements_root = Path(measurements_dir)

    if loader is None:
        try:
            from spinorama.load import parse_graphs_speaker as loader
        except ImportError as exc:
            result.add_error(f"Measurement loader dependencies are unavailable: {exc}")
            return result

    for speaker_name, speaker_data in speakers.items():
        if not isinstance(speaker_data, dict):
            continue
        if speaker_data.get("skip") is True:
            continue

        measurements = speaker_data.get("measurements")
        if not isinstance(measurements, dict):
            continue

        brand = speaker_data.get("brand")
        shape = speaker_data.get("shape")
        if not isinstance(brand, str) or not isinstance(shape, str):
            continue

        filesystem_speaker_name = sanitize_filename(speaker_name)
        for measurement_key, measurement in measurements.items():
            if not isinstance(measurement_key, str) or not isinstance(measurement, dict):
                continue

            measurement_format = measurement.get("format")
            origin = measurement.get("origin")
            if measurement_format not in VALID_FORMATS or not isinstance(origin, str):
                continue

            measurement_path = measurements_root / filesystem_speaker_name / measurement_key
            if not measurement_path.is_dir():
                result.add_error(
                    f"Measurement directory is missing for '{measurement_key}' in "
                    f"{speaker_name}: {measurement_path}"
                )
                continue

            try:
                parameters = {
                    "mformat": measurement_format,
                    "morigin": origin,
                    "mversion": measurement_key,
                    "msymmetry": measurement.get("symmetry"),
                    "mparameters": measurement.get("parameters"),
                    "distance": measurement2distance(speaker_name, measurement),
                    "shape": shape,
                }
                loaded = loader(
                    speaker_path=str(measurements_root),
                    speaker_brand=brand,
                    speaker_name=filesystem_speaker_name,
                    speaker_parameters=parameters,
                    log_level=logging.ERROR,
                )
            except Exception as exc:
                result.add_error(
                    f"Measurement '{measurement_key}' in {speaker_name} could not be loaded: {exc}"
                )
            else:
                if loaded is None or loaded.is_empty():
                    result.add_error(
                        f"Measurement '{measurement_key}' in {speaker_name} could not be loaded"
                    )
            finally:
                close_logger()

    return result


def main() -> int:
    """Main function to validate all speaker metadata."""
    logging.info("Starting speaker metadata validation...")

    # Cast the speakers_info to the expected type for validation
    speakers_dict = cast(Dict[str, Dict[str, Any]], metadata.speakers_info)

    # Validate the entire speaker database
    result = validate_speaker_database(speakers_dict)
    file_result = validate_measurement_files(speakers_dict)
    result.valid = result.valid and file_result.valid
    result.messages.extend(file_result.messages)

    # Log all validation messages
    for message in result.messages:
        if message.startswith("ERROR:"):
            logging.error(message[7:])  # Remove "ERROR: " prefix
        elif message.startswith("WARNING:"):
            logging.warning(message[9:])  # Remove "WARNING: " prefix
        else:
            logging.info(message)

    # Return status based on validation result
    if result.valid:
        logging.info("All speaker metadata validation passed!")
        return 0
    else:
        logging.error("Speaker metadata validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
