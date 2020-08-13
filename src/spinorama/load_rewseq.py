#                                                  -*- coding: utf-8 -*-
import logging
import numpy as np
import pandas as pd
from .filter_iir import Biquad

# TODO(pierre): max rgain and max Q should be in parameters

def parse_eq_iir_rews(filename, srate):
    peq = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for l in lines:
                if len(l)>0 and l[0] == '*':
                    continue
                words = l.split()
                if len(words) == 12 and words[0] == 'Filter':
                    if words[2] == 'ON':
                        status = 1
                    else:
                        status = 0
                        
                    kind = words[3]
                    freq = words[5]
                    gain = words[8]
                    q    = words[11]

                    ifreq = int(freq)
                    if ifreq < 0 or ifreq > srate/2:
                        logging.info('IIR peq freq {0}Hz out of bounds (srate={1}'.format(freq, srate))
                        continue

                    rgain = float(gain)
                    if rgain < -10 or rgain > 10:
                        logging.info('IIR peq gain {0} is large!'.format(rgain))
                        # continue

                    rq = float(q)
                    if rq < 0 or rq > 10:
                        logging.info('IIR peq Q {0} is out of bounds!'.format(rq))
                        # continue

                    if kind == 'PK':
                        iir = Biquad(Biquad.PEAK, ifreq, srate, rq, rgain)
                        logging.debug('add IIR peq PEAK freq {0}Hz srate {1} Q {2} Gain {3}'.format(ifreq, srate, rq, rgain))
                        peq.append((status, iir))
                    else:
                        logging.warning('kind {0} is unknown'.format(kind))

    except FileNotFoundError:
        logging.info('Loading filter: eq file {0} not found'.format(filename))
    return peq
        
    
