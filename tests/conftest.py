"""Pytest configuration for Qt tests.

For headless CI on macOS, the 'offscreen' platform can hang. Force the
'minimal' platform before any Qt modules are imported.
"""
from __future__ import annotations

import os

# Set once, don't override if user explicitly set it when invoking pytest
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

# Additional stability tweaks for macOS headless
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
os.environ.setdefault("QT_OPENGL", "software")

# Avoid native macOS menu bar integration which can crash with headless plugins
try:
    from PySide6.QtCore import Qt, QCoreApplication  # type: ignore[reportMissingImports]

    # Must be set before QApplication is instantiated (pytest-qt will create it on demand)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
except Exception:
    # If PySide6 is not available or fails to import yet, ignore; tests that need Qt will import it later
    pass
