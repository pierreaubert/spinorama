#                                                  -*- coding: utf-8 -*-
import os
import sys
import glob
import logging
from .load import filter_graphs, load_normalize
from .load_klippel import parse_graphs_speaker_klippel
from .load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from .load_princeton import parse_graphs_speaker_princeton
from .load_rewstextdump import parse_graphs_speaker_rewstextdump
from .load_rewseq import parse_eq_iir_rews
from .load_splHVtxt import parse_graphs_speaker_splHVtxt
from .filter_peq import peq_apply_measurements


def parse_eq_speaker(speaker_path : str, speaker_name : str, df_ref) -> dict:
    iirname = '{0}/eq/{1}/iir.txt'.format(speaker_path, speaker_name)
    if os.path.isfile(iirname):
        srate = 48000
        logging.debug('found IIR eq {0}: applying to {1}'.format(iirname, speaker_name))
        iir = parse_eq_iir_rews(iirname, srate)
        if 'SPL Horizontal_unmelted' in df_ref.keys() and 'SPL Vertical_unmelted' in df_ref.keys():
            h_spl = df_ref['SPL Horizontal_unmelted']
            v_spl = df_ref['SPL Vertical_unmelted']
            eq_h_spl = peq_apply_measurements(h_spl, iir)
            eq_v_spl = peq_apply_measurements(v_spl, iir)
            df_eq = filter_graphs(speaker_name, eq_h_spl, eq_v_spl)
            # normalize wrt to original measurement to make comparison easier
            # original_mean = df_ref.get('CEA2034_original_mean', None)
            # return load_normalize(df_eq, original_mean)
            return df_eq
    return None


def parse_graphs_speaker(speaker_path : str, speaker_brand : str, speaker_name : str, mformat='klippel', mversion='default') -> dict:
    df = None
    if mformat == 'klippel':
        df = parse_graphs_speaker_klippel(speaker_path, speaker_brand, speaker_name, mversion)
    elif mformat == 'webplotdigitizer':
        df = parse_graphs_speaker_webplotdigitizer(speaker_path, speaker_brand, speaker_name, mversion)
    elif mformat == 'princeton':
        df = parse_graphs_speaker_princeton(speaker_path, speaker_brand, speaker_name, mversion)
    elif mformat == 'splHVtxt':
        df = parse_graphs_speaker_splHVtxt(speaker_path, speaker_brand, speaker_name, mversion)
    elif mformat == 'rewstextdump':
        df = parse_graphs_speaker_rewstextdump(speaker_path, speaker_brand, speaker_name, mversion)
    else:
        logging.fatal('Format {:s} is unkown'.format(mformat))
        sys.exit(1)

    if df is None:
        logging.warning('Parsing failed for {0} {1} {2} {3} {4}'.format(speaker_path, speaker_brand, speaker_name, mformat, mversion))
        return None
    df_normalized = load_normalize(df)
    if df_normalized is None:
        logging.warning('Normalisation failed for {0} {1} {2} {3} {4}'.format(speaker_path, speaker_brand, speaker_name, mformat, mversion))
        return None
    return df_normalized


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


def parse_all_speakers(metadata : dict, filter_origin: str, speakerpath='./datas', filter_version='default', parse_max=None) -> dict:
    speakerlist = get_speaker_list(speakerpath)
    df = {}
    count_measurements = 0
    count_eqs = 0
    for speaker in speakerlist:
        logging.debug('Starting with {0}'.format(speaker))
        df[speaker] = {}
        if speaker not in metadata.keys():
            logging.error('{:s} is not in metadata.py!'.format(speaker))
            sys.exit(1)
        meta_speaker = metadata[speaker]
        if 'measurements' not in meta_speaker.keys():
            logging.error('no measurements for speaker {:s}, please add to metadata.py!'.format(speaker))
            sys.exit(1)
        for version, measurement in meta_speaker['measurements'].items():
            # print('debug {0} {1}'.format(version, measurement))
            # check format
            if 'format' not in measurement:
                logging.error('measurement for speaker {:s} need a format field, please add to metadata.py!'.format(speaker))
                sys.exit(1)
            mformat = measurement['format']
            if mformat not in ['klippel', 'princeton', 'webplotdigitizer', 'rewstextdump']:
                logging.error('format field must be one of klippel, princeton, webplotdigitizer, rewstextdump. meta_speaker value is: {:s}'.format(mformat))
                sys.exit(1)
            # check origin
            if 'origin' not in measurement.keys():
                logging.error('measurement for speaker {:s} need an origin field, please add to metadata.py!'.format(speaker))
                sys.exit(1)
            origin = measurement['origin']
            #if filter_origin is not None and origin != filter_origin:
            #    continue
            # check version
            #if filter_version is not None and version != filter_version:
            #    continue
            # keep it simple
            if origin not in df[speaker]:
                df[speaker][origin] = {}
            brand = metadata[speaker]['brand']
            # start // version here
            logging.info('Stacking {0} {1} {2} {3} {4}'.format(speakerpath, brand, speaker, mformat, version))
            df_ref = parse_graphs_speaker(speakerpath, brand, speaker, mformat, version)
            if df_ref is not None:
                df[speaker][origin][version] = df_ref
                count_measurements += 1
                df_eq = parse_eq_speaker(speakerpath, speaker, df_ref)
                if df_eq is not None:
                    df[speaker][origin]['{0}_eq'.format(version)] = df_eq
                    count_eqs += 1
                            
        if parse_max is not None and count_measurements > parse_max:
            break

    print('Loaded {0} speakers {1} measurements and {2} EQs'.format(len(speakerlist), count_measurements, count_eqs))
    return df
