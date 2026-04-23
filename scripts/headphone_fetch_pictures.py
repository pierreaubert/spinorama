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

"""Fetch headphone product images from manufacturer websites.

For each headphone in the metadata that lacks a picture in datas/pictures/,
discover the product page URL, find the main product image, and download it.

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
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PICTURES_DIR = Path("datas/pictures")
MIN_IMAGE_SIZE = 5_000  # bytes — skip tiny icons/placeholders
REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 1.0  # seconds — be polite

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

logger = logging.getLogger("headphone_pictures")


# ---------------------------------------------------------------------------
# Brand URL patterns
# ---------------------------------------------------------------------------

def _slug(s: str) -> str:
    return (
        s.strip()
        .lower()
        .replace("®", "")
        .replace("™", "")
        .replace("/", "-")
        .replace("_", "-")
        .replace(" ", "-")
    )


# Brand -> URL template. {model} is replaced with the slugified model name.
BRAND_URL_PATTERNS: dict[str, list[str]] = {
    "Sennheiser": [
        "https://www.sennheiser.com/en-us/catalog/products/headphones/{model}",
        "https://www.sennheiser.com/en-us/{model}",
    ],
    "Sony": [
        "https://electronics.sony.com/audio/headphones/all-headphones/p/{model}",
        "https://www.sony.com/en/headphones/{model}",
    ],
    "Beyerdynamic": [
        "https://www.beyerdynamic.com/{model}.html",
    ],
    "Audio-Technica": [
        "https://www.audio-technica.com/en-us/{model}",
    ],
    "AKG": [
        "https://www.akg.com/headphones/{model}.html",
        "https://www.akg.com/{model}.html",
    ],
    "HiFiMAN": [
        "https://www.hifiman.com/products/detail/{model}",
        "https://store.hifiman.com/index.php/hifiman-{model}.html",
    ],
    "Focal": [
        "https://www.focal.com/en/headphones/{model}",
    ],
    "Dan Clark Audio": [
        "https://danclarkaudio.com/{model}",
    ],
    "Meze Audio": [
        "https://mezeaudio.com/products/{model}",
    ],
    "Moondrop": [
        "https://www.moondroplab.com/en/products/{model}",
    ],
    "Shure": [
        "https://www.shure.com/en-US/products/earphones/{model}",
        "https://www.shure.com/en-US/products/headphones/{model}",
    ],
    "Apple": [
        "https://www.apple.com/{model}/",
    ],
    "Bose": [
        "https://www.bose.com/p/headphones/{model}",
        "https://www.bose.com/p/earbuds/{model}",
    ],
    "JBL": [
        "https://www.jbl.com/headphones/{model}.html",
        "https://www.jbl.com/in-ear-headphones/{model}.html",
    ],
    "Samsung": [
        "https://www.samsung.com/us/mobile-audio/{model}/",
    ],
    "1MORE": [
        "https://usa.1more.com/products/{model}",
    ],
    "FiiO": [
        "https://www.fiio.com/products/{model}",
    ],
    "KZ": [
        "https://kz-audio.com/kz-{model}.html",
    ],
}


def discover_product_urls(brand: str, model: str) -> list[str]:
    """Generate candidate product page URLs for a headphone."""
    b_slug = _slug(brand)
    m_slug = _slug(model)

    urls: list[str] = []

    # Brand-specific patterns first
    if brand in BRAND_URL_PATTERNS:
        for pattern in BRAND_URL_PATTERNS[brand]:
            urls.append(pattern.format(model=m_slug))

    # Generic patterns
    domains = [
        f"https://www.{b_slug}.com",
        f"https://{b_slug}.com",
    ]
    for d in domains:
        urls.extend([
            f"{d}/products/{m_slug}",
            f"{d}/product/{m_slug}",
            f"{d}/headphones/{m_slug}",
            f"{d}/{m_slug}",
        ])

    return urls


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

def _is_valid_image_url(url: str) -> bool:
    """Check if a URL looks like a product image (not an icon/logo/svg)."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    # Skip SVGs, tiny icons, tracking pixels
    if path.endswith(".svg") or path.endswith(".gif"):
        return False
    if "icon" in path or "logo" in path or "favicon" in path:
        return False
    if "1x1" in path or "pixel" in path:
        return False
    return True


