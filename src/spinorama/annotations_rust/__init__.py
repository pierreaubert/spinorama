"""Package-local shim for the optional Rust annotation-layout extension."""

from __future__ import annotations

import importlib
import sys

# Maturin builds ``annotations_rust`` as a top-level module.  When this
# package is imported first, temporarily hide its parent from sys.path so the
# import resolver can find that extension instead of recursing into this shim.
_package_dir = __file__.rsplit("/__init__.py", 1)[0]
_parent_dir = _package_dir.rsplit("/spinorama", 1)[0]
_removed = [
    path for path in sys.path if path == _parent_dir or path.rstrip("/").endswith("/spinorama")
]
try:
    sys.path[:] = [path for path in sys.path if path not in _removed]
    _extension = importlib.import_module("annotations_rust")
finally:
    sys.path[:0] = _removed

c_place_annotations = _extension.c_place_annotations

__all__ = ["c_place_annotations"]
