# import os
import unittest
# import logging
from spinorama.load import parse_graph_freq_klippel, parse_graph_princeton


class SpinoramaLoadTests(unittest.TestCase):

    def setUp(self):
        self.title, self.df = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/CEA2034.txt')

    def test_smoke1(self):
        self.assertEqual(self.title, 'CEA2034')
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn('On Axis', self.df.columns)
        self.assertNotIn('On-Axis', self.df.columns)


class SpinoramaLoadSPLTests(unittest.TestCase):

    def setUp(self):
        self.title, self.df = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')

    def test_smoke1(self):
        self.assertEqual(self.title, 'SPL Horizontal')
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn('On Axis', self.df.columns)
        self.assertNotIn('On-Axis', self.df.columns)
        # 200 in Freq, 36 off axis and 0
        self.assertEqual(self.df.shape, (200, 37))


class SpinoramaLoadPrinceton(unittest.TestCase):

    def setUp(self):
        self.df = parse_graph_princeton('datas/Princeton/Genelec 8351A/Genelec8351A_H_IR.mat', 'H')

    def test_smoke1(self):
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn('Freq', self.df.columns)
        self.assertIn('On Axis', self.df.columns)
        self.assertNotIn('On-Axis', self.df.columns)
        self.assertEqual(self.df.shape, (3328, 20))
        self.assertLess(500, self.df.Freq.min())


if __name__ == '__main__':
    unittest.main()
