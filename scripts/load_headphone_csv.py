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

"""Parse headphone frequency response CSV files.

Supports:
  - ASR 4-column (Hz,dBSPL,Hz,dBSPL with multi-line header, left+right channels)
  - AutoEq 2-column (frequency,raw)
  - Generic 2/3-column (freq,spl[,phase])
  - Headerless numeric CSV (first col = freq, second col = dB)

Output columns are normalised:
  - 4-column sources → Freq_L, dB_L, Freq_R, dB_R
  - 2-column sources → Freq, dB
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("spinorama")


def average_headphone_channels(df: pd.DataFrame) -> pd.DataFrame:
    """Average multiple headphone channels using pressure averaging.

    For stereo (L+R) data, converts each channel from dB to pressure,
    computes the mean pressure, and converts back to dB.
    For mono data, returns the input unchanged.

    Returns a DataFrame with Freq and dB columns.
    """
    if "Freq_L" not in df.columns:
        # Mono / single channel — already in Freq, dB format
        return df[["Freq", "dB"]].copy()

    # Pressure average: dB → pressure → mean → dB
    # Using the same reference as the codebase: p = 10^((dB-105)/20)
    p_left = np.power(10, (df["dB_L"] - 105.0) / 20.0)
    p_right = np.power(10, (df["dB_R"] - 105.0) / 20.0)
    p_avg = (p_left + p_right) / 2.0
    db_avg = 20.0 * np.log10(p_avg) + 105.0

    return pd.DataFrame({"Freq": df["Freq_L"], "dB": db_avg})

# Strict keywords for detecting the header row (no x/y — too generic)
_HEADER_FREQ_KW = {"frequency", "freq", "hz"}
_HEADER_DB_KW = {"raw", "spl", "db", "dbspl", "level"}

# Looser keywords for mapping columns after parsing
_COL_FREQ_KW = ("frequency", "freq", "hz", "x")
_COL_DB_KW = ("raw", "spl", "db", "dbspl", "level", "y")


def _find_header_row(lines: list[str]) -> int | None:
    """Return the line index that contains recognisable column headers."""
    for i, line in enumerate(lines):
        parts = {p.strip().strip('"').lower() for p in line.split(",")}
        if parts & _HEADER_FREQ_KW and parts & _HEADER_DB_KW:
            return i
    return None


def _find_first_numeric_row(lines: list[str]) -> int | None:
    """Return the line index of the first row with numeric CSV data."""
    for i, line in enumerate(lines):
        parts = line.strip().split(",")
        if len(parts) >= 2:
            try:
                float(parts[0])
                float(parts[1])
                return i
            except ValueError:
                pass
    return None


def _extract_columns(df: pd.DataFrame, filepath: str) -> pd.DataFrame | None:
    """Normalise *df* into Freq/dB (2-col) or Freq_L/dB_L/Freq_R/dB_R (4-col)."""
    cols_raw = list(df.columns)
    cols = [str(c).strip().lower() for c in cols_raw]
    df.columns = pd.Index(cols)

    # --- ASR 4-column: Hz, dBSPL, Hz.1, dBSPL.1 ---
    if len(cols) >= 4:
        freq_cols = [c for c in cols if any(c.startswith(k) for k in ("hz", "freq"))]
        db_cols = [c for c in cols if any(c.startswith(k) for k in ("dbspl", "spl", "db"))]
        if len(freq_cols) >= 2 and len(db_cols) >= 2:
            result = pd.DataFrame(
                {
                    "Freq_L": pd.to_numeric(df[freq_cols[0]], errors="coerce"),
                    "dB_L": pd.to_numeric(df[db_cols[0]], errors="coerce"),
                    "Freq_R": pd.to_numeric(df[freq_cols[1]], errors="coerce"),
                    "dB_R": pd.to_numeric(df[db_cols[1]], errors="coerce"),
                }
            ).dropna()
            if len(result) >= 10:
                logger.info(
                    "Loaded %d points (L+R) from %s (%.0f-%.0f Hz)",
                    len(result),
                    filepath,
                    result["Freq_L"].min(),
                    result["Freq_L"].max(),
                )
                return result

    # --- standard 2-column ---
    freq_col = None
    for candidate in _COL_FREQ_KW:
        if candidate in cols:
            freq_col = candidate
            break

    db_col = None
    for candidate in _COL_DB_KW:
        if candidate in cols:
            db_col = candidate
            break

    # headerless: integer column names from read_csv(header=None)
    if freq_col is None and db_col is None and len(cols) >= 2:
        try:
            float(str(cols_raw[0]))
            freq_col = cols[0]
            db_col = cols[1]
        except ValueError:
            pass

    if freq_col is None or db_col is None:
        logger.error("Could not identify columns in %s (columns: %s)", filepath, cols)
        return None

    result = pd.DataFrame(
        {
            "Freq": pd.to_numeric(df[freq_col], errors="coerce"),
            "dB": pd.to_numeric(df[db_col], errors="coerce"),
        }
    ).dropna()

    if result.empty:
        logger.error("No valid data points in %s", filepath)
        return None

    logger.info(
        "Loaded %d points from %s (%.0f-%.0f Hz)",
        len(result),
        filepath,
        result["Freq"].min(),
        result["Freq"].max(),
    )
    return result


def parse_headphone_csv(filepath: str) -> pd.DataFrame | None:
    """Parse a headphone frequency response CSV file.

    Returns a DataFrame with either:
      - ``Freq, dB`` (2-column sources)
      - ``Freq_L, dB_L, Freq_R, dB_R`` (4-column ASR sources)
    or *None* on failure.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            peek = [f.readline() for _ in range(15)]
    except OSError as e:
        logger.error("Failed to read %s: %s", filepath, e)
        return None

    header_row = _find_header_row(peek)

    try:
        if header_row is not None:
            df = pd.read_csv(filepath, header=header_row, on_bad_lines="skip")
        else:
            skip = _find_first_numeric_row(peek)
            if skip is None:
                logger.error("No recognisable header or numeric data in %s", filepath)
                return None
            df = pd.read_csv(filepath, header=None, skiprows=skip, on_bad_lines="skip")
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
        logger.error("Failed to parse %s: %s", filepath, e)
        return None

    return _extract_columns(df, filepath)
