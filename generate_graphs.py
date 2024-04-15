#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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
"""Usage:
generate_graphs.py [-h|--help] [-v] [--width=<width>] [--height=<height>]\
  [--force] [--smoke-test=<algo>] [--type=<ext>] [--log-level=<level>]\
  [--origin=<origin>]  [--speaker=<speaker>] [--mversion=<mversion>] [--brand=<brand>]\
  [--dash-ip=<ip>] [--dash-port=<port>] [--ray-local] [--update-cache]\
  [--data-dir=<data_dir>] [--ray-cluster=<ip_port>]

Options:
 -h|--help           display usage()
  --data-dir=<data_dir> directory where the datas are stores (. by default)
  --height=<height>   height size in pixel
  --force             force regeneration of all graphs, by default only generate new ones
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --origin=<origin>   filter by origin
  --brand=<brand>     filter by brand
  --dash-ip=<ip>      ip of dashboard to track execution, default to localhost/127.0.0.1
  --dash-port=<port>  port for the dashbboard, default to 8265
  --mversion=<mversion> filter by measurement
  --ray-local         if present, ray will run locally, it is usefull for debugging
  --ray-cluster=<ip_port> set to ip:port if you want to join an existing cluster
  --smoke-test=<algo> run a few speakers only (choice are random or default)
  --speaker=<speaker> filter by speaker
  --update-cache      force updating the cache
  --width=<width>     width size in pixel
"""
import glob
import os
import random
import sys


from docopt import docopt


try:
    import ray
except ModuleNotFoundError:
    try:
        import miniray as ray
    except ModuleNotFoundError:
        print("Did you run env.sh?")
        sys.exit(-1)

from generate_common import (
    args2level,
    cache_save,
    cache_update,
    custom_ray_init,
    get_custom_logger,
)
from datas import metadata
from spinorama.load_parse import parse_graphs_speaker, parse_eq_speaker
from spinorama.speaker_print import print_graphs
from spinorama.plot import plot_params_default


VERSION = "2.03"

ACTIVATE_TRACING: bool = False


def tracing(msg: str):
    """debugging ray is sometimes painfull"""
    if ACTIVATE_TRACING:
        print(f"---- TRACING ---- {msg} ----")


def get_speaker_list(speakerpath: str) -> set[str]:
    """return a list of speakers from data subdirectory"""
    speakers = []
    dirs = glob.glob(speakerpath + "/*")
    for current_dir in dirs:
        shortname = os.path.basename(current_dir)
        if os.path.isdir(current_dir) and shortname not in (
            "assets",
            "compare",
            "stats",
            "pictures",
            "tmp",
        ):
            speakers.append(shortname)
    return set(speakers)


def queue_measurement(
    brand: str,
    speaker: str,
    mformat: str,
    morigin: str,
    mversion: str,
    msymmetry: str | None,
    mparameters: dict | None,
    level: int,
) -> tuple[int, int, int, int]:
    """Add all measurements in the queue to be processed"""
    id_df = parse_graphs_speaker.remote(
        f"{data_dir}/datas/measurements",
        brand,
        speaker,
        mformat,
        morigin,
        mversion,
        msymmetry,
        mparameters,
        level,
    )
    id_eq = parse_eq_speaker.remote(f"{data_dir}/datas", speaker, id_df, mparameters, level)
    width = int(plot_params_default["width"])
    height = int(plot_params_default["height"])
    tracing("calling print_graph remote for {}".format(speaker))
    id_g1 = print_graphs.remote(
        id_df,
        speaker,
        mversion,
        morigin,
        metadata.origins_info,
        mversion,
        width,
        height,
        force,
        level,
    )
    tracing("calling print_graph remote eq for {}".format(speaker))
    id_g2 = print_graphs.remote(
        id_eq,
        speaker,
        mversion,
        morigin,
        metadata.origins_info,
        mversion + "_eq",
        width,
        height,
        force,
        level,
    )
    tracing("print_graph done")
    return (id_df, id_eq, id_g1, id_g2)


