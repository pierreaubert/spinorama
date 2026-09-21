# -*- coding: utf-8 -*-
"""Legend semantics (plan-20260810, section 6F): swatches + labels -> series.

Legend text and swatches are matched to tracked identities by colour evidence.
A VLM may *propose* chart family, units, or legend associations for unfamiliar
layouts through the VLMProvider protocol, but every proposal is validated
against OCR text and geometry before it can touch a result — generated
coordinates or labels never become measurement authority on their own.
"""

from __future__ import annotations

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
    bigger). Colour comes from the darkest ink quartile: the key's dots
    are always darker than its pale frame, so the frame can never win.
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
        hits = sum(1 for bx, by, bw, bh in boxes
                   if x - 2 < bx + bw and bx - 2 < x + w
                   and y - 2 < by + bh and by - 2 < y + h)
        if hits >= 2:
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
        ink = ink[np.argsort(np.max(bg - ink, axis=1))[-max(1, len(ink) // 4):]]
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
    """Most-saturated dark-quartile colour of ink pixels."""
    spread = ink.max(axis=1) - ink.min(axis=1)
    dark = 765.0 - ink.sum(axis=1)
    order = np.argsort(spread * 1024.0 + dark, kind="stable")
    core = ink[order[max(0, len(order) * 3 // 4):]]
    m = core.mean(axis=0)
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


def snap_legend_seeds(interior: npt.NDArray,
                      styles: list,
                      min_own_px: int = 300,
                      box_tol: int = 40,
                      snap_cap: float = 175.0) -> list:
    """Re-point legend seeds whose key colour has no interior ink.

    Key swatches are thin and anti-aliased; the sampled key colour can
    miss the plotted paint entirely (black key, dark-grey 1px curve),
    and the series then tracks nothing. A starved seed (fewer than
    ``min_own_px`` interior pixels near its colour) snaps to the nearest
    structurally vetted curve colour from fallback seeding, which grid
    and fringe colours never survive. Seeds with their own ink stay
    untouched, so same-hue dB/DI pairs never collapse onto each other
    here, and an adopted pool colour is spent: a second starved seed
    cannot steal its sibling's curve. Returns a new list; labels and ids
    are preserved.
    """
    from dataclasses import replace as _replace

    starved = []
    for s in styles:
        if not s.series_id.startswith("legend_"):
            continue
        ref = np.array(s.bgr)
        diff = np.max(np.abs(interior.astype(int) - ref), axis=2) <= box_tol
        own = int(diff.sum())
        if own >= min_own_px:
            continue
        starved.append(s)
    if not starved:
        return list(styles)
    pool = seed_fallback_styles(interior, [], limit=8)
    if not pool:
        return list(styles)
    spent: list[tuple[int, int, int]] = []
    for s in styles:
        if not any(s is t for t in starved):
            spent.append(tuple(int(v) for v in s.bgr))
    order = sorted(
        starved,
        key=lambda s: min([float(np.linalg.norm(np.array(c.bgr) - np.array(s.bgr)))
                           for c in pool] or [snap_cap]))
    adopted: dict[int, tuple[int, int, int]] = {}
    for s in order:
        ref = np.array(s.bgr)
        # A claimed sibling colour nearer the key than any pool colour
        # means the key belongs to that family's paint (dark-blue ERDI
        # key vs dark-red ER curve): adopting a farther pool colour
        # would steal junk, so the key colour stands.
        claimed_near = min(
            [float(np.linalg.norm(np.array(k) - ref))
             for k in spent + list(adopted.values())] or [float("inf")])
        best, best_d = None, min(snap_cap, claimed_near)
        for cand in pool:
            cand_bgr = tuple(int(v) for v in cand.bgr)
            if any(float(np.linalg.norm(np.array(cand_bgr) - np.array(k))) <= 60.0
                   for k in spent + list(adopted.values())):
                continue
            d = float(np.linalg.norm(np.array(cand_bgr) - ref))
            if d < best_d:
                best, best_d = cand_bgr, d
        if best is not None:
            adopted[id(s)] = best
            spent.append(best)
    out = []
    for s in styles:
        if id(s) in adopted:
            out.append(_replace(s, bgr=adopted[id(s)]))
        else:
            out.append(s)
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
                                e.swatch_bgr))
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
