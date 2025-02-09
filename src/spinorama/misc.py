# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

import pathlib

import pandas as pd
import numpy as np

from spinorama import logger


def graph_melt(df_in: pd.DataFrame) -> pd.DataFrame:
    """Convert wide-format DataFrame to long-format.

    Args:
        df: DataFrame with 'Freq' and measurement columns

    Returns:
        DataFrame with columns ['Freq', 'Measurements', 'dB']
    """
    # Ensure we have a clean index
    df_out = df_in.copy()
    if not isinstance(df_in.index, pd.RangeIndex):
        df_out = df_out.reset_index(drop=True)

    # Melt the dataframe
    return df_out.melt(id_vars="Freq", var_name="Measurements", value_name="dB")


def graph_unmelt(df_in: pd.DataFrame) -> pd.DataFrame:
    """Convert long-format DataFrame back to wide-format.

    Args:
        df: DataFrame with columns ['Freq', 'Measurements', 'dB']

    Returns:
        DataFrame with 'Freq' and measurement columns
    """
    # Handle potential duplicate (Freq, Measurements) pairs
    df_out = df_in.pivot_table(
        index="Freq",
        columns="Measurements",
        values="dB",
        aggfunc="first",  # Take first value instead of max for duplicates
    )

    # Clean up the index/columns
    df_out.columns.name = None
    return df_out.reset_index()


def sort_angles(dfi: pd.DataFrame) -> pd.DataFrame:
    """Sort DataFrame columns by measurement angles in ascending order.

    Special handling for 'Freq' (placed first) and 'On Axis'/'On-Axis' (placed after Freq).
    Angles are expected to be in format like '30°', '-30°', etc.

    Args:
        dfi: DataFrame with angle measurements as columns

    Returns:
        DataFrame with columns sorted by angle values
    """

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
    """Check for NaN values in a dictionary of DataFrames.

    Args:
        df: Dictionary containing DataFrames to check

    Returns:
        Total number of NaN values found across all DataFrames

    Notes:
        Logs error messages for each column containing NaN values
    """
    for k, v in df.items():
        if not isinstance(v, pd.DataFrame):
            continue
        for j in v:
            if isinstance(v, pd.DataFrame):
                count = v[j].isna().sum()
                if count > 0:
                    logger.error("%d %d %d", k, j, count)
    return np.sum(
        [df[frame].isna().sum().sum() for frame in df if isinstance(df[frame], pd.DataFrame)]
    )


def need_update(filename: str, dependencies: list[str]) -> bool:
    """Check if a file needs to be updated based on its dependencies.

    Args:
        filename: Path to the file to check
        dependencies: List of paths to dependency files

    Returns:
        True if the file needs to be updated (doesn't exist, is empty,
        or is older than any dependency), False otherwise

    Notes:
        A file needs updating if:
        - It doesn't exist
        - It's empty
        - Any of its dependencies are newer than the file itself
    """
    # if filename doesn't exist then True
    path = pathlib.Path(filename)
    if not path.is_file():
        return True

    # if file is empty (we store images or json)
    file_stats = path.stat()
    if file_stats.st_size == 0:
        return True

    # if one of the dep is newer than file then True
    for dep in dependencies:
        dep_path = pathlib.Path(dep)
        if not dep_path or dep_path.is_symlink():
            continue
        dep_stats = dep_path.stat()
        if dep_stats.st_mtime > file_stats.st_mtime:
            return True

    return False


def write_if_different(new_content: str, filename: str, force: bool = False) -> None:  # noqa: FBT002
    """Write content to a file only if it differs from current content.

    Args:
        new_content: Content to write to the file
        filename: Path to the target file
        force: If True, write regardless of current content

    Notes:
        This function helps optimize HTTP caching by only updating files
        when their content actually changes. If force is True, the file
        will be written regardless of current content.
    """
    identical = False
    path = pathlib.Path(filename)
    if path.exists():
        old_content = path.read_text(encoding="utf-8")
        if old_content == new_content:
            identical = True

    if not identical or force:
        path.write_text(new_content, encoding="utf-8")


def measurements_complete_spl(h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None) -> bool:
    complete_spl = False
    expected = set(["{}°".format(i) for i in range(-170, 190, 10)])
    expected.remove("0°")
    expected.add("On Axis")
    if (
        h_spl is not None
        and v_spl is not None
        and expected.issubset(set(h_spl.keys()))
        and expected.issubset(set(v_spl.keys()))
    ):
        complete_spl = True
    # print('check spl : {} H {} V {}'.format(
    #    complete_spl,
    #    expected.issubset(set(h_spl.keys())),
    #    expected.issubset(set(v_spl.keys())),
    # ))
    return complete_spl


def measurements_complete_freq(h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None) -> bool:
    def check(spl: pd.DataFrame | None) -> bool:
        complete_freq = False
        if spl is not None:
            freq = spl["Freq"]
            if freq.min() < 40 and freq.max() > 16000 and freq.shape[0] > 100:
                complete_freq = True
        return complete_freq

    # print('check freq H: {}'.format(check(h_spl)))
    # print('check freq V: {}'.format(check(v_spl)))
    return check(h_spl) and check(v_spl)


def measurements_missing_angles(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> str:
    expected = set(["{}°".format(i) for i in range(-170, 190, 10)])
    expected.remove("0°")
    expected.add("On Axis")
    found_h = set(h_spl.keys())
    found_v = set(v_spl.keys())
    diff_h = expected - found_h
    diff_v = expected - found_v
    return "H {} V {}".format(
        ", ".join(diff_h),
        ", ".join(diff_v),
    )
