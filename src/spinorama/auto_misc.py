# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

import pandas as pd
from spinorama.compute_estimates import estimates_spin


def get3db(spin: dict[str, pd.DataFrame], db_point: float) -> tuple[bool, float]:
    """Get -3dB point"""
    est = {}
    if "CEA2034_unmelted" in spin:
        est = estimates_spin(spin["CEA2034_unmelted"])
    elif "CEA2034" in spin and "Measurements" in spin:
        est = estimates_spin(spin["CEA2034"])
    spl = est.get("ref_3dB", None)
    if spl is None:
        return False, 0.0
    return True, spl


def have_full_measurements(df_speaker: dict[str, pd.DataFrame]) -> bool:
    len = 0
    required = [
        "On Axis",
        "10°",
        "20°",
        "30°",
        "40°",
        "50°",
        "60°",
        "70°",
        "80°",
        "90°",
        "100°",
        "110°",
        "120°",
        "130°",
        "140°",
        "150°",
        "160°",
        "170°",
        "180°",
        "-10°",
        "-20°",
        "-30°",
        "-40°",
        "-50°",
        "-60°",
        "-70°",
        "-80°",
        "-90°",
        "-100°",
        "-110°",
        "-120°",
        "-130°",
        "-140°",
        "-150°",
        "-160°",
        "-170°",
    ]
    check_required_h = False
    check_required_v = False
    if "SPL Horizontal_unmelted" in df_speaker:
        len += df_speaker["SPL Horizontal_unmelted"].shape[1]
        check_required_h = all([r in df_speaker["SPL Horizontal_unmelted"] for r in required])
    if "SPL Vertical_unmelted" in df_speaker:
        len += df_speaker["SPL Horizontal_unmelted"].shape[1]
        check_required_v = all([r in df_speaker["SPL Vertical_unmelted"] for r in required])
    check_len = len >= 72
    return check_len and check_required_v and check_required_h
