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
"""Usage:
  update-graphs.py [-h|--help] [-v] [--width=<width>] [--height=<height>] [--force] [--type=<ext>]

Options:
  -h|--help         display usage()
  --width=<width>   width size in pixel
  --height=<height> height size in pixel
  --force           force regeneration of all graphs, by default only generate new ones
  --type=<ext>      choose one of: json, html, png, svg
"""
import datas.metadata as metadata
from src.spinorama.load import parse_all_speakers
from src.spinorama.print import print_graphs

from docopt import docopt


def generate_graphs(df, width, height, force, ptype):
    print('Speaker                         #updated')
    for speaker_name, speaker_data in df.items():
        for origin, dataframe in speaker_data.items():
            key = 'default'
            # print('{:30s} {:20s} {:20s}'.format(speaker_name, origin, key))
            updated = print_graphs(df, speaker_name, origin, key, width, height, force, ptype)
    print('{:30s} {:2d}'.format(speaker_name, updated))


if __name__ == '__main__':
    args = docopt(__doc__,
                  version='update-graphs.py version 1.0',
                  options_first=True)

    width = 1200
    height = 600
    force = args['--force']
    ptype = None

    if args['--width'] is not None:
        width = int(args['--width'])

    if args['--height'] is not None:
        height = int(args['--height'])

    if args['--type'] is not None:
        ptype = args['--type']
        if ptype not in ('png', 'html', 'svg', 'json'):
            print('type %s is not recognize!'.format(ptype))
            exit(1)

    df = parse_all_speakers(metadata.speakers_info)
    generate_graphs(df, width, height, force, ptype=ptype)
