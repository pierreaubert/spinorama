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

# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import pathlib

import numpy as np
import pandas as pd
import plotly.io

from spinorama import logger


def graph_melt(df_in: pd.DataFrame) -> pd.DataFrame:
    """Convert wide-format DataFrame to long-format.

    Args:
        df: DataFrame with 'Freq' and measurement columns

    Returns:
        DataFrame with columns ['Freq', 'Measurements', 'dB']
    """
    # Ensure we have a clean index
    if df_in is None:
        return None
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

    def a2v(angle: str) -> int:
        try:
            if angle == "Freq":
                return -1000
            if angle in ("On Axis", "On-Axis"):
                return 0
            if angle == "Phase On Axis":
                return 1000
            if angle[0:5] == "Phase":
                return 1000 + int(angle[6:-1])
            return int(angle[:-1])
        except ValueError as ve:
            logger.error("Parsing error for =={}== {}".format(angle, ve))
            raise

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


def write_multiformat(chart, filename, force):
    """Write a png file and then convert and save to jpg and webp"""
    filepath = pathlib.Path(filename)

    if not filepath.parent.exists():
        logger.warning("%s parent dir does not exists!", filename)
        return
    if not filepath.is_file() or force:
        try:
            plotly.io.write_images(
                [chart, chart, chart],
                file=[
                    filename,
                    filename.replace("_large.png", ".jpg"),
                    filename.replace("_large.png", ".webp"),
                ],
                width=chart.layout.width,
                height=chart.layout.height,
            )
        except RuntimeError as rt:
            logger.error("writing image %s crashed! %s", filename, rt)
            return
    if os.path.getsize(filename) == 0:
        logger.warning("Saving %s failed!", filename)
        return
    logger.info("Saving %s", filename)


def write_multiformat_batch(
    charts_and_files: list[tuple[object, str]], force: bool, chunk_size: int = 64
) -> None:
    """Write many charts to png/jpg/webp in batches using plotly.io.write_images.

    charts_and_files: list of (chart, filename_png) - png filename
    force: bypass existing-file check in caller context
    chunk_size: number of charts to process per batch
    """
    if not charts_and_files:
        return

    # Assume all charts share the same dimensions. Use the first one.
    first_chart = charts_and_files[0][0]
    try:
        width = first_chart.layout.width
        height = first_chart.layout.height
    except Exception:
        width = None
        height = None

    # Process in chunks to limit memory usage
    for i in range(0, len(charts_and_files), chunk_size):
        batch = charts_and_files[i : i + chunk_size]
        charts: list[object] = []
        files: list[str] = []
        # Prepare triplets for each chart (png, jpg, webp)
        for chart, filename in batch:
            filepath = pathlib.Path(filename)
            if not filepath.parent.exists():
                logger.warning("%s parent dir does not exists!", filename)
                continue
            if filepath.is_file() and not force:
                # Skip if already exists and not forcing
                continue
            charts.extend([chart, chart, chart])
            # Handle both _large.png and .png formats
            if filename.endswith("_large.png"):
                files.extend(
                    [
                        filename,
                        filename.replace("_large.png", ".jpg"),
                        filename.replace("_large.png", ".webp"),
                    ]
                )
            elif filename.endswith(".png"):
                base_filename = filename[:-4]  # Remove .png extension
                files.extend(
                    [
                        filename,
                        base_filename + ".jpg",
                        base_filename + ".webp",
                    ]
                )
            else:
                logger.warning("Unexpected filename format: %s", filename)
                continue
        if not charts:
            continue
        try:
            kwargs = {}
            if width is not None and height is not None:
                kwargs = {"width": width, "height": height}
            plotly.io.write_images(charts, file=files, **kwargs)
            # Log successful writes
            for _, filename in batch:
                logger.info("Saving %s", filename)
        except RuntimeError as rt:
            logger.error("batch write_images crashed! %s", rt)
            # Fall back to single writes for this batch to continue progress
            for chart, filename in batch:
                try:
                    write_multiformat(chart, filename, force)
                except Exception:
                    logger.exception("fallback write failed for %s", filename)


def expected_measurements(spl: pd.DataFrame) -> bool:
    expected = set(["{}°".format(i) for i in range(-170, 190, 10)])
    if spl is not None and "5°" in spl:
        expected = set(["{}°".format(i) for i in range(-175, 185, 5)])
    expected.remove("0°")
    expected.add("On Axis")
    return expected.issubset(spl)


def measurements_complete_spl(h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None) -> bool:
    complete_spl = False
    if (
        h_spl is not None
        and v_spl is not None
        and expected_measurements(h_spl)
        and expected_measurements(v_spl)
    ):
        complete_spl = True
    if not complete_spl:
        logger.debug("check spl : %s", str(complete_spl))
        if h_spl is not None and v_spl is not None:
            logger.info("missing angles : %s", measurements_missing_angles(h_spl, v_spl))
    return complete_spl


def measurements_complete_freq(h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None) -> bool:
    def check(spl: pd.DataFrame | None) -> bool:
        complete_freq = False
        if spl is not None:
            freq = spl["Freq"]
            # 97 comes from some old ASR measurements that are good enough but only have 98 freq datapoints
            # later on, ASR switched to 200 points
            if freq.min() < 40 and freq.max() > 16000 and freq.shape[0] > 97:
                complete_freq = True
            else:
                logger.debug(
                    "check freq failed: min=%fHz max=%fHz #=%d",
                    freq.min(),
                    freq.max(),
                    freq.shape[0],
                )
        return complete_freq

    complete = check(h_spl) and check(v_spl)
    if not complete:
        logger.debug("check freq H: %s", check(h_spl))
        logger.debug("check freq V: %s", check(v_spl))
    return complete


def measurements_missing_angles(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> str:
    expected = set(["{}°".format(i) for i in range(-170, 190, 10)])
    if (h_spl is not None and "5°" in h_spl) or (v_spl is not None and "5°" in v_spl):
        expected = set(["{}°".format(i) for i in range(-175, 185, 5)])
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


def measurements_valid_freq_range(
    speaker_name: str,
    version: str,
    h_spl: pd.DataFrame | None,
    v_spl: pd.DataFrame | None,
) -> tuple[float, float]:
    from datas import Measurement  # noqa: PLC0415
    from datas.helpers import measurement_valid_freq  # noqa: PLC0415
    from datas.speaker import speakers_info  # noqa: PLC0415

    measurement: Measurement = speakers_info[speaker_name]["measurements"][version]
    min_valid_freq, max_valid_freq = measurement_valid_freq(speaker_name, measurement)
    if h_spl is not None and "Freq" in h_spl:
        min_valid_freq = max(min_valid_freq, h_spl.Freq.min())
        max_valid_freq = min(max_valid_freq, h_spl.Freq.max())
    if v_spl is not None and "Freq" in v_spl:
        min_valid_freq = max(min_valid_freq, v_spl.Freq.min())
        max_valid_freq = min(max_valid_freq, v_spl.Freq.max())
    min_valid_freq = max(20.0, min_valid_freq)
    max_valid_freq = min(20000.0, max_valid_freq)
    return min_valid_freq, max_valid_freq


def sanitize_filename(name: str) -> str:
    """Replace characters invalid on Windows filesystems with underscores.

    Windows doesn't allow: | < > : " / \\ ? * and control characters.
    """
    invalid_chars = '|:<>"\\/\\?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name
