# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Collision-aware placement of Plotly annotations inside a plot area."""

from dataclasses import dataclass
from functools import cmp_to_key
import math
from typing import Iterable, Sequence

try:
    from spinorama.annotations_rust import c_place_annotations as _c_place_annotations
except ImportError:
    _c_place_annotations = None


Rect = tuple[float, float, float, float]
Point = tuple[float, float]


@dataclass(frozen=True)
class AnnotationRequest:
    """An axis-space annotation anchor plus its layout preferences."""

    key: str
    x: float
    y: float
    yref: str
    text: str
    color: str
    priority: int = 0
    preferred_lanes: tuple[str, ...] = ("middle", "lower", "upper")
    preferred_direction: str | None = None


@dataclass(frozen=True)
class AnnotationGeometry:
    """Pixel geometry used by the placement solver.

    ``x_range`` contains the values used by Plotly's axis range. For a log
    axis this is the log10 range, while trace x values are converted by the
    solver before mapping them to pixels.
    """

    width: float
    height: float
    margin: dict[str, float]
    x_range: tuple[float, float]
    y_ranges: dict[str, tuple[float, float]]
    x_scale: str = "linear"
    font_size: float = 10
    label_pad: float = 5
    x_domain: tuple[float, float] = (0.0, 1.0)
    y_domain: tuple[float, float] = (0.0, 1.0)
    grid_x: tuple[float, ...] = ()
    grid_y: dict[str, tuple[float, ...]] | None = None

    @property
    def plot_rect(self) -> Rect:
        inner_left = float(self.margin.get("l", 0))
        inner_top = float(self.margin.get("t", 0))
        inner_right = self.width - float(self.margin.get("r", 0))
        inner_bottom = self.height - float(self.margin.get("b", 0))
        inner_width = inner_right - inner_left
        inner_height = inner_bottom - inner_top
        x_start, x_end = self.x_domain
        y_start, y_end = self.y_domain
        left = inner_left + x_start * inner_width
        right = inner_left + x_end * inner_width
        # Plotly axis domains are normalized from the bottom, while pixels
        # are normalized from the top.
        top = inner_top + (1.0 - y_end) * inner_height
        bottom = inner_top + (1.0 - y_start) * inner_height
        return left, top, right, bottom

    def grid_x_pixels(self) -> tuple[float, ...]:
        left, _, right, _ = self.plot_rect
        return tuple(
            _value_to_pixel(value, self.x_range, left, right) for value in self.grid_x
        )

    def grid_y_pixels(self, yref: str) -> tuple[float, ...]:
        if self.grid_y is None:
            return ()
        _, top, _, bottom = self.plot_rect
        values = self.grid_y.get(yref, ())
        value_range = self.y_ranges.get(yref)
        if value_range is None:
            return ()
        return tuple(_value_to_pixel(value, value_range, bottom, top) for value in values)


@dataclass(frozen=True)
class PlacedAnnotation:
    """The pixel placement chosen for one annotation."""

    request: AnnotationRequest
    anchor: Point
    center: Point | None
    size: tuple[float, float]
    hidden: bool = False


_LANE_FRACTIONS = {
    "top": 0.12,
    "upper": 0.28,
    "middle": 0.50,
    "lower": 0.70,
    "bottom": 0.86,
}

_TRACE_CLEARANCE = 14.0
_LEADER_START_CLEARANCE = 12.0
_LEADER_TRACE_CLEARANCE = 3.0
_MIN_LEADER_LENGTH = 48.0
_GRID_ALIGNMENT_TOLERANCE = 8.0
_GRID_ALIGNMENT_WEIGHT = 0.35


