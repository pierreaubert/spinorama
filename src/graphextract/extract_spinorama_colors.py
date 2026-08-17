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

"""HSV color specifications for spinorama graph curves (CEA2034, On Axis, etc.)."""

import cv2
import numpy as np

from spinorama.extract_color_segment import CurveColorSpec


def hex_to_hsv_range(
    hex_color: str,
    h_tol: int = 10,
    s_tol: int = 40,
    v_tol: int = 40,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Convert a hex color string to an OpenCV HSV range with tolerance.

    Args:
        hex_color: Color as '#RRGGBB'.
        h_tol: Hue tolerance (OpenCV hue is 0-179).
        s_tol: Saturation tolerance (0-255).
        v_tol: Value tolerance (0-255).

    Returns:
        (lower_hsv, upper_hsv) tuple suitable for cv2.inRange.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # OpenCV expects BGR pixel in uint8 array
    bgr = np.array([[[b, g, r]]], dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0, 0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])

    lower = (max(0, h - h_tol), max(0, s - s_tol), max(0, v - v_tol))
    upper = (min(179, h + h_tol), min(255, s + s_tol), min(255, v + v_tol))
    return lower, upper


def _spec(
    name: str,
    hex_color: str,
    *,
    h_tol: int = 10,
    s_tol: int = 40,
    v_tol: int = 40,
    remove_grid_first: bool = False,
) -> CurveColorSpec:
    """Build a CurveColorSpec from a hex color."""
    hsv_range = hex_to_hsv_range(hex_color, h_tol=h_tol, s_tol=s_tol, v_tol=v_tol)

    # Handle hue wrap-around for red-ish colors (H near 0 or 179)
    lower, upper = hsv_range
    if lower[0] <= 0 and upper[0] < 179:
        # Hue wraps: create two ranges
        ranges = [
            ((0, lower[1], lower[2]), (upper[0], upper[1], upper[2])),
            ((179 + lower[0], lower[1], lower[2]), (179, upper[1], upper[2])),
        ]
        # Only add wrap range if it makes sense
        wrap_lower = 179 + lower[0]  # lower[0] is negative conceptually, but clamped to 0
        if wrap_lower < 179:
            ranges = [
                ((0, lower[1], lower[2]), (upper[0], upper[1], upper[2])),
                ((180 - h_tol, lower[1], lower[2]), (179, upper[1], upper[2])),
            ]
        else:
            ranges = [hsv_range]
    else:
        ranges = [hsv_range]

    return CurveColorSpec(name=name, hsv_ranges=ranges, remove_grid_first=remove_grid_first)


# ── Hex colors from plot.py UNIFORM_COLORS ──────────────────────────
_HEX_ON_AXIS = "#5c77a5"
_HEX_LISTENING_WINDOW = "#dc842a"
_HEX_EARLY_REFLECTIONS = "#c85857"
_HEX_SOUND_POWER = "#89b5b1"
_HEX_EARLY_REFLECTIONS_DI = "#71a152"
_HEX_SOUND_POWER_DI = "#bab0ac"
_HEX_TOTAL_EARLY_REFLECTION = "#76b7b2"  # colors[7]

# Early Reflections sub-curves share colors with other assignments
_HEX_CEILING_BOUNCE = "#dc842a"  # colors[1]
_HEX_FLOOR_BOUNCE = "#c85857"  # colors[2]
_HEX_FRONT_WALL = "#89b5b1"  # colors[3]
_HEX_SIDE_WALL = "#bab0ac"  # colors[5]
_HEX_REAR_WALL = "#71a152"  # colors[4]


# ── CEA2034 ─────────────────────────────────────────────────────────
CEA2034_CURVE_SPECS: list[CurveColorSpec] = [
    _spec("On Axis", _HEX_ON_AXIS),
    _spec("Listening Window", _HEX_LISTENING_WINDOW),
    _spec("Early Reflections", _HEX_EARLY_REFLECTIONS, h_tol=8),
    _spec("Sound Power", _HEX_SOUND_POWER),
    _spec("Early Reflections DI", _HEX_EARLY_REFLECTIONS_DI),
    _spec("Sound Power DI", _HEX_SOUND_POWER_DI, s_tol=30, remove_grid_first=True),
]

# ── On Axis ─────────────────────────────────────────────────────────
ON_AXIS_CURVE_SPECS: list[CurveColorSpec] = [
    _spec("On Axis", _HEX_ON_AXIS),
]

# ── Early Reflections ───────────────────────────────────────────────
EARLY_REFLECTIONS_CURVE_SPECS: list[CurveColorSpec] = [
    _spec("Floor Bounce", _HEX_FLOOR_BOUNCE, h_tol=8),
    _spec("Ceiling Bounce", _HEX_CEILING_BOUNCE),
    _spec("Front Wall Bounce", _HEX_FRONT_WALL),
    _spec("Side Wall Bounce", _HEX_SIDE_WALL, s_tol=30, remove_grid_first=True),
    _spec("Rear Wall Bounce", _HEX_REAR_WALL),
    _spec("Total Early Reflection", _HEX_TOTAL_EARLY_REFLECTION),
]

# ── Estimated In-Room Response ──────────────────────────────────────
ESTIMATED_IN_ROOM_CURVE_SPECS: list[CurveColorSpec] = [
    _spec("Estimated In-Room Response", _HEX_ON_AXIS),
]

# Curve name to hex color for use in HTML/plotting
CURVE_HEX_COLORS: dict[str, str] = {
    "On Axis": _HEX_ON_AXIS,
    "Listening Window": _HEX_LISTENING_WINDOW,
    "Early Reflections": _HEX_EARLY_REFLECTIONS,
    "Sound Power": _HEX_SOUND_POWER,
    "Early Reflections DI": _HEX_EARLY_REFLECTIONS_DI,
    "Sound Power DI": _HEX_SOUND_POWER_DI,
    "Floor Bounce": _HEX_FLOOR_BOUNCE,
    "Ceiling Bounce": _HEX_CEILING_BOUNCE,
    "Front Wall Bounce": _HEX_FRONT_WALL,
    "Side Wall Bounce": _HEX_SIDE_WALL,
    "Rear Wall Bounce": _HEX_REAR_WALL,
    "Total Early Reflection": _HEX_TOTAL_EARLY_REFLECTION,
    "Estimated In-Room Response": _HEX_ON_AXIS,
}

# Map graph type names to their curve specs
GRAPH_TYPE_SPECS: dict[str, list[CurveColorSpec]] = {
    "CEA2034": CEA2034_CURVE_SPECS,
    "On Axis": ON_AXIS_CURVE_SPECS,
    "Early Reflections": EARLY_REFLECTIONS_CURVE_SPECS,
    "Estimated In-Room Response": ESTIMATED_IN_ROOM_CURVE_SPECS,
}
