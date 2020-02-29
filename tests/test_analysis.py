# import os
import unittest
import logging
from spinorama.load import parse_graph_freq_klippel, graph_melt
from spinorama.analysis import estimates, compute_cea2034


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
        # load spin from klippel data
        self.title, self.spin_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/CEA2034.txt')
        self.spin = graph_melt(self.spin_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        # computed graphs
        self.computed_spin_unmelted = compute_cea2034(self.splH, self.splV)
        self.computed_spin = graph_melt(self.computed_spin_unmelted)
        
    def test_validate_cea2034(self):
        for measurement in ['On Axis', 'Listening Window']:
            # from klippel
            reference = self.spin.loc[self.spin['Measurements'] == measurement]
            # computed
            computed = self.computed_spin.loc[self.computed_spin['Measurements'] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size , reference.Freq.size)
            self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            delta = (computed.dB-reference.dB).abs().max()
            # 1 db tolerance?
            # TODO(pierreaubert): that's too high
            self.assertLess(delta, 1.0)
        
    def test_validate_cea2034_soundpower(self):
        for measurement in ['Sound Power']:
            # from klippel
            reference = self.spin.loc[self.spin['Measurements'] == measurement]
            # computed
            computed = self.computed_spin.loc[self.computed_spin['Measurements'] == measurement]
            # delta
            self.assertEqual(computed.shape, reference.shape)
            # freq are not exactly the same
            # print(reference.dB.abs().max())
            # print(computed.dB.abs().max())
            # print(reference.dB.mean(axis=0))
            # print(computed.dB.mean(axis=0))
            # and should be equal or close in dB
            self.assertLess( abs(reference.dB.abs().max()-computed.dB.abs().max()), 1.0 )
            self.assertLess( abs(reference.dB.mean(axis=0)-computed.dB.mean(axis=0)), 1.0 )
        

if __name__ == '__main__':
    unittest.main()
