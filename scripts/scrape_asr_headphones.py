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

"""Scrape ASR headphone reviews via the asrdata JSON API and download measurement CSVs.

Uses https://www.audiosciencereview.com/forum/index.php?pages/Reviews/ which embeds
an iframe to https://www.audiosciencereview.com/asrdata/ backed by a JSON API.

The API endpoint https://www.audiosciencereview.com/asrdata/api/list/headphoneall
returns structured data (brand, model, type, price, review URL, date) for all
headphone reviews. Each review thread URL is a direct link.

Attachment selection strategy:
  1. Collect all CSV/TXT/ZIP attachments from the review thread (up to 10)
  2. Score each by filename (prefer "frequency response", skip "eq"/"apo")
  3. Download in priority order; detect ZIPs by magic bytes, not extension
  4. Validate each candidate with parse_headphone_csv
  5. Save the first file that parses as valid frequency response data

Rate-limited to 1 request per 10 seconds for page loads, 2 seconds between
attachment downloads.
"""

import argparse
import io
import logging
import os
import tempfile
import time
import zipfile

import requests
from bs4 import BeautifulSoup

from load_headphone_csv import parse_headphone_csv

logger = logging.getLogger("spinorama")

ASR_BASE_URL = "https://www.audiosciencereview.com/forum"
ASR_HEADPHONE_API = "https://www.audiosciencereview.com/asrdata/api/list/headphoneall"

PAGE_DELAY_S = 10.0
DOWNLOAD_DELAY_S = 2.0
MAX_ATTACHMENTS_TO_TRY = 10

# Absolute path to datas/headphones, independent of cwd. The script lives at
# <root>/scripts/scrape_asr_headphones.py, so the project root is two
# os.path.dirname() calls up.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADPHONES_ROOT = os.path.join(_PROJECT_ROOT, "datas", "headphones")

HEADERS = {
    "User-Agent": "spinorama-scraper/1.0 (headphone measurement collector)",
}

# Map ASR DeviceType to HeadphoneShape values
DEVICE_TYPE_MAP: dict[str, str] = {
    "Over-Ear": "over-ear",
    "Wireless Over-Ear": "over-ear",
    "On-Ear": "on-ear",
    "In-Ear": "in-ear",
}

# DeviceTypes that are accessories, not headphones
SKIP_DEVICE_TYPES = {"Cable", "Cable (IEM)"}

# --- Filename scoring ---
# (substring, score_delta) matched case-insensitively against filenames.
# Higher total score = more likely to be raw frequency response data.

_FR_POSITIVE = [
    ("frequency response", 10),
    ("frequency_response", 10),
    ("freq response", 8),
    ("measurement", 5),
    ("raw", 3),
]

_FR_NEGATIVE = [
    ("preamp", -10),
    ("parametric", -8),
    ("equalization", -8),
    ("apo eq", -10),
    (" eq ", -8),
    (" eq.", -8),
    ("_eq_", -8),
    ("_eq.", -8),
    (" apo ", -8),
    ("harman", -5),
    ("flat@hf", -5),
    ("flat ", -5),
    ("target", -5),
    ("correction", -5),
    ("score", -3),
]


def _score_filename(filename: str) -> int:
    """Score a filename for likelihood of being raw frequency response data."""
    name = f" {filename.lower()} "
    score = 0
    for keyword, pts in _FR_POSITIVE:
        if keyword in name:
            score += pts
    for keyword, pts in _FR_NEGATIVE:
        if keyword in name:
            score += pts
    if filename.lower().endswith(".csv"):
        score += 1
    return score


# --- Content detection ---


def _is_zip_content(content: bytes) -> bool:
    return len(content) >= 4 and content[:4] == b"PK\x03\x04"


def _is_apo_eq_text(text: str) -> bool:
    """Detect APO parametric EQ files (common false positive on ASR threads)."""
    first_chunk = text[:500].lower()
    if "preamp:" in first_chunk:
        return True
    for line in text.split("\n", 12)[:10]:
        stripped = line.strip().lower()
        if stripped.startswith("filter") and any(
            k in stripped for k in ("pk", "lsh", "hsh", "ls ", "hs ", "no ")
        ):
            return True
    return False


