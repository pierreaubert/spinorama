#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
import glob
import os
import shutil
from pathlib import Path
import sys

from datas.metadata import speakers_info as metadata

skeys = {}
brands = {}
models = {}

# some exceptions, i have too lazy to implement the code for these ones
manual_exceptions_table = {
    "Alcons Audio 2xQR24+2QM24.zip": ("Alcons Audio QR24", "vendor-v2QR24+2QM24"),
    "Alcons Audio 3xQR24+1xQM24.zip": ("Alcons Audio QR24", "vendor-v3QR24+1QM24"),
    "DB Audiotechnik AL60 x3 + 2 sub.zip": (
        "DB Audiotechnik AL60",
        "vendor-pattern-60x30-v3x+2sub",
    ),
    "DB Audiotechnik AL60 x3.zip": ("DB Audiotechnik AL60", "vendor-pattern-60x30-v3x"),
    "DB Audiotechnik AL60.zip": ("DB Audiotechnik AL60", "vendor-pattern-60x30-v1x"),
    "DB Audiotechnik AL90 x3.zip": ("DB Audiotechnik AL90", "vendor-pattern-90x30-v3x"),
    "DB Audiotechnik AL90.zip": ("DB Audiotechnik AL90", "vendor-pattern-90x30-v1x"),
    "K ARRAY Dragon KX12 KRX x1.zip": ("K ARRAY Dragon KX12", "vendor-configuration-krx-1x"),
    "K ARRAY Dragon KX12 KRX x2.zip": ("K ARRAY Dragon KX12", "vendor-configuration-krx-2x"),
    "K ARRAY Dragon KX12 KRX x3.zip": ("K ARRAY Dragon KX12", "vendor-configuration-krx-3x"),
    "Kling Freitag Spectral LS FR.zip": ("Kling Freitag Spectra", "vendor-narrow"),
    "Kling Freitag Spectral PS FR.zip": ("Kling Freitag Spectra", "vendor-wide"),
    "Meyer Sound Ultra X40.zip": ("Meyer Sound Ultra X40", "vendor-v2-20230107"),
    "EV MFX-15MC FR FOH.zip": ("EV MFX-15MC", "vendor-pattern-60x40"),
    "EV MFX-15MC FR MON.zip": ("EV MFX-15MC", "vendor-pattern-40x60"),
    "EV MFX-12MC FR FOH.zip": ("EV MFX-12MC", "vendor-pattern-60x40"),
    "EV MFX-12MC FR MON.zip": ("EV MFX-12MC", "vendor-pattern-40x60"),
    "EV EVC 1082 90x60.zip": ("EV EVC-1082", "vendor-pattern-90x60"),
    "EV EVC 1122 90x55.zip": ("EV EVC-1122", "vendor-pattern-90x55"),
    "EV EVC 1152 90x55.zip": ("EV EVC-1152", "vendor-pattern-90x55"),
    "EV MTS 4153 60x40.zip": ("EV MTS-4153", "vendor-pattern-60x40"),
    "EV MTS 4153 40x30.zip": ("EV MTS-4153", "vendor-pattern-40x30"),
    "EV MTS 6154 60x40.zip": ("EV MTS-6154", "vendor-pattern-60x40"),
    "EV MTS 6154 40x30.zip": ("EV MTS-6154", "vendor-pattern-40x30"),
}


def process(zipfile, speaker, destination_path):
    """Move the zipfile and cleanup"""
    pwd = os.getcwd()
    destination = Path(pwd) / destination_path

    if not destination.exists():
        print("error destination directory {} does not exist".format(destination))
        return
    if not destination.is_dir():
        print("error destination directory {} exist but is not a directory".format(destination))
        return
    if not os.path.exists(zipfile):
        print("error zipfile {} does not exist".format(zipfile))
        return

    # print('mv {}.zip to {}'.format(speaker, destination))
    destination_zipfile = destination / os.path.basename(zipfile)
    if destination_zipfile.exists():
        os.unlink(destination_zipfile)
    shutil.move(zipfile, destination)
    # print('git remove  {}/*.txt'.format(destination))
    txts = glob.glob(f"{destination}/*.txt")
    for t in txts:
        os.unlink(t)

    # print('git remove  {}/*/*.txt'.format(destination))
    txts = glob.glob(f"{destination}/*/*.txt")
    for t in txts:
        os.unlink(t)
    # print('rmdir {}/*'.format(destination))
    dirs = glob.glob(f"{destination}/*")
    for d in dirs:
        if os.path.isdir(d):
            shutil.rmtree(d)


