import os
import sys
import glob
import locale
from locale import atof
import json
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .path import measurement2name
# from scipy.interpolate import InterpolatedUnivariateSpline

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

removequote = str.maketrans({'"': None, '\n': ''})


def graph_melt(df):
    return df.reset_index().melt(id_vars='Freq', var_name='Measurements',
                                 value_name='dB').loc[lambda df: df['Measurements'] != 'index']


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

    if len(df.columns) > 2 and df.columns[2] == '10°':
        return title, df[[df.columns[perm[i]] for i in range(0, len(perm))]]
    return title, df


def parse_graph_freq_webplotdigitizer(filename):
    """ """
    # from 20Hz to 20kHz, log(2)~0.3
    ref_freq = np.logspace(0.30103, 4.30103, 203)
    #
    with open(filename, 'r') as f:
        # data are stored in a json file.
        speaker_data = json.load(f)
        # store all results
        res = []
        for col in speaker_data['datasetColl']:
            data = col['data']
            # sort data
            sdata = np.sort([[data[d]['value'][0],
                              data[d]['value'][1]]
                             for d in range(0, len(data))], axis=0)
            # print(col['name'], len(sdata))
            # print(sdata)
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
                    ref_p += 1
                    if ref_p >= len(ref_freq):
                        continue
                # if ref_f is too large, skip
                ref_f = ref_freq[ref_p]
                if ref_f > frn:
                    continue
                # linear interpolation
                ref_db = db+((dbn-db)*(ref_f-fr))/(frn-fr)
                # print('fr={:.2f} fr_ref={:.2f} fr_n={:.2f} \
                #       db={:.1f} db_ref={:.1f} db_n={:.1f}'\
                #      .format(fr, ref_f, frn,
                #              db, ref_db,          dbn))
                res.append([ref_f, ref_db, col['name']])

        # build dataframe
        ares = np.array(res)
        df = pd.DataFrame({'Freq': ares[:, 0],
                           'dB': ares[:, 1],
                           'Measurements': ares[:, 2]})
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
    #
    dfx = []
    dfy = []
    dfz = []
    # loop over measurements
    for i in range(0, 3):
        # extract ir
        ir = mat[ir_name][i]
        # compute FFT
        y = np.fft.fft(ir)
        # reduce spectrum to 0 to 24kHz
        lg = y.size
        lgs = int(lg/4)
        # sample by N element
        xs = freq  # [freq[i] for i in range(0, lgs) if i % 1 == 0]
        # sample by N elements and take |db|
        ys = np.abs([y[i] for i in range(0, lgs) if i % 1 == 0])
        # apply formula from paper to translate to dbFS
        ys = 105.+np.log10(ys)*20.
        # interpolate to smooth response
        # s = InterpolatedUnivariateSpline(xs, ys)
        dfx.append(xs)
        dfy.append(ys)
        label = '{:2d}°'.format(i*10)
        # pretty print label
        dfz.append([label for j in range(0, len(xs))])
    return dfx, dfy, dfz


def parse_graph_freq_princeton(h_file, v_file):
    # h_mat = loadmat(h_file)
    # v_mat = loadmat(v_file)
    # h_df = parse_graph_freq_princeton_mat(h_mat, 'H')
    return 'CEA2034', None


def parse_graphs_speaker(speakerpath, format='klippel'):
    dfs = {}
    if format == 'klippel':
        csvfiles = ["CEA2034",
                    "Early Reflections",
                    "Directivity Index",
                    "Estimated In-Room Response",
                    "Horizontal Reflections",
                    "Vertical Reflections",
                    "SPL Horizontal",
                    "SPL Vertical"]
        for csv in csvfiles:
            csvfilename = "datas/ASR/" + speakerpath + "/" + csv + ".txt"
            try:
                title, df = parse_graph_freq_klippel(csvfilename)
                print('Speaker: '+speakerpath+' Loaded: '+title)
                dfs[title + '_unmelted'] = df
                dfs[title] = graph_melt(df)
            except FileNotFoundError:
                print('Speaker: '+speakerpath+' Not found: '+csv)
                pass
    elif format == 'webplotdigitizer':
        jsonfilename = 'datas/Vendors/' + speakerpath + '/' + speakerpath + '.json'
        try:
            title, df = parse_graph_freq_webplotdigitizer(jsonfilename)
            dfs[title] = df
        except FileNotFoundError:
            # print('Speaker: '+speakerpath+' Not found: '+csv)
            pass
    elif format == 'princeton':
        # 2 files per directory xxx_H_IR.mat and xxx_V_IR.mat
        matfilename = 'datas/Princeton/' + speakerpath 
        dirpath = glob.glob(matfilename+'/*.mat')
        h_file = None
        v_file = None
        for d in dirpath:
            if d[-9:] == '_H_IR.mat':
                h_file = d
            elif d[-9:] == '_V_IR.mat':
                v_file = d
        if h_file is None or v_file is None:
            print('Couldn\'t find Horizontal and Vertical IR files for speaker '+speakerpath)
            print('Looking in directory {:s}'.format(matfilename))
            for d in dirpath:
                print('Found file {:s}'.format(d))
        else:
            title, df = parse_graph_freq_princeton(h_file, v_file)
            dfs[title] = df
    else:
        print('Format {:s} is unkown'.format(format))
        sys.exit(1)
    return dfs


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


def parse_all_speakers(metadata, speakerpath='./datas'):
    speakerlist = get_speaker_list(speakerpath)
    df = {}
    count_measurements = 0
    for speaker in speakerlist:
        df[speaker] = {}
        if speaker not in metadata.keys():
            print('Error: {:s} is not in metadata.py!'.format(speaker))
            sys.exit(1)
        current = metadata[speaker]
        if 'measurements' not in current.keys():
            print('Error: no measurements for speaker {:s}, please add to metadata.py!'.format(speaker))
            sys.exit(1)
        for m in current['measurements']:
            if 'format' not in m.keys():
                print('Error: measurement for speaker {:s} need a format field, please add to metadata.py!'.format(speaker))
                sys.exit(1)
            mformat = m['format']
            if mformat not in ['klippel', 'princeton', 'webplotdigitizer']:
                print('Error: format field must be one of klippel, princeton, webplotdigitizer. Current value is: {:s}'.format(mformat))
                sys.exit(1)
            if 'origin' not in m.keys():
                print('Error: measurement for speaker {:s} need an origin field, please add to metadata.py!'.format(speaker))
                sys.exit(1)
            origin = m['origin']
            # keep it simple
            df[speaker][origin] = {}
            # speaker / origin / measurement 
            df[speaker][origin]['default'] = parse_graphs_speaker(speaker, mformat)
            if df[speaker][origin]['default'] is not None:
                count_measurements += 1

    print('Loaded {:d} speakers {:d} measurements'.format(len(speakerlist),
          count_measurements))
    
    return df
