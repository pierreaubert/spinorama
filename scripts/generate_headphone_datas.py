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

"""Generate datas/headphone_*.py metadata files from ASR API + local filesystem.

Fetches the ASR headphone index, matches entries to locally downloaded CSVs,
and writes split metadata files (headphone_a.py .. headphone_z.py, headphone_0.py .. headphone_9.py)
plus an aggregator (headphones.py).
"""

import argparse
import logging
import os
import string

import requests

import spinorama.constant_paths as cpaths

logger = logging.getLogger("spinorama")

ASR_HEADPHONE_API = "https://www.audiosciencereview.com/asrdata/api/list/headphoneall"

HEADERS = {
    "User-Agent": "spinorama-scraper/1.0 (headphone measurement collector)",
}

DEVICE_TYPE_MAP: dict[str, str] = {
    "Over-Ear": "over-ear",
    "Wireless Over-Ear": "over-ear",
    "On-Ear": "on-ear",
    "In-Ear": "in-ear",
}

SKIP_DEVICE_TYPES = {"Cable", "Cable (IEM)"}

ALL_KEYS = list(string.digits) + list(string.ascii_lowercase)


def fetch_headphone_index() -> list[dict]:
    """Fetch the full headphone review index from the ASR JSON API."""
    resp = requests.get(
        ASR_HEADPHONE_API,
        params={"start": "0", "recperpage": "-1"},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    entries = data.get("headphoneall", [])
    logger.info(
        "ASR API returned %d headphones (total: %d)",
        len(entries),
        data.get("totalRecordCount", len(entries)),
    )
    return entries


def build_headphones_from_api(entries: list[dict]) -> dict:
    """Build headphones dict from API entries matched against local CSV files."""
    headphones: dict = {}

    for entry in entries:
        device_type = entry.get("DeviceType", "")
        if device_type in SKIP_DEVICE_TYPES:
            continue
        shape = DEVICE_TYPE_MAP.get(device_type)
        if shape is None:
            logger.warning(
                "Unknown DeviceType %r for %s %s",
                device_type,
                entry.get("Brand"),
                entry.get("Model"),
            )
            continue

        brand = entry.get("Brand", "").strip()
        model = entry.get("Model", "").strip()
        if not brand or not model:
            continue

        full_name = f"{brand} {model}"
        csv_path = f"{cpaths.CPATH_DATAS_HEADPHONES}/{full_name}/asr/frequency_response.csv"
        if not os.path.exists(csv_path):
            continue

        meas: dict = {
            "origin": "ASR",
            "format": "csv_freq_spl",
        }

        review_url = entry.get("ReviewLink", "")
        if review_url:
            meas["review"] = review_url

        review_date = entry.get("ReviewDate", "").replace("-", "")
        if review_date:
            meas["review_published"] = review_date

        sensitivity = entry.get("Sensitivty_mV_for_94dB_SPL", "")
        if sensitivity:
            try:
                meas["sensitivity_mV_94dB"] = float(sensitivity)
            except ValueError:
                pass

        recommendation = entry.get("Recommendation", "")
        if recommendation:
            meas["recommendation"] = recommendation

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

        headphones[full_name] = hp

    return headphones


def add_filesystem_headphones(headphones: dict) -> None:
    """Add any local headphone directories not found in the API."""
    base = cpaths.CPATH_DATAS_HEADPHONES
    if not os.path.isdir(base):
        return

    for name in sorted(os.listdir(base)):
        if name in headphones:
            continue
        csv_path = os.path.join(base, name, "asr", "frequency_response.csv")
        if not os.path.exists(csv_path):
            continue

        parts = name.split(" ", 1)
        brand = parts[0]
        model = parts[1] if len(parts) > 1 else name

        headphones[name] = {
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
        logger.info("Added %s from filesystem (not in API)", name)


def group_by_key(headphones: dict) -> dict[str, dict]:
    """Group headphones by first character of their name (lowercased)."""
    groups: dict[str, dict] = {k: {} for k in ALL_KEYS}
    for name, hp in sorted(headphones.items()):
        first = name[0].lower()
        if first not in groups:
            logger.warning("Unexpected first character %r in %s, skipping", first, name)
            continue
        groups[first][name] = hp
    return groups


def format_measurement(meas: dict, indent: str) -> list[str]:
    """Format a measurement dict as Python source lines."""
    lines = []
    lines.append(f'{indent}"origin": {repr(meas["origin"])},')
    lines.append(f'{indent}"format": {repr(meas["format"])},')
    for field in ("review", "review_published", "quality", "notes", "recommendation"):
        if field in meas:
            lines.append(f"{indent}{repr(field)}: {repr(meas[field])},")
    if "sensitivity_mV_94dB" in meas:
        lines.append(f'{indent}"sensitivity_mV_94dB": {meas["sensitivity_mV_94dB"]},')
    return lines


def write_headphone_file(key: str, headphones: dict, datas_dir: str) -> None:
    """Write a single headphone_x.py file."""
    filepath = os.path.join(datas_dir, f"headphone_{key}.py")
    lines = [
        "# -*- coding: utf-8 -*-",
        "# generated by generate_headphone_datas.py",
        "",
        "from . import HeadphoneDatabase",
        "",
        f"headphones_info_{key}: HeadphoneDatabase = {{",
    ]

    for name in sorted(headphones.keys()):
        hp = headphones[name]
        lines.append(f"    {repr(name)}: {{")
        lines.append(f'        "brand": {repr(hp["brand"])},')
        lines.append(f'        "model": {repr(hp["model"])},')
        lines.append(f'        "shape": {repr(hp["shape"])},')
        lines.append(f'        "default_measurement": {repr(hp["default_measurement"])},')
        if "price" in hp:
            lines.append(f'        "price": {repr(hp["price"])},')
        lines.append('        "measurements": {')
        for mkey, mval in hp["measurements"].items():
            lines.append(f"            {repr(mkey)}: {{")
            lines.extend(format_measurement(mval, " " * 16))
            lines.append("            },")
        lines.append("        },")
        lines.append("    },")

    lines.append("}")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Wrote %s (%d headphones)", filepath, len(headphones))


def write_aggregator(datas_dir: str) -> None:
    """Write datas/headphones.py that imports and merges all headphone_x.py files."""
    filepath = os.path.join(datas_dir, "headphones.py")
    lines = [
        "# -*- coding: utf-8 -*-",
        "# generated by generate_headphone_datas.py",
        "",
        "from . import HeadphoneDatabase",
        "",
    ]

    for key in ALL_KEYS:
        lines.append(f"from .headphone_{key} import headphones_info_{key}")

    lines.append("")
    lines.append("")
    lines.append("headphones_info: HeadphoneDatabase = (")

    for i, key in enumerate(ALL_KEYS):
        if i == 0:
            lines.append(f"    headphones_info_{key}")
        else:
            lines.append(f"    | headphones_info_{key}")

    lines.append(")")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Wrote %s", filepath)


def main():
    parser = argparse.ArgumentParser(description="Generate datas/headphone_*.py from ASR API")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    # Fetch ASR index
    entries = fetch_headphone_index()

    # Build headphones dict from API
    headphones = build_headphones_from_api(entries)
    logger.info("Matched %d headphones from API to local CSVs", len(headphones))

    # Add any filesystem-only entries
    add_filesystem_headphones(headphones)
    logger.info("Total: %d headphones", len(headphones))

    # Group by first character
    groups = group_by_key(headphones)

    # Write individual files
    datas_dir = os.path.join(os.path.dirname(__file__), "../datas")
    for key in ALL_KEYS:
        write_headphone_file(key, groups[key], datas_dir)

    # Write aggregator
    write_aggregator(datas_dir)

    # Summary
    non_empty = sum(1 for k in ALL_KEYS if groups[k])
    print(f"Generated {len(ALL_KEYS)} headphone_*.py files ({non_empty} non-empty) + headphones.py")
    print(f"Total: {len(headphones)} headphones")


if __name__ == "__main__":
    main()
