#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
usage: generate_book.py [--help] [--version] [--log-level=<level>]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import json
import logging
import os
import sys
from glob import glob
from mako.lookup import TemplateLookup
from docopt import docopt


if __name__ == "__main__":
    args = docopt(__doc__, version="generate_book.py version 0.1", options_first=True)

    # logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    #                    datefmt='%Y-%m-%d:%H:%M:%S')
    if args["--log-level"] is not None:
        level = args["--log-level"]
        if level in ["INFO", "DEBUG", "WARNING", "ERROR"]:
            logging.basicConfig(level=level)

    # load all metadata from generated json file
    json_filename = "../docs/assets/metadata.json"
    if not os.path.exists(json_filename):
        logging.fatal("Cannot find {0}".format(json_filename))
        sys.exit(1)

    meta = None
    with open(json_filename, "r") as f:
        meta = json.load(f)

    def sort_meta(s):
        if "pref_rating" in s.keys():
            if "pref_score" in s["pref_rating"].keys():
                return s["pref_rating"]["pref_score"]
        return -1

    keys_sorted = sorted(meta, key=lambda a: sort_meta(meta[a]), reverse=True)
    meta_sorted = {k: meta[k] for k in keys_sorted}

    # only build a dictionnary will all graphs
    speakers = {}
    names = glob("./tmp/*.eps")
    for name in names:
        speaker_name = name.replace("./tmp/", "")
        speaker_title = speaker_name.replace("-", " ").replace(".eps", "")
        speakers[speaker_name] = {"image": speaker_name, "title": speaker_title}

    # configure Mako
    mako_templates = TemplateLookup(
        directories=["."], module_directory="/tmp/mako_modules"
    )

    # write index.html
    for template in ("asrbook",):
        name = "{0}.tex".format(template)
        logging.info("Write {0} ({1} speakers found".format(name, len(speakers.keys())))
        template_tex = mako_templates.get_template(name)

        with open("tmp/{0}".format(name), "w") as f:
            f.write(template_tex.render(speakers=speakers, meta=meta_sorted))
            f.close()

    sys.exit(0)