def edit_meta_change_spltogll(speaker):
    # print("change format for {} {} from SPL to GLL".format(speaker))
    pass


def guess(speaker):
    """Can we guess the real speaker if we do not find a proper match?"""
    tokens = speaker.split()

    # last token
    guess_1 = " ".join(tokens[-1])
    if guess_1 in metadata.keys():
        return guess_1

    # last 2 tokens
    guess_2 = " ".join(tokens[-2])
    if guess_2 in metadata.keys():
        return guess_2

    # forget part of brand
    brand = tokens[0]
    model = tokens[1:]
    guess_3 = " ".join([brand] + model)
    if guess_3 in metadata.keys():
        return guess_3

    # lower / upper mismatch
    guess_4 = speaker.lower()
    if guess_4 in skeys:
        for k in metadata.keys():
            if k.lower() == guess_4:
                return k

    #
    brand1 = tokens[0]
    brand2 = " ".join(tokens[0:2])
    if brand1 not in brands and brand2 not in brands:
        possible_brand = None
        for k, v in metadata.items():
            if v["brand"].lower().startswith(tokens[0].lower()):
                possible_brand = v["brand"]
        print("Brand is not known for {}: it could be {}".format(speaker, possible_brand))
        model1 = " ".join(tokens[1:2])
        model2 = " ".join(tokens[2:3])
        model3 = " ".join(tokens[1:3])
        if model1.lower() in models:
            print("Model {} is known".format(model1))
        elif model2.lower() in models:
            print("Model {} is known".format(model2))
        elif model3.lower() in models:
            print("Model {} is known".format(model3))
        else:
            print("Model is not known for {}".format(speaker))

    return None


def match(version, name):
    """Implement some basic matching between the name in Windows and the name in the metadata file"""
    if version in name:
        return True
    if (
        version[0] == "x"
        and len(version) > 1
        and version[1].isdigit()
        and "v{}".format(version[1:]) in name
    ):
        return True
    if version[0] == "[" and version[-1] == "]":
        parts = version[1:-1].split()
        zero = False
        one = False
        if parts[0] == "BR" and "bassreflex" in name:
            zero = True
        elif parts[0] == "C" and "cardioid" in name:
            zero = True

        if parts[1] == "W" and "wide" in name:
            one = True
        elif parts[1] == "N" and "narrow" in name:
            one = True
        elif parts[1] == "M" and "medium" in name:
            one = True
        # print("debug parts[0]={} parts[1]={} return {}".format(parts[0], parts[1], zero and one))
        return zero and one
    if version[0:4] == "FR+H" and version[4:].isdigit():
        return version[4:] in name
    if version == "FR":
        return "fullrange" in name
    if version == "LowCut":
        return "lowcut" in name
    if version == "Passiv":
        return "passive" in name
    # danley's: 96 == 90x60
    if version.isdigit() and len(version) == 2 and "{}0x{}0".format(version[0], version[1]) in name:
        return True

    # some exceptions
    if version == "wide":
        return True

    return False


