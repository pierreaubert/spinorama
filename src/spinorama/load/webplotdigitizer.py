import logging
import json
import math
import numpy as np
import os
import pandas as pd
import tarfile
from ..cea2034 import early_reflections, vertical_reflections, horizontal_reflections,\
     compute_cea2034, compute_onaxis, estimated_inroom, estimated_inroom_HV
from ..normalize import unify_freq, normalize_mean, normalize_cea2034, normalize_graph
from . import graph_melt

def parse_webplotdigitizer_get_jsonfilename(dirname, speaker_name):
    filename = dirname + '/' + speaker_name
    tarfilename = filename + '.tar'
    jsonfilename = None
    try:
        if os.path.exists(tarfilename):
            # we are looking for info.json that may or not be in a directory
            with tarfile.open(tarfilename, 'r|*') as tar:
                info_json = None
                for tarinfo in tar:
                    # print(tarinfo.name)
                    if tarinfo.isreg() and tarinfo.name[-9:] == 'info.json':
                        # note that files/directory with name tmp are in .gitignore
                        tar.extract(tarinfo, path=dirname+'/tmp', set_attrs=False)
                        info_json = dirname + 'tmp/' + tarinfo.name
                        with open(info_json, 'r') as f:
                            info = json.load(f)
                            jsonfilename = dirname + 'tmp/' + tarinfo.name[:-9] + info['json']
                            
            # now extract the large json file
            if jsonfilename is not None:
                with tarfile.open(tarfilename, 'r|*') as tar:
                    for tarinfo in tar:
                        if tarinfo.isfile() and tarinfo.name in jsonfilename:
                            logging.debug('Extracting: {0}'.format(tarinfo.name))
                            tar.extract(tarinfo, path=dirname+'/tmp', set_attrs=False)
                   
    except tarfile.ReadError as re:
        logging.error('Tarfile {0}: {1}'.format(tarfilename, re))
    if jsonfilename is None:
        jsonfilename = filename + '.json'
    logging.debug('Jsonfilename {0}'.format(jsonfilename))
    return jsonfilename


def parse_graph_freq_webplotdigitizer(filename):
    """ """
    # from 20Hz to 20kHz, log(2)~0.3
    ref_freq = np.logspace(1+math.log10(2), 4+math.log10(2), 500)
    #
    try:
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
                    if ref_f <= 20000 and ref_f > 0 and ref_db > -50 and ref_db < 200:
                        res.append([ref_f, ref_db, col['name']])
                    else:
                        logging.error('fr={:.2f} fr_ref={:.2f} fr_n={:.2f} db={:.1f} db_ref={:.1f} db_n={:.1f}'.format(fr, ref_f, frn, db, ref_db, dbn))
                        break

            # build dataframe
            # print(res)
            freq = np.array([res[i][0] for i in range(0, len(res))]).astype(np.float)
            dB   = np.array([res[i][1] for i in range(0, len(res))]).astype(np.float)
            mrt  = [res[i][2] for i in range(0, len(res))]
            df = pd.DataFrame({'Freq': freq, 'dB': dB, 'Measurements': mrt})
            # print(df)
            return 'CEA2034', df 
    except IOError as e:
        logging.error('Cannot not open: {0}'.format(e))
        return None, None
            

def parse_graphs_speaker_webplotdigitizer(speaker_brand, speaker_name):
    dfs = {}
    dirname = 'datas/Vendors/' + speaker_brand + '/' + speaker_name + '/'
    jsonfilename = parse_webplotdigitizer_get_jsonfilename(dirname, speaker_name)

    try:
        title, spin_uneven = parse_graph_freq_webplotdigitizer(jsonfilename)
        spin_even = unify_freq(spin_uneven)
        spin = graph_melt(spin_even)
        if title != 'CEA2034':
            logging.debug('title is {0}'.format(title))
            return spin

        if spin is not None:
            # compute EIR
            on = spin.loc[spin['Measurements'] == 'On Axis'].reset_index(drop=True)
            lw = spin.loc[spin['Measurements'] == 'Listening Window'].reset_index(drop=True)
            er = spin.loc[spin['Measurements'] == 'Early Reflections'].reset_index(drop=True)
            sp = spin.loc[spin['Measurements'] == 'Sound Power'].reset_index(drop=True)

            # check DI index
            sp_di_computed = lw.dB-sp.dB
            sp_di = spin.loc[spin['Measurements'] == 'Sound Power DI'].reset_index(drop=True) 
            if sp_di.shape[0] == 0:
                logging.debug('No Sound Power DI curve!')
                df2 = pd.DataFrame({'Freq': on.Freq, 'dB': sp_di_computed, 'Measurements': 'Sound Power DI'})
                spin = spin.append(df2).reset_index(drop=True)
            else:
                delta = np.mean(sp_di)-np.mean(sp_di_computed)
                logging.debug('Sound Power DI curve: removing {0}'.format(delta))
                spin.loc[spin['Measurements'] == 'Sound Power DI', 'dB'] -= delta

            # sp_di = spin.loc[spin['Measurements'] == 'Sound Power DI'].reset_index(drop=True)
            # print('Post treatment SP DI: shape={0} min={1} max={2}'.format(sp_di.shape, sp_di.dB.min(), sp_di.dB.max()))
            # print(sp_di)

            er_di_computed = lw.dB-er.dB
            er_di = spin.loc[spin['Measurements'] == 'Early Reflections DI'].reset_index(drop=True) 
            if er_di.shape[0] == 0:
                logging.debug('No Early Reflections DI curve!')
                df2 = pd.DataFrame({'Freq': on.Freq, 'dB': er_di_computed, 'Measurements': 'Early Reflections DI'})
                spin = spin.append(df2).reset_index(drop=True)
            else:
                delta = np.mean(er_di)-np.mean(er_di_computed)
                logging.debug('Early Reflections DI curve: removing {0}'.format(delta))
                spin.loc[spin['Measurements'] == 'Early Reflections DI', 'dB'] -= delta

            # er_di = spin.loc[spin['Measurements'] == 'Early Reflections DI'].reset_index(drop=True)
            # print('Post treatment ER DI: shape={0} min={1} max={2}'.format(er_di.shape, er_di.dB.min(), er_di.dB.max()))
            # print(er_di)

            di_offset = spin.loc[spin['Measurements'] == 'DI offset'].reset_index(drop=True) 
            if di_offset.shape[0] == 0:
                logging.debug('No DI offset curve!')
                df2 = pd.DataFrame({'Freq': on.Freq, 'dB': 0, 'Measurements': 'DI offset'})
                spin = spin.append(df2).reset_index(drop=True)
                
            # print(on.shape, lw.shape, er.shape, sp.shape)
            eir = estimated_inroom(lw, er, sp)
            # print('eir {0}'.format(eir.shape))
            # print(eir)
            logging.debug('eir {0}'.format(eir.shape))
            dfs['Estimated In-Room Response'] = graph_melt(eir)

            # add spin (at the end because we could have modified DI curves
            dfs[title] = spin

    except FileNotFoundError:
        logging.info('Speaker: {0} Not found: {1}'.format(speaker_name, jsonfilename))
    return dfs
        
    
