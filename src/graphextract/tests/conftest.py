# -*- coding: utf-8 -*-
"""Shared pytest fixtures: import the canonical pipeline from any cwd."""

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Optional sibling checkout providing the spinorama loaders (parser interop).
SPINORAMA_SRC = Path(os.environ.get("SPINORAMA_SRC", "/Users/pierre/src/spinorama/src"))
if SPINORAMA_SRC.is_dir() and str(SPINORAMA_SRC) not in sys.path:
    sys.path.insert(0, str(SPINORAMA_SRC))
