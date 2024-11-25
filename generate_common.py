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

from collections import defaultdict
import difflib
from glob import glob
from hashlib import md5
import ipaddress
import logging
import os
import pathlib
import re
import sys
import warnings

import flammkuchen as fl
from pandas.core.arrays.masked import to_numpy_dtype_inference
import tables

import datas.metadata as metadata

from spinorama import ray_setup_logger
import spinorama.constant_paths as cpaths
from spinorama.constant_paths import flags_ADD_HASH

MINIRAY = None
try:
    import ray

    MINIRAY = False
except ModuleNotFoundError:
    import src.miniray as ray

    MINIRAY = True

CACHE_DIR = ".cache"


def get_similar_names(speakername):
    return difflib.get_close_matches(speakername, metadata.speakers_info.keys())


def get_custom_logger(level, duplicate):
    """Define properties of our logger"""
    custom = logging.getLogger("spinorama")
    custom_file_handler = logging.FileHandler("debug_optim.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    custom_file_handler.setFormatter(formatter)
    custom.addHandler(custom_file_handler)
    if duplicate is True:
        custom_stream_handler = logging.StreamHandler(sys.stdout)
        custom_stream_handler.setFormatter(formatter)
        custom.addHandler(custom_stream_handler)
    custom.setLevel(level)
    return custom


def args2level(args):
    """Transform an argument into a logger level"""
    level = logging.WARNING
    if args["--log-level"] is not None:
        check_level = args["--log-level"].upper()
        if check_level in ("INFO", "DEBUG", "WARNING", "ERROR"):
            if check_level == "INFO":
                level = logging.INFO
            elif check_level == "DEBUG":
                level = logging.DEBUG
            elif check_level == "WARNING":
                level = logging.WARNING
            elif check_level == "ERROR":
                level = logging.ERROR
    return level


def create_default_directories():
    for d in (
        CACHE_DIR,
        "docs",
        "docs/pictures",
        "docs/speakers",
        "build/eqs",
        "build/ray",
        "build/website",
        "build/mako_modules",
    ):
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)


def custom_ray_init(args):
    """Customize ray initialisation with a few parameters"""
    create_default_directories()
    if MINIRAY:
        return
    # expose the dashboard on another ip if required
    dashboard_ip = "127.0.0.1"
    dashboard_port = 8265
    if "--dash-ip" in args and args["--dash-ip"] is not None:
        check_ip = args["--dash-ip"]
        try:
            _ = ipaddress.ip_address(check_ip)
            dashboard_ip = check_ip
        except ipaddress.AddressValueError as ave:
            print("ip {} is not valid {}!".format(check_ip, ave))
            sys.exit(1)

    if "--dash-port" in args and args["--dash-port"] is not None:
        check_port = args["--dash-port"]
        try:
            dashboard_port = int(check_port)
            if dashboard_port < 0 or dashboard_port > 2**16 - 1:
                print("--dash-port={} is out of bounds".format(check_port))
                sys.exit(1)
        except ValueError:
            print("--dash-port={} is not an integer".format(check_port))
            sys.exit(1)

    # this start ray in single process mode
    ray_local_mode = False
    if "--ray-local" in args and args["--ray-local"] is True:
        ray_local_mode = True

    level = args2level(args)

    ray_address = None
    if "--ray-cluster" in args and args["--ray-cluster"] is not None:
        check_address = args["--ray-cluster"]
        check_ip, check_port = check_address.split(":")
        try:
            _ = ipaddress.ip_address(check_ip)
        except ipaddress.AddressValueError as ave:
            print("ray ip {} is not valid {}!".format(check_ip, ave))
            sys.exit(1)
        try:
            ray_port = int(check_port)
            if ray_port < 0 or ray_port > 2**16 - 1:
                print("ray port {} is out of bounds".format(check_port))
                sys.exit(1)
        except ValueError:
            print("ray port {} is not an integer".format(check_port))
            sys.exit(1)
        ray_address = check_address

    # tmp_dir = (pathlib.Path.cwd().absolute() / 'build/ray').as_posix()
    if ray_address is not None:
        print(
            "Calling init with cluster at {} dashboard at {}:{}".format(
                ray_address, dashboard_ip, dashboard_port
            )
        )
        ray.init(
            address=ray_address,
            include_dashboard=True,
            dashboard_host=dashboard_ip,
            dashboard_port=dashboard_port,
            local_mode=ray_local_mode,
            configure_logging=True,
            logging_level=level,
            log_to_driver=True,
            # _temp_dir=tmp_dir,
        )
    else:
        print("Calling init with dashboard at {}:{}".format(dashboard_ip, dashboard_port))
        if ray.is_initialized:
            ray.shutdown()
        ray.init(
            include_dashboard=True,
            dashboard_host=dashboard_ip,
            dashboard_port=dashboard_port,
            local_mode=ray_local_mode,
            configure_logging=True,
            logging_level=level,
            log_to_driver=True,
            # _temp_dir=tmp_dir,
        )


