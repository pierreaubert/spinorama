# -*- coding: utf-8 -*-
# pyright: reportAttributeAccessIssue=false
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Single source of truth for the native (Rust → Cython) compute extensions.

Prefer the Rust extension when available; fall back to the Cython build.
Callers import the public names from this module instead of repeating the
try/except dance at every call site.
"""

# The Rust shim re-exports via a runtime ``globals().update`` and the Cython
# build has no .pyi stub, so pyright cannot see either set of names
# statically. The annotations below tell type checkers what to expect; the
# actual bindings come from the imports.
from typing import Any, Callable

c_cea2034: Callable[..., Any]
c_score_peq_approx: Callable[..., Any]

try:
    from spinorama.compute_scores_rust import (  # type: ignore[no-redef]
        c_cea2034,
        c_score_peq_approx,
    )
except ImportError:
    from spinorama.compute_scores_cython.compute_scores_cython import (  # type: ignore[no-redef]
        c_cea2034,
        c_score_peq_approx,
    )

__all__ = ["c_cea2034", "c_score_peq_approx"]
