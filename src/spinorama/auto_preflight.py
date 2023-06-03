# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
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

import pandas as pd

from spinorama import logger
from spinorama.ltype import Vector


def optim_preflight(
    freq: Vector,
    target: list[Vector],
    auto_target_interp: list[Vector],
    df_speaker: dict[str, pd.DataFrame],
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

    if isinstance(df_speaker, pd.DataFrame):
        logger.error("df_speaker is a DataFrame but should be a dict[str, df]")
        status = False
    if not isinstance(df_speaker, dict):
        logger.error("df_speaker is a DataFrame but should be a dict[str, df]")
        status = False
    if isinstance(df_speaker, dict) and len(df_speaker.keys()) == 0:
        logger.error("df_speaker is empty")
        status = False

    return status
