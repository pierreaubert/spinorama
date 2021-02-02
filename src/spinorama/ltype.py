#                                                  -*- coding: utf-8 -*-
# local types
from typing import List, Tuple

Vector = List[float]

from .filter_iir import Biquad

Peq = List[Tuple[float, Biquad]]
