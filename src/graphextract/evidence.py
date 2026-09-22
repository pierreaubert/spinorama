# -*- coding: utf-8 -*-
"""Curve evidence at native resolution, without destructive preprocessing.

The raster is never sharpened, denoised, dilated-opened, or cropped for
measurement; layers are predicted separately (curve / grid / background) and
may overlap. One-pixel strokes survive because no morphological cleanup runs
by default. Centerlines are refined against the native cross-stroke intensity
profile with an explicit uncertainty interval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import math

import cv2
import numpy as np
import numpy.typing as npt


@dataclass
class StyleSpec:
    """Per-series colour identity inferred per panel (never a global fixed name)."""

    series_id: str
    label: str
    bgr: tuple[int, int, int]
    channel_tol: tuple[int, int, int] = (40, 40, 40)
    # Legend key box in image-global ``(x, y, w, h)`` when the style came
    # from a parsed legend; None for explicit/discovered styles. Keys
    # inside the panel would otherwise hand their series a hijack lane.
    key_xywh: tuple[int, int, int, int] | None = None


@dataclass
class EvidenceLayers:
    """Separate, possibly overlapping evidence layers in native coordinates."""

    curve_masks: dict[str, npt.NDArray]  # raw uint8 masks, unmodified
    grid_mask: npt.NDArray
    background_bgr: tuple[int, int, int]
    provenance: dict = field(default_factory=dict)
    # Union candidacy (uint8): every series' unsubtracted ink OR-ed.
    # Tracking clusters candidates from this inclusive union (gridlines
    # keep their structural role: seeding, coverage, occlusion status),
    # while ownership comes from the grid-subtracted curve masks, so a
    # grid-coloured series can be covered by grid ink but never ride it.
    # None (hand-built layers) falls back to OR-ing the curve masks.
    union_mask: npt.NDArray | None = None


def estimate_background(plot_img: npt.NDArray) -> tuple[int, int, int]:
    """Median colour over the whole region as the compositing background.

    Curves, grids, and frames are thin minorities, so the median is the paper
    colour even when the region border itself is a dark frame. A border-only
    median would lock onto that frame and corrupt foreground unmixing.
    """
    med = np.median(plot_img.reshape(-1, 3).astype(float), axis=0)
    return (int(med[0]), int(med[1]), int(med[2]))


def detect_grid_mask_thin(plot_img: npt.NDArray) -> npt.NDArray:
    """Grid/frame mask: panel-spanning axis-aligned ink, cores plus skirts."""
    h, w = plot_img.shape[:2]
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY) if plot_img.ndim == 3 else plot_img
    # Faint-first ink: grid greys wash down to ~7 below the background,
    # far below textbook edge thresholds, and a missed gridline is a
    # phantom curve the tracker will happily ride. Hough runs on the ink
    # itself (not Canny edges, which mark a faint line's flanks while its
    # core — the part the tracker rides — survives unmarked); the length
    # gate below, not the ink strength, tells grid from curves.
    bg = float(np.median(np.asarray(gray).reshape(-1)))
    ink = (((np.asarray(gray).astype(float) < bg - 5.0).astype(np.uint8)) * 255)
    mask = np.zeros((h, w), dtype=np.uint8)
    from graphextract.calibration import unpack_hough_lines

    # Panel-spanning only: gridlines run edge to edge, while curve
    # segments (DI flats, wall fragments) never reach 90% of the panel.
    # Anything shorter stays curve evidence; subtracting it would punch
    # honest strokes full of holes. The gap bridges faint-line patchiness
    # and curve crossings, never whole missing lines.
    lines = cv2.HoughLinesP(
        ink, 1, np.pi / 180, threshold=50,
        minLineLength=int(0.9 * min(h, w)), maxLineGap=25,
    )
    for x1, y1, x2, y2 in unpack_hough_lines(lines):
        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            cv2.line(mask, (x1, y1), (x2, y2), 255, 1)
    # Undilated: faint 1px skirts beside the subtracted core are too
    # weak to ride (a single faint pixel against live motion), while any
    # dilation would eat thin-curve fringe between dense minor gridlines.
    return mask


def mixture_match(
    plot_img: npt.NDArray,
    background_bgr: tuple[int, int, int],
    fg_bgr: tuple[int, int, int],
    alpha_min: float = 0.25,
    alpha_max: float = 1.3,
    residual_tol: float = 30.0,
    spread_tol: float = 0.3,
) -> npt.NDArray:
    """Match pixels explainable as ``alpha * fg + (1 - alpha) * background``.

    Anti-aliased thin strokes have no fully saturated interior pixel; their
    edge colours are foreground/background mixtures. A pixel matches when the
    per-channel implied coverages agree (spread), the coverage is substantial
    (alpha floor rejects desaturated grid greys) but not over-full (pixels
    much darker than the template are a different ink: black cores unmix
    cleanly against grey templates at alpha ~1.8), and the reconstructed
    colour fits on every channel (rejects black text/frames that mimic full
    coverage on a subset of channels).
    """
    px = plot_img.astype(np.float32)
    bg = np.array(background_bgr, dtype=np.float32).reshape(1, 1, 3)
    fg = np.array(fg_bgr, dtype=np.float32).reshape(1, 1, 3)
    denom = bg - fg
    significant = np.abs(denom) > 20.0  # (1, 1, 3) broadcast mask
    if not significant.any():
        return np.zeros(plot_img.shape[:2], dtype=bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha_c = np.where(significant, (bg - px) / np.where(significant, denom, 1.0), np.nan)
    stack = np.where(np.isnan(alpha_c), np.nan, alpha_c)
    with np.errstate(all="ignore"):
        alpha_hat = np.nanmedian(stack, axis=2)
        spread = np.nanmax(stack, axis=2) - np.nanmin(stack, axis=2)
    pred = alpha_hat[..., None] * fg + (1.0 - alpha_hat[..., None]) * bg
    residual = np.max(np.abs(px - pred), axis=2)
    return ((alpha_hat >= alpha_min) & (alpha_hat <= alpha_max)
            & (spread <= spread_tol) & (residual <= residual_tol))


_EVIDENCE_MIN_DEPTH = 8.0
"""Darkness below background a pixel needs to count as curve evidence.

