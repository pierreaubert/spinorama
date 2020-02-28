# import os
import unittest
# import logging
from spinorama.load import parse_graph_freq_klippel


class SpinoramaLoadTests(unittest.TestCase):

    def setUp(self):
        self.title, self.df = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/CEA2034.txt')

    def test_smoke1(self):
        self.assertEqual(self.title, 'CEA2034')
        self.assertIsNotNone(self.df)

    def test_smoke2(self):
        self.assertIn('On Axis', self.df.keys())


if __name__ == '__main__':
    unittest.main()
