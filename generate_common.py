#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
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

import ipaddress
import logging
import os
import sys
import warnings

import flammkuchen as fl
import tables

try:
    import ray

    MINIRAY = False
except ModuleNotFoundError:
    import src.miniray as ray

    MINIRAY = True


def get_custom_logger(duplicate=False):
    """ "define properties of our logger"""
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
    return custom


def args2level(args):
    """ "transform an argument into a logger level"""
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
        dashboard_port = check_port

    # this start ray in single process mode
    ray_local_mode = False
    if "--ray-local" in args and args["--ray-local"] is True:
        ray_local_mode = True

    level = args2level(args)

    def ray_setup_logger(worker_logger):
        worker_logger = get_custom_logger(False)
        worker_logger.setLevel(level)

    ray.worker.global_worker.run_function_on_all_workers(ray_setup_logger)
    # address is the one from the ray server<
    ray.init(
        dashboard_host=dashboard_ip,
        dashboard_port=dashboard_port,
        local_mode=ray_local_mode,
    )


CACHE_NAME = "cache.parse_all_speakers.h5"
SMOKE_CACHE_NAME = "cache.smoketest_speakers.h5"


def cache_key(name):
    return name[0]


def cache_hash(df_all):
    df = {}
    for k, v in df_all.items():
        h = cache_key(k)
        if h not in df.keys():
            df[h] = {}
        df[h][k] = v
    return df


def cache_unhash(df_all):
    df = {}
    for _, v in df_all.items():
        for k2, v2 in v.items():
            df[k2] = v2
    return df


def cache_save(df_all, smoke_test=False):
    df_hashed = cache_hash(df_all)
    cache_name = CACHE_NAME
    if smoke_test:
        cache_name = SMOKE_CACHE_NAME
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", tables.NaturalNameWarning)
        fl.save(path=cache_name, data=df_hashed)


def cache_load(filter=None, smoke_test=False):
    df_all = None
    cache_name = CACHE_NAME
    if smoke_test:
        cache_name = SMOKE_CACHE_NAME
    if filter is None:
        df_all = fl.load(path=cache_name)
    else:
        df_read = fl.load(
            path=cache_name,
            group="/{}/{}".format(cache_key(filter), filter),
        )
        df_all = {
            cache_key(filter): {
                filter: df_read,
            },
        }
    return cache_unhash(df_all)


def cache_update(df_new):
    if not os.path.exists(CACHE_NAME) or len(df_new) == 0:
        return

    print("Updating cache ", end=" ", flush=True)
    df_tbu = cache_unhash(fl.load(path=CACHE_NAME))
    print("(loaded {}) ".format(len(df_tbu)), end=" ", flush=True)
    count = 0
    for new_speaker, new_datas in df_new.items():
        for new_origin, new_measurements in new_datas.items():
            for new_measurement, new_data in new_measurements.items():
                if new_speaker not in df_tbu.keys():
                    df_tbu[new_speaker] = {new_origin: {new_measurement: new_data}}
                elif new_origin not in df_tbu[new_speaker].keys():
                    df_tbu[new_speaker][new_origin] = {new_measurement: new_data}
                else:
                    df_tbu[new_speaker][new_origin][new_measurement] = new_data
                count += 1
    print("(updated +{}) ".format(count), end=" ", flush=True)
    cache_save(df_tbu)
    print("(saved).")
