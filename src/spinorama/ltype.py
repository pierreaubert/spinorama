#                                                  -*- coding: utf-8 -*-
# local types
from typing import List, Tuple, Dict, Any
import pandas as pd
from nptyping import NDArray

Vector = List[float]

FloatVector1D = NDArray[(1, Any), float]

from .filter_iir import Biquad

Peq = List[Tuple[float, Biquad]]

DataSpeaker = Dict[str, pd.DataFrame]
