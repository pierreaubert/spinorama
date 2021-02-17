#!/usr/bin/env python
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

import logging

import scipy.optimize as opt

from .filter_iir import Biquad
from .auto_loss import loss, score_loss


logger = logging.getLogger("spinorama")


def find_best_biquad(
    freq,
    auto_target,
    freq_range,
    Q_range,
    dbGain_range,
    biquad_range,
    count,
    optim_config,
):
    def opt_peq(x):
        peq = [(1.0, Biquad(int(x[0]), x[1], 48000, x[2], x[3]))]
        return loss(freq, auto_target, peq, count, optim_config)

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
        "x": [0.0, 0.0, 0.0, 0.0],
        "fun": 0.0,
        "nit": -1,
        "message": "",
    }
    try:
        res = opt.dual_annealing(
            opt_peq,
            bounds,
            maxiter=optim_config["maxiter"],
            # initial_temp=10000
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
    except ValueError as ve:
        res["success"] = False
        logger.error("{} bounds {}".format(ve, bounds))
        for i in range(0, 4):
            if bounds[i][0] >= bounds[i][1]:
                logger.error("on bound [{}]".format(i))
                return (
                    res["success"],
                    int(res["x"][0]),
                    res["x"][1],
                    res["x"][2],
                    res["x"][3],
                    res["fun"],
                    res["nit"],
                )


def find_best_peak(
    freq,
    auto_target,
    freq_range,
    Q_range,
    dbGain_range,
    biquad_range,
    count,
    optim_config,
):

    biquad_type = 3

    def opt_peq(x):
        peq = [(1.0, Biquad(biquad_type, x[0], 48000, x[1], x[2]))]
        return loss(freq, auto_target, peq, count, optim_config)

    bounds = [
        (freq_range[0], freq_range[-1]),
        (Q_range[0], Q_range[-1]),
        (dbGain_range[0], dbGain_range[-1]),
    ]

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
        "x": [0.0, 0.0, 0.0, 0.0],
        "fun": 0.0,
        "nit": -1,
        "message": "",
    }
    try:
        res = opt.dual_annealing(
            opt_peq, bounds, maxiter=optim_config["maxiter"], initial_temp=10000
        )
        logger.debug(
            "          optim loss {:2.2f} in {} iter type PK at F {:.0f} Hz Q {:2.2f} dbGain {:2.2f} {}".format(
                res.fun, res.nfev, res.x[0], res.x[1], res.x[2], res.message
            )
        )
        return res.success, biquad_type, res.x[0], res.x[1], res.x[2], res.fun, res.nit
    except ValueError as ve:
        logger.error("{} bounds {}".format(ve, bounds))
        for i in range(0, 4):
            if bounds[i][0] >= bounds[i][1]:
                logger.error("on bound [{}]".format(i))
        return False, 0, -1, -1, -1, -1, -1