def cache_key(name: str) -> str:
    # 256 partitions, use hashlib for stable hash
    key = md5(name.encode("utf-8"), usedforsecurity=False).hexdigest()
    short_key = key[0:2]
    return f"{short_key:2s}"


def cache_match(key: str, name: str) -> bool:
    return key == cache_key(name)


def cache_hash(df_all: dict) -> dict:
    df_hashed = {}
    for k, v in df_all.items():
        if k is None or len(k) == 0:
            continue
        h = cache_key(k)
        if h not in df_hashed:
            df_hashed[h] = {}
        df_hashed[h][k] = v
    return df_hashed


def cache_save_key(key: str, data):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", tables.NaturalNameWarning)
        # print('{} {}'.format(key, data.keys()))
        cache_name = "{}/{}.h5".format(CACHE_DIR, key)
        # print(cache_name)
        fl.save(path=cache_name, data=data)


def cache_save(df_all: dict):
    pathlib.Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    df_hashed = cache_hash(df_all)
    for key, data in df_hashed.items():
        cache_save_key(key, data)
    print("(saved {} speakers)".format(len(df_all)))


def is_filtered(speaker: str, filters: dict):
    if filters.get("speaker_name") is not None and filters.get("speaker_name") != speaker:
        return True

    current = None
    if speaker in metadata.speakers_info:
        if "default_measurement" not in metadata.speakers_info[speaker]:
            print("error no default measurement for {}".format(speaker))
            return True
        first = metadata.speakers_info[speaker]["default_measurement"]
        if first not in metadata.speakers_info[speaker]["measurements"]:
            # only happens when you change the metadata
            return False
        current = metadata.speakers_info[speaker]["measurements"][first]

    if (
        filters.get("origin") is not None
        and current is not None
        and current["origin"] != filters.get("origin")
    ):
        return True

    return (
        filters.get("format") is not None
        and current is not None
        and current["format"] != filters.get("format")
    )


def cache_load_seq(filters, smoke_test):
    df_all = defaultdict()
    cache_files = glob("{}/*.h5".format(CACHE_DIR))
    count = 0
    logging.debug("found %d cache files", len(cache_files))
    for cache in cache_files:
        speaker_name = filters.get("speaker_name")
        if speaker_name is not None and cache[-5:-3] != cache_key(speaker_name):
            logging.debug("skipping %s key=%s", speaker_name, cache_key(speaker_name))
            continue
        df_read = fl.load(path=cache)
        logging.debug("reading file %s found %d entries", cache, len(df_read) if df_read else 0)
        if not isinstance(df_read, dict):
            continue
        for speaker, data in df_read.items():
            if speaker in df_all:
                print("error in cache: {} is already in keys".format(speaker))
                continue
            if is_filtered(speaker, filters):
                # print(speaker, speaker_name)
                continue
            df_all[speaker] = data
            count += 1
        if smoke_test and count > 10:
            break

    print("(loaded {} speakers)".format(len(df_all)))
    return df_all


@ray.remote(num_cpus=1)
def cache_fetch(cachepath: str, level):
    logger = logging.getLogger("spinorama")
    ray_setup_logger(level)
    logger.debug("Level of debug is %d", level)
    return fl.load(path=cachepath)


def cache_load_distributed_map(filters, smoke_test, level):
    cache_files = glob("./{}/*.h5".format(CACHE_DIR))
    ids = []
    # mapper read the cache and start 1 worker per file
    for cache in cache_files:
        if filters.get("speaker_name") is not None and cache[-5:-3] != cache_key(
            filters.get("speaker_name")
        ):
            continue
        ids.append(cache_fetch.remote(cache, level))

    print("(queued {} files)".format(len(cache_files)))
    return ids


def cache_load_distributed_reduce(filters, smoke_test, ids):
    df_all = defaultdict()
    count = 0
    while 1:
        done_ids, remaining_ids = ray.wait(ids, num_returns=min(len(ids), 64))
        for id in done_ids:
            df_read = ray.get(id)
            for speaker, data in df_read.items():
                if speaker in df_all:
                    print("error in cache: {} is already in keys".format(speaker))
                if is_filtered(speaker, filters):
                    continue
                df_all[speaker] = data
                count += 1
                if smoke_test and count > 10:
                    break

        if len(remaining_ids) == 0:
            break

        ids = remaining_ids

    print("(loaded {} speakers)".format(len(df_all)))
    return df_all


