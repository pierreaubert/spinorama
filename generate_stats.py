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
    brand = df.loc[(df.param == 'brand')].reset_index()
    lfx_hz = df.loc[(df.param == 'lfx_hz')].reset_index()
    nbd_on = df.loc[(df.param == 'nbd_on_axis')].reset_index()
    nbd_pir = df.loc[(df.param == 'nbd_pred_in_room')].reset_index()
    sm_pir = df.loc[(df.param == 'sm_pred_in_room')].reset_index()

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
            y=alt.Y('pref_score:Q'),
            color=alt.Color('brand:N'),
            tooltip=['speaker', g, 'pref_score']
        )
        graphs[g] = data+data.transform_regression(g, 'pref_score').mark_line()

    correlation = (graphs['lfx_hz'] | graphs['nbd_on']) & (graphs['nbd_pir'] | graphs['sm_pir'])

    distribution = alt.Chart(source).mark_bar().encode(
        x=alt.X('pref_score:Q', bin=True),
        y='count()'
    ).properties(width=300, height=300)

    spread = alt.Chart(source).mark_circle(size=30).encode(
        x=alt.X('speaker', sort='y', axis=alt.Axis(labelAngle=45)),
        y=alt.Y('pref_score')
    ).properties(width=1024,height=300)

    scores = spread & distribution

    # used in website
    filedir = 'docs/stats'
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)

    corname = filedir + '/correlation.json'
    correlation.save(corname)

    scoresname = filedir + '/scores.json'
    scores.save(scoresname)

    # used in book
    filedir = 'book/stats'
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)

    for graph in graphs.keys():
        graph_name = '{0}/{1}.png'.format(filedir, graph)
        graphs[graph].save(graph_name)

    spread_name = '{0}/spread.png'.format(filedir)
    spread.save(spread_name)

    distribution_name = '{0}/distribution.png'.format(filedir)
    distribution.save(distribution_name)

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
