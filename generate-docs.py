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
usage: update-docs.py [--version] [--dev]
"""
import json
from mako.template import Template
from src.spinorama.load import parse_all_speakers
from src.spinorama.analysis import estimates
import datas.metadata as metadata

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

    df = parse_all_speakers()

    for k, v in df.items():
        try:
            spin = df[k]['CEA2034']
            onaxis = spin.loc[spin['Measurements'] == 'On Axis']
            metadata.speakers_info[k]['estimates'] = estimates(onaxis)
        except ValueError:
            print('Computing estimates failed for speaker: ' + k)

    # write index.html
    index_html = Template(filename='templates/index.html')
    with open('docs/index.html', 'w') as f:
        f.write(index_html.render(speakers=df, meta=metadata.speakers_info, site=site))
        f.close()

    # write a file per speaker
    speaker_html = Template(filename='templates/speaker.html')
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