def find_speaker(zipfile):
    """ "Find and process each zipfile"""
    # remove .zip
    base_speaker = os.path.basename(zipfile)
    speaker = base_speaker[:-4]

    version = None
    manual_exception = False
    if base_speaker in manual_exceptions_table.keys():
        speaker, version = manual_exceptions_table[base_speaker]
        manual_exception = True
    elif speaker not in metadata.keys():
        tokens = speaker.split()
        for pos in range(1, min(len(tokens), 5)):
            candidate = " ".join(tokens[:-pos])
            if candidate in metadata.keys():
                speaker = candidate
                version = " ".join(tokens[-pos:])

    # print("debug speaker={} version={} exception={}".format(speaker, version, manual_exception))

    if speaker in metadata.keys() and version is None:
        # easy case
        measurements = metadata[speaker]
        # find the correct measurement
        count_gll = 0
        count_spl = 0
        gll_name = None
        spl_name = None
        for name, data in measurements["measurements"].items():
            if data["format"] == "gllHVtxt":
                count_gll += 1
                gll_name = name
            elif data["format"] == "splHVtxt":
                count_spl += 1
                spl_name = name

        if count_gll == 1:
            destination = "datas/measurements/{}/{}".format(speaker, gll_name)
            process(zipfile, speaker, destination)
            return 0

        if count_spl == 1:
            destination = "datas/measurements/{}/{}".format(speaker, spl_name)
            process(zipfile, speaker, destination)
            edit_meta_change_spltogll(speaker)
            return 0

        if count_gll + count_gll > 1:
            print("warning too many measurements for {}".format(speaker))
            return 0

    if speaker in metadata.keys() and version is not None:
        # easy case
        measurements = metadata[speaker]
        # find the correct measurement
        count_gll = 0
        count_spl = 0
        gll_name = None
        spl_name = None
        # look for exact matches first
        for name, data in measurements["measurements"].items():
            if data["format"] == "gllHVtxt" and version == name:
                count_gll += 1
                gll_name = name
            elif data["format"] == "splHVtxt" and version == name:
                count_spl += 1
                spl_name = name

        # print('debug 1 version={} name={} format={} #gll={} #spl={}'.format(version, gll_name, data["format"], count_gll, count_spl))

        # if not look for partial matches
        if count_gll + count_spl == 0:
            for name, data in measurements["measurements"].items():
                if data["format"] == "gllHVtxt" and match(version, name):
                    count_gll += 1
                    gll_name = name
                elif data["format"] == "splHVtxt" and match(version, name):
                    count_spl += 1
                    spl_name = name

        # print('debug 2 version={} name={} format={} #gll={} #spl={}'.format(version, gll_name, data["format"], count_gll, count_spl))

        if count_gll == 1:
            destination = "datas/measurements/{}/{}".format(speaker, gll_name)
            # print("goal {} goes to {}".format(zipfile, destination))
            process(zipfile, speaker, destination)
            return 0

        if count_spl == 1:
            destination = "datas/measurements/{}/{}".format(speaker, spl_name)
            # print("goal {} goes to {}".format(zipfile, destination))
            process(zipfile, speaker, destination)
            edit_meta_change_spltogll(speaker)
            return 0

        if count_gll + count_gll > 1:
            print("warning too many measurements for {}".format(speaker))
            return 1

    if speaker in metadata.keys() and version is not None:
        measurements = metadata[speaker]
        if len(measurements["measurements"].keys()) == 1:
            destination = "datas/measurements/{}/{}".format(
                speaker, measurements["default_measurement"]
            )
            # print("goal {} goes to {}".format(zipfile, destination))
            process(zipfile, speaker, destination)
            return 0

    educated = guess(speaker)
    if educated is not None:
        print("error: didn't find ///{}/// but {} exist ".format(speaker, educated))
    else:
        print("error: didn't find ///{}///".format(speaker))

    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(-1)

    zip_file = sys.argv[1]

    if not os.path.exists(zip_file):
        print("error: {} does not exist!".format(zip_file))
        sys.exit(1)

    skeys = {k.lower() for k in metadata.keys()}
    brands = {v["brand"].lower() for _, v in metadata.items()}
    models = {v["model"].lower() for _, v in metadata.items()}

    STATUS = find_speaker(zip_file)
    sys.exit(STATUS)
