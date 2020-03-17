# import os
import unittest
import logging
import numpy as np
import pandas as pd
from spinorama.load import parse_graph_freq_klippel, graph_melt
from spinorama.analysis import estimates, compute_cea2034, early_reflections,\
     vertical_reflections, horizontal_reflections, estimated_inroom_HV, \
     octave, aad


pd.set_option("display.max_rows", 202)


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
        # 
        self.assertAlmostEqual(self.estimates[0], 106)
        self.assertAlmostEqual(self.estimates[1],  59)
        self.assertAlmostEqual(self.estimates[2],  53)
        self.assertAlmostEqual(self.estimates[3],  2.0)


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
        

class SpinoramaEarlyReflectionsTests(unittest.TestCase):


    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/Early Reflections.txt')
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        # computed graphs
        self.computed_unmelted = early_reflections(self.splH, self.splV)
        self.computed = graph_melt(self.computed_unmelted)


    def test_smoke(self):
       self.assertEqual( self.reference_unmelted.shape, self.computed_unmelted.shape)
       self.assertEqual( self.reference.shape, self.computed.shape)
        

    def test_validate_early_reflections(self):
        for measurement in ['Floor Bounce', 'Ceiling Bounce', 'Front Wall Bounce', 'Side Wall Bounce', 'Rear Wall Bounce', 'Total Early Reflection']:
            # key check 
            self.assertIn(measurement, self.computed_unmelted.keys())
            self.assertIn(measurement, self.reference_unmelted.keys())
            # from klippel
            reference = self.reference.loc[self.reference['Measurements'] == measurement]
            # computed
            computed = self.computed.loc[self.computed['Measurements'] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size , reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # 0.2 db tolerance?
            # TODO(pierreaubert): that's too high
            self.assertLess(abs(reference.dB.abs().max()-computed.dB.abs().max()), 0.2)
        
        
class SpinoramaVerticalReflectionsTests(unittest.TestCase):


    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/Vertical Reflections.txt')
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        # computed graphs
        self.computed_unmelted = vertical_reflections(self.splH, self.splV)
        self.computed = graph_melt(self.computed_unmelted)


    def test_smoke(self):
       self.assertEqual( self.reference_unmelted.shape, self.computed_unmelted.shape)
       self.assertEqual( self.reference.shape, self.computed.shape)
        

    def test_validate_vertical_reflections(self):
        for measurement in ['Floor Reflection', 'Ceiling Reflection']:
            # key check 
            self.assertIn(measurement, self.computed_unmelted.keys())
            self.assertIn(measurement, self.reference_unmelted.keys())
            # from klippel
            reference = self.reference.loc[self.reference['Measurements'] == measurement]
            # computed
            computed = self.computed.loc[self.computed['Measurements'] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size , reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # 0.2 db tolerance?
            # TODO(pierreaubert): that's too high
            self.assertLess(abs(reference.dB.abs().max()-computed.dB.abs().max()), .2)
        
        

class SpinoramaHorizontalReflectionsTests(unittest.TestCase):


    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/Horizontal Reflections.txt')
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        # computed graphs
        self.computed_unmelted = horizontal_reflections(self.splH, self.splV)
        self.computed = graph_melt(self.computed_unmelted)


    def test_smoke(self):
       self.assertEqual( self.reference_unmelted.shape, self.computed_unmelted.shape)
       self.assertEqual( self.reference.shape, self.computed.shape)
        

    def test_validate_vertical_reflections(self):
        for measurement in ['Rear', 'Side', 'Front']:
            # key check 
            self.assertIn(measurement, self.computed_unmelted.keys())
            self.assertIn(measurement, self.reference_unmelted.keys())
            # from klippel
            reference = self.reference.loc[self.reference['Measurements'] == measurement]
            # computed
            computed = self.computed.loc[self.computed['Measurements'] == measurement]
            # should have the same Freq
            self.assertEqual(computed.Freq.size , reference.Freq.size)
            # self.assertTrue(computed.Freq.eq(reference.Freq).all())
            # and should be equal or close in dB
            # 0.2 db tolerance?
            self.assertLess(abs(reference.dB.abs().max()-computed.dB.abs().max()), .2)
        
        

class SpinoramaEstimatedInRoomTests(unittest.TestCase):


    def setUp(self):
        # load spin from klippel data
        self.title, self.reference_unmelted = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/Estimated In-Room Response.txt')
        self.reference = graph_melt(self.reference_unmelted)
        # load spl vertical and horizontal
        self.titleH, self.splH = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Horizontal.txt')
        self.titleV, self.splV = parse_graph_freq_klippel('datas/ASR/Neumann KH 80/SPL Vertical.txt')
        # computed graphs
        self.computed_unmelted = estimated_inroom_HV(self.splH, self.splV)
        self.computed = graph_melt(self.computed_unmelted)


    def test_smoke(self):
       self.assertEqual( self.reference_unmelted.shape, self.computed_unmelted.shape)
       self.assertEqual( self.reference.shape, self.computed.shape)
        

    def test_validate_estimated_inroom(self):
        # key check 
        self.assertIn('Estimated In-Room Response', self.computed_unmelted.keys())
        self.assertIn('Estimated In-Room Response', self.reference_unmelted.keys())
        # from klippel
        reference = self.reference.loc[self.reference['Measurements'] == 'Estimated In-Room Response']
        # computed
        computed = self.computed.loc[self.computed['Measurements'] == 'Estimated In-Room Response']
        # should have the same Freq
        self.assertEqual(computed.Freq.size , reference.Freq.size)
        # self.assertTrue(computed.Freq.eq(reference.Freq).all())
        # and should be equal or close in dB
        # 0.1 db tolerance?
        self.assertLess(abs(reference.dB.abs().max()-computed.dB.abs().max()), 0.1)
        
        
class PrefRatingTests(unittest.TestCase):

    def setUp(self):
        self.octave2 = octave(2)
        self.octave3 = octave(3)
        self.octave20 = octave(20)

    def test_octave(self):
        self.assertEqual(len(self.octave2), 21)
        self.assertLess(self.octave2[0][0], 100)
        self.assertLess(20000, self.octave2[-1][1])
        
        self.assertEqual(len(self.octave3), 31)
        self.assertLess(self.octave3[0][0], 100)
        self.assertLess(20000, self.octave3[-1][1])

    def test_aad(self):
        freq = [i for i in np.logspace(0.3,4.3,1000)]
        db = [100 for i in np.logspace(0.3,4.3,1000)]
        df = pd.DataFrame({'Freq': freq, 'dB': db})
        # expect 0 deviation from flat line
        self.assertEqual(aad(df), 0.0)
    
if __name__ == '__main__':
    unittest.main()

    
