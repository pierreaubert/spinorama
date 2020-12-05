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
generate_graphs.py [-h|--help] [-v] [--width=<width>] [--height=<height>]\
  [--force] [--type=<ext>] [--log-level=<level>]\
  [--origin=<origin>]  [--speaker=<speaker>] [--version=<version>] [--brand=<brand>]\
  [--ip=<ip>] [--port=<port>]                                         

Options:
  -h|--help         display usage()
  --width=<width>   width size in pixel
  --height=<height> height size in pixel
  --force           force regeneration of all graphs, by default only generate new ones
  --type=<ext>      choose one of: json, html, png, svg
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --origin=<origin> filter by origin
  --brand=<brand> filter by brand
  --speaker=<speaker> filter by speaker
  --version=<version> filter by measurement
  --ip=<ip>         ip of dashboard to track execution, default to localhost/127.0.0.1
  --port=<port>     port for the dashbboard, default to 8265    
"""
import glob
import ipaddress
import logging
import os
import socket
import sys
import time

from docopt import docopt
import flammkuchen as fl
import pandas as pd
import ray

import datas.metadata as metadata
from src.spinorama.load_parse import parse_graphs_speaker, parse_eq_speaker
from src.spinorama.speaker_print import print_graphs, print_compare
from src.spinorama.graph import graph_params_default


def get_speaker_list(speakerpath : str):
    speakers = []
    asr = glob.glob(speakerpath+'/ASR/*')
    vendors = glob.glob(speakerpath+'/Vendors/*/*')
    misc = glob.glob(speakerpath+'/Misc/*/*')
    princeton = glob.glob(speakerpath+'/Princeton/*')
    ear = glob.glob(speakerpath+'/ErinsAudioCorner/*')
    dirs = asr + vendors + princeton + ear + misc
    for d in dirs:
        if os.path.isdir(d) and d not in ('assets', 'compare', 'stats', 'pictures', 'logos'):
            speakers.append(os.path.basename(d))
    return speakers


def queue_measurement(brand, speaker, mformat, morigin, mversion):
    id_df = parse_graphs_speaker.remote('./datas', brand, speaker, mformat, morigin, mversion)
    id_eq = parse_eq_speaker.remote('./datas', speaker, id_df)
    force = False
    ptype = None
    width = graph_params_default['width']
    height = graph_params_default['height']
    id_g1 = print_graphs.remote(id_df, id_eq, speaker, morigin, metadata.origins_info, mversion, width, height, force, ptype)
    id_g2 = print_graphs.remote(id_eq, id_eq, speaker, morigin, metadata.origins_info, mversion+'_eq', width, height, force, ptype)
    return (id_df, id_eq, id_g1, id_g2)


def queue_speakers(speakerlist, metadata : dict, filters: dict) -> dict:
    ray_ids = {}
    count = 0
    for speaker in speakerlist:
        if 'speaker' in filters and speaker != filters['speaker']:
            logger.debug('skipping {}'.format(speaker))
            continue
        ray_ids[speaker] = {}
        for mversion, measurement in metadata[speaker]['measurements'].items():
            # mversion looks like asr and asr_eq
            if 'version' in filters and not (mversion == filters['version'] or mversion != '{}_eq'.format(filters['version'])):
                logger.debug('skipping {}/{}'.format(speaker, mversion))
                continue
            # filter on format (klippel, princeton, ...)
            mformat = measurement['format']
            if 'format' in filters and mformat != filters['format']:
                logger.debug('skipping {}/{}/{}'.format(speaker, mformat, mversion))
                continue
            # filter on origin (ASR, princeton, ...)
            morigin = measurement['origin']
            if 'origin' in filters and morigin != filters['origin']:
                logger.debug('skipping {}/{}/{}/{}'.format(speaker, morigin, mformat, mversion))
                continue
            # TODO(add filter on brand)
            brand = metadata[speaker]['brand']
            logger.debug('queing {}/{}/{}/{}'.format(speaker, morigin, mformat, mversion))
            ray_ids[speaker][mversion] = queue_measurement(brand, speaker, mformat, morigin, mversion)
            count += 1
    print('Queued {0} speakers {1} measurements'.format(len(speakerlist), count))
    return ray_ids


def compute(speakerkist, metadata, ray_ids):

    df = {}

    done_ids = {}
    
    while(1):
        
        df_ids = [ray_ids[s][v][0] for s in ray_ids.keys() for v in ray_ids[s].keys() if ray_ids[s][v][0] not in done_ids.keys()]
        eq_ids = [ray_ids[s][v][1] for s in ray_ids.keys() for v in ray_ids[s].keys() if ray_ids[s][v][1] not in done_ids.keys()]
        g1_ids = [ray_ids[s][v][2] for s in ray_ids.keys() for v in ray_ids[s].keys() if ray_ids[s][v][2] not in done_ids.keys()]
        g2_ids = [ray_ids[s][v][3] for s in ray_ids.keys() for v in ray_ids[s].keys() if ray_ids[s][v][3] not in done_ids.keys()]
        ids = df_ids + eq_ids + g1_ids + g2_ids
        if len(ids) == 0:
            break
        num_returns = min(len(ids), 16)
        ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)

        logger.info('State: {0} ready IDs {1} remainings IDs {2} Total IDs {3} Done'.format(len(ready_ids), len(remaining_ids), len(ids), len(done_ids)))
        
        for speaker in speakerlist:
            speaker_key = speaker #.translate({ord(ch) : '_' for ch in '-.;/\' '})
            if speaker not in df.keys():
                df[speaker_key] = {}
            for m_version, measurement in metadata[speaker]['measurements'].items():
                m_version_key = m_version #.translate({ord(ch) : '_' for ch in '-.;/\' '})
                m_origin = measurement['origin']
                if m_origin not in df[speaker_key].keys():
                    df[speaker_key][m_origin] = {}

                if speaker not in ray_ids:
                    continue
                
                current_id = ray_ids[speaker][m_version][0]
                if current_id in ready_ids:
                    df[speaker_key][m_origin][m_version_key] = ray.get(current_id)
                    logger.debug('Getting df done for {0} / {1} / {2}'.format(speaker, m_origin, m_version))
                    done_ids[current_id] = True
                
                m_version_eq = '{0}_eq'.format(m_version_key)
                current_id = ray_ids[speaker][m_version][1]
                if current_id in eq_ids:
                    logger.debug('Getting eq done for {0} / {1} / {2}'.format(speaker, m_version_eq, m_version))
                    eq = ray.get(current_id)
                    if eq is not None:
                        df[speaker_key][m_origin][m_version_eq] = eq
                        logger.debug('Getting preamp eq done for {0} / {1} / {2}'.format(speaker, m_version_eq, m_version))
                        if 'preamp_gain' in eq:
                            df[speaker_key][m_origin][m_version_eq]['preamp_gain'] = eq['preamp_gain']
                    done_ids[current_id] = True

                current_id = ray_ids[speaker][m_version][2]
                if current_id in g1_ids:
                    logger.debug('Getting graph done for {0} / {1} / {2}'.format(speaker, m_version, m_origin))
                    ray.get(current_id)
                    done_ids[current_id] = True

                current_id = ray_ids[speaker][m_version][3]
                if current_id in g2_ids:
                    logger.debug('Getting graph done for {0} / {1} / {2}'.format(speaker, m_version_eq, m_origin))
                    ray.get(current_id)
                    done_ids[current_id] = True


        if len(remaining_ids) == 0:
            break
        
    return df

    
if __name__ == '__main__':
    args = docopt(__doc__, version='generate_graphs.py version 1.22', options_first=True)

    # TODO remove it and replace by iterating over metadatas
    speakerlist = get_speaker_list('./datas')

    width = graph_params_default['width']
    height = graph_params_default['height']
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

    logger = logging.getLogger('spinorama')
    fh = logging.FileHandler('debug_graphs.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    if level is not None:
        logger.setLevel(level)

    def setup_logger(worker):
        logger = logging.getLogger('spinorama')
        if level is not None:
            logger.setLevel(level)

    # will eat all your CPUs
    ip = '127.0.0.1'
    port = 8265
    if 'ip' in args and args['ip'] is not None:
        check_ip = args['ip']
        try:
            address = ipaddress.ip_address(ip)
            ip = check_ip
        except AddressValueError:
            logger.error('ip {} is not valid!'.format(ip))
            sys.exit(1)

    if 'port' in args and args['port'] is not None:
        check_port = args['port']
        port = check_port

    ray.worker.global_worker.run_function_on_all_workers(setup_logger)
    # address is the one from the ray server
    # ray.init(address='{}:{}'.format(ip, port))
    ray.init()

    filters = {}
    for filter in ('speaker', 'origin', 'version'):
        flag = '--{}'.format(filter)
        if args[flag] is not None:
            filters[filter] = args[flag]
    
    ray_ids = queue_speakers(speakerlist, metadata.speakers_info, filters)
    df = compute(speakerlist, metadata.speakers_info, ray_ids)
    if len(filters.keys()) == 0:
        fl.save('cache.parse_all_speakers.h5', df)

    ray.shutdown()
    sys.exit(0)
