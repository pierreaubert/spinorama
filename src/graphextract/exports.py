# -*- coding: utf-8 -*-
"""Exports: canonical JSON (with uncertainty sidecars) and WPD compatibility.

WPD ``datasetColl`` cannot express gaps, identities, or uncertainty, so the
adapter emits one dataset per contiguous OBSERVED run, named with stable
``image/panel/series`` IDs that survive empty or repeated titles. The full
canonical document (statuses, alternatives, calibration anchors) is the primary
artifact; WPD is a derived, lossy view. ``write_curve_csvs`` instead emits one
plain CSV per series (data coordinates plus a status column) for direct
analysis.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.calibration import ScaleType
from graphextract.schema import AxisFit, DocumentResult, SegmentStatus, SeriesResult


def document_to_json(doc: DocumentResult) -> dict:
    return doc.to_dict()


def write_canonical(doc: DocumentResult, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(document_to_json(doc), indent=2) + "\n", encoding="utf-8")
    return path


_DRAWABLE = (SegmentStatus.OBSERVED, SegmentStatus.INTERPOLATED)


def _drawable_runs(series: SeriesResult,
                   draw_occlusion: bool = False) -> list[list[tuple[float, float]]]:
    """Split drawable samples into contiguous runs; real gaps stay gaps.

    INTERPOLATED samples (``curve_continuous`` bridges) draw as measurement;
    the canonical statuses still distinguish them from OBSERVED evidence.
    INFERRED_OCCLUSION draws only when ``draw_occlusion`` is set (the
    ``assume_overlap`` contract: hidden curves are assumed present), so
    default reconstructions keep honest gaps.
    """
    runs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for s in series.samples:
        drawable = s.status in _DRAWABLE or (
            draw_occlusion and s.status is SegmentStatus.INFERRED_OCCLUSION)
        if drawable and s.value_x is not None and s.value_y is not None:
            cur.append((s.value_x, s.value_y))
        else:
            if cur:
                runs.append(cur)
                cur = []
    if cur:
        runs.append(cur)
    return runs


def to_wpd_json(doc: DocumentResult) -> dict:
    """WPD datasetColl keyed by stable IDs; one dataset per observed run."""
    coll: list[dict] = []
    for panel in doc.panels:
        for series in panel.series:
            for i, run in enumerate(_drawable_runs(series)):
                name = f"{doc.image_id}/{panel.panel.panel_id.split('#')[-1]}/{series.series_id}"
                if len(_drawable_runs(series)) > 1:
                    name += f"#seg{i}"
                if series.label and series.label != series.series_id:
                    name += f" {series.label}"
                coll.append({"name": name,
                             "data": [{"value": [x, y]} for x, y in run]})
    return {"datasetColl": coll}


HEADER_H = 48
"""Layout contract: header-bar height (px) above each stacked comparison view."""

_LOG_MAJOR_TICKS = (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000)
_FALLBACK_PALETTE = (
    (0, 0, 255), (255, 128, 0), (0, 176, 0), (255, 0, 176),
    (0, 176, 176), (150, 0, 200), (0, 128, 255), (0, 0, 0),
)
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_INK = (20, 20, 20)
_GRID = (225, 225, 225)
_MINOR_GRID = (240, 240, 240)
_FRAME = (60, 60, 60)


def _tick_label(value: float) -> str:
    if value >= 1000 and float(value).is_integer() and value % 1000 == 0:
        return f"{int(value // 1000)}k"
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _nice_ticks(lo: float, hi: float, count: int = 8) -> list[float]:
    """Evenly spaced human-readable ticks covering [lo, hi]."""
    span = hi - lo
    if not math.isfinite(span) or span <= 0:
        return [lo]
    raw = span / max(1, count - 1)
    mag = 10.0 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    ticks = []
    tick = math.ceil(lo / step) * step
    while tick <= hi + 1e-9:
        ticks.append(tick)
        tick += step
    return ticks


def _domain(fit: AxisFit, data: list[float]) -> tuple[float, float]:
    """Axis value range: calibration anchors widened to observed data."""
    log = fit.scale is ScaleType.LOG10
    vals = [a.value for a in fit.anchors_used if a.value is not None]
    vals += [v for v in data if v is not None and math.isfinite(v)]
    if log:
        vals = [v for v in vals if v > 0]
    if not vals:
        return (1.0, 10.0) if log else (0.0, 1.0)
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        hi = lo + (abs(lo) or 1.0)
    if not log:
        pad = 0.03 * (hi - lo)
        lo, hi = lo - pad, hi + pad
    return lo, hi


def _series_colour(series_id: str, label: str, by_id: dict, by_label: dict,
                   fallback: int) -> tuple[int, int, int]:
    style = by_id.get(series_id)
    if style is None:
        style = by_label.get((label or "").strip().lower())
    if style is not None:
        bgr = style.bgr
        return (int(bgr[0]), int(bgr[1]), int(bgr[2]))
    return _FALLBACK_PALETTE[fallback % len(_FALLBACK_PALETTE)]


def _comparison_block(image: npt.NDArray, panel, image_id: str,
                      by_id: dict, by_label: dict,
                      draw_occlusion: bool = False) -> npt.NDArray:
    """One panel as [header, original crop, header, value-space replot]."""
    img_h, img_w = image.shape[:2]
    x0, y0, w, h = (int(v) for v in panel.panel.interior_xywh)
    w, h = max(w, 64), max(h, 64)
    crop = image[max(0, y0):min(img_h, y0 + h), max(0, x0):min(img_w, x0 + w)]
    if crop.size == 0:
        crop = np.full((h, w, 3), 255, np.uint8)
    if (crop.shape[1], crop.shape[0]) != (w, h):
        fitted = np.full((h, w, 3), 255, np.uint8)
        fitted[:crop.shape[0], :crop.shape[1]] = crop
        crop = fitted

    x_fit = panel.axes.get("x")
    y_fit = panel.axes.get("y_left", panel.axes.get("y_right"))
    series = list(panel.series)

    def _visible(s) -> bool:
        return s.status in _DRAWABLE or (
            draw_occlusion and s.status is SegmentStatus.INFERRED_OCCLUSION)

    obs_x = [s.value_x for sr in series for s in sr.samples if _visible(s)]
    obs_y = [s.value_y for sr in series for s in sr.samples if _visible(s)]

    k = min(2.0, max(0.75, w / 1600.0))
    line_w = max(2, round(w / 1200))
    tick_scale, tick_thick = 0.55 * k, max(1, round(0.8 * k))
    text_scale, text_thick = 0.7 * k, max(1, round(k))

    bottom = np.full((h, w, 3), 255, np.uint8)
    names = ", ".join(sr.label for sr in series) if series else "no series"
    headers = [
        f"original — {image_id} · panel {panel.panel.panel_id} ({w}x{h}px)",
        f"reconstructed — {len(series)} curve(s): {names}",
    ]

    if x_fit is None or y_fit is None or not any(obs_x) or not any(obs_y):
        cv2.putText(bottom, "no calibrated samples to replot", (int(30 * k), h // 2),
                    _FONT, text_scale, _INK, text_thick, cv2.LINE_AA)
    else:
        log_x = x_fit.scale is ScaleType.LOG10
        x_lo, x_hi = _domain(x_fit, [v for v in obs_x if v])
        # Twin y axes share one pixel geometry: a right-axis value reaches
        # the figure through its own fit (value -> native pixel) composed
        # with the left fit back to figure space, exactly like the source
        # plot. Directivity series therefore hug the bottom band as drawn
        # instead of stretching over the dB domain.
        key_of = {}
        for sr in series:
            key_of[id(sr)] = sr.axis_id if sr.axis_id in panel.axes else "y_left"
        has_right = any(k != "y_left" for k in key_of.values())
        r_fit = panel.axes.get("y_right") if has_right else None
        left_y = [s.value_y for sr in series if key_of[id(sr)] == "y_left"
                  for s in sr.samples if _visible(s)]
        y_lo, y_hi = _domain(y_fit, [v for v in left_y if v]
                             or [v for v in obs_y if v])
        if (r_fit is not None and r_fit.unit == "dB"
                and r_fit.scale is not ScaleType.LOG10):
            # The dB domain stretches to show the full directivity
            # archetype on the right axis, like the source plots.
            for edge in (-10.0, 40.0):
                native = r_fit.a * edge + r_fit.b
                try:
                    at = y_fit.invert(native)
                except (ValueError, ZeroDivisionError):
                    continue
                y_lo, y_hi = min(y_lo, at), max(y_hi, at)
        x_lo_t, x_hi_t = ((math.log10(x_lo), math.log10(x_hi)) if log_x
                          else (x_lo, x_hi))
        span_t = x_hi_t - x_lo_t or 1.0
        span_y = y_hi - y_lo or 1.0

        legend_w = 0
        for sr in series:
            (tw, _), _ = cv2.getTextSize(sr.label, _FONT, text_scale, text_thick)
            legend_w = max(legend_w, tw)
        left = min(int(95 * k), w // 4)
        right = min(int(40 * k) + int(34 * k) + legend_w, w // 3)
        top_m = int(40 * k)
        bot_m = int(70 * k)
        plot_w = max(50, w - left - right)
        plot_h = max(50, h - top_m - bot_m)

        def px(val: float) -> float:
            t = math.log10(val) if log_x and val > 0 else val
            frac = (t - x_lo_t) / span_t
            if x_fit.reversed:
                frac = 1.0 - frac
            return left + frac * plot_w

        def py(val: float) -> float:
            frac = (val - y_lo) / span_y
            if y_fit.reversed:
                frac = 1.0 - frac
            return top_m + (1.0 - frac) * plot_h

        def py_right(val: float, fit: AxisFit) -> float:
            # Twin-axis composition: right value -> native pixel through
            # the right fit, then native -> figure through the left fit.
            t = math.log10(val) if fit.scale is ScaleType.LOG10 and val > 0 else val
            return py(y_fit.invert(fit.a * t + fit.b))

        if log_x:
            for decade in range(int(math.floor(math.log10(x_lo))),
                               int(math.ceil(math.log10(x_hi))) + 1):
                base = 10.0 ** decade
                for mult in range(1, 10):
                    v = base * mult
                    if v < x_lo or v > x_hi:
                        continue
                    col = _GRID if mult == 1 else _MINOR_GRID
                    cv2.line(bottom, (round(px(v)), top_m),
                             (round(px(v)), top_m + plot_h), col, 1)
            x_ticks = [t for t in _LOG_MAJOR_TICKS if x_lo <= t <= x_hi]
        else:
            x_ticks = _nice_ticks(x_lo, x_hi)
            for t in x_ticks:
                cv2.line(bottom, (round(px(t)), top_m),
                         (round(px(t)), top_m + plot_h), _GRID, 1)
        y_ticks = _nice_ticks(y_lo, y_hi)
        for t in y_ticks:
            cv2.line(bottom, (left, round(py(t))),
                     (left + plot_w, round(py(t))), _GRID, 1)
        cv2.rectangle(bottom, (left, top_m),
                      (left + plot_w, top_m + plot_h), _FRAME, max(1, line_w - 1))

        for t in x_ticks:
            label = _tick_label(t)
            (tw, th), _ = cv2.getTextSize(label, _FONT, tick_scale, tick_thick)
            cv2.putText(bottom, label, (round(px(t) - tw / 2),
                                       top_m + plot_h + int(28 * k)),
                        _FONT, tick_scale, _INK, tick_thick, cv2.LINE_AA)
        for t in y_ticks:
            label = _tick_label(t)
            (tw, th), _ = cv2.getTextSize(label, _FONT, tick_scale, tick_thick)
            cv2.putText(bottom, label, (left - tw - int(10 * k),
                                       round(py(t) + th / 2)),
                        _FONT, tick_scale, _INK, tick_thick, cv2.LINE_AA)
        x_title = f"{x_fit.unit} ({'log' if log_x else 'linear'})"
        (tw, _), _ = cv2.getTextSize(x_title, _FONT, text_scale, text_thick)
        cv2.putText(bottom, x_title, (left + (plot_w - tw) // 2,
                                     top_m + plot_h + int(58 * k)),
                    _FONT, text_scale, _INK, text_thick, cv2.LINE_AA)
        cv2.putText(bottom, y_fit.unit, (left, top_m - int(12 * k)),
                    _FONT, text_scale, _INK, text_thick, cv2.LINE_AA)

        for index, sr in enumerate(series):
            colour = _series_colour(sr.series_id, sr.label, by_id, by_label, index)
            right = r_fit is not None and key_of.get(id(sr)) != "y_left"
            for run in _drawable_runs(sr, draw_occlusion):
                if right and r_fit is not None:
                    pts = np.array([(px(x), py_right(y, r_fit)) for x, y in run
                                    if x is not None and y is not None
                                    and (not log_x or x > 0)], dtype=np.float32)
                else:
                    pts = np.array([(px(x), py(y)) for x, y in run
                                    if x is not None and y is not None
                                    and (not log_x or x > 0)], dtype=np.float32)
                if len(pts) >= 2:
                    cv2.polylines(bottom, [pts.astype(np.int32)], False,
                                  colour, line_w, cv2.LINE_AA)
            chip_x = left + plot_w + int(24 * k)
            row_h = min(int(36 * k), plot_h // max(1, len(series)))
            row_h = max(row_h, 14)
            cy = top_m + row_h // 2 + index * row_h
            if cy - 8 * k < top_m + plot_h:
                cv2.rectangle(bottom, (chip_x, int(cy - 7 * k)),
                              (chip_x + int(26 * k), int(cy + 7 * k)),
                              colour, -1)
                cv2.rectangle(bottom, (chip_x, int(cy - 7 * k)),
                              (chip_x + int(26 * k), int(cy + 7 * k)),
                              _INK, 1)
                cv2.putText(bottom, sr.label, (chip_x + int(34 * k), int(cy + 6 * k)),
                            _FONT, min(text_scale, row_h / 30.0), _INK,
                            tick_thick, cv2.LINE_AA)

        if r_fit is not None:
            # Right-axis ticks live inside the frame's right edge: the
            # legend occupies the outside margin.
            r_lo, r_hi = right_tick_span(r_fit, y_fit, y_lo, y_hi)
            for t in _nice_ticks(r_lo, r_hi):
                label = _tick_label(t)
                (tw, th), _ = cv2.getTextSize(label, _FONT, tick_scale, tick_thick)
                cv2.putText(bottom, label,
                            (left + plot_w - tw - int(6 * k),
                             round(py_right(t, r_fit) + th / 2)),
                            _FONT, tick_scale, _INK, tick_thick, cv2.LINE_AA)
            (tw, _), _ = cv2.getTextSize(r_fit.unit, _FONT, text_scale, text_thick)
            cv2.putText(bottom, r_fit.unit, (left + plot_w - tw,
                                             top_m - int(12 * k)),
                        _FONT, text_scale, _INK, text_thick, cv2.LINE_AA)

    head_scale, head_thick = min(1.1 * k, 1.6), max(1, round(k))
    heads = []
    for text in headers:
        head = np.full((HEADER_H, w, 3), 242, np.uint8)
        while text:
            (tw, _), _ = cv2.getTextSize(text, _FONT, head_scale, head_thick)
            if tw <= w - 20:
                break
            text = text.rsplit(",", 1)[0] if "," in text else text[:-20]
        cv2.putText(head, text, (10, HEADER_H - 14), _FONT,
                    head_scale, _INK, head_thick, cv2.LINE_AA)
        cv2.line(head, (0, HEADER_H - 1), (w, HEADER_H - 1), _FRAME, 1)
        heads.append(head)
    return np.vstack([heads[0], crop, heads[1], bottom])


def right_tick_span(r_fit, y_fit, y_lo: float, y_hi: float) -> tuple[float, float]:
    """Right-axis tick span over the shared pixel range.

    The span covers the right values visible over the left domain; a dB
    right axis always covers the directivity archetype range too, so DI
    curves read against -10..40 like the source plots even when the
    observed span is narrower, while wider data extends past it.
    """
    nat_lo = y_fit.a * y_lo + y_fit.b
    nat_hi = y_fit.a * y_hi + y_fit.b
    r_vis = [r_fit.invert(n) for n in (nat_lo, nat_hi)]
    if r_fit.unit == "dB":
        r_vis = [min(r_vis + [-10.0]), max(r_vis + [40.0])]
    return min(r_vis), max(r_vis)


_CURVE_NAMES = {"hz": "freq", "db": "spl"}


def _slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return slug or fallback


def _column_name(unit: str, fallback: str) -> str:
    """Unit-aware CSV column name: Hz -> freq_Hz, dB -> spl_dB, else x/y."""
    unit = (unit or "").strip()
    if not unit or unit.lower() == "unknown":
        return fallback
    stem = re.sub(r"[^a-z0-9]+", "_", _CURVE_NAMES.get(unit.lower(), unit.lower()))
    return f"{stem}_{unit}" if stem else fallback


def write_curve_csvs(doc: DocumentResult, directory: str | Path,
                     include_occlusion: bool = False) -> list[Path]:
    """Write one CSV per series: data-coordinate rows plus a status column.

    Only drawable samples (OBSERVED + INTERPOLATED) become rows, so the
    files match the reconstructed plots; the ``status`` column keeps
    measurement distinguishable from inference. With ``include_occlusion``
    (the ``assume_overlap`` contract), INFERRED_OCCLUSION rows are included
    too, matching reconstructions drawn with occlusion. Filenames are
    ``<image>.<label>.csv`` with slugified labels (deduplicated), plus a
    panel suffix for multi-panel documents. Series without drawable
    samples still get a header-only file, keeping one-file-per-curve.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    multi = len(doc.panels) > 1
    used: set[str] = set()
    written: list[Path] = []
    for panel in doc.panels:
        suffix = panel.panel.panel_id.split("#")[-1] if multi else ""
        x_unit = panel.axes["x"].unit if "x" in panel.axes else ""
        for series in panel.series:
            y_fit = panel.axes.get(series.axis_id, panel.axes.get("y_left"))
            y_unit = y_fit.unit if y_fit is not None else ""
            header = f"{_column_name(x_unit, 'x')},{_column_name(y_unit, 'y')},status"
            parts = [_slugify(doc.image_id, "curves")]
            if suffix:
                parts.append(suffix)
            parts.append(_slugify(series.label, series.series_id))
            stem = ".".join(parts)
            name, serial = stem, 2
            while f"{name}.csv" in used:
                name, serial = f"{stem}_{serial}", serial + 1
            used.add(f"{name}.csv")
            rows = [f"{s.value_x:.6g},{s.value_y:.6g},{s.status.value}"
                    for s in series.samples
                    if (s.status in _DRAWABLE or (
                        include_occlusion
                        and s.status is SegmentStatus.INFERRED_OCCLUSION))
                    and s.value_x is not None and s.value_y is not None]
            path = directory / f"{name}.csv"
            path.write_text(header + "\n" + ("".join(r + "\n" for r in rows)),
                            encoding="utf-8")
            written.append(path)
    return written


