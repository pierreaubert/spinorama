#                                                  -*- coding: utf-8 -*-
import logging
import math
import numpy as np


def directivity_matrix(splH, splV):
    # print(splH.shape, splV.shape)
    # print(splH.head())
    # print(splV.head())
    if splH is None or splV is None:
        logging.info("Skipping directivty matrix, one measurement at least is empty")
        return None

    if splH.isnull().values.any() or splV.isnull().values.any():
        logging.info("Skipping directivty matrix, one value at least is NaN")
        return None

    n = splH.Freq.shape[0]
    r = np.floor(np.logspace(1.0 + math.log10(2), 4.0 + math.log10(2), n))
    x, y = np.meshgrid(r, r)
    splV = splV.set_index("Freq")
    splH = splH.set_index("Freq")
    zU = splV.dot(splH.T)
    zD = splV.dot(splV.T) * splH.dot(splH.T)
    # not completly sure why it is possible to get negative values
    zD[zD < 0] = 0.0
    z = zU / np.sqrt(zD) - 1.0
    return (x, y, z)
