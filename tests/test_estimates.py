# import os
import unittest
import pandas as pd
from spinorama.load import graph_melt
from spinorama.load_klippel import parse_graph_freq_klippel
from spinorama.compute_estimates import estimates


pd.set_option("display.max_rows", 202)


class SpinoramaEstimatesNV2Tests(unittest.TestCase):


    def setUp(self):
        self.title, self.df_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/asr-v2-20200208/CEA2034.txt')
        self.df = graph_melt(self.df_unmelted)
        self.onaxis = self.df.loc[self.df['Measurements'] == 'On Axis']
        

    def test_estimates(self):
        self.estimates = estimates(self.onaxis)
        self.assertNotEqual(-1, self.estimates['ref_level'])
        self.assertNotEqual(-1, self.estimates['ref_3dB'])
        self.assertNotEqual(-1, self.estimates['ref_6dB'])
        self.assertNotEqual(-1, self.estimates['ref_band'])
        # 
        self.assertAlmostEqual(self.estimates['ref_level'],  106)
        self.assertAlmostEqual(self.estimates['ref_3dB'],  59) # Hz
        self.assertAlmostEqual(self.estimates['ref_6dB'],  53) # Hz
        self.assertAlmostEqual(self.estimates['ref_band'],  2.0) # deviation in dB


class SpinoramaEstimatesNV3Tests(unittest.TestCase):


    def setUp(self):
        self.title, self.df_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/asr-v3-20200711/CEA2034.txt')
        self.df = graph_melt(self.df_unmelted)
        self.onaxis = self.df.loc[self.df['Measurements'] == 'On Axis']
        

    def test_estimates(self):
        self.estimates = estimates(self.onaxis)
        self.assertNotEqual(-1, self.estimates['ref_level'])
        self.assertNotEqual(-1, self.estimates['ref_3dB'])
        self.assertNotEqual(-1, self.estimates['ref_6dB'])
        self.assertNotEqual(-1, self.estimates['ref_band'])
        # 
        self.assertAlmostEqual(self.estimates['ref_level'],  81)
        self.assertAlmostEqual(self.estimates['ref_3dB'],  56) # Hz
        self.assertAlmostEqual(self.estimates['ref_6dB'],  51) # Hz
        self.assertAlmostEqual(self.estimates['ref_band'],  1.4) # deviation in dB


if __name__ == '__main__':
    unittest.main()

    
