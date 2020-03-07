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
usage: generate_meta.py [--help] [--version] [--log-level=<level>]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import os
import math
import sys
import json
import logging
from src.spinorama.load import parse_all_speakers, parse_graphs_speaker
from src.spinorama.analysis import estimates, speaker_pref_rating
import datas.metadata as metadata
from docopt import docopt

def sanity_check(df, meta):
    for speaker_name, origins in df.items():
        # check if metadata exists
        if speaker_name not in meta:
            logging.error('Metadata not found for >{:s}<'.format(speaker_name))
            return 1
        # check if each measurement looks reasonable
        for origin, keys in origins.items():
            if origin not in ['ASR', 'Princeton'] and origin[0:8] != 'Vendors/':
                logging.error('Measurement origin >{:s}< is unkown for >{:s}'.format(origin, speaker_name))
                return 1
            if 'default' not in keys.keys():
                logging.error('Key default is mandatory for >{:s}<'.format(speaker_name))
                return 1
        # check if image exists
        if not os.path.exists('./datas/pictures/' + speaker_name + '.jpg'):
            print('Fatal: Image associated with >', speaker_name, '< not found!')
            return 1
        # check if downscale image exists
        if not os.path.exists('./docs/pictures/' + speaker_name + '.jpg'):
            print('Fatal: Image associated with >', speaker_name, '< not found!')
            print('Please run: cd docs && ./convert.sh')
            return 1
    return 0


def add_estimates(df):
    """""Compute some values per speaker and add them to metadata """
    min_pref_score = -10
    max_pref_score = 20
    min_lfx_hz = 0
    max_lfx_hz = 1000
    min_nbd_on = 0
    max_nbd_on = 1
    min_flatness = 0
    max_flatness = 100
    for speaker_name, speaker_data in df.items():
        for origin, measurements in speaker_data.items():
            if origin != 'ASR':
                # this measurements are only valid above 500hz
                continue
            for m, dfs in measurements.items():
                if m == 'default':
                    if 'CEA2034' in dfs.keys():
                        spin = dfs['CEA2034']
                        if spin is not None:
                            # basic math
                            onaxis = spin.loc[spin['Measurements'] == 'On Axis']
                            est = estimates(onaxis)
                            if est[0] == -1:
                                continue
                            logging.info('Adding -3dB {:d}Hz -6dB {:d}Hz +/-{:f}dB'.format(est[1], est[2], est[3]))
                            metadata.speakers_info[speaker_name]['estimates'] = est
                            min_flatness = min(est[3], min_flatness)
                            max_flatness = max(est[3], max_flatness)
                            # from Olive&all paper
                            pref_rating = speaker_pref_rating(spin)
                            logging.info('Adding {0}'.format(pref_rating))
                            metadata.speakers_info[speaker_name]['pref_rating'] = pref_rating
                            # compute min and max for each value
                            min_pref_score = min(min_pref_score, pref_rating['pref_score'])
                            max_pref_score = max(max_pref_score, pref_rating['pref_score'])
                            min_lfx_hz = min(min_lfx_hz, pref_rating['lfx_hz'])
                            max_lfx_hz = max(max_lfx_hz, pref_rating['lfx_hz'])
                            min_nbd_on = min(min_nbd_on, pref_rating['nbd_on'])
                            max_nbd_on = max(max_nbd_on, pref_rating['nbd_on'])
                            
    # add normalized value to metadata
    for speaker_name, speaker_data in df.items():
        for origin, measurements in speaker_data.items():
            if origin != 'ASR':
                # this measurements are only valid above 500hz
                continue
            for m, dfs in measurements.items():
                if m == 'default':
                    if 'CEA2034' in dfs.keys():
                        spin = dfs['CEA2034']
                        if spin is not None and \
                            'pref_rating' in metadata.speakers_info[speaker_name].keys() and \
                            'estimates' in metadata.speakers_info[speaker_name].keys() and \
                            metadata.speakers_info[speaker_name]['estimates'][0] != -1:
                            # get values
                            pref_rating = metadata.speakers_info[speaker_name]['pref_rating']
                            pref_score = pref_rating['pref_score']
                            lfx_hz = pref_rating['lfx_hz']
                            nbd_on = pref_rating['nbd_on']
                            flatness = metadata.speakers_info[speaker_name]['estimates'][3]
                            # normalize min and max
                            scaled_pref_score = math.floor(100*(pref_score-min_pref_score)/(max_pref_score-min_pref_score))
                            scaled_lfx_hz = math.floor(100*(lfx_hz-min_lfx_hz)/(max_lfx_hz-min_lfx_hz))
                            scaled_nbd_on = math.floor(100*(nbd_on-min_nbd_on)/(max_nbd_on-min_nbd_on))
                            scaled_flatness = math.floor(100*(flatness-min_flatness)/(max_flatness-min_flatness))
                            # add normalized values
                            scaled_pref_rating = {
                                'scaled_pref_score': scaled_pref_score,
                                'scaled_lfx_hz': scaled_lfx_hz,
                                'scaled_nbd_on': scaled_nbd_on,
                                'scaled_flatness': scaled_flatness,
                            }
                            logging.info('Adding {0}'.format(scaled_pref_rating))
                            metadata.speakers_info[speaker_name]['scaled_pref_rating'] = scaled_pref_rating


def dump_metadata(meta):
    with open('docs/assets/metadata.json', 'w') as f:
        js = json.dumps(meta)
        f.write(js)
        f.close()


if __name__ == '__main__':
    args = docopt(__doc__,
                  version='generate_meta.py version 1.0',
                  options_first=True)

    # check args section
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S')
    if args['--log-level'] is not None:
        level = args['--log-level']
        if level in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
            logging.basicConfig(level=level)

    df = parse_all_speakers(metadata.speakers_info)
        
    if sanity_check(df, metadata.speakers_info) != 0:
        logging.error('Sanity checks failed!')
        sys.exit(1)

    # add computed data to metadata
    logging.info('Compute estimates per speaker')
    add_estimates(df)

    # write metadata in a json file for easy search
    logging.info('Write metadat')
    dump_metadata(metadata.speakers_info)

    sys.exit(0)
