# -*- coding: utf-8 -*-
#
import sys

# Kef ls50 w II
# FIXED = 150 # Hz
# CUTOFF = 300  # Hz
# SPLDELTA = 81.83-98.41
# CUTOFF = 200  # Hz
# SPLDELTA = 81.83-96.69

# Elac Debut
# FIXED = 150  # Hz
# CUTOFF = 300  # Hz
# SPLDELTA = 84.77 - 68.36

# Elac BS
FIXED = 300  # Hz
CUTOFF = 400  # Hz
SPLDELTA = -2  # 70.69 - 68.80


# CUTOFF = 200  # Hz
# SPLDELTA = 85.6 - 66.6
# CUTOFF = 125  # Hz
# SPLDELTA = 87.146 - 64.61

refFreq = [
    20.5078,
    21.9727,
    23.4375,
    24.9023,
    26.3672,
    27.832,
    29.2969,
    30.7617,
    32.2266,
    33.6914,
    35.1562,
    36.6211,
    38.0859,
    39.5508,
    41.0156,
    42.4805,
    43.9453,
    45.4102,
    46.875,
    48.3398,
    51.2695,
    52.7344,
    54.1992,
    55.6641,
    58.5938,
    60.0586,
    62.9883,
    64.4531,
    67.3828,
    68.8477,
    71.7773,
    74.707,
    77.6367,
    79.1016,
    82.0312,
    84.9609,
    87.8906,
    90.8203,
    95.2148,
    98.1445,
    101.074,
    105.469,
    108.398,
    112.793,
    117.188,
    120.117,
    124.512,
    128.906,
    133.301,
    139.16,
    143.555,
    147.949,
    153.809,
    159.668,
    165.527,
    171.387,
    177.246,
    183.105,
    188.965,
    196.289,
    203.613,
    210.938,
    218.262,
    225.586,
    232.91,
    241.699,
    250.488,
    259.277,
    268.066,
    276.855,
    287.109,
    297.363,
    307.617,
    319.336,
    329.59,
    341.309,
    353.027,
    366.211,
    379.395,
    392.578,
    405.762,
    420.41,
    435.059,
    451.172,
    465.82,
    483.398,
    499.512,
    517.09,
    536.133,
    555.176,
    574.219,
    594.727,
    615.234,
    637.207,
    659.18,
    682.617,
    707.52,
    732.422,
    757.324,
    785.156,
    811.523,
    840.82,
    870.117,
    900.879,
    933.105,
    965.332,
    1000,
    1035,
    1072,
    1108,
    1148,
    1189,
    1230,
    1274,
    1319,
    1366,
    1413,
    1463,
    1516,
    1568,
    1624,
    1681,
    1741,
    1803,
    1866,
    1932,
    1999,
    2069,
    2143,
    2219,
    2296,
    2378,
    2462,
    2548,
    2639,
    2731,
    2828,
    2928,
    3030,
    3137,
    3249,
    3363,
    3481,
    3604,
    3732,
    3864,
    4000,
    4141,
    4287,
    4438,
    4595,
    4756,
    4924,
    5097,
    5277,
    5463,
    5657,
    5856,
    6062,
    6276,
    6498,
    6726,
    6963,
    7209,
    7464,
    20,
    7727,
    7999,
    8282,
    8573,
    8876,
    9188,
    9514,
    9849,
    10196,
    10555,
    10927,
    11313,
    11712,
    12126,
    12553,
    12996,
    13454,
    13929,
    14419,
    14928,
    15455,
    16000,
    16564,
    17148,
    17752,
    18379,
    19026,
    19697,
    19999,
]


def process_onaxis(speaker):
    freqs = []
    spls = []
    with open("Frequency_SPL curve.txt", "r") as datas:
        lines = datas.readlines()
        for line in lines:
            items = line.split()
            if len(items) != 2:
                continue
            freq = items[0]
            spl = items[1]
            freqs.append(float(freq.replace(",", "")))
            spls.append(float(spl.replace(",", "")))
    return (freqs, spls)


def interpolate(onaxis, freq):
    # return closest spl at freq
    i = 0
    while onaxis[0][i] <= freq:
        i += 1
    freqmin = onaxis[0][i]
    # dn't be smart
    return freq, onaxis[1][i]

    # if freqmin == freq:
    #    return freq, onaxis[1][i]

    # freqmax = onaxis[0][i + 1]
    # if freq < freqmax:
    #    splmin = onaxis[1][i]
    #    splmax = onaxis[1][i + 1]
    #    spldelta = (splmax - splmin) / (freq - freqmin)
    #    if splmin + spldelta > max(splmin, splmax):
    #        print(
    #            "error freq={} f min={} fmax={} spl min={} max={} delta={}".format(
    #                freq, freqmin, freqmax, splmin, splmax, spldelta
    #            )
    #        )
    #    return freq, splmin + spldelta

    # print("error")


def process_hv(speaker, direction, onaxis):
    files = {}
    for angle in range(-180, 190, 10):
        files["{}".format(angle)] = open("{} _{} {}.txt".format(speaker, direction[0], angle), "w")
        files["{}".format(angle)].write("Freq Spl Phase\n")
        for freq in refFreq:
            if freq >= FIXED:
                continue
            freqOn, splOn = interpolate(onaxis, freq)
            if freqOn == 20.0:
                continue
            # print('debug {} {} {}'.format(freq, freqOn, splOn))
            files["{}".format(angle)].write("{} {} 0.0\n".format(freqOn, splOn))

    with open("{} Contour Plot.txt".format(direction), "r") as data:
        lines = data.readlines()

        for line in lines:
            items = line.split()
            if len(items) != 3:
                continue
            freq = items[0]
            spl = items[1]
            angle = items[2]

            # print("{} {} {}".format(freq, spl, angle))
            if angle not in files:
                print(files.keys())
                continue

            ffreq = float(freq.replace(",", ""))
            fspl = float(spl.replace(",", ""))
            if ffreq >= CUTOFF:
                fspl += SPLDELTA
                files[angle].write("{} {} 0.0\n".format(ffreq, fspl))
            # elif ffreq >= FIXED:
            #    computed =
            #    files[angle].write("{} {} 0.0\n".format(ffreq, computed))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(-1)

    speaker = sys.argv[1]
    onaxis = process_onaxis(speaker)
    process_hv(speaker, "Horizontal", onaxis)
    process_hv(speaker, "Vertical", onaxis)
