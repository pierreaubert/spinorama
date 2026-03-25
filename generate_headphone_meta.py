#!/usr/bin/env python3
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

"""Generate headphone.json metadata from datas/headphones.py and CSV measurements."""

import argparse
import json
import logging
import math
import os
import zipfile

import numpy as np

import spinorama.constant_paths as cpaths
from api.load_headphone_csv import parse_headphone_csv

logger = logging.getLogger("spinorama")


def discover_headphones() -> dict:
    """Auto-discover headphones from ASR API and local filesystem.

    Tries the ASR JSON API first (provides accurate brand/model/shape),
    then fills in any remaining local entries from the filesystem.
    """
    result: dict = {}

    # Try API first for accurate metadata
    try:
        from api.scrape_asr_headphones import (
            DEVICE_TYPE_MAP,
            SKIP_DEVICE_TYPES,
            fetch_headphone_index,
        )

        entries = fetch_headphone_index()
        for entry in entries:
            device_type = entry.get("DeviceType", "")
            if device_type in SKIP_DEVICE_TYPES:
                continue
            shape = DEVICE_TYPE_MAP.get(device_type)
            if shape is None:
                continue

            brand = entry.get("Brand", "").strip()
            model = entry.get("Model", "").strip()
            if not brand or not model:
                continue

            full_name = f"{brand} {model}"
            csv_path = f"{cpaths.CPATH_DATAS_HEADPHONES}/{full_name}/asr/frequency_response.csv"
            if not os.path.exists(csv_path):
                continue

            meas: dict = {"origin": "ASR", "format": "csv_freq_spl"}
            review_url = entry.get("ReviewLink", "")
            if review_url:
                meas["review"] = review_url
            review_date = entry.get("ReviewDate", "")
            if review_date:
                meas["review_published"] = review_date

            hp: dict = {
                "brand": brand,
                "model": model,
                "shape": shape,
                "default_measurement": "asr",
                "measurements": {"asr": meas},
            }
            price = entry.get("Price_Each_USD", "")
            if price:
                hp["price"] = str(price)

            result[full_name] = hp

        logger.info("Discovered %d headphones from ASR API", len(result))
    except Exception as exc:
        logger.warning("ASR API discovery failed: %s", exc)

    # Fill in any local entries not covered by API
    base = cpaths.CPATH_DATAS_HEADPHONES
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if name in result:
                continue
            csv_path = os.path.join(base, name, "asr", "frequency_response.csv")
            if not os.path.exists(csv_path):
                continue

            parts = name.split(" ", 1)
            brand = parts[0]
            model = parts[1] if len(parts) > 1 else name

            result[name] = {
                "brand": brand,
                "model": model,
                "shape": "over-ear",
                "default_measurement": "asr",
                "measurements": {
                    "asr": {
                        "origin": "ASR",
                        "format": "csv_freq_spl",
                    }
                },
            }

        logger.info("Total after filesystem discovery: %d headphones", len(result))

    return result


def compute_flatness_score(filepath: str) -> float | None:
    """Compute a simple flatness score (RMS deviation from mean in dB).

    Lower is flatter / better.
    Handles both 2-column (Freq, dB) and 4-column (Freq_L, dB_L, Freq_R, dB_R) formats.
    For 4-column data the left and right channels are averaged first.
    """
    df = parse_headphone_csv(filepath)
    if df is None:
        return None

    if "Freq_L" in df.columns:
        freq = df["Freq_L"]
        db = (df["dB_L"] + df["dB_R"]) / 2
    else:
        freq = df["Freq"]
        db = df["dB"]

    mask = (freq >= 20) & (freq <= 20000)
    db_values = np.asarray(db[mask])

    if len(db_values) < 10:
        return None

    mean_db = float(np.mean(db_values))
    rms_deviation = float(math.sqrt(np.mean((db_values - mean_db) ** 2)))
    return round(rms_deviation, 2)


def build_headphone_metadata(headphones_info: dict) -> dict:
    """Build the output metadata dict for headphone.json."""
    output = {}

    for name, hp in headphones_info.items():
        if hp.get("skip", False):
            continue

        entry = {
            "brand": hp["brand"],
            "model": hp["model"],
            "shape": hp["shape"],
            "default_measurement": hp["default_measurement"],
            "measurements": {},
        }

        if "price" in hp:
            entry["price"] = hp["price"]

        for meas_key, meas in hp["measurements"].items():
            meas_entry: dict = {
                "origin": meas["origin"],
                "format": meas["format"],
            }

            if "review" in meas:
                meas_entry["review"] = meas["review"]
            if "review_published" in meas:
                meas_entry["review_published"] = meas["review_published"]
            if "quality" in meas:
                meas_entry["quality"] = meas["quality"]
            if "notes" in meas:
                meas_entry["notes"] = meas["notes"]
            if "sensitivity_mV_94dB" in meas:
                meas_entry["sensitivity_mV_94dB"] = meas["sensitivity_mV_94dB"]
            if "recommendation" in meas:
                meas_entry["recommendation"] = meas["recommendation"]

            # Try to load FR data and compute flatness
            csv_path = f"{cpaths.CPATH_DATAS_HEADPHONES}/{name}/asr/frequency_response.csv"
            if os.path.exists(csv_path):
                score = compute_flatness_score(csv_path)
                if score is not None:
                    meas_entry["flatness_rms"] = score

            entry["measurements"][meas_key] = meas_entry

        output[name] = entry

    return output


def dict_to_json(filename: str, data: dict) -> None:
    """Write a dict as JSON with compressed variants."""
    js = json.dumps(data)

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(js)
    logger.info("Generated %s", filename)

    for ext, method in (
        ("zip", zipfile.ZIP_DEFLATED),
        ("bz2", zipfile.ZIP_BZIP2),
    ):
        compressed_path = f"{filename}.{ext}"
        with zipfile.ZipFile(
            compressed_path,
            "w",
            compression=method,
            allowZip64=True,
        ) as zf:
            zf.writestr(os.path.basename(filename), js)
        logger.info("Generated %s", compressed_path)


def main():
    parser = argparse.ArgumentParser(description="Generate headphone.json metadata")
    parser.add_argument("--log-level", type=str, default="WARNING", help="Logging level")
    parser.add_argument("--log-to-stdout", action="store_true", help="Also log to stdout")
    args = parser.parse_args()

    level = getattr(logging, args.log_level.upper(), logging.WARNING)
    logging.basicConfig(level=level)
    if args.log_to_stdout:
        logging.getLogger("spinorama").addHandler(logging.StreamHandler())

    # Import headphone metadata
    from datas.headphones import headphones_info

    if not headphones_info:
        logger.info("headphones_info is empty, auto-discovering headphones")
        headphones_info = discover_headphones()

    logger.info("Loaded %d headphones from metadata", len(headphones_info))

    # Build output metadata
    output = build_headphone_metadata(headphones_info)

    # Write headphone.json
    dict_to_json(cpaths.CPATH_DIST_HEADPHONE_JSON, output)

    print(f"Generated {cpaths.CPATH_DIST_HEADPHONE_JSON} with {len(output)} headphones")


if __name__ == "__main__":
    main()
