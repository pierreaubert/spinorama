#                                                  -*- coding: utf-8 -*-
import logging
import glob
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .load import compute_graphs


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


def parse_graphs_speaker_princeton(speaker_name):
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

    return compute_graphs(speaker_name, h_spl, v_spl)


