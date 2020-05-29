# import os
import unittest
import pandas as pd
from spinorama.load import graph_melt
from spinorama.load.klippel import parse_graph_freq_klippel
from spinorama.estimates import estimates


pd.set_option("display.max_rows", 202)


class SpinoramaEstimatesTests(unittest.TestCase):


    def setUp(self):
        self.title, self.df_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/CEA2034.txt')
        self.df = graph_melt(self.df_unmelted)
        self.onaxis = self.df.loc[self.df['Measurements'] == 'On Axis']
        

    def test_estimates(self):
        self.estimates = estimates(self.onaxis)
        self.assertNotEqual(-1, self.estimates[0])
        self.assertNotEqual(-1, self.estimates[1])
        self.assertNotEqual(-1, self.estimates[2])
        self.assertNotEqual(-1, self.estimates[3])
        # 
        self.assertAlmostEqual(self.estimates[0], 106)
        self.assertAlmostEqual(self.estimates[1],  59)
        self.assertAlmostEqual(self.estimates[2],  53)
        self.assertAlmostEqual(self.estimates[3],  2.0)


if __name__ == '__main__':
    unittest.main()

    
