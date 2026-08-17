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


Rect = tuple[float, float, float, float]
Point = tuple[float, float]


@dataclass(frozen=True)
class AnnotationRequest:
    """A data-space annotation anchor plus its layout preferences."""

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

    @property
    def plot_rect(self) -> Rect:
        left = float(self.margin.get("l", 0))
        top = float(self.margin.get("t", 0))
        right = self.width - float(self.margin.get("r", 0))
        bottom = self.height - float(self.margin.get("b", 0))
        return left, top, right, bottom


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


def _segment_crosses_rect(start: Point, end: Point, rect: Rect) -> bool:
    # An arrow that starts inside a label is already attached to that label's
    # curve; do not make the fallback solver hide every candidate in that case.
    if _point_in_rect(start, rect):
        return False
    if _point_in_rect(end, rect):
        return True
    edges = (
        ((rect[0], rect[1]), (rect[2], rect[1])),
        ((rect[2], rect[1]), (rect[2], rect[3])),
        ((rect[2], rect[3]), (rect[0], rect[3])),
        ((rect[0], rect[3]), (rect[0], rect[1])),
    )
    return any(_segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in edges)


def _value_to_pixel(
    value: float, value_range: tuple[float, float], start: float, end: float
) -> float:
    minimum, maximum = value_range
    if maximum == minimum:
        return (start + end) / 2
    fraction = (value - minimum) / (maximum - minimum)
    return start + fraction * (end - start)


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

    # Try short, local offsets before the full semantic lanes. The solver's
    # direction penalty decides whether an above/below offset is valid, while
    # the distance term keeps arrows compact whenever space permits it.
    lane_names = list(request.preferred_lanes)
    lane_names.extend(name for name in _LANE_FRACTIONS if name not in lane_names)
    seen: set[tuple[int, int]] = set()

    vertical_offset = max(24.0, size[1] / 2 + _TRACE_CLEARANCE + 6)
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
        center = (
            min(x_max, max(x_min, anchor[0] + dx)),
            min(y_max, max(y_min, anchor[1] + dy)),
        )
        key = (round(center[0]), round(center[1]))
        if key not in seen:
            seen.add(key)
            yield center, len(lane_names) + index

    for lane_rank, lane_name in enumerate(lane_names):
        fraction = _LANE_FRACTIONS[lane_name]
        lane_y = top + fraction * (bottom - top)
        for dx in (0, -100, 100, -190, 190):
            center = (min(x_max, max(x_min, anchor[0] + dx)), min(y_max, max(y_min, lane_y)))
            key = (round(center[0]), round(center[1]))
            if key not in seen:
                seen.add(key)
                yield center, lane_rank

def _direction_penalty(direction: str | None, anchor: Point, center: Point) -> float:
    if direction == "above":
        return 1000.0 + center[1] - anchor[1] if center[1] > anchor[1] else 0.0
    if direction == "below":
        return 1000.0 + anchor[1] - center[1] if center[1] < anchor[1] else 0.0
    return 0.0


def _curve_penalty(rect: Rect, points: Sequence[Point]) -> float | None:
    penalty = 0.0
    clearance_rect = _expand_rect(rect, _TRACE_CLEARANCE)
    for point in points:
        point_rect = _rect_from_center(point, (5, 5))
        if _rect_overlap(rect, point_rect) > 0:
            return None
        if _rect_overlap(clearance_rect, point_rect) > 0:
            penalty += 20.0
    return penalty


def place_annotations(
    requests: Sequence[AnnotationRequest],
    geometry: AnnotationGeometry,
    trace_points: Iterable[tuple[float, float, str]] = (),
    reserved_rects: Iterable[Rect] = (),
) -> list[PlacedAnnotation]:
    """Place annotations without overlapping labels or reserved regions.

    Requests are placed by descending priority. Actual contact with a trace,
    existing label, or reserved region makes a candidate invalid; a small
    clearance corridor around traces contributes a soft penalty. This keeps
    labels readable while preserving the strongest annotations when space is
    scarce.
    """

    points_by_axis: dict[str, list[Point]] = {axis: [] for axis in geometry.y_ranges}
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
        for center, lane_rank in _candidate_centers(request, anchor, size, geometry):
            rect = _rect_from_center(center, size)
            if any(_rect_overlap(rect, other) > 0 for other in occupied):
                continue
            if any(_rect_overlap(rect, other) > 0 for other in reserved):
                continue
            if any(_segments_intersect(anchor, center, arrow_start, arrow_end) for arrow_start, arrow_end in arrows):
                continue
            if any(_segment_crosses_rect(anchor, center, other) for other in occupied):
                continue
            if any(_segment_crosses_rect(arrow_start, arrow_end, rect) for arrow_start, arrow_end in arrows):
                continue

            curve_score = _curve_penalty(rect, points_by_axis.get(request.yref, []))
            if curve_score is None:
                continue
            distance = math.hypot(center[0] - anchor[0], center[1] - anchor[1])
            score = (
                distance
                + lane_rank * 2.0
                + _direction_penalty(request.preferred_direction, anchor, center)
                + curve_score
            )
            if best is None or score < best[0]:
                best = score, center, rect

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
            axref="x domain" if geometry is not None else "pixel",
            ayref=f"{request.yref} domain" if geometry is not None else "pixel",
            visible=visible and not placement.hidden,
        )
        if placement.center is not None:
            if geometry is None:
                annotation["ax"] = round(placement.center[0] - placement.anchor[0])
                annotation["ay"] = round(placement.center[1] - placement.anchor[1])
            else:
                left, top, right, bottom = geometry.plot_rect
                annotation["ax"] = (placement.center[0] - left) / (right - left)
                annotation["ay"] = (bottom - placement.center[1]) / (bottom - top)
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