def find_product_image(html: str, base_url: str) -> Optional[str]:
    """Find the main product image URL from an HTML page.

    Heuristics in priority order:
    1. og:image meta tag — used by virtually all major brands
    2. <img> inside product/hero/gallery containers
    3. First large <img> with product-related attributes
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. og:image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        img_url = og["content"]
        if _is_valid_image_url(img_url):
            return urljoin(base_url, img_url)

    # 2. twitter:image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        img_url = tw["content"]
        if _is_valid_image_url(img_url):
            return urljoin(base_url, img_url)

    # 3. Product image containers
    selectors = [
        'img[class*="product-image"]',
        'img[class*="product_image"]',
        'div[class*="product-image"] img',
        'div[class*="product-gallery"] img',
        'div[class*="hero"] img',
        'div[class*="product-media"] img',
        'section[class*="product"] img',
        '[data-product-image] img',
        'img[itemprop="image"]',
    ]
    for selector in selectors:
        img = soup.select_one(selector)
        if img:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and _is_valid_image_url(src):
                return urljoin(base_url, src)

    # 4. Largest explicit-size image
    best_img = None
    best_area = 0
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src or not _is_valid_image_url(src):
            continue
        width = img.get("width", "0")
        height = img.get("height", "0")
        try:
            w = int(str(width).replace("px", ""))
            h = int(str(height).replace("px", ""))
            area = w * h
            if area > best_area and w >= 200 and h >= 200:
                best_area = area
                best_img = urljoin(base_url, src)
        except (ValueError, TypeError):
            continue

    return best_img


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


def fetch_page(session: requests.Session, url: str) -> Optional[str]:
    """Fetch an HTML page, return content or None on failure."""
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type and "text" not in content_type:
            return None
        return resp.text
    except (requests.RequestException, Exception) as e:
        logger.debug("  Failed to fetch %s: %s", url, e)
        return None


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
        # Determine extension from content-type
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"
        else:
            ext = ".jpg"
        # If dest has a different extension, adjust
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
    session: requests.Session,
    brand: str,
    model: str,
    dry_run: bool = False,
) -> bool:
    """Try to fetch a product picture for a headphone. Returns True on success."""
    name = f"{brand} {model}"
    dest = PICTURES_DIR / f"{name}.jpg"

    urls = discover_product_urls(brand, model)
    logger.info("Trying %d URLs for %s", len(urls), name)

    for url in urls:
        logger.debug("  Trying: %s", url)
        html = fetch_page(session, url)
        if html is None:
            continue

        img_url = find_product_image(html, url)
        if img_url is None:
            logger.debug("  No product image found on: %s", url)
            continue

        logger.info("  Found image: %s", img_url)
        if dry_run:
            logger.info("  [DRY RUN] Would download: %s -> %s", img_url, dest)
            return True

        if download_image(session, img_url, dest):
            return True

    logger.warning("  No picture found for %s", name)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Fetch headphone product images from manufacturer websites"
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

    # Add project paths
    sys.path.insert(0, "src")
    sys.path.insert(0, ".")

    # Import headphone metadata
    try:
        from datas.headphone_metadata import headphones_info
    except ImportError:
        logger.error(
            "Cannot import headphone metadata. "
            "Make sure datas/headphone_metadata.py exists."
        )
        sys.exit(1)

    PICTURES_DIR.mkdir(parents=True, exist_ok=True)

    session = _get_session()
    total = 0
    fetched = 0
    skipped = 0
    failed = 0

    for name, info in headphones_info.items():
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

        if fetch_headphone_picture(session, brand, model, dry_run=args.dry_run):
            fetched += 1
        else:
            failed += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(
        "Done: %d total, %d fetched, %d skipped, %d failed",
        total,
        fetched,
        skipped,
        failed,
    )


if __name__ == "__main__":
    main()
