# -*- coding: utf-8 -*-

import math
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from spinorama.plot.annotations import (
    AnnotationGeometry,
    AnnotationRequest,
    _curve_penalty,
    _anchor_pixel,
    _rect_from_center,
    _leader_crosses_trace,
    annotation_dicts,
    estimate_annotation_size,
    place_annotations,
)
from spinorama.plot.spinorama import plot_spinorama
from scripts.plot_cea2034_annotations import show_annotations
from spinorama.plot import annotations as annotations_module


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

    def test_log_annotation_anchor_uses_axis_coordinate(self):
        geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(1, 4),
            y_ranges={"y": (0, 1)},
            x_scale="log",
        )
        anchor = _anchor_pixel(
            AnnotationRequest("log", 2.5, 0.5, "y", "label", "black"), geometry
        )

        self.assertAlmostEqual(anchor[0], 400.0)

    def test_placements_keep_label_rectangles_inside_plot_domain(self):
        geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(1, 4),
            y_ranges={"y": (0, 1)},
            x_domain=(0.0, 0.8),
        )
        placement = place_annotations(
            [AnnotationRequest("edge", 4, 0.5, "y", "edge label", "black")], geometry
        )[0]
        left, top, right, bottom = geometry.plot_rect
        rect = _rect_from_center(placement.center, placement.size)

        self.assertGreaterEqual(rect[0], left)
        self.assertLessEqual(rect[2], right)
        self.assertGreaterEqual(rect[1], top)
        self.assertLessEqual(rect[3], bottom)

    def test_grid_alignment_is_a_soft_preference(self):
        geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(0, 1),
            y_ranges={"y": (0, 1)},
            grid_y={"y": (0.6,)},
        )
        request = AnnotationRequest("grid", 0.5, 0.5, "y", "grid label", "black")
        placement = place_annotations([request], geometry)[0]

        self.assertFalse(placement.hidden)
        rect = _rect_from_center(placement.center, placement.size)
        grid_pixel = 220.0
        self.assertLessEqual(
            min(abs(edge - grid_pixel) for edge in (rect[1], (rect[1] + rect[3]) / 2, rect[3])),
            8.0,
        )

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
        self.assertTrue(
            any(
                abs(placement.center[0] - placement.anchor[0]) >= 12
                for placement in placements
            )
        )

    def test_keeps_primary_curve_labels_above_the_curves_and_short(self):
        requests = [
            AnnotationRequest(
                key="On Axis",
                x=3.5,
                y=1,
                yref="y",
                text="0.26 db/oct sm 0.58",
                color="blue",
                priority=100,
                preferred_lanes=("top", "upper", "middle"),
                preferred_direction="above",
            ),
            AnnotationRequest(
                key="Listening Window",
                x=3.8,
                y=0,
                yref="y",
                text="-0.04 db/oct sm 0.44",
                color="orange",
                priority=95,
                preferred_lanes=("top", "upper", "middle"),
                preferred_direction="above",
            ),
        ]
        placements = place_annotations(requests, self.geometry)
        first, second = placements

        self.assertLess(first.center[1], first.anchor[1])
        self.assertLess(second.center[1], second.anchor[1])
        self.assertLess(math.dist(first.center, first.anchor), 120)

        def rect(placement):
            half_width, half_height = placement.size[0] / 2, placement.size[1] / 2
            return (
                placement.center[0] - half_width,
                placement.center[1] - half_height,
                placement.center[0] + half_width,
                placement.center[1] + half_height,
            )

        first_rect = rect(first)
        second_rect = rect(second)
        self.assertTrue(
            first_rect[2] <= second_rect[0]
            or second_rect[2] <= first_rect[0]
            or first_rect[3] <= second_rect[1]
            or second_rect[3] <= first_rect[1]
        )

    def test_keeps_labels_clear_of_nearby_trace_points(self):
        geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(1.3, 4.3),
            y_ranges={"y": (-45, 10)},
        )
        requests = [
            AnnotationRequest(
                key="On Axis",
                x=3.5,
                y=0,
                yref="y",
                text="0.26 db/oct sm 0.58",
                color="blue",
                priority=100,
                preferred_lanes=("top", "upper", "middle"),
                preferred_direction="above",
            ),
            AnnotationRequest(
                key="Listening Window",
                x=3.8,
                y=-1,
                yref="y",
                text="-0.04 db/oct sm 0.44",
                color="orange",
                priority=95,
                preferred_lanes=("top", "upper", "middle"),
                preferred_direction="above",
            ),
        ]
        placements = place_annotations(
            requests,
            geometry,
            trace_points=((3.5, 0, "y"), (3.8, -1, "y")),
        )

        for placement in placements:
            self.assertLess(placement.center[1] + placement.size[1] / 2, placement.anchor[1] - 10)

    def test_rejects_curve_segment_crossing_label_between_sampled_points(self):
        rect = (100.0, 100.0, 200.0, 140.0)
        points = ((40.0, 70.0), (260.0, 170.0))
        segments = (((40.0, 70.0), (260.0, 170.0)),)

        self.assertIsNone(_curve_penalty(rect, points, segments))

    def test_directivity_label_avoids_a_curve_on_the_primary_axis(self):
        request = AnnotationRequest(
            key="Sound Power DI",
            x=0.5,
            y=0.5,
            yref="y2",
            text="directivity label",
            color="grey",
            preferred_lanes=("upper", "top", "middle"),
            preferred_direction="above",
        )
        geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(0, 1),
            y_ranges={"y": (0, 1), "y2": (0, 1)},
        )
        primary_curve = (((50.0, 212.0), (750.0, 212.0), "y", "On Axis"),)

        placement = place_annotations([request], geometry, trace_segments=primary_curve)[0]

        self.assertFalse(placement.hidden)
        rect = _rect_from_center(placement.center, placement.size)
        self.assertLess(rect[3], 212.0)

    def test_rejects_leader_that_tracks_curve_after_anchor(self):
        anchor = (400.0, 260.0)
        curve = (((400.0, 260.0), (400.0, 100.0)),)

        self.assertTrue(_leader_crosses_trace(anchor, (400.0, 180.0), curve))
        self.assertFalse(_leader_crosses_trace(anchor, (500.0, 180.0), curve))

    def test_solver_uses_longer_leader_when_short_path_tracks_curve(self):
        request = AnnotationRequest(
            key="curve",
            x=0.5,
            y=0.5,
            yref="y",
            text="curve label",
            color="blue",
            preferred_lanes=("upper",),
        )
        geometry = AnnotationGeometry(
            width=800,
            height=500,
            margin={"l": 50, "r": 50, "t": 60, "b": 40},
            x_range=(0, 1),
            y_ranges={"y": (0, 1)},
        )
        anchor = (400.0, 260.0)
        placements = place_annotations(
            [request],
            geometry,
            trace_segments=((anchor, (400.0, 60.0), "y", "curve"),),
        )

        placement = placements[0]
        self.assertFalse(placement.hidden)
        self.assertGreaterEqual(math.dist(placement.anchor, placement.center), 48)
        self.assertFalse(
            _leader_crosses_trace(placement.anchor, placement.center, ((anchor, (400.0, 60.0)),))
        )
        annotation = annotation_dicts(
            [placement], visible=True, geometry=geometry
        )[0]
        self.assertNotIn("standoff", annotation)
        self.assertEqual(annotation["axref"], "x")
        self.assertEqual(annotation["ayref"], "y")
        self.assertNotEqual(annotation["ay"], placement.request.y)

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

    def test_show_annotations_preserves_solver_hidden_labels(self):
        visible = SimpleNamespace(name="spinorama:visible", visible=False)
        hidden = SimpleNamespace(name="layout-hidden:unplaced", visible=False)
        figure = SimpleNamespace(layout=SimpleNamespace(annotations=[visible, hidden]))

        self.assertEqual(show_annotations(figure), 1)
        self.assertTrue(visible.visible)
        self.assertFalse(hidden.visible)


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
            all(annotation.axref in ("x", "pixel") for annotation in figure.layout.annotations)
        )
        self.assertTrue(all(annotation.bgcolor for annotation in figure.layout.annotations))
        self.assertTrue(any(annotation.ay > 0 for annotation in figure.layout.annotations))


    def test_cea2034_annotations_fall_back_to_static_offsets_for_a_long_leader(self):
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
        params = {"width": 1000, "height": 700, "layout": "compact"}

        with mock.patch(
            "spinorama.plot.spinorama.place_annotations",
            return_value=[
                annotations_module.PlacedAnnotation(
                    AnnotationRequest("On Axis", 3.0, 0.0, "y", "label", "blue"),
                    (100.0, 100.0),
                    (400.0, 100.0),
                    (60.0, 24.0),
                    hidden=False,
                )
            ],
        ):
            figure = plot_spinorama(spin, params, {}, False, (100, 18000))

        self.assertEqual(len(figure.layout.annotations), 6)
        self.assertTrue(all(annotation.name.startswith("static:") for annotation in figure.layout.annotations))
        self.assertTrue(all(annotation.axref == "pixel" for annotation in figure.layout.annotations))

    def test_rcf_kx_32_a_is_solved_without_static_fallback(self):
        from pathlib import Path

        from compute_spin import load_speaker_data
        from scripts.plot_cea2034_annotations import (
            detect_format_and_version,
            make_plot_parameters,
            valid_frequency_range,
        )
        from spinorama.speaker import display_spinorama

        project_root = Path(__file__).resolve().parents[1]
        speaker_name = "RCF KX 32-A"
        speaker_dir = project_root / "datas" / "measurements" / speaker_name
        fmt, version = detect_format_and_version(speaker_dir, speaker_name, "auto")
        success, measurements, _ = load_speaker_data(
            str(speaker_dir), speaker_name, fmt, version, None
        )
        self.assertTrue(success)

        figure = display_spinorama(
            measurements,
            make_plot_parameters(1200, 800),
            valid_frequency_range(measurements),
        )
        annotations = list(figure.layout.annotations or ())

        self.assertEqual(len(annotations), 6)
        self.assertTrue(
            all(str(annotation.name).startswith("spinorama:") for annotation in annotations)
        )
        self.assertTrue(all(annotation.ax != annotation.x for annotation in annotations))


if __name__ == "__main__":
    unittest.main()
