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
usage: generate_peqs.py [--help] [--version] [--log-level=<level>] [--force] [--smoke-test] [-v|--verbose] [--origin=<origin>] [--speaker=<speaker>] [--mversion=<mversion>] [--max-peq=<count>] [--min-Q=<minQ>] [--max-Q=<maxQ>] [--min-dB=<mindB>] [--max-dB=<maxdB>]  [--min-freq=<minFreq>] [--max-freq=<maxFreq>][--max-iter=<maxiter>] [--only-biquad-peak] [--curve-peak-only] [--loss=<pick>]

Options:
  --help                   Display usage()
  --version                Script version number
  --force                  Force generation of eq even if already computed
  --verbose                Print some informations
  --smoke-test             Test the optimiser with a small amount of variables
  --log-level=<level>      Default is WARNING, options are DEBUG or INFO or ERROR.
  --origin=<origin>        Restrict to a specific origin
  --speaker=<speaker>      Restrict to a specific speaker, if not specified it will optimise all speakers
  --mversion=<mversion>    Restrict to a specific mversion (for a given origin you can have multiple measurements)
  --max-peq=<count>        Maximum allowed number of Biquad
  --min-Q=<minQ>           Minumum value for Q
  --max-Q=<maxQ>           Maximum value for Q
  --min-dB=<mindB>         Minumum value for dBGain
  --max-dB=<maxdB>         Maximum value for dBGain
  --min-freq=<minFreq>     Optimisation will happen above min freq
  --max-freq=<maxFreq>     Optimisation will happen below max freq
  --max-iter=<maxiter>     Maximum number of iterations
  --only-biquad-peak       PEQ can only be of type Peak aka PK
  --curve-peak-only        Optimise both for peaks and valleys on a curve
