#!/usr/bin/env python3
#                                                  -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2021 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
usage: generate_peqs.py [--help] [--version] [--log-level=<level>]\
    [--force] [--smoke-test] [-v|--verbose]\
    [--origin=<origin>] [--speaker=<speaker>] [--mversion=<mversion>]

Options:
  --help            display usage()
  --version         script version number
  --force           force generation of eq even if already computed
  --verbose         print some informations
  --smoke-test      test the optimiser with a small amount of variables
  --log-level=<level> default is WARNING, options are DEBUG INFO ERROR.
  --origin=<origin> restrict to a specific origin, usefull for debugging
  --speaker=<speaker> restrict to a specific speaker, usefull for debugging
  --mversion=<mversion> restrict to a specific mversion (for a given origin
                        you can have multiple measurements)
"""
from datetime import datetime
import logging
import math
import os
import pathlib
import sys

from docopt import docopt
import flammkuchen as fl
import numpy as np
import ray
import scipy.signal as sig
from scipy.stats import linregress
import scipy.optimize as opt
from scipy.interpolate import InterpolatedUnivariateSpline

from datas.metadata import speakers_info as metadata
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import peq_build  # peq_print
from spinorama.load_rewseq import parse_eq_iir_rews
from spinorama.filter_peq import peq_format_apo
from spinorama.filter_scores import scores_apply_filter, scores_print2


# ------------------------------------------------------------------------------
# various loss function
# ------------------------------------------------------------------------------


def l2_loss(local_target, freq, peq):
    # L2 norm
    return np.linalg.norm(local_target+peq_build(freq, peq), 2)


def lw_loss(local_target, freq, peq, iterations):
    # sum of L2 norms if we have multiple targets
    return np.sum([l2_loss(local_target[i], peq)
                   for i in range(0, len(local_target))])


def flat_loss(freq, local_target, peq, iterations):
    # make LW as close as target as possible and SP flat
    lw = l2_loss(local_target[0], freq, peq)
    # want sound power to be flat but not necessary aligned
    # with a target
    _, _, r_value, _, _ = linregress(np.log10(freq), local_target[1])
    sp = 1-r_value**2
    return lw+sp


def swap_loss(freq, local_target, peq, iteration):
    # try to alternate, optimise for 1 objective then the second one
    if len(local_target) == 0 or iteration < 10:
        return l2_loss([local_target[0]], peq)
    else:
        return l2_loss([local_target[1]], peq)


def alternate_loss(freq, local_target, peq, iteration):
    # optimise for 2 objectives 1 each time
    if len(local_target) == 0 or iteration % 2 == 0:
        return l2_loss([local_target[0]], peq)
    else:
        return l2_loss([local_target[1]], peq)


def score_loss(df_spin, peq):
    """Compute the preference score for speaker
    local_target: unsued
    peq: evaluated peq
    return minus score (we want to maximise the score)
    """
    _, _, score = scores_apply_filter(df_spin, peq)
    return -score['pref_score']

# ------------------------------------------------------------------------------
# compute freq and targets
# ------------------------------------------------------------------------------


def getFreq(df_speaker_data, optim_config):
    """extract freq and one curve"""
    curves = optim_config['curve_names']
    # extract LW
    columns = {'Freq'}.union(curves)
    local_df = df_speaker_data['CEA2034_unmelted'].loc[:, columns]
    # selector
    selector = local_df['Freq'] > optim_config['freq_reg_min']
    # freq
    local_freq = local_df.loc[selector, 'Freq'].values
    local_target = []
    for curve in curves:
        local_target.append(local_df.loc[selector, curve].values)
    return local_df, local_freq, local_target


def getTarget(df_speaker_data, freq, current_curve_name, optim_config):
    # freq
    current_curve = df_speaker_data.loc[
        df_speaker_data['Freq'] > optim_config['freq_reg_min'],
        current_curve_name].values
    # print(len(freq), len(current_curve))
    # compute linear reg on lw
    slope, intercept, r_value, p_value, std_err = \
        linregress(np.log10(freq), current_curve)
    # normalise to have a flat target (primarly for bright speakers)
    if current_curve_name == 'On Axis':
        slope = 0
        intercept = current_curve[0]
    elif current_curve_name == 'Listening Window':
        # slighlithy downward
        slope = -2/math.log(20000)
        intercept = current_curve[0]
    elif current_curve_name == 'Early Reflections':
        slope = -5/math.log(20000)
        intercept = current_curve[0]
    elif current_curve_name == 'Sound Power':
        slope = -8/math.log(20000)
        intercept = current_curve[0]
    else:
        logger.error('No match for getTarget')
        return None
        
    target_interp = [(slope*math.log10(freq[i])+intercept)
                     for i in range(0, len(freq))]
    logger.debug('Slope {} Intercept {} R {} P {} err {}'.format(
        slope, intercept, r_value, p_value, std_err))
    return target_interp

# ------------------------------------------------------------------------------
# find initial values for biquads
# ------------------------------------------------------------------------------


def find_largest_area(freq, curve, optim_config):

    def largest_area(positive_curve):
        #print('freq {} positive_curve {}'.format(freq, positive_curve))
        found_peaks, _ = sig.find_peaks(positive_curve, distance=10)
        if len(found_peaks) == 0:
            return None, None
        #print('found peaks at {}'.format(found_peaks))
        found_widths = sig.peak_widths(positive_curve, found_peaks,
                                       rel_height=0.1)[0]
        #print('computed width at {}'.format(found_widths))
        areas = [(i, positive_curve[found_peaks[i]]*found_widths[i])
                 for i in range(0, len(found_peaks))]
        #print('areas {}'.format(areas))
        sorted_areas = sorted(areas, key=lambda a: -a[1])
        #print('sorted {}'.format(sorted_areas))
        ipeaks, area = sorted_areas[0]
        return found_peaks[ipeaks], area

    plus_curve = np.clip(curve, a_min=0, a_max=None)
    plus_index, plus_areas = largest_area(plus_curve)
    minus_curve = -np.clip(curve, a_min=None, a_max=0)
    minus_index, minus_areas = largest_area(minus_curve)

    if minus_areas is None and plus_areas is None:
        logger.error('No initial freq found')
        return None, None, None

    if minus_areas is None:
        return +1, plus_index, freq[plus_index]

    if plus_areas is None:
        return -1, minus_index, freq[minus_index]

    if minus_areas > plus_areas:
        return -1, minus_index, freq[minus_index]
    else:
        return +1, plus_index, freq[plus_index]


def propose_range_freq(freq, local_target, optim_config):
    sign, indice, init_freq = find_largest_area(freq, local_target,
                                                optim_config)
    scale = optim_config['elastic']
    #print('Scale={} init_freq {}'.format(scale, init_freq))
    init_freq_min = max(init_freq*scale, 20)
    init_freq_max = min(init_freq/scale, 20000)
    init_freq_range = np.linspace(init_freq_min, init_freq_max,
                                  optim_config['MAX_STEPS_FREQ']).tolist()
    if optim_config['MAX_STEPS_FREQ'] == 1:
        init_freq_range = [init_freq]
    init_freq_range = np.linspace(init_freq_min, init_freq_max,
                                  optim_config['MAX_STEPS_FREQ']).tolist()
    logger.debug('freq min {}Hz peak {}Hz max {}Hz'.format(
        init_freq_min, init_freq, init_freq_max))
    return sign, init_freq, init_freq_range


def propose_range_dbGain(freq, local_target, sign, init_freq, optim_config):
    spline = InterpolatedUnivariateSpline(np.log10(freq), local_target, k=1)
    init_dbGain = abs(spline(np.log10(init_freq)))
    init_dbGain_min = max(init_dbGain/5, optim_config['MIN_DBGAIN'])
    init_dbGain_max = min(init_dbGain*5, optim_config['MAX_DBGAIN'])
    init_dbGain_range = ()
    if sign < 0:
        init_dbGain_range = np.linspace(
            init_dbGain_min, init_dbGain_max,
            optim_config['MAX_STEPS_DBGAIN']).tolist()
    else:
        init_dbGain_range = np.linspace(
            -init_dbGain_max, -init_dbGain_min,
            optim_config['MAX_STEPS_DBGAIN']
            ).tolist()
    logger.debug('gain min {}dB peak {}dB max {}dB'.format(
        init_dbGain_min, init_dbGain, init_dbGain_max))
    return init_dbGain_range


def propose_range_Q(optim_config):
    return np.concatenate(
        (np.linspace(optim_config['MIN_Q'], 1.0, optim_config['MAX_STEPS_Q']),
         np.linspace(1+optim_config['MIN_Q'], optim_config['MAX_Q'],
                     optim_config['MAX_STEPS_Q'])),
        axis=0).tolist()


def propose_range_biquad(optim_config):
    return [Biquad.PEAK]
    # Biquad.NOTCH, Biquad.LOWPASS, Biquad.HIGHPASS,
    # Biquad.BANDPASS, Biquad.LOWSHELF, Biquad.HIGHSHELF
    # ]


def find_best_biquad(freq, auto_target, freq_range, Q_range, dbGain_range,
                     biquad_range, count, optim_config):

    bT = 3

    def opt_peq(x):
        peq = [(1.0, Biquad(bT, x[0], 48000, x[1], x[2]))]
        return flat_loss(freq, auto_target, peq, count)

    bounds = [(freq_range[0], freq_range[-1]),
              (Q_range[0], Q_range[-1]),
              (dbGain_range[0], dbGain_range[-1])]

    logger.debug('range is [{}, {}], [{}, {}], [{}, {}]'.format(
        bounds[0][0], bounds[0][1],
        bounds[1][0], bounds[1][1],
        bounds[2][0], bounds[2][1]))
    # can use differential_evolution basinhoppin dual_annealing
    res = opt.dual_annealing(opt_peq, bounds)
    logger.debug('          optim loss {:2.2f} in {} iter at F {:.0f} Hz Q {:2.2f} dbGain {:2.2f}'.format(
        res.fun, res.nfev, res.x[0], res.x[1], res.x[2]))
    return True, bT, res.x[0], res.x[1], res.x[2], res.fun


# ------------------------------------------------------------------------------
# find next best biquad
# ------------------------------------------------------------------------------

def optim_preflight(freq, target, target_interp, optim_config):
    sz = len(freq)
    nbt = len(target)
    nbi = len(target_interp)

    status = True

    if sz != len(target[0]):
        logger.error('Size mismatch #freq {} != #target {}'.format(
            sz, len(target[0])))
        status = False

    if nbt != nbi:
        logger.error('Size mismatch #target {} != #target_interp {}'.format(
            nbt, nbi))
        status = False

    for i in range(0, len(target)):
        if len(target[i]) != len(target_interp[i]):
            logger.error(
                'Size mismatch #target[{}] {} != #target_interp[{}] {}'.format(
                    i, len(target[i]), i, len(target_interp[i])))
            status = False

    return status


def optim_compute_auto_target(freq, target, target_interp, peq):
    peq_freq = peq_build(freq, peq)
    return [target[i]-target_interp[i]+peq_freq for i in range(0, len(target))]


def optim_greedy(speaker_name, df_speaker, freq, target, target_interp, optim_config):

    if optim_preflight(freq, target, target_interp, optim_config) is False:
        logger.error('Preflight check failed!')
        return None

    auto_peq = []
    auto_target = optim_compute_auto_target(freq, target, target_interp, auto_peq)
    best_loss = flat_loss(freq, auto_target, auto_peq, 0)
    pref_score = score_loss(df_speaker, auto_peq)

    print(
        'OPTIM {} START {} #PEQ {:d} Freq #{:d} Gain #{:d} +/-[{}, {}] Q #{} [{}, {}] Loss {:2.2f} Score {:2.2f}'.format(
            speaker_name,
            optim_config['curve_names'],
            optim_config['MAX_NUMBER_PEQ'], optim_config['MAX_STEPS_FREQ'],
            optim_config['MAX_STEPS_DBGAIN'], optim_config['MIN_DBGAIN'], optim_config['MAX_DBGAIN'],
            optim_config['MAX_STEPS_Q'], optim_config['MIN_Q'], optim_config['MAX_Q'],
            best_loss, pref_score))

    for optim_iter in range(0, optim_config['MAX_NUMBER_PEQ']):

        # we are optimizing above my_freq_reg_min hz on anechoic data
        auto_target = optim_compute_auto_target(freq, target, target_interp, auto_peq)

        # greedy strategy: look for lowest & highest peak
        sign, init_freq, init_freq_range = propose_range_freq(freq, auto_target[0], optim_config)
        init_dbGain_range = propose_range_dbGain(freq, auto_target[0], sign, init_freq, optim_config)
        init_Q_range = propose_range_Q(optim_config)
        biquad_range = propose_range_biquad(optim_config)

        state, current_type, current_freq, current_Q, current_dbGain, \
            current_loss = find_best_biquad(freq,
                                            auto_target, init_freq_range,
                                            init_Q_range, init_dbGain_range,
                                            biquad_range, optim_iter,
                                            optim_config)
        if state:
            biquad = (1.0, Biquad(current_type, current_freq, 48000, current_Q, current_dbGain))
            auto_peq.append(biquad)
            best_loss = current_loss
            pref_score = score_loss(df_speaker, auto_peq)
            print('Iter {:2d} Optim converged loss {:2.2f} pref score {:2.2f} biquad {:1d} F:{:5.0f}Hz Q:{:2.2f} G:{:+2.2f}dB'
                  .format(optim_iter,
                          best_loss,
                          pref_score,
                          current_type,
                          current_freq,
                          current_Q,
                          current_dbGain))
        else:
            logger.error('Skip failed optim for best {:2.2f} current {:2.2f}'
                         .format(best_loss, current_loss))
            break

    print('OPTIM END {}: best loss {:2.2f} with {:2d} PEQs'.format(speaker_name, flat_loss(freq, auto_target, [], 0), len(auto_peq)))
    return auto_peq


def optim_auto_peq(speaker_name, df_speaker, optim_config):
    curves = optim_config['curve_names']
    df, freq, target = getFreq(df_speaker, optim_config)
    target_interp = []
    for curve in curves:
        target_interp.append(getTarget(df, freq, curve, optim_config))
    auto_peq = optim_greedy(speaker_name, df_speaker, freq, target, target_interp, optim_config)
    return auto_peq


@ray.remote
def optim_save_peq(speaker_name, df_speaker, optim_config, verbose, smoke_test):
    """Compute ans save PEQ for this speaker """
    eq_dir = 'datas/eq/{}'.format(speaker_name)
    pathlib.Path(eq_dir).mkdir(parents=True, exist_ok=True)
    eq_name = '{}/iir-autoeq.txt'.format(eq_dir)
    if not force and os.path.exists(eq_name):
        if verbose:
            print('eq {} already exist!'.format(eq_name))
        return 0

    # extract current speaker
    _, _, score = scores_apply_filter(df_speaker, [])

    # compute an optimal PEQ
    auto_peq = optim_auto_peq(speaker_name, df_speaker, optim_config)

    # do we have a manual peq?
    score_manual = {}
    if verbose:
        manual_peq_name = './datas/eq/{}/iir.txt'.format(speaker_name)
        manual_peq = parse_eq_iir_rews(manual_peq_name, optim_config['fs'])
        _, _, score_manual = scores_apply_filter(df_speaker, manual_peq)

    # compute new score with this PEQ
    spin_auto, pir_auto, score_auto = scores_apply_filter(df_speaker, auto_peq)

    # print peq
    comments = ['EQ for {:s} computed from ASR data'.format(speaker_name),
                'Preference Score {:2.1f} with EQ {:2.1f}'.format(
                    score['pref_score'],
                    score_auto['pref_score']),
                'Generated from http://github.com/pierreaubert/spinorama',
                'Date {}'.format(datetime.today().strftime('%Y-%m-%d-%H:%M:%S')),
                '',
    ]
    eq_apo = peq_format_apo('\n'.join(comments), auto_peq)
    if verbose:
        print('{:30s} ---------------------------------------'.format(speaker_name))
        print(peq_format_apo('\n'.join(comments), auto_peq))
        print('----------------------------------------------------------------------')
    if not smoke_test:
        with open(eq_name, 'w') as fd:
            fd.write(eq_apo)

    # print scores
    if verbose:
        print('{:30s} ---------------------------------------'.format(speaker_name))
        scores_print2(score, score_manual, score_auto)
        print('----------------------------------------------------------------------')

    return 0


def queue_speakers(df_all_speakers, optim_config, verbose, smoke_test):
    ray_ids = {}
    for speaker_name in df_all_speakers.keys():
        if 'ASR' not in df_all_speakers[speaker_name].keys():
            # currently doing only ASR but should work for the others
            # Princeton start around 500hz
            continue
        default = 'asr'
        if speaker_name in metadata.keys() and 'default_measurement' in metadata[speaker_name].keys():
            default = metadata[speaker_name]['default_measurement']
        if default not in df_all_speakers[speaker_name]['ASR'].keys():
            logger.error('no {} for {}'.format(default, speaker_name))
            continue
        df_speaker = df_all_speakers[speaker_name]['ASR'][default]
        if 'SPL Horizontal_unmelted' not in df_speaker.keys() or 'SPL Vertical_unmelted' not in df_speaker.keys():
            logger.error('no Horizontal or Vertical measurement for {}'.format(speaker_name))
            continue
            
        id = optim_save_peq.remote(speaker_name, df_speaker, optim_config, verbose, smoke_test)
        ray_ids[speaker_name] = id

    print('Queing {} speakers for EQ computations'.format(len(ray_ids)))
    return ray_ids


def compute_peqs(ray_ids):
    done_ids = set()
    while 1:
        ids = [id for id in ray_ids.values() if id not in done_ids]
        num_returns = min(len(ids), 16)
        ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)

        if len(remaining_ids) == 0:
            break

        for id in ready_ids:
            ray.get(id)
            done_ids.add(id)

        logger.info('State: {0} ready IDs {1} remainings IDs '.format(len(ready_ids), len(remaining_ids)))
    return 0


if __name__ == '__main__':
    args = docopt(__doc__, version='generate_peqs.py version 0.1',
                  options_first=True)

    force = args['--force']
    verbose = args['--verbose']
    ptype = None
    smoke_test = args['--smoke-test']

    level = None
    if args['--log-level'] is not None:
        check_level = args['--log-level']
        if check_level in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
            level = check_level

    logger = logging.getLogger('spinorama')
    fh = logging.FileHandler('debug_optim.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # sh = logging.StreamHandler(sys.stdout)
    # sh.setFormatter(formatter)
    logger.addHandler(fh)
    # logger.addHandler(sh)
    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(logging.INFO)

    def setup_logger(worker):
        logger = logging.getLogger('spinorama')
        if level is not None:
            logger.setLevel(level)

    # read optimisation parameter
    optim_config = {
        # name of the loss function
        'loss': 'flat_loss',
        # lookup around a value is [value*elastic, value/elastic]
        'elastic': 0.8,
        # cut frequency
        'fs': 48000,
        # optimise the curve above the Schroeder frequency (here default is
        # 300hz)
        'freq_reg_min': 300,
        # if an algorithm use a mean of frequency to find a reference level
        # compute it over [min, max]hz
        'freq_mean_min': 100,
        'freq_mean_max': 300,
        # optimisation is on both curves
        # depending on the algorithm it is not doing the same things
        # for example: with flat_loss (the default)
        # it will optimise for having a Listening Window as close as possible
        # the target and having a Sound Power as flat as possible (without a
        # target)
        'curve_names': ['Listening Window', 'Sound Power'],
    }

    # define other parameters for the optimisation algorithms
    # MAX_STEPS_XXX are usefull for grid search when the algorithm is looking
    # for random values (or trying all) across a range
    if smoke_test:
        optim_config['MAX_NUMBER_PEQ'] = 3
        optim_config['MAX_STEPS_FREQ'] = 3
        optim_config['MAX_STEPS_DBGAIN'] = 3
        optim_config['MAX_STEPS_Q'] = 3
    else:
        optim_config['MAX_NUMBER_PEQ'] = 20
        optim_config['MAX_STEPS_FREQ'] = 5
        optim_config['MAX_STEPS_DBGAIN'] = 5
        optim_config['MAX_STEPS_Q'] = 5

    # MIN or MAX_Q or MIN or MAX_DBGAIN control the shape of the biquad which
    # are admissible.
    optim_config['MIN_DBGAIN'] = 0.5
    optim_config['MAX_DBGAIN'] = 12
    optim_config['MIN_Q'] = 0.5
    optim_config['MAX_Q'] = 12

    # load data
    df_all_speakers = {}
    if smoke_test is True:
        df_all_speakers = fl.load('./cache.smoketest_speakers.h5')
    else:
        df_all_speakers = fl.load('./cache.parse_all_speakers.h5')

    # name of speaker
    speaker_name = None
    if args['--speaker'] is not None:
        speaker_name = args['--speaker']

    # ray section
    ray.worker.global_worker.run_function_on_all_workers(setup_logger)
    # address is the one from the ray server<
    # ray.init(address='{}:{}'.format(ip, port))
    ray.init()

    # select all speakers
    if speaker_name is None:
        ids = queue_speakers(df_all_speakers, optim_config, verbose, smoke_test)
        compute_peqs(ids)
    else:
        if speaker_name not in df_all_speakers.keys():
            logger.error('{} is not known!'.format(speaker_name))
            sys.exit(1)
        if 'ASR' not in df_all_speakers[speaker_name].keys():
            sys,exit(0)
        default = 'asr'
        if speaker_name in metadata.keys() and 'default_measurement'in metadata[speaker_name].keys():
            default = metadata[speaker_name]['default_measurement']
        df_speaker = df_all_speakers[speaker_name]['ASR'][default]
        id = optim_save_peq.remote(speaker_name, df_speaker, optim_config, verbose, smoke_test)
        while 1:
            ready_ids, remaining_ids = ray.wait([id], num_returns=1)
            if len(ready_ids) == 1:
                ray.get(ready_ids[0])
                break
            if len(remaining_ids) == 0:
                break
        
    sys.exit(0)
