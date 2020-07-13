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
    else:
        brand = speaker['brand']
        if name[0:len(brand)] != brand:
            logging.error('{0} doesn\'t start with {1}'.format(name, brand))


def sanity_check_model(name, speaker):
    if 'model' not in speaker:
        logging.error('model is not in {0}'.format(name))
    else:
        model = speaker['model']
        if name[-len(model):] != model:
            logging.error('{0} doesn\'t end with {1}'.format(name, model))


def sanity_check_type(name, speaker):
    if 'type' not in speaker:
        logging.error('type is not in {0}'.format(name))
    else:
        thetype = speaker['type']
        if thetype not in ('active', 'passive'):
            logging.error('{0}: type {1} is not allowed'.format(name, thetype))


def sanity_check_shape(name, speaker):
    if 'shape' not in speaker:
        logging.error('shape is not in {0}'.format(name))
    else:
        theshape = speaker['shape']
        if theshape not in ('floorstanders', 'bookshelves', 'center', 'surround', 'omnidirectional'):
            logging.error('{0}: shape {1} is not allowed'.format(name, theshape))

            
def sanity_check_default_measurement(name, speaker):
    if 'default_measurement' not in speaker:
        logging.error('default_measurement is not in {0}'.format(name))
    else:
        default = speaker['default_measurement']
        if 'measurements' in speaker and default not in speaker['measurements'].keys():
            logging.error('{0}: no measurement with key {1}'.format(name, default))


def sanity_check_measurement(name, speaker, version, measurement):
    if version[0:3] not in ('asr', 'pri', 'ven', 'har'):
        logging.error('{0}: key {1} doesn\'t look correct'.format(name, version))
    for k, v in measurement.items():
        if k not in ('origin', 'format', 'review', 'website'):
            logging.error('{0}: version {1} : {2} is not known'.format(name, version, k))
        

def sanity_check_measurements(name, speaker):
    if 'measurements' not in speaker:
        logging.error('measurements is not in {0}'.format(name))
    else:
        for version, measurement in speaker['measurements'].items():
            sanity_check_measurement(name, speaker, version, measurement)


    
def sanity_check_speaker(name, speaker):
    sanity_check_brand(name, speaker)
    sanity_check_model(name, speaker)
    sanity_check_type(name, speaker)
    sanity_check_shape(name, speaker)
    sanity_check_measurements(name, speaker)
    sanity_check_default_measurement(name, speaker)
            

def sanity_check_speakers(speakers):
    for name, speaker in speakers.items():
        sanity_check_speaker(name, speaker)


if __name__ == '__main__':
    sanity_check_speakers(metadata.speakers_info)
    sys.exit(0)
