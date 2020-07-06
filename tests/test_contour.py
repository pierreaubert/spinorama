import unittest
import pandas as pd
from spinorama.graph_contour import compute_contour


class SpinoramaContourTests(unittest.TestCase):

    def setUp(self):
        
        freq = [20, 200, 2000, 20000]
        onaxis = [10, 10, 10, 10]
        d10    = [8, 7, 6, 5]
        self.df = pd.DataFrame({'Freq': freq, 'On Axis': onaxis, '10o': d10 })

    def test_smoke1(self):
        af, am, az = compute_contour(self.df)
        self.assertEqual(af.size, am.size)
        self.assertEqual(af.size, az.size)



if __name__ == '__main__':
    unittest.main()
