#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import glob
import sys
import os
import pathlib
import shutil

from string import Template

import datas.metadata as metadata

known_brands = set(v["brand"].lower() for k, v in metadata.speakers_info.items())
# other new brands which are ok
known_brands.update(
    [
        "amphion",
        "devialet",
        "google",
        "hsu research",
        "martin logan",
        "monoprice",
        "outlaw audio",
        "rbh",
        "speakercraft",
        "sonos",
        "sonus faber",
    ]
)

change_brands = {
    "polk": "polk audio",
    "buchardt": "buchardt audio",
    "devialet’s": "devialet",
    "martinlogan": "martin logan",
}


def brand_cleanup(b):
    if b.lower() in ("jbl", "kef"):
        return b.upper()
    return b


table = {
    ord(" "): None,
    ord("'"): " ",
    ord(","): " ",
    ord("&"): "\&",
}


def match_speaker(look, references):
    # do we have a match if we lowercase and remove spaces?
    for reference in references:
        if look == reference:
            return True, reference

        slook = look.lower().translate(table)
        sreference = reference.lower().translate(table)
        if slook == sreference:
            return True, reference

        if slook in change_brands.keys() and change_brands[slook] == sreference:
            return True, reference

    return False, None


def guess_brand_model(speaker_name):
    brand = None
    chunk = speaker_name.split(" ")

    # print("{} chunk {}".format(speaker_name, chunk))

    # if chunk[0].lower() in change_brands.keys() and change_brands[chunk[0].lower()] in known_brands:
    #    print("Match with a change from {} to {}".format(chunk[0],change_brands[chunk[0].lower()]))

    if chunk[0].lower() in known_brands:
        return chunk[0].capitalize(), " ".join(chunk[1:])
    elif chunk[0].lower() in change_brands.keys() and change_brands[chunk[0].lower()] in known_brands:
        brand = " ".join([s.capitalize() for s in change_brands[chunk[0].lower()].split(" ")])
        return brand, " ".join(chunk[1:])
    elif len(chunk) > 1 and "{} {}".format(chunk[0].lower(), chunk[1].lower()) in known_brands:
        # print("match chunk {}".format(chunk))
        return "{} {}".format(chunk[0].capitalize(), chunk[1].capitalize()), " ".join(chunk[2:])
    else:
        # a few exceptions
        if speaker_name[0:13] == "Dutch & Dutch":
            return "Dutch Dutch", speaker_name[14:]
        elif speaker_name[0:16] == "Bowers & Wilkins":
            return "Bower Wilkins", speaker_name[18:]
        print("ERROR Please add brand if ok {}".format(speaker_name))

    return None, None


def get_review_key(reviewer_name):
    review_key = reviewer_name.lower()
    if review_key is None or len(review_key) == 0:
        print('Error: review_key is None or Empty, reviewer_name is "{}"'.format(review_key))
        return None
    if review_key[0] == "@":
        review_key = "misc-{}".format(review_key[1:])
    else:
        review_key = "misc-{}".format(review_key)
    return review_key


def get_review_src(speakerdir):
    review_src = None
    reviews_src = {}
    source_dir = "{}/1 Original Data/source.txt".format(speakerdir)
    try:
        with open(source_dir, "r") as f:
            l = f.readlines()
            if len(l) == 1:
                review_src = l[0]
    except FileNotFoundError:
        # print("source does not exists {}".format(source_dir))
        pass

    try:
        for i in range(1, 5):
            source_dir = "{}/1 Original Data/source{}.txt".format(speakerdir, i)
            with open(source_dir, "r") as f:
                l = f.readlines()
                if len(l) == 1:
                    reviews_src["rev{}".format(i)] = l[0]
    except FileNotFoundError:
        # print("source does not exists {}".format(source_dir))
        pass

    return review_src, reviews_src


def get_review_tar(speakerdir):
    review_tar = None
    tar_dir = "{}/2 WebPlotDigitizer Project".format(speakerdir)
    if os.path.isdir(tar_dir):
        tar = glob.glob("{}/*.tar".format(tar_dir))
        if len(tar) == 1:
            review_tar = tar[0]
    return review_tar


def get_review_txt(key, review_src, reviews_src):
    review_txt = ""
    if review_src is not None:
        review_txt = '"review": "{}",'.format(review_src)

    if reviews_src is not None and len(reviews_src.keys()) > 0:
        review_tab = ['"reviews": {']
        for k, v in reviews_src.items():
            if "audiosciencereview" in v:
                k = "asr"
            elif "thenextweb" in v:
                k = "tnw"
            review_tab.append('                        "{}": "{}",'.format(k, v))
        review_tab.append("                    },")
        review_txt = "\n".join(review_tab)

    return review_txt


def scan_speaker(reviewer, speakerdir):
    reviewer_name = None
    if reviewer[-1] == "/":
        reviewer_name = reviewer[0:-1].split("/")[-1].strip()
    else:
        reviewer_name = reviewer.split("/")[-1].strip()
    speaker_name = speakerdir.split("/")[-1].strip()
    # print("Start scanning {} {}".format(reviewer_name, speaker_name))

    matched, key = match_speaker(speaker_name, metadata.speakers_info.keys())
    review_tar = None
    speaker_brand = None
    speaker_model = None

    if not matched:
        # print("{} is new".format(speaker_name))
        review_key = get_review_key(reviewer_name)
        review_src, reviews_src = get_review_src(speakerdir)
        review_txt = get_review_txt(key, review_src, reviews_src)
        review_tar = get_review_tar(speakerdir)
        speaker_brand, speaker_model = guess_brand_model(speaker_name)
        if speaker_brand is None:
            return
        else:
            speaker_brand = brand_cleanup(speaker_brand)

        out = Template(
            '\
        "$sb $sm" : {\n\
            "brand": "$sb",\n\
            "model": "$sm",\n\
            "type": "passive",\n\
            "price": "",\n\
            "amount": "pair",\n\
            "shape": "bookshelves",\n\
            "default_measurement": "$rk",\n\
            "measurements" : {\n\
                "$rk": {\n\
                    "origin": "Misc",\n\
                    "format": "webplotdigitizer",\n\
                    "quality": "quasi-anechoic",\n\
                    $review\n\
                },\n\
            },\n\
        },\n'
        )

        print(
            out.substitute(
                sn=speaker_name,
                sb=speaker_brand,
                sm=speaker_model,
                rk=review_key,
                review=review_txt,
            )
        )
    else:
        review_tar = get_review_tar(speakerdir)
        speaker_brand = metadata.speakers_info[key]["brand"]
        speaker_model = metadata.speakers_info[key]["model"]

    target_dir = "./datas/Misc/{b}/{b} {m}".format(b=brand_cleanup(speaker_brand), m=speaker_model)
    if not os.path.isdir(target_dir):
        print("creating {}".format(target_dir))
        pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

    if review_tar is not None:
        target_file = "{d}/{b} {m}.tar".format(d=target_dir, b=brand_cleanup(speaker_brand), m=speaker_model)
        if not os.path.exists(target_file):
            print("copying {} to {}".format(review_tar, target_file))
            shutil.copy(review_tar, target_file)


if __name__ == "__main__":

    reviewdir = sys.argv[1]

    if not os.path.isdir(reviewdir):
        print("{} is not a directory!".format(reviewdir))

    sdirs = glob.glob(reviewdir + "/*")
    for d in sdirs:
        if os.path.isdir(d):
            scan_speaker(reviewdir, d)
        # else:
        #    print("skipping {}".format(d))
