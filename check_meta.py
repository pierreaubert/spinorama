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
usage: check_meta.py [--help] [--version]

Options:
  --help            display usage()
  --version         script version number
"""
import logging
import json
import sys
import datas.metadata as metadata


def sanity_check_brand(name, speaker):
    if 'brand' not in speaker:
        logging.error('brand is not in {0}'.format(name))
        return 1
    else:
        brand = speaker['brand']
        if name[0:len(brand)] != brand:
            logging.error('{0} doesn\'t start with {1}'.format(name, brand))
            return 1
    return 0


def sanity_check_model(name, speaker):
    if 'model' not in speaker:
        logging.error('model is not in {0}'.format(name))
        return 1
    else:
        brand = speaker['brand']
        model = speaker['model']
        name_split = model.split(' ')
        if len(name_split) > 0 and name_split[0] == brand:
            logging.warning('{0} does start with brand {1}'.format(name, brand))
            return 1
        if name[-len(model):] != model:
            logging.error('{0} doesn\'t end with {1}'.format(name, model))
            return 1
    return 0


def sanity_check_type(name, speaker):
    if 'type' not in speaker:
        logging.error('type is not in {0}'.format(name))
        return 1
    else:
        thetype = speaker['type']
        if thetype not in ('active', 'passive'):
            logging.error('{0}: type {1} is not allowed'.format(name, thetype))
            return 1
    return 0


def sanity_check_shape(name, speaker):
    if 'shape' not in speaker:
        logging.error('shape is not in {0}'.format(name))
        return 1
    else:
        theshape = speaker['shape']
        if theshape not in ('floorstanders', 'bookshelves', 'center', 'surround', 'omnidirectional'):
            logging.error('{0}: shape {1} is not allowed'.format(name, theshape))
            return 1
    return 0

            
def sanity_check_default_measurement(name, speaker):
    if 'default_measurement' not in speaker:
        logging.error('default_measurement is not in {0}'.format(name))
        return 1
    else:
        default = speaker['default_measurement']
        if 'measurements' in speaker and default not in speaker['measurements'].keys():
            logging.error('{0}: no measurement with key {1}'.format(name, default))
            return 1
    return 0


def sanity_check_measurement(name, speaker, version, measurement):
    status = 0
    if version[0:3] not in ('asr', 'pri', 'ven', 'har', 'eac', 'mis'):
        logging.error('{0}: key {1} doesn\'t look correct'.format(name, version))
        status = 1
    for k, v in measurement.items():
        if k not in ('origin', 'format', 'review', 'website', 'misc'):
            logging.error('{0}: version {1} : {2} is not known'.format(name, version, k))
            status = 1
        if k == 'origin' and \
          (v not in ['ASR', 'Misc', 'ErinsAudioCorner', 'Princeton'] \
           and v[0:8] != 'Vendors-'):
            logging.error('{0}: origin {1} is not known'.format(name, v))
            status = 1
        if k == 'format' and v not in ['klippel', 'princeton', 'webplotdigitizer', 'rewstextdump', 'splHVtxt']:
            logging.error('{0}: format {1} is not known'.format(name, v))
            status = 1
    return status
        

def sanity_check_measurements(name, speaker):
    status = 0
    if 'measurements' not in speaker:
        logging.error('measurements is not in {0}'.format(name))
        status = 1
    else:
        for version, measurement in speaker['measurements'].items():
            if sanity_check_measurement(name, speaker, version, measurement) != 0:
                status = 1
    return status

    
def sanity_check_speaker(name, speaker):
    if sanity_check_brand(name, speaker) != 0 or \
       sanity_check_model(name, speaker) != 0 or \
       sanity_check_type(name, speaker) != 0 or \
       sanity_check_shape(name, speaker) != 0 or \
       sanity_check_measurements(name, speaker) != 0 or \
       sanity_check_default_measurement(name, speaker) != 0:
        return 1
    return 0


def sanity_check_speakers(speakers):
    status = 0
    for name, speaker in speakers.items():
        if sanity_check_speaker(name, speaker) != 0:
            status = 1
    return status


if __name__ == '__main__':
    status = sanity_check_speakers(metadata.speakers_info)
    sys.exit(status)
