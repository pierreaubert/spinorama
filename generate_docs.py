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
usage: update-docs.py [--help] [--version] [--dev] [--width=<width>] [--height=<height>] [--force] [--type=<ext>]

Options:
  --help            display usage()
  --version         script version number
  --width=<width>   width size in pixel
  --height=<height> height size in pixel
  --force           force regeneration of all graphs, by default only generate new ones
  --type=<ext>      choose one of: json, html, png, svg
"""
import os
import sys
import json
from mako.template import Template
from mako.lookup import TemplateLookup
from src.spinorama.load import parse_all_speakers
from src.spinorama.analysis import estimates
import datas.metadata as metadata
from generate_graphs import generate_graphs

from docopt import docopt

siteprod = 'https://pierreaubert.github.io/spinorama'
sitedev = 'http://localhost:8000/docs/'

if __name__ == '__main__':
    args = docopt(__doc__,
                  version='update-docs.py version 1.1',
                  options_first=True)

    dev = args['--dev']
    site = siteprod
    if dev is True:
        site = sitedev

    width = 1200
    height = 600
    force = args['--force']
    type = None

    if args['--width'] is not None:
        width = int(args['--width'])

    if args['--height'] is not None:
        height = int(args['--height'])

    if args['--type'] is not None:
        type = args['--type']
        if type not in ('png', 'html', 'svg', 'json'):
            print('type %s is not recognize!'.format(type))
            exit(1)

    # read data from disk
    df = parse_all_speakers()

    # some sanity checks
    for k, v in df.items():
        # check if metadata exists
        if k not in metadata.speakers_info:
            print('Metadata not found for >', k, '<')
            sys.exit(1)
        # check if image exists
        if not os.path.exists('datas/originals/' + k + '.jpg'):
            print('Image associated with >', k, '< not found!')
            sys.exit(1)
        # check if downscale image exists
        if not os.path.exists('docs/metadata/' + k + '.jpg'):
            print('Image associated with >', k, '< not found!')
            print('Please run: cd docs && ./convert.sh')
            sys.exit(1)


    # add computed data to metadata
    for k, v in df.items():
        try:
            spin = df[k]['CEA2034']
            onaxis = spin.loc[spin['Measurements'] == 'On Axis']
            metadata.speakers_info[k]['estimates'] = estimates(onaxis)
        except ValueError:
            print('Computing estimates failed for speaker: ' + k)

    # configure Mako
    mako_templates = TemplateLookup(directories=['templates'], module_directory='/tmp/mako_modules')

    # write index.html
    index_html = mako_templates.get_template('index.html')
    with open('docs/index.html', 'w') as f:
        f.write(index_html.render(speakers=df, meta=metadata.speakers_info, site=site))
        f.close()

    # write a file per speaker
    speaker_html = mako_templates.get_template('speaker.html')
    for speaker, measurements in df.items():
        with open('docs/' + speaker + '.html', 'w') as f:
            freq_filter = [
                "CEA2034",
                "Early Reflections",
                "Estimated In-Room Response",
                "Horizontal Reflections",
                "Vertical Reflections",
                "SPL Horizontal",
                "SPL Vertical"
            ]
            freqs = {key: measurements[key]
                     for key in freq_filter if key in measurements}
            contour_filter = [
                "SPL Horizontal_unmelted",
                "SPL Vertical_unmelted"
            ]
            contours = {key: measurements[key]
                        for key in contour_filter if key in measurements}
            radar_filter = [
                "SPL Horizontal_unmelted",
                "SPL Vertical_unmelted"
            ]
            radars = {key: measurements[key]
                      for key in radar_filter if key in measurements}
            f.write(speaker_html.render(speaker=speaker,
                                        freqs=freqs,
                                        contours=contours,
                                        radars=radars,
                                        meta=metadata.speakers_info,
                                        site=site))
            f.close()

    # write help.html
    help_html = mako_templates.get_template('help.html')
    with open('docs/help.html', 'w') as f:
        f.write(help_html.render(speakers=df, meta=metadata.speakers_info, site=site))
        f.close()

    # write metadata in a json file for easy search
    def flatten(d):
        f = []
        for k, v in d.items():
            s = {}
            s['speaker'] = k
            for k2, v2 in v.items():
                s[k2] = v2
            f.append(s)
        return f

    with open('docs/assets/metadata.json', 'w') as f:
        meta = flatten(metadata.speakers_info)
        js = json.dumps(meta)
        f.write(js)
        f.close()

    search_js = Template(filename='templates/search.js')
    with open('docs/assets/metadata.js', 'w') as f:
        f.write(search_js.render(site=site))
        f.close()

    # generate potential missing graphs
    generate_graphs(df, width, height, force, type)

    sys.exit(0)
