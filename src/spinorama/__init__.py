# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

import logging
import sys

# global variable
logger = logging.getLogger("spinorama")


def ray_setup_logger(level=logging.WARNING):
    """Since ray execution is remote, the logger needs to be instanciated and
    configured in each process
    """
    custom_file_handler = logging.FileHandler("debug_optim.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    custom_file_handler.setFormatter(formatter)
    logger.addHandler(custom_file_handler)
    custom_stream_handler = logging.StreamHandler(sys.stdout)
    custom_stream_handler.setFormatter(formatter)
    logger.addHandler(custom_stream_handler)
    logger.setLevel(level)
