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
    [--dash-ip=<ip>] [--dash-port=<port>] [--ray-local]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --metadata=<metadata> metadata file to use (default is ./datas/metadata.py)
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

from docopt import docopt

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray

from generate_common import get_custom_logger, args2level, custom_ray_init, cache_load
import datas.metadata as metadata
from spinorama.compute_estimates import estimates
from spinorama.compute_scores import speaker_pref_rating
from spinorama.filter_peq import peq_preamp_gain
from spinorama.load_parse import parse_graphs_speaker
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
        logger.info("Processing {0}".format(speaker_name))
        for _, measurements in speaker_data.items():
            default_key = metadata.speakers_info[speaker_name]['default_measurement']
            for key, dfs in measurements.items():
                try:
                    if dfs is None or "CEA2034" not in dfs.keys():
                        logger.debug(
                            "skipping add_score no spinorama for {0}".format(
                                speaker_name
                            )
                        )
                        continue

                    spin = dfs["CEA2034"]
                    if spin is None or "Estimated In-Room Response" not in dfs.keys():
                        continue

                    logger.debug(
                        "Compute score for speaker {0} key {1}".format(
                            speaker_name, key
                        )
                    )
                    # sensitivity
                    sensitivity = dfs.get("sensitivity")
                    if (
                        sensitivity is not None
                        and metadata.speakers_info[speaker_name].get("type")
                        == "passive"
                        and key == default_key
                    ):
                        logger.debug("{} sensitivity is {}".format(speaker_name, sensitivity))
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
                        "Adding -3dB {0}Hz -6dB {1}Hz +/-{2}dB".format(
                            est.get("ref_3dB", "--"),
                            est.get("ref_6dB", "--"),
                            est.get("ref_band", "--"),
                        )
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
                        if metadata.speakers_info[speaker_name]["measurements"][
                            origin
                        ] in ("ASR", "ErinsAudioCorner"):
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
                except KeyError as ke:
                    print("{} get {}".format(speaker_name, ke))
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
        logger.info("Normalize data for {0}".format(speaker_name))
        for _, measurements in speaker_data.items():
            for version, measurement in measurements.items():
                if (
                    version
                    not in metadata.speakers_info[speaker_name]["measurements"].keys()
                ):
                    if len(version) > 4 and version[-3:] != "_eq":
                        logger.error(
                            "Confusion in metadata, did you edit a speaker recently? {} should be in metadata for {}".format(
                                version, speaker_name
                            )
                        )
                    continue

                if measurement is None or "CEA2034" not in measurement.keys():
                    logger.debug(
                        "skipping normalization no spinorama for {0}".format(
                            speaker_name
                        )
                    )
                    continue

                spin = measurement["CEA2034"]
                if spin is None:
                    logger.debug(
                        "skipping normalization no spinorama for {0}".format(
                            speaker_name
                        )
                    )
                    continue
                if version[-3:] == "_eq":
                    logger.debug(
                        "skipping normalization for eq for {0}".format(speaker_name)
                    )
                    continue
                if (
                    "estimates"
                    not in metadata.speakers_info[speaker_name]["measurements"][
                        version
                    ].keys()
                ):
                    logger.debug(
                        "skipping normalization no estimates in {0} for {1}".format(
                            version, speaker_name
                        )
                    )
                    continue
                if (
                    "pref_rating"
                    not in metadata.speakers_info[speaker_name]["measurements"][
                        version
                    ].keys()
                ):
                    logger.debug(
                        "skipping normalization no pref_rating in {0} for {1}".format(
                            version, speaker_name
                        )
                    )
                    continue

                logger.debug(
                    "Compute relative score for speaker {0}".format(speaker_name)
                )
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

                scaled_pref_score_wsub = percent(
                    pref_score_wsub, min_pref_score_wsub, max_pref_score_wsub
                )
                if "pref_score" in pref_rating:
                    scaled_pref_score = percent(
                        pref_score, min_pref_score, max_pref_score
                    )
                    scaled_lfx_hz = 100 - percent(lfx_hz, min_lfx_hz, max_lfx_hz)
                scaled_nbd_on = 100 - percent(nbd_on, min_nbd_on, max_nbd_on)
                scaled_flatness = 100 - percent(flatness, min_flatness, max_flatness)
                scaled_sm_sp = percent(sm_sp, min_sm_sp, max_sm_sp)
                scaled_sm_pir = percent(sm_pir, min_sm_pir, max_sm_pir)
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


def dump_metadata(meta):
    metadir = "./docs/assets/"
    metafile = "{}/metadata.json".format(metadir)
    if not os.path.isdir(metadir):
        os.makedirs(metadir)
    meta2 = {k: v for k, v in meta.items() if not v.get("skip", False)}

    with open(metafile, "w") as f:
        js = json.dumps(meta2)
        f.write(js)
        f.close()


if __name__ == "__main__":
    args = docopt(__doc__, version="generate_meta.py version 1.4", options_first=True)

    # check args section
    level = args2level(args)
    logger = get_custom_logger(True)
    logger.setLevel(level)

    # start ray
    custom_ray_init(args)

    df = None
    speaker = args["--speaker"]
    origin = args["--origin"]
    mversion = args["--mversion"]
    parse_max = args["--parse-max"]
    if parse_max is not None:
        parse_max = int(parse_max)

    if speaker is not None:
        df = cache_load(simple_filter=speaker)
    else:
        df = cache_load()

    if df is None:
        logger.error("Load failed! Please run ./generate_graphs.py")
        sys.exit(1)

    # add computed data to metadata
    logger.info("Compute scores per speaker")
    add_quality(parse_max)
    add_scores(df, parse_max)
    add_eq("./datas", df, parse_max)

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
