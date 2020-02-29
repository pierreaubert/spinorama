# import os
import unittest
import logging
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
        
    def test_validate_cea2034_onaxis(self):
        computed_spin_unmelted = cea2034(self.splH, self.splV)
        computed_spin = graph_melt(computed_spin_unmelted)
        computed_onaxis = computed_spin.loc[computed_spin['Measurements'] == 'On Axis']
        # should have the same Freq
        self.assertEqual(computed_onaxis.Freq.size , self.onaxis.Freq.size)
        # and should be close in dB
        mean = self.onaxis.mean(0)
        computed_mean = computed_onaxis.mean(0)
        # looks to good to be true
        self.assertEqual(mean.dB, computed_mean.dB)
        

if __name__ == '__main__':
    unittest.main()
