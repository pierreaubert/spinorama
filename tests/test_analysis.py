# import os
import unittest
# import logging
from spinorama.load import parse_graph_freq_klippel, graph_melt
from spinorama.analysis import estimates, cea2034


class SpinoramaAnalysisTests(unittest.TestCase):

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
        self.assertAlmostEqual(self.estimates[0], 60)
        self.assertAlmostEqual(self.estimates[1], 57)
        self.assertAlmostEqual(self.estimates[2], 54)
        self.assertAlmostEqual(self.estimates[3], 3.0)


class SpinoramaSpinoramaTests(unittest.TestCase):

    def setUp(self):
        # load spin
        self.title, self.df_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/CEA2034.txt')
        self.df = graph_melt(self.df_unmelted)
        self.onaxis = self.df.loc[self.df['Measurements'] == 'On Axis']
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        
    def test_validate_cea2034(self):
        computed_spin_unmelted = cea2034(self.splH, self.splV)
        computed_spin = graph_melt(computed_spin_unmelted)
        computed_onaxis = computed_spin.loc[computed_spin['Measurements'] == 'On Axis']
        # self.assertEqual(computed_onaxi.Freq.size , self.onaxis.Freq.size)
        pass
        
        

if __name__ == '__main__':
    unittest.main()
