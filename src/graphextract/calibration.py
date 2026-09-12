# -*- coding: utf-8 -*-
"""Axis calibration with explicit scales, units, and refusal to guess.

Each axis is ``pixel = a * t + b`` with ``t = value`` (linear) or
``t = log10(value)`` (log10). Supported families: log-frequency / linear-dB,
linear-percent, linear-time (negative ordinates allowed), generic linear, and
independent left/right y axes. Broken axes are unsupported and raise.

When anchors are insufficient or unreadable, calibration raises
``CalibrationUnresolved`` describing exactly what a reviewer must supply.
It never invents scale values from family templates.
"""

from __future__ import annotations

import itertools
import math
import re

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.schema import AxisFit, AxisRole, ScaleType, TickAnchor


class CalibrationUnresolved(Exception):
    """Calibration evidence is insufficient; human review or source data needed."""

    def __init__(self, reason: str, needed: list[str]) -> None:
        super().__init__(reason)
        self.reason = reason
        self.needed = needed


def parse_tick_label(text: str) -> tuple[float, str] | None:
    """Parse a tick label into (value, kind). Kind is freq/db/percent/time/linear."""
    t = text.strip().lower().replace(" ", "").replace(",", "")
    if not t:
        return None
    m = re.fullmatch(r"(-?\d+\.?\d*)(ms|s|khz|hz|k|db|%)?", t)
    if not m:
        return None
    val, suffix = float(m.group(1)), (m.group(2) or "")
    if suffix == "%":
        return val, "percent"
    if suffix in ("db",):
        return val, "db"
    if suffix in ("hz", "k", "khz"):
        if suffix == "k":
            val *= 1000.0
        return val, "freq"
    if suffix in ("s", "ms"):
        if suffix == "ms":
            val /= 1000.0
        return val, "time"
    return val, "linear"


def unpack_hough_lines(lines: npt.NDArray | None) -> list[tuple[int, int, int, int]]:
    """Unpack HoughLinesP output regardless of OpenCV layout ((N,1,4) or (N,4))."""
    if lines is None:
        return []
    flat = np.asarray(lines).reshape(-1, 4)
    return [(int(x1), int(y1), int(x2), int(y2)) for x1, y1, x2, y2 in flat]


def _run_positions(hits: npt.NDArray, gap: int = 6) -> list[int]:
    """Cluster adjacent hit indices; returns one centre position per run."""
    if len(hits) == 0:
        return []
    groups: list[list[int]] = [[int(hits[0])]]
    for v in (int(v) for v in hits[1:]):
        if v - groups[-1][-1] <= gap:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [int(sum(g) / len(g)) for g in groups]


def projection_lines(
    plot_img: npt.NDArray,
    support_frac: float = 0.4,
    band: tuple[float, float] = (0.2, 0.8),
    dark_thresh: int = 30,
) -> tuple[list[int], list[int]]:
    """Columns/rows that stay dark across most of the middle band.

    Frame strokes and major grid lines span the plot, while curves, labels,
    and minor (log-decade) grid dots do not survive a tall/wide support
    window. ``support_frac`` is the fraction of the band that must be dark.
    Returns (vertical xs, horizontal ys) in crop-local pixels.
    """
    h, w = plot_img.shape[:2]
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY) if plot_img.ndim == 3 else plot_img
    dark = gray.astype(float) < 255.0 - dark_thresh
    r0, r1 = int(h * band[0]), int(h * band[1])
    c0, c1 = int(w * band[0]), int(w * band[1])
    vx = _run_positions(np.where(dark[r0:r1, :].mean(axis=0) >= support_frac)[0]) if r1 > r0 else []
    hy = _run_positions(np.where(dark[:, c0:c1].mean(axis=1) >= support_frac)[0]) if c1 > c0 else []
    return vx, hy


def _merge_positions(first: list[int], second: list[int], gap: int = 8) -> list[int]:
    """Union of two position lists, collapsing near-duplicates."""
    return _run_positions(np.asarray(sorted(set(first) | set(second)), dtype=int), gap=gap)


