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
from typing import cast, Dict, Any

from datas import metadata
from datas.checks import validate_speaker_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def main() -> int:
    """Main function to validate all speaker metadata."""
    logging.info("Starting speaker metadata validation...")

    # Cast the speakers_info to the expected type for validation
    speakers_dict = cast(Dict[str, Dict[str, Any]], metadata.speakers_info)

    # Validate the entire speaker database
    result = validate_speaker_database(speakers_dict)

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
