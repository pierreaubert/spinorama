# SPDX-License-Identifier: MIT
from __future__ import annotations

"""URL discovery for official product pages.

This is a minimal stub to keep the package runnable and testable without
network calls. It can be extended to use search APIs (Bing, Google CSE,
SerpAPI) and brand-specific URL patterns.
"""

from typing import List


def _slug(s: str) -> str:
    return (
        s.strip()
        .lower()
        .replace("®", "")
        .replace("™", "")
        .replace("\u00ae", "")
        .replace("\u2122", "")
        .replace("/", "-")
        .replace("_", "-")
        .replace(" ", "-")
    )


def discover_urls(brand: str, model: str) -> List[str]:
    """Return candidate URLs for a given brand and model.

    Heuristic, no-network strategy producing likely candidates:
    - Brand homepage and product catalog guesses
    - Product detail guesses (common paths)
    - Manuals/support guesses (PDF as well)
    - Public search engine query URLs (left to fetcher/CLI to decide)
    """
    b = _slug(brand)
    m = _slug(model)

    # base domains to try
    domains = [
        f"https://{b}.com",
        f"https://www.{b}.com",
        f"https://{b}audio.com",
        f"https://www.{b}audio.com",
        f"https://{b}.co.uk",
        f"https://www.{b}.co.uk",
    ]

    candidates: List[str] = []

    for d in domains:
        candidates.extend(
            [
                d,
                f"{d}/products",
                f"{d}/product",
                f"{d}/speakers",
                f"{d}/speaker",
                f"{d}/support",
                f"{d}/manuals",
                f"{d}/downloads",
                # product detail guesses
                f"{d}/products/{m}",
                f"{d}/product/{m}",
                f"{d}/speakers/{m}",
                f"{d}/speaker/{m}",
                f"{d}/en/{m}",
                f"{d}/{m}",
                # manual guesses
                f"{d}/manual/{m}.pdf",
                f"{d}/manuals/{m}.pdf",
                f"{d}/downloads/{m}.pdf",
                f"{d}/media/{m}.pdf",
            ]
        )

    # Generic web search URLs (non-API)
    candidates.extend(
        [
            f"https://www.google.com/search?q={brand}+{model}+site:{b}.com",
            f"https://duckduckgo.com/?q={brand}+{model}+site:{b}.com",
            f"https://duckduckgo.com/?q={brand}+{model}+manual",
        ]
    )

    # Deduplicate preserving order
    seen = set()
    ordered: List[str] = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered
