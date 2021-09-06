#                                                  -*- coding: utf-8 -*-
# local types
from typing import List, Tuple, Dict
import pandas as pd

Vector = List[float]

from .filter_iir import Biquad

Peq = List[Tuple[float, Biquad]]

DataSpeaker = Dict[str, pd.DataFrame]
