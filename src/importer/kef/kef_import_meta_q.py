#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
import os
from pathlib import Path

import numpy as np


def kef2dict2(kef_dir: str) -> dict[str, tuple[list[float], list[float]]]:
    kef = {}
    for curve in ("On Axis", "LW", "ER", "SP"):
        with open(f"{kef_dir}/{curve}.txt") as fd:
            lines = fd.readlines()
            freq = []
            spl = []
            for line in lines:
                data = line.split()
                if len(data) < 2:
                    if len(data) != 0:
                        print("error line does not have 2 fields >>{}<<".format(data))
                    continue
                try:
                    spl.append(float(data[1]))
                    freq.append(float(data[0]))
                except ValueError:
                    print("value is not a float eithe {} or {}".format(data[0], data[1]))
                    continue
            kef[curve] = (freq, spl)
    return kef


def interpolate2(
    kef: dict[str, tuple[list[float], list[float]]], cut_freq_high: float
) -> dict[str, tuple[list[float], list[float]]]:
    merged = {}
    idx_300 = 0
    on_axis_freq = kef["On Axis"][0]
    on_axis_spl = kef["On Axis"][1]
    while on_axis_freq[idx_300] < cut_freq_high:
        idx_300 += 1
    idx_3000 = idx_300 + 1
    while on_axis_freq[idx_3000] < cut_freq_high * 10:
        idx_3000 += 1
    y_ref = np.mean(on_axis_spl[idx_300:idx_3000])
    idx = 0
    while on_axis_spl[idx] < y_ref:
        idx += 1
    # override
    cut_freq_low = on_axis_freq[idx]
    idx_low = 0
    while on_axis_freq[idx_low] < cut_freq_low:
        idx_low += 1
    idx_high = idx_low + 1
    while on_axis_freq[idx_high] < cut_freq_high:
        idx_high += 1
    ln = idx_high - idx_low

    # do a basic linear interpoloation
    def interp(x, y, l):
        s = y - x
        return [on_axis_spl[idx_low + i] + i * s / (l - 1) for i in range(l)]

    for curve in kef:
        # data from KEF valid above cut_freq
        if curve == "On Axis":
            merged[curve] = kef[curve]
        else:
            curve_freq = kef[curve][0]
            idx_300 = 0
            while curve_freq[idx_300] < cut_freq_high:
                idx_300 += 1
            curve_spl = kef[curve][1]
            # print('debug {} freq=[{},{}] spl=[{}, {}]'.format(curve, min(curve_freq), max(curve_freq), min(curve_spl), max(curve_spl)))
            freq = [f for f in on_axis_freq[0:idx_high]] + [f for f in curve_freq[idx_300:]]
            spl = (
                [s for s in on_axis_spl[0:idx_low]]
                + interp(on_axis_spl[idx_high], curve_spl[idx_300 - 1], ln)
                + curve_spl[idx_300:]
            )
            # tmp = list(zip(freq, spl, strict=True)).sort(key=lambda a: a[0])
            merged[curve] = (freq, spl)
        print(
            "curve {} ln {} freq #{} [{}, {}], spl #{} [{}, {}]".format(
                curve,
                ln,
                len(merged[curve][0]),
                min(merged[curve][0]),
                max(merged[curve][0]),
                len(merged[curve][1]),
                min(merged[curve][1]),
                max(merged[curve][1]),
            )
        )
    return merged


def data_save2(dir: str, curves):
    for curve in curves:
        filename = f"{dir}/{curve}.txt"
        # if os.path.exists(filename):
        #    print("warning cowardly not overriding {}".format(filename))
        #    continue
        with open(filename, "w") as fd:
            fd.writelines(
                [f"{f} {c}\n" for f, c in zip(curves[curve][0], curves[curve][1], strict=True)]
            )


def process_copy(speaker_name, path_in, path_out):
    print("Processing {}".format(speaker_name))
    dir_in = Path(path_in)
    if not dir_in.exists() or not dir_in.is_dir():
        print("warning: path {} does not exist!".format(dir_in))
        return
    dir_out = Path(path_out)
    if not dir_out.exists() or not dir_out.is_dir():
        print("warning: path {} does not exist!".format(dir_out))
        return

    # interpolate data and save the result
    data = kef2dict2(dir_in.as_posix())
    interpolated = interpolate2(data, 300)
    data_save2(dir_out.as_posix(), interpolated)


def run():
    speakers = (
        "KEF Q1 Meta",
        "KEF Q3 Meta",
        "KEF Q4 Meta",
        "KEF Q6 Meta",
        "KEF Q7 Meta",
        "KEF Q11 Meta",
        "KEF Q Concerto Meta",
    )

    for speaker in speakers:
        speaker_o = "./datas/measurements/{}/vendor".format(speaker)
        speaker_i = "{}/from-kef".format(speaker_o)
        process_copy(speaker, speaker_i, speaker_o)


if __name__ == "__main__":
    run()
