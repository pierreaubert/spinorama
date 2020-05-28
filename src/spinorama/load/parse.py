import os
import sys
import glob
import math
import logging
import numpy as np
import pandas as pd

from ..cea2034 import early_reflections, vertical_reflections, horizontal_reflections,\
     compute_cea2034, compute_onaxis, estimated_inroom, estimated_inroom_HV
from ..normalize import unify_freq, normalize_mean, normalize_cea2034, normalize_graph

from .klippel import parse_graphs_speaker_klippel
from .webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from .princeton import parse_graphs_speaker_princeton
from .rewstextdump import parse_graphs_speaker_rewstextdump


def normalize(df):
    # normalize all melted graphs
    dfc = {}
    if 'CEA2034' in df:
        mean = normalize_mean(df['CEA2034'])
        for graph in df.keys():
            if graph != 'CEA2034':
                if graph.replace('_unmelted', '') != graph:
                    dfc[graph] = df[graph]
                else:
                    dfc[graph] = normalize_graph(df[graph], mean)
        dfc['CEA2034'] = normalize_cea2034(df['CEA2034'], mean)
        return dfc
    elif 'On Axis' in df:
        mean = normalize_mean(df['On Axis'])
        for graph in df.keys():
            if graph.replace('_unmelted', '') != graph:
                dfc[graph] = df[graph]
            else:
                dfc[graph] = normalize_graph(df[graph], mean)
        return dfc
        
    # do nothing
    return df


def parse_graphs_speaker(speaker_brand : str, speaker_name : str, mformat='klippel') -> str:
    df = None
    if mformat == 'klippel':
        df = parse_graphs_speaker_klippel(speaker_name)
    elif mformat == 'webplotdigitizer':
        df = parse_graphs_speaker_webplotdigitizer(speaker_brand, speaker_name)
    elif mformat == 'princeton':
        df = parse_graphs_speaker_princeton(speaker_name)
    elif mformat == 'rewstextdump':
        df = parse_graphs_speaker_rewstextdump(speaker_brand, speaker_name)
    else:
        logging.fatal('Format {:s} is unkown'.format(mformat))
        sys.exit(1)

    return normalize(df)
        


def get_speaker_list(speakerpath):
    speakers = []
    asr = glob.glob(speakerpath+'/ASR/*')
    vendors = glob.glob(speakerpath+'/Vendors/*/*')
    princeton = glob.glob(speakerpath+'/Princeton/*')
    dirs = asr + vendors + princeton
    for d in dirs:
        if os.path.isdir(d) and d not in ('assets', 'compare', 'stats', 'pictures', 'logos'):
            speakers.append(os.path.basename(d))
    return speakers


def parse_all_speakers(metadata, filter_origin, speakerpath='./datas'):
    speakerlist = get_speaker_list(speakerpath)
    df = {}
    count_measurements = 0
    for speaker in speakerlist:
        logging.info('Parsing {0}'.format(speaker))
        df[speaker] = {}
        if speaker not in metadata.keys():
            logging.error('{:s} is not in metadata.py!'.format(speaker))
            sys.exit(1)
        current = metadata[speaker]
        if 'measurements' not in current.keys():
            logging.error('no measurements for speaker {:s}, please add to metadata.py!'.format(speaker))
            sys.exit(1)
        for m in current['measurements']:
            if 'format' not in m.keys():
                logging.error('measurement for speaker {:s} need a format field, please add to metadata.py!'.format(speaker))
                sys.exit(1)
            mformat = m['format']
            if mformat not in ['klippel', 'princeton', 'webplotdigitizer', 'rewstextdump']:
                logging.error('format field must be one of klippel, princeton, webplotdigitizer, rewstextdump. Current value is: {:s}'.format(mformat))
                sys.exit(1)
            if 'origin' not in m.keys():
                logging.error('measurement for speaker {:s} need an origin field, please add to metadata.py!'.format(speaker))
                sys.exit(1)
            origin = m['origin']
            if filter_origin is not None and origin != filter_origin:
                continue
            # keep it simple
            df[speaker][origin] = {}
            # speaker / origin / measurement
            brand = metadata[speaker]['brand']
            df[speaker][origin]['default'] = parse_graphs_speaker(brand, speaker, mformat)
            if df[speaker][origin]['default'] is not None:
                count_measurements += 1
        
    print('Loaded {:d} speakers {:d} measurements'.format(len(speakerlist),
          count_measurements))
    
    return df
