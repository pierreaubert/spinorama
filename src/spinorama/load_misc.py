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
import numpy as np

from spinorama import logger


def graph_melt(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.reset_index()
        .melt(id_vars="Freq", var_name="Measurements", value_name="dB")
        .loc[lambda df: df["Measurements"] != "index"]
    )


def graph_unmelt(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.pivot_table(index="Freq", columns="Measurements", values="dB", aggfunc="max")
        .rename_axis(columns=None)
        .reset_index()
    )


def sort_angles(dfi: pd.DataFrame) -> pd.DataFrame:
    # sort columns in increasing angle order
    def a2v(angle):
        if angle == "Freq":
            return -1000
        if angle in ("On Axis", "On-Axis"):
            return 0
        return int(angle[:-1])

    dfu = dfi.reindex(columns=sorted(set(dfi.columns), key=a2v))
    dfu = dfu.rename(columns={"On-Axis": "On Axis"})
    return dfu


def check_nan(df: dict) -> float:
    for k in df:
        if not isinstance(df[k], pd.DataFrame):
            continue
        for j in df[k]:
            if isinstance(df[k], pd.DataFrame):
                count = df[k][j].isna().sum()
                if count > 0:
                    logger.error("%d %d %d", k, j, count)
    return np.sum(
        [df[frame].isna().sum().sum() for frame in df if isinstance(df[frame], pd.DataFrame)]
    )
