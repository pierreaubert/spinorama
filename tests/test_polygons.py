import unittest
import logging
import numpy as np
import pandas as pd

import graphs.polygons as poly

p0 = (0,0)    
p1 = (1,0)
p2 = (1,1)
p3 = (0,1)
p4 = (-1,1)
p5 = (-1,0)

class PolyIsCloseTests(unittest.TestCase):

    def setUp(self):
        self.po = [p0, p1, p2]
        self.pc = [p0, p1, p2, p0]
    
    def test_is_close(self):
        self.assertEqual(poly.is_close(self.po), 0)
        self.assertEqual(poly.is_close(self.pc), 1)

class PolyOrderTests(unittest.TestCase):

    def setUp(self):
        self.triangles = ([p0, p1, p2], [p0, p2, p1], [p2, p1, p0], [p2, p0, p1], [p1, p0, p2], [p1, p2, p0])
        self.rectangles = ([p0, p1, p2, p3], [p0, p3, p2, p1],
                           [p1, p2, p3, p0], [p1, p0, p3, p2],
                           [p2, p3, p0, p1], [p2, p1, p0, p3],
                           [p3, p0, p1, p2], [p3, p2, p1, p0])
    
    def test_ordering_triangles(self):
        print('--- test open triangles ---')
        for triangle in self.triangles:
            self.assertEqual(poly.order_polygon(triangle, [p0, p1]), [p0, p1, p2])
            self.assertEqual(poly.order_polygon(triangle, [p0, p2]), [p0, p2, p1])
            self.assertEqual(poly.order_polygon(triangle, [p1, p2]), [p1, p2, p0])
            self.assertEqual(poly.order_polygon(triangle, [p1, p0]), [p1, p0, p2])
            self.assertEqual(poly.order_polygon(triangle, [p2, p0]), [p2, p0, p1])
            self.assertEqual(poly.order_polygon(triangle, [p2, p1]), [p2, p1, p0])

        print('--- test closed triangles ---')
        for triangle in self.triangles:
            triangle_close = triangle
            triangle_close.append(triangle[0])
            self.assertEqual(poly.order_polygon(triangle_close, [p0, p1]), [p0, p1, p2, p0])
            self.assertEqual(poly.order_polygon(triangle_close, [p0, p2]), [p0, p2, p1, p0])
            self.assertEqual(poly.order_polygon(triangle_close, [p1, p2]), [p1, p2, p0, p1])
            self.assertEqual(poly.order_polygon(triangle_close, [p1, p0]), [p1, p0, p2, p1])
            self.assertEqual(poly.order_polygon(triangle_close, [p2, p0]), [p2, p0, p1, p2])
            self.assertEqual(poly.order_polygon(triangle_close, [p2, p1]), [p2, p1, p0, p2])

    def test_ordering_rectangles(self):
        print('--- test open rectangles ---')
        for rectangle in self.rectangles:
            self.assertEqual(poly.order_polygon(rectangle, [p0, p1]), [p0, p1, p2, p3])
            self.assertEqual(poly.order_polygon(rectangle, [p1, p0]), [p1, p0, p3, p2])
            self.assertEqual(poly.order_polygon(rectangle, [p1, p2]), [p1, p2, p3, p0])
            self.assertEqual(poly.order_polygon(rectangle, [p2, p1]), [p2, p1, p0, p3])
            self.assertEqual(poly.order_polygon(rectangle, [p3, p2]), [p3, p2, p1, p0])
            self.assertEqual(poly.order_polygon(rectangle, [p2, p3]), [p2, p3, p0, p1])
            self.assertEqual(poly.order_polygon(rectangle, [p3, p0]), [p3, p0, p1, p2])
            self.assertEqual(poly.order_polygon(rectangle, [p0, p3]), [p0, p3, p2, p1])

        print('--- test closed rectangless ---')
        for rectangle in self.rectangles:
            rectangle_close = rectangle
            rectangle_close.append(rectangle[0])
            self.assertEqual(poly.order_polygon(rectangle_close, [p0, p1]), [p0, p1, p2, p3, p0])
            self.assertEqual(poly.order_polygon(rectangle_close, [p1, p0]), [p1, p0, p3, p2, p1])
            self.assertEqual(poly.order_polygon(rectangle_close, [p1, p2]), [p1, p2, p3, p0, p1])
            self.assertEqual(poly.order_polygon(rectangle_close, [p2, p1]), [p2, p1, p0, p3, p2])
            self.assertEqual(poly.order_polygon(rectangle_close, [p3, p2]), [p3, p2, p1, p0, p3])
            self.assertEqual(poly.order_polygon(rectangle_close, [p2, p3]), [p2, p3, p0, p1, p2])
            self.assertEqual(poly.order_polygon(rectangle_close, [p3, p0]), [p3, p0, p1, p2, p3])
            self.assertEqual(poly.order_polygon(rectangle_close, [p0, p3]), [p0, p3, p2, p1, p0])

            
