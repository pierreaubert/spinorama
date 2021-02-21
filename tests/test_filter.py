import math
import unittest

import numpy as np
import numpy.testing as npt

from spinorama.filter_iir import Biquad


class SpinoramaFilterIIRTests(unittest.TestCase):
    def setUp(self):
        self.freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 200)
        self.peak = Biquad(3, 1000, 48000, 1, 3)

    def test_smoke1(self):
        peq_slow = np.array(
            [20.0 * math.log10(self.peak.resultSlow(f)) for f in self.freq]
        )
        peq_fast = np.array([20.0 * math.log10(self.peak.result(f)) for f in self.freq])
        peq_vec = self.peak.np_log_result(self.freq)
        with self.assertRaises(AssertionError):
            npt.assert_array_almost_equal_nulp(peq_slow, peq_fast)
            npt.assert_array_almost_equal_nulp(peq_slow, peq_vec)


if __name__ == "__main__":
    unittest.main()
