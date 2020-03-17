import os
import sys
import glob
import locale
import math
from locale import atof
import json
import logging
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .analysis import early_reflections, vertical_reflections, horizontal_reflections,\
     compute_cea2034, estimated_inroom, estimated_inroom_HV


locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

removequote = str.maketrans({'"': None, '\n': ''})


def graph_melt(df : pd.DataFrame):
    return df.reset_index().melt(id_vars='Freq', var_name='Measurements',
                                 value_name='dB').loc[lambda df: df['Measurements'] != 'index']

def unify_freq(dfs):
    on = dfs[dfs.Measurements == 'On Axis'].rename(columns={'dB': 'ON'}).set_index('Freq')
    lw = dfs[dfs.Measurements == 'Listening Window'].rename(columns={'dB': 'LW'}).set_index('Freq')
    er = dfs[dfs.Measurements == 'Early Reflections'].rename(columns={'dB': 'ER'}).set_index('Freq')
    sp = dfs[dfs.Measurements == 'Sound Power'].rename(columns={'dB': 'SP'}).set_index('Freq')
    # align 2 by 2
    align = on.align(lw, axis=0)
    # print(align[0].shape)
    align = align[0].align(er, axis=0)
    # print(align[0].shape)
    all_on = align[0].align(sp, axis=0)
    # print(all_on[0].head())
    # print(all_on[0].shape)
    # realigned with the largest frame
    all_lw = all_on[0].align(lw, axis=0)
    all_er = all_on[0].align(er, axis=0)
    all_sp = all_on[0].align(sp, axis=0)
    # print(all_lw[1].shape, all_er[1].shape, all_sp[1].shape)
    # extract right parts and interpolate
    a_on = all_on[0].drop('Measurements', axis=1).interpolate()
    a_lw = all_lw[1].drop('Measurements', axis=1).interpolate()
    a_er = all_er[1].drop('Measurements', axis=1).interpolate()
    a_sp = all_sp[1].drop('Measurements', axis=1).interpolate()
    # print(a_lw.shape, a_er.shape, a_sp.shape)
    # remove NaN numbers
    res2 = pd.DataFrame({'Freq': a_lw.index, 
                         'On Axis': a_on.ON,
                         'Listening Window': a_lw.LW, 
                         'Early Reflections': a_er.ER, 
                         'Sound Power': a_sp.SP})
    # print(res2.head())
    return res2.dropna().reset_index(drop=True)


def parse_graph_freq_klippel(filename):
    title = None
    columns = ['Freq']
    usecols = [0]
    with open(filename) as csvfile:
        # first line is graph title
        title = csvfile.readline().split('\t')[0][1:-1]
        # second line is column titles
        csvcolumns = [c.translate(removequote)
                      for c in csvfile.readline().split('\t')]
        # third line is column units
        # units = [c.translate(removequote)
        #         for c in csvfile.readline().split('\t')]
        # print(units)
        columns.extend([c for c in csvcolumns if len(c) > 0])
        # print(columns)
        usecols.extend([1 + i * 2 for i in range(len(columns) - 1)])
        # print(usecols)

    # read all columns, drop 0
    df = pd.read_csv(
        filename,
        sep='\t',
        skiprows=2,
        usecols=usecols,
        names=columns,
        thousands=',').drop(0)
    # convert to float (issues with , and . in numbers)
    df = df.applymap(atof)
    # reorder column if we are reading a file with angles (Pandas doesn't care but easier to plot)
    # c: Freq  0 10 -10 20 -20 30 -30 40-40 50 -50 60 -60 70 -70 -80 90 -90 100 -100 110 -110
    #                               120 -120 130 -130 140 -140 150 -150 160 -160 170 -170 180
    # i: 0     1  2   3  4   5  6   7  9 10 11  12 13  14 15  16  17 18  19  20   21  22   23
    #                                24   25  26   27  28   29  30   31  32   33  34   35  36
    # p: 0    18 17  19 16  20 15  22 14 23 13  24 12  25 11  26  10 27   9   28    8  29   7
    #                                 30    6  31    5  32    4  33    3  34    2  35    1 36
    perm = [0, 35, 33, 31, 29, 27, 25, 23, 21, 19, 17, 15, 13, 11, 9, 7, 5,
            3, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
            32, 34, 36]

    # make it consistent
    df = df.rename(columns={'On-Axis': 'On Axis'})
    # put it in order, not relevant for pandas but for np array
    if len(df.columns) > 2 and df.columns[2] == '10°':
        return title, df[[df.columns[perm[i]] for i in range(0, len(perm))]]
    return title, df


