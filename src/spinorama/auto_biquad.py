#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import logging
import math

import numpy as np
import scipy.optimize as opt

from .ltype import DataSpeaker, Peq
from .filter_iir import Biquad
from .filter_peq import peq_print
from .auto_loss import loss


logger = logging.getLogger("spinorama")


def find_best_biquad(
    df_speaker: DataSpeaker,
    freq,
    auto_target,
    freq_range,
    Q_range,
    dbGain_range,
    biquad_range,
    count,
    optim_config,
    prev_best,
):
    def opt_peq(x):
        peq = [(1.0, Biquad(int(x[0]), x[1], 48000, x[2], x[3]))]
        return loss(df_speaker, freq, auto_target, peq, count, optim_config)

    bounds = [
        (biquad_range[0], biquad_range[-1]),
        (freq_range[0], freq_range[-1]),
        (Q_range[0], Q_range[-1]),
        (dbGain_range[0], dbGain_range[-1]),
    ]

    logger.debug(
        "range is [{}, {}], [{}, {}], [{}, {}], [{}, {}]".format(
            bounds[0][0],
            bounds[0][1],
            bounds[1][0],
            bounds[1][1],
            bounds[2][0],
            bounds[2][1],
            bounds[3][0],
            bounds[3][1],
        )
    )
    # can use differential_evolution basinhoppin dual_annealing
    res = {
        "success": False,
        "x": [
            3,
            (bounds[1][0] + bounds[1][1]) / 2,
            (bounds[2][0] + bounds[2][1]) / 2,
            (bounds[3][0] + bounds[3][1]) / 2,
        ],
        "fun": 0.0,
        "nit": -1,
        "message": "",
    }
    try:
        # res = opt.dual_annealing(
        #    opt_peq,
        #    bounds,
        #    maxiter=optim_config["maxiter"],
        #    # initial_temp=10000
        # )
        res = opt.differential_evolution(
            opt_peq,
            bounds,
            # workers=64,
            # updating='deferred',
            # mutation=(0.5, 1.5),
            # recombination=1.9,
            maxiter=optim_config["maxiter"],
            atol=0.01,
            polish=False,
            integrality=[True, False, False, False],
        )
        logger.debug(
            "          optim loss {:2.2f} in {} iter type {:d} at F {:.0f} Hz Q {:2.2f} dbGain {:2.2f} {}".format(
                res["fun"],
                res["nfev"],
                int(res["x"][0]),
                res["x"][1],
                res["x"][2],
                res["x"][3],
                res["message"],
            )
        )
        if res.message[0] == "Maximum number of function call reached during annealing" and res.fun < prev_best:
            res.success = True
        return (
            res.success,
            int(res.x[0]),
            res.x[1],
            res.x[2],
            res.x[3],
            res.fun,
            res.nit,
        )
    except ValueError as ve:
        res["success"] = False
        logger.error("{} bounds {}".format(ve, bounds))
        for i in range(0, 4):
            try:
                if bounds[i][0] >= bounds[i][1]:
                    logger.error("on bound [{}]".format(i))
            except ValueError:
                pass
            except IndexError:
                pass
        return False, 0, -1, -1, -1, -1, -1


def find_best_peak(
    df_speaker,
    freq,
    auto_target,
    freq_range,
    Q_range,
    dbGain_range,
    biquad_range,
    count,
    optim_config,
    prev_best,
):

    biquad_type = 3

    def opt_peq(x):
        peq = [(1.0, Biquad(biquad_type, x[0], 48000, x[1], x[2]))]
        return loss(df_speaker, freq, auto_target, peq, count, optim_config)

    bounds = [
        (freq_range[0], freq_range[-1]),
        (Q_range[0], Q_range[-1]),
        (dbGain_range[0], dbGain_range[-1]),
    ]

    # print('Bounds: {}'.format(bounds))

    x_init = [
        (bounds[0][0] + bounds[0][-1]) / 2,
        (bounds[1][0] + bounds[1][-1]) / 2,
        (bounds[2][0] + bounds[2][-1]) / 2,
    ]

    v_init = np.array(
        [
            np.logspace(math.log10(bounds[0][0]), math.log10(bounds[0][-1]), 5),
            np.linspace(bounds[1][0], bounds[1][-1], 5),
            np.linspace(bounds[2][0], bounds[2][-1], 5),
        ]
    ).T

    # print(v_init)

    z_init = [
        [v_init[i][0], v_init[j][1], v_init[k][2]]
        for i in range(0, len(v_init))
        for j in range(0, len(v_init))
        for k in range(0, len(v_init))
    ]

    # z_init.append([1000, 1, -3])
    # print(z_init)

    # grid_search = sorted(
    #     [(opt_peq(z),z) for z in z_init],
    #     key=lambda x: x[0])
    # for g in grid_search:
    #     print("{:3.3f} {:.0f}Hz {:.2f}Q {:.2f}dB".format(g[0], g[1][0], g[1][1], g[1][2]))
    # print('grid search top 2: {}'.format(grid_search[0:2]))

    logger.debug(
        "range is [{}, {}], [{}, {}], [{}, {}]".format(
            bounds[0][0],
            bounds[0][1],
            bounds[1][0],
            bounds[1][1],
            bounds[2][0],
            bounds[2][1],
        )
    )

    # can use differential_evolution basinhoppin dual_annealing
    res = {
        "success": False,
        "x": x_init,
        "fun": -1000.0,
        "nit": -1,
        "message": "",
    }
    try:
        # res = opt.dual_annealing(
        #    opt_peq,
        #    bounds,
        #    visit=2.9,
        #    maxfun=optim_config["maxiter"],
        #    initial_temp=10000,
        #    no_local_search=True,
        # )

        def display(xk, convergence):
            print(xk, convergence)

        res = opt.differential_evolution(
            opt_peq,
            bounds,
            # workers=64,
            # updating='deferred',
            # mutation=(0.5, 1.5),
            # recombination=1.9,
            # strategy='best2bin',
            # init='sobol',
            init=z_init,
            # x0 = x_init,
            # popsize=175,
            maxiter=optim_config["maxiter"],
            # disp=True,
            atol=0.01,
            # polish=True,
            integrality=[False, False, False],
            callback=display,
        )
        logger.info(
            "          optim loss {:2.2f} in {} iter type PK at F {:.0f} Hz Q {:2.2f} dbGain {:2.2f} {}".format(
                res.fun, res.nfev, res.x[0], res.x[1], res.x[2], res.message
            )
        )
        if res.message[0] == "Maximum number of function call reached during annealing" and res.fun < prev_best:
            res.success = True
        return res.success, biquad_type, res.x[0], res.x[1], res.x[2], res.fun, res.nit
    except ValueError as ve:
        logger.error("{} bounds {}".format(ve, bounds))
        for i in range(0, 4):
            try:
                if bounds[i][0] >= bounds[i][1]:
                    logger.error("on bound [{}]".format(i))
            except ValueError:
                pass
            except IndexError:
                pass
        return False, 0, -1, -1, -1, -1, -1
