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
update-graphs.py [-h|--help] [-v] [--width=<width>] [--height=<height>]\
  [--force] [--type=<ext>] [--log-level=<level>] [--origin=<origin>]\
  [--speaker=<speaker>] [--only-compare=<compare>]

Options:
  -h|--help         display usage()
  --width=<width>   width size in pixel
  --height=<height> height size in pixel
  --force           force regeneration of all graphs, by default only generate new ones
  --type=<ext>      choose one of: json, html, png, svg
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --origin=<origin> restrict to a specific origin, usefull for debugging
  --speaker=<speaker> restrict to a specific speaker, usefull for debugging
  --only-compare=<compare> if true then skip graphs generation and only dump compare data
"""
import logging
import datas.metadata as metadata
from docopt import docopt
from src.spinorama.load.parse import parse_all_speakers, parse_graphs_speaker
from src.spinorama.print import print_graphs, print_compare


def generate_graphs(df, width, height, force, ptype):
    for speaker_name, speaker_data in df.items():
        for origin, dataframe in speaker_data.items():
            key = 'default'
            logging.debug('{:30s} {:20s} {:20s}'.format(speaker_name, origin, key))
            dfs = df[speaker_name][origin][key]
            updated = print_graphs(dfs,
                                   speaker_name, origin, metadata.origins_info, key,
                                   width, height, force, ptype)
            print('{:30s} {:2d}'.format(speaker_name, updated))


def generate_compare(df, width, height, force, ptype):
    print_compare(df, force, ptype)


if __name__ == '__main__':
    args = docopt(__doc__,
                  version='generate_raphs.py version 1.18',
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

    level = None
    if args['--log-level'] is not None:
        check_level = args['--log-level']
        if check_level in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
            level = check_level

    if level is not None:
        logging.basicConfig(
            format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d:%H:%M:%S',
            level=level)
    else:
        logging.basicConfig(
            format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d:%H:%M:%S')

    df = None
    if args['--speaker'] is not None and args['--origin'] is not None:
        speaker = args['--speaker']
        origin = args['--origin']
        mformat = None
        if origin == 'Princeton':
            mformat = 'princeton'
        elif origin == 'ASR':
            mformat = 'klippel'
        else:
            # need to get this information from meta
            mformat = metadata.speakers_info[speaker]['measurements'][0]['format']
        brand = metadata.speakers_info[speaker]['brand']
        df = {}
        df[speaker] = {}
        df[speaker][origin] = {}
        df[speaker][origin]['default'] = parse_graphs_speaker(brand, speaker, mformat)
        print('Speaker                         #updated')
        generate_graphs(df, width, height, force, ptype=ptype)
    else:
        origin = None
        if args['--origin'] is not None:
            origin = args['--origin']

        df = parse_all_speakers(metadata.speakers_info, origin)
        if args['--only-compare'] is not True:
            generate_graphs(df, width, height, force, ptype=ptype)

    if args['--speaker'] is None and args['--origin'] is None:
        generate_compare(df, width, height, force, ptype=ptype)
