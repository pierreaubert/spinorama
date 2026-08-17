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

    # Put the preferred semantic lanes first. The small horizontal offsets
    # allow adjacent annotations to fan out without changing the margins.
    lane_names = list(request.preferred_lanes)
    lane_names.extend(name for name in _LANE_FRACTIONS if name not in lane_names)
    seen: set[tuple[int, int]] = set()
    for lane_rank, lane_name in enumerate(lane_names):
        fraction = _LANE_FRACTIONS[lane_name]
        lane_y = top + fraction * (bottom - top)
        for dx in (0, -100, 100, -190, 190):
            center = (min(x_max, max(x_min, anchor[0] + dx)), min(y_max, max(y_min, lane_y)))
            key = (round(center[0]), round(center[1]))
            if key not in seen:
                seen.add(key)
                yield center, lane_rank

    # If a preferred lane is crowded, try positions close to the anchor before
    # considering suppression. These are deliberately pixel offsets because
    # they behave consistently across the SPL and DI axes.
    for lane_rank, (dx, dy) in enumerate(
        ((0, -70), (0, 70), (-100, -55), (100, -55), (-100, 55), (100, 55), (0, -125), (0, 125)),
        start=len(lane_names),
    ):
        center = (min(x_max, max(x_min, anchor[0] + dx)), min(y_max, max(y_min, anchor[1] + dy)))
        key = (round(center[0]), round(center[1]))
        if key not in seen:
            seen.add(key)
            yield center, lane_rank


def place_annotations(
    requests: Sequence[AnnotationRequest],
    geometry: AnnotationGeometry,
    trace_points: Iterable[tuple[float, float, str]] = (),
    reserved_rects: Iterable[Rect] = (),
) -> list[PlacedAnnotation]:
    """Place annotations without overlapping labels or reserved regions.

    Requests are placed by descending priority. Curves contribute a soft
    penalty, while overlap with an existing label or reserved region makes a
    candidate invalid. This lets labels move away from dense curves while
    keeping the strongest annotations visible when space is scarce.
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
    placed: list[PlacedAnnotation] = []
    occupied: list[Rect] = []
    ordered = sorted(enumerate(requests), key=lambda item: (-item[1].priority, item[0]))
    for _, request in ordered:
        anchor = _anchor_pixel(request, geometry)
        size = estimate_annotation_size(request.text, geometry.font_size, geometry.label_pad)
        best: tuple[float, Point, Rect] | None = None
        for center, lane_rank in _candidate_centers(request, anchor, size, geometry):
            rect = _rect_from_center(center, size)
            if any(_rect_overlap(rect, other) > 0 for other in occupied):
                continue
            if any(_rect_overlap(rect, other) > 0 for other in reserved):
                continue

            curve_penalty = 0.0
            for point in points_by_axis.get(request.yref, []):
                if _rect_overlap(rect, _rect_from_center(point, (5, 5))) > 0:
                    curve_penalty += 4.0
            distance = math.hypot(center[0] - anchor[0], center[1] - anchor[1])
            score = lane_rank * 15.0 + distance * 0.025 + curve_penalty
            if best is None or score < best[0]:
                best = score, center, rect

        if best is None:
            placed.append(PlacedAnnotation(request, anchor, None, size, hidden=True))
            continue

        _, center, rect = best
        occupied.append(rect)
        placed.append(PlacedAnnotation(request, anchor, center, size))

    return placed


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
