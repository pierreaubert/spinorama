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

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl


class Range(BaseModel):
    min: float
    max: float


JsonValue = Union[float, int, str, bool, Range, Dict[str, Any], List[Any], None]


class ConfidenceValue(BaseModel):
    value: JsonValue
    confidence: str = Field(pattern=r"^(low|medium|high)$")
    source_hint: Optional[str] = None  # e.g., "specs_html", "pdf"


class SpeakerSpecs(BaseModel):
    # Core identifiers
    brand: ConfidenceValue
    model: ConfidenceValue
    type: ConfidenceValue

    # Key specs aligned with normalizer
    sensitivity_db_2p83v_1m: ConfidenceValue
    impedance: Dict[str, ConfidenceValue]
    amplifier_power_recommended_w: ConfidenceValue
    frequency_response_hz: Dict[str, ConfidenceValue]
    drivers: Dict[str, ConfidenceValue]
    crossover_hz: Dict[str, ConfidenceValue]
    dispersion_horizontal_deg: ConfidenceValue
    dispersion_vertical_deg: ConfidenceValue
    max_spl_db: ConfidenceValue
    dimensions: Dict[str, ConfidenceValue]
    weight: Dict[str, ConfidenceValue]
    cabinet: Dict[str, ConfidenceValue]
    uom_sold_as: ConfidenceValue
    certifications: Dict[str, ConfidenceValue]

    # Provenance
    source_url: Optional[HttpUrl] = None
    last_verified: Optional[str] = None
