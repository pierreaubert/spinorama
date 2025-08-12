#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

import os
import sys
import argparse
from typing import Optional


def read_on(on_spl_filename: str) -> list[tuple[float, float]]:
    on_spl = []

    with open(on_spl_filename) as fin:
        lines = fin.readlines()
        for line in lines:
            toparse = line
            if line[-2:] == "];":
                toparse = line[:-2]
            items = toparse.split()
            if len(items) == 2:
                try:
                    freq = float(items[0])
                    spl = float(items[1])
                    if freq >= 20.0 and freq <= 20000:
                        on_spl.append((freq, spl))
                except ValueError:
                    continue
    return sorted(on_spl, key=lambda x: x[0])


def read_spl(spl_filename: str) -> dict[int, list[tuple[float, float]]]:
    spl = {}
    for angle in range(-180, 190, 10):
        spl[angle] = []

    with open(spl_filename) as fin:
        lines = fin.readlines()
        for line in lines:
            toparse = line
            if line[-2:] == "];":
                toparse = line[:-2]
            items = toparse.split()
            if len(items) == 3:
                try:
                    freq = float(items[0].replace(",", ""))
                    fspl = float(items[1].replace(",", ""))
                    angle = int(items[2])
                    if freq >= 20.0 and freq <= 20000 and angle >= -180 and angle <= 180:
                        spl[angle].append((freq, fspl))
                except ValueError:
                    continue
    for angle in range(-180, 190, 10):
        spl[angle] = sorted(spl[angle], key=lambda x: x[0])
    return spl


def process_spl(
    spl: dict[int, list[tuple[float, float]]],
    on_spl: list[tuple[float, float]],
    freq_similar: float,
    freq_valid_data: float,
) -> dict[int, list[tuple[float, float]]]:
    spl_filtered = {}
    for angle in spl:
        spl_filtered[angle] = []
    # find the last spl point on ON before freq_similar
    similar_on_point = None
    valid_on_point = None
    valid_on_point2 = None
    for freq, fspl in on_spl:
        if freq <= freq_similar:
            similar_on_point = (freq, fspl)
        if freq <= freq_valid_data:
            valid_on_point = (freq, fspl)
    for freq, fspl in spl[0]:
        if freq <= freq_valid_data:
            valid_on_point2 = (freq, fspl)
    spl_shift = valid_on_point2[1] - valid_on_point[1]
    print("similar point on ON {}".format(similar_on_point))
    print("valid point on ON {}".format(valid_on_point))
    print("valid point on SPL0 {}".format(valid_on_point2))
    print("shift SPL {} to {}".format(valid_on_point[1], valid_on_point2[1]))
    for angle, spl_at_angle in spl.items():
        # take data from ON below freq_similar
        for freq, fspl in on_spl:
            if freq <= freq_similar:
                spl_filtered[angle].append((freq, fspl))
        # find the first spl point at angle after freq_valid_data
        first_angle_point = None
        for freq, fspl in spl_at_angle:
            if freq >= freq_valid_data:
                first_angle_point = (freq, fspl)
                break
        if first_angle_point is None:
            print("angle {} does not have data".format(angle))
            continue
        # between freq_similar and freq_valid_data interpolate ON SPL data such that
        # SPL at freq_similar is equal to ON SPL and SPL at freq_valid_data is equal to first_angle_point
        gap = first_angle_point[1] - spl_shift - valid_on_point[1]
        for freq, fspl in on_spl:
            if freq >= freq_similar and freq <= freq_valid_data:
                spl_interpolated = fspl + gap * (freq - similar_on_point[0]) / (
                    valid_on_point[0] - similar_on_point[0]
                )
                spl_filtered[angle].append((freq, spl_interpolated))
        # take data at angle after freq_valid_data
        for freq, fspl in spl_at_angle:
            if freq >= freq_valid_data:
                spl_filtered[angle].append((freq, fspl - spl_shift))
    return spl_filtered


def process(
    speakername: str,
    on_spl_filename: str,
    h_spl_filename: str,
    v_spl_filename: str,
    freq_similar: Optional[float] = None,
    freq_valid_data: Optional[float] = None,
) -> None:
    on_spl = read_on(on_spl_filename)
    h_spl = read_spl(h_spl_filename)
    if freq_similar is not None and freq_valid_data is not None:
        h_spl = process_spl(h_spl, on_spl, freq_similar, freq_valid_data)
    v_spl = None
    if os.path.exists(v_spl_filename):
        v_spl = read_spl(v_spl_filename)
        if freq_similar is not None and freq_valid_data is not None:
            v_spl = process_spl(v_spl, on_spl, freq_similar, freq_valid_data)

    for orientation, x_spl in (
        ("_H", h_spl),
        ("_V", v_spl),
    ):
        if x_spl is None:
            continue
        for angle, spl_at_angle in x_spl.items():
            filename = "../{} {} {}.txt".format(speakername, orientation, angle)

            if len(spl_at_angle) == 0:
                continue

            with open(filename, "w") as fout:
                for freq, spl in spl_at_angle:
                    fout.write("{} {}\n".format(freq, spl))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process audio measurement data from AudioREKR.")
    parser.add_argument("--speaker", type=str, required=True, help="Speaker name (mandatory)")
    parser.add_argument(
        "--freq-similar",
        type=float,
        help="Frequency threshold for similarity comparison (between 20 and 20000 Hz)",
        default=None,
    )
    parser.add_argument(
        "--freq-valid-data",
        type=float,
        help="Minimum valid frequency for data filtering (between 20 and 20000 Hz)",
        default=None,
    )
    parser.add_argument("--on-file", type=str, default="01_FR.txt", help="On-axis SPL filename")
    parser.add_argument(
        "--h-file",
        type=str,
        default="02_Horizontal Contour Plot.txt",
        help="Horizontal SPL filename",
    )
    parser.add_argument(
        "--v-file", type=str, default="03_Vertical Contour Plot.txt", help="Vertical SPL filename"
    )

    args = parser.parse_args()

    # Validate individual frequency arguments are in valid range
    for arg_name, arg_value in [
        ("freq_similar", args.freq_similar),
        ("freq_valid_data", args.freq_valid_data),
    ]:
        if arg_value is not None and (arg_value < 20 or arg_value > 20000):
            parser.error(f"--{arg_name.replace('_', '-')} must be between 20 and 20000 Hz")

    # Validate frequency argument relationships
    if args.freq_similar is not None and args.freq_valid_data is not None:
        if args.freq_similar >= args.freq_valid_data:
            parser.error("--freq-similar must be smaller than --freq-valid-data")

    return args


if __name__ == "__main__":
    args = parse_args()
    process(
        args.speaker,
        args.on_file,
        args.h_file,
        args.v_file,
        freq_similar=args.freq_similar,
        freq_valid_data=args.freq_valid_data,
    )
    sys.exit(0)
