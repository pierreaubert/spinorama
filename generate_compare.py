#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
usage: generate_compare.py [--help] [--version] [--smoke-test] [--log-level=<level>]

Options:
  --help            display usage()
  --version         script version number
  --smoke-test             Test the optimiser with a small amount of variables
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import sys

from docopt import docopt

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray

from generate_common import get_custom_logger, args2level, cache_load
from src.spinorama.speaker_print import print_compare


ray.init()


if __name__ == "__main__":
    args = docopt(
        __doc__, version="generate_compare.py version 1.2", options_first=True
    )

    level = args2level(args)
    logger = get_custom_logger(True)
    logger.setLevel(level)

    smoke_test = args.get("smoke-test", False)
    df = cache_load(smoke_test=smoke_test)
    if df is None:
        logger.error("Load failed! Please run ./generate_graphs.py")
        sys.exit(1)
    force = True
    ptype = None
    print_compare(df, force, ptype)

    logger.info("Bye")
    sys.exit(0)
