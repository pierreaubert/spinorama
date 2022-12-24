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

from collections import defaultdict
import difflib
from glob import glob
from hashlib import md5
import ipaddress
import logging
import os
import pathlib
import sys
import warnings

import flammkuchen as fl
import tables

import datas.metadata as metadata

MINIRAY = None
try:
    import ray

    MINIRAY = False
except ModuleNotFoundError:
    import src.miniray as ray

    MINIRAY = True


def get_similar_names(speakername):
    return difflib.get_close_matches(speakername, metadata.speakers_info.keys())


def get_custom_logger(duplicate=False):
    """Define properties of our logger"""
    custom = logging.getLogger("spinorama")
    custom_file_handler = logging.FileHandler("debug_optim.log")
    formatter = logging.Formatter("%(asctime)s - %(filename)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s")
    custom_file_handler.setFormatter(formatter)
    custom.addHandler(custom_file_handler)
    if duplicate is True:
        custom_stream_handler = logging.StreamHandler(sys.stdout)
        custom_stream_handler.setFormatter(formatter)
        custom.addHandler(custom_stream_handler)
    return custom


def args2level(args):
    """Transform an argument into a logger level"""
    level = logging.WARNING
    if args["--log-level"] is not None:
        check_level = args["--log-level"]
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


def custom_ray_init(args):
    """Customize ray initialisation with a few parameters"""
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

    def ray_setup_logger(worker_logger):
        worker_logger = get_custom_logger(False)
        worker_logger.setLevel(level)

    # doesn't work in 2.0
    # ray.worker.global_worker.run_function_on_all_workers(ray_setup_logger)
    # address is the one from the ray server<

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
    )


CACHE_DIR = ".cache"


def cache_key(name):
    # 256 partitions, use hashlib for stable hash
    return "{:2s}".format(md5(name.encode("utf-8"), usedforsecurity=False).hexdigest()[0:2])


def cache_match(key, name):
    return key == cache_key(name)


def cache_hash(df_all):
    df = {}
    for k, v in df_all.items():
        if k is None or len(k) == 0:
            continue
        h = cache_key(k)
        if h not in df.keys():
            df[h] = {}
        df[h][k] = v
    return df


def cache_save_key(key, data):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", tables.NaturalNameWarning)
        # print('{} {}'.format(key, data.keys()))
        cache_name = "{}/{}.h5".format(CACHE_DIR, key)
        # print(cache_name)
        fl.save(path=cache_name, data=data)


def cache_save(df_all, smoke_test=False):
    pathlib.Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    df_hashed = cache_hash(df_all)
    for key, data in df_hashed.items():
        cache_save_key(key, data)
    print("(saved {} speakers)".format(len(df_all)))


def cache_load_seq(simple_filter=None, smoke_test=False):
    df_all = defaultdict()
    cache_files = glob("{}/*.h5".format(CACHE_DIR))
    count = 0
    for cache in cache_files:
        if simple_filter is not None and cache[-5:-3] != cache_key(simple_filter):
            continue
        df_read = fl.load(path=cache)
        # print('reading file {} found {} entries'.format(cache, len(df_read)))
        for speaker, data in df_read.items():
            if speaker in df_all.keys():
                print("error in cache: {} is already in keys".format(speaker))
            if simple_filter is not None and speaker != simple_filter:
                # print(speaker, simple_filter)
                continue
            df_all[speaker] = data
            count += 1
        if smoke_test and count > 10:
            break

    print("(loaded {} speakers)".format(len(df_all)))
    return df_all


@ray.remote(num_cpus=1)
def cache_fetch(cachepath):
    return fl.load(path=cachepath)


def cache_load_distributed_map(simple_filter=None, smoke_test=False):
    cache_files = glob("{}/*.h5".format(CACHE_DIR))
    ids = []
    # mapper read the cache and start 1 worker per file
    for cache in cache_files:
        if simple_filter is not None and cache[-5:-3] != cache_key(simple_filter):
            continue
        ids.append(cache_fetch.remote(cache))

    print("(queued {} files)".format(len(cache_files)))
    return ids


def cache_load_distributed_reduce(simple_filter, smoke_test, ids1):
    df_all = defaultdict()
    count = 0
    ids = ids1
    while 1:

        done_ids, remaining_ids = ray.wait(ids, num_returns=min(len(ids), 64))
        for id in done_ids:
            df_read = ray.get(id)
            for speaker, data in df_read.items():
                if speaker in df_all.keys():
                    print("error in cache: {} is already in keys".format(speaker))
                if simple_filter is not None and speaker != simple_filter:
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


def cache_load_distributed(simple_filter=None, smoke_test=False):
    ids = cache_load_distributed_map(simple_filter, smoke_test)
    return cache_load_distributed_reduce(simple_filter, smoke_test, ids)


def cache_load(simple_filter=None, smoke_test=False):
    if ray.is_initialized:
        return cache_load_distributed(simple_filter, smoke_test)
    return cache_load_seq(simple_filter, smoke_test)


def cache_update(df_new, filters):
    if not os.path.exists(CACHE_DIR) or len(df_new) == 0:
        return

    print("Updating cache ", end=" ", flush=True)
    count = 0
    for new_speaker, new_datas in df_new.items():
        if filters is not None and new_speaker != filters.get("speaker", ""):
            continue
        df_old = cache_load(new_speaker)
        for new_origin, new_measurements in new_datas.items():
            for new_measurement, new_data in new_measurements.items():
                if new_speaker not in df_old.keys():
                    df_old[new_speaker] = {new_origin: {new_measurement: new_data}}
                elif new_origin not in df_old[new_speaker].keys():
                    df_old[new_speaker][new_origin] = {new_measurement: new_data}
                else:
                    df_old[new_speaker][new_origin][new_measurement] = new_data
                count += 1
        cache_save_key(cache_key(new_speaker), df_old)
    print("(updated +{}) ".format(count), end=" ", flush=True)
    print("(saved).")