def write_comparison_figure(image: npt.NDArray, doc: DocumentResult,
                            styles: Sequence[Any], path: str | Path,
                            draw_occlusion: bool = False) -> Path:
    """Stack each panel's original crop over its value-space reconstruction.

    The top view is the untouched original interior; the bottom view replots
    OBSERVED samples in data coordinates (log-x when calibrated so), using
    the curve styles (legend names/colours) that drove tracking. Gaps stay
    gaps: only OBSERVED runs are drawn, plus INFERRED_OCCLUSION runs when
    ``draw_occlusion`` is set (the ``assume_overlap`` contract).
    """
    path = Path(path)
    if not doc.panels:
        raise ValueError("no panels to compare")
    by_id = {s.series_id: s for s in styles}
    by_label = {str(s.label).strip().lower(): s for s in styles}
    blocks = [_comparison_block(image, panel, doc.image_id, by_id, by_label,
                                draw_occlusion)
              for panel in doc.panels]
    width = max(b.shape[1] for b in blocks)
    padded = []
    for block in blocks:
        if block.shape[1] < width:
            pad = np.full((block.shape[0], width - block.shape[1], 3), 255, np.uint8)
            block = np.hstack([block, pad])
        padded.append(block)
    gap = np.full((24, width, 3), 255, np.uint8)
    figure = padded[0]
    for block in padded[1:]:
        figure = np.vstack([figure, gap, block])
    if not cv2.imwrite(str(path), figure):
        raise ValueError(f"could not write comparison figure: {path}")
    return path
