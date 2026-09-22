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


_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def parse_tick_label(text: str) -> tuple[float, str] | None:
    """Parse a tick label into (value, kind). Kind is freq/db/percent/time/linear."""
    t = text.strip().lower().replace(" ", "").replace(",", "")
    # A trailing dash is a touching tick mark, not a minus: labels never
    # end with a sign. Leading negatives ('-80') are preserved.
    t = t.rstrip("-")
    if not t:
        return None
    # Scientific power notation (``10²`` / ``10^2``): powers of ten label
    # log-decade ticks. Only the explicit exponent form folds; plain digit
    # strings (``102``) keep their face value and are disambiguated by fit
    # consistency, never here.
    t = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹]+)",
               lambda m: "10^" + m.group(1).translate(_SUPERSCRIPT), t)
    m = re.fullmatch(r"10\^(-?\d+)", t)
    if m:
        return 10.0 ** int(m.group(1)), "linear"
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


def detect_frame_ticks(
    gray: npt.NDArray,
    interior_xywh: tuple[int, int, int, int],
    band: int = 28,
    min_len: int = 9,
    max_width: int = 8,
    dark: int = 220,
) -> tuple[list[int], list[int]]:
    """Tick marks protruding from the frame edge (interior-local coords).

    Gridless charts mark decades with short ticks between the frame and the
    labels, where interior-only grid detection can never see them. A tick is
    an ink run attached to the frame edge: long enough to clear frame-edge
    smear, narrow enough to exclude the smear itself, short enough to
    exclude through-running gridlines (those already report via grid
    detection). Returns (tick_xs, tick_ys) for the vertical/horizontal
    edges; empty when the interior touches the image border.
    """
    h, w = gray.shape[:2]
    ix, iy, iw, ih = (int(v) for v in interior_xywh)
    tick_xs: list[int] = []
    tick_ys: list[int] = []

    def _runs(edge: npt.NDArray) -> list[int]:
        """Tick centres along one edge strip (frame at row 0 by flip).

        Connected ink blobs starting at the frame edge: tall enough to
        clear smear and dots, short enough to exclude through-running
        gridlines, narrow enough to exclude the frame smear band itself.
        Full-width rows are frame-edge smear the tick protrudes past, so
        they are cleared first; otherwise smear and tick merge into one
        unusable blob.
        """
        ink_frac = edge.sum(axis=1) / max(1, edge.shape[1])
        edge = edge.copy()
        edge[ink_frac > 0.5] = 0
        ncc, _, stats, _ = cv2.connectedComponentsWithStats(edge, 8)
        centres = []
        for i in range(1, ncc):
            x, y, w, h, area = (int(v) for v in stats[i])
            if (min_len <= h <= band - 4 and w <= max_width and y <= 8
                    and area >= 0.5 * w * h):
                centres.append(x + w // 2)
        return centres

    def _band_img(y0: int, y1: int, x0: int, x1: int
                  ) -> tuple[npt.NDArray, int, int] | None:
        y0c, y1c, x0c, x1c = max(0, y0), min(h, y1), max(0, x0), min(w, x1)
        if y1c - y0c < min_len or x1c - x0c < 1:
            return None
        return (gray[y0c:y1c, x0c:x1c] < dark).astype(np.uint8), x0c, y0c

    bottom = _band_img(iy + ih, iy + ih + band, ix, ix + iw)
    if bottom is not None:
        img, ox, _ = bottom
        tick_xs += [x + ox - ix for x in _runs(img)]
    top = _band_img(iy - band, iy, ix, ix + iw)
    if top is not None:
        img, ox, _ = top
        tick_xs += [x + ox - ix for x in _runs(np.flip(img, axis=0))]
    left = _band_img(iy, iy + ih, ix - band, ix)
    if left is not None:
        img, _, oy = left
        tick_ys += [y + oy - iy for y in _runs(np.flip(img, axis=1).transpose(1, 0))]
    right = _band_img(iy, iy + ih, ix + iw, ix + iw + band)
    if right is not None:
        img, _, oy = right
        tick_ys += [y + oy - iy for y in _runs(img.transpose(1, 0))]
    tick_xs = sorted({x for x in tick_xs if 0 <= x <= iw})
    tick_ys = sorted({y for y in tick_ys if 0 <= y <= ih})
    return tick_xs, tick_ys


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

    if scale is ScaleType.LOG10:
        # Non-positive readings ('0' fragments) can never be log inliers;
        # drop them so pairs among the positive majority still compete.
        anchors = [a for a in anchors if a.value > 0]
    ts = [t_of(a.value) for a in anchors]
    px = [a.pixel for a in anchors]

    def _support(idxs: list[int]) -> int:
        # One vote per pixel row: several conflicting reads of one tick
        # label share a pixel, and counting them separately lets a
        # misread plus its twins outvote the true consensus.
        return len({round(px[k]) for k in idxs})

    best: tuple[float, float, list[int]] | None = None
    best_conf = 0.0
    for i, j in itertools.combinations(range(len(anchors)), 2):
        if ts[j] == ts[i]:
            continue
        a = (px[j] - px[i]) / (ts[j] - ts[i])
        if a == 0:
            continue  # degenerate: a pile of conflicting reads on one
            # grid line is not an axis, whatever its inlier count.
        b = px[i] - a * ts[i]
        inl = [k for k in range(len(anchors)) if abs((a * ts[k] + b) - px[k]) <= inlier_tol_px]
        # Equal-support ties prefer the higher-confidence consensus: with
        # multi-candidate snapping, every word proposes neighbouring
        # gridlines too, and the systematically shifted ghost line ties the
        # true line on support while losing on snap distance. Without the
        # tie-break, input order would pick true-or-ghost arbitrarily.
        conf = sum(float(anchors[k].confidence) for k in inl)
        if best is None or _support(inl) > _support(best[2]) or (
                _support(inl) == _support(best[2]) and conf > best_conf):
            best = (a, b, inl)
            best_conf = conf
    if best is None or _support(best[2]) < 2:
        raise CalibrationUnresolved(
            "Anchors are degenerate (coincident transform values).",
            ["two anchors with distinct axis values"],
        )
    a, b, inl = best
    # Refit on inliers by confidence-weighted least squares: a shaky
    # margin re-read that slips inside the inlier gate by a pixel must
    # not drag the intercept with the same weight as solid ticks.
    t_arr = np.array([ts[k] for k in inl])
    p_arr = np.array([px[k] for k in inl])
    w_arr = np.array([max(0.05, float(anchors[k].confidence)) for k in inl])
    if len(inl) == 2:
        a = float((p_arr[1] - p_arr[0]) / (t_arr[1] - t_arr[0]))
        b = float(p_arr[0] - a * t_arr[0])
    else:
        a, b = (float(v) for v in np.polyfit(t_arr, p_arr, 1, w=w_arr))
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

    Gridline positions carry a few pixels of detection noise, so a strict
    pass runs first and a single doubled-tolerance retry follows: passing
    panels see byte-identical results while noisy grids still resolve. The
    retry is marked in the fit method.
    """
    try:
        return _fit_axis_once(anchors, role, unit, scale, inlier_tol_px, min_anchors,
                              4.0 * inlier_tol_px)
    except CalibrationUnresolved as strict_exc:
        try:
            relaxed = _fit_axis_once(anchors, role, unit, scale,
                                     2.0 * inlier_tol_px, min_anchors,
                                     4.0 * inlier_tol_px)
        except CalibrationUnresolved:
            raise strict_exc from None
        relaxed.method += "+retol"
        return relaxed


def _fit_axis_once(
    anchors: list[TickAnchor],
    role: AxisRole,
    unit: str,
    scale: ScaleType | None,
    inlier_tol_px: float,
    min_anchors: int,
    support_tol_px: float,
) -> AxisFit:
    """Single-tolerance axis fit; see ``fit_axis`` for the contract."""
    if scale is ScaleType.LOG10 and not any(a.value > 0 for a in anchors):
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
        if role in (AxisRole.Y_LEFT, AxisRole.Y_RIGHT) and a >= 0:
            continue  # pixel rows grow downward while axis values grow
            # upward in every chart: a non-negative y slope is a misread
            # value ('90' as '30'), never an axis.
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
    # Support counts distinct pixel rows (see _fit_from_anchors): twin
    # reads of one label corroborate nothing.
    n = len({round(a.pixel) for a in best.anchors_used})
    if n < min_anchors:
        # Two anchors define the affine map; demand independent corroboration.
        # Support stays at strict tolerance even on the relaxed retry: a
        # corroborating tick far off the line means the line is wrong.
        # Non-positive values can never corroborate a log axis ('0' and
        # sign-fragment misreads); attempting log10 on them crashes the
        # whole panel instead of merely failing the fit.
        support = [a for a in anchors if a not in best.anchors_used]
        if best.scale is ScaleType.LOG10:
            support = [a for a in support if a.value > 0]
        ok = any(
            abs(best.a * (math.log10(s.value) if best.scale is ScaleType.LOG10 else s.value)
                + best.b - s.pixel) <= support_tol_px
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


_OFFSET_RE = re.compile(r"offset\s*:?\s*(-?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)


def parse_di_offset(label: str) -> float | None:
    """Explicit ``(Offset:45dB)`` annotation in a legend label.

    Some vendors plot directivity curves shifted up by a fixed dB offset so
    they share the panel, and print the shift in the label. The parenthesised
    form is authoritative when present; None means unstated (the identity
    search in ``solve_di_offset`` must recover it).
    """
    if not label:
        return None
    m = _OFFSET_RE.search(label)
    return float(m.group(1)) if m else None


def solve_di_offset(
    di_pixels: dict[float, float],
    refs: list[tuple[str, dict[float, float]]],
    left_a: float,
    left_b: float,
    min_points: int = 10,
    max_iqr_db: float = 0.75,
) -> tuple[float, tuple[str, str], float, int] | None:
    """Recover a directivity curve's plot offset from the DI identity.

    A directivity curve is the difference of two measured dB curves, plotted
    shifted by a fixed offset (``plotted = (A - B) + N``) through the shared
    left-axis mapping (same panel, same pixels per dB). Inputs are OBSERVED
    pixel columns (``{u: v}``); both sides are converted to plotted dB
    through the left fit, so only measurements vote, never model fills. For
    every ordered reference pair the offset residuals ``plotted - (A - B)``
    are formed over common columns; the true pair's residuals collapse to a
    constant (the offset) while wrong pairs vary with frequency. Returns
    ``(offset, (label_a, label_b), iqr, n)`` for the tightest pair, or None
    when no pair is tight enough: an unidentified offset stays uncalibrated
    rather than guessed.
    """
    if left_a == 0 or len(di_pixels) < min_points or len(refs) < 2:
        return None

    def _db(pix: dict[float, float]) -> dict[float, float]:
        return {u: (v - left_b) / left_a for u, v in pix.items()}

    plotted = _db(di_pixels)
    db_refs = [(label, _db(pix)) for label, pix in refs]
    best: tuple[float, tuple[str, str], float, int] | None = None
    for i, (la, da) in enumerate(db_refs):
        for j, (lb, db) in enumerate(db_refs):
            if i == j:
                continue
            common = [u for u in plotted if u in da and u in db]
            if len(common) < min_points:
                continue
            resid = np.array([plotted[u] - (da[u] - db[u]) for u in common])
            q75, q25 = float(np.percentile(resid, 75)), float(np.percentile(resid, 25))
            iqr = q75 - q25
            if iqr <= max_iqr_db and (best is None or iqr < best[2]):
                best = (float(np.median(resid)), (la, lb), iqr, len(common))
    return best


_OFFSET_CONSENSUS_BIN = 0.75
"""Residual window (dB) for the consensus offset peak."""
_OFFSET_CONSENSUS_FRAC = 0.15
"""Minimum share of residuals inside the peak window."""
_OFFSET_SELF_OVERLAP = 0.5
"""Maximum pixel overlap with the pair for a valid consensus.

A latched measured curve explains itself through a flat reference at
that reference's level; its pixels coincide with the pair's, while a
true directivity track inks its own rows.
"""


def _consensus_di_offset(
    di_pixels: dict[float, float],
    refs: list[tuple[str, dict[float, float]]],
    left_a: float,
    left_b: float,
    min_points: int = 10,
) -> tuple[float, tuple[str, str], float, int] | None:
    """Offset from the tightest residual consensus, for mixed tracks.

    Strict ``solve_di_offset`` needs the whole track on one curve; a
    track hopping between twin directivity ink (Ascilab SPDI rides
    blue dashes and orange solid) spreads globally but keeps a tight
    peak at the true offset. Per pair this takes the fullest sliding
    ``_OFFSET_CONSENSUS_BIN`` window, requires ``_OFFSET_CONSENSUS_FRAC``
    of residuals inside, and rejects self-explaining pairs (pixel
    overlap with the pair at ``_OFFSET_SELF_OVERLAP``). Returns
    ``(offset, (label_a, label_b), peak_frac, n_peak)`` for the
    fullest valid peak, else None.
    """
    if left_a == 0 or len(di_pixels) < min_points or len(refs) < 2:
        return None

    def _db(pix: dict[float, float]) -> dict[float, float]:
        return {u: (v - left_b) / left_a for u, v in pix.items()}

    plotted = _db(di_pixels)
    best: tuple[float, tuple[str, str], float, int] | None = None
    for i, (la, da0) in enumerate(refs):
        for j, (lb, dbb0) in enumerate(refs):
            if i == j:
                continue
            da, dbb = _db(da0), _db(dbb0)
            common = [u for u in plotted if u in da and u in dbb]
            if len(common) < min_points:
                continue
            resid = sorted(plotted[u] - (da[u] - dbb[u]) for u in common)
            n = len(resid)
            peak_n, peak_med, k = 0, 0.0, 0
            for left_i in range(n):
                while k < n and resid[k] - resid[left_i] <= _OFFSET_CONSENSUS_BIN:
                    k += 1
                if k - left_i > peak_n:
                    peak_n = k - left_i
                    peak_med = float(np.median(resid[left_i:k]))
            if peak_n < min_points or peak_n / n < _OFFSET_CONSENSUS_FRAC:
                continue
            di_px = {(u, round(di_pixels[u])) for u in common}
            ab_px = {(u, round(da0[u])) for u in common}
            ab_px |= {(u, round(dbb0[u])) for u in common}
            if len(di_px & ab_px) / len(di_px) >= _OFFSET_SELF_OVERLAP:
                continue
            if best is None or peak_n > best[3]:
                best = (peak_med, (la, lb), peak_n / n, peak_n)
    return best


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
