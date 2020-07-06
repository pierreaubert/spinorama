# import os
import unittest
import spinorama.graph_isobands as gi


class CrossPointTests(unittest.TestCase):

    def setUp(self):
        self.p0 = (0, 0)
        self.p1 = (1, 0)
        self.p2 = (0, 1)
        self.triangle = gi.Triangle(self.p0, self.p1, self.p2)
        self.z = {}
        self.z[self.p0] = 1
        self.z[self.p1] = 3
        self.z[self.p2] = 5

    def test_cross_point(self):
        self.assertEqual(gi.cross_point(self.p0, self.p1, self.z, 2), (0.5, 0))
        self.assertEqual(gi.cross_point(self.p0, self.p1, self.z, 1.5), (0.25, 0))
        self.assertEqual(gi.cross_point(self.p0, self.p1, self.z, 1), self.p0)
        self.assertEqual(gi.cross_point(self.p0, self.p1, self.z, 3), self.p1)


HL = (0.25, 0)
HH = (0.5, 0)
VL = (0, 0.25)
VH = (0, 0.5)
DL = (0.75, 0.25)
DH = (0.5, 0.5)

class TrapezeTests(unittest.TestCase):

    def setUp(self):
        self.p0 = (0, 0)
        self.p1 = (1, 0)
        self.p2 = (0, 1)
        # needs to be sorted by z
        self.triangle = gi.Triangle(self.p0, self.p1, self.p2)
        self.z = {}

    def test_trapeze1(self):
        self.z[self.p0] = 0
        self.z[self.p1] = 8
        self.z[self.p2] = 8
        self.assertEqual(gi.trapeze1(self.triangle, self.z, 2, 4), [HL, HH, VH, VL])

    def test_trapeze2(self):
        self.z[self.p0] = 0
        self.z[self.p1] = 0
        self.z[self.p2] = 8
        self.assertEqual(gi.trapeze2(self.triangle, self.z, 2, 4), [VL, VH, DH, DL])

    def test_trapeze3(self):
        self.z[self.p0] = 0
        self.z[self.p1] = 8
        self.z[self.p2] = 8
        self.assertEqual(gi.trapeze3(self.triangle, self.z, 2, 16), [HL, VL, self.p2, self.p1])

    def test_trapeze4(self):
        self.z[self.p0] = 0
        self.z[self.p1] = 0
        self.z[self.p2] = 8
        self.assertEqual(gi.trapeze4(self.triangle, self.z, -4, 2), [self.p0, self.p1, DL, VL])
        


class TriangleTests(unittest.TestCase):

    def setUp(self):
        self.p0 = (0, 0)
        self.p1 = (1, 0)
        self.p2 = (0, 1)
        # needs to be sorted by z
        self.triangle = gi.Triangle(self.p0, self.p1, self.p2)
        self.z = {}

    def test_triangle1(self):
        self.z[self.p0] = 0
        self.z[self.p1] = 8
        self.z[self.p2] = 8
        self.assertEqual(gi.triangle1(self.triangle, self.z, -4, 2), [HL, VL, self.p0])

    def test_triangle2(self):
        self.z[self.p0] = 0
        self.z[self.p1] = 0
        self.z[self.p2] = 8
        self.assertEqual(gi.triangle2(self.triangle, self.z, 2, 16), [DL, VL, self.p2])


class PentagonTests(unittest.TestCase):

    def setUp(self):
        self.p0 = (0, 0)
        self.p1 = (1, 0)
        self.p2 = (0, 1)
        # needs to be sorted by z
        self.triangle = gi.Triangle(self.p0, self.p1, self.p2)
        self.z = {}

    def test_triangle1(self):
        self.z[self.p0] = 1
        self.z[self.p1] = 3
        self.z[self.p2] = 5
        self.assertEqual(gi.pentagon(self.triangle, self.z, 2, 4),
                         [(0.5,0), (0,0.25), (0,0.75), (0.5,0.5), (1,0)])

class Triangle2BandTests(unittest.TestCase):

    def setUp(self):
        self.p0 = (0, 0)
        self.p1 = (1, 0)
        self.p2 = (0, 1)
        # needs to be sorted by z
        self.triangle = gi.Triangle(self.p0, self.p1, self.p2)
        self.z = {}

    def test_triangle2band(self):
        self.z[self.p0] = 1
        self.z[self.p1] = 3
        self.z[self.p2] = 5
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, -2, -1))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, -2, 1))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, -2, 2))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, -2, 3))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, -2, 4))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, -2, 5))
        
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 2, 3))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 2, 4))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 2, 5))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 2, 6))
        
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 3, 4))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 3, 5))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 3, 6))
        
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 4, 5))
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 4, 6))
        
        self.assertIsNotNone(gi.triangle2band(self.triangle, self.z, 6, 6))




if __name__ == '__main__':
    unittest.main()
