#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2026 Pierre Aubert pierre(at)spinorama(dot)org
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

"""Fetch headphone product images via the Brave Image Search API.

For each headphone in the metadata that lacks a picture in datas/pictures/,
search for a product image using Brave and download the best result.

Requires the BRAVE_KEY environment variable to be set.

Usage:
    python3 scripts/headphone_fetch_pictures.py [--force] [--dry-run] [--headphone NAME]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PICTURES_DIR = Path("datas/pictures")
MIN_IMAGE_SIZE = 5_000  # bytes — skip tiny icons/placeholders
REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 1.0  # seconds — respect API rate limits

BRAVE_IMAGE_SEARCH_URL = "https://api.search.brave.com/res/v1/images/search"

logger = logging.getLogger("headphone_pictures")


# ---------------------------------------------------------------------------
# Brave Image Search
# ---------------------------------------------------------------------------


def search_image(api_key: str, brand: str, model: str) -> list[dict]:
    """Search Brave Image Search for a headphone product image.

    Returns a list of image result dicts with 'url', 'thumbnail', 'title', etc.
    """
    query = f"{brand} {model} headphone product photo"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": 20,
        "safesearch": "strict",
    }

    resp = requests.get(
        BRAVE_IMAGE_SEARCH_URL,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 400


def _pick_best_image(results: list[dict]) -> str | None:
    """Pick the highest-resolution product image from Brave search results.

    Filters out SVGs, icons, and tiny images, then returns the largest by pixel area.
    """
    best_url: str | None = None
    best_area = 0

    for result in results:
        props = result.get("properties", {})
        src = props.get("url") or result.get("url", "")
        if not src:
            continue
        path = urlparse(src).path.lower()
        if path.endswith(".svg") or path.endswith(".gif"):
            continue
        if "icon" in path or "logo" in path or "favicon" in path:
            continue
        if "1x1" in path or "pixel" in path:
            continue

        width = result.get("width") or props.get("width") or 0
        height = result.get("height") or props.get("height") or 0
        try:
            w = int(width)
            h = int(height)
        except (ValueError, TypeError):
            w, h = 0, 0

        if w >= MIN_IMAGE_WIDTH and h >= MIN_IMAGE_HEIGHT:
            area = w * h
            if area > best_area:
                best_area = area
                best_url = src
        elif best_url is None and w == 0 and h == 0:
            # No dimensions reported — keep as fallback if nothing better found
            best_url = src

    return best_url


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "spinorama-headphone-pictures/1.0",
            "Accept": "image/*,*/*;q=0.8",
        }
    )
    return session


def download_image(session: requests.Session, url: str, dest: Path) -> bool:
    """Download an image and save to dest. Returns True on success."""
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            logger.debug("  Not an image: %s (%s)", url, content_type)
            return False
        data = resp.content
        if len(data) < MIN_IMAGE_SIZE:
            logger.debug("  Image too small (%d bytes): %s", len(data), url)
            return False
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"
        else:
            ext = ".jpg"
        final_dest = dest.with_suffix(ext)
        final_dest.write_bytes(data)
        logger.info("  Downloaded: %s (%d bytes)", final_dest.name, len(data))
        return True
    except (requests.RequestException, Exception) as e:
        logger.debug("  Failed to download %s: %s", url, e)
        return False


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def picture_exists(brand: str, model: str) -> bool:
    """Check if a picture already exists for this headphone."""
    name = f"{brand} {model}"
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (PICTURES_DIR / f"{name}{ext}").exists():
            return True
    return False


def fetch_headphone_picture(
    api_key: str,
    session: requests.Session,
    brand: str,
    model: str,
    dry_run: bool = False,
) -> bool:
    """Try to fetch a product picture for a headphone. Returns True on success."""
    name = f"{brand} {model}"
    dest = PICTURES_DIR / f"{name}.jpg"

    try:
        results = search_image(api_key, brand, model)
    except requests.RequestException as e:
        logger.error("  Brave API error for %s: %s", name, e)
        return False

    if not results:
        logger.warning("  No search results for %s", name)
        return False

    img_url = _pick_best_image(results)
    if img_url is None:
        logger.warning("  No suitable image found for %s", name)
        return False

    logger.info("  Found image for %s: %s", name, img_url)
    if dry_run:
        logger.info("  [DRY RUN] Would download: %s -> %s", img_url, dest)
        return True

    return download_image(session, img_url, dest)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch headphone product images via Brave Image Search"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch pictures even if they already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't download, just show what would be fetched",
    )
    parser.add_argument(
        "--headphone",
        type=str,
        help="Only fetch picture for this specific headphone (brand + model name)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    api_key = os.environ.get("BRAVE_KEY", "")
    if not api_key:
        logger.error("BRAVE_KEY environment variable is not set")
        sys.exit(1)

    # Add project paths
    sys.path.insert(0, "src")
    sys.path.insert(0, ".")

    # Import headphone metadata
    try:
        from datas.headphones import headphones_info
    except ImportError:
        logger.error("Cannot import headphone metadata. Make sure datas/headphones.py exists.")
        sys.exit(1)

    PICTURES_DIR.mkdir(parents=True, exist_ok=True)

    session = _get_session()
    total = 0
    fetched = 0
    skipped = 0
    failed = 0

    for name, info in sorted(headphones_info.items()):
        if info.get("skip", False):
            continue

        brand = info["brand"]
        model = info["model"]

        if args.headphone and args.headphone != name:
            continue

        total += 1

        if not args.force and picture_exists(brand, model):
            logger.debug("Picture exists for %s, skipping", name)
            skipped += 1
            continue

        if fetch_headphone_picture(api_key, session, brand, model, dry_run=args.dry_run):
            fetched += 1
        else:
            failed += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(
        "Done: %d total, %d fetched, %d skipped (already have picture), %d failed",
        total,
        fetched,
        skipped,
        failed,
    )


if __name__ == "__main__":
    main()
