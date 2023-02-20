# -*- coding: utf-8 -*-
# local types
from typing import Any
import pandas as pd
from nptyping import NDArray, Float

from spinorama.filter_iir import Biquad

Vector = list[float]

FloatVector1D = NDArray[(Any), Float]

Peq = list[tuple[float, Biquad]]

DataSpeaker = dict[str, pd.DataFrame]
