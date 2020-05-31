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
usage: generate_stats.py [--help] [--version] [--dev]\
 [--sitedev=<http>]  [--log-level=<level>]

Options:
  --help            display usage()
  --version         script version number
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
"""
import json
import logging
import os
import sys
import pathlib
from docopt import docopt
import pandas as pd
import altair as alt


def meta2df(meta):
    df = pd.DataFrame({'speaker': [], 'param': [], 'value': []})
    count = 0
    for i in meta:
        speaker = meta[i]
        for p in speaker:
            val = speaker[p]
            if type(val) is dict:
                for v in val.keys():
                    # print('{0} {1} {2}'.format(i, v, val[v]))
                    df.loc[count] = [i, v, val[v]]
                    count += 1
            else:
                # print('{0} {1} {2}'.format(i, p, val))
                df.loc[count] = [i, p, val]
                count += 1

    return df


def generate_stats(meta):
    df = meta2df(meta)

    pref_score = df.loc[(df.param == 'pref_score')].reset_index()
    pref_score_wsub = df.loc[(df.param == 'pref_score_wsub')].reset_index()
    brand = df.loc[(df.param == 'brand')].reset_index()
    lfx_hz = df.loc[(df.param == 'lfx_hz')].reset_index()
    nbd_on = df.loc[(df.param == 'nbd_on_axis')].reset_index()
    nbd_pir = df.loc[(df.param == 'nbd_pred_in_room')].reset_index()
    sm_pir = df.loc[(df.param == 'sm_pred_in_room')].reset_index()

    spread_score = alt.Chart(pref_score).mark_circle(size=30).encode(
        x=alt.X('speaker', sort='y', axis=alt.Axis(labelAngle=45), title='Speakers sorted by Preference Score'),
        y=alt.Y('value', title='Preference Score')
    ).properties(width=1024,height=300)
    
    spread_score_wsub = alt.Chart(pref_score_wsub).mark_circle(size=30).encode(
        x=alt.X('speaker', sort='y', axis=alt.Axis(labelAngle=45), title='Speakers sorted by Preference Score with a Subwoofer'),
        y=alt.Y('value', title='Preference Score w/Sub')
    ).properties(width=1024,height=300)

    distribution1 = alt.Chart(pref_score).mark_bar().encode(
        x=alt.X('value:Q', bin=True, title='Preference Score'),
        y=alt.Y('count()', title='Count')
    ).properties(width=450, height=300)

    distribution2 = alt.Chart(pref_score_wsub).mark_bar().encode(
        x=alt.X('value:Q', bin=True, title='Preference Score w/Sub'),
        y=alt.Y('count()', title='Count')
    ).properties(width=450, height=300)

    distribution = distribution1 | distribution2 

    source = pd.DataFrame({
        'speaker': pref_score.speaker,
        'brand': brand.value,
        'pref_score': pref_score.value,
        'lfx_hz': lfx_hz.value,
        'nbd_on': nbd_on.value,
        'nbd_pir': nbd_pir.value,
        'sm_pir': sm_pir.value,
    }).dropna()

    graphs = {}
    for g in ('lfx_hz', 'nbd_pir', 'nbd_on', 'sm_pir'):
        data = alt.Chart(source).mark_point().encode(
            x=alt.X('{0}:Q'.format(g)),
            y=alt.Y('pref_score:Q', title='Preference Score'),
            color=alt.Color('brand:N'),
            tooltip=['speaker', g, 'pref_score']
        )
        graphs[g] = data+data.transform_regression(g, 'pref_score').mark_line()

    correlation = (graphs['lfx_hz'] | graphs['nbd_on']) & (graphs['nbd_pir'] | graphs['sm_pir'])

    # used in website
    filedir = 'docs/stats'
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)

    for graph, name in ((correlation, 'correlation'),
                        (distribution, 'distribution'),
                        (spread_score, 'spread_score'),
                        (spread_score_wsub, 'spread_score_wsub')):
        filename = '{0}/{1}.json'.format(filedir, name)
        graph.save(filename)

    # used in book
    filedir = 'book/stats'
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)

    for graph in graphs.keys():
        graph_name = '{0}/{1}.png'.format(filedir, graph)
        graphs[graph].save(graph_name)

    for graph, name in ((distribution1, 'distribution1'),
                        (distribution2, 'distribution2'),
                        (spread_score, 'spread_score'),
                        (spread_score_wsub, 'spread_score_wsub')):
        filename = '{0}/{1}.png'.format(filedir, name)
        graph.save(filename)

    return 0


if __name__ == '__main__':
    args = docopt(__doc__,
                  version='generate_stats.py version 0.1',
                  options_first=True)

    level = None
    if args['--log-level'] is not None:
        check_level = args['--log-level']
        if check_level in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
            level = check_level

    if level is not None:
        logging.basicConfig(
            format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d:%H:%M:%S',
            level=level)
    else:
        logging.basicConfig(
            format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d:%H:%M:%S')

    # load all metadata from generated json file
    json_filename = './docs/assets/metadata.json'
    if not os.path.exists(json_filename):
        logging.fatal('Cannot find {0}'.format(json_filename))
        sys.exit(1)

    meta = None
    with open(json_filename, 'r') as f:
        meta = json.load(f)

    generate_stats(meta)

    sys.exit(0)
