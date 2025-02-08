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
import json
import os
import urllib.parse
from sys import argv


def parse(datas):
    """parse json data and extract ranges"""
    ranges = datas["ranges"]
    text = datas["text"]
    url = datas["url"]
    path = urllib.parse.urlparse(url).path
    output = "./tmp/{}".format(os.path.basename(path))
    if output == "./tmp/":
        return
    print("debug: {}".format(output))
    with open(output, "w") as fd:
        fd.write(" ".join([text[range["start"] : range["end"]] for range in ranges]))


def main(filename):
    """read file, convert to json and parse it"""
    with open(filename, "r") as f_d:
        datas = json.load(f_d)
        for _, data in enumerate(datas):
            parse(data)


if __name__ == "__main__":
    if len(argv) != 2:
        print(f"usage: {argv[0]} coverage_file.json")
    main(argv[1])