class PolyMergeTests(unittest.TestCase):

    def setUp(self):
        self.triangles = [
         ([p0, p1, p2], [p0, p2, p3], [p2, p0], [p0, p1, p2, p3, p0]),
         ([p0, p1, p2], [p0, p2, p3], [p0, p2], [p2, p1, p0, p3, p2]),
         ([p0, p1, p3], [p1, p2, p3], [p1, p3], [p3, p0, p1, p2, p3]),
         ([p0, p1, p3], [p1, p2, p3], [p3, p1], [p1, p0, p3, p2, p1]),
        ]
        self.rectangles = [
         ([p0, p1, p2, p3], [p0, p3, p4, p5], [p0, p3], [p3, p2, p1, p0, p5, p4, p3]),
        ]
        self.mixed = [
         ([p0, p1, p2], [p2, p4, p5, p0], [p0, p2], [p2, p1, p0, p5, p4, p2]),
         ([p0, p1, p2], [p2, p4, p5, p0], [p2, p0], [p0, p1, p2, p4, p5, p0]),
         ([p0, p1, p2], [p2, p3, p4, p5, p0], [p0, p2], [p2, p1, p0, p5, p4, p3, p2]),
        ]
                            

    def test_merge_triangles(self):
        for triangle1, triangle2, segment, expected in self.triangles:
            self.assertEqual(poly.merge_2polygons(triangle1, triangle2, segment), expected)
            triangle1_close = triangle1
            triangle1_close.append(triangle1[0])
            triangle2_close = triangle2
            triangle2_close.append(triangle2[0])
            self.assertEqual(poly.merge_2polygons(triangle1_close, triangle2_close, segment), expected)

    def test_merge_rectangles(self):
        for rectangle1, rectangle2, segment, expected in self.rectangles:
            self.assertEqual(poly.merge_2polygons(rectangle1, rectangle2, segment), expected)
            rectangle1_close = rectangle1
            rectangle1_close.append(rectangle1[0])
            rectangle2_close = rectangle2
            rectangle2_close.append(rectangle2[0])
            self.assertEqual(poly.merge_2polygons(rectangle1_close, rectangle2_close, segment), expected)
            
    def test_merge_mixed(self):
        for poly1, poly2, segment, expected in self.mixed:
            self.assertEqual(poly.merge_2polygons(poly1, poly2, segment), expected)
            poly1_close = poly1
            poly1_close.append(poly1[0])
            poly2_close = poly2
            poly2_close.append(poly2[0])
            self.assertEqual(poly.merge_2polygons(poly1_close, poly2_close, segment), expected)

            
class PolyMergeConnectedTests(unittest.TestCase):

    def setUp(self):
        self.datasets = [
         # 2 triangles with a common edge => a rectangle
         # (([p0, p1, p2, p0], [p0, p2, p3, p0]), [[p0, p1, p2, p3, p0]]),
         # 2 triangles without a common edge => 2 triangles
         # (([p0, p1, p2, p0], [p0, p4, p5, p0]), ([p0, p1, p2, p0], [p0, p4, p5, p0])),
         # 4 triangles with common edges => a rectangle
         (([p0, p1, p2, p0], [p0, p2, p3, p0], [p0, p5, p3, p0], (p3, p4, p5, p3)), [[p0, p1, p2, p3, p4, p5, p0]]),
        ]

    def test_merge_connected(self):
        for data, result in self.datasets:
            self.assertEqual(poly.merge_connected_polygons(data), result)


if __name__ == '__main__':
    unittest.main()
