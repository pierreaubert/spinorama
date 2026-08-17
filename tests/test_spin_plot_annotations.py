# -*- coding: utf-8 -*-

import unittest

import numpy as np
import pandas as pd

from spinorama.plot.annotations import (
    AnnotationGeometry,
    AnnotationRequest,
    annotation_dicts,
    estimate_annotation_size,
    place_annotations,
)
from spinorama.plot.spinorama import plot_spinorama


class AnnotationLayoutTests(unittest.TestCase):
    def setUp(self):
        self.geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(1.3, 4.3),
            y_ranges={"y": (-45, 5), "y2": (-5, 45)},
        )

    def test_estimate_annotation_size_is_conservative_for_long_labels(self):
        short = estimate_annotation_size("slope")
        long = estimate_annotation_size("-1.43 db/oct sm 0.24")
        self.assertGreater(long[0], short[0])
        self.assertEqual(short[1], long[1])

    def test_places_labels_without_overlapping_each_other(self):
        requests = [
            AnnotationRequest(
                key="primary",
                x=3.5,
                y=1,
                yref="y",
                text="primary slope",
                color="blue",
                priority=100,
                preferred_lanes=("lower", "middle"),
            ),
            AnnotationRequest(
                key="secondary",
                x=3.55,
                y=-2,
                yref="y",
                text="secondary slope",
                color="red",
                priority=90,
                preferred_lanes=("lower", "middle"),
            ),
        ]
        placements = place_annotations(requests, self.geometry)
        self.assertEqual(len(placements), 2)
        self.assertFalse(any(placement.hidden for placement in placements))

        first = placements[0]
        second = placements[1]
        self.assertIsNotNone(first.center)
        self.assertIsNotNone(second.center)
        first_rect = (
            first.center[0] - first.size[0] / 2,
            first.center[1] - first.size[1] / 2,
            first.center[0] + first.size[0] / 2,
            first.center[1] + first.size[1] / 2,
        )
        second_rect = (
            second.center[0] - second.size[0] / 2,
            second.center[1] - second.size[1] / 2,
            second.center[0] + second.size[0] / 2,
            second.center[1] + second.size[1] / 2,
        )
        non_overlapping = (
            first_rect[2] <= second_rect[0]
            or second_rect[2] <= first_rect[0]
            or first_rect[3] <= second_rect[1]
            or second_rect[3] <= first_rect[1]
        )
        self.assertTrue(non_overlapping)
        self.assertTrue(first.center[1] > first.anchor[1] or second.center[1] > second.anchor[1])

    def test_suppresses_annotation_when_plot_is_smaller_than_label(self):
        geometry = AnnotationGeometry(
            width=80,
            height=80,
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            x_range=(0, 1),
            y_ranges={"y": (0, 1)},
        )
        request = AnnotationRequest(
            key="too-large",
            x=0.5,
            y=0.5,
            yref="y",
            text="this label cannot fit",
            color="black",
        )
        placement = place_annotations([request], geometry)[0]
        self.assertTrue(placement.hidden)
        self.assertFalse(annotation_dicts([placement], visible=True)[0]["visible"])
        self.assertTrue(
            annotation_dicts([placement], visible=True)[0]["name"].startswith("layout-hidden:")
        )


class SpinoramaAnnotationIntegrationTests(unittest.TestCase):
    def test_cea2034_annotations_use_internal_lanes_without_margin_changes(self):
        freq = np.logspace(np.log10(20), np.log10(20000), 160)
        base = 1.5 * np.sin(np.log(freq))
        spin = pd.DataFrame(
            {
                "Freq": freq,
                "On Axis": base + 1,
                "Listening Window": base,
                "Early Reflections": base - 3,
                "Sound Power": base - 5,
                "Early Reflections DI": np.full_like(freq, 5),
                "Sound Power DI": np.full_like(freq, 10),
            }
        )
        params = {"width": 1000, "height": 700, "layout": ""}
        figure = plot_spinorama(spin, params, {}, False, (100, 18000))

        self.assertEqual(figure.layout.margin.l, 10)
        self.assertEqual(figure.layout.margin.r, 10)
        self.assertEqual(figure.layout.margin.t, 80)
        self.assertEqual(figure.layout.margin.b, 10)
        self.assertEqual(len(figure.layout.annotations), 6)
        self.assertTrue(
            all(annotation.axref == "x domain" for annotation in figure.layout.annotations)
        )
        self.assertTrue(all(annotation.bgcolor for annotation in figure.layout.annotations))
        self.assertTrue(any(annotation.ay > 0 for annotation in figure.layout.annotations))


if __name__ == "__main__":
    unittest.main()
