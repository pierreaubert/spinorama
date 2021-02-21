import math
import unittest
import numpy as np
import numpy.testing as npt
from spinorama.compute_cea2034 import (
    compute_areaQ,
    compute_weigths,
)


std_weigths = [
    0.000604486,
    0.004730189,
    0.008955027,
    0.012387354,
    0.014989611,
    0.016868154,
    0.018165962,
    0.019006744,
    0.019477787,
    0.019629373,
]


class WeigthsTests(unittest.TestCase):
    def setUp(self):
        pass

    def test_areaQ(self):
        # expect area of half sphere
        self.assertAlmostEqual(compute_areaQ(90, 90), 2.0 * math.pi)

    def test_weigths(self):
        weigths = np.array(compute_weigths())
        # check that they are the same expect the scaling
        scale = np.linalg.norm(weigths) / np.linalg.norm(std_weigths)
        scaled_weigths = weigths / scale

        with self.assertRaises(AssertionError) as e:
            npt.assert_array_almost_equal_nulp(scaled_weigths, std_weigths)

        delta = np.max(np.abs(scaled_weigths - std_weigths))
        self.assertLess(delta, 1.0e-9)
