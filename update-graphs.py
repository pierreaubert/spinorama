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
"""Usage: 
  update-graphs.py [-v] [--width=SIZE] [--heigth=SIZE] [--force] [--type=<ext>]

Options:
  --width=<width>   width size in pixel
  --heigth=<heigth> heigth size in pixel
  --force           force regeneration of all graphs, by default only generate new ones
  --type=<ext>      choose one of: json, html, png, svg
"""
from src.spinorama.load import parse_all_speakers
from src.spinorama.graph import print_graphs

from docopt import docopt

if __name__ == '__main__':
    args = docopt(__doc__,
                  version='update-graphs.py version 1.0',
                  options_first=True)

    width = 1200
    heigth = 600
    force = args['--force']
    type = None

    if args['--width'] is not None:
        width = int(args['--width'])

    if args['--heigth'] is not None:
        heigth = int(args['--heigth'])

    if args['--type'] is not None:
        type = args['--type']
        if type not in ('png', 'html', 'svg', 'json'):
            print('type %s is not recognize!'.format(type))
            exit(1)

    df = parse_all_speakers()
    for (speaker, measurements) in df.items():
        print_graphs(df, speaker, width, heigth, force, type)