def estimate_annotation_size(
    text: str, font_size: float = 10, label_pad: float = 5
) -> tuple[float, float]:
    """Estimate a Plotly annotation's rendered size in pixels.

    Plotly renders these labels as SVG text. A conservative estimate is more
    useful than an exact font metric here: it keeps labels apart before the
    browser has rendered the figure and makes the result deterministic for
    static exports.
    """

    lines = str(text).split("<br>")
    longest_line = max((len(line) for line in lines), default=1)
    width = longest_line * font_size * 0.62 + 2 * label_pad + 2
    height = len(lines) * font_size * 1.35 + 2 * label_pad + 2
    return width, height


def _rect_from_center(center: Point, size: tuple[float, float]) -> Rect:
    width, height = size
    x, y = center
    return x - width / 2, y - height / 2, x + width / 2, y + height / 2


def _rect_overlap(first: Rect, second: Rect) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0
    return (right - left) * (bottom - top)


def _expand_rect(rect: Rect, padding: float) -> Rect:
    return rect[0] - padding, rect[1] - padding, rect[2] + padding, rect[3] + padding


def _points_equal(first: Point, second: Point) -> bool:
    return abs(first[0] - second[0]) < 0.001 and abs(first[1] - second[1]) < 0.001


def _cross(first: Point, second: Point, third: Point) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def _between(value: float, first: float, second: float) -> bool:
    return min(first, second) - 0.001 <= value <= max(first, second) + 0.001


def _segments_intersect(first_start: Point, first_end: Point, second_start: Point, second_end: Point) -> bool:
    """Return whether two arrow center-lines cross, ignoring shared anchors."""

    if any(
        _points_equal(first, second)
        for first in (first_start, first_end)
        for second in (second_start, second_end)
    ):
        return False

    first_cross = _cross(first_start, first_end, second_start)
    second_cross = _cross(first_start, first_end, second_end)
    third_cross = _cross(second_start, second_end, first_start)
    fourth_cross = _cross(second_start, second_end, first_end)
    first_proper = (first_cross > 0 and second_cross < 0) or (first_cross < 0 and second_cross > 0)
    second_proper = (third_cross > 0 and fourth_cross < 0) or (third_cross < 0 and fourth_cross > 0)
    if first_proper and second_proper:
        return True

    return (
        abs(first_cross) < 0.001
        and _between(second_start[0], first_start[0], first_end[0])
        and _between(second_start[1], first_start[1], first_end[1])
    ) or (
        abs(second_cross) < 0.001
        and _between(second_end[0], first_start[0], first_end[0])
        and _between(second_end[1], first_start[1], first_end[1])
    ) or (
        abs(third_cross) < 0.001
        and _between(first_start[0], second_start[0], second_end[0])
        and _between(first_start[1], second_start[1], second_end[1])
    ) or (
        abs(fourth_cross) < 0.001
        and _between(first_end[0], second_start[0], second_end[0])
        and _between(first_end[1], second_start[1], second_end[1])
    )


def _point_in_rect(point: Point, rect: Rect) -> bool:
    return rect[0] < point[0] < rect[2] and rect[1] < point[1] < rect[3]


def _point_in_or_on_rect(point: Point, rect: Rect) -> bool:
    return rect[0] <= point[0] <= rect[2] and rect[1] <= point[1] <= rect[3]


def _segment_intersects_rect(start: Point, end: Point, rect: Rect) -> bool:
    """Return whether a line segment touches or crosses a rectangle."""
    if _point_in_or_on_rect(start, rect) or _point_in_or_on_rect(end, rect):
        return True
    edges = (
        ((rect[0], rect[1]), (rect[2], rect[1])),
        ((rect[2], rect[1]), (rect[2], rect[3])),
        ((rect[2], rect[3]), (rect[0], rect[3])),
        ((rect[0], rect[3]), (rect[0], rect[1])),
    )
    return any(_segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in edges)


def _point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    segment_x = end[0] - start[0]
    segment_y = end[1] - start[1]
    segment_length_squared = segment_x * segment_x + segment_y * segment_y
    if segment_length_squared == 0:
        return math.dist(point, start)
    projection = (
        (point[0] - start[0]) * segment_x + (point[1] - start[1]) * segment_y
    ) / segment_length_squared
    projection = min(1.0, max(0.0, projection))
    closest = (start[0] + projection * segment_x, start[1] + projection * segment_y)
    return math.dist(point, closest)


