#                                                  -*- coding: utf-8 -*-
import logging
import os
import glob
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .load import filter_graphs


logger = logging.getLogger('spinorama')


def parse_graph_splHVtxt(dirpath, orientation):
    df = pd.DataFrame()

    filenames = '{0}/*_{1}.txt'.format(dirpath, orientation)
    files = glob.glob(filenames)
    if len(files) == 0:
        filenames = '{0}/* _{1} *.txt'.format(dirpath, orientation)
        files = glob.glob(filenames)
        
    symmetry = True
    for file in files:
        format = os.path.basename(file).split()
        if len(format) > 2:
            angle = format[-1][:-4]
        else:
            angle = os.path.basename(file).split('_')[0]
            
        if int(angle) < 0:
            symmetry = False

    logger.info('Symmetrie is {}'.format(symmetry))

    dfs = []
    for file in files:
        freqs = []
        dbs = []

        # 2 possible formats:
        # 1. angle_H or angle_V.txt
        # 2. name _H angle.txt
        format = os.path.basename(file).split()
        if len(format) > 2:
            angle = format[-1][:-4]
        else:
            angle = os.path.basename(file).split('_')[0]
            
        if angle == '0':
            angle = 'On Axis'
        else:
            angle += '°'

        logger.debug('read file "{}" for angle "{}"'.format(file, angle))
        with open(file, 'r') as fd:
            lines = fd.readlines()
            for l in lines:
                # again 2 possible format
                # freq, db
                words = l[:-1].split(',')
                if len(words) == 2:
                    freqs.append(float(words[0]))
                    dbs.append(float(words[1]))
                    continue

                # freq db phase
                words = l.split()
                if  len(words) == 3:
                    freq = words[0]
                    db = words[1]
                    # skip first line
                    if freq[0] != 'F':
                        freqs.append(float(freq))
                        dbs.append(float(db))
                    continue

                logger.warning('unkown file format len words {} for line {}'.format(len(words), l))

        if angle == 'On Axis':
            dfs.append(pd.DataFrame({'Freq': freqs, angle: dbs}))
        else:
            if angle != '-180°':
                dfs.append(pd.DataFrame({angle: dbs}))
            if symmetry and orientation == 'H' and angle != '180°':
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
    if version == 'eac':
        dirname = '{0}/ErinsAudioCorner/{1}'.format(speaker_path, speaker_name)
    else:
        dirname = '{0}/ErinsAudioCorner/{1}/{2}'.format(speaker_path, speaker_name, version)

    logger.debug('scanning path {}'.format(dirname))

    h_spl = parse_graph_splHVtxt(dirname, 'H')
    v_spl = parse_graph_splHVtxt(dirname, 'V')

    return filter_graphs(speaker_name, h_spl, v_spl)


