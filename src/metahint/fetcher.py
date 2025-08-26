#!/usr/bin/env python3

from __future__ import annotations

"""HTTP/HTML fetch helpers.

Supports:
- Local file loading via `fetch_local_html`
- Remote URL fetching via `fetch_url` using `requests` by default
- Optional Playwright engine for dynamic websites (if installed)
"""

from pathlib import Path
from typing import Literal, Tuple

import contextlib

try:  # Optional dependency
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:  # pragma: no cover - optional
    sync_playwright = None  # type: ignore

import requests


def fetch_local_html(path: Path) -> Tuple[str, str]:
    """Load HTML content from disk.

    Returns a tuple of (content, mime).
    """
    text = path.read_text(encoding="utf-8")
    return text, "text/html"


def fetch_url(
    url: str, engine: Literal["auto", "requests", "playwright"] = "auto"
) -> Tuple[str, str]:
    """Fetch a remote URL and return (content, mime).

    - engine="requests": use requests.get
    - engine="playwright": use Playwright (if available), else raise
    - engine="auto": try requests first, fall back to Playwright if available
    """
    if engine not in {"auto", "requests", "playwright"}:
        raise ValueError(f"Unknown engine: {engine}")

    def _via_requests() -> Tuple[str, str]:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "text/html").split(";")[0]
        return resp.text, ctype

    def _via_playwright() -> Tuple[str, str]:  # pragma: no cover - exercised only when installed
        if sync_playwright is None:
            raise RuntimeError("Playwright not installed")
        with sync_playwright() as p:  # type: ignore[misc]
            browser = p.firefox.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle")
                html = page.content()
            finally:
                with contextlib.suppress(Exception):
                    browser.close()
        return html, "text/html"

    if engine == "requests":
        return _via_requests()
    if engine == "playwright":
        return _via_playwright()

    # auto
    with contextlib.suppress(Exception):
        return _via_requests()
    return _via_playwright()