def _segment_distance(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> float:
    if _segments_intersect(first_start, first_end, second_start, second_end):
        return 0.0
    return min(
        _point_to_segment_distance(first_start, second_start, second_end),
        _point_to_segment_distance(first_end, second_start, second_end),
        _point_to_segment_distance(second_start, first_start, first_end),
        _point_to_segment_distance(second_end, first_start, first_end),
    )


def _leader_crosses_trace(
    anchor: Point,
    center: Point,
    trace_segments: Sequence[tuple[Point, Point]],
) -> bool:
    """Return whether the visible part of a leader is too close to a curve.

    The first few pixels are intentionally exempt: every valid leader starts
    on its own curve. The rest of the arrow must clear the curve polyline
    supplied by the caller.
    """

    leader_length = math.dist(anchor, center)
    if leader_length <= _LEADER_START_CLEARANCE:
        return True
    fraction = _LEADER_START_CLEARANCE / leader_length
    visible_start = (
        anchor[0] + (center[0] - anchor[0]) * fraction,
        anchor[1] + (center[1] - anchor[1]) * fraction,
    )
    return any(
        _segment_distance(visible_start, center, trace_start, trace_end)
        <= _LEADER_TRACE_CLEARANCE
        for trace_start, trace_end in trace_segments
    )


def _leader_curve_penalty(
    anchor: Point,
    center: Point,
    trace_segments: Sequence[tuple[Point, Point]],
) -> float:
    """Penalize near misses and crossings when a global route is impossible."""

    leader_length = math.dist(anchor, center)
    if leader_length <= _LEADER_START_CLEARANCE:
        return 1000.0
    fraction = _LEADER_START_CLEARANCE / leader_length
    visible_start = (
        anchor[0] + (center[0] - anchor[0]) * fraction,
        anchor[1] + (center[1] - anchor[1]) * fraction,
    )
    penalty = 0.0
    for trace_start, trace_end in trace_segments:
        distance = _segment_distance(visible_start, center, trace_start, trace_end)
        if distance <= _LEADER_TRACE_CLEARANCE:
            penalty += 100.0
        elif distance < 20.0:
            penalty += 20.0 - distance
    return penalty


def _segment_crosses_rect(start: Point, end: Point, rect: Rect) -> bool:
    # An arrow that starts inside a label is already attached to that label's
    # curve; do not make the fallback solver hide every candidate in that case.
    if _point_in_rect(start, rect):
        return False
    return _segment_intersects_rect(start, end, rect)


def _value_to_pixel(
    value: float, value_range: tuple[float, float], start: float, end: float
) -> float:
    minimum, maximum = value_range
    if maximum == minimum:
        return (start + end) / 2
    fraction = (value - minimum) / (maximum - minimum)
    return start + fraction * (end - start)


def _pixel_to_value(
    pixel: float, value_range: tuple[float, float], start: float, end: float
) -> float:
    minimum, maximum = value_range
    if start == end:
        return minimum
    fraction = (pixel - start) / (end - start)
    return minimum + fraction * (maximum - minimum)


def _anchor_pixel(request: AnnotationRequest, geometry: AnnotationGeometry) -> Point:
    left, top, right, bottom = geometry.plot_rect
    x = _value_to_pixel(request.x, geometry.x_range, left, right)
    y_min, y_max = geometry.y_ranges[request.yref]
    # Pixel y grows downwards, while data y grows upwards.
    y = _value_to_pixel(request.y, (y_min, y_max), bottom, top)
    return x, y


def _candidate_centers(
    request: AnnotationRequest,
    anchor: Point,
    size: tuple[float, float],
    geometry: AnnotationGeometry,
) -> Iterable[tuple[Point, int]]:
    left, top, right, bottom = geometry.plot_rect
    label_width, label_height = size
    x_min = left + label_width / 2 + geometry.label_pad
    x_max = right - label_width / 2 - geometry.label_pad
    y_min = top + label_height / 2 + geometry.label_pad
    y_max = bottom - label_height / 2 - geometry.label_pad
    if x_min > x_max or y_min > y_max:
        return

    def add_candidate(center: Point, lane_rank: int):
        clamped = (
            min(x_max, max(x_min, center[0])),
            min(y_max, max(y_min, center[1])),
        )
        key = (round(clamped[0]), round(clamped[1]))
        if key in seen:
            return None
        seen.add(key)
        return clamped, lane_rank

    # Try short, local offsets before the full semantic lanes. The solver's
    # direction penalty decides whether an above/below offset is valid, while
    # the distance term keeps arrows compact whenever space permits it.
    lane_names = list(request.preferred_lanes)
    lane_names.extend(name for name in _LANE_FRACTIONS if name not in lane_names)
    seen: set[tuple[int, int]] = set()

    vertical_offset = max(_MIN_LEADER_LENGTH, size[1] / 2 + _TRACE_CLEARANCE + 6)
    local_offsets = (
        (0, -vertical_offset),
        (0, vertical_offset),
        (-48, -vertical_offset),
        (48, -vertical_offset),
        (-48, vertical_offset),
        (48, vertical_offset),
        (0, -2 * vertical_offset),
        (0, 2 * vertical_offset),
        (-96, -2 * vertical_offset),
        (96, -2 * vertical_offset),
        (-96, 2 * vertical_offset),
        (96, 2 * vertical_offset),
    )
    for index, (dx, dy) in enumerate(local_offsets):
        candidate = add_candidate(
            (anchor[0] + dx, anchor[1] + dy), len(lane_names) + index
        )
        if candidate is not None:
            yield candidate

    base_x = (anchor[0], anchor[0] - 48, anchor[0] + 48, anchor[0] - 96, anchor[0] + 96)
    base_y = (
        anchor[1] - vertical_offset,
        anchor[1] + vertical_offset,
        anchor[1] - 2 * vertical_offset,
        anchor[1] + 2 * vertical_offset,
    )
    for grid_x in geometry.grid_x_pixels():
        for center_x in (grid_x, grid_x - label_width / 2, grid_x + label_width / 2):
            for center_y in base_y:
                candidate = add_candidate((center_x, center_y), 1)
                if candidate is not None:
                    yield candidate
    for grid_y in geometry.grid_y_pixels(request.yref):
        for center_y in (grid_y, grid_y - label_height / 2, grid_y + label_height / 2):
            for center_x in base_x:
                candidate = add_candidate((center_x, center_y), 1)
                if candidate is not None:
                    yield candidate

    for lane_rank, lane_name in enumerate(lane_names):
        fraction = _LANE_FRACTIONS[lane_name]
        lane_y = top + fraction * (bottom - top)
        for dx in (0, -100, 100, -190, 190):
            candidate = add_candidate((anchor[0] + dx, lane_y), lane_rank)
            if candidate is not None:
                yield candidate

def _direction_penalty(direction: str | None, anchor: Point, center: Point) -> float:
    if direction == "above":
        return 1000.0 + center[1] - anchor[1] if center[1] >= anchor[1] else 0.0
    if direction == "below":
        return 1000.0 + anchor[1] - center[1] if center[1] <= anchor[1] else 0.0
    return 0.0


def _leader_geometry_penalty(anchor: Point, center: Point) -> float:
    """Prefer a label above-left of its curve anchor over vertical leaders."""

    dx = center[0] - anchor[0]
    dy = center[1] - anchor[1]
    if abs(dx) < 12:
        return 80.0
    if dy < 0 and dx < 0:
        return 0.0
    if abs(dy) < 12:
        return 12.0
    if dy < 0:
        return 25.0
    return 35.0


def _curve_penalty(
    rect: Rect,
    points: Sequence[Point],
    segments: Sequence[tuple[Point, Point]] = (),
) -> float | None:
    penalty = 0.0
    clearance_rect = _expand_rect(rect, _TRACE_CLEARANCE)
    for point in points:
        point_rect = _rect_from_center(point, (5, 5))
        if _rect_overlap(rect, point_rect) > 0:
            return None
        if _rect_overlap(clearance_rect, point_rect) > 0:
            penalty += 20.0
    for start, end in segments:
        if _segment_intersects_rect(start, end, rect):
            return None
        if _segment_intersects_rect(start, end, clearance_rect):
            penalty += 20.0
    return penalty


def _grid_alignment_penalty(
    rect: Rect,
    x_lines: Sequence[float],
    y_lines: Sequence[float],
) -> float:
    """Softly prefer a label edge or center to sit on a visible grid line."""

    def axis_penalty(edges: tuple[float, float, float], lines: Sequence[float]) -> float:
        if not lines:
            return 0.0
        distance = min(abs(edge - line) for edge in edges for line in lines)
        return max(0.0, distance - _GRID_ALIGNMENT_TOLERANCE)

    x_edges = (rect[0], (rect[0] + rect[2]) / 2, rect[2])
    y_edges = (rect[1], (rect[1] + rect[3]) / 2, rect[3])
    return _GRID_ALIGNMENT_WEIGHT * (
        axis_penalty(x_edges, x_lines) + axis_penalty(y_edges, y_lines)
    )


def place_annotations(
    requests: Sequence[AnnotationRequest],
    geometry: AnnotationGeometry,
    trace_points: Iterable[tuple[float, float, str]] = (),
    reserved_rects: Iterable[Rect] = (),
    trace_segments: Iterable[
        tuple[Point, Point, str] | tuple[Point, Point, str, str]
    ] = (),
) -> list[PlacedAnnotation]:
    """Place annotations without overlapping labels, curves, or leaders.

    Requests are placed by descending priority. Actual contact with a trace,
    existing label, or reserved region makes a candidate invalid. Leaders
    also need to clear the trace after their attachment point. A small
    clearance corridor around traces contributes a soft penalty. This keeps
    labels readable while preserving the strongest annotations when space is
    scarce.
    """

    # Keep the Python implementation as a source-compatible fallback for
    # environments where Maturin's optional extension was not built.
    trace_points = tuple(trace_points)
    trace_segments = tuple(trace_segments)
    if _c_place_annotations is None:
        raise RuntimeError(
            "The Rust annotation solver is required; run scripts/setup.sh to install the Maturin extension."
        )

    if _c_place_annotations is not None:
        raw_requests = [
            (
                request.key,
                request.x,
                request.y,
                request.yref,
                request.text,
                request.priority,
                list(request.preferred_lanes),
                request.preferred_direction,
            )
            for request in requests
        ]
        margin = geometry.margin
        raw_segments = [
            (
                start[0],
                start[1],
                end[0],
                end[1],
                yref,
                key if len(segment) == 4 else None,
            )
            for segment in trace_segments
            if len(segment) in (3, 4)
            for start, end, yref, *key_values in [segment]
            for key in [key_values[0] if key_values else None]
        ]
        placements = _c_place_annotations(
            raw_requests,
            geometry.width,
            geometry.height,
            (
                margin.get("l", 0.0),
                margin.get("r", 0.0),
                margin.get("t", 0.0),
                margin.get("b", 0.0),
            ),
            geometry.x_range,
            [
                (axis, value_range[0], value_range[1])
                for axis, value_range in geometry.y_ranges.items()
            ],
            geometry.x_scale == "log",
            geometry.font_size,
            geometry.label_pad,
            geometry.x_domain,
            geometry.y_domain,
            list(geometry.grid_x),
            list((geometry.grid_y or {}).items()),
            list(trace_points),
            list(reserved_rects),
            raw_segments,
        )
        return [
            PlacedAnnotation(
                request,
                _anchor_pixel(request, geometry),
                center,
                estimate_annotation_size(request.text, geometry.font_size, geometry.label_pad),
                hidden,
            )
            for request, (center, hidden) in zip(requests, placements, strict=True)
        ]

    points_by_axis: dict[str, list[Point]] = {axis: [] for axis in geometry.y_ranges}
    segments_by_axis: dict[str, list[tuple[Point, Point]]] = {
        axis: [] for axis in geometry.y_ranges
    }
    segments_by_curve: dict[tuple[str, str], list[tuple[Point, Point]]] = {}
    all_trace_segments: list[tuple[Point, Point]] = []
    left, top, right, bottom = geometry.plot_rect
    for x, y, yref in trace_points:
        if yref not in geometry.y_ranges or not math.isfinite(x) or not math.isfinite(y):
            continue
        x_value = math.log10(x) if geometry.x_scale == "log" and x > 0 else x
        if not math.isfinite(x_value):
            continue
        x_pixel = _value_to_pixel(x_value, geometry.x_range, left, right)
        y_min, y_max = geometry.y_ranges[yref]
        y_pixel = _value_to_pixel(y, (y_min, y_max), bottom, top)
        if left <= x_pixel <= right and top <= y_pixel <= bottom:
            points_by_axis[yref].append((x_pixel, y_pixel))
    for trace_segment in trace_segments:
        if len(trace_segment) not in (3, 4):
            continue
        start, end, yref = trace_segment[:3]
        if yref not in geometry.y_ranges:
            continue
        if not all(math.isfinite(value) for value in (*start, *end)):
            continue
        segments_by_axis[yref].append((start, end))
        all_trace_segments.append((start, end))
        if len(trace_segment) == 4:
            curve_key = trace_segment[3]
            segments_by_curve.setdefault((yref, curve_key), []).append((start, end))

    all_points = tuple(point for axis_points in points_by_axis.values() for point in axis_points)
    reserved = tuple(reserved_rects)
    placed: list[PlacedAnnotation | None] = [None] * len(requests)
    occupied: list[Rect] = []
    arrows: list[tuple[Point, Point]] = []

    def compare_requests(first: tuple[int, AnnotationRequest], second: tuple[int, AnnotationRequest]) -> int:
        first_index, first_request = first
        second_index, second_request = second
        if (
            first_request.preferred_direction == "above"
            and second_request.preferred_direction == "above"
            and first_request.x != second_request.x
        ):
            return -1 if first_request.x > second_request.x else 1
        if first_request.priority != second_request.priority:
            return -1 if first_request.priority > second_request.priority else 1
        return first_index - second_index

    ordered = sorted(enumerate(requests), key=cmp_to_key(compare_requests))
    for request_index, request in ordered:
        anchor = _anchor_pixel(request, geometry)
        size = estimate_annotation_size(request.text, geometry.font_size, geometry.label_pad)
        best: tuple[float, Point, Rect] | None = None
        axis_segments = segments_by_axis.get(request.yref, [])
        leader_segments = segments_by_curve.get((request.yref, request.key), axis_segments)
        candidates = tuple(_candidate_centers(request, anchor, size, geometry))
        for require_global_clearance in (True, False):
            phase_best: tuple[float, Point, Rect] | None = None
            for center, lane_rank in candidates:
                rect = _rect_from_center(center, size)
                distance = math.dist(center, anchor)
                if distance < _MIN_LEADER_LENGTH:
                    continue
                if _direction_penalty(request.preferred_direction, anchor, center) > 0:
                    continue
                if not (
                    left <= rect[0]
                    and rect[2] <= right
                    and top <= rect[1]
                    and rect[3] <= bottom
                ):
                    continue
                if any(_rect_overlap(rect, other) > 0 for other in occupied):
                    continue
                if any(_rect_overlap(rect, other) > 0 for other in reserved):
                    continue
                if any(
                    _segments_intersect(anchor, center, arrow_start, arrow_end)
                    for arrow_start, arrow_end in arrows
                ):
                    continue
                if any(_segment_crosses_rect(anchor, center, other) for other in occupied):
                    continue
                if any(
                    _segment_crosses_rect(arrow_start, arrow_end, rect)
                    for arrow_start, arrow_end in arrows
                ):
                    continue
                if require_global_clearance:
                    if _leader_crosses_trace(anchor, center, all_trace_segments):
                        continue
                    leader_score = 0.0
                else:
                    if _leader_crosses_trace(anchor, center, leader_segments):
                        continue
                    leader_score = _leader_curve_penalty(
                        anchor, center, all_trace_segments
                    )

                cross_axis = request.yref == "y2"
                curve_score = _curve_penalty(
                    rect,
                    all_points if cross_axis else points_by_axis.get(request.yref, []),
                    all_trace_segments if cross_axis else axis_segments,
                )
                if curve_score is None:
                    continue
                score = (
                    distance
                    + lane_rank * 2.0
                    + _leader_geometry_penalty(anchor, center)
                    + curve_score
                    + leader_score
                    + _grid_alignment_penalty(
                        rect,
                        geometry.grid_x_pixels(),
                        geometry.grid_y_pixels(request.yref),
                    )
                )
                if phase_best is None or score < phase_best[0]:
                    phase_best = score, center, rect
            if phase_best is not None:
                best = phase_best
                break

        if best is None:
            placed[request_index] = PlacedAnnotation(request, anchor, None, size, hidden=True)
            continue

        _, center, rect = best
        occupied.append(rect)
        arrows.append((anchor, center))
        placed[request_index] = PlacedAnnotation(request, anchor, center, size)

    return [placement for placement in placed if placement is not None]


def annotation_dicts(
    placements: Sequence[PlacedAnnotation],
    *,
    visible: bool,
    font_size: float = 10,
    background_color: str = "rgba(255, 255, 255, 0.86)",
    geometry: AnnotationGeometry | None = None,
) -> list[dict]:
    """Convert placements to Plotly annotation dictionaries."""

    annotations = []
    for placement in placements:
        request = placement.request
        annotation = dict(
            x=request.x,
            y=request.y,
            xref="x",
            yref=request.yref,
            text=request.text,
            font=dict(size=font_size, color=request.color),
            bordercolor=request.color,
            borderwidth=1,
            borderpad=3,
            bgcolor=background_color,
            align="center",
            showarrow=True,
            arrowhead=2,
            arrowcolor=request.color,
            xanchor="center",
            yanchor="middle",
            axref="x" if geometry is not None else "pixel",
            ayref=request.yref if geometry is not None else "pixel",
            visible=visible and not placement.hidden,
        )
        if placement.center is not None:
            if geometry is None:
                annotation["ax"] = round(placement.center[0] - placement.anchor[0])
                annotation["ay"] = round(placement.center[1] - placement.anchor[1])
            else:
                left, top, right, bottom = geometry.plot_rect
                annotation["ax"] = _pixel_to_value(
                    placement.center[0], geometry.x_range, left, right
                )
                annotation["ay"] = _pixel_to_value(
                    placement.center[1],
                    geometry.y_ranges[request.yref],
                    bottom,
                    top,
                )
        else:
            annotation["ax"] = 0
            annotation["ay"] = 0
        if placement.hidden:
            # Annotation objects do not expose Plotly's general ``meta`` field.
            # ``name`` is a supported, serialized field and gives the JS
            # configuration layer a stable way to preserve this decision.
            annotation["name"] = f"layout-hidden:{request.key}"
        else:
            annotation["name"] = f"spinorama:{request.key}"
        annotations.append(annotation)
    return annotations
