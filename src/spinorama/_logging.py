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

"""Centralized logger setup for spinorama and its subpackages.

Ray executes work in remote processes, so loggers must be (re)configured per
process. Callers call ``setup_logger`` once per process before logging.
"""

import logging
import sys

logger = logging.getLogger("spinorama")

DEFAULT_LOG_PATH = "build/debug_spin.log"
_LOG_FORMAT = "%(asctime)s - %(filename)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
_HANDLER_ATTR = "_spinorama_handler"


def close_logger() -> None:
    """Remove and close handlers installed by :func:`setup_logger`."""
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_ATTR, False):
            logger.removeHandler(handler)
            handler.close()


def setup_logger(level: int = logging.WARNING, path: str = DEFAULT_LOG_PATH) -> None:
    """Attach a file + stdout handler to the shared ``spinorama`` logger.

    Safe to call from any process (incl. ray workers).
    """
    close_logger()

    formatter = logging.Formatter(_LOG_FORMAT)
    file_handler = logging.FileHandler(path)
    file_handler.setFormatter(formatter)
    setattr(file_handler, _HANDLER_ATTR, True)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    setattr(stream_handler, _HANDLER_ATTR, True)
    logger.addHandler(stream_handler)
    logger.setLevel(level)
