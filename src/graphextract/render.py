# -*- coding: utf-8 -*-
"""Exact-label synthetic renderer for training pilots and regression tests.

Renders each series independently (geometric masks) then composites in draw
order (visible evidence), so overlap tests know both the truth path and what
the raster actually shows. Transforms are exactly known and independently
verifiable; renderer output never enters production calibration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.calibration import axis_from_exact_range
from graphextract.schema import AxisFit, AxisRole, ScaleType


@dataclass
class RenderSeries:
    series_id: str
    color_bgr: tuple[int, int, int]
    x_values: list[float]
    y_values: list[float]
    width_px: int = 1
    dash: tuple[int, int] | None = None  # (on, off) pattern; None = solid
    y_role: AxisRole = AxisRole.Y_LEFT


@dataclass
class RenderPanel:
    rect_xywh: tuple[int, int, int, int]  # interior in image coordinates
    x_scale: ScaleType = ScaleType.LOG10
    x_range: tuple[float, float] = (20.0, 20000.0)
    x_unit: str = "Hz"
    y_range: tuple[float, float] = (20.0, 100.0)
    y_unit: str = "dB"
    y2_range: tuple[float, float] | None = None
    grid: bool = True
    series: list[RenderSeries] = field(default_factory=list)


@dataclass
class RenderTruth:
    image: npt.NDArray
    geometric_masks: dict[str, npt.NDArray]
    visible_masks: dict[str, npt.NDArray]
    native_polylines: dict[str, list[tuple[float, float]]]
    x_fit: AxisFit
    y_fit: AxisFit
    y2_fit: AxisFit | None = None


def _data_to_pixel(x: float, y: float, panel: RenderPanel,
                   x0: int, y0: int, w: int, h: int,
                   y_role: AxisRole) -> tuple[float, float]:
    if panel.x_scale is ScaleType.LOG10:
        t = (math.log10(x) - math.log10(panel.x_range[0])) / (
            math.log10(panel.x_range[1]) - math.log10(panel.x_range[0]))
    else:
        t = (x - panel.x_range[0]) / (panel.x_range[1] - panel.x_range[0])
    yr = panel.y2_range if y_role is AxisRole.Y_RIGHT and panel.y2_range else panel.y_range
    s = (y - yr[0]) / (yr[1] - yr[0])
    return x0 + t * w, y0 + (1.0 - s) * h


def _stroke(img: npt.NDArray, pts: list[tuple[float, float]],
            color: tuple[int, ...], width: int,
            dash: tuple[int, int] | None) -> None:
    if dash is None:
        ipts = np.array([(int(round(x)), int(round(y))) for x, y in pts], dtype=np.int32)
        cv2.polylines(img, [ipts], False, color, width, cv2.LINE_8)
        return
    on, off = dash
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            continue
        dx, dy = (x2 - x1) / length, (y2 - y1) / length
        d = 0.0
        while d < length:
            e = min(d + on, length)
            cv2.line(img, (int(round(x1 + dx * d)), int(round(y1 + dy * d))),
                     (int(round(x1 + dx * e)), int(round(y1 + dy * e))), color, width,
                     cv2.LINE_8)
            d = e + off


def render_panel(image_size: tuple[int, int], panel: RenderPanel,
                 supersample: int = 1) -> RenderTruth:
    """Render one panel; returns image plus exact per-series truth."""
    img_w, img_h = image_size
    ss = max(1, supersample)
    canvas = np.full((img_h * ss, img_w * ss, 3), 255, np.uint8)
    x0, y0, w, h = panel.rect_xywh
    x0s, y0s, ws, hs = x0 * ss, y0 * ss, w * ss, h * ss

    if panel.grid:
        for f in (10, 31.6, 100, 316, 1000, 3160, 10000):
            if panel.x_scale is ScaleType.LOG10 and panel.x_range[0] <= f <= panel.x_range[1]:
                gx, _ = _data_to_pixel(f, panel.y_range[0], panel, x0s, y0s, ws, hs, AxisRole.Y_LEFT)
                cv2.line(canvas, (int(gx), y0s), (int(gx), y0s + hs), (220, 220, 220), 1 * ss)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            gy = y0s + frac * hs
            cv2.line(canvas, (x0s, int(gy)), (x0s + ws, int(gy)), (220, 220, 220), 1 * ss)
    cv2.rectangle(canvas, (x0s, y0s), (x0s + ws, y0s + hs), (180, 180, 180), 1 * ss)

    geo: dict[str, npt.NDArray] = {}
    vis: dict[str, npt.NDArray] = {}
    polys: dict[str, list[tuple[float, float]]] = {}
    for s in panel.series:
        pts = [_data_to_pixel(x, y, panel, x0s, y0s, ws, hs, s.y_role)
               for x, y in zip(s.x_values, s.y_values)]
        layer = np.zeros((img_h * ss, img_w * ss), np.uint8)
        _stroke(layer, pts, (255,), max(1, s.width_px * ss), s.dash)
        geo[s.series_id] = layer[::ss, ::ss] if ss > 1 else layer
        before = canvas.copy()
        _stroke(canvas, pts, s.color_bgr, max(1, s.width_px * ss),
                (s.dash[0] * ss, s.dash[1] * ss) if s.dash else None)
        diff = cv2.cvtColor(cv2.absdiff(canvas, before), cv2.COLOR_BGR2GRAY)
        newly = (((diff > 0) & (layer > 0)).astype(np.uint8)) * 255
        vis[s.series_id] = newly[::ss, ::ss] if ss > 1 else newly
        polys[s.series_id] = [ (px / ss, py / ss) for px, py in pts]

    if ss > 1:
        canvas = cv2.resize(canvas, (img_w, img_h), interpolation=cv2.INTER_AREA)

    x_fit = axis_from_exact_range(AxisRole.X, panel.x_scale, panel.x_unit,
                                  panel.x_range[0], panel.x_range[1], x0, x0 + w)
    y_fit = axis_from_exact_range(AxisRole.Y_LEFT, ScaleType.LINEAR, panel.y_unit,
                                  panel.y_range[0], panel.y_range[1], y0 + h, y0)
    y2_fit = None
    if panel.y2_range:
        y2_fit = axis_from_exact_range(AxisRole.Y_RIGHT, ScaleType.LINEAR, panel.y_unit,
                                       panel.y2_range[0], panel.y2_range[1], y0 + h, y0)
    return RenderTruth(canvas, geo, vis, polys, x_fit, y_fit, y2_fit)


def render_canvas(image_size: tuple[int, int], panels: list[RenderPanel],
                  supersample: int = 1) -> tuple[npt.NDArray, list[RenderTruth]]:
    """Render several panels onto one canvas (multi-panel layouts, insets).

    Returns the composed image plus one RenderTruth per panel, all in shared
    canvas-native coordinates. Series ids must be unique across panels.
    """
    img_w, img_h = image_size
    ss = max(1, supersample)
    canvas = np.full((img_h * ss, img_w * ss, 3), 255, np.uint8)
    truths: list[RenderTruth] = []
    for panel in panels:
        x0, y0, w, h = panel.rect_xywh
        x0s, y0s, ws, hs = x0 * ss, y0 * ss, w * ss, h * ss
        if panel.grid:
            for f in (10, 31.6, 100, 316, 1000, 3160, 10000):
                if panel.x_scale is ScaleType.LOG10 and panel.x_range[0] <= f <= panel.x_range[1]:
                    gx, _ = _data_to_pixel(f, panel.y_range[0], panel, x0s, y0s, ws, hs,
                                           AxisRole.Y_LEFT)
                    cv2.line(canvas, (int(gx), y0s), (int(gx), y0s + hs),
                             (220, 220, 220), 1 * ss)
            for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
                gy = y0s + frac * hs
                cv2.line(canvas, (x0s, int(gy)), (x0s + ws, int(gy)),
                         (220, 220, 220), 1 * ss)
        cv2.rectangle(canvas, (x0s, y0s), (x0s + ws, y0s + hs), (180, 180, 180), 1 * ss)
        geo: dict[str, npt.NDArray] = {}
        vis: dict[str, npt.NDArray] = {}
        polys: dict[str, list[tuple[float, float]]] = {}
        for s in panel.series:
            pts = [_data_to_pixel(x, y, panel, x0s, y0s, ws, hs, s.y_role)
                   for x, y in zip(s.x_values, s.y_values)]
            layer = np.zeros((img_h * ss, img_w * ss), np.uint8)
            _stroke(layer, pts, (255,), max(1, s.width_px * ss), s.dash)
            geo[s.series_id] = layer[::ss, ::ss] if ss > 1 else layer
            before = canvas.copy()
            _stroke(canvas, pts, s.color_bgr, max(1, s.width_px * ss),
                    (s.dash[0] * ss, s.dash[1] * ss) if s.dash else None)
            diff = cv2.cvtColor(cv2.absdiff(canvas, before), cv2.COLOR_BGR2GRAY)
            newly = (((diff > 0) & (layer > 0)).astype(np.uint8)) * 255
            vis[s.series_id] = newly[::ss, ::ss] if ss > 1 else newly
            polys[s.series_id] = [(px / ss, py / ss) for px, py in pts]
        x_fit = axis_from_exact_range(AxisRole.X, panel.x_scale, panel.x_unit,
                                      panel.x_range[0], panel.x_range[1], x0, x0 + w)
        y_fit = axis_from_exact_range(AxisRole.Y_LEFT, ScaleType.LINEAR, panel.y_unit,
                                      panel.y_range[0], panel.y_range[1], y0 + h, y0)
        y2_fit = None
        if panel.y2_range:
            y2_fit = axis_from_exact_range(AxisRole.Y_RIGHT, ScaleType.LINEAR, panel.y_unit,
                                           panel.y2_range[0], panel.y2_range[1], y0 + h, y0)
        truths.append(RenderTruth(canvas, geo, vis, polys, x_fit, y_fit, y2_fit))
    if ss > 1:
        canvas = cv2.resize(canvas, (img_w, img_h), interpolation=cv2.INTER_AREA)
        for t in truths:
            t.image = canvas
    else:
        for t in truths:
            t.image = canvas
    return canvas, truths


def verify_transforms(truth: RenderTruth, panel: RenderPanel) -> float:
    """Max round-trip error (pixels) mapping polyline data values through fits."""
    worst = 0.0
    for s in panel.series:
        y_fit = truth.y2_fit if s.y_role is AxisRole.Y_RIGHT and truth.y2_fit else truth.y_fit
        for (x, y), (px, py) in zip(zip(s.x_values, s.y_values), truth.native_polylines[s.series_id]):
            worst = max(worst, abs(truth.x_fit.transform(x) - px), abs(y_fit.transform(y) - py))
    return worst
