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

from spinorama.compute_estimates import estimates_spin
from spinorama.measurements import Measurements


_REQUIRED_HORIZONTAL_ANGLES = [
    "On Axis",
    *[f"{i}°" for i in range(10, 190, 10)],
    *[f"-{i}°" for i in range(10, 180, 10)],
]


def get3db(m: Measurements, db_point: float) -> tuple[bool, float]:
    """Return the -3 dB rolloff frequency derived from the CEA2034 spin."""
    if m.cea2034 is None:
        return False, 0.0
    est = estimates_spin(m.cea2034)
    spl = est.get("ref_3dB", None)
    if spl is None:
        return False, 0.0
    return True, spl


def have_full_measurements(m: Measurements) -> bool:
    """``True`` iff both H and V SPL sweeps contain every required angle column."""
    if m.h_spl is None or m.v_spl is None:
        return False
    have_all_h = all(angle in m.h_spl for angle in _REQUIRED_HORIZONTAL_ANGLES)
    have_all_v = all(angle in m.v_spl for angle in _REQUIRED_HORIZONTAL_ANGLES)
    if not (have_all_h and have_all_v):
        return False
    return m.h_spl.shape[1] + m.v_spl.shape[1] >= 72
