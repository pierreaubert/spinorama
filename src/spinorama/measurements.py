# -*- coding: utf-8 -*-
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

"""Typed container for one speaker's worth of measurements.

The legacy storage type is ``DataSpeaker = dict[str, pd.DataFrame]``. Frames
are stored twice: once melted (``"CEA2034"``) and once wide
(``"CEA2034_unmelted"``). Consumers have to memorise the suffix convention
and re-shape on the fly. :class:`Measurements` stores each frame **once** in
wide form (which is what every computation wants); ``to_legacy_dict`` rebuilds
the dual-shape dict at the boundary so downstream code keeps working
unchanged while migration proceeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, ClassVar

import pandas as pd

from spinorama.filters.peq import Peq
from spinorama.misc import graph_melt, graph_unmelt


# Mapping of dataclass-field name → legacy dict key (without ``_unmelted``).
_FRAME_FIELD_TO_LEGACY_KEY: dict[str, str] = {
    "h_spl": "SPL Horizontal",
    "v_spl": "SPL Vertical",
    "cea2034": "CEA2034",
    "cea2034_normalized": "CEA2034 Normalized",
    "on_axis": "On Axis",
    "eir": "Estimated In-Room Response",
    "eir_normalized": "Estimated In-Room Response Normalized",
    "early_reflections": "Early Reflections",
    "horizontal_reflections": "Horizontal Reflections",
    "vertical_reflections": "Vertical Reflections",
}

# Frames the legacy dict exposes only in wide form (no melted key).
_FRAME_FIELD_TO_LEGACY_KEY_UNMELTED_ONLY: dict[str, str] = {
    "h_spl_normalized": "SPL Horizontal_normalized_unmelted",
    "v_spl_normalized": "SPL Vertical_normalized_unmelted",
}


@dataclass(frozen=True)
class Sensitivity:
    """Sensitivity reading derived from on-axis SPL at the measurement distance."""

    spl: float
    distance: float
    spl_at_1m: float


@dataclass
class Measurements:
    """One speaker's measurements in wide form.

    Each ``DataFrame`` field is either ``None`` (not measured / not derived
    yet) or a wide-form frame with a ``Freq`` column and one column per
    measurement curve. Use :meth:`to_legacy_dict` to obtain the historical
    ``DataSpeaker`` dict shape (both melted and unmelted views).
    """

    # H/V SPL sweeps — the raw measurements from the loaders.
    h_spl: pd.DataFrame | None = None
    v_spl: pd.DataFrame | None = None
    h_spl_normalized: pd.DataFrame | None = None
    v_spl_normalized: pd.DataFrame | None = None

    # CEA2034 spin and its on-axis-normalised twin.
    cea2034: pd.DataFrame | None = None
    cea2034_normalized: pd.DataFrame | None = None

    # Single-curve derived frames.
    on_axis: pd.DataFrame | None = None
    eir: pd.DataFrame | None = None
    eir_normalized: pd.DataFrame | None = None
    early_reflections: pd.DataFrame | None = None
    horizontal_reflections: pd.DataFrame | None = None
    vertical_reflections: pd.DataFrame | None = None

    # Scalars + filter.
    sensitivity: Sensitivity | None = None
    eq: Peq | None = None

    # Extra entries that came in from the legacy dict and we don't model yet.
    # Preserved verbatim by ``to_legacy_dict`` so a round-trip through this
    # class is lossless during the migration.
    _extras: dict[str, Any] = field(default_factory=dict)

    # Memoised, optim-only scratch space (e.g. the precomputed CEA2034 score
    # inputs used by autoeq's hot path). Never serialised.
    _score_cache: Any = field(default=None, repr=False, compare=False)

    # All the dataclass field names that hold a DataFrame, in legacy-dict order.
    _FRAME_FIELDS: ClassVar[tuple[str, ...]] = (
        "h_spl",
        "v_spl",
        "h_spl_normalized",
        "v_spl_normalized",
        "cea2034",
        "cea2034_normalized",
        "on_axis",
        "eir",
        "eir_normalized",
        "early_reflections",
        "horizontal_reflections",
        "vertical_reflections",
    )

    @classmethod
    def from_legacy_dict(cls, data: dict[str, Any] | None) -> Measurements:
        """Build a :class:`Measurements` from a legacy ``DataSpeaker`` dict.

        Each known frame is taken from its wide-form key when present and
        otherwise unmelted from the melted key. Any unrecognised key is
        preserved in ``_extras`` so the inverse :meth:`to_legacy_dict` is a
        no-op for callers that don't touch the typed view.
        """
        m = cls()
        if not data:
            return m

        consumed: set[str] = set()

        for field_name, legacy_key in _FRAME_FIELD_TO_LEGACY_KEY.items():
            wide_key = f"{legacy_key}_unmelted"
            melted_key = legacy_key
            wide = data.get(wide_key)
            if isinstance(wide, pd.DataFrame):
                setattr(m, field_name, wide)
                consumed.add(wide_key)
                if melted_key in data:
                    consumed.add(melted_key)
                continue
            melted = data.get(melted_key)
            if isinstance(melted, pd.DataFrame):
                setattr(m, field_name, graph_unmelt(melted))
                consumed.add(melted_key)

        for field_name, legacy_key in _FRAME_FIELD_TO_LEGACY_KEY_UNMELTED_ONLY.items():
            value = data.get(legacy_key)
            if isinstance(value, pd.DataFrame):
                setattr(m, field_name, value)
                consumed.add(legacy_key)

        if "sensitivity" in data and "sensitivity_distance" in data and "sensitivity_1m" in data:
            m.sensitivity = Sensitivity(
                spl=float(data["sensitivity"]),
                distance=float(data["sensitivity_distance"]),
                spl_at_1m=float(data["sensitivity_1m"]),
            )
            consumed.update({"sensitivity", "sensitivity_distance", "sensitivity_1m"})

        if "eq" in data:
            m.eq = data["eq"]
            consumed.add("eq")

        # Anything else (unmelted keys we didn't model, debug entries, …)
        # rides along untouched.
        for k, v in data.items():
            if k in consumed:
                continue
            m._extras[k] = v
        return m

    def to_legacy_dict(self) -> dict[str, Any]:
        """Render as the dict that ``DataSpeaker``-shaped consumers expect.

        For every modelled frame ``F`` the result contains both ``F`` (melted)
        and ``F_unmelted`` (wide). Sensitivity is exploded into the three
        scalar keys; the optional ``eq`` is passed through; and any entries
        captured in ``_extras`` are appended last.
        """
        out: dict[str, Any] = {}

        for field_name, legacy_key in _FRAME_FIELD_TO_LEGACY_KEY.items():
            frame = getattr(self, field_name)
            if frame is None:
                continue
            out[f"{legacy_key}_unmelted"] = frame
            out[legacy_key] = graph_melt(frame)

        for field_name, legacy_key in _FRAME_FIELD_TO_LEGACY_KEY_UNMELTED_ONLY.items():
            frame = getattr(self, field_name)
            if frame is not None:
                out[legacy_key] = frame

        if self.sensitivity is not None:
            out["sensitivity"] = self.sensitivity.spl
            out["sensitivity_distance"] = self.sensitivity.distance
            out["sensitivity_1m"] = self.sensitivity.spl_at_1m

        if self.eq is not None:
            out["eq"] = self.eq

        out.update(self._extras)
        return out

    def is_empty(self) -> bool:
        """``True`` iff no DataFrame, no sensitivity, no eq, no extras are set."""
        if self.sensitivity is not None or self.eq is not None or self._extras:
            return False
        return all(getattr(self, name) is None for name in self._FRAME_FIELDS)

    def has(self, field_name: str) -> bool:
        """Sugar for ``getattr(m, name) is not None`` with field-name validation."""
        if not any(f.name == field_name for f in fields(self)):
            msg = f"Measurements has no field {field_name!r}"
            raise AttributeError(msg)
        return getattr(self, field_name) is not None
