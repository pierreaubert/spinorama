# -*- coding: utf-8 -*-
import logging
import numpy as np
from spinorama.filter_iir import Biquad


def main():
    srates = [44100, 48000, 96000]
    freqs = np.asarray([70, 80, 90, 100, 110, 120, 130])
    gains = [-3, 3, -1, 1]
    qs = [0.1, 1, 2, 5]
    types = [0, 1, 2, 3, 4, 5, 6]

    with open("test_biquad.cpp.txt", "r") as fd:
        lines = fd.readlines()
        i = 0
        for srate in srates:
            for t in types:
                for gain in gains:
                    for q in qs:
                        bq = Biquad(t, 100, srate, q, gain)
                        try:
                            dbs = bq.np_log_result(freqs)
                            for db in dbs:
                                val_py = db
                                val_cpp = float(lines[i].split()[0])
                                i += 1
                                if val_cpp == 0.0 and val_py == 0.0:
                                    continue
                                delta = 0.0
                                if abs(val_cpp) < 1.0e-5:
                                    delta = abs(val_py)
                                else:
                                    delta = abs(val_py - val_cpp) / val_cpp
                                    if delta > 0.0001:
                                        print(
                                            f"Error python {delta:+1.5f} {val_py:f} {val_cpp:f} srate={srate:5d} q={q:1.1f} type={t} gain={gain}"
                                        )
                        except OverflowError:
                            logging.exception(
                                "Error python srate=%5d q=%1.1f type=%s gain=%f", srate, q, t, gain
                            )


if __name__ == "__main__":
    main()