Grey-level depth (background grey minus pixel grey). Near-grey seeds
match JPEG noise (~5-7 deep) through both the box test and mixture
unmixing, and the tracker then wanders the noise field on invented
takes; true strokes (even pale 1px ones) clear 8 in their cores on
every column while noise columns mostly drop out, so continuity
bridges honest holes instead of paving noise flats.
"""

_CHROMA_SEED_SPREAD = 20.0
"""Seed max-min channel spread that counts as a chromatic identity."""

_CHROMA_MIN_SPREAD = 12.0
"""Pixel max-min spread a chromatic seed's evidence must carry.

Grey impostors — tick-glyph edges, grid skirts, paper noise — unmix
into pastel seeds' masks and hand the tracker (and the seed take)
foreign attractors. True pastel pixels always carry their hue (even
1px cores), while impostor greys sit near spread 0-3; per-column
truth survives on cores alone. Achromatic seeds (grey, black) cannot
use hue and keep the depth floor only.
"""


def segment_evidence(
    plot_img: npt.NDArray,
    styles: list[StyleSpec],
    cleanup: bool = False,
    exclude: Sequence[tuple[int, int, int, int]] = (),
) -> EvidenceLayers:
    """Build per-series colour masks without destroying thin evidence.

    Each style matches saturated core pixels (box test) OR anti-aliased edge
    mixtures (foreground/background unmixing). ``cleanup`` enables
    morphological open/close for display previews only; measurement masks
    always keep the raw match. Grid pixels are reported in their own layer
    and subtracted from curve evidence (see below).

    ``exclude`` (interior-local ``(x, y, w, h)`` text boxes, e.g. legend
    words and in-plot tick digits) zeroes curve evidence: text ink is never
    curve ink, and legend keys would otherwise hand their series a hijack
    lane through the legend zone. Absurdly large boxes (a dimension past
    half the interior) are watermarks/titles spanning live data, not
    labels, and are left alone so good evidence survives.

    Grid pixels subtract from a curve mask only when that seed can meet
    the grid: seeds near the grey axis (grey, pastel, washed) match grey
    gridlines through the box test or mixture unmixing and would otherwise
    ride gridlines as happily as their curve. Saturated seeds never meet
    grey, so their masks keep every crossing pixel exactly. The grid mask
    is drawn 1px thin, so multi-pixel strokes keep their crossing pixels
    and only true 1px riders bridge over 1-2 columns. The frame itself
    (panel-spanning, so grid-detected) never subtracts: curve endpoints
    live at the frame, and only inner grid confuses tracking.

    Mixture-only pixels within a few pixels of the interior border are
    dropped when achromatic: that band holds the frame/axis furniture
    (greys) whose antialiased edges unmix into dark curve colours and would
    otherwise hand every series a full-height hijack lane at the plot edge.
    Core (box-test) pixels survive everywhere, as do chromatic endpoint
    fringes, so true curve endpoints are preserved.
    (Frame rides by grey curves are stopped at re-seed time instead:
    removing border pixels fragments union connectivity and flips seed
    takes, while re-seeds onto the frame are simply vetoed.)

    Both match paths additionally require ``_EVIDENCE_MIN_DEPTH`` grey
    levels of darkness below the background: without a floor, near-grey
    seeds match paper noise through either path. Chromatic seeds
    additionally require ``_CHROMA_MIN_SPREAD`` of pixel colour spread:
    grey impostor pixels carry no hue to attribute.
    """
    h, w = plot_img.shape[:2]
    bg = estimate_background(plot_img)
    grid = detect_grid_mask_thin(plot_img)
    blocked = np.zeros((h, w), dtype=bool)
    for x, y, bw_, bh_ in exclude:
        if bw_ >= w / 2 or bh_ >= h / 2:
            continue
        x0, y0 = max(0, x - 2), max(0, y - 2)
        x1, y1 = min(w, x + bw_ + 2), min(h, y + bh_ + 2)
        if x1 > x0 and y1 > y0:
            blocked[y0:y1, x0:x1] = True
    border = np.zeros((h, w), dtype=bool)
    bw = min(4, h // 2, w // 2)
    if bw > 0:
        border[:bw, :] = True
        border[-bw:, :] = True
        border[:, :bw] = True
        border[:, -bw:] = True
    px = plot_img.astype(np.int16)
    spread = np.max(px, axis=2) - np.min(px, axis=2)
    achromatic = spread < 25
    gray = cv2.cvtColor(plot_img, cv2.COLOR_BGR2GRAY).astype(float)
    bg_gray = 0.114 * bg[0] + 0.587 * bg[1] + 0.299 * bg[2]
    deep = (bg_gray - gray) >= _EVIDENCE_MIN_DEPTH
    colourful = spread >= _CHROMA_MIN_SPREAD
    masks: dict[str, npt.NDArray] = {}
    union = np.zeros((h, w), dtype=np.uint8)
    for spec in styles:
        ref = np.array(spec.bgr, dtype=np.int16).reshape(1, 1, 3)
        tol = np.array(spec.channel_tol, dtype=np.int16).reshape(1, 1, 3)
        box = np.all(np.abs(px - ref) <= tol, axis=2)
        mixed = mixture_match(plot_img, bg, spec.bgr) & ~(border & achromatic)
        hue_ok = (colourful if float(np.max(spec.bgr) - np.min(spec.bgr))
                  >= _CHROMA_SEED_SPREAD else True)
        hit = (box | mixed) & deep & hue_ok & ~blocked
        union = np.bitwise_or(union, hit.astype(np.uint8) * 255)
        # Distance to the grey axis: only grid-coloured seeds meet the
        # grid (box tolerance 40 plus mixture skirts); saturated seeds
        # keep every crossing pixel exactly.
        grey_axis = float(np.mean(np.array(spec.bgr, dtype=float)))
        meets_grid = (float(np.linalg.norm(
            np.array(spec.bgr, dtype=float) - grey_axis)) < 60.0)
        cut = ((grid > 0) & ~border) if meets_grid else np.zeros((h, w), dtype=bool)
        raw = ((hit & ~cut).astype(np.uint8)) * 255
        if cleanup and raw.any():
            k = np.ones((2, 2), np.uint8)
            raw = cv2.morphologyEx(cv2.morphologyEx(raw, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
        if raw.any():
            masks[spec.series_id] = raw
    return EvidenceLayers(curve_masks=masks, grid_mask=grid, background_bgr=bg,
                          union_mask=union,
                          provenance={"cleanup_preview_only": cleanup})


def refine_centerline(
    gray: npt.NDArray,
    col_x: int,
    y_guess: float,
    bg_value: float,
    window: int = 3,
    weights: npt.NDArray | None = None,
) -> tuple[float, float]:
    """Fit a parabola to the cross-stroke darkness profile around y_guess.

    ``weights`` (per-row, same span as the window) restricts the fit to one
    series' own evidence; without it the fit locks onto whichever nearby
    stroke is darkest and identities bleed at crossings.

    Returns (center_y, half_width_px). Low contrast or flat curvature yields a
    wide interval instead of a false precise position.
    """
    h = gray.shape[0]
    ys = np.arange(max(0, int(y_guess) - window), min(h, int(y_guess) + window + 1))
    if len(ys) < 3:
        return float(y_guess), float(window)
    dark = bg_value - gray[ys, col_x].astype(float)
    if weights is not None:
        dark = dark * np.asarray(weights, dtype=float).reshape(-1)
    peak = float(dark.max())
    if peak < 8.0:  # indistinguishable from background noise
        return float(y_guess), float(window)
    # Centroid of the profile above half maximum: unbiased for both sharp
    # one-pixel strokes and flat-top wide strokes (a first-maximum or
    # parabola-peak estimator biases the latter by half the plateau width).
    half_max = 0.5 * (peak + float(dark.min()))
    w = np.clip(dark - half_max, 0.0, None)
    total = float(w.sum())
    if total <= 0:
        return float(ys[int(np.argmax(dark))]), 1.0
    center = float(np.sum(ys.astype(float) * w) / total)
    var = float(np.sum(w * (ys.astype(float) - center) ** 2) / total)
    half_width = min(2.0, max(0.3, math.sqrt(var)))
    return center, half_width
