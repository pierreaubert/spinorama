#!/usr/bin/python3
# -*- coding: utf-8 -*-
#

from pathlib import Path
from shutil import copy
import sys
import glob
import os
import numpy as np


def kef2dict(kef_dir: str) -> dict[str, list[float]]:
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


def interpolate(kef: dict[str, list[float]], cut_freq_high: float) -> dict[str, list[float]]:
    merged = {}
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
    for curve, measurement in kef.items():
        if curve == "freq":
            merged[curve] = kef["freq"]
            continue
        # data from KEF valid above cut_freq
        spl_kef = measurement
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


def data_save(dir: str, curves):
    freq = curves["freq"]
    for curve in curves:
        if curve == "freq":
            continue
        filename = f"{dir}/{curve}.txt"
        if os.path.exists(filename):
            print("warning cowardly not overriding {}".format(filename))
            continue
        with open(filename, "w") as fd:
            print(filename)
            print(len(freq), len(curves[curve]))
            fd.writelines([f"{f} {c}\n" for f, c in zip(freq, curves[curve], strict=True)])


def process_copy(dirname, speaker_in, speaker_out):
    # check dirs
    dir_out = Path(f"./datas/measurements/{speaker_out}")

    if not dir_out.exists() or not dir_out.is_dir():
        print("warning: path {} does not exist!".format(dir_out))

    dir_vendor = Path(f"{dir_out}/vendor")
    dir_vendor1 = Path(f"{dir_out}/vendor-v1")
    dir_vendor2 = Path(f"{dir_out}/vendor-v2")
    dir_vendor2k = Path(f"{dir_out}/vendor-v2/from-kef")
    if dir_vendor.exists() and not dir_vendor1.exists():
        dir_vendor.replace(dir_vendor1)
    dir_vendor2k.mkdir(mode=0o755, parents=True, exist_ok=True)

    # copy files
    for i, name in [(1, "On Axis"), (2, "LW"), (3, "ER"), (4, "SP")]:
        file_in = Path(f"{dirname}/{speaker_in}_Spinorama_00{i}.txt")
        if not file_in.exists():
            print("error {} does not exist!".format(file_in))
            continue
        file_out = Path(f"{dir_vendor2k}/{name}.txt")
        copy(file_in, file_out)

    # interpolate data and save the result
    data = kef2dict(dir_vendor2k.as_posix())
    interpolated = interpolate(data, 300)
    data_save(dir_vendor2.as_posix(), interpolated)


def run(dirname):
    files = glob.glob(f"{dirname}/*.txt")
    if len(files) < 4:
        print("Error: are you sure it is the correct directory?")
        return

    speakers = {
        "R2Meta": "KEF R2C Meta",
        "R3Meta": "KEF R3 Meta",
        "R5Meta": "KEF R5 Meta",
        "R6Meta": "KEF R6C Meta",
        "R7Meta": "KEF R7 Meta",
        "R11Meta": "KEF R11 Meta",
        "Reference1Meta": "KEF Reference 1 Meta",
        "Reference2Meta": "KEF Reference 2C Meta",
        "Reference3Meta": "KEF Reference 3 Meta",
        "Reference4Meta": "KEF Reference 4C Meta",
        "Reference5Meta": "KEF Reference 5 Meta",
        "BladeOneMeta": "KEF Blade 1 Meta",
        "BladeTwoMeta": "KEF Blade 2 Meta",
    }

    for speaker_i, speaker_o in speakers.items():
        process_copy(dirname, speaker_i, speaker_o)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: {} path_to_kef_data".format(sys.argv[0]))
        sys.exit(-1)
    run(
        dirname=sys.argv[1],
    )
