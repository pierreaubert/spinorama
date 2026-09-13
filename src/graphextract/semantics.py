# -*- coding: utf-8 -*-
"""Legend semantics (plan-20260810, section 6F): swatches + labels -> series.

Legend text and swatches are matched to tracked identities by colour evidence.
A VLM may *propose* chart family, units, or legend associations for unfamiliar
layouts through the VLMProvider protocol, but every proposal is validated
against OCR text and geometry before it can touch a result — generated
coordinates or labels never become measurement authority on their own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import cv2
import numpy as np
import numpy.typing as npt

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
    """Small saturated blobs (legend swatches); returns (xywh, median bgr)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = ((hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 80)).astype(np.uint8) * 255
    contours, _ = cv2.findContours(sat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        if not (4 <= w <= 60 and 4 <= h <= 60 and 25 <= area <= 3600):
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
        # Keys are short segments (high-resolution renders reach ~95px);
        # frame/grid strokes span hundreds of pixels and stay excluded.
        if not (12 <= w <= 120 and 1 <= h <= 12):
            continue
        if w / max(1, h) < 3 or cv2.contourArea(cnt) < 30:
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
    """Join collinear same-colour fragments of one dashed legend key."""
    merged: list[_Sample] = []
    for s in sorted(samples, key=lambda c: (c.xywh[1], c.xywh[0])):
        sx, sy, sw, sh = s.xywh
        hit = None
        for m in merged:
            mx, my, mw, mh = m.xywh
            same_row = abs((sy + sh / 2.0) - (my + mh / 2.0)) <= 4.0
            gap = min(abs(sx - (mx + mw)), abs(mx - (sx + sw)))
            same_color = float(np.linalg.norm(np.array(s.bgr) - np.array(m.bgr))) <= 60.0
            if same_row and gap <= 12 and same_color:
                hit = m
                break
        if hit is None:
            merged.append(s)
        else:
            mx, my, mw, mh = hit.xywh
            x0, y0 = min(mx, sx), min(my, sy)
            x1, y1 = max(mx + mw, sx + sw), max(my + mh, sy + sh)
            hit.xywh = (x0, y0, x1 - x0, y1 - y0)
    return merged


def _swatch_candidates(img: npt.NDArray) -> list[_Sample]:
    """Unified colour keys: filled box swatches plus line samples, deduped."""
    cands = [_Sample(xywh, bgr, "box") for xywh, bgr in _swatch_components(img)]
    for line in _line_samples(img):
        lx, ly, lw, lh = line.xywh
        dup = False
        for i, cand in enumerate(cands):
            cx, cy, cw, ch = cand.xywh
            # Same physical key seen by both detectors: keep the line
            # version, whose ink-only colour survives thin segments on white.
            if (lx - 2 <= cx + cw / 2.0 <= lx + lw + 2
                    and ly - 2 <= cy + ch / 2.0 <= ly + lh + 2):
                dup = True
                if lw / max(1, lh) >= 3:
                    cands[i] = line
                break
        if not dup:
            cands.append(line)
    return cands


def _word_hit_by_sample(wd, samples: list[_Sample]) -> bool:
    """True when an OCR word re-reads a colour key instead of labelling it.

    OCR frequently misreads a coloured line sample itself as short text
    (e.g. 'mum'/'eee' on a 57x5 segment). Such words are the key, not a
    label, and must not become legend entries. Either overlap direction
    counts: a tall misread box ('——' with padded height) covers little of
    its own area yet blankets most of the key, while a tight box covers
    most of itself. Real labels sit beside their key, overlapping neither.
    """
    wx, wy, ww, wh = wd.x, wd.y, wd.w, wd.h
    if ww <= 0 or wh <= 0:
        return False
    for s in samples:
        sx, sy, sw, sh = s.xywh
        inter = (max(0, min(wx + ww, sx + sw) - max(wx, sx))
                 * max(0, min(wy + wh, sy + sh) - max(wy, sy)))
        if inter > 0.5 * ww * wh or (sw > 0 and sh > 0 and inter > 0.5 * sw * sh):
            return True
    return False


def _nearest_sample(wd, samples: list[_Sample]) -> _Sample | None:
    """Nearest row-compatible colour key, reading left to right.

    Legend keys precede their labels (``— label``), so a word belongs to the
    nearest key on its left; only when no left key fits is a key on the
    right considered. This keeps the second word of a wide label ('2nd'
    + 'Harmonic') on its own key instead of drifting to the next item.
    Words past the ±80px window (later words of wide high-resolution
    labels) fall back to the nearest row-compatible key on their left.
    """
    cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
    vgate = max(12.0, float(max(wd.h, 1)))
    compat = []
    for s in samples:
        sx, sy, sw, sh = s.xywh
        scx, scy = sx + sw / 2.0, sy + sh / 2.0
        if scx < wd.x - 80 or scx > wd.x + wd.w + 80:
            continue
        dy = abs(scy - cy)
        if dy > vgate:
            continue
        compat.append((abs(scx - cx) + 2.0 * dy, scx <= cx, s))
    if compat:
        left = [c for c in compat if c[1]]
        pool = left if left else compat
        return min(pool, key=lambda c: c[0])[2]
    far = []
    for s in samples:
        sx, sy, sw, sh = s.xywh
        scx, scy = sx + sw / 2.0, sy + sh / 2.0
        if scx > cx or abs(scy - cy) > vgate:
            continue
        far.append((cx - scx, s))
    return min(far)[1] if far else None


def extract_legend_entries(img: npt.NDArray, words,
                           band_frac: float = 0.14) -> list[LegendEntry]:
    """Pair top-band OCR words with nearby colour keys (boxes and lines)."""
    h, _ = img.shape[:2]
    samples = _swatch_candidates(img)
    entries = []
    for wd in words:
        if wd.y > band_frac * h or len(wd.text.strip()) < 2:
            continue
        if _word_hit_by_sample(wd, samples):
            continue
        best = _nearest_sample(wd, samples)
        entries.append(LegendEntry(
            text=wd.text.strip(), word_xywh=(wd.x, wd.y, wd.w, wd.h),
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
    samples = _swatch_candidates(img)
    rx, ry, rw, rh = 0, 0, w, h
    if roi_xywh is not None:
        rx, ry, rw, rh = roi_xywh
        samples = [s for s in samples
                   if rx <= s.xywh[0] + s.xywh[2] / 2.0 <= rx + rw
                   and ry <= s.xywh[1] + s.xywh[3] / 2.0 <= ry + rh]
    grouped: dict[int, list] = {}
    for wd in words:
        if len(wd.text.strip()) < 2:
            continue
        if roi_xywh is not None and not (rx <= wd.x <= rx + rw and ry <= wd.y <= ry + rh):
            continue
        if _word_hit_by_sample(wd, samples):
            continue
        best = _nearest_sample(wd, samples)
        if best is None:
            continue
        grouped.setdefault(id(best), []).append(wd)
    if not grouped:
        return LegendResult(has_legend=False)
    by_id = {id(s): s for s in samples}
    # A line key without label words still counts when it sits on a
    # labelled legend row (its label likely failed OCR); isolated keys, and
    # box keys (whose false positives cluster on watermark rows), do not.
    labelled_rows = [np.mean([wd.y + wd.h / 2.0 for wd in wds]) for wds in grouped.values()]
    row_h = float(np.median([wd.h for wds in grouped.values() for wd in wds]))
    for s in samples:
        if id(s) in grouped or s.kind != "line":
            continue
        scy = s.xywh[1] + s.xywh[3] / 2.0
        if any(abs(scy - row) <= 1.5 * max(row_h, 1) for row in labelled_rows):
            grouped[id(s)] = []
    entries = []
    for sid, wds in grouped.items():
        s = by_id[sid]
        wds = sorted(wds, key=lambda d: d.x)
        text = " ".join(d.text.strip() for d in wds)
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
