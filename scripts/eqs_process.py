#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from glob import glob
import json
import pathlib
import os
import shutil

from generate_common import find_metadata_file
from spinorama.auto_save import get_previous_score


def update_eq(speaker_name, from_dir, to_dir):
    to_path = pathlib.Path(to_dir)
    to_path.mkdir(mode=0x755, parents=False, exist_ok=True)
    for f in ("conf-autoeq.json", "iir.txt", "iir-autoeq.txt"):
        # 3.14
        # pathlib.Path('{}/{}'.format(from_dir, f)).copy_into(to_dir)
        from_file = "{}/{}".format(from_dir, f)
        shutil.copy(from_file, to_dir)


def process(speaker: str, metadata: dict):
    path = pathlib.Path(speaker)
    if not path.exists():
        print("Path {} does not exists?".format(path))
        return
    #
    speaker_name = os.path.basename(speaker)
    #
    prev_eq_path = "./datas/eq/{}/iir-autoeq.txt".format(speaker_name)
    prev_score = get_previous_score(prev_eq_path)
    prev_score = prev_score if prev_score is not None else -10.0
    # print('Prev score={}'.format(prev_score))
    #
    computed_eqs = path.glob("**/iir-autoeq.txt")
    # print('Found #{} eqs for {}'.format(len(list(computed_eqs)), speaker))
    best_score = prev_score
    best_eq = None
    for eqname in computed_eqs:
        new_score = get_previous_score(str(eqname))
        if new_score is not None and new_score > best_score:
            best_score = new_score
            best_eq = eqname
    if best_eq is not None:
        meta = metadata.get(speaker_name)
        if meta is None:
            print("no metadata for {}".format(speaker_name))
            return
        meta_default = meta["default_measurement"]
        measurement = meta["measurements"][meta_default]
        noeq_pref_rating = measurement.get("pref_rating")
        noeq_score = -10.0
        if noeq_pref_rating is not None:
            noeq_score = noeq_pref_rating.get("pref_score")
        print(
            "EQ: new {:4.2f} prev eq {:4.2f} noeq {:4.2f} {}".format(
                best_score, prev_score, noeq_score, speaker_name
            )
        )
        update_eq(speaker_name, os.path.dirname(best_eq), os.path.dirname(prev_eq_path))


def run():
    metadata_file, _ = find_metadata_file()
    jsmeta = {}
    with open(metadata_file, "r") as f:
        jsmeta = json.load(f)

    computed_speakers = glob("./build/eqs/*")
    for speaker in computed_speakers:
        process(speaker, jsmeta)


if __name__ == "__main__":
    run()