"""
from datetime import datetime
import logging
import math
import os
import pathlib
import sys
from typing import Literal, List, Tuple

import altair as alt
from altair_saver import save
from docopt import docopt
import flammkuchen as fl
import numpy as np
import pandas as pd
import ray
import scipy.signal as sig
from scipy.stats import linregress
import scipy.optimize as opt
from scipy.interpolate import InterpolatedUnivariateSpline

from datas.metadata import speakers_info as metadata
from spinorama.ltype import Vector, Peq
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import peq_build  # peq_print
from spinorama.load import graph_melt
from spinorama.load_rewseq import parse_eq_iir_rews
from spinorama.filter_peq import peq_format_apo
from spinorama.filter_scores import scores_apply_filter, scores_print2
from spinorama.graph import graph_spinorama, graph_freq, graph_regression_graph, graph_regression


VERSION=0.4
logger = logging.getLogger('spinorama')

# ------------------------------------------------------------------------------
# various loss function
# ------------------------------------------------------------------------------


def l2_loss(local_target: Vector, freq: Vector, peq: Peq) -> float:
    # L2 norm
    return np.linalg.norm(local_target+peq_build(freq, peq), 2)


def leastsquare_loss(freq, local_target, peq, iterations: int) -> float:
    # sum of L2 norms if we have multiple targets
    return np.sum([l2_loss(local_target[i], freq, peq) for i in range(0, len(local_target))])


def flat_loss(freq, local_target, peq, iterations, weigths):
    # make LW as close as target as possible and SP flat
    lw = np.sum([l2_loss(local_target[i], freq, peq) for i in range(0, len(local_target)-1)])
    # want sound power to be flat but not necessary aligned
    # with a target
    _, _, r_value, _, _ = linregress(np.log10(freq), local_target[-1])
    sp = 1-r_value**2
    # * or + 
    #return weigths[0]*lw+weigths[1]*sp
    return lw*sp


def swap_loss(freq, local_target, peq, iteration):
    # try to alternate, optimise for 1 objective then the second one
    if len(local_target) == 0 or iteration < 10:
        return l2_loss([local_target[0]], freq, peq)
    else:
        return l2_loss([local_target[1]], freq, peq)


def alternate_loss(freq, local_target, peq, iteration):
    # optimise for 2 objectives 1 each time
    if len(local_target) == 0 or iteration % 2 == 0:
        return l2_loss([local_target[0]], freq, peq)
    else:
        return l2_loss([local_target[1]], freq, peq)


def score_loss(df_spin, peq):
    """Compute the preference score for speaker
    local_target: unsued
    peq: evaluated peq
    return minus score (we want to maximise the score)
    """
    _, _, score = scores_apply_filter(df_spin, peq)
    return -score['pref_score']


def loss(freq, local_target, peq, iterations, optim_config):
    which_loss = optim_config['loss']
    if which_loss == 'flat_loss':
        weigths = optim_config['loss_weigths']
        return flat_loss(freq, local_target, peq, iterations, weigths)
    elif which_loss == 'leastsquare_loss':
        return leastsquare_loss(freq, local_target, peq, iterations)
    elif which_loss == 'alternate_loss':
        return alternate_loss(freq, local_target, peq, iterations)
    else:
        logger.error('loss function is unkown')
    
    

# ------------------------------------------------------------------------------
# compute freq and targets
# ------------------------------------------------------------------------------

def getSelector(df, optim_config):
    return ((df['Freq'] > optim_config['freq_reg_min']) & (df['Freq'] < optim_config['freq_reg_max']))


def getFreq(df_speaker_data, optim_config):
    """extract freq and one curve"""
    curves = optim_config['curve_names']
    # extract LW
    columns = {'Freq'}.union(curves)
    local_df = df_speaker_data['CEA2034_unmelted'].loc[:, columns]
    # selector
    selector = getSelector(local_df, optim_config)
    # freq
    local_freq = local_df.loc[selector, 'Freq'].values
    local_target = []
    for curve in curves:
        local_target.append(local_df.loc[selector, curve].values)
    return local_df, local_freq, local_target


def getTarget(df_speaker_data, freq, current_curve_name, optim_config):
    # freq
    selector = getSelector(df_speaker_data, optim_config)
    current_curve = df_speaker_data.loc[selector, current_curve_name].values
    # compute linear reg on lw
    slope, intercept, r_value, p_value, std_err = linregress(np.log10(freq), current_curve)
    # normalise to have a flat target (primarly for bright speakers)
    if current_curve_name == 'On Axis':
        slope = 0
    elif current_curve_name == 'Listening Window':
        # slighlithy downward
        slope = -2
    elif current_curve_name == 'Early Reflections':
        slope = -5
    elif current_curve_name == 'Sound Power':
        slope = -8
    else:
        logger.error('No match for getTarget')
        return None
    slope *= math.log10(freq[0])/math.log10(freq[-1])
    intercept = current_curve[0]-slope
    line= [slope*math.log10(freq[i])+intercept for i in range(0, len(freq))]
    logger.debug('Slope {} Intercept {} R {} P {} err {}'.format(slope, intercept, r_value, p_value, std_err))
    logger.debug('Target_interp from {:.1f}dB at {}Hz to {:.1f}dB at {}Hz'.format(line[0], freq[0], line[-1], freq[-1]))
    return line

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
        found_widths = sig.peak_widths(positive_curve, found_peaks, rel_height=0.1)[0]
        #print('computed width at {}'.format(found_widths))
        areas = [(i, positive_curve[found_peaks[i]]*found_widths[i]) for i in range(0, len(found_peaks))]
        #print('areas {}'.format(areas))
        sorted_areas = sorted(areas, key=lambda a: -a[1])
        #print('sorted {}'.format(sorted_areas))
        ipeaks, area = sorted_areas[0]
        return found_peaks[ipeaks], area

    plus_curve = np.clip(curve, a_min=0, a_max=None)
    plus_index, plus_areas = largest_area(plus_curve)

    minus_index, minus_areas = None, None
    if optim_config['plus_and_minus'] is True:
        minus_curve = -np.clip(curve, a_min=None, a_max=0)
        minus_index, minus_areas = largest_area(minus_curve)

    if minus_areas is None and plus_areas is None:
        logger.error('No initial freq found')
        return +1, None, None

    if plus_areas is None:
        return -1, minus_index, freq[minus_index]

    if minus_areas is None:
        return +1, plus_index, freq[plus_index]

    if minus_areas > plus_areas:
        return -1, minus_index, freq[minus_index]
    else:
        return +1, plus_index, freq[plus_index]


def propose_range_freq(freq, local_target, optim_config):
    sign, indice, init_freq = find_largest_area(freq, local_target, optim_config)
    scale = optim_config['elastic']
    #print('Scale={} init_freq {}'.format(scale, init_freq))
    init_freq_min = max(init_freq*scale, optim_config['freq_reg_min'])
    init_freq_max = min(init_freq/scale, optim_config['freq_reg_max'])
    logger.debug('freq min {}Hz peak {}Hz max {}Hz'.format(init_freq_min, init_freq, init_freq_max))
    if optim_config['MAX_STEPS_FREQ'] == 1:
        return sign, init_freq, [init_freq]
    else:
        return sign, init_freq, np.linspace(init_freq_min, init_freq_max, optim_config['MAX_STEPS_FREQ']).tolist()


def propose_range_dbGain(freq: Vector, local_target: List[Vector], sign: Literal[-1, 1], init_freq: Vector, optim_config: dict) -> Vector:
    spline = InterpolatedUnivariateSpline(np.log10(freq), local_target, k=1)
    scale = optim_config['elastic']
    init_dbGain = abs(spline(np.log10(init_freq)))
    init_dbGain_min = max(init_dbGain*scale, optim_config['MIN_DBGAIN'])
    init_dbGain_max = min(init_dbGain/scale, optim_config['MAX_DBGAIN'])
    logger.debug('gain min {}dB peak {}dB max {}dB'.format(init_dbGain_min, init_dbGain, init_dbGain_max))

    if sign < 0:
        return np.linspace(init_dbGain_min, init_dbGain_max, optim_config['MAX_STEPS_DBGAIN']).tolist()
    else:
        return np.linspace(-init_dbGain_max, -init_dbGain_min, optim_config['MAX_STEPS_DBGAIN']).tolist()


def propose_range_Q(optim_config):
    return np.concatenate((np.linspace(optim_config['MIN_Q'], 1.0, optim_config['MAX_STEPS_Q']),
                           np.linspace(1+optim_config['MIN_Q'], optim_config['MAX_Q'], optim_config['MAX_STEPS_Q'])),
                          axis=0).tolist()


def propose_range_biquad(optim_config):
    return [
        0, # Biquad.lowpass
        1, # Biquad.highpass
        2, # Biquad.bandpass
        3, # Biquad.peak
        4, # Biquad.notch
        5, # Biquad.lowshelf
        6, # Biquad.highshelf
    ]


def find_best_biquad(
        freq, auto_target, freq_range, Q_range, dbGain_range,
        biquad_range, count, optim_config):

    def opt_peq(x):
        peq = [(1.0, Biquad(int(x[0]), x[1], 48000, x[2], x[3]))]
        return loss(freq, auto_target, peq, count, optim_config)

    bounds = [
        (biquad_range[0], biquad_range[-1]),
        (freq_range[0], freq_range[-1]),
        (Q_range[0], Q_range[-1]),
        (dbGain_range[0], dbGain_range[-1]),
    ]

    logger.debug('range is [{}, {}], [{}, {}], [{}, {}], [{}, {}]'.format(
        bounds[0][0], bounds[0][1],
        bounds[1][0], bounds[1][1],
        bounds[2][0], bounds[2][1],
        bounds[3][0], bounds[3][1],
    ))
    # can use differential_evolution basinhoppin dual_annealing
    res = opt.dual_annealing(opt_peq, bounds,
                             maxiter=optim_config['maxiter'],
                             #initial_temp=10000
    )
    logger.debug('          optim loss {:2.2f} in {} iter type {:d} at F {:.0f} Hz Q {:2.2f} dbGain {:2.2f} {}'.format(
        res.fun, res.nfev, int(res.x[0]), res.x[1], res.x[2], res.x[3], res.message))
    return res.success, int(res.x[0]), res.x[1], res.x[2], res.x[3], res.fun, res.nit


def find_best_peak(freq, auto_target, freq_range, Q_range, dbGain_range,
                   biquad_range, count, optim_config):

    biquad_type = 3

    def opt_peq(x):
        peq = [(1.0, Biquad(biquad_type, x[0], 48000, x[1], x[2]))]
        return loss(freq, auto_target, peq, count, optim_config)

    bounds = [
        (freq_range[0], freq_range[-1]),
        (Q_range[0], Q_range[-1]),
        (dbGain_range[0], dbGain_range[-1]),
    ]

    logger.debug('range is [{}, {}], [{}, {}], [{}, {}]'.format(
        bounds[0][0], bounds[0][1],
        bounds[1][0], bounds[1][1],
        bounds[2][0], bounds[2][1],
    ))
    # can use differential_evolution basinhoppin dual_annealing
    res = opt.dual_annealing(opt_peq, bounds,
                             maxiter=optim_config['maxiter'],
                             initial_temp=10000
    )
    logger.debug('          optim loss {:2.2f} in {} iter type PK at F {:.0f} Hz Q {:2.2f} dbGain {:2.2f} {}'.format(
        res.fun, res.nfev, res.x[0], res.x[1], res.x[2], res.message))
    return res.success, biquad_type, res.x[0], res.x[1], res.x[2], res.fun, res.nit


# ------------------------------------------------------------------------------
# find next best biquad
# ------------------------------------------------------------------------------

def optim_preflight(freq, target, auto_target_interp, optim_config):
    sz = len(freq)
    nbt = len(target)
    nbi = len(auto_target_interp)

    status = True

    if sz != len(target[0]):
        logger.error('Size mismatch #freq {} != #target {}'.format(
            sz, len(target[0])))
        status = False

    if nbt != nbi:
        logger.error('Size mismatch #target {} != #auto_target_interp {}'.format(
            nbt, nbi))
        status = False

    for i in range(0, len(target)):
        if len(target[i]) != len(auto_target_interp[i]):
            logger.error(
                'Size mismatch #target[{}] {} != #auto_target_interp[{}] {}'.format(
                    i, len(target[i]), i, len(auto_target_interp[i])))
            status = False

    return status


def optim_compute_auto_target(freq, target, auto_target_interp, peq):
    peq_freq = peq_build(freq, peq)
    return [target[i]-auto_target_interp[i]+peq_freq for i in range(0, len(target))]


def graph_eq(freq, peq, domain, title):
    df_eq = pd.DataFrame({'Freq': freq})
    for i, (pos, eq) in enumerate(peq):
        df_eq['EQ {}'.format(i)] = peq_build(freq, [(pos, eq)])
    
    g_eq = alt.Chart(
        graph_melt(df_eq)
    ).mark_line().encode(
        alt.X('Freq:Q', title='Freq (Hz)', scale=alt.Scale(type='log', nice=False, domain=domain)),
        alt.Y('dB:Q', title='Sound Pressure (dB)', scale=alt.Scale(zero=False, domain=[-12,12 ])),
        alt.Color('Measurements', type='nominal', sort=None),
    ).properties(
        width=800,
        height=400,
        title='{} EQ'.format(title)
    )
    return g_eq
    

def graph_eq_compare(freq, manual_peq, auto_peq, domain, speaker_name):
    return alt.Chart(
        graph_melt(
            pd.DataFrame({
                'Freq': freq,
                'Manual': peq_build(freq, manual_peq),
                'Auto': peq_build(freq, auto_peq),
            }))
    ).mark_line().encode(
        alt.X('Freq:Q', title='Freq (Hz)', scale=alt.Scale(type='log', nice=False, domain=domain)),
        alt.Y('dB:Q', title='Sound Pressure (dB)', scale=alt.Scale(zero=False, domain=[-5,5 ])),
        alt.Color('Measurements', type='nominal', sort=None),
    ).properties(
        width=800,
        height=400,
        title='{} manual and auto filter'.format(speaker_name)
    )


def graph_results(speaker_name, freq,
                  manual_peq, auto_peq,
                  auto_target, auto_target_interp,
                  manual_target, manual_target_interp,
                  spin, spin_manual, spin_auto,
                  pir, pir_manual, pir_auto,
                  optim_config):

    # what's the min over freq?
    reg_min = optim_config['freq_reg_min']
    reg_max = optim_config['freq_reg_max']
    domain = [reg_min, reg_max]
    # build a graph for each peq
    g_manual_eq = graph_eq(freq, manual_peq, domain, '{} manual'.format(speaker_name))
    g_auto_eq = graph_eq(freq, auto_peq, domain,  '{} auto'.format(speaker_name))

    # compare the 2 eqs
    g_eq_full = graph_eq_compare(freq, manual_peq, auto_peq, domain, speaker_name)

    # compare the 2 corrected curves
    df_optim = pd.DataFrame({'Freq': freq})
    df_optim['Auto'] = auto_target[0]-auto_target_interp[0]+peq_build(freq, auto_peq)
    if manual_target is not None:
        df_optim['Manual'] = manual_target[0]-manual_target_interp[0]+peq_build(freq, manual_peq)
    g_optim = alt.Chart(graph_melt(df_optim)
    ).mark_line().encode(
        alt.X('Freq:Q', title='Freq (Hz)', scale=alt.Scale(type='log', nice=False, domain=domain)),
        alt.Y('dB:Q', title='Sound Pressure (dB)', scale=alt.Scale(zero=False, domain=[-5,5 ])),
        alt.Color('Measurements', type='nominal', sort=None),
    ).properties(
        width=800,
        height=400,
        title='{} manual and auto corrected {}'.format(speaker_name, optim_config['curve_names'][0])
    )

    # show the 3 spinoramas
    g_params = {'xmin': 20, 'xmax': 20000, 'ymin': -40, 'ymax': 10, 'width': 400, 'height': 250}
    g_params['width'] = 800
    g_params['height'] = 400
    g_spin_asr = graph_spinorama(spin, g_params).properties(title='{} from ASR'.format(speaker_name)) 
    g_spin_manual = graph_spinorama(spin_manual, g_params).properties(title='{} ASR + manual EQ'.format(speaker_name)) 
    g_spin_auto = graph_spinorama(spin_auto, g_params).properties(title='{} ASR + auto EQ'.format(speaker_name))

    # show the 3 optimised curves
    # which_curve='Listening Window
    # which_curve='Sound Power'
    which_curve='Estimated In-Room Response'
    data = spin
    data_manual = spin_manual
    data_auto = spin_auto
    if which_curve == 'Estimated In-Room Response':
        data = pir
        data_manual = pir_manual
        data_auto = pir_auto
    g_pir_reg = graph_regression(data_auto.loc[(data_auto.Measurements==which_curve)], 100, reg_max)
    g_pir_asr = (graph_freq(data.loc[(data.Measurements==which_curve)], g_params)+g_pir_reg).properties(
        title='{} from ASR [{}]'.format(speaker_name, which_curve))
    g_pir_manual = (graph_freq(data_manual.loc[(data_manual.Measurements==which_curve)], g_params)+g_pir_reg).properties(
        title='{} from ASR [{}] + manual EQ'.format(speaker_name, which_curve))
    g_pir_auto = (graph_freq(data_auto.loc[(data_auto.Measurements==which_curve)], g_params)+g_pir_reg).properties(
        title='{} from ASR [{}] + auto EQ'.format(speaker_name, which_curve))
    
    # add all graphs and print it
    graphs = (\
              ((g_manual_eq | g_auto_eq) & (g_eq_full | g_optim)) & \
              ( g_spin_asr | g_spin_manual | g_spin_auto) & \
              ( g_pir_asr | g_pir_manual | g_pir_auto) \
    ).resolve_scale('independent')
    return graphs
    

def optim_greedy(speaker_name, df_speaker, freq, auto_target, auto_target_interp, optim_config):

    if optim_preflight(freq, auto_target, auto_target_interp, optim_config) is False:
        logger.error('Preflight check failed!')
        return None

    auto_peq = []
    current_auto_target = optim_compute_auto_target(freq, auto_target, auto_target_interp, auto_peq)
    best_loss = loss(freq, auto_target, auto_peq, 0, optim_config)
    pref_score = score_loss(df_speaker, auto_peq)

    results = [(0, best_loss, -pref_score)]
    logger.info('OPTIM {} START {} #PEQ {:d} Freq #{:d} Gain #{:d} +/-[{}, {}] Q #{} [{}, {}] Loss {:2.2f} Score {:2.2f}'.format(
        speaker_name,
        optim_config['curve_names'],
        optim_config['MAX_NUMBER_PEQ'], optim_config['MAX_STEPS_FREQ'],
        optim_config['MAX_STEPS_DBGAIN'], optim_config['MIN_DBGAIN'], optim_config['MAX_DBGAIN'],
        optim_config['MAX_STEPS_Q'], optim_config['MIN_Q'], optim_config['MAX_Q'],
        best_loss, -pref_score))

    for optim_iter in range(0, optim_config['MAX_NUMBER_PEQ']):

        # we are optimizing above my_freq_reg_min hz on anechoic data
        current_auto_target = optim_compute_auto_target(freq, auto_target, auto_target_interp, auto_peq)

        # greedy strategy: look for lowest & highest peak
        sign, init_freq, init_freq_range = propose_range_freq(freq, current_auto_target[0], optim_config)
        init_dbGain_range = propose_range_dbGain(freq, current_auto_target[0], sign, init_freq, optim_config)
        init_Q_range = propose_range_Q(optim_config)
        biquad_range = propose_range_biquad(optim_config)

        state, current_type, current_freq, current_Q, current_dbGain, current_loss, current_nit = False, -1, -1, -1, -1, -1, -1
        if optim_config['full_biquad_optim'] is True:
            state, current_type, current_freq, current_Q, current_dbGain, current_loss, current_nit = find_best_biquad(
                freq, current_auto_target, init_freq_range, init_Q_range, init_dbGain_range, biquad_range, optim_iter, optim_config)
        else:
            state, current_type, current_freq, current_Q, current_dbGain, current_loss, current_nit = find_best_peak(
                freq, current_auto_target, init_freq_range, init_Q_range, init_dbGain_range, biquad_range, optim_iter, optim_config)
        if state:
            biquad = (1.0, Biquad(current_type, current_freq, 48000, current_Q, current_dbGain))
            auto_peq.append(biquad)
            best_loss = current_loss
            pref_score = score_loss(df_speaker, auto_peq)
            results.append((optim_iter+1, best_loss, -pref_score))
            logger.info('Iter {:2d} Optim converged loss {:2.2f} pref score {:2.2f} biquad {:2s} F:{:5.0f}Hz Q:{:2.2f} G:{:+2.2f}dB in {} iterations'
                  .format(optim_iter,
                          best_loss,
                          -pref_score,
                          biquad[1].type2str(),
                          current_freq,
                          current_Q,
                          current_dbGain,
                          current_nit))
        else:
            logger.error('Skip failed optim for best {:2.2f} current {:2.2f}'
                         .format(best_loss, current_loss))
            break

    # recompute auto_target with the full auto_peq
    current_auto_target = optim_compute_auto_target(freq, auto_target, auto_target_interp, auto_peq)
    final_loss = loss(freq, current_auto_target, [], 0, optim_config)
    final_score = score_loss(df_speaker, auto_peq)
    results.append((optim_config['MAX_NUMBER_PEQ']+1, best_loss, -pref_score))
    logger.info('OPTIM END {}: best loss {:2.2f} final score {:2.2f} with {:2d} PEQs'.format(
        speaker_name,
        final_loss,
        -final_score,
        len(auto_peq)))
    return results, auto_peq


@ray.remote
def optim_save_peq(speaker_name, df_speaker, df_speaker_eq, optim_config, verbose, smoke_test):
    """Compute ans save PEQ for this speaker """
    eq_dir = 'datas/eq/{}'.format(speaker_name)
    pathlib.Path(eq_dir).mkdir(parents=True, exist_ok=True)
    eq_name = '{}/iir-autoeq.txt'.format(eq_dir)
    if not force and os.path.exists(eq_name):
        if verbose:
            logger.info('eq {} already exist!'.format(eq_name))
        return None, None

    # extract current speaker
    _, _, score = scores_apply_filter(df_speaker, [])

    # compute an optimal PEQ
    curves = optim_config['curve_names']
    df, freq, auto_target = getFreq(df_speaker, optim_config)
    auto_target_interp = []
    for curve in curves:
        auto_target_interp.append(getTarget(df, freq, curve, optim_config))
    auto_results, auto_peq = optim_greedy(speaker_name, df_speaker, freq, auto_target, auto_target_interp, optim_config)

    # do we have a manual peq?
    score_manual = {}
    manual_peq = []
    manual_target = None
    manual_target_interp = None
    if verbose:
        manual_peq_name = './datas/eq/{}/iir.txt'.format(speaker_name)
        manual_peq = parse_eq_iir_rews(manual_peq_name, optim_config['fs'])
        manual_spin, manual_pir, score_manual = scores_apply_filter(df_speaker, manual_peq)
        if df_speaker_eq is not None:
            manual_df, manual_freq, manual_target = getFreq(df_speaker_eq, optim_config)
            manual_target_interp = []
            for curve in curves:
                manual_target_interp.append(getTarget(manual_df, manual_freq, curve, optim_config))

    # compute new score with this PEQ
    spin_auto, pir_auto, score_auto = scores_apply_filter(df_speaker, auto_peq)

    # print peq
    comments = ['EQ for {:s} computed from ASR data'.format(speaker_name),
                'Preference Score {:2.1f} with EQ {:2.1f}'.format(
                    score['pref_score'],
                    score_auto['pref_score']),
                'Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v{}'.format(VERSION),
                'Dated: {}'.format(datetime.today().strftime('%Y-%m-%d-%H:%M:%S')),
                '',
    ]
    eq_apo = peq_format_apo('\n'.join(comments), auto_peq)
    
    # print eq
    if not smoke_test:
        with open(eq_name, 'w') as fd:
            fd.write(eq_apo)
            iir_txt = 'iir.txt'
            iir_name = '{}/{}'.format(eq_dir, iir_txt)
            if not os.path.exists(iir_name):
                try:
                    os.symlink(eq_name, iir_txt)
                except OSError:
                    pass

    # print results
    if len(manual_peq) > 0 and len(auto_peq) > 0:
        graphs = graph_results(
            speaker_name, freq,  manual_peq, auto_peq,
            auto_target, auto_target_interp,
            manual_target, manual_target_interp,
            df_speaker['CEA2034'], manual_spin, spin_auto,
            df_speaker['Estimated In-Room Response'], manual_pir, pir_auto,
            optim_config)
        graphs_filename = 'docs/{}/ASR/filters'.format(speaker_name)
        if smoke_test:
            graphs_filename += '_smoketest'
        graphs_filename += '.png'
        graphs.save(graphs_filename)

    # print a compact table of results
    if verbose:
        print('{:30s} ---------------------------------------'.format(speaker_name))
        print(peq_format_apo('\n'.join(comments), auto_peq))
        print('----------------------------------------------------------------------')
        print('ITER  LOSS SCORE -----------------------------------------------------')
        print('\n'.join(['  {:2d} {:+2.2f} {:+2.2f}'.format(r[0], r[1], r[2]) for r in auto_results]))
        print('----------------------------------------------------------------------')
        print('{:30s} ---------------------------------------'.format(speaker_name))
        scores_print2(score, score_manual, score_auto)
        print('----------------------------------------------------------------------')

        
    return speaker_name, auto_results


def queue_speakers(df_all_speakers, optim_config, verbose, smoke_test):
    ray_ids = {}
    for speaker_name in df_all_speakers.keys():
        if 'ASR' not in df_all_speakers[speaker_name].keys():
            # currently doing only ASR but should work for the others
            # Princeton start around 500hz
            continue
        default = 'asr'
        default_eq = 'asr_eq'
        if speaker_name in metadata.keys() and 'default_measurement' in metadata[speaker_name].keys():
            default = metadata[speaker_name]['default_measurement']
            default_eq = '{}_eq'.format(default)
        if default not in df_all_speakers[speaker_name]['ASR'].keys():
            logger.error('no {} for {}'.format(default, speaker_name))
            continue
        df_speaker = df_all_speakers[speaker_name]['ASR'][default]
        if 'SPL Horizontal_unmelted' not in df_speaker.keys() or 'SPL Vertical_unmelted' not in df_speaker.keys():
            logger.error('no Horizontal or Vertical measurement for {}'.format(speaker_name))
            continue
        df_speaker_eq = None
        if default_eq in df_all_speakers[speaker_name]['ASR'].keys():
            df_speaker_eq = df_all_speakers[speaker_name]['ASR'][default_eq]
            
        id = optim_save_peq.remote(speaker_name, df_speaker, df_speaker_eq, optim_config, verbose, smoke_test)
        ray_ids[speaker_name] = id

    print('Queing {} speakers for EQ computations'.format(len(ray_ids)))
    return ray_ids


def compute_peqs(ray_ids):
    done_ids = set()
    aggregated_results = {}
    while 1:
        ids = [id for id in ray_ids.values() if id not in done_ids]
        num_returns = min(len(ids), 16)
        ready_ids, remaining_ids = ray.wait(ids, num_returns=num_returns)

        for id in ready_ids:
            speaker_name, results = ray.get(id)
            if results is not None:
                aggregated_results[speaker_name] = results
            done_ids.add(id)

        if len(remaining_ids) == 0:
            break

        logger.info('State: {0} ready IDs {1} remainings IDs '.format(len(ready_ids), len(remaining_ids)))

    v_sn = []
    v_iter = []
    v_loss = []
    v_score = []
    for speaker, results in aggregated_results.items():
        for r in results:
            v_sn.append('{}'.format(speaker))
            v_iter.append(r[0])
            v_loss.append(r[1])
            v_score.append(r[2])
    df_results = pd.DataFrame({'speaker_name': v_sn, 'iter': v_iter, 'loss': v_loss, 'score': v_score})
    df_results.to_csv('results.csv', index=False)
    return 0


if __name__ == '__main__':
    args = docopt(__doc__,
                  version='generate_peqs.py version {}'.format(VERSION),
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

    fh = logging.FileHandler('debug_optim.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    #sh = logging.StreamHandler(sys.stdout)
    #sh.setFormatter(formatter)
    logger.addHandler(fh)
    #logger.addHandler(sh)
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
        # if you have multiple loss functions, define the weigth for each
        'loss_weigths': [1.0, 1.0],
        # do you optimise only peaks or both peaks and valleys?
        'plus_and_minus': True,
        # do you optimise for all kind of biquad or do you want only Peaks?
        'full_biquad_optim': True,
        # lookup around a value is [value*elastic, value/elastic]
        'elastic': 0.8,
        # cut frequency
        'fs': 48000,
        # optimise the curve above the Schroeder frequency (here default is
        # 300hz)
        'freq_reg_min': 300,
        # do not try to optimise above:
        'freq_reg_max': 16000,
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
        # 'curve_names': ['Listening Window', 'Sound Power'],
        'curve_names': ['Listening Window', 'Early Reflections'],
        # 'curve_names': ['Listening Window', 'On Axis', 'Early Reflections'],
        # 'curve_names': ['On Axis', 'Early Reflections'],
        # 'curve_names': ['Early Reflections', 'Sound Power'],
    }

    # define other parameters for the optimisation algorithms
    # MAX_STEPS_XXX are usefull for grid search when the algorithm is looking
    # for random values (or trying all) across a range
    if smoke_test:
        optim_config['MAX_NUMBER_PEQ'] = 5
        optim_config['MAX_STEPS_FREQ'] = 3
        optim_config['MAX_STEPS_DBGAIN'] = 3
        optim_config['MAX_STEPS_Q'] = 3
        # max iterations (if algorithm is iterative)
        optim_config['maxiter'] = 20
    else:
        optim_config['MAX_NUMBER_PEQ'] = 20
        optim_config['MAX_STEPS_FREQ'] = 5
        optim_config['MAX_STEPS_DBGAIN'] = 5
        optim_config['MAX_STEPS_Q'] = 5
        # max iterations (if algorithm is iterative)
        optim_config['maxiter'] = 500

    # MIN or MAX_Q or MIN or MAX_DBGAIN control the shape of the biquad which
    # are admissible.
    optim_config['MIN_DBGAIN'] = 0.2
    optim_config['MAX_DBGAIN'] = 12
    optim_config['MIN_Q'] = 0.1
    optim_config['MAX_Q'] = 12

    # do we override optim default?
    if args['--max-peq'] is not None:
        max_number_peq = int(args['--max-peq'])
        optim_config['MAX_NUMBER_PEQ'] = max_number_peq
    if args['--min-Q'] is not None:
        min_Q = float(args['--min-Q'])
        optim_config['MIN_Q'] = min_Q
    if args['--max-Q'] is not None:
        max_Q = float(args['--max-Q'])
        optim_config['MAX_Q'] = max_Q
    if args['--min-dB'] is not None:
        min_dB = float(args['--min-dB'])
        optim_config['MIN_DBGAIN'] = min_dB
    if args['--max-dB'] is not None:
        max_dB = float(args['--max-dB'])
        optim_config['MAX_DBGAIN'] = max_dB
    if args['--max-iter'] is not None:
        max_iter = int(args['--max-iter'])
        optim_config['maxiter'] = max_iter
    if args['--min-freq'] is not None:
        min_freq = int(args['--min-freq'])
        optim_config['freq_req_min'] = min_freq
    if args['--max-freq'] is not None:
        max_freq = int(args['--max-freq'])
        optim_config['freq_req_max'] = max_freq
    if args['--only-biquad-peak'] is not None:
        if args['--only-biquad-peak'] is True:
            optim_config['full_biquad_optim'] = False
    if args['--curve-peak-only'] is not None:
        if args['--curve-peak-only'] is True:
            optim_config['plus_and_minus'] = False

    # name of speaker
    speaker_name = None
    if args['--speaker'] is not None:
        speaker_name = args['--speaker']

    # load data
    df_all_speakers = {}
    if smoke_test is True:
        df_all_speakers = fl.load(path='./cache.smoketest_speakers.h5')
    else:
        if speaker_name is None:
            df_all_speakers = fl.load(path='./cache.parse_all_speakers.h5')
        else:
            df_speaker = fl.load(path='./cache.parse_all_speakers.h5',
                                 group='/{}'.format(speaker_name))
            df_all_speakers[speaker_name] = df_speaker

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
            sys,sys.exit(0)
        default = 'asr'
        if speaker_name in metadata.keys() and 'default_measurement'in metadata[speaker_name].keys():
            default = metadata[speaker_name]['default_measurement']
        df_speaker = df_all_speakers[speaker_name]['ASR'][default]
        df_speaker_eq = None
        default_eq = '{}_eq'.format(default)
        if default_eq in df_all_speakers[speaker_name]['ASR'].keys():
            df_speaker_eq = df_all_speakers[speaker_name]['ASR'][default_eq]
        # compute 
        id = optim_save_peq.remote(speaker_name, df_speaker, df_speaker_eq,
                                   optim_config, verbose, smoke_test)
        while 1:
            ready_ids, remaining_ids = ray.wait([id], num_returns=1)
            if len(ready_ids) == 1:
                _, _ = ray.get(ready_ids[0])
                break
            if len(remaining_ids) == 0:
                break
        
    sys.exit(0)
