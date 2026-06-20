# -*- coding: utf-8 -*-
"""Shared paths, constants, and dependency-injection helpers for the API.

Routers import from here so ``main.py`` stays a small bootstrap. The two
module-level caches mirror what the lifespan loads on startup; the
dependency-injection functions also fill them on demand which makes the unit
tests easier (they can ``patch`` ``METADATA`` and call ``load_metadata``
directly).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Generator

from fastapi import FastAPI

API_VERSION = "v1"
CURRENT_VERSION = 0
SOFTWARE_VERSION = f"{API_VERSION}.{CURRENT_VERSION}"

APIFILES = "/var/www/html/spinorama-api"
SPINFILES = "/var/www/html/spinorama-prod/speakers"
METADATA = f"{APIFILES}/assets/metadata.json"
HEADPHONE_METADATA = f"{APIFILES}/assets/headphone.json"
HEADPHONE_FILES = f"{APIFILES}/assets/headphones"

KNOWN_MEASUREMENTS: set[str] = {
    "CEA2034",
    "On Axis",
    "Estimated In-Room Response",
    "Early Reflections",
    "Horizontal Reflections",
    "Vertical Reflections",
    "SPL Horizontal",
    "SPL Horizontal Normalized",
    "SPL Vertical",
    "SPL Vertical Normalized",
    "SPL Horizontal Contour",
    "SPL Horizontal Contour Normalized",
    "SPL Vertical Contour",
    "SPL Vertical Contour Normalized",
    "SPL Horizontal Contour 3D",
    "SPL Horizontal Contour Normalized 3D",
    "SPL Vertical Contour 3D",
    "SPL Vertical Contour Normalized 3D",
    "SPL Horizontal Globe",
    "SPL Horizontal Globe Normalized",
    "SPL Vertical Globe",
    "SPL Vertical Globe Normalized",
    "SPL Horizontal Radar",
    "SPL Vertical Radar",
}

ALIAS_MEASUREMENTS: dict[str, str] = {
    "ON": "On Axis",
    "On-Axis": "On Axis",
    "LW": "Listening Window",
    "ER": "Early Reflections",
    "PIR": "Estimated In-Room Response",
    "Predicted In-Room Response": "Estimated In-Room Response",
}


_metadata_cache: dict | None = None
_headphone_metadata_cache: dict | None = None


def load_metadata() -> Generator[dict, None, None]:
    """FastAPI dependency that yields the cached speaker metadata.

    Loads the JSON file on first call. If the file is missing the process
    exits — the API is useless without it.
    """
    global _metadata_cache
    if _metadata_cache is None:
        if not os.path.exists(METADATA):
            logging.error("Cannot find %s", METADATA)
            sys.exit(1)

        with open(METADATA, "r", encoding="utf8") as f:
            _metadata_cache = json.load(f)

    assert _metadata_cache is not None
    yield _metadata_cache


def load_headphone_metadata() -> Generator[dict, None, None]:
    """FastAPI dependency that yields the cached headphone metadata.

    Headphone metadata is optional: a missing file yields an empty dict.
    """
    global _headphone_metadata_cache
    if _headphone_metadata_cache is None:
        if not os.path.exists(HEADPHONE_METADATA):
            logging.warning("Cannot find %s, headphone endpoints disabled", HEADPHONE_METADATA)
            _headphone_metadata_cache = {}
        else:
            with open(HEADPHONE_METADATA, "r", encoding="utf8") as f:
                _headphone_metadata_cache = json.load(f)

    assert _headphone_metadata_cache is not None
    yield _headphone_metadata_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eagerly populate caches on startup so first requests are fast."""
    global _metadata_cache, _headphone_metadata_cache
    if not os.path.exists(METADATA):
        logging.error("Cannot find %s", METADATA)
        sys.exit(1)

    with open(METADATA, "r", encoding="utf8") as f:
        _metadata_cache = json.load(f)

    if os.path.exists(HEADPHONE_METADATA):
        with open(HEADPHONE_METADATA, "r", encoding="utf8") as f:
            _headphone_metadata_cache = json.load(f)
    else:
        _headphone_metadata_cache = {}

    yield

    _metadata_cache = None
    _headphone_metadata_cache = None


def safe_segment(value: str) -> bool:
    """Return ``True`` if ``value`` is a single safe path segment.

    Rejects empty strings, current/parent directory references, path separators,
    backslashes and NUL bytes.
    """
    if not value or value in (".", ".."):
        return False
    if "\x00" in value or "/" in value or "\\" in value:
        return False
    return ".." not in value


def safe_path(base: str, *parts: str) -> str | None:
    """Join ``parts`` under ``base`` and ensure the result stays inside ``base``.

    Each part is checked for traversal characters before normalising the
    complete path and verifying that the candidate starts with the base
    directory.  Returns the normalised path on success, or ``None`` if the
    path would escape ``base``.
    """
    for part in parts:
        if not safe_segment(part):
            return None
    try:
        norm_base = os.path.normpath(base)
        candidate = os.path.normpath(os.path.join(norm_base, *parts))
    except (OSError, ValueError):
        return None
    separator = os.sep
    if candidate != norm_base and not candidate.startswith(norm_base + separator):
        return None
    return candidate
