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

"""Per-format speaker measurement loader registry.

Two flavours of loader live behind a common entry point:

* **HV loaders** read a directory laid out with horizontal and vertical SPL
  sweeps and return ``(h_spl, v_spl)``.
* **Curve loaders** read a single set of curves (e.g. a digitised CEA2034
  spinorama) and return ``(title, df)`` where ``title`` is the curve family
  name.

Each ``parse_graphs_speaker_<format>`` function takes a slightly different
argument list; the adapters in this module pull whatever each format needs
out of a single :class:`SpeakerLoadParams` so callers see a uniform shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from spinorama.ltype import StatusOr
from spinorama.loaders.gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.loaders.klippel import parse_graphs_speaker_klippel
from spinorama.loaders.princeton import parse_graphs_speaker_princeton
from spinorama.loaders.rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.loaders.spl_hv_txt import parse_graphs_speaker_spl_hv_txt
from spinorama.loaders.webplotdigitizer import parse_graphs_speaker_webplotdigitizer


class UnknownMeasurementFormatError(ValueError):
    """Raised when ``speaker_parameters["mformat"]`` is not in the registry."""


@dataclass(frozen=True)
class SpeakerLoadParams:
    """Typed bag of inputs needed by the per-format loaders.

    Replaces the untyped ``speaker_parameters`` dict at the loader boundary.
    Each loader picks the fields it needs from this struct via its adapter.
    """

    measurement_path: str
    speaker_brand: str
    speaker_name: str
    mversion: str
    morigin: str
    mformat: str
    msymmetry: str | None
    mparameters: dict | None
    distance: float
    shape: str

    @classmethod
    def from_legacy(
        cls,
        speaker_path: str,
        speaker_brand: str,
        speaker_name: str,
        speaker_parameters: dict[str, Any],
    ) -> SpeakerLoadParams:
        """Build params from the legacy ``(path, brand, name, dict)`` API."""
        return cls(
            measurement_path=speaker_path,
            speaker_brand=speaker_brand,
            speaker_name=speaker_name,
            mversion=speaker_parameters["mversion"],
            morigin=speaker_parameters["morigin"],
            mformat=speaker_parameters["mformat"],
            msymmetry=speaker_parameters.get("msymmetry"),
            mparameters=speaker_parameters.get("mparameters"),
            distance=speaker_parameters["distance"],
            shape=speaker_parameters["shape"],
        )


class HVLoader(Protocol):
    """A loader that returns horizontal + vertical SPL DataFrames."""

    def __call__(
        self, params: SpeakerLoadParams
    ) -> StatusOr[tuple[pd.DataFrame, pd.DataFrame]]: ...


class CurveLoader(Protocol):
    """A loader that returns a single ``(title, dataframe)`` pair."""

    def __call__(self, params: SpeakerLoadParams) -> StatusOr[tuple[str, pd.DataFrame]]: ...


def _load_klippel(params: SpeakerLoadParams):
    return parse_graphs_speaker_klippel(
        params.measurement_path,
        params.speaker_brand,
        params.speaker_name,
        params.mversion,
        params.shape,
    )


def _load_princeton(params: SpeakerLoadParams):
    return parse_graphs_speaker_princeton(
        params.measurement_path,
        params.speaker_brand,
        params.speaker_name,
        params.mversion,
        params.msymmetry,
    )


def _load_spl_hv_txt(params: SpeakerLoadParams):
    return parse_graphs_speaker_spl_hv_txt(
        params.measurement_path,
        params.speaker_brand,
        params.speaker_name,
        params.mversion,
    )


def _load_gll_hv_txt(params: SpeakerLoadParams):
    return parse_graphs_speaker_gll_hv_txt(
        params.measurement_path,
        params.speaker_name,
        params.mversion,
    )


def _load_webplotdigitizer(params: SpeakerLoadParams):
    return parse_graphs_speaker_webplotdigitizer(
        params.measurement_path,
        params.speaker_brand,
        params.speaker_name,
        params.morigin,
        params.mversion,
    )


def _load_rew_text_dump(params: SpeakerLoadParams):
    return parse_graphs_speaker_rew_text_dump(
        params.measurement_path,
        params.speaker_brand,
        params.speaker_name,
        params.morigin,
        params.mversion,
    )


HV_LOADERS: dict[str, HVLoader] = {
    "klippel": _load_klippel,
    "princeton": _load_princeton,
    "spl_hv_txt": _load_spl_hv_txt,
    "gll_hv_txt": _load_gll_hv_txt,
}

CURVE_LOADERS: dict[str, CurveLoader] = {
    "webplotdigitizer": _load_webplotdigitizer,
    "rew_text_dump": _load_rew_text_dump,
}


__all__ = [
    "CURVE_LOADERS",
    "HV_LOADERS",
    "CurveLoader",
    "HVLoader",
    "SpeakerLoadParams",
    "UnknownMeasurementFormatError",
]