def detect_grid_lines(plot_img: npt.NDArray) -> tuple[list[int], list[int]]:
    """Detect axis-aligned grid/frame lines; returns (vertical xs, horizontal ys)."""
    h, w = plot_img.shape[:2]
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY) if plot_img.ndim == 3 else plot_img
    edges = cv2.Canny(gray, 30, 100)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=50,
        minLineLength=int(0.3 * min(h, w)), maxLineGap=5,
    )
    vx: list[int] = []
    hy: list[int] = []
    for x1, y1, x2, y2 in unpack_hough_lines(lines):
        if abs(x2 - x1) < 3 and abs(y2 - y1) > 0.2 * h:
            vx.append((x1 + x2) // 2)
        elif abs(y2 - y1) < 3 and abs(x2 - x1) > 0.2 * w:
            hy.append((y1 + y2) // 2)
    # Faint log-decade strokes fragment under Hough (curves crossing the grid
    # split segments below minLineLength) while frames and major decade lines
    # still span the plot; the projection pass recovers those survivors.
    proj_x, proj_y = projection_lines(plot_img)
    vx = _merge_positions(vx, proj_x)
    hy = _merge_positions(hy, proj_y)
    return _cluster(sorted(vx), max(4, int(0.02 * w))), _cluster(sorted(hy), max(4, int(0.02 * h)))


def _cluster(positions: list[int], min_gap: int) -> list[int]:
    if not positions:
        return []
    groups: list[list[int]] = [[positions[0]]]
    for p in positions[1:]:
        if p - groups[-1][-1] < min_gap:
            groups[-1].append(p)
        else:
            groups.append([p])
    return [int(sum(g) / len(g)) for g in groups]


def _fit_from_anchors(
    anchors: list[TickAnchor], scale: ScaleType, inlier_tol_px: float = 2.0
) -> tuple[float, float, list[TickAnchor], float, float]:
    """Deterministic RANSAC for pixel = a*t+b over anchor pairs; refit inliers."""
    def t_of(v: float) -> float:
        if scale is ScaleType.LOG10:
            if v <= 0:
                raise ValueError(f"log axis needs positive anchor, got {v}")
            return math.log10(v)
        return v

    ts = [t_of(a.value) for a in anchors]
    px = [a.pixel for a in anchors]
    best: tuple[float, float, list[int]] | None = None
    for i, j in itertools.combinations(range(len(anchors)), 2):
        if ts[j] == ts[i]:
            continue
        a = (px[j] - px[i]) / (ts[j] - ts[i])
        b = px[i] - a * ts[i]
        inl = [k for k in range(len(anchors)) if abs((a * ts[k] + b) - px[k]) <= inlier_tol_px]
        if best is None or len(inl) > len(best[2]):
            best = (a, b, inl)
    if best is None or len(best[2]) < 2:
        raise CalibrationUnresolved(
            "Anchors are degenerate (coincident transform values).",
            ["two anchors with distinct axis values"],
        )
    a, b, inl = best
    # Refit on inliers by least squares.
    t_arr = np.array([ts[k] for k in inl])
    p_arr = np.array([px[k] for k in inl])
    if len(inl) == 2:
        a = float((p_arr[1] - p_arr[0]) / (t_arr[1] - t_arr[0]))
        b = float(p_arr[0] - a * t_arr[0])
    else:
        a, b = (float(v) for v in np.polyfit(t_arr, p_arr, 1))
    resid = [abs((a * ts[k] + b) - px[k]) for k in inl]
    used = [anchors[k] for k in inl]
    return a, b, used, float(np.mean(resid)), float(max(resid))


def fit_axis(
    anchors: list[TickAnchor],
    role: AxisRole,
    unit: str,
    scale: ScaleType | None = None,
    inlier_tol_px: float = 2.0,
    min_anchors: int = 3,
) -> AxisFit:
    """Fit one axis from tick anchors with robust regression and validation.

    With fewer than ``min_anchors`` anchors, two anchors are accepted only when
    at least one independent supporting anchor (grid alignment or held-out tick
    within tolerance) corroborates the fit; otherwise CalibrationUnresolved.
    When ``scale`` is None, linear and log10 hypotheses compete on explained
    anchors first, residuals second: any two anchors fit a line exactly, so a
    bare residual comparison would always tie on log-spaced decades.
    """
    if scale is ScaleType.LOG10 and any(a.value <= 0 for a in anchors):
        raise CalibrationUnresolved(
            "Log axis requires positive tick values.", ["positive tick values for log axis"]
        )
    candidates = [scale] if scale is not None else [ScaleType.LINEAR, ScaleType.LOG10]
    fits: list[tuple[float, AxisFit]] = []
    for cand in candidates:
        try:
            a, b, used, rms, mx = _fit_from_anchors(anchors, cand, inlier_tol_px)
        except (CalibrationUnresolved, ValueError):
            continue
        if role is AxisRole.X and cand is ScaleType.LINEAR and a <= 0:
            continue
        if role is AxisRole.X and cand is ScaleType.LOG10 and a <= 0:
            continue
        fits.append((mx, AxisFit(role=role, scale=cand, unit=unit, a=a, b=b,
                                 anchors_used=used, residual_px_rms=rms,
                                 residual_px_max=mx, method="ransac_pairs")))
    if not fits:
        raise CalibrationUnresolved(
            f"No viable {role.value}-axis hypothesis from {len(anchors)} anchors.",
            ["readable tick labels with associated tick pixel positions", "axis unit/scale"],
        )
    fits.sort(key=lambda f: (-len(f[1].anchors_used), f[0]))
    best = fits[0][1]
    if len(fits) > 1:
        runner_up = fits[1][1]
        # Inlier counts from a 2px threshold are noisy by ±1, so only a
        # clear support gap (2+) breaks the tie; close residuals otherwise
        # keep the ambiguity explicit.
        tied_support = len(runner_up.anchors_used) >= len(best.anchors_used) - 1
        close = abs(fits[0][0] - fits[1][0]) <= 0.5
        if tied_support and close and best.scale is not ScaleType.LOG10:
            # Ambiguous scale with no convincing winner: keep ambiguity explicit.
            raise CalibrationUnresolved(
                "Linear and logarithmic hypotheses fit equally well.",
                ["explicit axis scale selection (linear vs log)"],
            )
    n = len(best.anchors_used)
    if n < min_anchors:
        # Two anchors define the affine map; demand independent corroboration.
        support = [a for a in anchors if a not in best.anchors_used]
        ok = any(
            abs(best.a * (math.log10(s.value) if best.scale is ScaleType.LOG10 else s.value)
                + best.b - s.pixel) <= 4.0 * inlier_tol_px
            for s in support
        )
        if not ok:
            raise CalibrationUnresolved(
                f"Only {n} anchors for {role.value}-axis; need independent support.",
                ["one more labeled tick or verified grid spacing"],
            )
    if role is AxisRole.X and best.a <= 0:
        raise CalibrationUnresolved("Non-monotonic x mapping.", ["consistent tick order"])
    return best


def held_out_tick_error(fit: AxisFit, held_out: list[TickAnchor]) -> dict[str, float]:
    """Reproject independent anchors through a fit; whole-axis diagnostic."""
    errs = []
    for t in held_out:
        errs.append(abs(fit.transform(t.value) - t.pixel))
    if not errs:
        return {"n": 0, "max_px": float("nan"), "rms_px": float("nan")}
    arr = np.array(errs)
    return {"n": len(errs), "max_px": float(arr.max()), "rms_px": float(np.sqrt((arr**2).mean()))}


def axis_from_exact_range(
    role: AxisRole,
    scale: ScaleType,
    unit: str,
    v_min: float,
    v_max: float,
    px_min: float,
    px_max: float,
) -> AxisFit:
    """Oracle constructor from known ranges (diagnosis/tests only, never production)."""
    import math as _m

    t0 = _m.log10(v_min) if scale is ScaleType.LOG10 else v_min
    t1 = _m.log10(v_max) if scale is ScaleType.LOG10 else v_max
    a = (px_max - px_min) / (t1 - t0)
    return AxisFit(role=role, scale=scale, unit=unit, a=a, b=px_min - a * t0,
                   method="oracle_exact_range")
