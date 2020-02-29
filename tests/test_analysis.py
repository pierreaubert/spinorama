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
        # load spin from klippel data
        self.title, self.spin_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/CEA2034.txt')
        self.spin = graph_melt(self.spin_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        # computed graphs
        self.computed_spin_unmelted = cea2034(self.splH, self.splV)
        self.computed_spin = graph_melt(self.computed_spin_unmelted)
        
    def test_validate_cea2034_onaxis(self):
        # from klippel
        onaxis = self.spin.loc[self.spin['Measurements'] == 'On Axis']
        # computed
        computed_onaxis = self.computed_spin.loc[self.computed_spin['Measurements'] == 'On Axis']
        # should have the same Freq
        self.assertEqual(computed_onaxis.Freq.size , onaxis.Freq.size)
        self.assertTrue(computed_onaxis.Freq.eq(onaxis.Freq).all())
        # and should be close in dB
        mean = onaxis.mean(0)
        computed_mean = computed_onaxis.mean(0)
        # looks to good to be true
        self.assertEqual(mean.dB, computed_mean.dB)
        self.assertTrue(computed_onaxis.dB.eq(onaxis.dB).all())
        
    def test_validate_cea2034_listening_window(self):
        # from klippel
        lw = self.computed_spin.loc[self.spin['Measurements'] == 'Listening Window']
        # computed
        computed_lw = self.computed_spin.loc[self.computed_spin['Measurements'] == 'Listening Window']
        # should have the same Freq size
        self.assertEqual(computed_lw.Freq.size , lw.Freq.size)
        self.assertTrue(computed_lw.Freq.eq(lw.Freq).all())
        # and should be close in dB
        mean = lw.mean(0)
        computed_mean = computed_lw.mean(0)
        # looks to good to be true
        self.assertEqual(mean.dB, computed_mean.dB)
        self.assertTrue(computed_lw.dB.eq(lw.dB).all())
        

    def test_validate_cea2034_sound_power(self):
        # from klippel
        sp = self.computed_spin.loc[self.spin['Measurements'] == 'Sound Power']
        # computed
        computed_sp = self.computed_spin.loc[self.computed_spin['Measurements'] == 'Sound Power']
        # should have the same Freq size
        self.assertEqual(computed_sp.Freq.size , sp.Freq.size)
        # not True because of resampling
        # self.assertTrue(computed_sp.Freq.eq(sp.Freq).all())
        # and should be close in dB
        mean = sp.mean(0)
        computed_mean = computed_sp.mean(0)
        # looks to good to be true
        self.assertEqual(mean.dB, computed_mean.dB)
        self.assertTrue(computed_sp.dB.eq(sp.dB).all())
        

if __name__ == '__main__':
    unittest.main()
