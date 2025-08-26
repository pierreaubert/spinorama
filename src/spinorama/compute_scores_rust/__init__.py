"""
Shim module for `spinorama.compute_scores_rust`.

It attempts to load a package-local compiled extension (when present), and
falls back to the top-level `compute_scores_rust` wheel installed in the
active environment. This ensures tests importing `spinorama.compute_scores_rust`
get the correct Rust-accelerated functions regardless of installation mode.
"""
from __future__ import annotations

# Prefer a local extension built into this package directory (e.g.,
# `spinorama/compute_scores_rust/compute_scores_rust.*.so`). If not present,
# fall back to the site-packages provided module name `compute_scores_rust`.
try:
    from . import compute_scores_rust as _ext  # type: ignore[attr-defined]
except Exception:
    # Fallback: proxy everything from the installed extension module.
    from compute_scores_rust import *  # noqa: F401,F403
    try:  # Build a stable __all__ for introspection and linting
        import compute_scores_rust as _ext2  # type: ignore

        __all__ = [n for n in dir(_ext2) if not n.startswith("_")]
    except Exception:  # pragma: no cover - extremely unlikely
        __all__ = []
else:
    # Re-export public names from the local extension as top-level symbols.
    _names = [n for n in dir(_ext) if not n.startswith("_")]
    globals().update({n: getattr(_ext, n) for n in _names})
    __all__ = _names
