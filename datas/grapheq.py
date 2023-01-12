# -*- coding: utf-8 -*-
#

import math

# conversion from bandwidth to Q
# http://www.sengpielaudio.com/calculator-bandwidth.htm


def bandwidth2Q(bw):
    pbw = math.pow(2, bw)
    return math.sqrt(pbw) / (pbw - 1)


vendor_info = {
    "Altair EQ-215": {
        "gain_p": 6,  # dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            25,
            40,
            100,
            250,
            400,
            630,
            1000,
            1600,
            2500,
            4000,
            6300,
            10000,
            16000,
        ],
        # 2/3 octave
        "fixed_q": bandwidth2Q(2 / 3),
    },
    "Subzero SZEQ-215": {  # yet another clone
        "gain_p": 6,  # dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            25,
            40,
            100,
            250,
            400,
            630,
            1000,
            1600,
            2500,
            4000,
            6300,
            10000,
            16000,
        ],
        # 2/3 octave
        "fixed_q": bandwidth2Q(2 / 3),
    },
    "Altair EQ-230": {
        "gain_p": 6,  # dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
    "Behringer FBQ3102HD": {
        "gain_p": 6,  # dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
    "DBX 1231": {
        "gain_p": 6,  # dB can do more up to +/- 15dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
    "DBX 2231": {
        "gain_p": 6,  # dB can do more up to +/- 15dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
    "DBX 321S": {
        "gain_p": 6,  # dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
    "KlarkTecknik DN360": {
        "gain_p": 6,  # dB can do more up to +/- 15dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
    # this one has a proportional Q but I do not understand what that means
    #
    "KlarkTecknik DN370": {
        "gain_p": 6,  # dB can do more up to +/- 15dB
        "gain_m": -6,  # dB
        "steps": 1,  # dB
        "bands": [
            20,
            25,
            31.5,
            40,
            50,
            63,
            80,
            100,
            125,
            160,
            200,
            250,
            315,
            400,
            500,
            630,
            800,
            1000,
            1250,
            1600,
            2000,
            2500,
            3150,
            4000,
            5000,
            6300,
            8000,
            10000,
            12000,
            16000,
            20000,
        ],
        # 1/3 octave
        "fixed_q": bandwidth2Q(1 / 3),
    },
}