def parse_graph_freq_webplotdigitizer(filename):
    """ """
    # from 20Hz to 20kHz, log(2)~0.3
    ref_freq = np.logspace(1+math.log10(2), 4+math.log10(2), 500)
    #
    with open(filename, 'r') as f:
        # data are stored in a json file.
        speaker_data = json.load(f)
        # store all results
        res = []
        for col in speaker_data['datasetColl']:
            data = col['data']
            # sort data
            udata = [(data[d]['value'][0],
                      data[d]['value'][1])
                     for d in range(0, len(data))]
            sdata = sorted(udata, key=lambda a: a[0])
            #print(col['name'], len(sdata))
            #print(sdata[0])
            # since sdata and freq_ref are both sorted, iterate over both
            ref_p = 0
            for di in range(0, len(sdata)-1):
                d = sdata[di]
                dn = sdata[di+1]
                fr = d[0]
                db = d[1]
                frn = dn[0]
                dbn = dn[1]
                # remove possible errors
                if fr == frn:
                    continue
                # look for closest match
                while ref_freq[ref_p] <= fr:
                    if ref_p >= len(ref_freq)-1:
                        break
                    ref_p += 1
                # if ref_f is too large, skip
                ref_f = ref_freq[ref_p]
                if ref_f > frn:
                    continue
                # linear interpolation
                ref_db = db+((dbn-db)*(ref_f-fr))/(frn-fr)
                #print('fr={:.2f} fr_ref={:.2f} fr_n={:.2f} db={:.1f} db_ref={:.1f} db_n={:.1f}'.format(fr, ref_f, frn, db, ref_db, dbn))
                res.append([ref_f, ref_db, col['name']])

        # build dataframe
        freq = np.array([res[i][0] for i in range(0, len(res))]).astype(np.float)
        dB   = np.array([res[i][1] for i in range(0, len(res))]).astype(np.float)
        mrt  = [res[i][2] for i in range(0, len(res))]
        df = pd.DataFrame({'Freq': freq, 'dB': dB, 'Measurements': mrt})
        # print(df)
        return 'CEA2034', df 


def parse_graph_freq_princeton_mat(mat, suffix):
    """ Suffix can be either H or V """
    ir_name = 'IR_{:1s}'.format(suffix)
    fs_name = 'fs_{:1s}'.format(suffix)
    # compute Freq                                                                                                                   
    timestep = 1./mat[fs_name]
    # hummm                                                                                                                          
    freq = np.fft.fftfreq(2**14, d=timestep)
    # reduce spectrum to 0 to 24kHz                                                                                                  
    # lg = 2**14                                                                                                                     
    # 24k is lgs = int(lg/4)                                                                                                         
    # 20k is at 3414                                                                                                                 
    lgs = 3414
    xs = freq[0][0:lgs]
    #    
    df = pd.DataFrame({'Freq': xs})
    # loop over measurements (skipping the 5 increments)
    for i in range(0, 72, 1):
        # extract ir                                                                                                                 
        ir = mat[ir_name][i]
        # compute FFT                                                                                                                
        y = np.fft.fft(ir)
        ys = np.abs(y[0:lgs])
        # check for 0 (from manual: 0 means not measured)                                                                            
        if ys.max() == 0.0:
            continue
        # apply formula from paper to translate to dbFS                                                                              
        ys = 105.+np.log10(ys)*20.
        # interpolate to smooth response                                                                                             
        # s = InterpolatedUnivariateSpline(xs, ys)                                                                                   
        # pretty print label, per 5 deg increment, follow klippel labelling                                                          
        ilabel =i*5
        if ilabel > 180: 
            ilabel = ilabel-360
        label = '{:d}°'.format(ilabel)
        if ilabel == 0:
            label = 'On Axis'
        df[label] = ys
    # sort columns in increasing angle order 
    def a2v(angle):
        if angle == 'Freq':
            return -1000
        elif angle == 'On Axis':
            return 0
        else:
            return int(angle[:-1])

    df = df.reindex(columns=sorted(df.columns, key=lambda a: a2v(a)))
    # check empty case
    if 'On Axis' not in df.keys():
        return None
    # precision of measurement is ok above 500
    return df[df.Freq>=500]


def parse_graph_princeton(filename, orient):
    matfile = loadmat(filename)
    return parse_graph_freq_princeton_mat(matfile, orient)


def parse_graphs_speaker_klippel(speaker_name):
    dfs = {}
    csvfiles = ["CEA2034",
                "Early Reflections",
                "Directivity Index",
                "Estimated In-Room Response",
                "Horizontal Reflections",
                "Vertical Reflections",
                "SPL Horizontal",
                "SPL Vertical"]
    for csv in csvfiles:
        csvfilename = "datas/ASR/" + speaker_name + "/" + csv + ".txt"
        try:
            title, df = parse_graph_freq_klippel(csvfilename)
            logging.info('Speaker: ' + speaker_name + ' (ASR) Loaded: '+title)
            dfs[title + '_unmelted'] = df
            dfs[title] = graph_melt(df)
        except FileNotFoundError:
            logging.warning('Speaker: ' + speaker_name +' (ASR) Not found: ' + csvfilename)
    return dfs