def queue_speakers(speakerlist: set[str], filters: dict[str, dict], level: int) -> dict:
    """Add all speakers in the queue to be processed"""
    ray_ids = {}
    count = 0
    for speaker in speakerlist:
        if "speaker" in filters and speaker != filters["speaker"]:
            logger.debug("skipping %s", speaker)
            continue
        ray_ids[speaker] = {}
        if speaker not in metadata.speakers_info:
            logger.error("Metadata error: %s", speaker)
            continue
        for mversion, measurement in metadata.speakers_info[speaker]["measurements"].items():
            # mversion looks like asr and asr_eq
            if "mversion" in filters and not (
                mversion == filters["mversion"] or mversion == "{}_eq".format(filters["mversion"])
            ):
                logger.debug("skipping %s/%s", speaker, mversion)
                continue
            # filter on format (klippel, princeton, ...)
            mformat = measurement["format"]
            if "format" in filters and mformat != filters["format"]:
                logger.debug("skipping %s/%s/%s", speaker, mformat, mversion)
                continue
            # filter on origin (ASR, princeton, ...)
            morigin = measurement["origin"]
            if "origin" in filters and morigin != filters["origin"]:
                logger.debug("skipping %s/%s/%s/%s", speaker, morigin, mformat, mversion)
                continue
            # TODO(add filter on brand)
            brand = metadata.speakers_info[speaker]["brand"]
            logger.debug("queing %s/%s/%s/%s", speaker, morigin, mformat, mversion)
            msymmetry = measurement.get("symmetry", None)
            mparameters = measurement.get("parameters", None)

            ray_ids[speaker][mversion] = queue_measurement(
                brand, speaker, mformat, morigin, mversion, msymmetry, mparameters, level
            )
            count += 1
    print("Queued {} speakers {} measurements".format(len(speakerlist), count))
    return ray_ids


