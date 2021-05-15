#!/usr/bin/env python3
# encoding: utf-8
#
import glob
import sys
import os
import pathlib
import shutil

from string import Template

import datas.metadata as metadata

known_brands = set(v["brand"] for k, v in metadata.speakers_info.items())


def exec_git(command):
    print(command)


def move_data(speaker_name, speaker_data):

    brand = speaker_data["brand"]
    model = speaker_data["model"]

    root = "./datas/measurements"
    target_dir = "{}/{}/{}".format(root, brand, speaker_name)
    pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

    for measurement_name, measurement_data in speaker_data["measurements"].items():
        measurement_dir = "{}/{}".format(target_dir, measurement_name)
        pathlib.Path(measurement_dir).mkdir(parents=True, exist_ok=True)

        origin = measurement_data["origin"]

        if origin == "ASR":
            from_dir = "./datas/ASR/{}".format(speaker_name)
            for file in glob.glob(from_dir + "/*.txt"):
                exec_git('git mv "{}" "{}"'.format(file, measurement_dir))
            for file in glob.glob(from_dir + "/asr*"):
                exec_git('git mv "{}" "{}"'.format(file, measurement_dir))
        elif origin == "ErinsAudioCorner":
            from_dir = "./datas/ErinsAudioCorner/{}".format(speaker_name)
            scan = glob.glob(from_dir + "/*")
            found = False
            for unk in scan:
                if os.path.isdir(unk) and unk[-3:] != "tmp":
                    exec_git('git mv "{}" "{}"'.format(unk, measurement_dir))
                    found = True
                elif os.path.isfile(unk) and len(unk) > 5 and unk[-4:] == ".tar":
                    exec_git('git mv "{}" "{}"'.format(unk, measurement_dir))
                    found = True
                elif os.path.isfile(unk) and len(unk) > 5 and unk[-4:] == ".txt":
                    exec_git('git mv "{}" "{}"'.format(unk, measurement_dir))
                    found = True
            # if not found or unk[-2:] == 'tmp':
            #    print("ERROR error for {}".format(speaker_name))
        elif origin == "Misc" or "Vendor" in origin:
            if "Vendor" in origin:
                origin = "Vendors"
            from_dir = "./datas/{}/{}/{}".format(origin, brand, speaker_name)

            tar_name = "{}/{}.tar".format(from_dir, speaker_name)
            if os.path.exists(tar_name):
                exec_git('git mv "{}" "{}"'.format(tar_name, measurement_dir))
                continue

            tar_name = "{}/{}/{}.tar".format(from_dir, measurement_name, speaker_name)
            if os.path.exists(tar_name):
                exec_git('git mv "{}" "{}"'.format(tar_name, measurement_dir))
                continue

            json_name = "{}/{}.json".format(from_dir, speaker_name)
            if os.path.exists(json_name):
                exec_git('git mv "{}" "{}"'.format(json_name, measurement_dir))
                continue

            json_name = "{}/{}/{}.json".format(from_dir, measurement_name, speaker_name)
            if os.path.exists(json_name):
                exec_git('git mv "{}" "{}"'.format(json_name, measurement_dir))
                continue

            txt_name = glob.glob("{}/*.txt".format(from_dir, speaker_name))
            if len(txt_name) > 0:
                for txt in txt_name:
                    if os.path.exists(txt):
                        exec_git('git mv "{}" "{}"'.format(txt, measurement_dir))
                continue

            # print("ERROR error for {}".format(speaker_name))


if __name__ == "__main__":

    for speaker_name, speaker_data in metadata.speakers_info.items():
        # print("DEBUG {}".format(speaker_name))
        move_data(speaker_name, speaker_data)
