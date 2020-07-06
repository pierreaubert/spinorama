#                                                  -*- coding: utf-8 -*-
import os
import sys
import glob
import logging
from .compute_normalize import normalize_mean, normalize_cea2034, normalize_graph
from .load import compute_graphs
from .load_klippel import parse_graphs_speaker_klippel
from .load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from .load_princeton import parse_graphs_speaker_princeton
from .load_rewstextdump import parse_graphs_speaker_rewstextdump
from .load_rewseq import parse_eq_iir_rews
from .filter_peq import peq_apply_measurements


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


def parse_eq_speaker(speaker_name : str, df_ref) -> dict:
    iirname = './datas/eq/{0}/iir.txt'.format(speaker_name)
    if os.path.isfile(iirname):
        srate = 48000
        logging.debug('found IIR eq {0}: applying to {1}'.format(iirname, speaker_name))
        iir = parse_eq_iir_rews(iirname, srate)
        h_spl = df_ref['SPL Horizontal_unmelted']
        v_spl = df_ref['SPL Vertical_unmelted']
        eq_h_spl = peq_apply_measurements(h_spl, iir)
        eq_v_spl = peq_apply_measurements(v_spl, iir)
        df_eq = compute_graphs(speaker_name, eq_h_spl, eq_v_spl)
        return df_eq
    return None


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


def parse_all_speakers(metadata : dict, filter_origin: str, speakerpath='./datas') -> dict:
    speakerlist = get_speaker_list(speakerpath)
    df = {}
    count_measurements = 0
    count_eqs = 0
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
            df_ref = parse_graphs_speaker(brand, speaker, mformat)
            if df_ref is not None:
                df[speaker][origin]['default'] = df_ref
                count_measurements += 1
                df_eq = parse_eq_speaker(speaker, df_ref)
                if df_eq is not None:
                    df[speaker][origin]['default_eq'] = df_eq
                    count_eqs += 1
        
    print('Loaded {0} speakers {1} measurements and {2} EQs'.format(len(speakerlist), count_measurements, count_eqs))
    return df
