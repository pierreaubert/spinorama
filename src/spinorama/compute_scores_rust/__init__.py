"""
Shim module for `spinorama.compute_scores_rust`.

It attempts to load a package-local compiled extension (when present), and
falls back to the top-level `compute_scores_rust` wheel installed in the
active environment. This ensures tests importing `spinorama.compute_scores_rust`
get the correct Rust-accelerated functions regardless of installation mode.
"""

from __future__ import annotations

import importlib
import sys

# When PYTHONPATH includes src/spinorama, a plain ``import compute_scores_rust``
# resolves to *this* shim instead of the installed wheel. To break the cycle we
# temporarily hide the conflicting path entries, import the real extension, then
# restore the path and re-export everything.

_ext = None

try:
    from . import compute_scores_rust as _ext  # type: ignore[attr-defined]
except Exception:
    pass

if _ext is None:
    _this_pkg = __file__.rsplit("/__init__.py", 1)[0]
    _blocked = [p for p in sys.path if p == _this_pkg or p.endswith("/spinorama")]
    _saved = sys.path[:]
    try:
        for _b in _blocked:
            if _b in sys.path:
                sys.path.remove(_b)
        if "compute_scores_rust" in sys.modules:
            del sys.modules["compute_scores_rust"]
        _ext = importlib.import_module("compute_scores_rust")
    except Exception:
        _ext = None
    finally:
        sys.path[:] = _saved

if _ext is not None:
    _names = [n for n in dir(_ext) if not n.startswith("_")]
    globals().update({n: getattr(_ext, n) for n in _names})
    __all__ = _names
else:
    __all__ = []