def _extract_texts_from_zip(content: bytes) -> list[tuple[str, str]]:
    """Extract CSV/TXT text files from a ZIP archive.

    Returns [(inner_filename, text_content), ...] sorted by FR-likelihood score.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        return []

    results = []
    for name in zf.namelist():
        if name.startswith("__MACOSX"):
            continue
        lower = name.lower()
        if not lower.endswith((".csv", ".txt")):
            continue
        try:
            text = zf.read(name).decode("utf-8", errors="replace")
            results.append((name, text))
        except Exception:
            pass

    results.sort(key=lambda x: _score_filename(x[0]), reverse=True)
    return results


def _validate_fr_text(text: str) -> bool:
    """Return True if *text* parses as a valid frequency response CSV."""
    fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        old_level = logger.level
        logger.setLevel(logging.CRITICAL)
        try:
            df = parse_headphone_csv(tmp_path)
        finally:
            logger.setLevel(old_level)
        if df is None or len(df) < 10:
            return False
        freq_col = "Freq_L" if "Freq_L" in df.columns else "Freq"
        if df[freq_col].max() < 1000:
            return False
        return True
    finally:
        os.unlink(tmp_path)


# --- Network helpers ---


def fetch_headphone_index() -> list[dict]:
    """Fetch the full headphone review index from the ASR JSON API.

    Returns a list of dicts with keys:
        DeviceType, Brand, Model, Sensitivty_mV_for_94dB_SPL,
        Price_Each_USD, Recommendation, ReviewDate, ReviewLink
    """
    try:
        resp = requests.get(
            ASR_HEADPHONE_API,
            params={"start": "0", "recperpage": "-1"},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Failed to fetch headphone index: %s", e)
        return []

    entries = data.get("headphoneall", [])
    total = data.get("totalRecordCount", len(entries))
    logger.info("ASR API returned %d headphones (total: %d)", len(entries), total)
    return entries


def _find_attachments(thread_url: str) -> list[tuple[str, str]]:
    """Find file attachments in a review thread.

    Returns [(display_filename, url), ...] sorted by FR-likelihood score (best first).
    """
    try:
        resp = requests.get(thread_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch %s: %s", thread_url, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    attachments: list[tuple[str, str]] = []

    for link in soup.select("a.file-preview"):
        href = str(link.get("href", ""))
        filename = link.get_text(strip=True)
        if not filename.lower().endswith((".csv", ".txt", ".zip")):
            continue

        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = f"https://www.audiosciencereview.com{href}"
        else:
            full_url = f"{ASR_BASE_URL}/{href}"

        attachments.append((filename, full_url))

    attachments.sort(key=lambda x: _score_filename(x[0]), reverse=True)
    return attachments


def _try_extract_fr(content: bytes, filename: str) -> str | None:
    """Try to extract valid FR CSV text from downloaded content.

    Handles plain-text CSVs, and ZIP archives (detected by magic bytes,
    not by file extension).  Returns the validated text, or None.
    """
    if _is_zip_content(content):
        logger.info("  detected ZIP content in %s", filename)
        extracted = _extract_texts_from_zip(content)
        if not extracted:
            logger.info("  no CSV/TXT inside ZIP %s", filename)
            return None

        for inner_name, text in extracted:
            if _is_apo_eq_text(text):
                logger.info("  skipping EQ file inside ZIP: %s", inner_name)
                continue
            if _validate_fr_text(text):
                logger.info("  valid FR in ZIP: %s -> %s", filename, inner_name)
                return text
            logger.info("  invalid FR in ZIP entry: %s", inner_name)
        return None

    # Plain text
    text = content.decode("utf-8", errors="replace")

    if _is_apo_eq_text(text):
        logger.info("  skipping EQ file: %s", filename)
        return None

    if _validate_fr_text(text):
        logger.info("  valid FR: %s", filename)
        return text

    logger.info("  invalid FR: %s", filename)
    return None


def _download_best_fr(
    attachments: list[tuple[str, str]],
    max_downloads: int = MAX_ATTACHMENTS_TO_TRY,
) -> str | None:
    """Try attachments in priority order, return the first valid FR CSV text."""
    limit = min(len(attachments), max_downloads)
    for i, (filename, url) in enumerate(attachments[:limit]):
        if i > 0:
            time.sleep(DOWNLOAD_DELAY_S)

        logger.info(
            "  trying %d/%d: %s (score=%d)",
            i + 1,
            limit,
            filename,
            _score_filename(filename),
        )

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("  download failed %s: %s", url, e)
            continue

        text = _try_extract_fr(resp.content, filename)
        if text is not None:
            return text

    return None


# --- Validity check for existing files ---


def has_valid_csv(name: str) -> bool:
    """Return True if *name* already has a valid frequency response CSV on disk."""
    csv_path = os.path.join(HEADPHONES_ROOT, name, "asr", "frequency_response.csv")
    if not os.path.exists(csv_path):
        return False
    old_level = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        df = parse_headphone_csv(csv_path)
    finally:
        logger.setLevel(old_level)
    return df is not None and len(df) >= 10


# --- Main scrape loop ---


def scrape_asr_headphones(
    dry_run: bool = False,
    rescrape_bad: bool = False,
) -> list[dict]:
    """Scrape ASR headphone reviews.

    By default only headphones not already present in the local dataset (no
    directory under ``datas/headphones/``) are scanned. When *rescrape_bad* is
    True, headphones whose existing CSV fails validation are re-scraped (the
    bad file is removed first).
    """
    entries = fetch_headphone_index()
    if not entries:
        return []

    all_results: list[dict] = []

    for entry in entries:
        device_type = entry.get("DeviceType", "")

        if device_type in SKIP_DEVICE_TYPES:
            logger.info(
                "Skipping accessory: %s %s (%s)",
                entry.get("Brand"),
                entry.get("Model"),
                device_type,
            )
            continue

        shape = DEVICE_TYPE_MAP.get(device_type)
        if shape is None:
            logger.warning(
                "Unknown DeviceType %r for %s %s, skipping",
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
        review_url = entry.get("ReviewLink", "")
        review_date = entry.get("ReviewDate", "").replace("-", "")
        price = entry.get("Price_Each_USD", "")
        headphone_dir = os.path.join(HEADPHONES_ROOT, full_name)
        csv_path = os.path.join(headphone_dir, "asr", "frequency_response.csv")

        # Decide whether to process this headphone
        if rescrape_bad:
            if has_valid_csv(full_name):
                logger.info("Skipping %s (valid CSV)", full_name)
                continue
            if os.path.exists(csv_path):
                logger.info("Removing bad CSV for %s", full_name)
                os.unlink(csv_path)
        else:
            if os.path.isdir(headphone_dir):
                logger.info("Skipping %s (already in dataset)", full_name)
                continue

        result = {
            "brand": brand,
            "model": model,
            "shape": shape,
            "url": review_url,
            "date": review_date,
            "price": price,
            "csv_downloaded": False,
        }

        if dry_run:
            logger.info("[DRY RUN] Would process: %s", full_name)
            all_results.append(result)
            continue

        # Rate limit before page load
        time.sleep(PAGE_DELAY_S)

        # Find and score attachments
        attachments = _find_attachments(review_url)

        if not attachments:
            logger.info("No attachments for %s", full_name)
            all_results.append(result)
            continue

        logger.info("Found %d attachments for %s", len(attachments), full_name)

        # Try to find the best valid FR CSV
        fr_text = _download_best_fr(attachments)

        if fr_text is not None:
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(fr_text)
            result["csv_downloaded"] = True
            logger.info("Saved FR for %s", full_name)
        else:
            logger.info(
                "No valid FR found in %d attachments for %s",
                len(attachments),
                full_name,
            )

        all_results.append(result)

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Scrape ASR headphone reviews")
    parser.add_argument(
        "--dry-run", action="store_true", help="List new headphones without downloading"
    )
    parser.add_argument(
        "--rescrape-bad",
        action="store_true",
        help="Re-scrape headphones whose existing CSV fails validation",
    )
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    results = scrape_asr_headphones(
        dry_run=args.dry_run,
        rescrape_bad=args.rescrape_bad,
    )

    downloaded = sum(1 for r in results if r["csv_downloaded"])
    print(f"\nProcessed {len(results)} headphones ({downloaded} CSVs downloaded)")
    for r in results:
        status = "CSV" if r["csv_downloaded"] else "no-csv"
        print(f"  [{status}] {r['brand']} {r['model']} ({r['shape']}) - {r['url']}")


if __name__ == "__main__":
    main()