def parse_graphs_speaker_webplotdigitizer(speaker_brand, speaker_name):
    dfs = {}
    jsonfilename = 'datas/Vendors/' + speaker_brand + '/' + speaker_name + '/' + speaker_name + '.json'
    try:
        title, spin_uneven = parse_graph_freq_webplotdigitizer(jsonfilename)
        spin = graph_melt(unify_freq(spin_uneven))
        if title != 'CEA2034':
            logging.debug('title is {0}'.format(title))
            return spin

        if spin is not None:
            dfs[title] = spin

            on = spin.loc[spin['Measurements'] == 'On Axis'].reset_index(drop=True)
            lw = spin.loc[spin['Measurements'] == 'Listening Window'].reset_index(drop=True)
            er = spin.loc[spin['Measurements'] == 'Early Reflections'].reset_index(drop=True)
            sp = spin.loc[spin['Measurements'] == 'Sound Power'].reset_index(drop=True)

            # print(on.shape, lw.shape, er.shape, sp.shape)
            eir = estimated_inroom(lw, er, sp)
            # print('eir {0}'.format(eir.shape))
            # print(eir)
            logging.debug('eir {0}'.format(eir.shape))
            dfs['Estimated In-Room Response'] = graph_melt(eir)
    except FileNotFoundError:
        logging.warning('Speaker: ' + speaker_name +' Not found: '+ jsonfilename)
    return dfs
        
    
def parse_graphs_speaker_princeton(speaker_name):
    dfs = {}
    # 2 files per directory xxx_H_IR.mat and xxx_V_IR.mat
    matfilename = 'datas/Princeton/' + speaker_name 
    dirpath = glob.glob(matfilename+'/*.mat')
    h_file = None
    v_file = None
    for d in dirpath:
        if d[-9:] == '_H_IR.mat':
            h_file = d
        elif d[-9:] == '_V_IR.mat':
            v_file = d
    if h_file is None or v_file is None:
        logging.info('Couldn\'t find Horizontal and Vertical IR files for speaker {:s}'.format(speaker_name))
        logging.info('Looking in directory {:s}'.format(matfilename))
        for d in dirpath:
            logging.info('Found file {:s}'.format(d))
        return None

    h_spl = parse_graph_princeton(h_file, 'H')
    v_spl = parse_graph_princeton(v_file, 'V')
    # add H and V SPL graphs
    if h_spl is not None:
        dfs['SPL Horizontal_unmelted'] = h_spl
        dfs['SPL Horizontal'] = graph_melt(h_spl)
    if v_spl is not None:
        dfs['SPL Vertical_unmelted'] = v_spl
        dfs['SPL Vertical'] = graph_melt(v_spl)
    # add computed graphs
    table = [['Early Reflections', early_reflections],
             ['Horizontal Reflections', horizontal_reflections],
             ['Vertical Reflections', vertical_reflections],
             ['Estimated In-Room Response', estimated_inroom_HV],
             ['CEA2034', compute_cea2034],
             ]
    for title, functor in table:
        try:
            df = functor(h_spl, v_spl)
            if df is not None:
                dfs[title+'_unmelted'] = df
                dfs[title] = graph_melt(df)
            else:
                logging.warning('{0} computation is None for speaker{1:s} (Princeton)'.format(title, speaker_name))
        except KeyError as ke:
            logging.warning('{0} computation failed with key:{1} for speaker{2:s} (Princeton)'.format(title, ke, speaker_name))
            
    return dfs



def parse_graphs_speaker(speaker_brand : str, speaker_name : str, mformat='klippel') -> str:
    if mformat == 'klippel':
        return parse_graphs_speaker_klippel(speaker_name)
    elif mformat == 'webplotdigitizer':
        return parse_graphs_speaker_webplotdigitizer(speaker_brand, speaker_name)
    elif mformat == 'princeton':
        return parse_graphs_speaker_princeton(speaker_name)

    logging.error('Format {:s} is unkown'.format(mformat))
    sys.exit(1)


def get_speaker_list(speakerpath):
    speakers = []
    asr = glob.glob(speakerpath+'/ASR/[A-Z]*')
    vendors = glob.glob(speakerpath+'/Vendors/*/[A-Z]*')
    princeton = glob.glob(speakerpath+'/Princeton/[A-Z]*')
    dirs = asr + vendors + princeton
    for d in dirs:
        if os.path.isdir(d):
            speakers.append(os.path.basename(d))
    return speakers


def parse_all_speakers(metadata, filter_origin, speakerpath='./datas'):
    speakerlist = get_speaker_list(speakerpath)
    df = {}
    count_measurements = 0
    for speaker in speakerlist:
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
            if mformat not in ['klippel', 'princeton', 'webplotdigitizer']:
                logging.error('format field must be one of klippel, princeton, webplotdigitizer. Current value is: {:s}'.format(mformat))
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
