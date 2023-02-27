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

from spinorama import logger
from spinorama.ltype import FloatVector1D


def optim_preflight(
    freq: FloatVector1D, target: list[FloatVector1D], auto_target_interp: list[FloatVector1D]
) -> bool:
    """Some quick checks before optim runs."""
    freq_len = len(freq)
    target_len = len(target)
    auto_len = len(auto_target_interp)

    status = True

    if freq_len != len(target[0]):
        logger.error("Size mismatch #freq %s != #target %d", freq_len, len(target[0]))
        status = False

    if target_len != auto_len:
        logger.error("Size mismatch #target %d != #auto_target_interp %d", target_len, auto_len)
        status = False

    for i in range(0, min(target_len, auto_len)):
        if len(target[i]) != len(auto_target_interp[i]):
            logger.error(
                "Size mismatch #target[%d] %d != #auto_target_interp[%d] %d",
                i,
                len(target[i]),
                i,
                len(auto_target_interp[i]),
            )
            status = False

    return status
