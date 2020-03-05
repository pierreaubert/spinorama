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
usage: update_html.py [--help] [--version] [--dev]\
 [--width=<width>] [--height=<height>] [--force] [--type=<ext>]\
 [--sitedev=<http>]  [--log-level=<level>] [--origin=<origin>]\
 [--speaker=<speaker>]

Options:
  --help            display usage()
  --version         script version number
  --width=<width>   width size in pixel
  --height=<height> height size in pixel
  --force           force regeneration of all graphs, by default only generate new ones
  --type=<ext>      choose one of: json, html, png, svg
  --sitedev=<http>  default: http://localhost:8000/docs
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --origin=<origin> restrict to a specific origin, usefull for debugging
  --speaker=<speaker> restrict to a specific speaker, usefull for debugging
"""
import os
import sys
import json
import logging
from mako.template import Template
from mako.lookup import TemplateLookup
from src.spinorama.load import parse_all_speakers, parse_graphs_speaker
from src.spinorama.analysis import estimates, speaker_pref_rating
import datas.metadata as metadata
from docopt import docopt


siteprod = 'https://pierreaubert.github.io/spinorama'
sitedev = 'http://localhost:8000/docs/'


def sanity_check(df, meta):
    for speaker_name, origins in df.items():
        # check if metadata exists
        if speaker_name not in meta:
            logging.error('Metadata not found for >{:s}<'.format(speaker_name))
            return 1
        # check if each measurement looks reasonable
        for origin, keys in origins.items():
            if origin not in ['ASR', 'Princeton'] and origin[0:8] != 'Vendors/':
                logging.error('Measurement origin >{:s}< is unkown for >{:s}'.format(origin, speaker_name))
                return 1
            if 'default' not in keys.keys():
                logging.error('Key default is mandatory for >{:s}<'.format(speaker_name))
                return 1
        # check if image exists
        if not os.path.exists('datas/originals/' + speaker_name + '.jpg'):
            print('Fatal: Image associated with >', speaker_name, '< not found!')
            return 1
        # check if downscale image exists
        if not os.path.exists('docs/metadata/' + speaker_name + '.jpg'):
            print('Fatal: Image associated with >', speaker_name, '< not found!')
            print('Please run: cd docs && ./convert.sh')
            return 1
    return 0


def add_estimates(df):
    """""Compute some values per speaker and add them to metadata """
    for speaker_name, speaker_data in df.items():
        for origin, measurements in speaker_data.items():
            if origin == 'Princeton':
                # this measurements are only valid above 500hz
                return
            for m, dfs in measurements.items():
                if m == 'default':
                    if 'CEA2034' in dfs.keys():
                        spin = dfs['CEA2034']
                        if spin is not None:
                            # basic math
                            onaxis = spin.loc[spin['Measurements'] == 'On Axis']
                            est = estimates(onaxis)
                            logging.info('Adding -3dB {:d}Hz -6dB {:d}Hz +/-{:f}dB'.format(est[1], est[2], est[3]))
                            metadata.speakers_info[speaker_name]['estimates'] = est
                            # from Olive&all paper
                            metadata.speakers_info[speaker_name]['pref_rating'] = speaker_pref_rating(spin)


def generate_speaker(mako, df, meta, site):
    speaker_html = mako.get_template('speaker.html')
    graph_html = mako.get_template('graph.html')
    for speaker_name, origins in df.items():
        for origin, measurements in origins.items():
            for m, dfs in measurements.items():
                # freq
                freq_filter = [
                    "CEA2034",
                    "Early Reflections",
                    "Estimated In-Room Response",
                    "Horizontal Reflections", "Vertical Reflections",
                    "SPL Horizontal", "SPL Vertical",
                ]
                freqs = {key: dfs[key] for key in freq_filter if key in dfs}
                # contour
                contour_filter = [
                    "SPL Horizontal_unmelted",
                    "SPL Vertical_unmelted",
                ]
                contours = {key: dfs[key] for key in contour_filter if key in dfs}
                # radar
                radar_filter = [
                    "SPL Horizontal_unmelted",
                    "SPL Vertical_unmelted"
                ]
                radars = {key: dfs[key] for key in radar_filter if key in dfs}

                # get index.html filename
                dirname = 'docs/' + speaker_name + '/'
                if origin == 'ASR' or origin == 'Princeton':
                    dirname += origin
                else:
                    dirname += meta[speaker_name]['brand']
                indexname = dirname + '/index.html'

                # write index.html
                logging.info('Writing index.html for {:s}'.format(speaker_name))
                with open(indexname, 'w') as f:
                    # write all
                    f.write(speaker_html.render(speaker=speaker_name, freqs=freqs, contours=contours,
                                                radars=radars, meta=meta, site=site))
                    f.close()

                # write a small file per graph to render the json generated by Vega
                for kind, suffix in [(freqs, ''), (contours, ' Contour'), (radars, ' Radar')]:
                    for graph_type in kind:
                        graph_name = graph_type.replace('_unmelted','') + suffix
                        graph_filename = dirname + '/default/' + graph_name + '.html'
                        logging.info('Writing default/{0}.html for {1}'.format(graph_name, speaker_name))
                        with open(graph_filename, 'w') as f:
                            f.write(graph_html.render(graph=graph_name, meta=meta, site=site))
                            f.close()
    return 0


def dump_metadata(meta):
    with open('docs/assets/metadata.json', 'w') as f:
        js = json.dumps(meta)
        f.write(js)
        f.close()


if __name__ == '__main__':
    args = docopt(__doc__,
                  version='update_html.py version 1.21',
                  options_first=True)

    # check args section
    width = 600
    height = 200
    force = args['--force']
    ptype = None

    if args['--width'] is not None:
        width = int(args['--width'])

    if args['--height'] is not None:
        height = int(args['--height'])

    if args['--type'] is not None:
        ptype = args['--type']
        if type not in ('png', 'html', 'svg', 'json'):
            print('type %s is not recognize!'.format(ptype))
            exit(1)

    dev = args['--dev']
    site = siteprod
    if dev is True:
        if args['--sitedev'] is not None:
            sitedev = args['--sitedev']
            if len(sitedev) < 4 or sitedev[0:4] != 'http':
                print('sitedev %s does not start with http!'.format(sitedev))
                exit(1)

        site = sitedev

    if args['--log-level'] is not None:
        level = args['--log-level']
        if level in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
            logging.basicConfig(level=level)

    generate_all_speakers = True
    # read data from disk
    if args['--speaker'] is not None and args['--origin'] is not None:
        speaker = args['--speaker']
        origin = args['--origin']
        mformat = None
        if origin == 'Princeton':
            mformat = 'princeton'
        elif origin == 'ASR':
            mformat = 'klippel'
        else:
            mformat = 'webplotdigitizer'
        brand = metadata.speakers_info[speaker]['brand']
        df = {}
        df[speaker] = {}
        df[speaker][origin] = {}
        df[speaker][origin]['default'] = parse_graphs_speaker(brand, speaker, mformat)
        generate_all_speakers = False
    else:
        df = parse_all_speakers(metadata.speakers_info)
        
    if sanity_check(df, metadata.speakers_info) != 0:
        logging.error('Sanity checks failed!')
        sys.exit(1)

    # add computed data to metadata
    logging.info('Compute estimates per speaker')
    add_estimates(df)

    # configure Mako
    mako_templates = TemplateLookup(directories=['templates'], module_directory='/tmp/mako_modules')

    # write metadata in a json file for easy search
    if generate_all_speakers:
        logging.info('Write metadat')
        dump_metadata(metadata.speakers_info)

    # write index.html
    if generate_all_speakers:
        logging.info('Write index.html')
        index_html = mako_templates.get_template('index.html')
        with open('docs/index.html', 'w') as f:
            f.write(index_html.render(df=df, meta=metadata.speakers_info, site=site))
            f.close()

    # write help.html
    if generate_all_speakers:
        logging.info('Write help.html')
        help_html = mako_templates.get_template('help.html')
        with open('docs/help.html', 'w') as f:
            f.write(help_html.render(df=df, meta=metadata.speakers_info, site=site))
            f.close()

    # write a file per speaker
    logging.info('Write a file per speaker')
    generate_speaker(mako_templates, df, metadata.speakers_info, site=site)

    if generate_all_speakers:
        logging.info('Copy js/css files to docs')
        for f in ['search.js', 'bulma.js', 'compare.js', 'tabs.js', 'spinorama.css']:
            file_ext = Template(filename='templates/assets/'+f)
            with open('docs/assets/'+f, 'w') as fd:
                fd.write(file_ext.render(site=site))
                fd.close()

    # generate potential missing graphs
    # logging.info('Generate missing graphs')
    # generate_graphs(df, width, height, force, ptype)

    sys.exit(0)
