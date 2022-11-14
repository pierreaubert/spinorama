#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-21 Pierre Aubert pierreaubert(at)yahoo(dot)fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
usage: generate_meta.py [--help] [--version] [--log-level=<level>]\
    [--metadata=<metadata>] [--parse-max=<max>] [--use-cache=<cache>]\
    [--origin=<origin>] [--speaker=<speaker>] [--mversion=<mversion>]\
    [--dash-ip=<ip>] [--dash-port=<port>] [--ray-local] \
    [--smoke-test=<algo>]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --metadata=<metadata> metadata file to use (default is ./datas/metadata.py)
  --smoke-test=<algo> run a few speakers only (choice are random or default)
  --parse-max=<max> for debugging, set a max number of speakers to look at
  --origin=<origin> restrict to a specific origin, usefull for debugging
  --speaker=<speaker> restrict to a specific speaker, usefull for debugging
  --mversion=<mversion> restrict to a specific mversion (for a given origin you can have multiple measurements)
  --dash-ip=<dash-ip>      IP for the ray dashboard to track execution
  --dash-port=<dash-port>  Port for the ray dashbboard
"""
import os
import json
import math
import sys

import numpy as np

from docopt import docopt

# try:
#    import ray
# except ModuleNotFoundError:
#    import src.miniray as ray

from generate_common import get_custom_logger, args2level, cache_load
import datas.metadata as metadata
import spinorama.constant_paths as cpaths
from spinorama.compute_estimates import estimates
from spinorama.compute_scores import speaker_pref_rating
from spinorama.filter_peq import peq_preamp_gain
from spinorama.load_rewseq import parse_eq_iir_rews


def add_scores(dataframe, parse_max):
    """Compute some values per speaker and add them to metadata"""
    min_pref_score = +100
    max_pref_score = -100
    min_pref_score_wsub = +100
    max_pref_score_wsub = -100
    min_lfx_hz = 1000
    max_lfx_hz = 0
    min_nbd_on = 1
    max_nbd_on = 0
    min_flatness = 100
    max_flatness = 1
    min_sm_sp = 1
    max_sm_sp = 0
    min_sm_pir = 1
    max_sm_pir = 0
    parsed = 0
    for speaker_name, speaker_data in dataframe.items():
        if parse_max is not None and parsed > parse_max:
            break
        parsed = parsed + 1
        logger.info("Processing {speaker_name}", speaker_name)
        for _, measurements in speaker_data.items():
            default_key = None
            try:
                default_key = metadata.speakers_info[speaker_name][
                    "default_measurement"
                ]
            except KeyError:
                logger.error(
                    "Got an key error exception for speaker_name {} default measurement",
                    speaker_name,
                )
                continue
            for key, dfs in measurements.items():
                try:
                    if dfs is None or "CEA2034" not in dfs.keys():
                        logger.debug(
                            "skipping add_score no spinorama for {}", speaker_name
                        )
                        continue

                    spin = dfs["CEA2034"]
                    if spin is None or "Estimated In-Room Response" not in dfs.keys():
                        continue

                    logger.debug(
                        "Compute score for speaker {0} key {1}", speaker_name, key
                    )
                    # sensitivity
                    sensitivity = dfs.get("sensitivity")
                    if (
                        sensitivity is not None
                        and metadata.speakers_info[speaker_name].get("type")
                        == "passive"
                        and key == default_key
                    ):
                        logger.debug(
                            "{} sensitivity is {}".format(speaker_name, sensitivity)
                        )
                        metadata.speakers_info[speaker_name][
                            "sensitivity"
                        ] = sensitivity
                    # basic math
                    splH = dfs.get("SPL Horizontal_unmelted", None)
                    splV = dfs.get("SPL Vertical_unmelted", None)
                    est = estimates(spin, splH, splV)
                    logger.info("Computing estimated for {0}".format(speaker_name))
                    if est is None:
                        logger.debug(
                            "estimated return None for {0}".format(speaker_name)
                        )
                        continue
                    logger.info(
                        "Adding -3dB {0}Hz -6dB {1}Hz +/-{2}dB",
                        est.get("ref_3dB", "--"),
                        est.get("ref_6dB", "--"),
                        est.get("ref_band", "--"),
                    )
                    if key[-3:] == "_eq":
                        metadata.speakers_info[speaker_name]["measurements"][key[:-3]][
                            "estimates_eq"
                        ] = est
                    else:
                        metadata.speakers_info[speaker_name]["measurements"][key][
                            "estimates"
                        ] = est

                    inroom = dfs["Estimated In-Room Response"]
                    if inroom is None:
                        continue

                    logger.debug(
                        "Compute score for speaker {0} key {1}".format(
                            speaker_name, key
                        )
                    )

                    pref_rating = speaker_pref_rating(spin, inroom)
                    if pref_rating is None:
                        origin = "test"
                        if origin in ("ASR", "ErinsAudioCorner"):
                            logger.error(
                                "pref_rating failed for {0} {1}".format(
                                    speaker_name, key
                                )
                            )
                        else:
                            logger.debug(
                                "pref_rating failed for {0} {1}".format(
                                    speaker_name, key
                                )
                            )
                        continue
                    # print(
                    #    "sm pir {} for {}".format(
                    #        pref_rating["sm_sound_power"], speaker_name
                    #    )
                    # )
                    logger.info("Adding {0}".format(pref_rating))
                    # compute min and max for each value
                    min_flatness = min(est["ref_band"], min_flatness)
                    max_flatness = max(est["ref_band"], max_flatness)
                    min_pref_score_wsub = min(
                        min_pref_score_wsub, pref_rating["pref_score_wsub"]
                    )
                    max_pref_score_wsub = max(
                        max_pref_score_wsub, pref_rating["pref_score_wsub"]
                    )
                    min_nbd_on = min(min_nbd_on, pref_rating["nbd_on_axis"])
                    max_nbd_on = max(max_nbd_on, pref_rating["nbd_on_axis"])
                    min_sm_sp = min(min_nbd_on, pref_rating["sm_sound_power"])
                    max_sm_sp = max(max_nbd_on, pref_rating["sm_sound_power"])
                    min_sm_pir = min(min_nbd_on, pref_rating["sm_pred_in_room"])
                    max_sm_pir = max(max_nbd_on, pref_rating["sm_pred_in_room"])
                    # if datas have low freq:
                    if "pref_score" in pref_rating:
                        min_pref_score = min(min_pref_score, pref_rating["pref_score"])
                        max_pref_score = max(max_pref_score, pref_rating["pref_score"])
                        if "lfx_hz" in pref_rating:
                            min_lfx_hz = min(min_lfx_hz, pref_rating["lfx_hz"])
                            max_lfx_hz = max(max_lfx_hz, pref_rating["lfx_hz"])

                    if key[-3:] == "_eq":
                        metadata.speakers_info[speaker_name]["measurements"][key[:-3]][
                            "pref_rating_eq"
                        ] = pref_rating
                    else:
                        metadata.speakers_info[speaker_name]["measurements"][key][
                            "pref_rating"
                        ] = pref_rating
                except KeyError as current_error:
                    print("{} get {}".format(speaker_name, current_error))
                    continue

    # if we are looking only after 1 speaker, return
    if len(dataframe.items()) == 1:
        logger.info("skipping normalization with only one speaker")
        return

    # add normalized value to metadata
    parsed = 0
    for speaker_name, speaker_data in dataframe.items():
        if parse_max is not None and parsed > parse_max:
            break
        parsed = parsed + 1
        logger.info("Normalize data for {0}", speaker_name)
        for _, measurements in speaker_data.items():
            for version, measurement in measurements.items():
                if (
                    version
                    not in metadata.speakers_info[speaker_name]["measurements"].keys()
                ):
                    if len(version) > 4 and version[-3:] != "_eq":
                        logger.error(
                            "Confusion in metadata, did you edit a speaker recently? {} should be in metadata for {}",
                            version,
                            speaker_name,
                        )
                    continue

                if measurement is None or "CEA2034" not in measurement.keys():
                    logger.debug(
                        "skipping normalization no spinorama for {0}", speaker_name
                    )
                    continue

                spin = measurement["CEA2034"]
                if spin is None:
                    logger.debug(
                        "skipping normalization no spinorama for {0}", speaker_name
                    )
                    continue
                if version[-3:] == "_eq":
                    logger.debug("skipping normalization for eq for {0}", speaker_name)
                    continue
                if (
                    "estimates"
                    not in metadata.speakers_info[speaker_name]["measurements"][
                        version
                    ].keys()
                ):
                    logger.debug(
                        "skipping normalization no estimates in {0} for {1}",
                        version,
                        speaker_name,
                    )
                    continue
                if (
                    "pref_rating"
                    not in metadata.speakers_info[speaker_name]["measurements"][
                        version
                    ].keys()
                ):
                    logger.debug(
                        "skipping normalization no pref_rating in {0} for {1}",
                        version,
                        speaker_name,
                    )
                    continue

                logger.debug("Compute relative score for speaker {0}", speaker_name)
                # get values
                pref_rating = metadata.speakers_info[speaker_name]["measurements"][
                    version
                ]["pref_rating"]
                pref_score_wsub = pref_rating["pref_score_wsub"]
                nbd_on = pref_rating["nbd_on_axis"]
                sm_sp = pref_rating["sm_sound_power"]
                sm_pir = pref_rating["sm_pred_in_room"]
                flatness = metadata.speakers_info[speaker_name]["measurements"][
                    version
                ]["estimates"]["ref_band"]
                pref_score = -1
                lfx_hz = -1
                if "pref_score" in pref_rating:
                    pref_score = pref_rating["pref_score"]
                if "lfx_hz" in pref_rating:
                    lfx_hz = pref_rating["lfx_hz"]

                # normalize min and max
                def percent(val, vmin, vmax):
                    if math.isnan(val) or math.isnan(vmin) or math.isnan(vmax):
                        logger.debug("data is NaN")
                        return 0
                    if vmax == vmin:
                        logger.debug("max == min")
                        return 0
                    p = math.floor(100 * (val - vmin) / (vmax - vmin))
                    return min(max(0, p), 100)

                scaled_pref_score = None
                scaled_pref_score_wsub = percent(
                    pref_score_wsub, min_pref_score_wsub, max_pref_score_wsub
                )
                scaled_pref_score = None
                if "pref_score" in pref_rating:
                    scaled_pref_score = percent(
                        pref_score, min_pref_score, max_pref_score
                    )
                    scaled_lfx_hz = 100 - percent(lfx_hz, min_lfx_hz, max_lfx_hz)
                scaled_nbd_on = 100 - percent(nbd_on, min_nbd_on, max_nbd_on)
                scaled_sm_sp = percent(sm_sp, min_sm_sp, max_sm_sp)
                scaled_sm_pir = percent(sm_pir, min_sm_pir, max_sm_pir)
                scaled_flatness = 100 - percent(flatness, min_flatness, max_flatness)
                # bucket score instead of a linear scale
                if scaled_pref_score is not None:
                    if pref_score > 7:
                        scaled_pref_score = 100
                    elif pref_score > 6.5:
                        scaled_pref_score = 90
                    elif pref_score > 6:
                        scaled_pref_score = 80
                    elif pref_score > 5.5:
                        scaled_pref_score = 70
                    elif pref_score > 5:
                        scaled_pref_score = 60
                    elif pref_score > 4.5:
                        scaled_pref_score = 50
                    elif pref_score > 4.0:
                        scaled_pref_score = 40
                    elif pref_score > 3.0:
                        scaled_pref_score = 30
                    elif pref_score > 3.0:
                        scaled_pref_score = 30
                    elif pref_score > 1.0:
                        scaled_pref_score = 10
                    else:
                        scaled_pref_score = 0
                # bucket flatness instead of a linear scale
                if flatness < 2.0:
                    scaled_flatness = 100
                elif flatness < 2.25:
                    scaled_flatness = 90
                elif flatness < 2.5:
                    scaled_flatness = 80
                elif flatness < 3:
                    scaled_flatness = 70
                elif flatness < 4:
                    scaled_flatness = 50
                elif flatness < 5:
                    scaled_flatness = 30
                elif flatness < 6:
                    scaled_flatness = 10
                else:
                    scaled_flatness = 0
                # bucked lfx too
                if scaled_lfx_hz is not None:
                    if lfx_hz < 25:
                        scaled_lfx_hz = 100
                    elif lfx_hz < 30:
                        scaled_lfx_hz = 90
                    elif lfx_hz < 35:
                        scaled_lfx_hz = 80
                    elif lfx_hz < 40:
                        scaled_lfx_hz = 70
                    elif lfx_hz < 50:
                        scaled_lfx_hz = 60
                    elif lfx_hz < 60:
                        scaled_lfx_hz = 50
                    elif lfx_hz < 70:
                        scaled_lfx_hz = 40
                    elif lfx_hz < 80:
                        scaled_lfx_hz = 30
                    elif lfx_hz < 100:
                        scaled_lfx_hz = 10
                    else:
                        scaled_lfx_hz = 0
                # bucket sm_pir too
                if sm_pir > 0.95:
                    scaled_sm_pir = 100
                elif sm_pir > 0.9:
                    scaled_sm_pir = 90
                elif sm_pir > 0.85:
                    scaled_sm_pir = 80
                elif sm_pir > 0.8:
                    scaled_sm_pir = 70
                elif sm_pir > 0.7:
                    scaled_sm_pir = 60
                elif sm_pir > 0.6:
                    scaled_sm_pir = 50
                elif sm_pir > 0.5:
                    scaled_sm_pir = 25
                else:
                    scaled_sm_pir = 0

                # add normalized values
                scaled_pref_rating = {
                    "scaled_pref_score_wsub": scaled_pref_score_wsub,
                    "scaled_nbd_on_axis": scaled_nbd_on,
                    "scaled_flatness": scaled_flatness,
                    "scaled_sm_sound_power": scaled_sm_sp,
                    "scaled_sm_pred_in_room": scaled_sm_pir,
                }
                if "pref_score" in pref_rating:
                    scaled_pref_rating["scaled_pref_score"] = scaled_pref_score
                if "lfx_hz" in pref_rating:
                    scaled_pref_rating["scaled_lfx_hz"] = scaled_lfx_hz
                logger.info("Adding {0}".format(scaled_pref_rating))
                metadata.speakers_info[speaker_name]["measurements"][version][
                    "scaled_pref_rating"
                ] = scaled_pref_rating


def add_quality(parse_max: int):
    """Compute quality of data and add it to metadata
    Rules:
    - Independant measurements from ASR or EAC : high quality
    - Most measurements from Harmann group: medium quality
    - Most measurements quasi anechoic: low quality
    This can be overriden by setting the correct value in the metadata file
    """
    parsed = 0
    for speaker_name, speaker_data in metadata.speakers_info.items():
        if parse_max is not None and parsed > parse_max:
            break
        parsed = parsed + 1
        logger.info("Processing {0}".format(speaker_name))
        for version, m_data in speaker_data["measurements"].items():
            if "quality" not in m_data.keys():
                quality = "unknown"
                origin = m_data.get("origin")
                measurement_format = m_data.get("format")
                if measurement_format == "klippel":
                    quality = "high"
                elif origin == "Princeton":
                    quality = "low"
                elif origin == "Misc":
                    if "napilopez" in version or "audioholics" in version:
                        quality = "low"
                elif "Vendor" in origin:
                    brand = speaker_data["brand"]
                    # Harman group provides spin from an anechoic room
                    if brand in ("JBL", "Revel", "Infinity"):
                        quality = "medium"

                logger.debug(
                    "Setting quality {} {} to {}".format(speaker_name, version, quality)
                )
                if (
                    version
                    in metadata.speakers_info[speaker_name]["measurements"].keys()
                ):
                    metadata.speakers_info[speaker_name]["measurements"][version][
                        "quality"
                    ] = quality
                else:
                    logger.info("Version {} is not in {}".format(version, speaker_name))


def add_eq(speaker_path, dataframe, parse_max):
    """Compute some values per speaker and add them to metadata"""
    parsed = 0
    for speaker_name in dataframe.keys():
        if parse_max is not None and parsed > parse_max:
            break
        parsed = parsed + 1
        logger.info("Processing {0}".format(speaker_name))

        for suffix in ("", "-autoeq", "-amirm", "-maiky76", "-flipflop"):
            iir = parse_eq_iir_rews(
                "{}/eq/{}/iir{}.txt".format(speaker_path, speaker_name, suffix), 48000
            )
            if iir is not None and len(iir) > 0:
                eq_key = "eq{}".format(suffix.replace("-", "_"))
                metadata.speakers_info[speaker_name][eq_key] = {}
                metadata.speakers_info[speaker_name][eq_key]["preamp_gain"] = round(
                    peq_preamp_gain(iir), 1
                )
                metadata.speakers_info[speaker_name][eq_key]["type"] = "peq"
                metadata.speakers_info[speaker_name][eq_key]["peq"] = []
                for i, (iir_weigth, iir_filter) in enumerate(iir):
                    if iir_weigth != 0.0:
                        metadata.speakers_info[speaker_name][eq_key]["peq"].append(
                            {
                                "type": iir_filter.typ,
                                "freq": iir_filter.freq,
                                "srate": iir_filter.srate,
                                "Q": iir_filter.Q,
                                "dbGain": iir_filter.dbGain,
                            }
                        )
                        logger.debug(
                            "adding eq: {}".format(
                                metadata.speakers_info[speaker_name][eq_key]
                            )
                        )


def interpolate(speaker_name, freq, freq1, data1):
    data = []
    len1 = len(freq1)
    i = 0
    for f in freq:
        try:
            # print('debug: i={} f={}'.format(i, f))
            while freq1[i] < f and i < len1:
                i += 1
            # print('debug: i={} f={} f1={}'.format(i, f, freq1[i]))

            if i >= len1:
                data.append(0.0)
                # print('append 0')
                continue

            if freq1[i] >= f:
                if i == 0:
                    data.append(0.0)
                    # print('append 0')
                    continue
                else:
                    i = i - 1
                    # print('decrease i')

            # print('debug: i={} f={} f1={}'.format(i, f, freq1[i]))
            j = i
            while freq1[j] < f and j < len1:
                j += 1
            if j >= len1:
                data.append(data1[i])
                continue

            # print('debug: i={} j={} f={} f1[i]={} f1[j]={}'.format(i, j, f, freq1[i], freq1[j]))
            interp = data1[i] + (data1[j] - data1[i]) * (f - freq1[i]) / (
                freq1[j] - freq1[i]
            )
            # print('interp={}'.format(interp))
            data.append(interp)
        except IndexError as ie:
            print("{}: {} for f={}".format(speaker_name, ie, f))
            data.append(0.0)

    # print(data)
    return np.array(data)


def compute_near(fspin1, fspin2):
    lw1, er1, sp1 = fspin1
    lw2, er2, sp2 = fspin2

    lw = lw1 - lw2
    er = er1 - er2
    sp = sp1 - sp2

    near = np.mean([np.linalg.norm(lw), np.linalg.norm(sp), np.linalg.norm(er, 2)])
    if math.isnan(near):
        # print("get a NaN")
        # print(lw.head(), sp.head())
        return 1000000.0
    print("near lengths {} {} {} near {}".format(len(lw), len(er), len(sp), near))
    return near


def get_spin_data(freq, speaker_name, speaker_data):
    default_key = None
    try:
        default_key = metadata.speakers_info[speaker_name]["default_measurement"]
        default_origin = metadata.speakers_info[speaker_name]["measurements"][
            default_key
        ]["origin"]
    except KeyError:
        return None

    default_format = metadata.speakers_info[speaker_name]["measurements"][default_key][
        "format"
    ]
    if default_format != "klippel":
        return None

    for reviewer, measurements in speaker_data.items():
        if "asr" in default_key and reviewer != "ASR":
            # print(
            #     "skipping {} with {} and {}".format(speaker_name, reviewer, default_key)
            # )
            continue
        if "eac" in default_key and reviewer != "ErinsAudioCorner":
            # print(
            #    "skipping {} with {} and {}".format(speaker_name, reviewer, default_key)
            # )
            continue
        for key, dfs in measurements.items():
            if "_eq" in key:
                #     print(
                #    "skipping {} with {} and {} : key {} match _eq".format(
                #        speaker_name, reviewer, default_key, key
                #    )
                # )
                continue
            if dfs is None or "CEA2034" not in dfs.keys():
                # print(
                #    "skipping {} with {} and {} : key {} no SPIN".format(
                #        speaker_name, reviewer, default_key, key
                #    )
                # )
                return None

            spin = dfs["CEA2034_unmelted"]
            if (
                spin is None
                or "Listening Window" not in spin.keys()
                or "Sound Power" not in spin.keys()
            ):
                # print(
                #    "skipping {} with {} and {} : key {} no LW or no SP".format(
                #        speaker_name, reviewer, default_key, key
                #    )
                #
                # )
                return None

            lw = interpolate(speaker_name, freq, spin["Freq"], spin["Listening Window"])
            er = interpolate(
                speaker_name, freq, spin["Freq"], spin["Early Reflections"]
            )
            sp = interpolate(speaker_name, freq, spin["Freq"], spin["Sound Power"])

            return lw, er, sp

        print("skipping {} no match".format(speaker_name))
    return None


def add_near(dataframe, parse_max):
    """Compute nearest speaker"""
    parsed = 0
    distribution = []
    normalized = {}
    distances = {}
    freq = np.logspace(np.log10(25), np.log10(16000), 100)
    for speaker_name, speaker_data in dataframe.items():
        curves = get_spin_data(freq, speaker_name, speaker_data)
        if curves is not None:
            normalized[speaker_name] = curves
            distances[speaker_name] = {}

    for speaker_name1, speaker_data1 in normalized.items():
        if parse_max is not None and parsed > parse_max:
            break
        parsed = parsed + 1
        deltas = []

        for speaker_name2, speaker_data2 in normalized.items():
            if speaker_name1 == speaker_name2:
                continue
            prev_delta = distances[speaker_name2].get(speaker_name1)
            delta = prev_delta
            if prev_delta is None:
                delta = compute_near(speaker_data1, speaker_data2)
                distances[speaker_name2][speaker_name1] = delta
                distances[speaker_name1][speaker_name2] = delta
            deltas.append((delta, speaker_name2))
            distribution.append(delta)

        if speaker_name1 == "Dutch Dutch 8C":
            print(sorted(deltas, key=lambda x: x[0]))

        closest = sorted(deltas, key=lambda x: x[0])[:3]
        metadata.speakers_info[speaker_name1]["nearest"] = closest

    # print some stats
    height = 20
    bins = 80
    h = np.histogram(distribution, bins=bins)
    hmin = np.min(h[0])
    hmax = np.max(h[0])
    print("distances [{}, {}]".format(hmin, hmax))
    val = [int(i * height / hmax) for i in h[0] if hmax != 0]

    def lign(v):
        return ["." if i < v else " " for i in range(height)]

    table = [lign(v) for v in val]
    ttable = ["".join(row) for row in np.array(table).T]
    print("\n".join(ttable))


def dump_metadata(meta):
    metadir = cpaths.CPATH_DOCS_ASSETS
    metafile = cpaths.CPATH_METADATA_JSON
    if not os.path.isdir(metadir):
        os.makedirs(metadir)
    meta2 = {k: v for k, v in meta.items() if not v.get("skip", False)}

    with open(metafile, "w") as f:
        js = json.dumps(meta2)
        f.write(js)
        f.close()


def main():
    # start ray
    # custom_ray_init(args)

    df = None
    speaker = args["--speaker"]
    origin = args["--origin"]
    mversion = args["--mversion"]
    parse_max = args["--parse-max"]
    if parse_max is not None:
        parse_max = int(parse_max)
    smoke_test = False
    if args["--smoke-test"] is not None:
        smoke_test = True

    if speaker is not None:
        df = cache_load(simple_filter=speaker, smoke_test=smoke_test)
    else:
        df = cache_load(smoke_test=smoke_test)

    if df is None:
        logger.error("Load failed! Please run ./generate_graphs.py")
        sys.exit(1)

    # add computed data to metadata
    logger.info("Compute scores per speaker")
    add_quality(parse_max)
    add_scores(df, parse_max)
    add_eq("./datas", df, parse_max)
    add_near(df, parse_max)

    # check that json is valid
    # try:
    #    json.loads(metadata.speakers_info)
    # except ValueError as ve:
    #    logger.fatal('Metadata Json is not valid {0}'.format(ve))
    #    sys.exit(1)

    # write metadata in a json file for easy search
    logger.info("Write metadata")
    dump_metadata(metadata.speakers_info)

    logger.info("Bye")
    sys.exit(0)


if __name__ == "__main__":
    args = docopt(__doc__, version="generate_meta.py version 1.4", options_first=True)

    # check args section
    level = args2level(args)
    logger = get_custom_logger(True)
    logger.setLevel(level)

    main()
