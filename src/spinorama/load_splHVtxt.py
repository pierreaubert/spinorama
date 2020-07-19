#                                                  -*- coding: utf-8 -*-
import logging
import os
import glob
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .load import filter_graphs


def  parse_graph_splHVtxt(dirpath, orientation):
    df = pd.DataFrame()

    filenames = '{0}/*_{1}.txt'.format(dirpath, orientation)
    files = glob.glob(filenames)
    
    dfs = []
    for file in files:
        freqs = []
        dbs = []
        angle = os.path.basename(file).split('_')[0]
        if angle == '0':
            angle = 'On Axis'
        else:
            angle += '°'
        with open(file, 'r') as fd:
            lines = fd.readlines()
            for l in lines:
                words = l[:-1].split(',')
                if len(words) != 2:
                    continue
                freqs.append(float(words[0]))
                dbs.append(float(words[1]))
        if angle == 'On Axis':
            dfs.append(pd.DataFrame({'Freq': freqs, angle: dbs}))
        else:
            if angle != '-180°':
                dfs.append(pd.DataFrame({angle: dbs}))
            if orientation == 'H' and angle != '180°':
                mangle = '-{0}'.format(angle)
                dfs.append(pd.DataFrame({mangle: dbs}))
                

    df = pd.concat(dfs, axis=1)
    # reorder from -90 to +270 and not -180 to 180 to be closer to other plots
    def a2v(angle):
        if angle == 'Freq':
            return -1000
        elif angle == 'On Axis':
            return 0
        iangle = int(angle[:-1])
        if iangle <-90:
            return iangle+270
        return iangle
        
    return df.reindex(columns=sorted(df.columns, key=lambda a: a2v(a)))
    

def parse_graphs_speaker_splHVtxt(speaker_path, speaker_brand, speaker_name, version):
    # 2 files per directory xxx_H_IR.mat and xxx_V_IR.mat
    dirname = '{0}/ErinsAudioCorner/{1}'.format(speaker_path, speaker_name)

    h_spl = parse_graph_splHVtxt(dirname, 'H')
    v_spl = parse_graph_splHVtxt(dirname, 'V')

    return filter_graphs(speaker_name, h_spl, v_spl)


