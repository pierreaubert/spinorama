#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
import os
import json
import sys


import numpy as np
import pandas as pd


def process_json(filename: str) -> pd.DataFrame:
    df_cea2034 = pd.DataFrame()

    with open(filename) as fd:
        cea2034 = json.load(fd)

        # on_freq = cea2034['data'][0]['x']
        # on_spl  = cea2034['data'][0]['y']
        # print(on_freq, on_spl)
        for data in cea2034["data"]:
            curve = {
                "On Axis": "On Axis",
                "Listening Window": "LW",
                "Sound Power": "SP",
                "Early Reflections": "ER",
            }.get(data["name"], "??")
            if curve == "??" and "DI" not in data["name"]:
                print("error: curve is unknown {}".format(data["name"]))
                continue
            freq = data["x"]
            spl = data["y"]
            if curve == "On Axis":
                df_cea2034["freq"] = freq
            df_cea2034[curve] = spl

    return df_cea2034


def process_kef(kef_dir: str) -> dict[str, list[float]]:
    kef = {}
    for curve in ("On Axis", "LW", "ER", "SP"):
        with open(f"{kef_dir}/{curve}.txt") as fd:
            lines = fd.readlines()
            freq = []
            spl = []
            for line in lines:
                data = line.split()
                if len(data) != 2:
                    if len(data) != 0:
                        print("error line does not have 2 fields >>{}<<".format(data))
                    continue
                try:
                    spl.append(float(data[1]))
                    if curve == "On Axis":
                        freq.append(float(data[0]))
                except ValueError:
                    print("value is not a float {}".format(data[1]))
                    continue
            if curve == "On Axis":
                kef["freq"] = freq
            kef[curve] = spl
    return kef


def merge(
    kef: dict[str, list[float]], cea2034: pd.DataFrame, cut_freq_low: float, cut_freq_high: float
) -> dict[str, list[float]]:
    merged = {}
    # delta between the 2, could be small or large if one is already normalized
    # delta = kef["LW"][0] - cea2034["LW"].loc[cea2034.freq < cut_freq_high].to_numpy()[-1]
    # what's -6dB ? computed on On Axis since that's all we have?
    idx_300 = 0
    while kef["freq"][idx_300] < 300:
        idx_300 += 1
    idx_3000 = idx_300 + 1
    while kef["freq"][idx_3000] < 3000:
        idx_3000 += 1
    y_ref = np.mean(kef["On Axis"][idx_300:idx_3000])
    idx = 0
    while kef["On Axis"][idx] < y_ref:
        idx += 1
    # override
    cut_freq_low = kef["freq"][idx]
    idx_low = 0
    while kef["freq"][idx_low] < cut_freq_low:
        idx_low += 1
    idx_high = idx_low + 1
    while kef["freq"][idx_high] < cut_freq_high:
        idx_high += 1
    for curve in kef:
        if curve == "freq":
            merged[curve] = kef["freq"]
            continue
        # data from KEF valid above cut_freq
        spl_kef = kef[curve]
        # data from KEF but scanned (less precise but extend lower)
        # spl_cea2034 = cea2034[curve].loc[((cea2034.freq >= cut_freq_low) & (cea2034.freq < cut_freq_high))].to_numpy()
        if curve == "On Axis":
            merged[curve] = spl_kef
            continue
        l = idx_high - idx_low

        # do a basic linear interpoloation
        def interp(x, y, l):
            s = y - x
            return [kef["On Axis"][idx_low + i] + i * s / (l - 1) for i in range(l)]

        spl = (
            [s for s in kef["On Axis"][0:idx_low]]
            + interp(kef["On Axis"][idx_high], spl_kef[0], l)
            + [s for s in spl_kef]
        )
        merged[curve] = spl
    return merged


def save(dir: str, curves):
    freq = curves["freq"]
    for curve in curves:
        if curve == "freq":
            continue
        filename = f"{dir}/{curve}.txt"
        if os.path.exists(filename):
            print("warning cowardly not overriding {}".format(filename))
            continue
        with open(filename, "w") as fd:
            fd.writelines([f"{f} {c}\n" for f, c in zip(freq, curves[curve], strict=True)])


def run(cea2034_json, kef_in_dir, kef_out_dir):
    cea2034 = process_json(cea2034_json)
    kef = process_kef(kef_in_dir)
    kef_merged = merge(kef, cea2034, 80, 300)
    save(kef_out_dir, kef_merged)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(-1)
    run(
        cea2034_json=sys.argv[1],
        kef_in_dir=sys.argv[2],
        kef_out_dir=sys.argv[3],
    )
