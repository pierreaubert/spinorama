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

# local types
from typing import Literal, TypeVar

import numpy.typing as npt
import pandas as pd

Vector = npt.ArrayLike

DataSpeaker = dict[str, pd.DataFrame]

Zone = list[tuple[float, float]]

OptimResult = tuple[int, float, float]

T = TypeVar("T")
Status = Literal[True] | Literal[False]
StatusOr = tuple[Status, T]

ScoreError = tuple[None, None, dict[str, float]]
ScoreSuccess = tuple[DataSpeaker, DataSpeaker, dict[str, float]]
ScoreType = ScoreError | ScoreSuccess
