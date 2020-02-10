#!/usr/bin/env python
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

"""Usage: update-graphs.py [-v] [-f] [--width=SIZE] [--heigth=SIZE]

Options:
  --width=<width>   width size in pixel
  --heigth=<heigth> heigth size in pixel
  -f                   force regeneration of all graphs, by default only generate new ones
"""
from src.spinorama.load import parse_all_speakers
from src.spinorama.graph import print_graphs

from docopt import docopt

if __name__ == '__main__':
    args = docopt(__doc__,
                  version='update-graphs.py version 1.0',
                  options_first=True)
    
    width = 900
    heigth = 500
    force = args['-f']

    if args['--width'] is not None:
        width = int(args['--width'])

    if args['--heigth'] is not None:
        heigth = int(args['--heigth'])

    df = parse_all_speakers()
    for (speaker, measurements) in df.items():
        print_graphs(df, speaker, width, heigth, force)
