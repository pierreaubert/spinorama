import logging
import math
from math import log10, isnan
from scipy.stats import linregress
import numpy as np
import pandas as pd


def estimates(onaxis: pd.DataFrame):
    estimates_error = [-1, -1, -1, -1]
    try:
        freq_min = onaxis.Freq.min()
        logging.debug('Freq min: {0}'.format(freq_min))
        if math.isnan(freq_min):
            logging.warning('Estimates failed for onaxis {0}'.format(onaxis.shape))
            return estimates_error
        if freq_min < 300:
            # mean over 300-10k
            y_ref = np.mean(onaxis.loc[(onaxis.Freq >= 300) & (onaxis.Freq <= 10000)].dB)
            y_3 = onaxis.loc[(onaxis.Freq < 150) & (onaxis.dB <= y_ref-3)].Freq.max()
            y_6 = onaxis.loc[(onaxis.Freq < 150) & (onaxis.dB <= y_ref-6)].Freq.max()
            # search band up/down
            up:   float = onaxis.loc[(onaxis.Freq >= 100) & (onaxis.Freq <= 10000)].dB.max()
            down: float = onaxis.loc[(onaxis.Freq >= 100) & (onaxis.Freq <= 10000)].dB.min()
            band = max(abs(up-y_ref), abs(y_ref-down))
            est = [round(y_ref, 0), round(y_3, 0), round(y_6, 0), round(band, 1)]
            logging.debug('Estimates: {0}'.format(est))
            return est
        else:
            y_ref = np.mean(onaxis.loc[(onaxis.Freq >= freq_min) & (onaxis.Freq <= 10000)].dB)
            # search band up/down
            up:   float = onaxis.loc[(onaxis.Freq >= freq_min) & (onaxis.Freq <= 10000)].dB.max()
            down: float = onaxis.loc[(onaxis.Freq >= freq_min) & (onaxis.Freq <= 10000)].dB.min()
            band = max(abs(up-y_ref), abs(y_ref-down))
            est = [round(y_ref, 0), -1, -1, round(band, 1)]
            logging.debug('Estimates: {0}'.format(est))
            return est
    except TypeError as te:
        logging.warning('Estimates failed for {0} with {1}'.format(onaxis.shape, te))
        return estimates_error
    except ValueError as ve:
        logging.warning('Estimates failed for {0} with {1}'.format(onaxis.shape, ve))
        return estimates_error