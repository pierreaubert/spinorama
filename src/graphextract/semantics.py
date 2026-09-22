# -*- coding: utf-8 -*-
"""Legend semantics (plan-20260810, section 6F): swatches + labels -> series.

Legend text and swatches are matched to tracked identities by colour evidence.
A VLM may *propose* chart family, units, or legend associations for unfamiliar
layouts through the VLMProvider protocol, but every proposal is validated
against OCR text and geometry before it can touch a result — generated
coordinates or labels never become measurement authority on their own.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.calibration import parse_tick_label

KNOWN_UNITS = {"Hz", "kHz", "dB", "dBSPL", "%", "s", "ms", "V", "Pa", "deg", ""}
KNOWN_FAMILIES = {"distortion", "thd", "distortion_percent", "frequency_response",
                  "step_response", "cea2034", "early_reflections", "unknown"}


@dataclass
class LegendEntry:
    text: str
    word_xywh: tuple[int, int, int, int]
    swatch_bgr: tuple[int, int, int] | None = None
    swatch_xywh: tuple[int, int, int, int] | None = None
    kind: str = "box"  # box (filled swatch) | line (horizontal line sample)


@dataclass
class LegendResult:
    """Whether a legend was found, with one entry per curve."""

    has_legend: bool
    entries: list[LegendEntry] = field(default_factory=list)
    bbox_xywh: tuple[int, int, int, int] | None = None  # union of entries
    confidence: float = 0.0
    method: str = "swatch+text"


@dataclass
class LegendAssociation:
    series_id: str
    label: str | None  # None = anonymous ID preserved, association uncertain
    source: str  # color | vlm | none
    confidence: float = 0.0


def _swatch_components(img: npt.NDArray) -> list[tuple[tuple[int, int, int, int], tuple[int, int, int]]]:
    """Small saturated blobs (legend swatches); returns (xywh, median bgr).

    Keys are horizontal: wider than tall. Tall narrow blobs are glyph
    strokes (caption/annotation text), never legend keys.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = ((hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 80)).astype(np.uint8) * 255
    contours, _ = cv2.findContours(sat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        # Wide solid bars (~130x22) key legend items on some renders;
        # frame/grid strokes still span hundreds of pixels and stay out.
        if not (4 <= w <= 160 and 4 <= h <= 60 and 25 <= area <= 5200):
            continue
        if w < h:
            continue
        # A filled key is a solid rectangle; anti-aliased text fragments
        # that pass the saturation filter are irregular and sparse.
        if area / (w * h) < 0.65:
            continue
        region = img[y:y + h, x:x + w].reshape(-1, 3)
        med = tuple(int(v) for v in np.median(region.astype(float), axis=0))
        out.append(((x, y, w, h), med))
    return out


@dataclass
class _Sample:
    """One colour key: a filled box swatch or a horizontal line sample."""

    xywh: tuple[int, int, int, int]
    bgr: tuple[int, int, int]
    kind: str  # box | line


def _line_samples(img: npt.NDArray, ink_thresh: float = 30.0) -> list[_Sample]:
    """Detect thin horizontal coloured line samples (``— label`` legends).

    Real legends usually key each curve with a short line segment, not a
    filled box. Colour is sampled from ink pixels only (pixels far from the
    background), so thin segments on white still resolve, including
    unsaturated black/gray samples a saturation filter would miss. Long
    grid/frame strokes are excluded by the width cap.
    """
    bg = np.median(img.reshape(-1, 3).astype(float), axis=0)
    dist = np.max(np.abs(img.astype(float) - bg), axis=2)
    fg = (dist > ink_thresh).astype(np.uint8) * 255
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Keys are short segments (high-resolution renders reach ~130px);
        # frame/grid strokes span hundreds of pixels and stay excluded.
        # Tall solid bars (~130x22) key items on some renders; label text
        # stays out through the ink-density gate below.
        if not (12 <= w <= 160 and 1 <= h <= 30):
            continue
        # Dashed keys fragment into short dashes (~19x10 on high-resolution
        # renders); aspect 1.5 admits them while tall text strokes and
        # sparse glyph runs still fail this gate or the density gate below.
        if w / max(1, h) < 1.5 or cv2.contourArea(cnt) < 30:
            continue
        region = img[y:y + h, x:x + w].reshape(-1, 3).astype(float)
        ink_mask = np.max(np.abs(region - bg), axis=1) > ink_thresh
        # Rendered label text also forms horizontal ink runs, but its strokes
        # are sparse (ink fraction ~0.5); solid keys are dense (~0.95).
        if float(ink_mask.mean()) < 0.7:
            continue
        ink = region[ink_mask]
        if len(ink) == 0:
            continue
        # Core, not fringe average: thin high-resolution keys carry light
        # anti-aliased skirts rows wide, and the median over all ink pixels
        # lands halfway to white (PMC12 On Axis read #57839a for a #23577b
        # stroke). The most saturated quartile is the stroke core; darkness
        # breaks ties so unsaturated black/gray keys still resolve.
        spread = ink.max(axis=1) - ink.min(axis=1)
        dark = 765.0 - ink.sum(axis=1)
        order = np.argsort(spread * 1024.0 + dark, kind="stable")
        core = ink[order[max(0, len(order) * 3 // 4):]]
        m = core.mean(axis=0)
        med = (int(m[0]), int(m[1]), int(m[2]))
        out.append(_Sample((x, y, w, h), med, "line"))
    return _merge_dash_fragments(out)


def _merge_dash_fragments(samples: list[_Sample]) -> list[_Sample]:
    """Join collinear same-colour fragments of one dashed legend key.

    Applies across detector kinds: a dashed key surfaces as line fragments,
    saturated box dashes, or a mix (long first dash plus short fragments),
    so per-dash entries would otherwise split one curve's label across
    several keys. A merged key reads as a line sample however it was
    detected, keeping it out of the indistinct-box filter.
    """
    merged: list[_Sample] = []
    for s in sorted(samples, key=lambda c: (c.xywh[1], c.xywh[0])):
        sx, sy, sw, sh = s.xywh
        hit = None
        for m in merged:
            mx, my, mw, mh = m.xywh
            same_row = abs((sy + sh / 2.0) - (my + mh / 2.0)) <= 4.0
            # Zero when the fragments overlap (both detectors saw the
            # same dash); otherwise the edge-to-edge gap. Dash pitch on
            # low-resolution renders reaches ~14px between fragments.
            gap = max(sx - (mx + mw), mx - (sx + sw), 0)
            same_color = float(np.linalg.norm(np.array(s.bgr) - np.array(m.bgr))) <= 60.0
            if same_row and gap <= 18 and same_color:
                hit = m
                break
        if hit is None:
            merged.append(s)
        else:
            mx, my, mw, mh = hit.xywh
            x0, y0 = min(mx, sx), min(my, sy)
            x1, y1 = max(mx + mw, sx + sw), max(my + mh, sy + sh)
            hit.xywh = (x0, y0, x1 - x0, y1 - y0)
            hit.kind = "line"
    return merged


def _zigzag_samples(img: npt.NDArray, words: Sequence = ()) -> list[_Sample]:
    """Detect zigzag polyline keys (``/\\/\\ label`` legends).

    Some vendors key curves with a small zigzag stroke inside a frame
    instead of a line segment or filled box. A zigzag is one connected ink
    run spanning a key-sized box but too sparse for the line density gate.
    Glyphs are excluded two ways: multi-glyph text splits into several
    narrow contours (never one wide run), and a run dwarfed by an
    overlapping OCR word box is a glyph part, never a key (OCR also
    misreads key fragments as words, but those boxes are key-sized, not
    bigger). Colour comes from the darker half of the chromatic ink
    (channel spread past the pastel gate): the zigzag stroke is the
    saturated minority over a grey frame, pale or dark, so saturation
    separates stroke from frame and darkness separates stroke core
    from halo. Unsaturated keys fall back to the darkest few dozen
    pixels (the stroke core, not a frame-polluted quartile).
    """
    bg = np.median(img.reshape(-1, 3).astype(float), axis=0)
    dist = np.max(np.abs(img.astype(float) - bg), axis=2)
    fg = (dist > 30).astype(np.uint8) * 255
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [(w.x, w.y, w.w, w.h) for w in words]
    out = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if not (30 <= w <= 120 and 10 <= h <= 70):
            continue
        if not (0.08 <= cv2.contourArea(cnt) / (w * h) <= 0.5):
            continue
        touching = [(bx, by, bw, bh) for bx, by, bw, bh in boxes
                      if x - 2 < bx + bw and bx - 2 < x + w
                      and y - 2 < by + bh and by - 2 < y + h]
        # Overlapping misreads of the icon itself ('ly' + '"51:' over one
        # zigzag) are one cluster, not a text run: only disjoint word
        # groups count, so a key under a misread cluster survives while
        # a real multi-word text run still vetoes.
        clusters: list[list[tuple[int, int, int, int]]] = []
        for b in touching:
            bx, by, bw, bh = b
            placed = False
            for c in clusters:
                if any(bx - 2 < ox + ow and ox - 2 < bx + bw
                       and by - 2 < oy + oh and oy - 2 < by + bh
                       for ox, oy, ow, oh in c):
                    c.append(b)
                    placed = True
                    break
            if not placed:
                clusters.append([b])
        if len(clusters) >= 2:
            # A text run spans its words; a key only ever touches its own
            # label's edge.
            continue
        if any(max(0, min(bx + bw, x + w) - max(bx, x))
               * max(0, min(by + bh, y + h) - max(by, y)) >= 0.6 * w * h
               and getattr(wd, "confidence", 1.0) >= 0.75
               for wd, (bx, by, bw, bh) in zip(words, boxes)):
            # One connected glyph run ('Woofer' with merged strokes) overlaps
            # a single word, but a confident OCR read covering most of the
            # run means it is that word's glyphs, not a key: a key only
            # touches its label's edge, and key-fragment misreads never
            # read this confidently.
            continue
        if any(bx - 2 < x and x + w < bx + bw + 2
               and by - 2 < y and y + h < by + bh + 2
               and bw * bh >= 2 * w * h for bx, by, bw, bh in boxes):
            continue
        region = img[y:y + h, x:x + w].reshape(-1, 3).astype(float)
        ink = region[np.max(np.abs(region - bg), axis=1) > 30]
        if len(ink) == 0:
            continue
        spread = ink.max(axis=1) - ink.min(axis=1)
        chroma = ink[spread >= 22.0]
        if len(chroma) >= 8:
            # Saturated stroke substance: spread already proves key ink,
            # so the pale-frame value veto below does not apply (a vivid
            # red stroke reads V=220 yet is exactly the key's colour).
            # The darker half is the stroke core; the pale half is its
            # anti-aliased halo, which would wash the median toward grey.
            dark = 765.0 - chroma.sum(axis=1)
            order = np.argsort(dark, kind="stable")
            ink = chroma[order[max(0, len(order) // 2):]]
        else:
            take = min(max(8, len(ink) // 4), 48)
            ink = ink[np.argsort(np.max(bg - ink, axis=1))[-take:]]
            if float(np.median(cv2.cvtColor(
                    ink.reshape(-1, 1, 3).astype(np.float32),
                    cv2.COLOR_BGR2HSV).reshape(-1, 3)[:, 2])) >= 140:
                continue
        med = tuple(int(v) for v in np.median(ink, axis=0))
        out.append(_Sample((x, y, w, h), med, "line"))
    return out


def _scaffold_filter(cands: list[_Sample]) -> list[_Sample]:
    """Drop candidate rows stranded far from every other row.

    Legend rows continue at a steady pitch (single-column legends hold one
    key per row); a row far from every other row is stray ink (title glyph
    fragments, caption bullets), not a legend item. The limit scales with
    the observed row pitch, with an absolute floor for few-row legends.
    With fewer than three rows there is no pitch evidence, so everything
    stays: scaffolding only removes, never invents.
    """
    if len(cands) < 4:
        return cands
    rows: list[list[_Sample]] = []
    for s in sorted(cands, key=lambda c: c.xywh[1] + c.xywh[3] / 2.0):
        cy = s.xywh[1] + s.xywh[3] / 2.0
        if rows and abs(cy - (rows[-1][0].xywh[1] + rows[-1][0].xywh[3] / 2.0)) <= 12:
            rows[-1].append(s)
        else:
            rows.append([s])
    if len(rows) < 3:
        return cands
    cys = sorted(sum(s.xywh[1] + s.xywh[3] / 2.0 for s in r) / len(r)
                 for r in rows)
    pitches = [b - a for a, b in zip(cys, cys[1:])]
    limit = max(48.0, 3.0 * float(np.median(pitches)))
    keep = [min(abs(c - o) for o in cys if o != c) <= limit for c in cys]
    return [s for r, k in zip(rows, keep) if k for s in r]


def _sandwich_filter(img: npt.NDArray, cands: list[_Sample]) -> list[_Sample]:
    """Drop samples with text ink directly above or below them.

    Real keys sit in whitespace (labels run beside the key, rows are well
    separated); a fragment with ink a few pixels above or below sits inside
    a text line, i.e. it is a glyph part, not a key.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, _ = gray.shape
    out = []
    for s in cands:
        sx, sy, sw, sh = s.xywh
        x0, x1 = max(0, sx - 2), sx + sw + 2
        above = gray[max(0, sy - 5):max(0, sy - 1), x0:x1]
        below = gray[min(h, sy + sh + 1):min(h, sy + sh + 5), x0:x1]
        ink = lambda band: band.size > 0 and float((band < 180).mean()) > 0.25
        if ink(above) or ink(below):
            continue
        out.append(s)
    return out


def _interior_filter(cands: list[_Sample], words: Sequence) -> list[_Sample]:
    """Drop samples strictly interior to a word box.

    A sample with word text extending well past it on both sides lies
    inside the word's glyphs (a bar, dot, or stroke fragment), while a
    real key only ever touches a word's edge. Needs OCR boxes; without
    words everything stays.
    """
    if not words:
        return cands
    out = []
    for s in cands:
        sx, sy, sw, sh = s.xywh
        inside = False
        for wd in words:
            if (wd.x + 8 < sx and sx + sw + 8 < wd.x + wd.w
                    and min(wd.y + wd.h, sy + sh) - max(wd.y, sy) > 0.5 * sh):
                inside = True
                break
        if not inside:
            out.append(s)
    return out


def _swatch_candidates(img: npt.NDArray, words: Sequence = ()) -> list[_Sample]:
    """Unified colour keys: boxes, line samples and zigzags, deduped."""
    cands = [_Sample(xywh, bgr, "box") for xywh, bgr in _swatch_components(img)]
    for line in list(_line_samples(img)) + _zigzag_samples(img, words):
        lx, ly, lw, lh = line.xywh
        dup = False
        for i, cand in enumerate(cands):
            cx, cy, cw, ch = cand.xywh
            # Same physical key seen by both detectors: keep the line
            # version, whose ink-only colour survives thin segments on white.
            if (lx - 2 <= cx + cw / 2.0 <= lx + lw + 2
                    and ly - 2 <= cy + ch / 2.0 <= ly + lh + 2):
                dup = True
                if lw / max(1, lh) >= 1.5:
                    cands[i] = line
                break
        if not dup:
            cands.append(line)
    # Dashed keys arrive as one candidate per dash (line fragments, box
    # dashes, or a mix); merge them back into one key per curve so each
    # label maps to exactly one entry.
    merged = _merge_dash_fragments(cands)
    if words:
        merged = _interior_filter(merged, words)
        merged = _sandwich_filter(img, merged)
        merged = _drop_covered_samples(merged, words)
    return _scaffold_filter(merged)


def _row_key_samples(img: npt.NDArray, rows: Sequence[Sequence],
                     exclude: Sequence[tuple[int, int, int, int]] = ()
                     ) -> list[tuple[_Sample, list]]:
    """Keys for legend rows the swatch detectors missed, with their words.

    Faint pastel keys (and keys merged into one image-wide ink web with
    the curves) never surface as components. For each word row, the
    densest ink row in the band beside the words is the key: dark
    label text is excluded by brightness, gridlines by length and
    continuation. Gray keys get a second-chance mask (same gates
    without the chromatic spread floor) with label boxes masked out,
    since glyph fringe is gray. A candidate survives only when its run
    ends near its label: keys lead their words, while curve tangents
    and grid crossings sit far away. Consecutive rows sharing a key
    colour are one multi-row label and merge into a single sample.
    Returns ``(sample, words)`` pairs so rows pair with their own key,
    never with a nearer neighbour row's.
    """
    h, w = img.shape[:2]
    bg = np.median(img.reshape(-1, 3).astype(float), axis=0)
    full = img.reshape(h, w, 3).astype(float)
    groups: list[list] = []  # [rowy, color, box, words]
    cands: list[list] = []  # [ry, words, peak1, peak2]
    for wds in rows:
        wds = list(wds)
        if not wds:
            continue
        ry = float(np.mean([wd.y + wd.h / 2.0 for wd in wds]))
        x0 = min(wd.x for wd in wds)
        # Narrow per-row bands keep the vetoes honest (wide bands admit
        # curve haze that bridges keys into vetoed runs); overlapping
        # bands are resolved by proximity assignment below, not by the
        # search itself. The right edge stops at the word start: dark
        # glyph ink self-excludes from the pastel gates.
        bx0, bx1 = max(0, x0 - 170), min(w, x0 + 5)
        by0, by1 = max(0, int(ry) - 40), min(h, int(ry) + 35)
        gw, gh = bx1 - bx0, by1 - by0
        if gw < 20 or gh < 10:
            continue
        flat = img[by0:by1, bx0:bx1].reshape(-1, 3).astype(float)
        dist = np.max(np.abs(flat - bg), axis=1)
        spread = flat.max(axis=1) - flat.min(axis=1)
        bright = flat.max(axis=1)
        masks = {
            "pastel": ((dist > 25.0) & (spread >= 22.0)
                       & (spread <= 140.0) & (bright > 150.0)),
            "gray": ((dist > 25.0) & (spread < 22.0) & (bright > 150.0)),
        }
        grids: dict[str, npt.NDArray] = {}
        # Glyph fringe hugs glyph cores; keys stand alone. The halo
        # (dark pixels dilated) marks fringe: label boxes exclude only
        # their halo pixels, so a key hiding under a dirty word box
        # (fused dashes inflate the box over its own key) survives while
        # digit fringe sharing the band still masks out.
        dark = (bright < 140.0).reshape(gh, gw)
        halo = cv2.dilate(dark.astype(np.uint8),
                          np.ones((3, 3), np.uint8), iterations=2) > 0
        for name, kept in masks.items():
            grid = kept.reshape(gh, gw)
            if name == "gray" and exclude:
                for wx, wy, ww, wh in exclude:
                    ix0, iy0 = max(bx0, wx - 2), max(by0, wy - 2)
                    ix1, iy1 = min(bx1, wx + ww + 2), min(by1, wy + wh + 2)
                    if ix1 > ix0 and iy1 > iy0:
                        zone = grid[iy0 - by0:iy1 - by0, ix0 - bx0:ix1 - bx0]
                        zone &= ~halo[iy0 - by0:iy1 - by0, ix0 - bx0:ix1 - bx0]
            grids[name] = grid

        def _runs(kr: int, grid: npt.NDArray
                    ) -> list[tuple[int, int, int]]:
            """Contiguous ink runs of one band row as ``(c0, c1, count)``.

            White gaps wider than a few pixels split the row: a key and
            a gridline sharing the row are two candidates, never one
            bridged span. Largest run first.
            """
            cols = np.where(grid[kr])[0]
            if len(cols) < 6:
                return []
            runs: list[tuple[int, int, int]] = []
            start, prev, n = int(cols[0]), int(cols[0]), 1
            for cc in (int(c) for c in cols[1:]):
                if cc - prev > 5:
                    runs.append((bx0 + start, bx0 + prev, n))
                    start, n = cc, 1
                else:
                    n += 1
                prev = cc
            runs.append((bx0 + start, bx0 + prev, n))
            runs.sort(key=lambda r: -(r[2]))
            return runs[:3]

        def _peak(grid: npt.NDArray, counts: npt.NDArray,
                  smooth: npt.NDArray, gray: bool,
                  banned: list[int]
                  ) -> tuple[list[list], int | None, int]:
            """Strongest unbanned row; its runs each face the vetoes.

            Returns ``(peaks, tried, radius)``: ``tried`` is None only
            when the search is exhausted (nothing left above the noise
            floor), so a fully vetoed row bans its neighbourhood and the
            search continues instead of dying on the first rejection.
            Row-local vetoes (length, density, continuation) ban narrowly:
            neighbouring rows are independent candidates (a key dash
            spans several rows, only some fused with a curve). Tall-body
            vetoes ban widely: the whole run is one wall.
            """
            loc = smooth.copy()
            for er in banned:
                if 0 <= er < gh:
                    loc[er] = -1.0
            kr = int(np.argmax(loc))
            if loc[kr] < 0 or int(counts[kr]) < 6:
                return [], None, 0
            ky = by0 + kr
            out: list[list] = []
            tall_hit = False
            for c0, c1, count in _runs(kr, grid):
                if count < 6:
                    continue
                if c1 - c0 + 1 > 160:
                    continue  # a curve segment, not a key
                # A key dash is solid ink; a sparse wide span is a curve
                # brushing the key column, not a key.
                if count / float(c1 - c0 + 1) < 0.5:
                    continue
                # A run touching both band edges is background structure
                # (a gridline), never a key: keys end well before words.
                if c0 <= bx0 and c1 >= bx1 - 1:
                    continue
                # A key ends at whitespace; a crossing curve continues
                # past it. Only CONNECTED continuation vetoes: nearby but
                # disconnected ink (a neighbouring curve, digit fringe)
                # ends at whitespace and leaves the key standing. Runs
                # clipped by the band edge are exempt: the missing half
                # could be whitespace, and the assignment below keeps
                # only the nearest row's claim anyway.
                clipped = c0 <= bx0 or c1 >= bx1 - 1
                if not clipped:
                    ex0, ex1 = max(0, c0 - 13), min(w, c1 + 14)
                    span = full[ky, ex0:ex1]
                    ink = (np.max(np.abs(span - bg), axis=1) > 25.0)
                    sat = (span.max(axis=1) - span.min(axis=1))
                    sat = sat < 22.0 if gray else sat >= 22.0
                    cont = ink & sat & (span.max(axis=1) > 150.0)
                    dead = False
                    for edge, side in ((c0 - ex0, slice(0, c0 - ex0)),
                                       (c1 + 1 - ex0,
                                        slice(c1 + 1 - ex0, ex1 - ex0))):
                        near = (cont[side][-3:] if edge == c0 - ex0
                                else cont[side][:3])
                        if (len(near) and bool(near.any())
                                and int(cont[side].sum()) >= 10):
                            dead = True
                            break
                    if dead:
                        continue
                # A key dash spans a few rows; a curve wall carries a
                # tall contiguous body through the RUN'S OWN COLUMNS. A
                # wall elsewhere in the band is irrelevant to this run,
                # so the tall check counts only the run's neighbourhood,
                # never the whole band width. Only substantial rows
                # count: faint haze would otherwise bridge any key into
                # a tall run.
                lo, hi = max(0, c0 - 5 - bx0), min(gw, c1 + 6 - bx0)
                lcounts = grid[:, lo:hi].sum(axis=1)
                r0, r1 = kr, kr
                while r0 - 1 >= 0 and lcounts[r0 - 1] >= 10:
                    r0 -= 1
                while r1 + 1 < gh and lcounts[r1 + 1] >= 10:
                    r1 += 1
                if r1 - r0 + 1 >= 12:
                    tall_hit = True
                    continue
                sel = np.zeros(gw, dtype=bool)
                sel[c0 - bx0:c1 - bx0 + 1] = True
                rowpx = flat.reshape(gh, gw, 3)[kr][grid[kr] & sel]
                if len(rowpx) >= 8:
                    # Faint keys read mostly fringe: the colour comes from
                    # the core half (furthest from the background), never
                    # the washed-out median.
                    dd = np.max(np.abs(rowpx - bg), axis=1)
                    core = rowpx[np.argsort(dd)[len(dd) // 2:]]
                    color = tuple(int(v) for v in np.median(core, axis=0))
                elif len(rowpx):
                    color = tuple(int(v) for v in np.median(rowpx, axis=0))
                else:
                    continue
                out.append([ky, color, (c0, ky - 1, c1 - c0 + 1, 3), kr])
            radius = 10 if out or tall_hit else 2
            return out, kr, radius

        peaks: list[list] = []
        for name in ("pastel", "gray"):
            grid = grids[name]
            if int(grid.sum()) < 10:
                continue
            counts = grid.sum(axis=1).astype(float)
            # Keys are strokes several rows tall; a lone speck row never
            # outranks one after vertical smoothing, while single-row
            # argmax would take a bright speck over a faint key.
            smooth = np.convolve(counts, np.ones(5) / 5.0, mode="same")
            banned: list[int] = []
            tries = 0
            found = 0
            while found < 6 and tries < 10:
                tries += 1
                fresh, tried, radius = _peak(grid, counts, smooth,
                                             name == "gray", banned)
                if tried is None:
                    break
                banned.extend(range(max(0, tried - radius),
                                    min(gh, tried + radius + 1)))
                for peak in fresh:
                    found += 1
                    peak.append(name)
                    peaks.append(peak)
        # Keys lead their labels: a run ending far from the word start
        # is a curve tangent or grid crossing, never the row's key.
        word_h = float(np.median([wd.h for wd in wds])) if wds else 12.0
        gap_limit = 1.5 * word_h + 10.0
        valid = [p for p in peaks if -10 <= x0 - (p[2][0] + p[2][2] - 1) <= gap_limit]
        if valid:
            cands.append([ry, wds, valid])
    # Contested key rows go to the nearest word row; losers fall back
    # to their next peak when it is unclaimed, else honestly nothing. A
    # row never takes a peak clearly nearer another row's centreline: a
    # neighbour's dense key spilling into this band is the neighbour's,
    # and taking it would swap the two rows' colours.
    claimed: list[int] = []
    taken: dict[int, list] = {}
    for i in sorted(range(len(cands)),
                    key=lambda i: abs(cands[i][2][0][0] - cands[i][0])):
        ry = cands[i][0]
        for peak in cands[i][2]:
            if any(j != i and abs(peak[0] - cands[j][0]) + 8.0 < abs(peak[0] - ry)
                   for j in range(len(cands))):
                continue
            if not any(abs(peak[0] - c) <= 8 for c in claimed):
                taken[i] = peak
                claimed.append(peak[0])
                break
    for i in sorted(taken):
        ry, wds = cands[i][0], cands[i][1]
        ky, color, box = taken[i][0], taken[i][1], taken[i][2]
        # Sibling pastel paints can sit ~30 apart, so only near-
        # identical consecutive keys merge (one multi-row label);
        # nearby distinct paints stay separate entries.
        if (groups and ry - groups[-1][0] <= 45.0
                and float(np.linalg.norm(np.array(color) - np.array(groups[-1][1]))) <= 25.0):
            prev = groups[-1]
            prev[1] = tuple(int(v) for v in
                            (np.array(prev[1]) + np.array(color)) // 2)
            px, py, pw, ph = prev[2]
            prev[2] = (min(px, box[0]), min(py, box[1]),
                       max(px + pw, box[0] + box[2]) - min(px, box[0]),
                       max(py + ph, box[1] + box[2]) - min(py, box[1]))
            prev[0] = ry
            prev[3].extend(wds)
        else:
            groups.append([ry, color, box, list(wds)])
    return [(_Sample(xywh=g[2], bgr=g[1], kind="line"), g[3]) for g in groups]


def _row_barrier(prev: object, wd: object,
                 samples: list[_Sample]) -> _Sample | None:
    """Rightmost key sample strictly between two same-row words.

    Fused key+text runs overlap their word and never qualify as strictly
    between; only a free-standing key between the words splits the label.
    """
    best: _Sample | None = None
    for s in samples:
        sx, sy, sw, sh = s.xywh
        if abs((sy + sh / 2.0) - (wd.y + wd.h / 2.0)) > max(
                12.0, float(wd.h), float(sh)):
            continue
        if sx > prev.x + prev.w + 2 and sx + sw < wd.x - 2:
            if best is None or sx + sw > best.xywh[0] + best.xywh[2]:
                best = s
    return best


def _drop_covered_samples(samples: list[_Sample],
                          words: Sequence) -> list[_Sample]:
    """Drop key samples printed over a label word's span.

    Title underlines and decorative rules sit inside a word's ink span
    (the word extends well past both edges on the same row); a real key
    leads or trails its label and never hides mid-word. Fused key+text
    ('-Listening') starts at the key, so the word must strictly cover
    the sample with margin, not merely touch it.
    """
    out = []
    for s in samples:
        sx, sy, sw, sh = s.xywh
        scy = sy + sh / 2.0
        covered = False
        for wd in words:
            try:
                wx, wy, ww, wh = wd.x, wd.y, wd.w, wd.h
            except AttributeError:
                continue
            if wx < sx - 8 and wx + ww > sx + sw + 8 and abs(
                    (wy + wh / 2.0) - scy) <= max(12.0, float(wh)):
                covered = True
                break
        if not covered:
            out.append(s)
    return out


def _clean_word_text(text: str) -> str:
    """Strip key-fragment artifacts fused onto a label word's ends.

    OCR merges adjacent key dashes into label words ('—Listening', '=F',
    'Reflections ——'); the dashes are key ink, not label text. Only ends
    are stripped: interior hyphens ('In-Room') and suffixes ('51:') stay.
    """
    return text.strip().strip("-—–_=~«»\"' ")


def _is_tick_word(wd) -> bool:
    """True when an OCR word is an axis tick label, not a legend label.

    Tick labels ('65', '100', '10k') pair with nearby tick marks and grid
    fragments, creating phantom legend entries with tick colours; legend
    labels ('On Axis', '2nd Harmonic') never fully parse as tick values.
    """
    return parse_tick_label(wd.text.strip()) is not None


def _word_hit_by_sample(wd, samples: list[_Sample]) -> bool:
    """True when an OCR word is mostly covered by a colour key.

    OCR misreads a key itself as short text ('mum' on a line sample);
    without this the misread pairs with a neighbouring sample (via the
    right-side fallback) and becomes a phantom entry. Words merely
    containing a key fragment ('—Listening', fused dashes plus label) or
    padding-overlapping a key stay words: pairing assigns them to the key
    they start on, or skips them when they sit fully on top of one.
    """
    wx, wy, ww, wh = wd.x, wd.y, wd.w, wd.h
    if ww <= 0 or wh <= 0:
        return False
    for s in samples:
        sx, sy, sw, sh = s.xywh
        inter = (max(0, min(wx + ww, sx + sw) - max(wx, sx))
                 * max(0, min(wy + wh, sy + sh) - max(wy, sy)))
        if inter >= 0.65 * ww * wh:
            return True
    return False


def _overlaps_key(wd, s: _Sample) -> bool:
    """True when a word box sits mostly on top of a colour key.

    A word mostly covered by a key is either the key's own misread or a
    label tail printed over the NEXT entry's key (crowded rows); in both
    cases the key is not its label's key, so the word must attach further
    left instead. Smaller overlaps are ordinary OCR padding (boxes
    overshoot tight legend gaps by a few pixels) or fused key-plus-text
    words ('—Listening'), and stay candidates, decided by the
    left-preference rule.
    """
    sx, _, sw, _ = s.xywh
    if wd.w <= 0:
        return False
    overlap = min(wd.x + wd.w, sx + sw) - max(wd.x, sx)
    return overlap >= 0.5 * wd.w


def _nearest_sample(wd, samples: list[_Sample]) -> _Sample | None:
    """Nearest row-compatible colour key on the word's left.

    Legend keys precede their labels (``— label``), so a word belongs to
    the nearest key on its left no matter how far: this keeps later words
    of wide high-resolution labels ('2nd' + 'Harmonic', 'Sound' + 'Power
    DI') on their own key instead of drifting to the next item. Only when
    no left key fits is a key on the right considered (words left of all
    keys, inside a ±80px window).
    """
    cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
    # Tall caption words (axis titles) must not reach distant keys: keys
    # sit on their label's baseline, centres never a row-height away.
    vgate = min(max(12.0, float(max(wd.h, 1))), 32.0)
    left = []
    right = []
    for s in samples:
        sx, sy, sw, sh = s.xywh
        scx, scy = sx + sw / 2.0, sy + sh / 2.0
        if abs(scy - cy) > vgate or _overlaps_key(wd, s):
            continue
        score = abs(scx - cx) + 2.0 * abs(scy - cy)
        if scx <= cx:
            left.append((score, s))
        elif scx <= wd.x + wd.w + 80:
            right.append((score, s))
    if left:
        return min(left, key=lambda c: c[0])[1]
    return min(right, key=lambda c: c[0])[1] if right else None


def extract_legend_entries(img: npt.NDArray, words,
                           band_frac: float = 0.14) -> list[LegendEntry]:
    """Pair top-band OCR words with nearby colour keys (boxes and lines)."""
    h, _ = img.shape[:2]
    samples = _swatch_candidates(img, words)
    entries = []
    for wd in words:
        text = _clean_word_text(wd.text)
        if wd.y > band_frac * h or len(text) < 2:
            continue
        if _is_tick_word(wd):
            continue
        # A word sitting mostly on top of a key is the key's own misread
        # ('mum' on a line sample): it would otherwise pair with a
        # neighbouring sample and become a phantom entry. Words merely
        # containing a key fragment ('—Listening') pair on and stay; words
        # sitting fully on top of a key pair with nothing and vanish below.
        if _word_hit_by_sample(wd, samples):
            continue
        best = _nearest_sample(wd, samples)
        entries.append(LegendEntry(
            text=text, word_xywh=(wd.x, wd.y, wd.w, wd.h),
            swatch_bgr=best.bgr if best else None,
            swatch_xywh=best.xywh if best else None,
            kind=best.kind if best else "box"))
    return entries


def detect_legend(img: npt.NDArray, words,
                  roi_xywh: tuple[int, int, int, int] | None = None) -> LegendResult:
    """Decide whether a legend is present and parse one entry per curve.

    Each entry pairs a colour key (filled box swatch or horizontal line
    sample) with its label words, so ``len(entries)`` is the curve count and
    each ``swatch_bgr`` is the curve colour. Multi-word labels on one key
    (e.g. '2nd' + 'Harmonic') are joined. Words that merely re-read a colour
    key are dropped, never counted as curves.
    """
    h, w = img.shape[:2]
    samples = _swatch_candidates(img, words)
    rx, ry, rw, rh = 0, 0, w, h
    if roi_xywh is not None:
        rx, ry, rw, rh = roi_xywh
        samples = [s for s in samples
                   if rx <= s.xywh[0] + s.xywh[2] / 2.0 <= rx + rw
                   and ry <= s.xywh[1] + s.xywh[3] / 2.0 <= ry + rh]
    grouped: dict[int, list[tuple[str, object]]] = {}
    # Row order for barrier splits: a key printed between two words of a
    # row starts a new item ('... Window -- Early ...'), so the right
    # word must not reach past it to the left key.
    order = sorted(
        [wd for wd in words if len(_clean_word_text(wd.text)) >= 2],
        key=lambda v: (v.y + v.h / 2.0, v.x))
    prev_in_row: dict[int, object] = {}
    last: object | None = None
    last_row = 0.0
    for wd in order:
        row = wd.y + wd.h / 2.0
        if last is None or abs(row - last_row) > max(12.0, float(wd.h)):
            last, last_row = wd, row
        prev_in_row[id(wd)] = last
        last, last_row = wd, row
    for wd in words:
        text = _clean_word_text(wd.text)
        if len(text) < 2:
            continue
        if roi_xywh is not None and not (rx <= wd.x <= rx + rw and ry <= wd.y <= ry + rh):
            continue
        if _is_tick_word(wd):
            continue
        # See extract_legend_entries: covered keys are excluded from
        # candidacy, so key-misread words pair with nothing and vanish.
        if _word_hit_by_sample(wd, samples):
            continue
        best = _nearest_sample(wd, samples)
        if best is None:
            continue
        prev = prev_in_row.get(id(wd))
        if prev is not None and prev is not wd:
            barrier = _row_barrier(prev, wd, samples)
            if barrier is not None and (
                    best.xywh[0] + best.xywh[2] <= barrier.xywh[0] + barrier.xywh[2]):
                right = _nearest_sample(wd, [s for s in samples
                                             if s.xywh[0] + s.xywh[2] > barrier.xywh[0]
                                             + barrier.xywh[2]])
                if right is not None:
                    best = right
        grouped.setdefault(id(best), []).append((text, wd))
    if not grouped:
        # No detector keyed any row (faint/thin keys, one ink web):
        # recover a key per legend row from the ink beside the words.
        # Pure fallback only: legends that paired anything keep exactly
        # what paired, so OCR-mangled rows never gain phantom keys.
        unpaired = [wd for wd in words
                    if len(_clean_word_text(wd.text)) >= 2
                    and not _is_tick_word(wd)
                    and not _word_hit_by_sample(wd, samples)]
        rows: list[list] = []
        for wd in sorted(unpaired, key=lambda v: (v.y + v.h / 2.0, v.x)):
            ry = wd.y + wd.h / 2.0
            same_row = (rows and abs(ry - rows[-1][0]) <= max(12.0, float(wd.h)))
            if same_row and abs(ry - rows[-1][0]) > float(wd.h) / 2.0:
                # Same-column stacked words are consecutive rows, not one
                # row: side-by-side row mates never share x. Without the
                # split, tight-pitch legends fuse two labels into one row
                # whose single key goes to the neighbour's contest.
                if any(wd.x < o.x + o.w and o.x < wd.x + wd.w
                       for o in rows[-1][1]):
                    same_row = False
            if same_row:
                rows[-1][1].append(wd)
            else:
                rows.append([ry, [wd]])
        # Only true label words mask out: single-character reads are
        # key fragments ('~', '-') whose boxes sit ON the keys.
        exclude = [(wd.x, wd.y, wd.w, wd.h) for wd in words
                   if len(_clean_word_text(wd.text)) >= 2]
        recovered = _row_key_samples(img, [r[1] for r in rows],
                                     exclude=exclude)
        if recovered:
            samples = list(samples) + [s for s, _ in recovered]
            for sample, wds in recovered:
                for wd in wds:
                    grouped.setdefault(
                        id(sample), []).append((_clean_word_text(wd.text), wd))
    if not grouped:
        return LegendResult(has_legend=False)
    by_id = {id(s): s for s in samples}
    # A line key without label words still counts when it sits on a
    # labelled legend row (its label likely failed OCR); isolated keys, and
    # box keys (whose false positives cluster on watermark rows), do not.
    labelled_rows = [np.mean([wd.y + wd.h / 2.0 for _, wd in wds])
                     for wds in grouped.values()]
    row_h = float(np.median([wd.h for wds in grouped.values() for _, wd in wds]))
    for s in samples:
        if id(s) in grouped or s.kind != "line":
            continue
        scy = s.xywh[1] + s.xywh[3] / 2.0
        if not any(abs(scy - row) <= 1.5 * max(row_h, 1) for row in labelled_rows):
            continue
        # A wordless key bordered by words is a glyph fragment, not a key
        # whose label OCR missed: real missed-label keys stand alone.
        # Every word counts here, paired or not: the fragment that ate its
        # own label ('Woofer' misread as key) still borders it.
        sx, sy, sw, sh = s.xywh
        if any(wd.x - 5 < sx + sw and sx - 5 < wd.x + wd.w
               and wd.y - 5 < sy + sh and sy - 5 < wd.y + wd.h
               and len(_clean_word_text(wd.text)) >= 2 for wd in words
               if roi_xywh is None
               or (rx <= wd.x <= rx + rw and ry <= wd.y <= ry + rh)):
            continue
        grouped[id(s)] = []
    entries = []
    for sid, wds in grouped.items():
        s = by_id[sid]
        if wds:
            # A key with label words extending past both its edges is an
            # inter-word dash ('CEA2034 -- TOPPING'), not a legend key:
            # real keys lead their label, words on one side only. The
            # tolerance covers OCR box overshoot, not whole words.
            kx, _, kw, _ = s.xywh
            min_x = min(wd.x for _, wd in wds)
            max_x = max(wd.x + wd.w for _, wd in wds)
            if min_x < kx - 8 and max_x > kx + kw + 8:
                continue
        wds = sorted(wds, key=lambda t: t[1].x)
        text = " ".join(t for t, _ in wds)
        wds = [wd for _, wd in wds]
        if wds:
            x0 = min([d.x for d in wds] + [s.xywh[0]])
            y0 = min([d.y for d in wds] + [s.xywh[1]])
            x1 = max([d.x + d.w for d in wds] + [s.xywh[0] + s.xywh[2]])
            y1 = max([d.y + d.h for d in wds] + [s.xywh[1] + s.xywh[3]])
            word_box = (x0, y0, x1 - x0, y1 - y0)
        else:
            text = ""
            word_box = s.xywh
        entries.append(LegendEntry(text=text, word_xywh=word_box,
                                  swatch_bgr=s.bgr, swatch_xywh=s.xywh, kind=s.kind))
    entries.sort(key=lambda e: (_key_xy(e)[1] // max(1, int(row_h * 2)), _key_xy(e)[0]))
    entries = _drop_indistinct_box_rows(entries, row_h)
    entries = _drop_misshapen_line_keys(entries)
    entries = _drop_incoherent_keys(entries)
    if not entries:
        return LegendResult(has_legend=False)
    x0 = max(0, min(e.word_xywh[0] for e in entries) - 4)
    y0 = max(0, min(e.word_xywh[1] for e in entries) - 4)
    x1 = min(w, max(e.word_xywh[0] + e.word_xywh[2] for e in entries) + 4)
    y1 = min(h, max(e.word_xywh[1] + e.word_xywh[3] for e in entries) + 4)
    rows = {_key_xy(e)[1] // max(1, int(row_h * 2)) for e in entries}
    confidence = min(0.95, 0.4 + 0.15 * len(entries) + (0.1 if len(rows) < len(entries) else 0.0))
    return LegendResult(has_legend=True, entries=entries,
                        bbox_xywh=(x0, y0, x1 - x0, y1 - y0),
                        confidence=confidence)


def _key_xy(e: LegendEntry) -> tuple[int, int, int, int]:
    """Swatch box, defaulting to the origin when the entry has no colour key."""
    return e.swatch_xywh if e.swatch_xywh is not None else (0, 0, 0, 0)


_LINE_KEY_MIN_ASPECT = 2.0
"""Minimum width/height for a horizontal line-sample key.

True line keys are wide thin dashes (2x and up); near-square grey
blobs are rotated-title glyph fragments or gridline bits. Short real
dashes (7x3) pass, while squarish blobs face the text/size rescue
below. Box swatches are square by design and never reach this test.
"""

_ICON_MIN_WORDS = 2
"""Substantial words a misshapen key's label needs for rescue."""

_ICON_MIN_AREA = 1000
"""Minimum key area (px) for a misshapen-key rescue.

Icon-style legend keys (mini curve thumbnails) are squarish but big
and lead full-phrase labels; glyph-fragment blobs are small and pair
with text shards. Rescue needs both signals.
"""

_COHERENCE_TOL_PX = 48.0
"""Row/column grouping tolerance for legend key coherence."""


def _drop_misshapen_line_keys(entries: list[LegendEntry]) -> list[LegendEntry]:
    """Drop squarish line-sample keys that are not rescued icons.

    Only ``line`` keys are tested; box swatches and keyless entries pass
    through untouched. Misshapen keys survive as icon-style keys: big
    (``_ICON_MIN_AREA``) with a full-phrase label (``_ICON_MIN_WORDS``
    words of 4+ letters), or big with a short-but-real label on a kept
    legend grid junction (its row and column each shared with a kept
    key): icon legends lay keys on a grid, so an aligned short-label
    key ('51: On Axis') is a real entry while unaligned blobs stay
    dropped. Glyph fragments fail the area/label gates either way.
    """
    import re as _re

    keep: list[LegendEntry] = []
    dropped: list[LegendEntry] = []
    for e in entries:
        if e.kind == "line" and e.swatch_xywh is not None:
            x, y, w, h = e.swatch_xywh
            if h <= 0 or w / max(1, h) < _LINE_KEY_MIN_ASPECT:
                words = _re.findall(r"[A-Za-z]{4,}", e.text or "")
                if len(words) < _ICON_MIN_WORDS or w * h < _ICON_MIN_AREA:
                    dropped.append(e)
                    continue
        keep.append(e)
    if dropped:
        grid = [ctr for k in keep if k.swatch_xywh is not None
                for ctr in [((k.swatch_xywh[0] + k.swatch_xywh[2] / 2.0),
                             (k.swatch_xywh[1] + k.swatch_xywh[3] / 2.0))]]
        rescued = []
        for e in dropped:
            x, y, w, h = e.swatch_xywh or (0, 0, 0, 0)
            words = _re.findall(r"[A-Za-z]{4,}", e.text or "")
            if w * h < _ICON_MIN_AREA or len(words) < 1:
                continue
            cx, cy = x + w / 2.0, y + h / 2.0
            if (any(abs(cy - gy) <= _COHERENCE_TOL_PX for _, gy in grid)
                    and any(abs(cx - gx) <= _COHERENCE_TOL_PX
                            for gx, _ in grid)):
                rescued.append(e)
        if rescued:
            keep = sorted(keep + rescued,
                          key=lambda k: entries.index(k))
    return keep


def _drop_incoherent_keys(entries: list[LegendEntry]) -> list[LegendEntry]:
    """Drop keys sharing no legend row or column with a sibling.

    Legend keys are laid out in rows (one y band) or columns (one x
    band); a key aligned with nothing — an axis-title word paired with
    a stray gridline fragment, a lone survivor of the shape filter —
    is not a legend row. Groups need two members; pairs and singletons
    cannot show incoherence and pass through.
    """
    if len(entries) < 3:
        return list(entries)
    keyed = [e for e in entries if e.swatch_xywh is not None]
    if len(keyed) < 3:
        return list(entries)

    def center(e: LegendEntry) -> tuple[float, float]:
        x, y, w, h = e.swatch_xywh or (0, 0, 0, 0)
        return (x + w / 2.0, y + h / 2.0)

    cy = sorted(center(e)[1] for e in keyed)
    cx = sorted(center(e)[0] for e in keyed)
    keep: list[LegendEntry] = []
    for e in entries:
        if e.swatch_xywh is None:
            keep.append(e)
            continue
        px, py = center(e)
        row_mates = sum(1 for v in cy if abs(v - py) <= _COHERENCE_TOL_PX)
        col_mates = sum(1 for v in cx if abs(v - px) <= _COHERENCE_TOL_PX)
        if row_mates >= 2 or col_mates >= 2:
            keep.append(e)
    return keep


def _drop_indistinct_box_rows(entries: list[LegendEntry], row_h: float) -> list[LegendEntry]:
    """Drop box-key rows whose keys are not mutually distinct colours.

    A legend row keys one colour per curve; in-plot annotations and
    watermarks pair nearby words with same-colour glyph fragments (e.g.
    repeated lavender caption text). Line samples are distinctive enough
    to keep unconditionally.
    """
    bucket = max(1, int(row_h * 2))
    rows: dict[int, list[LegendEntry]] = {}
    for e in entries:
        if e.swatch_xywh is None or e.swatch_bgr is None:
            continue  # no colour key: nothing to count or segment
        rows.setdefault(_key_xy(e)[1] // bucket, []).append(e)
    keep: list[LegendEntry] = []
    for row in rows.values():
        line = [e for e in row if e.kind != "box"]
        box = [e for e in row if e.kind == "box"]
        distinct: list[tuple[int, int, int]] = []
        for e in box:
            assert e.swatch_bgr is not None  # narrowed by the loop above
            if all(float(np.linalg.norm(np.array(e.swatch_bgr) - np.array(c))) > 60.0
                   for c in distinct):
                distinct.append(e.swatch_bgr)
        keep.extend(line)
        if len(distinct) >= 2:
            keep.extend(box)
    keep.sort(key=lambda e: (_key_xy(e)[1] // bucket, _key_xy(e)[0]))
    return keep


def _core_color(region: npt.NDArray, bg: npt.NDArray,
                ink_thresh: float = 30.0) -> tuple[int, int, int] | None:
    """Most-saturated dark-quartile ink colour of a region, else None."""
    flat = region.reshape(-1, 3).astype(float)
    ink = flat[np.max(np.abs(flat - bg), axis=1) > ink_thresh]
    if len(ink) == 0:
        return None
    return _core_of_pixels(ink)


def _core_of_pixels(ink: npt.NDArray) -> tuple[int, int, int]:
    """Most-saturated dark-quartile colour of ink pixels.

    Median, not mean: a few bright-saturated outliers (vivid fringe)
    inside the quartile would drag a mean off the paint core.
    """
    spread = ink.max(axis=1) - ink.min(axis=1)
    dark = 765.0 - ink.sum(axis=1)
    order = np.argsort(spread * 1024.0 + dark, kind="stable")
    core = ink[order[max(0, len(order) * 3 // 4):]]
    m = np.median(core, axis=0)
    return (int(m[0]), int(m[1]), int(m[2]))


def seed_fallback_styles(interior: npt.NDArray,
                         known_bgrs: Sequence[tuple[int, int, int]] = (),
                         start: int = 0, limit: int = 8) -> list:
    """Seed curve colours from long interior ink components (legend-free).

    Hue-peak discovery misses unsaturated black/gray curves, so legend-free
    plots would lose them entirely. Curves are the only long ink structures
    inside a plot: each strong-ink colour cube is tested structurally, and
    grid-mesh colours (one connected component spanning the whole panel),
    glyph fragments (few short pieces) and known colours are refused. One
    seed per surviving colour, so solid strokes and dashed curves seed
    alike. Labels stay generic (``curve_N``): with no legend, names are
    unknowable.
    """
    from graphextract.evidence import StyleSpec

    h, w = interior.shape[:2]
    bg = np.median(interior.reshape(-1, 3).astype(float), axis=0)
    # Strong ink only: anti-aliased fringe cubes would otherwise seed
    # phantom colours halfway between each curve and the background.
    # Coarse 64-cubes consolidate a thin anti-aliased stroke (whose ink
    # spreads over several 32-shades) back into one countable colour
    # while keeping distinct curve paints apart.
    fg_mask = np.max(np.abs(interior.astype(float) - bg), axis=2) > 60.0
    cubes = (interior // 64).reshape(-1, 3)[fg_mask.reshape(-1)]
    if len(cubes) == 0:
        return []
    uniq, counts = np.unique(cubes, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1]
    pending: list[tuple[float, npt.NDArray, tuple[int, int, int]]] = []
    # Low on purpose: thin (1px) strokes split their ink over many
    # shades, so no single cube holds much. The span, scatter, mesh and
    # fringe gates below do the real filtering, not this prefilter.
    min_count = max(200, int(w * h * 0.0001))
    for idx in order:
        if counts[idx] < min_count:
            break
        cube = tuple(int(v) for v in uniq[idx])
        lo = np.array(cube) * 64
        mask = (fg_mask
                & (interior[:, :, 0] >= lo[0]) & (interior[:, :, 0] < lo[0] + 64)
                & (interior[:, :, 1] >= lo[1]) & (interior[:, :, 1] < lo[1] + 64)
                & (interior[:, :, 2] >= lo[2]) & (interior[:, :, 2] < lo[2] + 64))
        ncc, _, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8) * 255, 8)
        spans = []
        meshed = False
        for i in range(1, ncc):
            x, y, cw, ch, _ = (int(v) for v in stats[i])
            if cw > 0.9 * w and ch > 0.9 * h:
                meshed = True  # grid mesh in this colour: not a curve
                break
            spans.append(max(cw, ch))
        if meshed or not spans:
            continue
        # Fragments spread evenly over the whole panel are dotted-grid
        # dots. Curve fragments (dashes, cube-split thin strokes) cluster
        # along one-dimensional paths: coarse cell occupancy tells them
        # apart. A single long stroke is never scatter, however far it
        # ranges.
        cell_w = max(1.0, w / 8.0)
        cell_h = max(1.0, h / 8.0)
        cells = set()
        for i in range(1, ncc):
            x, y, cw, ch, _ = (int(v) for v in stats[i])
            cells.add((int((x + cw / 2.0) // cell_w),
                       int((y + ch / 2.0) // cell_h)))
        scattered = (len(cells) >= 0.6 * 64 and max(spans) < 0.5 * w)
        if scattered:
            continue
        # A curve is one long stroke or many collinear dashes; glyph and
        # dot fragments are few and short.
        if max(spans) < 0.04 * max(w, h) and len(spans) < 6:
            continue
        # Core, not median: a thin stroke's cube holds mostly fringe, and
        # seeding the fringe shade would miss the paint it came from.
        color = _core_of_pixels(
            interior[mask].reshape(-1, 3).astype(float))
        # Weak ink (light grid wash) cannot segment against the
        # background; only strong strokes seed.
        strength = float(np.max(np.abs(np.array(color) - bg)))
        if strength < 90.0:
            continue
        pending.append((strength, mask, color))
    # Strongest ink first: curve cores claim their colour before
    # anti-aliased fringe cubes are tested against them.
    pending.sort(key=lambda t: -t[0])
    cands: list[tuple[int, int, int]] = []
    claimed = np.zeros((h, w), dtype=np.uint8)
    # Already-seeded discovery colours claim their ink too, so their
    # fringe cubes test as fringe rather than seeding phantoms.
    flat = interior.reshape(-1, 3).astype(float)
    for k in known_bgrs:
        kk = np.array(k, dtype=float)
        claimed |= (np.max(np.abs(flat - kk), axis=1) <= 50.0
                    ).reshape(h, w).astype(np.uint8) * 255
    # Wide halo reach: anti-aliased skirts sit several pixels off the
    # core stroke; same-paint parallels that close are unresolvable by
    # colour anyway, while crossings only ever touch briefly.
    kernel = np.ones((7, 7), np.uint8)
    for _, mask, color in pending:
        if len(cands) >= limit:
            break
        if any(float(np.linalg.norm(np.array(color) - np.array(k))) <= 50.0
               for k in list(known_bgrs) + cands):
            continue
        # Fringe halos hug an accepted stroke: most of their pixels sit
        # within a few pixels of claimed ink, while a real curve only
        # touches it at crossings.
        near = cv2.dilate(claimed, kernel)
        overlap = float((mask & (near > 0)).sum()) / max(1.0, float(mask.sum()))
        if overlap >= 0.4:
            continue
        cands.append(color)
        claimed |= mask.astype(np.uint8) * 255
    return [StyleSpec(f"curve_{start + i + 1}", f"curve_{start + i + 1}", bgr)
            for i, bgr in enumerate(cands)]


def _cells_scattered(mask: npt.NDArray, w: int, h: int) -> bool:
    """Whether mask ink is panel-wide debris rather than curve evidence.

    Evenly scattered fragments (dotted grid, compression haze: most
    coarse cells occupied with no long span) and few short pieces
    (glyph fragments) are not curves. Dash fragments and
    dotted-shredded strokes cluster along one-dimensional paths and
    pass. Size alone cannot judge: haze blobs and paint fragments
    overlap at 60-70px.
    """
    if not bool(mask.any()):
        return True
    ncc, _, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    spans = []
    for i in range(1, ncc):
        x, y, cw, ch, _ = (int(v) for v in stats[i])
        spans.append(max(cw, ch))
    if not spans:
        return True
    if max(spans) < 0.04 * max(w, h) and len(spans) < 6:
        return True
    cell_w = max(1.0, w / 8.0)
    cell_h = max(1.0, h / 8.0)
    cells = set()
    for i in range(1, ncc):
        x, y, cw, ch, _ = (int(v) for v in stats[i])
        cells.add((int((x + cw / 2.0) // cell_w),
                   int((y + ch / 2.0) // cell_h)))
    return len(cells) >= 0.6 * 64 and max(spans) < 0.5 * w


def _ink_scattered(mask: npt.NDArray, w: int, h: int) -> bool:
    """Whether mask ink is panel-wide debris rather than curve evidence.

    Same structural vocabulary as fallback seeding: a grid mesh (one
    component spanning the panel) vetoes on top of the scattered-cells
    test (``_cells_scattered``), which seed backing uses alone: a
    curve connected into the frame web still holds the curve.
    """
    if not bool(mask.any()):
        return True
    ncc, _, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    for i in range(1, ncc):
        x, y, cw, ch, _ = (int(v) for v in stats[i])
        if cw > 0.9 * w and ch > 0.9 * h:
            return True
    return _cells_scattered(mask, w, h)


_DI_LABEL_TOKENS = frozenset({"directivity", "index", "di", "dl"})
"""Label words marking a directivity curve (right-hand axis).

``dl`` covers Tesseract's common misread of the ``DI`` suffix
(``Reflections Dl``); whole-word matching keeps labels like
``Estimated In-Room`` on the left axis.
"""

_DI_MISREAD_RE = r"[o0][l1i]"
"""Two-character OCR confusions of the ``DI`` suffix (``O1``, ``Ol``).

``D`` reads as ``O``/``0`` and ``I`` as ``l``/``1``/``i``; the pattern
only counts beside a family name (``_DI_FAMILY_MARKERS``), since bare
two-letter tokens are usually word fragments.
"""

_DI_FAMILY_MARKERS = ("soundpower", "firstreflections", "earlyreflections",
                      "listeningwindow", "onaxis", "directivity", "index")
"""Family names licensing a ``DI``-suffix misread beside them."""


def _axis_for_label(label: str) -> str:
    """Right-hand axis for directivity labels, left axis otherwise."""
    # Tesseract drops inter-word spaces ('OnAxis', 'PowerDI') and reads
    # capital I as a pipe ('PowerD|'): split camel boundaries and fold
    # pipes before tokenising, so fused DI suffixes still route right.
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
                  " ", (label or "").replace("|", "I"))
    tokens = text.lower().replace("-", " ").split()
    if any(t in _DI_LABEL_TOKENS for t in tokens):
        return "y_right"
    ns = re.sub(r"[^a-z]", "", text.lower())
    if (any(m in ns for m in _DI_FAMILY_MARKERS)
            and any(re.fullmatch(_DI_MISREAD_RE, t) for t in tokens)):
        return "y_right"
    return "y_left"


def _family_words(label: str) -> frozenset[str]:
    """Curve-family words of a legend label, minus DI markers and numbers.

    ``53: First Reflections`` and ``56: First Reflections DI`` share a
    family (``{first, reflections}``); row numbers and DI suffixes
    (including OCR misreads) never distinguish families.
    """
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
                  " ", (label or "").replace("|", "I"))
    out = set()
    for t in text.lower().replace("-", " ").split():
        if not t or t in _DI_LABEL_TOKENS:
            continue
        if re.fullmatch(_DI_MISREAD_RE, t):
            continue
        if re.fullmatch(r"\d+:?", t):
            continue
        out.add(t)
    return frozenset(out)


_BAND_ROW_MIN_PX = 5
"""Paint pixels for a row to count as painted in band detection."""

_BAND_MAX_BRIDGE = 40
"""Largest painted-row gap absorbed inside one band.

Curves are vertically continuous; JPEG speckle rows between bands
never stack five paint pixels, so gaps past this split bands.
"""

_BAND_MIN_ROWS = 20
"""Minimum painted rows for a band to count."""


def _paint_two_banded(interior: npt.NDArray,
                      paint: tuple[int, int, int],
                      box_tol: int = 40) -> bool:
    """Whether a paint inks two vertically separated bands.

    Families that share paint ink it in the measured band and again in
    the offset directivity band with a void between; single-band paints
    belong to one curve. Painted-row runs (five pixels or more) split
    on gaps past ``_BAND_MAX_BRIDGE``; two runs of ``_BAND_MIN_ROWS``
    or more mean two bands.

    Achromatic impostor pixels (tick digits, text halo, grid dots)
    fall inside any dark paint's tolerance box and fake a second band
    of rows, so a chromatic paint must show chromatic ink: voters for
    a chromatic paint need channel spread too, mirroring the seed
    backing gates. Achromatic paints keep the loose box (grey washes
    are their paint).
    """
    from graphextract.evidence import _CHROMA_MIN_SPREAD

    px = interior.astype(int)
    ref = np.array(paint)
    box = np.max(np.abs(px - ref), axis=2) <= box_tol
    if float(np.max(ref) - np.min(ref)) >= _CHROMA_MIN_SPREAD:
        spread = px.max(axis=2) - px.min(axis=2)
        box = box & (spread >= _CHROMA_MIN_SPREAD)
    presence = box.sum(axis=1) >= _BAND_ROW_MIN_PX
    rows = np.nonzero(presence)[0]
    if len(rows) < 2 * _BAND_MIN_ROWS:
        return False
    gaps = np.nonzero(np.diff(rows) > _BAND_MAX_BRIDGE)[0]
    if len(gaps) == 0:
        return False
    edges = np.concatenate(([0], gaps + 1, [len(rows)]))
    runs = [rows[edges[i]:edges[i + 1]] for i in range(len(edges) - 1)]
    big = [r for r in runs if len(r) >= _BAND_MIN_ROWS]
    if len(big) < 2:
        return False
    # Same paint, not just one box: two different paints (a teal dB
    # curve upstairs, a grey-green DI curve downstairs) share a loose
    # tolerance box, so each band's median paint must agree within one
    # box radius, else the "shared" paint is two paints and the DI key
    # keeps its own colour.
    meds = []
    for r in big:
        sel = box[r[0]:r[-1] + 1, :]
        cloud = px[r[0]:r[-1] + 1, :][sel]
        if len(cloud) == 0:
            return False
        meds.append(np.median(cloud.astype(float), axis=0))
    return all(float(np.linalg.norm(a - b)) <= box_tol
               for i, a in enumerate(meds) for b in meds[i + 1:])


_COMP_MIN_PX = 600
"""Minimum largest-component pixels backing a solid-curve seed.

A spanning stroke stays connected through crossings and clutter, so
its component dwarfs glyph fragments and haze blobs; dotted-shredded
strokes fall through to the dashed fallback instead.
"""

_COMP_MIN_WIDTH_FRAC = 0.7
"""Minimum width fraction the backing component must cover."""

_COMP_MIN_ROWSPAN_FRAC = 0.15
"""Minimum height fraction the backing component must span.

Curves wander vertically; unmasked gridline remnants and frame skirts
run flat, so a row-span floor tells a spanning stroke from a long
horizontal furniture edge.
"""

_COMP_MAX_FRAME_FRAC = 0.5
"""Maximum frame-row fraction of the backing component.

Frame strokes are the largest spanning components in achromatic seed
boxes; furniture rows are measured, not assumed, and a component
sitting mostly on them is furniture, not paint.
"""

_COMP_MAX_HALO_FRAC = 0.85
"""Maximum complement-adjacent fraction of backing ink.

A fringe halo hugging a foreign curve spans and counts like paint,
but nearly all its pixels sit within a few pixels of complement ink,
while a real curve only touches it at crossings. Adjacency alone is
symmetric (the hugged curve hugs back), so the veto also requires the
hugger to be paler than the hugged (``_HALO_DARK_MARGIN``): fringe is
a blend of its core toward the background, while coincident same-shade
curves are real paint on both sides.
"""

_HALO_DARK_MARGIN = 0.1
"""Minimum darkness gap marking a complement-hugger as fringe.

Fringe blends substantially toward the background; same-shade
coincident curves sit within the margin and both back.
"""

_DASH_MIN_RUN = 15
"""Minimum longest run (px) for dashed-curve fallback backing.

Long dashes back a seed through the fallback; dotted grids (5px runs)
and glyph fragments never reach it.
"""

_DASH_MIN_ROWSPAN = 10
"""Minimum row span (px) for dashed-curve fallback backing.

Reference rulers (DI zero-lines) are flat full-width dashed lines;
data curves wander. A dashed voter mask spanning fewer rows is a
ruler, not a curve, so it never backs (its key re-enters through
adoption instead).
"""

_FRAME_ROW_INK_FRAC = 0.9
"""Row ink fraction marking measured furniture rows.

Frame strokes, margin skirts, and solid gridlines fill their rows
entirely; dense dashed curves run ~2/3 ink and dotted-grid rows ~20%,
so only rows inked nearly wall to wall are furniture.
"""


def _measure_frame_rows(ink: npt.NDArray) -> npt.NDArray:
    """Row indices dominated by furniture ink."""
    return np.nonzero(ink.mean(axis=1) > _FRAME_ROW_INK_FRAC)[0]


def _measure_frame_mask(ink: npt.NDArray) -> npt.NDArray:
    """2D furniture mask: wall-to-wall inked rows or columns.

    Frame strokes, margin skirts, and solid gridlines fill their rows
    or columns entirely in either direction; curves cross thinly both
    ways, so the same fraction separates furniture from paint.
    """
    rows = ink.mean(axis=1) > _FRAME_ROW_INK_FRAC
    cols = ink.mean(axis=0) > _FRAME_ROW_INK_FRAC
    return rows[:, None] | cols[None, :]


def _core_voters(px: npt.NDArray,
                   bg: npt.NDArray,
                   ref: npt.NDArray,
                   diff: npt.NDArray) -> npt.NDArray:
    """Box pixels at full paint strength along the seed direction.

    Same voter definition as template refinement: fringe and
    off-direction debris score away from 1.0, so only paint-strength
    ink votes. Backing counts voters, never raw box ink: a box of
    fringe and dot remnants backs nothing, and its key re-enters
    through adoption at a measured colour instead of dying on a grey
    key refinement cannot move.
    """
    denom = bg - ref
    sig = np.abs(denom) > 20.0
    if not sig.any():
        return np.zeros(diff.shape, bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.where(sig, (bg - px) / np.where(sig, denom, 1.0),
                         np.nan)
    with np.errstate(all="ignore"):
        mid = np.nanmedian(alpha, axis=2)
    return diff & (mid >= 0.85) & (mid <= 1.3)


def _seed_curve_backed(diff: npt.NDArray,
                       box: npt.NDArray,
                       ink: npt.NDArray,
                       dark: npt.NDArray,
                       frame: npt.NDArray,
                       iw: int,
                       ih: int,
                       min_own_px: int,
                       ruler_ok: bool = False) -> bool:
    """Whether seed-box ink holds a curve: solid or dashed.

    ``diff`` carries paint-strength voters (``_core_voters``), never
    raw box ink: a box of fringe and dot remnants backs nothing, and
    its key re-enters through adoption at a measured colour instead of
    dying on a grey key refinement cannot move. Whole-box scatter
    vetoes cannot tell a curve amid glyph clutter from pure debris
    (legend text inside the plot scatters every seed's box), so
    backing judges the largest component: a spanning stroke that is
    not frame furniture and not a fringe halo hugging complement ink
    backs the seed whatever else shares the box. Washed swatches hold
    only paint fragments, so the fallback backs numerous spanning
    off-frame voters with long closed dash runs that are not halo, or
    short runs when path-clustered (fine dashes and shredded strokes
    follow one-dimensional paths while dotted grids scatter). Runs
    read closed unmasked box ink, bridging the weave of thin strokes
    across box edges; and voters must spread plot-wide, since closed
    glyph words run long but concentrate in the legend box. A curve
    connected into the frame web still holds the curve, so the web
    veto never applies.
    """
    if int((diff & ~frame).sum()) < min_own_px:
        return False
    ncc, labels, stats, _ = cv2.connectedComponentsWithStats(
        diff.astype(np.uint8), connectivity=8)
    complement = ink & ~box
    comp_dil = cv2.dilate(complement.astype(np.uint8) * 255,
                          np.ones((5, 5), np.uint8)) > 0

    def _hugging_paler(ys: npt.NDArray, xs: npt.NDArray) -> bool:
        """Whether pixels hug complement ink while paler than it."""
        if float(comp_dil[ys, xs].mean()) < _COMP_MAX_HALO_FRAC:
            return False
        m = np.zeros((ih, iw), np.uint8)
        m[ys, xs] = 255
        adj = (cv2.dilate(m, np.ones((5, 5), np.uint8)) > 0) & complement
        if not adj.any():
            return False
        return (float(np.median(dark[ys, xs])) + _HALO_DARK_MARGIN
                < float(np.median(dark[adj])))

    if ncc > 1:
        i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        x, y, cw, ch, area = (int(v) for v in stats[i])
        if (area >= _COMP_MIN_PX
                and cw >= _COMP_MIN_WIDTH_FRAC * iw
                and ch >= _COMP_MIN_ROWSPAN_FRAC * ih):
            ys, xs = np.nonzero(labels == i)
            if (len(ys) > 0
                    and float(frame[ys, xs].mean()) < _COMP_MAX_FRAME_FRAC
                    and not _hugging_paler(ys, xs)):
                return True
    off = diff & ~frame
    if int(off.sum()) < min_own_px or not _spans_plot(off):
        return False
    ys, xs = np.nonzero(off)
    if int(ys.max() - ys.min() + 1) < _DASH_MIN_ROWSPAN and not ruler_ok:
        return False
    if _hugging_paler(ys, xs):
        return False
    # Dash runs on closed unmasked box ink: anti-aliased thin strokes
    # weave in and out of any fixed box, shredding solid paint into
    # short runs, so closing bridges the 1-2px weave gaps (dash gaps
    # and dot pitches stay open). Long runs back immediately; short
    # runs back only path-clustered (fine dashes and shredded strokes
    # follow one-dimensional paths while dotted grids scatter across
    # cells). Either way the voters must spread plot-wide: closed
    # glyph words run long but concentrate in the legend box.
    runs = box & ~frame
    closed = cv2.morphologyEx(runs.astype(np.uint8), cv2.MORPH_CLOSE,
                              np.ones((5, 5), np.uint8)) > 0
    ncc2, _, stats2, _ = cv2.connectedComponentsWithStats(
        closed.astype(np.uint8), connectivity=8)
    longrun = (ncc2 > 1
               and int(stats2[1:, cv2.CC_STAT_WIDTH].max()) >= _DASH_MIN_RUN)
    if not longrun and _cells_scattered(off, iw, ih):
        return False
    x10, x90 = np.percentile(xs, [10, 90])
    return (x90 - x10) >= 0.5 * iw


_SEED_MIN_INK = 0.5
"""Minimum background-relative ink fraction for seed evidence.

Paint halo inside a washed seed's box matches the seed in hue and
relative coverage yet is pale: same direction from the background,
only weaker. Absolute ink separates them — paints run 0.65+, halos
0.3-0.45 — so backing and refinement voters must carry substantial
ink. Pale pastel paints starve too and re-enter through the fallback
pool at their measured colour.
"""


def _ink_fraction(interior: npt.NDArray, bg: npt.NDArray) -> npt.NDArray:
    """Mean background-relative ink fraction per pixel, 0..1."""
    denom = max(float(np.mean(bg)), 1.0)
    return np.mean(bg - interior.astype(float), axis=2) / denom


_SPAN_MIN_FRAC = 0.15
"""Minimum width fraction seed evidence must span.

Curves cross the plot; furniture hugs the edges. A margin bar or frame
skirt inside a washed seed's box is connected, unimodal, and numerous
— every colour/structure gate passes — but concentrates in one width
bin (one bar alone also spans almost nothing), so the spread refusal
starves it while real curves, even short ones, spread far more.
"""


def _spans_plot(mask: npt.NDArray,
                frac: float = _SPAN_MIN_FRAC,
                max_bin_frac: float = 0.5,
                nbins: int = 10) -> bool:
    """Whether set pixels spread across the mask width like a curve."""
    cols = np.nonzero(mask.any(axis=0))[0]
    if len(cols) == 0:
        return False
    if (cols[-1] - cols[0] + 1) < frac * mask.shape[1]:
        return False
    counts = np.zeros(nbins, dtype=int)
    edges = np.linspace(0, mask.shape[1], nbins + 1)
    col_counts = mask.sum(axis=0)
    for b in range(nbins):
        lo, hi = int(edges[b]), int(edges[b + 1])
        counts[b] = int(col_counts[lo:hi].sum())
    total = int(counts.sum())
    return total > 0 and counts.max() / total <= max_bin_frac


def snap_legend_seeds(interior: npt.NDArray,
                      styles: list,
                      min_own_px: int = 300,
                      box_tol: int = 40,
                      snap_cap: float = 200.0,
                      exclude_mask: npt.NDArray | None = None) -> list:
    """Re-point legend seeds whose key colour has no interior ink.

    Key swatches are thin and anti-aliased; the sampled key colour can
    miss the plotted paint entirely (black key, dark-grey 1px curve),
    and the series then tracks nothing. A starved seed (fewer than
    ``min_own_px`` interior pixels near its colour) snaps to the nearest
    structurally vetted curve colour from fallback seeding, which grid
    and fringe colours never survive. Seeds with their own ink stay
    untouched; starved same-paint siblings adopt the same pool colour
    freely, while a backed sibling's paint is never adopted.
    Only substantial (``_SEED_MIN_INK``) curve ink backs a seed
    (``_seed_curve_backed``), counted unmasked: the grid mask shreds
    thin paint below the count floor, while measured frame
    rows/columns and the dash run floor already refuse furniture and
    dotted grids, so ``exclude_mask`` only guides refinement. A
    chromatic seed's backing must itself be chromatic
    (``_CHROMA_MIN_SPREAD``): achromatic grid dots and pale halo
    inside a washed seed's box are not its paint. Achromatic seeds
    skip only the chroma gate, since their paint is grey. Adoption
    keeps the key's hue family, so a hue-washed key cannot adopt a
    nearer wrong-hue pool colour; a starved key nearer a same-hue
    backed sibling than any pool colour adopts the sibling's paint
    (its key is a washed sample of that family's paint), while a
    nearer other-hue sibling means the key is its own paint and the
    key stands. Past adoption, over-claimed paints (more than one dB
    or DI key) evict excess adopted keys greyest-first to unclaimed
    pool paints; backed measurements never move. Finally, DI keys take
    a same-family twin's paint when it inks two separated bands
    (``_paint_two_banded``): the twin's paint is then shared with this
    family's directivity curve, even over the DI key's own backing,
    while a single-band twin paint leaves the key's own colour alone.
    Returns a new list; labels and ids are preserved.
    """
    from dataclasses import replace as _replace

    from graphextract.evidence import _CHROMA_MIN_SPREAD, estimate_background

    starved = []
    px = interior.astype(int)
    spread = px.max(axis=2) - px.min(axis=2)
    bg = np.array(estimate_background(interior), dtype=float)
    dark = _ink_fraction(interior, bg)
    ink = dark >= _SEED_MIN_INK
    ih, iw = interior.shape[:2]
    frame = _measure_frame_mask(ink)
    pxf = interior.astype(float)
    for s in styles:
        if not s.series_id.startswith("legend_"):
            continue
        ref = np.array(s.bgr)
        diff = (np.max(np.abs(px - ref), axis=2) <= box_tol) & ink
        if max(ref) - min(ref) >= _CHROMA_MIN_SPREAD:
            diff = diff & (spread >= _CHROMA_MIN_SPREAD)
        # Largest-component backing over unmasked paint-strength
        # voters: a spanning stroke that is not frame furniture and
        # not complement-hugging halo backs the seed whatever clutter
        # shares the box; dashed curves back through the long-run
        # fallback. Unmasked, because the grid mask shreds thin paint
        # below the count floor; wall-to-wall furniture never counts
        # (measured frame rows/columns) and dotted grids never reach
        # the dash run floor, so the mask buys nothing here.
        voters = _core_voters(pxf, bg, ref.astype(float), diff)
        # Offset-labeled keys name the reference ruler itself, so flat
        # dashed lines back them; every other key starves on a ruler
        # (its curve wanders) and re-enters through adoption.
        ruler_ok = "offset" in (s.label or "").lower()
        if _seed_curve_backed(voters, diff, ink, dark, frame, iw,
                              ih, min_own_px, ruler_ok):
            continue
        starved.append(s)
    # No early return: twin-paint adoption repoints DI keys even when
    # every key backs (a DI key can back on a same-grey reference
    # line). Adoption and eviction below no-op naturally on empty
    # starved lists and pools.
    pool = seed_fallback_styles(interior, [], limit=8) if starved else []
    spent: list[tuple[int, int, int]] = []
    for s in styles:
        if not any(s is t for t in starved):
            spent.append((tuple(int(v) for v in s.bgr), s.label or ""))
    order = sorted(
        starved,
        key=lambda s: min([float(np.linalg.norm(np.array(c.bgr) - np.array(s.bgr)))
                           for c in pool] or [snap_cap]))
    adopted: dict[int, tuple[int, int, int]] = {}
    for s in order:
        ref = np.array(s.bgr)
        # A backed sibling colour nearer the key than any pool colour
        # means the key belongs to that family's paint (washed ERDI
        # key vs backed ER curve): the key adopts the sibling's paint
        # when the hue family matches, since band fencing and the
        # same-paint swap sort out the assignment downstream. A nearer
        # other-hue sibling means the key is its own paint (dark-blue
        # ERDI key vs dark-red ER curve): adopting it would steal
        # junk, so the key colour stands. Starved siblings share
        # freely: same-paint entries adopt the same pool colour (three
        # red keys over two red curves).
        spent_arr = [np.array(k) for k, _ in spent]
        claimed_near = min(
            [float(np.linalg.norm(k - ref))
             for k in spent_arr] or [float("inf")])
        best, best_d = None, min(snap_cap, claimed_near)
        seed_chroma = max(ref) - min(ref) >= _CHROMA_MIN_SPREAD
        seed_hue = int(np.argmax(ref)) if seed_chroma else -1
        for cand in pool:
            cand_bgr = tuple(int(v) for v in cand.bgr)
            if seed_chroma and max(cand_bgr) - min(cand_bgr) < _CHROMA_MIN_SPREAD:
                continue  # chromatic keys never adopt achromatic pool ink
            if seed_chroma and int(np.argmax(np.array(cand_bgr))) != seed_hue:
                continue  # washing dulls a key but keeps its hue order
            # Achromatic keys adopt freely: dark-navy and umber paints
            # are chromatic, and a black key over one is the snap's
            # founding case.
            if any(float(np.linalg.norm(np.array(cand_bgr) - np.array(k))) <= 60.0
                   for k, _ in spent):
                continue
            d = float(np.linalg.norm(np.array(cand_bgr) - ref))
            if d < best_d:
                best, best_d = cand_bgr, d
        if best is not None:
            adopted[id(s)] = best
        elif spent_arr and claimed_near < snap_cap:
            # Nearest hue-matched backed sibling: a nearer other-hue
            # sibling (a grey reference key beside a washed blue key)
            # must not veto the match. Labelled siblings win over
            # textless ones: a key without words is a positional guess
            # (often fringe), while a labelled key names its curve.
            matched = []
            s_db = _axis_for_label(s.label or "") != "y_right"
            for (k, lab), arr in zip(spent, spent_arr):
                if s_db and _axis_for_label(lab or "") == "y_right":
                    continue  # dB keys measure their own band first and
                    # never adopt a directivity sibling's paint: the
                    # adoption would latch the DI band and starve the
                    # twin (a washed dB key starves honestly instead).
                sib_chroma = max(k) - min(k) >= _CHROMA_MIN_SPREAD
                if ((seed_chroma and sib_chroma
                     and int(np.argmax(arr)) == seed_hue)
                        or (not seed_chroma and not sib_chroma)):
                    generic = not lab or re.fullmatch(r"curve_\d+", lab)
                    matched.append((bool(generic),
                                    float(np.linalg.norm(arr - ref)), k))
            if matched:
                sib = min(matched)[2]
                if float(np.linalg.norm(np.array(sib) - ref)) < snap_cap:
                    adopted[id(s)] = tuple(int(v) for v in sib)
    # Over-claim eviction: one paint serves at most one dB key plus
    # one DI key, so wash-grey keys piling past that onto one paint
    # while pool paints stand unclaimed are mis-adoptions: grey washes
    # of different paints are indistinguishable locally (red and olive
    # keys both read grey), and only the global count tells them apart.
    # Past the first key per band (backed measurements always keep;
    # adopted keys rank by key saturation, since washing destroys hue
    # confidence), excess adopted keys move greyest-first to the
    # nearest unclaimed pool paint, distance-only: their hue order is
    # wash noise. Twins never follow: families do not always share
    # paint (Harman FR is olive while FRDI is red-brown), so each
    # twin's own colour adoption is the better signal for it. One
    # round: eviction rebalances, never chains.
    final = {id(s): tuple(adopted.get(id(s), tuple(int(v) for v in s.bgr)))
             for s in styles}
    legend = [s for s in styles if s.series_id.startswith("legend_")]
    claimed = {final[id(s)] for s in legend}
    pool_bgrs = [tuple(int(v) for v in c.bgr) for c in pool]
    unclaimed = [c for c in pool_bgrs
                 if c not in claimed
                 and not any(float(np.linalg.norm(np.array(c) - np.array(k)))
                             <= 60.0 for k, _ in spent)]
    starved_ids = {id(t) for t in starved}

    def _confidence(s) -> tuple[bool, float, float]:
        key = np.array(s.bgr, dtype=float)
        chroma = float(max(s.bgr) - min(s.bgr))
        d = float(np.linalg.norm(np.array(final[id(s)], dtype=float) - key))
        return (id(s) not in starved_ids, chroma, -d)

    by_paint: dict[tuple[int, int, int], list] = {}
    for s in legend:
        by_paint.setdefault(final[id(s)], []).append(s)
    excess: list = []
    for paint, keys in by_paint.items():
        bands: dict[str, list] = {}
        for s in keys:
            bands.setdefault(_axis_for_label(s.label or ""), []).append(s)
        for band_keys in bands.values():
            if len(band_keys) < 2:
                continue
            first = max(range(len(band_keys)),
                        key=lambda i: _confidence(band_keys[i]))
            for i, s in enumerate(band_keys):
                if i != first and id(s) in starved_ids:
                    excess.append(s)
    excess.sort(key=lambda s: (float(max(s.bgr) - min(s.bgr)),
                               id(s) in adopted))
    moved: dict[int, tuple[int, int, int]] = {}
    for s in excess:
        if id(s) in moved:
            continue
        fam = _family_words(s.label or "")
        moved_paints = {final[id(t)] for t in legend if id(t) in moved}
        joinable = []
        for p in moved_paints:
            on_p = [t for t in legend if final[id(t)] == p]
            if on_p and all(id(t) in moved
                            and _family_words(t.label or "") == fam
                            for t in on_p):
                joinable.append(p)
        cands = unclaimed + [p for p in joinable if p not in unclaimed]
        if not cands:
            continue
        key = np.array(s.bgr, dtype=float)
        target = min(cands, key=lambda c: float(
            np.linalg.norm(np.array(c, dtype=float) - key)))
        adopted[id(s)] = target
        final[id(s)] = target
        moved[id(s)] = target
        if target in unclaimed:
            unclaimed.remove(target)
    # Twin-paint adoption (DI keys only): a DI key's colour adoption is
    # a band-blind guess, but its measured twin's paint is evidence: a
    # twin paint inking two separated bands is shared with this
    # family's directivity curve, so the DI key takes it even over its
    # own backing (which may sit on a same-grey reference line), while
    # a single-band twin paint leaves the key's own colour alone
    # (families do not always share paint). dB keys never twin-adopt:
    # they measure their own band first and unfenced.
    for s in legend:
        if _axis_for_label(s.label or "") != "y_right":
            continue
        fam = _family_words(s.label or "")
        if not fam:
            continue
        # Subset, not equality: OCR drops words ('Reflections Dl' vs
        # 'Eary Reflections'), and either side may be the fragment.
        twin = next(
            (t for t in legend if t is not s
             and _family_words(t.label or "")
             and (fam <= _family_words(t.label or "")
                  or _family_words(t.label or "") <= fam)
             and _axis_for_label(t.label or "") != "y_right"),
            None)
        if twin is None:
            continue
        paint = final[id(twin)]
        if paint == final[id(s)]:
            continue
        if not _paint_two_banded(interior, paint, box_tol):
            continue
        adopted[id(s)] = paint
        final[id(s)] = paint
    out = []
    for s in styles:
        if id(s) in adopted:
            out.append(_replace(s, bgr=adopted[id(s)]))
        else:
            out.append(s)
    return out


def refine_seed_templates(
    interior: npt.NDArray,
    styles: list,
    box_tol: int = 40,
    min_core_px: int = 300,
    move_cap: float = 60.0,
    agree_dist: float = 25.0,
    agree_frac: float = 0.35,
    exclude_mask: npt.NDArray | None = None,
) -> list:
    """Re-point legend seeds at their measured paint colour.

    Key swatches are thin and anti-aliased; the sampled key colour
    routinely sits a few dozen levels off the plotted paint (a red key
    at R=214 over R=182 paint). Box masks tolerate the drift, but the
    tracker's foreground/background unmixing scores spread against the
    template, so off-template truth loses to occlusion column after
    column while a same-paint sibling survives on motion. Seeds backed
    by a solid core of near-box, high-coverage ink adopt the darker
    half's median (the stroke core; fringe outnumbers it on thin
    strokes); starved, far-moving, scattered, and mixed boxes
    (close-hue siblings sharing one tolerance box) keep the key.
    ``exclude_mask`` (grid/frame) never votes, only plot-spread core
    ink votes, and a chromatic seed's voters must be chromatic:
    achromatic dots and haze inside a washed seed's box are speckles,
    never its paint. Discovered ``curve_`` seeds already are interior
    measurements and pass through.
    """
    from dataclasses import replace as _replace

    from graphextract.evidence import _CHROMA_MIN_SPREAD, estimate_background

    if interior.ndim != 3 or interior.shape[2] != 3:
        return list(styles)
    bg = np.array(estimate_background(interior), dtype=float)
    px = interior.astype(float)
    spread = px.max(axis=2) - px.min(axis=2)
    ink = _ink_fraction(interior, bg) >= _SEED_MIN_INK
    ih, iw = interior.shape[:2]
    out = []
    for s in styles:
        if s.series_id.startswith("curve_"):
            out.append(s)
            continue
        ref = np.array(s.bgr, dtype=float)
        box = (np.max(np.abs(px - ref), axis=2) <= box_tol) & ink
        if float(ref.max() - ref.min()) >= _CHROMA_MIN_SPREAD:
            box = box & (spread >= _CHROMA_MIN_SPREAD)
        if int(box.sum()) < min_core_px:
            out.append(s)
            continue
        denom = bg - ref
        sig = np.abs(denom) > 20.0
        if not sig.any():
            out.append(s)  # seed == background: no ink to measure
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            alpha = np.where(sig, (bg - px) / np.where(sig, denom, 1.0),
                             np.nan)
        with np.errstate(all="ignore"):
            mid = np.nanmedian(alpha, axis=2)
        # Core-only voters: halo (0.6-0.8) outnumbers the stroke core
        # two to one on thin strokes and would wash the median off the
        # paint; full-strength paint scores ~1.0. Scattered debris
        # never votes; dash fragments and shredded strokes do.
        core = box & (mid >= 0.85) & (mid <= 1.3)
        if _ink_scattered(core, iw, ih):
            out.append(s)
            continue
        if exclude_mask is not None:
            core = core & (exclude_mask == 0)
        if not _spans_plot(core):
            out.append(s)  # edge-hugging furniture, not paint
            continue
        cloud = px[core]
        if len(cloud) < min_core_px:
            out.append(s)
            continue
        med = np.median(cloud, axis=0)
        agree = float((np.linalg.norm(cloud - med, axis=1) <= agree_dist).mean())
        if agree < agree_frac:
            out.append(s)  # mixed box: two paints, the key stands
            continue
        # The vote is the darker half's median: fringe outnumbers the
        # stroke core on thin strokes, and the core is the darker mode.
        dark = np.argsort(cloud.sum(axis=1), kind="stable")
        vote = np.median(cloud[dark[:max(1, len(dark) // 2)]], axis=0)
        if float(np.linalg.norm(vote - ref)) > move_cap:
            out.append(s)
            continue
        out.append(_replace(s, bgr=tuple(int(v) for v in np.round(vote))))
    return out


def styles_from_legend(result: LegendResult | list[LegendEntry]) -> list:
    """Curve count + colours from a parsed legend, as segmenter StyleSpecs."""
    from graphextract.evidence import StyleSpec

    entries = result.entries if isinstance(result, LegendResult) else result
    styles = []
    for i, e in enumerate(entries):
        if e.swatch_bgr is None:
            continue
        styles.append(StyleSpec(f"legend_{i + 1}", e.text or f"curve_{i + 1}",
                                e.swatch_bgr, key_xywh=e.swatch_xywh))
    return styles


def associate_by_color(entries: list[LegendEntry],
                       styles) -> list[LegendAssociation]:
    """Map legend entries to series via swatch colour; uncertain stays anonymous."""
    assocs = []
    for sid_idx, style in enumerate(styles):
        sid = style.series_id
        best_label, best_conf = None, 0.0
        for e in entries:
            if e.swatch_bgr is None:
                continue
            dist = float(np.linalg.norm(np.array(e.swatch_bgr) - np.array(style.bgr)))
            conf = max(0.0, 1.0 - dist / 150.0)
            if conf > best_conf:
                best_label, best_conf = e.text, conf
        if best_label is not None and best_conf >= 0.5:
            assocs.append(LegendAssociation(sid, best_label, "color", best_conf))
        else:
            assocs.append(LegendAssociation(sid, None, "none", 0.0))
    return assocs


class VLMProvider(Protocol):
    name: str
    available: bool

    def propose(self, img: npt.NDArray, context: dict) -> dict:
        """Propose {labels: {series_id: label}, units: {...}, family: str}."""
        ...


class StubVLM:
    """Deterministic stand-in for tests and offline environments."""

    name = "stub"

    def __init__(self, proposal: dict | None = None) -> None:
        self._proposal = proposal or {}
        self.available = True

    def propose(self, img: npt.NDArray, context: dict) -> dict:  # noqa: ARG002
        return dict(self._proposal)


def validate_proposal(proposal: dict, series_ids: list[str],
                      legend_texts: list[str],
                      known_units: set[str] = KNOWN_UNITS) -> list[str]:
    """Check a semantic proposal against observed evidence; errorsblock use."""
    errs: list[str] = []
    labels = proposal.get("labels", {})
    for sid, label in labels.items():
        if sid not in series_ids:
            errs.append(f"label for unknown series {sid!r}")
        if label not in legend_texts:
            errs.append(f"invented label {label!r} not present in legend")
    for axis, unit in proposal.get("units", {}).items():
        if unit not in known_units:
            errs.append(f"unknown unit {unit!r} for {axis}")
    family = proposal.get("family", "unknown")
    if family not in KNOWN_FAMILIES:
        errs.append(f"unknown family {family!r}")
    return errs


def apply_vlm_labels(assocs: list[LegendAssociation], proposal: dict,
                     series_ids: list[str], legend_texts: list[str]) -> list[str]:
    """Fill only anonymous slots from a validated VLM proposal; returns errors."""
    errs = validate_proposal(proposal, series_ids, legend_texts)
    if errs:
        return errs
    by_id = {a.series_id: a for a in assocs}
    for sid, label in proposal.get("labels", {}).items():
        slot = by_id.get(sid)
        if slot is not None and slot.label is None:
            slot.label = label
            slot.source = "vlm"
            slot.confidence = 0.5
    return []
