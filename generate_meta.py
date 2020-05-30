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
usage: generate_meta.py [--help] [--version] [--log-level=<level>]\
    [--origin=<origin>] [--speaker=<speaker>]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --origin=<origin> restrict to a specific origin, usefull for debugging
  --speaker=<speaker> restrict to a specific speaker, usefull for debugging
"""
import logging
import os
import math
import sys
import json
from src.spinorama.load.parse import parse_all_speakers, parse_graphs_speaker
from src.spinorama.estimates import estimates
from src.spinorama.scores import speaker_pref_rating
import datas.metadata as metadata
from docopt import docopt


def sanity_check(df, meta):
    for speaker_name, origins in df.items():
        # check if metadata exists
        if speaker_name not in meta:
            logging.error('Metadata not found for >{0}<'.format(speaker_name))
            return 1
        # check if each measurement looks reasonable
        for origin, keys in origins.items():
            if origin not in ['ASR', 'Princeton'] and origin[0:8] != 'Vendors/':
                logging.error('Measurement origin >{:s}< is unkown for >{:s}'.format(origin, speaker_name))
                return 1
            if 'default' not in keys.keys():
                logging.error('Key default is mandatory for >{:s}<'.format(speaker_name))
                return 1
        # check if image exists (jpg or png)
        if not os.path.exists('./datas/pictures/' + speaker_name + '.jpg') and not os.path.exists('./datas/pictures/' + speaker_name + '.png'):
            logging.error('Image associated with >{0}< not found.'.format(speaker_name))
        # check if downscale image exists (all jpg)
        if not os.path.exists('./docs/pictures/' + speaker_name + '.jpg'):
            logging.fatal('Image associated with >{0}< not found.'.format(speaker_name))
            logging.fatal('Please run: minimise_pictures.sh')
            return 1
    return 0


def add_estimates(df):
    """""Compute some values per speaker and add them to metadata """
    min_pref_score = +100
    max_pref_score = -100
    min_lfx_hz = 1000
    max_lfx_hz = 0
    min_nbd_on = 1
    max_nbd_on = 0
    min_flatness = 100
    max_flatness = 1
    min_sm_sp = 1
    max_sm_sp = 0
    min_sm_pir = 1
    max_sm_pir = 0
    for speaker_name, speaker_data in df.items():
        logging.info('Processing {0}'.format(speaker_name))
        for origin, measurements in speaker_data.items():
            for m, dfs in measurements.items():
                if m != 'default':
                    continue

                if 'CEA2034' not in dfs.keys():
                    continue

                spin = dfs['CEA2034']
                if spin is None:
                    continue

                logging.debug('Compute score for speaker {0}'.format(speaker_name))
                # basic math
                onaxis = spin.loc[spin['Measurements'] == 'On Axis'].reset_index(drop=True)
                est = estimates(onaxis)
                logging.info('Computing estimated for {0}'.format(speaker_name))
                if est is None or est == [-1, -1, -1, -1]:
                    logging.debug('estimated return None for {0}'.format(speaker_name))
                    continue
                if math.isnan(est[0]) or math.isnan(est[1]) or math.isnan(est[2]) or math.isnan(est[3]):
                    logging.error('estimated return NaN for {0}'.format(speaker_name))
                    continue
                logging.info('Adding -3dB {0}Hz -6dB {1}Hz +/-{2}dB'.format(est[1], est[2], est[3]))
                if 'estimates' not in metadata.speakers_info[speaker_name] or origin == 'ASR':
                    metadata.speakers_info[speaker_name]['estimates'] = est

                if origin == 'Princeton':
                    # this measurements are only valid above 500hz
                    continue

                # from Olive&all paper
                if 'Estimated In-Room Response' not in dfs.keys():
                    continue

                inroom = dfs['Estimated In-Room Response']
                if inroom is None:
                    continue

                pref_rating = speaker_pref_rating(spin, inroom)
                if pref_rating is None:
                    continue
                logging.info('Adding {0}'.format(pref_rating))
                metadata.speakers_info[speaker_name]['pref_rating'] = pref_rating
                # compute min and max for each value
                min_flatness = min(est[3], min_flatness)
                max_flatness = max(est[3], max_flatness)
                min_pref_score = min(min_pref_score, pref_rating['pref_score'])
                max_pref_score = max(max_pref_score, pref_rating['pref_score'])
                min_lfx_hz = min(min_lfx_hz, pref_rating['lfx_hz'])
                max_lfx_hz = max(max_lfx_hz, pref_rating['lfx_hz'])
                min_nbd_on = min(min_nbd_on, pref_rating['nbd_on_axis'])
                max_nbd_on = max(max_nbd_on, pref_rating['nbd_on_axis'])
                min_sm_sp = min(min_nbd_on, pref_rating['sm_sound_power'])
                max_sm_sp = max(max_nbd_on, pref_rating['sm_sound_power'])
                min_sm_pir = min(min_nbd_on, pref_rating['sm_pred_in_room'])
                max_sm_pir = max(max_nbd_on, pref_rating['sm_pred_in_room'])

    # if we are looking only after 1 speaker, return
    if len(df.items()) == 1:
        return
    
    # add normalized value to metadata
    for speaker_name, speaker_data in df.items():
        logging.info('Normalize data for {0}'.format(speaker_name))
        for origin, measurements in speaker_data.items():
            for m, dfs in measurements.items():
                if m != 'default':
                    continue
                if 'CEA2034' not in dfs.keys():
                    continue

                spin = dfs['CEA2034']
                if spin is None or 'pref_rating' not in metadata.speakers_info[speaker_name].keys() \
                  or 'estimates' not in metadata.speakers_info[speaker_name].keys() \
                  or metadata.speakers_info[speaker_name]['estimates'][0] == -1:
                    continue

                logging.debug('Compute relative score for speaker {0}'.format(speaker_name))
                # get values
                pref_rating = metadata.speakers_info[speaker_name]['pref_rating']
                pref_score = pref_rating['pref_score']
                lfx_hz = pref_rating['lfx_hz']
                nbd_on = pref_rating['nbd_on_axis']
                sm_sp = pref_rating['sm_sound_power']
                sm_pir = pref_rating['sm_pred_in_room']
                flatness = metadata.speakers_info[speaker_name]['estimates'][3]

                # normalize min and max
                def percent(val, vmin, vmax):
                    if vmax == vmin:
                        logging.debug('max == min')
                    return math.floor(100*(val-vmin)/(vmax-vmin))

                scaled_pref_score = percent(pref_score, min_pref_score, max_pref_score)
                # lower is better
                scaled_lfx_hz = 100-percent(lfx_hz, min_lfx_hz, max_lfx_hz)
                scaled_nbd_on = 100-percent(nbd_on, min_nbd_on, max_nbd_on)
                scaled_flatness = 100-percent(flatness, min_flatness, max_flatness)
                # higher is better
                scaled_sm_sp = percent(sm_sp, min_sm_sp, max_sm_sp)
                scaled_sm_pir = percent(sm_pir, min_sm_pir, max_sm_pir)
                # add normalized values
                scaled_pref_rating = {
                    'scaled_pref_score': scaled_pref_score,
                    'scaled_lfx_hz': scaled_lfx_hz,
                    'scaled_nbd_on_axis': scaled_nbd_on,
                    'scaled_flatness': scaled_flatness,
                    'scaled_sm_sound_power': scaled_sm_sp,
                    'scaled_sm_pred_in_room': scaled_sm_pir,
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
                  version='generate_meta.py version 1.1',
                  options_first=True)

    # check args section
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
            mformat = 'webplotdigitizer'
        brand = metadata.speakers_info[speaker]['brand']
        df = {}
        df[speaker] = {}
        df[speaker][origin] = {}
        df[speaker][origin]['default'] = parse_graphs_speaker(brand, speaker, mformat)
    else:    
        df = parse_all_speakers(metadata.speakers_info, None)

    if sanity_check(df, metadata.speakers_info) != 0:
        logging.error('Sanity checks failed!')
        sys.exit(1)

    # add computed data to metadata
    logging.info('Compute estimates per speaker')
    add_estimates(df)

    # check that json is valid
    #try:
    #    json.loads(metadata.speakers_info)
    #except ValueError as ve:
    #    logging.fatal('Metadata Json is not valid {0}'.format(ve))
    #    sys.exit(1)

    # write metadata in a json file for easy search
    logging.info('Write metadata')
    dump_metadata(metadata.speakers_info)

    logging.info('Bye')
    sys.exit(0)
