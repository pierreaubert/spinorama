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
import flammkuchen as fl
import glob
import logging
import os
import pandas as pd
import ray
import sys
import time

import datas.metadata as metadata
from src.spinorama.load_parse_ray import parse_graphs_speaker, parse_eq_speaker
from src.spinorama.speaker_print_ray import print_graphs, print_compare


# will eat all your CPUs
ray.init()


def get_speaker_list(speakerpath : str):
    speakers = []
    asr = glob.glob(speakerpath+'/ASR/*')
    vendors = glob.glob(speakerpath+'/Vendors/*/*')
    princeton = glob.glob(speakerpath+'/Princeton/*')
    dirs = asr + vendors + princeton
    for d in dirs:
        if os.path.isdir(d) and d not in ('assets', 'compare', 'stats', 'pictures', 'logos'):
            speakers.append(os.path.basename(d))
    return speakers


def queue_measurement(brand, speaker, mformat, morigin, mversion):
    id_df = parse_graphs_speaker.remote('./datas', brand, speaker, mformat, mversion)
    id_eq = parse_eq_speaker.remote('./datas', speaker, id_df)
    force = False
    ptype = None
    width = 1024
    height = 400
    id_g1 = print_graphs.remote(id_df, id_eq, speaker, morigin, metadata.origins_info, mversion, width, height, force, ptype)
    id_g2 = print_graphs.remote(id_eq, id_eq, speaker, morigin, metadata.origins_info, mversion+'_eq', width, height, force, ptype)
    return (id_df, id_eq, id_g1, id_g2)


def queue_speakers(speakerlist, metadata : dict) -> dict:
    ray_ids = {}
    count = 0
    for speaker in speakerlist:
        ray_ids[speaker] = {}
        for mversion, measurement in metadata[speaker]['measurements'].items():
            mformat = measurement['format']
            morigin = measurement['origin']
            brand = metadata[speaker]['brand']
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

        logging.info('State: {0} ready IDs {1} remainings IDs {2} Total IDs {3} Done'.format(len(ready_ids), len(remaining_ids), len(ids), len(done_ids)))
        
        for speaker in speakerlist:
            speaker_key = speaker #.translate({ord(ch) : '_' for ch in '-.;/\' '})
            if speaker not in df.keys():
                df[speaker_key] = {}
            for m_version, measurement in metadata[speaker]['measurements'].items():
                m_version_key = m_version #.translate({ord(ch) : '_' for ch in '-.;/\' '})
                m_origin = measurement['origin']
                if m_origin not in df[speaker_key].keys():
                    df[speaker_key][m_origin] = {}

                current_id = ray_ids[speaker][m_version][0]
                if current_id in ready_ids:
                    df[speaker_key][m_origin][m_version_key] = ray.get(current_id)
                    logging.debug('Getting df done for {0} / {1} / {2}'.format(speaker, m_origin, m_version))
                    done_ids[current_id] = True
                    continue
                
                m_version_eq = '{0}_eq'.format(m_version_key)
                current_id = ray_ids[speaker][m_version][1]
                if current_id in eq_ids:
                    logging.debug('Getting eq done for {0} / {1} / {2}'.format(speaker, m_version_eq, m_version))
                    eq = ray.get(current_id)
                    if eq is not None:
                        df[speaker_key][m_origin][m_version_eq] = eq
                    done_ids[current_id] = True
                    continue

                current_id = ray_ids[speaker][m_version][2]
                if current_id in g1_ids:
                    logging.debug('Getting graph done for {0} / {1} / {2}'.format(speaker, m_version, m_origin))
                    ray.get(current_id)
                    done_ids[current_id] = True
                    continue

                current_id = ray_ids[speaker][m_version][3]
                if current_id in g2_ids:
                    logging.debug('Getting graph done for {0} / {1} / {2}'.format(speaker, m_version_eq, m_origin))
                    ray.get(current_id)
                    done_ids[current_id] = True
                    continue

                done_ids[current_id] = True

        if len(remaining_ids) == 0:
            break
        
    return df

    
if __name__ == '__main__':
    # TODO remove it and replace by iterating over metadatas
    speakerlist = get_speaker_list('./datas')

    width = 1200
    height = 600
    force = False
    ptype = None
    
    ray_ids = queue_speakers(speakerlist, metadata.speakers_info)
    df = compute(speakerlist, metadata.speakers_info, ray_ids)
    fl.save('cache.parse_all_speakers.h5', df)

        
