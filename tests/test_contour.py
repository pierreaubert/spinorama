import unittest
import numpy as np
import pandas as pd
from spinorama.graph_contour import compute_contour, reshape, compute_contour_smoothed


class SpinoramaContourSizeTests(unittest.TestCase):
    def setUp(self):

        freq = [20, 200, 2000, 20000]
        onaxis = [10, 10, 10, 10]
        d10 = [8, 7, 6, 5]
        self.df = pd.DataFrame({"Freq": freq, "On Axis": onaxis, "10°": d10})

    def test_smoke1(self):
        af, am, az = compute_contour(self.df)
        self.assertEqual(af.size, am.size)
        self.assertEqual(af.size, az.size)


class SpinoramaContourTests(unittest.TestCase):
    def setUp(self):

        freq = [20, 100, 200, 1000, 2000, 10000, 20000]
        onaxis = [10, 10, 10, 10, 10, 10, 10]
        #
        d10p = [10, 10, 9, 9, 8, 8, 7]
        d20p = [10, 10, 8, 8, 7, 7, 6]
        d30p = [10, 10, 7, 7, 6, 6, 5]
        # decrease faster on the neg size
        d10m = [10, 10, 8, 8, 7, 7, 6]
        d20m = [10,  8, 6, 6, 4, 4, 2]
        d30m = [10,  6, 6, 4, 2, 2, 0]
        self.df = pd.DataFrame(
            {
                "Freq": freq,
                "On Axis": onaxis,
                "10°": d10p,
                "-10°": d10m,
                "20°": d20p,
                "-20°": d20m,
                "30°": d30p,
                "-30°": d30m,
            }
        )

    def test_smoke_size(self):
        af, am, az = compute_contour(self.df)
        self.assertEqual(af.size, am.size)
        self.assertEqual(af.size, az.size)

    def test_smoke_freq(self):
        af, am, az = compute_contour(self.df)
        self.assertAlmostEqual(np.min(af), 20)
        self.assertAlmostEqual(np.max(af), 20000)

    def test_smoke_angle(self):
        af, am, az = compute_contour(self.df)
        self.assertEqual(np.min(am), -30)
        self.assertEqual(np.max(am), 30)

    def test_smoke_db_normalized(self):
        af, am, az = compute_contour(self.df)
        self.assertEqual(np.min(az), -10)
        self.assertEqual(np.max(az), 0)

    def test_smoke_preserve_angle(self):
        af, am, az = compute_contour(self.df)
        print(af, am, az)
        print(self.df)
        print(error)


class SpinoramaReshapeTests(unittest.TestCase):
    def setUp(self):

        freq = [20, 100, 200, 1000, 2000, 10000, 20000]
        onaxis = [10, 10, 10, 10, 10, 10, 10]
        d10p = [10, 10, 9, 9, 8, 8, 7]
        d20p = [10, 10, 8, 8, 7, 7, 6]
        d30p = [10, 10, 7, 7, 6, 6, 5]
        # decrease faster on the neg size
        d10m = [10, 10, 8, 8, 7, 7, 6]
        d20m = [10,  8, 6, 6, 4, 4, 2]
        d30m = [10,  6, 6, 4, 2, 2, 0]
        self.df = pd.DataFrame(
            {
                "Freq": freq,
                "On Axis": onaxis,
                "10°": d10p,
                "-10°": d10m,
                "20°": d20p,
                "-20°": d20m,
                "30°": d30p,
                "-30°": d30m,
            }
        )
        self.af, self.am, self.az = compute_contour(self.df)

    def test_smoke_size(self):
        for scale in range(2, 10):
            raf, ram, raz = reshape(self.af, self.am, self.az, scale)
            self.assertEqual(raf.size, ram.size)
            self.assertEqual(raf.size, raz.size)

    def test_smoke_freq(self):
        for scale in range(2, 10):
            raf, ram, raz = reshape(self.af, self.am, self.az, scale)
            self.assertAlmostEqual(np.min(raf), 20)
            self.assertAlmostEqual(np.max(raf), 20000)

    def test_smoke_angle(self):
        for scale in range(2, 10):
            raf, ram, raz = reshape(self.af, self.am, self.az, scale)
            self.assertEqual(np.min(ram), -30)
            self.assertEqual(np.max(ram), 30)

    def test_smoke_db_normalized(self):
        for scale in range(2, 10):
            raf, ram, raz = reshape(self.af, self.am, self.az, scale)
            self.assertEqual(np.min(raz), -10)
            self.assertEqual(np.max(raz), 0)


if __name__ == "__main__":
    unittest.main()
