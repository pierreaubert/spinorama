# import os
import unittest
import logging
import numpy as np
import pandas as pd
from spinorama.scores import octave, aad


pd.set_option("display.max_rows", 202)


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

    