def compute(speakerlist, filters, ray_ids: dict, level: int):
    """Compute a series of measurements"""
    data_frame = {}
    done_ids = {}
    while 1:
        df_ids = [
            ray_ids[s][v][0]
            for s in ray_ids
            for v in ray_ids[s]
            if ray_ids[s][v][0] not in done_ids
        ]
        eq_ids = [
            ray_ids[s][v][1]
            for s in ray_ids
            for v in ray_ids[s]
            if ray_ids[s][v][1] not in done_ids
        ]
        g1_ids = [
            ray_ids[s][v][2]
            for s in ray_ids
            for v in ray_ids[s]
            if ray_ids[s][v][2] not in done_ids
        ]
        g2_ids = [
            ray_ids[s][v][3]
            for s in ray_ids
            for v in ray_ids[s]
            if ray_ids[s][v][3] not in done_ids
        ]
        ids = df_ids + eq_ids + g1_ids + g2_ids
        if len(ids) == 0:
            break
        num_returns = min(len(ids), 16)
        ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)

        logger.info(
            "State: %d ready IDs %d remainings IDs %d Total IDs %d Done",
            len(ready_ids),
            len(remaining_ids),
            len(ids),
            len(done_ids),
        )

        for speaker in speakerlist:
            speaker_key = speaker  # .translate({ord(ch) : '_' for ch in '-.;/\' '})
            if speaker not in data_frame:
                data_frame[speaker_key] = {}
            if speaker not in metadata.speakers_info:
                logger.warning("Speaker %s in SpeakerList but not in Metadata", speaker)
                continue
            for m_version, measurement in metadata.speakers_info[speaker]["measurements"].items():
                m_version_key = m_version  # .translate({ord(ch) : '_' for ch in '-.;/\' '})
                # should not happen, usually it is an error in metadata that should be trapped by check_meta
                if "origin" not in measurement:
                    logger.error(
                        "measurement's data are incorrect: speaker=%s m_version=%s keys are (%s)",
                        speaker,
                        m_version,
                        ", ".join(measurement),
                    )
                m_origin = measurement["origin"]
                if m_origin not in data_frame[speaker_key]:
                    data_frame[speaker_key][m_origin] = {}

                if speaker not in ray_ids:
                    continue

                if m_version not in ray_ids[speaker]:
                    if "mversion" in filters and (
                        m_version == filters["mversion"]
                        or m_version == "{}_eq".format(filters["mversion"])
                    ):
                        logger.error("Speaker %s mversion %s not in keys", speaker, m_version)
                    continue

                current_id = ray_ids[speaker][m_version][0]
                if current_id in ready_ids:
                    data_frame[speaker_key][m_origin][m_version_key] = ray.get(current_id)
                    logger.debug("Getting df done for %s / %s / %s", speaker, m_origin, m_version)
                    done_ids[current_id] = True

                m_version_eq = f"{m_version_key}_eq"
                current_id = ray_ids[speaker][m_version][1]
                if current_id in eq_ids:
                    logger.debug(
                        "Getting eq done for %s / %s / %s", speaker, m_version_eq, m_version
                    )
                    _, computed_eq = ray.get(current_id)
                    if computed_eq is not None and len(computed_eq) > 0:
                        data_frame[speaker_key][m_origin][m_version_eq] = computed_eq
                        logger.debug(
                            "Getting preamp eq done for %s / %s / %s",
                            speaker,
                            m_version_eq,
                            m_version,
                        )
                        if "preamp_gain" in computed_eq:
                            data_frame[speaker_key][m_origin][m_version_eq]["preamp_gain"] = (
                                computed_eq["preamp_gain"]
                            )
                    done_ids[current_id] = True

                current_id = ray_ids[speaker][m_version][2]
                if current_id in g1_ids:
                    logger.debug(
                        "Getting graph done for %s / %s / %s", speaker, m_version, m_origin
                    )
                    ray.get(current_id)
                    done_ids[current_id] = True

                current_id = ray_ids[speaker][m_version][3]
                if current_id in g2_ids:
                    logger.debug(
                        "Getting graph done for %s / %s / %s", speaker, m_version_eq, m_origin
                    )
                    ray.get(current_id)
                    done_ids[current_id] = True

        if len(remaining_ids) == 0:
            break

    return data_frame


def main(level):
    """Send all speakers in the queue to be processed"""
    speakerlist = get_speaker_list(f"{data_dir}/datas/measurements")
    if args["--smoke-test"] is not None:
        if args["--smoke-test"] == "random":
            speakerlist = set(random.sample(list(speakerlist), 15))
        else:
            speakerlist = set(
                [
                    "Genelec 8030C",
                    "KEF LS50",
                    "KRK Systems Classic 5",
                    "Verdant Audio Bambusa MG 1",
                ]
            )
        print(speakerlist)

    if args["--width"] is not None:
        opt_width = int(args["--width"])
        plot_params_default["width"] = opt_width

    if args["--height"] is not None:
        opt_height = int(args["--height"])
        plot_params_default["height"] = opt_height

    update_cache = False
    if args["--update-cache"] is True:
        update_cache = True

    # start ray
    custom_ray_init(args)

    filters = {}
    for ifilter in ("speaker", "origin", "mversion"):
        flag = "--{}".format(ifilter)
        if args[flag] is not None:
            filters[ifilter] = args[flag]

    ray_ids = queue_speakers(speakerlist, filters, level)
    df_new = compute(speakerlist, filters, ray_ids, level)

    if len(filters.keys()) == 0:
        cache_save(df_new)
    elif update_cache:
        cache_update(df_new, filters, LEVEL)

    ray.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    args = docopt(__doc__, version="generate_graphs.py v{}".format(VERSION), options_first=True)
    force = args["--force"]
    LEVEL = args2level(args)
    logger = get_custom_logger(level=LEVEL, duplicate=True)
    data_dir = "."
    if args["--data-dir"] is not None:
        data_dir = args["--data-dir"]
    main(level=LEVEL)
