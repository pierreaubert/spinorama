# SPDX-License-Identifier: MIT
"""
Lightweight package to discover, fetch and parse loudspeaker specifications
from official product pages or spec sheets, and emit normalized JSON with
confidence scores.

This initial scaffold focuses on HTML parsing of common "Specifications"
sections (key/value) and a minimal CLI. PDF and discovery modules are
intentionally minimal and can be expanded.
"""

from .schema import SpeakerSpecs, ConfidenceValue, Range  # noqa: F401