def cache_load_distributed(filters, smoke_test, level):
    ids = cache_load_distributed_map(filters, smoke_test, level)
    return cache_load_distributed_reduce(filters, smoke_test, ids)


def cache_load(filters, smoke_test, level):
    if ray.is_initialized and filters.get("speaker_name") is None:
        return cache_load_distributed(filters, smoke_test, level)
    return cache_load_seq(filters, smoke_test)


def cache_update(df_new, filters, level):
    if not os.path.exists(CACHE_DIR) or len(df_new) == 0:
        return

    print("Updating cache ", end=" ", flush=True)
    count = 0
    for new_speaker, new_datas in df_new.items():
        if filters is not None and new_speaker != filters.get("speaker", ""):
            continue
        df_old = cache_load(filters={"speaker_name": new_speaker}, smoke_test=False, level=level)
        for new_origin, new_measurements in new_datas.items():
            for new_measurement, new_data in new_measurements.items():
                if new_speaker not in df_old:
                    df_old[new_speaker] = {new_origin: {new_measurement: new_data}}
                elif new_origin not in df_old[new_speaker]:
                    df_old[new_speaker][new_origin] = {new_measurement: new_data}
                else:
                    df_old[new_speaker][new_origin][new_measurement] = new_data
                count += 1
        cache_save_key(cache_key(new_speaker), df_old)
    print(f"(updated +{count}) ", end=" ", flush=True)
    print("(saved).")


def sort_metadata_per_date(meta):
    def sort_meta_date(s):
        if s is not None:
            return s.get("review_published", "20170101")
        return "20170101"

    keys_sorted_date = sorted(
        meta,
        key=lambda a: sort_meta_date(
            meta[a]["measurements"].get(meta[a].get("default_measurement"))
        ),
        reverse=True,
    )
    return {k: meta[k] for k in keys_sorted_date}


def sort_metadata_per_score(meta):
    def sort_meta_score(s):
        if s is not None and "pref_rating" in s and "pref_score" in s["pref_rating"]:
            return s["pref_rating"]["pref_score"]
        return -1

    keys_sorted_score = sorted(
        meta,
        key=lambda a: sort_meta_score(
            meta[a]["measurements"].get(meta[a].get("default_measurement"))
        ),
        reverse=True,
    )
    return {k: meta[k] for k in keys_sorted_score}


def find_metadata_file():
    if not flags_ADD_HASH:
        return [cpaths.CPATH_DOCS_METADATA_JSON, cpaths.CPATH_DOCS_EQDATA_JSON]

    json_paths = []
    for radical, json_path in (
        ("metadata", cpaths.CPATH_DOCS_METADATA_JSON),
        ("eqdata", cpaths.CPATH_DOCS_EQDATA_JSON),
    ):
        pattern = "{}-[0-9a-f]*.json".format(json_path[:-5])
        json_filenames = glob(pattern)
        json_filename = None
        for json_maybe in json_filenames:
            regexp = ".*/{}[-][0-9a-f]{{5}}[.]json$".format(radical)
            check = re.match(regexp, json_maybe)
            if check is not None:
                json_filename = json_maybe
                break
        if json_filename is not None and os.path.exists(json_filename):
            json_paths.append(json_filename)
        else:
            json_paths.append(None)
    return json_paths


def find_metadata_chunks():
    json_paths = {}
    json_path = cpaths.CPATH_DOCS_METADATA_JSON
    pattern = "{}*.json".format(json_path[:-5])
    regexp = "{}[-][0-9a-z]{{4}}[.]json$".format(json_path[:-5])
    if flags_ADD_HASH:
        regexp = "{}[-][0-9a-z]{{4}}[-][0-9a-f]{{5}}[.]json$".format(json_path[:-5])
    json_filenames = glob(pattern)
    for json_filename in json_filenames:
        check = re.search(regexp, json_filename)
        if not check:
            # print('{} does not match'.format(json_filename))
            continue
        if os.path.exists(json_filename):
            span = check.span()
            if flags_ADD_HASH:
                tokens = json_filename[span[0] : span[1]].split("-")
                json_paths[tokens[1]] = json_filename
            else:
                tokens = json_filename[span[0] : span[1]].split("-")
                json_paths[tokens[1].split(".")[0]] = json_filename
    return json_paths
