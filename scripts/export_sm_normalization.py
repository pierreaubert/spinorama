#!/usr/bin/env python3
"""Export raw and slope-normalized SM values.

The CSV contains one row per speaker's default measurement.  ``*_raw_r2`` is
the unnormalized regression R², while ``*_normalized_r2`` is the current SM
calculation after correcting the response to the reference slope of -1 against
ln(f), equivalently -ln(10) dB/decade. The two score curves are exported because
they are the SM values
used by the preference-rating code: Sound Power and Estimated In-Room Response.

Run from the repository root with::

    .venv/bin/python scripts/export_sm_normalization.py

Use ``--all-measurements`` to emit one row for every cached non-EQ measurement
instead of only the default measurement for each speaker.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from generate_common import cache_load
from datas.speaker import speakers_info
from spinorama.compute.smoothness import compute_smoothness_regression
from spinorama.measurements import Measurements

CSV_FIELDS = [
    "speaker",
    "brand",
    "model",
    "measurement",
    "origin",
    "sm_sound_power_raw_r2",
    "sm_sound_power_normalized_r2",
    "sm_sound_power_normalized_minus_raw",
    "sm_pred_in_room_raw_r2",
    "sm_pred_in_room_normalized_r2",
    "sm_pred_in_room_normalized_minus_raw",
    "status",
]


def _raw_smoothness(freq: np.ndarray, values: np.ndarray) -> float:
    """Return the unnormalized regression R²."""
    x = np.log10(freq)
    x_mean = np.mean(x)
    y_mean = np.mean(values)
    ss_xx = np.sum((x - x_mean) ** 2)
    ss_yy = np.sum((values - y_mean) ** 2)
    if ss_xx == 0 or ss_yy == 0:
        return 1.0

    ss_xy = np.sum((x - x_mean) * (values - y_mean))
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    predicted = intercept + slope * x
    residual = np.sum((values - predicted) ** 2)
    return float(max(0.0, min(1.0, 1.0 - residual / ss_yy)))


def _sm_pair(frame: pd.DataFrame | None, column: str) -> tuple[float | None, float | None]:
    """Return ``(before, after)`` SM values for one wide-form curve."""
    if frame is None or column not in frame or "Freq" not in frame:
        return None, None

    data = frame[["Freq", column]].rename(columns={column: "dB"}).dropna()
    data = data.loc[(data.Freq >= 100) & (data.Freq <= 16000)]
    if len(data) < 2:
        return None, None

    freq = data.Freq.to_numpy(dtype=float)
    values = data.dB.to_numpy(dtype=float)
    finite = np.isfinite(freq) & np.isfinite(values)
    freq = freq[finite]
    values = values[finite]
    if len(freq) < 2:
        return None, None

    raw_r2 = _raw_smoothness(freq, values)
    normalized_r2 = compute_smoothness_regression(freq, values)[2]
    return raw_r2, float(normalized_r2)


def _as_measurements(value: Any) -> Measurements | None:
    if isinstance(value, Measurements):
        return value
    if isinstance(value, dict):
        return Measurements.from_legacy_dict(value)
    return None


def _measurement_value(
    speaker_data: Mapping[str, Any], measurement_key: str, preferred_origin: str | None
) -> tuple[str | None, Measurements | None]:
    """Find one measurement, preferring the origin declared in metadata."""
    origins = list(speaker_data)
    if preferred_origin in speaker_data:
        origins.remove(preferred_origin)
        origins.insert(0, preferred_origin)
    elif preferred_origin is not None:
        for origin in origins:
            if str(origin).casefold() == preferred_origin.casefold():
                origins.remove(origin)
                origins.insert(0, origin)
                break

    for origin in origins:
        versions = speaker_data[origin]
        if not isinstance(versions, Mapping) or measurement_key not in versions:
            continue
        measurement = _as_measurements(versions[measurement_key])
        if measurement is not None:
            return str(origin), measurement
    return None, None


def _iter_measurements(
    speaker_data: Mapping[str, Any],
) -> list[tuple[str, str, Measurements]]:
    measurements = []
    for origin, versions in speaker_data.items():
        if not isinstance(versions, Mapping):
            continue
        for version, value in versions.items():
            if str(version).endswith("_eq"):
                continue
            measurement = _as_measurements(value)
            if measurement is not None:
                measurements.append((str(origin), str(version), measurement))
    return measurements


def _row(
    speaker: str,
    info: Mapping[str, Any],
    measurement_key: str,
    origin: str | None,
    measurement: Measurements | None,
) -> dict[str, Any]:
    sound_power_raw_r2, sound_power_normalized_r2 = _sm_pair(
        measurement.cea2034 if measurement is not None else None, "Sound Power"
    )
    pir_raw_r2, pir_normalized_r2 = _sm_pair(
        measurement.eir if measurement is not None else None, "Estimated In-Room Response"
    )

    values = {
        "speaker": speaker,
        "brand": info.get("brand", ""),
        "model": info.get("model", ""),
        "measurement": measurement_key,
        "origin": origin or "",
        "sm_sound_power_raw_r2": sound_power_raw_r2,
        "sm_sound_power_normalized_r2": sound_power_normalized_r2,
        "sm_sound_power_normalized_minus_raw": _delta(
            sound_power_raw_r2, sound_power_normalized_r2
        ),
        "sm_pred_in_room_raw_r2": pir_raw_r2,
        "sm_pred_in_room_normalized_r2": pir_normalized_r2,
        "sm_pred_in_room_normalized_minus_raw": _delta(pir_raw_r2, pir_normalized_r2),
        "status": "ok",
    }
    statuses = []
    if measurement is None:
        statuses.append("missing_default_measurement")
    if sound_power_raw_r2 is None:
        statuses.append("missing_sound_power")
    if pir_raw_r2 is None:
        statuses.append("missing_pred_in_room")
    if statuses:
        values["status"] = ";".join(statuses)
    return values


def _delta(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None
    return after - before


def build_rows(
    cached_speakers: Mapping[str, Any],
    metadata: Mapping[str, Mapping[str, Any]],
    *,
    all_measurements: bool = False,
) -> list[dict[str, Any]]:
    """Build CSV rows, including metadata speakers with missing cache data."""
    rows = []
    for speaker, info in metadata.items():
        speaker_data = cached_speakers.get(speaker)
        if not isinstance(speaker_data, Mapping):
            default_key = str(info.get("default_measurement", ""))
            missing_row = _row(speaker, info, default_key, None, None)
            missing_row["status"] = "missing_cache"
            rows.append(missing_row)
            continue

        if all_measurements:
            measurements = _iter_measurements(speaker_data)
            if measurements:
                for origin, version, measurement in measurements:
                    rows.append(_row(speaker, info, version, origin, measurement))
            else:
                rows.append(
                    _row(
                        speaker,
                        info,
                        str(info.get("default_measurement", "")),
                        None,
                        None,
                    )
                )
            continue

        measurement_key = str(info.get("default_measurement", ""))
        measurement_info = info.get("measurements", {}).get(measurement_key, {})
        preferred_origin = (
            measurement_info.get("origin") if isinstance(measurement_info, Mapping) else None
        )
        origin, measurement = _measurement_value(speaker_data, measurement_key, preferred_origin)
        rows.append(_row(speaker, info, measurement_key, origin, measurement))
    return rows


def write_csv(rows: list[Mapping[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: "" if row.get(key) is None else row.get(key) for key in CSV_FIELDS}
            )


def load_cached_speakers(repository_root: Path) -> Mapping[str, Any]:
    """Load the canonical graph cache while making relative cache paths stable."""
    previous_directory = Path.cwd()
    os.chdir(repository_root)
    try:
        return cache_load(
            filters={"speaker_name": None, "origin": None, "format": None, "version": None},
            smoke_test=False,
            level=logging.WARNING,
        )
    finally:
        os.chdir(previous_directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("build/sm_normalization.csv"),
        help="CSV output path (default: build/sm_normalization.csv)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="Repository root containing .cache and datas (default: script repository)",
    )
    parser.add_argument(
        "--all-measurements",
        action="store_true",
        help="Export every cached non-EQ measurement instead of default measurements only",
    )
    args = parser.parse_args()

    cached_speakers = load_cached_speakers(args.root.resolve())
    rows = build_rows(cached_speakers, speakers_info, all_measurements=args.all_measurements)
    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
