# -*- coding: utf-8 -*-
"""FastAPI bootstrap. Routes live in ``api.routers``; constants in ``api.state``."""

from __future__ import annotations

# Re-exports for back-compat (tests and external callers do
# ``from api.main import app, METADATA, SPINFILES, load_metadata, glob``).
# Removing these would force every consumer to know the new layout.
from glob import glob

from fastapi import FastAPI

from .state import (
    API_VERSION,
    ALIAS_MEASUREMENTS,
    APIFILES,
    HEADPHONE_FILES,
    HEADPHONE_METADATA,
    KNOWN_MEASUREMENTS,
    METADATA,
    SOFTWARE_VERSION,
    SPINFILES,
    lifespan,
    load_headphone_metadata,
    load_metadata,
)
from .routers import headphone, speaker, validation


openapi_tags = [
    {"name": "speaker", "description": "Speaker measurements and metadata"},
    {"name": "headphone", "description": "Headphone measurements and metadata"},
    {"name": "validation", "description": "Data validation endpoints"},
]


app = FastAPI(
    debug=False,
    title="Spinorama API",
    version=SOFTWARE_VERSION,
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

app.include_router(speaker.router)
app.include_router(headphone.router)
app.include_router(validation.router)


__all__ = [
    "API_VERSION",
    "SOFTWARE_VERSION",
    "app",
]
