# -*- coding: utf-8 -*-
"""OCR/tick adapters: word boxes -> grid-snapped tick anchors -> AxisAnchors.

OCR reads text regions; tick *positions* come from grid/frame geometry, never
from text-box centers. Unreadable or unassociable scales yield empty anchors
(review requirement downstream), never guessed values. Tesseract is optional:
when absent the provider reports ``ocr_unavailable`` instead of failing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, Sequence

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.calibration import ScaleType, detect_grid_lines, parse_tick_label
from graphextract.pipeline import AxisAnchors
from graphextract.schema import PanelGeometry, TickAnchor


@dataclass
class OCRWord:
    text: str
    x: int
    y: int
    w: int
    h: int
    confidence: float = 1.0


class OCRProvider(Protocol):
    name: str
    available: bool

    def read_words(self, gray: npt.NDArray) -> list[OCRWord]:
        ...


class OCRError(Exception):
    """OCR backend missing or failed; caller must treat scales as unreadable."""


class TesseractOCR:
    """pytesseract backend; ``available`` is False when not installed."""

    name = "tesseract"

    def __init__(self) -> None:
        try:
            import pytesseract  # noqa: F401
            self.available = True
        except ImportError:
            self.available = False

    def read_words(self, gray: npt.NDArray) -> list[OCRWord]:
        if not self.available:
            raise OCRError("pytesseract is not installed; tick labels are unreadable")
        import pytesseract

        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        words: list[OCRWord] = []
        for i, text in enumerate(data["text"]):
            if text and text.strip():
                try:
                    conf = float(data["conf"][i])
                except (ValueError, TypeError):
                    conf = 0.0
                words.append(OCRWord(text.strip(), int(data["left"][i]), int(data["top"][i]),
                                     int(data["width"][i]), int(data["height"][i]), conf / 100.0))
        return words


class StubOCR:
    """Deterministic word source for tests and OCR-free environments."""

    name = "stub"

    def __init__(self, words: list[OCRWord] | None = None) -> None:
        self._words = list(words or [])
        self.available = True

    def read_words(self, gray: npt.NDArray) -> list[OCRWord]:  # noqa: ARG002
        return list(self._words)


@dataclass
class TickAssociation:
    x: list[TickAnchor] = field(default_factory=list)
    y_left: list[TickAnchor] = field(default_factory=list)
    y_right: list[TickAnchor] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)


def _snap_y(word: OCRWord, value: float, grid_ys: list[int], img_w: int,
            snap_px: int) -> TickAnchor | None:
    """Y association for one word; None when it cannot be a y tick."""
    cx, cy = word.x + word.w / 2.0, word.y + word.h / 2.0
    if cx > 0.3 * img_w or not grid_ys:
        return None
    gy = min(grid_ys, key=lambda g: abs(g - cy))
    if abs(gy - cy) > snap_px:
        return None
    conf = max(0.1, word.confidence * (1.0 - abs(gy - cy) / snap_px))
    return TickAnchor(float(gy), value, conf, "ocr")


def _snap_y_right(word: OCRWord, value: float, grid_ys: list[int], img_w: int,
                  snap_px: int) -> TickAnchor | None:
    """Right-strip mirror of ``_snap_y`` for second-y-axis ticks."""
    cx, cy = word.x + word.w / 2.0, word.y + word.h / 2.0
    if cx < 0.7 * img_w or not grid_ys:
        return None
    gy = min(grid_ys, key=lambda g: abs(g - cy))
    if abs(gy - cy) > snap_px:
        return None
    conf = max(0.1, word.confidence * (1.0 - abs(gy - cy) / snap_px))
    return TickAnchor(float(gy), value, conf, "ocr")


def associate_ticks(words: list[OCRWord], grid_xs: list[int], grid_ys: list[int],
                    img_w: int, img_h: int, snap_px: int = 12,
                    snap_x_px: int | None = None) -> TickAssociation:
    """Snap parsed tick words to the nearest grid line; drop the rest honestly.

    X labels use ``snap_x_px`` (default ``snap_px``): multi-digit labels
    ('10000') centre far from their grid line and Hough verticals carry a
    half-stroke bias, while x labels stay sparse enough that a wide gate
    cannot misfire; y ticks stay tight because adjacent ticks sit ~60px
    apart.
    """
    snap_x = snap_px if snap_x_px is None else snap_x_px
    assoc = TickAssociation()
    for wd in words:
        parsed = parse_tick_label(wd.text)
        if parsed is None:
            assoc.unmatched.append(f"{wd.text!r}: unparseable")
            continue
        value, kind = parsed
        cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
        if kind in ("freq", "time") or (kind == "linear" and cy > 0.8 * img_h):
            # X-axis label: lives in the bottom strip, position from vertical grid.
            if cy < 0.65 * img_h:
                assoc.unmatched.append(f"{wd.text!r}: x-like label outside bottom strip")
                continue
            if kind == "linear" and cx <= 0.3 * img_w:
                # The bottom y tick shares the bottom strip; its row decides.
                hit = _snap_y(wd, value, grid_ys, img_w, snap_px)
                if hit is not None:
                    assoc.y_left.append(hit)
                    continue
            if not grid_xs:
                assoc.unmatched.append(f"{wd.text!r}: no vertical grid to snap to")
                continue
            gx = min(grid_xs, key=lambda g: abs(g - cx))
            dist = abs(gx - cx)
            if dist > snap_x:
                assoc.unmatched.append(f"{wd.text!r}: {dist:.0f}px from nearest grid line")
                continue
            conf = max(0.1, wd.confidence * (1.0 - dist / snap_x))
            assoc.x.append(TickAnchor(float(gx), value, conf, "ocr"))
        else:
            # Y-axis label: left strip feeds y_left, right strip y_right,
            # position from horizontal grid in both cases. Tick labels
            # centre on their gridline (inside the plot); a numeric word
            # floating above/below the frame is legend or caption ink, not
            # a tick, and must never anchor the fit.
            if cy < 0 or cy > img_h:
                assoc.unmatched.append(f"{wd.text!r}: y-like label outside plot vertical span")
                continue
            if cx > 0.7 * img_w:
                hit = _snap_y_right(wd, value, grid_ys, img_w, snap_px)
                if hit is None:
                    if not grid_ys:
                        assoc.unmatched.append(f"{wd.text!r}: no horizontal grid to snap to")
                    else:
                        assoc.unmatched.append(f"{wd.text!r}: far from nearest grid line")
                    continue
                assoc.y_right.append(hit)
                continue
            hit = _snap_y(wd, value, grid_ys, img_w, snap_px)
            if hit is None:
                if cx > 0.3 * img_w:
                    assoc.unmatched.append(f"{wd.text!r}: y-like label outside y strips")
                elif not grid_ys:
                    assoc.unmatched.append(f"{wd.text!r}: no horizontal grid to snap to")
                else:
                    assoc.unmatched.append(f"{wd.text!r}: far from nearest grid line")
                continue
            assoc.y_left.append(hit)
    return assoc


_PAREN_UNIT = re.compile(r"[\(\[]\s*(khz|hz|ms|s|db|%)\s*[\)\]]", re.IGNORECASE)


def _paren_spec(words: Sequence[OCRWord]) -> tuple[ScaleType | None, str, str]:
    """Axis-title units like ``Frequency (Hz)``; empty when none observed.

    Only fills sides the tick-label kinds left undecided: frequency/time
    parentheticals speak for the x axis, dB/percent for y. Bare tick numbers
    (``20`` … ``20000``) carry no kind, so this is what names the log axis.
    """
    x_scale: ScaleType | None = None
    x_unit, y_unit = "", ""
    for wd in words:
        match = _PAREN_UNIT.search(wd.text)
        if not match:
            continue
        token = match.group(1).lower()
        if token in ("hz", "khz") and not x_unit:
            x_scale, x_unit = ScaleType.LOG10, "Hz"
        elif token in ("ms", "s") and not x_unit:
            x_scale, x_unit = ScaleType.LINEAR, "s"
        elif token == "db" and not y_unit:
            y_unit = "dB"
        elif token == "%" and not y_unit:
            y_unit = "%"
    return x_scale, x_unit, y_unit


def _title_spec(words: Sequence[OCRWord]) -> tuple[ScaleType | None, str]:
    """Axis-title units split across words, e.g. ``Frequency / Hz``.

    Parenthesised titles (``Frequency (Hz)``) are covered by
    ``_paren_spec``; real charts often render the unit as separate words,
    leaving bare tick numbers ('100', '1000') that carry no kind. The
    title words name the scale the ticks cannot.
    """
    tokens = {wd.text.strip().lower() for wd in words}
    if "frequency" in tokens and ("hz" in tokens or "khz" in tokens):
        return ScaleType.LOG10, "Hz"
    return None, ""


def infer_axis_spec(words: list[OCRWord]) -> tuple[ScaleType | None, str, str]:
    """Majority-vote scale/unit from parsed label kinds; None scale = undecided."""
    kinds: list[str] = []
    for wd in words:
        parsed = parse_tick_label(wd.text)
        if parsed is not None:
            kinds.append(parsed[1])
    if not kinds:
        scale, x_unit, y_unit = _paren_spec(words)
        if scale is None and not x_unit:
            scale, x_unit = _title_spec(words)
        return scale, x_unit, y_unit
    x_kinds = [k for k in kinds if k in ("freq", "time")]
    if x_kinds:
        top = max(set(x_kinds), key=x_kinds.count)
        return (ScaleType.LOG10, "Hz", "dB") if top == "freq" else (ScaleType.LINEAR, "s", "")
    y_kinds = [k for k in kinds if k in ("percent", "db")]
    if y_kinds:
        top = max(set(y_kinds), key=y_kinds.count)
        return None, "", ("%" if top == "percent" else "dB")
    scale, x_unit, y_unit = _paren_spec(words)
    if scale is None and not x_unit:
        scale, x_unit = _title_spec(words)
    return scale, x_unit, y_unit


def _union_lines(grid: list[int], extra: Sequence[int], gap: int = 4) -> list[int]:
    """Merge frame-tick positions into grid lines, deduplicating feet."""
    out = list(grid)
    for x in extra:
        if not any(abs(x - g) <= gap for g in out):
            out.append(int(x))
    return sorted(out)


def _restore_decimal_dots(gray: npt.NDArray,
                          words: Sequence[OCRWord]) -> list[OCRWord]:
    """Graft a dropped decimal dot back onto integer tick words.

    Faint decimal dots ('80.0') vanish under Tesseract's binarisation,
    leaving a 10x tick value that no fit can use. When an integer word of
    three or more digits ending in '0' has a dot-sized ink blob in its
    cell, the dot is restored before the last digit. Reads without the
    blob ('100', '20000') pass through untouched, and a wrongly grafted
    word breaks rank with the tick pitch, so the robust fit rejects it
    as an outlier rather than following it.
    """
    out = []
    for wd in words:
        # Margin reads carry whitelist grit ('800-'); the dot check runs
        # on the digits.
        text = wd.text.strip().rstrip("-+")
        if not (len(text) >= 3 and text.isdigit() and text.endswith("0")):
            out.append(wd)
            continue
        h_img, w_img = gray.shape[:2]
        # The dot sits right of Tesseract's tight digit box; pad the cell
        # so the blob is inside the search.
        x0, y0 = max(0, wd.x - 2), max(0, wd.y - 2)
        x1 = min(w_img, wd.x + wd.w + max(6, wd.w // 2))
        y1 = min(h_img, wd.y + wd.h + 2)
        if x1 - x0 < 6 or y1 - y0 < 6:
            out.append(wd)
            continue
        cell = gray[y0:y1, x0:x1]
        # Two binarisations: a light one separates the dot from its
        # digits, a darker one keeps faint dots; digits merge away at
        # the darker level, so the check runs on both.
        dotted = False
        for thresh in (180, 200):
            ink = ((cell < thresh).astype(np.uint8)) * 255
            ncc, _, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
            for i in range(1, ncc):
                cx, cy, cw, ch, area = (int(v) for v in stats[i])
                if not (3 <= area <= 80):
                    continue
                if ch > 0.5 * cell.shape[0] or cw > 0.5 * cell.shape[1]:
                    continue  # digit stroke, not a dot
                if max(cw, ch) > 3.5 * max(1, min(cw, ch)):
                    continue  # gridline fragment, not a dot
                if cx + cw / 2.0 < 0.3 * cell.shape[1]:
                    continue  # leading speck, decimals never lead
                if cy + ch / 2.0 < 0.4 * cell.shape[0]:
                    continue  # ascender speck, dots sit on the baseline
                dotted = True
                break
            if dotted:
                break
        if dotted:
            out.append(OCRWord(text[:-1] + "." + text[-1:], wd.x, wd.y,
                               wd.w, wd.h, wd.confidence))
        else:
            out.append(wd)
    return out


def anchors_from_ocr(words: list[OCRWord], interior: npt.NDArray,
                     source: str = "ocr_unverified",
                     extra_xs: Sequence[int] = (),
                     extra_ys: Sequence[int] = ()) -> tuple[AxisAnchors, list[str]]:
    """Build AxisAnchors from OCR words + grid geometry (crop-local pixels).

    ``extra_xs``/``extra_ys`` are frame-tick positions (gridless charts):
    they union with the detected grid lines as equivalent snap targets.
    """
    h, w = interior.shape[:2]
    grid_xs, grid_ys = detect_grid_lines(interior)
    grid_xs = _union_lines(grid_xs, extra_xs)
    grid_ys = _union_lines(grid_ys, extra_ys)
    snap_x = max(12, round(0.03 * w))
    assoc = associate_ticks(words, grid_xs, grid_ys, w, h, snap_x_px=snap_x)
    # Identical (pixel, value) anchors are one tick read twice (raw plus
    # thresholded strip variants); collapse them so re-reads never inflate
    # inlier counts downstream. Conflicting values on one row stay: the
    # robust fit's majority decides between a misread and the truth.
    for key in ("x", "y_left", "y_right"):
        seen: set[tuple[float, float]] = set()
        uniq = []
        for a in getattr(assoc, key):
            if (a.pixel, a.value) not in seen:
                seen.add((a.pixel, a.value))
                uniq.append(a)
        setattr(assoc, key, uniq)
    x_scale, x_unit, y_unit = infer_axis_spec(words)
    return (AxisAnchors(x=assoc.x, y_left=assoc.y_left, y_right=assoc.y_right,
                        x_scale=x_scale,
                        x_unit=x_unit, y_unit=y_unit or "dB", source=source),
            assoc.unmatched)


def _localize_words(
    words: Sequence[OCRWord],
    panel: PanelGeometry,
    margin_frac: float = 0.10,
    margin_min_px: int = 60,
) -> list[OCRWord]:
    """Full-image words near the panel, shifted to interior-local coords.

    Tick labels live in the margins *outside* the plot frame; words from
    neighbouring panels fall outside the margin and are ignored. A digit
    word centred inside the plot is a legend fragment or curve label
    ('7', '20'), never a tick, and is excluded before it can snap to a
    gridline as a phantom anchor.
    """
    ix, iy, iw, ih = panel.interior_xywh
    ex, ey, ew, eh = panel.envelope_xywh
    mx = max(margin_min_px, int(margin_frac * ew))
    my = max(margin_min_px, int(margin_frac * eh))
    local = []
    for wd in words:
        cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
        if ex - mx <= cx <= ex + ew + mx and ey - my <= cy <= ey + eh + my:
            if ix + 4 <= cx <= ix + iw - 4 and iy + 4 <= cy <= iy + ih - 4:
                continue
            local.append(OCRWord(wd.text, wd.x - ix, wd.y - iy, wd.w, wd.h, wd.confidence))
    return local


def panel_anchors_from_words(
    words: Sequence[OCRWord],
    panel: PanelGeometry,
    interior: npt.NDArray,
    source: str = "ocr_unverified",
    margin_frac: float = 0.10,
    margin_min_px: int = 60,
) -> AxisAnchors:
    """Tick anchors for one panel from full-image OCR words (image-global).

    Tick labels live in the margins *outside* the plot frame, so an
    interior-only read can never see them. Words near the panel envelope
    (tick labels, axis titles) are shifted into interior-local coordinates
    and run through the usual grid-snapping association; words from
    neighbouring panels fall outside the margin and are ignored. Position
    still comes from grid geometry, never from text-box centres.
    """
    local = _localize_words(words, panel, margin_frac, margin_min_px)
    anchors, _unmatched = anchors_from_ocr(local, interior, source)
    return anchors


_TICK_WHITELIST = "0123456789.,kKmM+-"


def _offset_words(words: list[OCRWord], ox: int, oy: int) -> list[OCRWord]:
    return [OCRWord(w.text, w.x + ox, w.y + oy, w.w, w.h, w.confidence) for w in words]


def _dedup_words(words: list[OCRWord], tol: int = 10) -> list[OCRWord]:
    """Collapse repeated reads of one label, keeping higher confidence.

    Same text at the same spot dedups exactly; several readings of one
    decade label (``104``, ``10``, ``10+``) collapse by prefix, keeping the
    longest, so a bare ``10`` duplicate cannot wedge between folded
    decades and break pitch-even triples downstream. Prefix collapse only
    applies within ``10``-family texts, never to genuine labels.
    """
    kept: list[OCRWord] = []
    for wd in sorted(words, key=lambda w: -w.confidence):
        cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
        if any(k.text == wd.text
               and abs(k.x + k.w / 2.0 - cx) <= tol
               and abs(k.y + k.h / 2.0 - cy) <= tol for k in kept):
            continue
        kept.append(wd)
    out: list[OCRWord] = []
    for wd in kept:
        cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
        rival = None
        for k in out:
            if (abs(k.x + k.w / 2.0 - cx) > tol
                    or abs(k.y + k.h / 2.0 - cy) > tol):
                continue
            a, b = k.text.strip(), wd.text.strip()
            if not (a.startswith("10") and b.startswith("10")):
                continue
            if len(a) == len(b) or not (a.startswith(b) or b.startswith(a)):
                continue
            longer = a if len(a) > len(b) else b
            if parse_tick_label(longer) is None:
                # Junk suffix ('10eee') never evicts a parsable read.
                continue
            rival = k
            break
        if rival is None:
            out.append(wd)
        elif len(wd.text.strip()) > len(rival.text.strip()):
            out.remove(rival)
            out.append(wd)
    return out


def read_margin_ticks(strip_gray: npt.NDArray) -> list[OCRWord]:
    """Digit-focused re-read of one axis-margin strip (strip-local coords).

    Full-image OCR misses small faint tick labels; an upscaled
    digit-whitelist read recovers them. Both the raw strip and a hard
    thresholded variant are read (faint grey digits vanish under
    Tesseract's internal binarisation), wide strips are tiled, and
    overlapping reads deduped. Empty when Tesseract is unavailable.
    """
    try:
        import pytesseract
    except ImportError:
        return []
    img = np.asarray(strip_gray)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]
    if h < 8 or w < 8:
        return []
    variants = [img, ((img < 180).astype(np.uint8) * 255).astype(np.uint8),
                ((img < 200).astype(np.uint8) * 255).astype(np.uint8)]
    windows = [(0, w)] if w <= 700 else [(x0, min(w, x0 + 650))
                                         for x0 in range(0, w, 450)]
    out: list[OCRWord] = []
    for variant in variants:
        for x0, x1 in windows:
            tile = variant[:, x0:x1]
            big = cv2.resize(tile, None, fx=3.0, fy=3.0,
                             interpolation=cv2.INTER_CUBIC)
            try:
                data = pytesseract.image_to_data(
                    big, config="--psm 6 -c tessedit_char_whitelist="
                               + _TICK_WHITELIST,
                    output_type=pytesseract.Output.DICT)
            except Exception:
                continue
            for i, text in enumerate(data["text"]):
                t = (text or "").strip()
                if not t or len(t) > 8:
                    continue
                try:
                    conf = max(0.0, min(1.0, float(data["conf"][i]) / 100.0))
                except (ValueError, TypeError):
                    conf = 0.0
                out.append(OCRWord(
                    t, x0 + int(data["left"][i]) // 3, int(data["top"][i]) // 3,
                    max(1, int(data["width"][i]) // 3),
                    max(1, int(data["height"][i]) // 3), conf))
    return _dedup_words(out)


def _ink_comps(crop_gray: npt.NDArray, thr: int = 180) -> list[tuple[int, int, int, int, int]]:
    """Connected ink components (x, y, w, h, area), left to right."""
    ink = (np.asarray(crop_gray) < thr).astype(np.uint8) * 255
    ncc, _, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    comps = [(int(stats[i, 0]), int(stats[i, 1]), int(stats[i, 2]),
              int(stats[i, 3]), int(stats[i, 4]))
             for i in range(1, ncc) if int(stats[i, 4]) >= 4]
    return sorted(comps, key=lambda c: (c[0], c[1]))


def _psm8_digit(gray: npt.NDArray, x0: int, y0: int, x1: int, y1: int) -> str | None:
    """Single-digit read with a confidence gate; None on any refusal."""
    try:
        import pytesseract
    except ImportError:
        return None
    h, w = gray.shape[:2]
    x0, y0 = max(0, x0 - 2), max(0, y0 - 2)
    x1, y1 = min(w, x1 + 2), min(h, y1 + 2)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    big = cv2.resize(gray[y0:y1, x0:x1], None, fx=4.0, fy=4.0,
                     interpolation=cv2.INTER_CUBIC)
    try:
        data = pytesseract.image_to_data(
            big, config="--psm 8 -c tessedit_char_whitelist=0123456789",
            output_type=pytesseract.Output.DICT)
    except Exception:
        return None
    for i, text in enumerate(data["text"]):
        t = (text or "").strip()
        if len(t) == 1 and t.isdigit():
            try:
                conf = float(data["conf"][i])
            except (ValueError, TypeError):
                conf = 0.0
            return t if conf >= 30.0 else None
    return None


def _merged_superscript_box(gray: npt.NDArray, wd: OCRWord) -> tuple[int, int, int, int] | None:
    """Image bbox of a ``10N`` word's raised last digit (None when uniform).

    OCR merges decade labels (``10³``) into one word reading ``103``; the
    exponent then floats above the baseline, smaller than the base digits.
    A genuine ``103`` sits uniformly on one baseline and is left alone.
    Split glyph arcs (a ``3`` in two components) unite: only the last
    component was re-read before, and a lone lower arc reads as ``2``.
    The digit itself is re-read downstream: the word text may misread it
    (``10²`` as ``107``).
    """
    h, w = gray.shape[:2]
    pad = 3
    x0, y0 = max(0, wd.x - pad), max(0, wd.y - pad)
    crop = gray[y0:min(h, wd.y + wd.h + pad), x0:min(w, wd.x + wd.w + pad)]
    comps = _ink_comps(crop)
    if len(comps) < 3:
        return None
    base_h = max(c[3] for c in comps)
    bases = [c[1] + c[3] for c in comps if c[3] >= 0.6 * base_h]
    if not bases:
        return None
    base_bottom = max(bases)
    cx = wd.x + wd.w / 2.0 - x0
    parts = [c for c in comps
             if c[3] <= 0.85 * base_h
             and c[1] + c[3] <= base_bottom - max(3, 0.15 * base_h)
             and c[0] + c[2] / 2.0 >= cx]
    if not parts:
        return None
    gx0 = x0 + min(c[0] for c in parts)
    gy0 = y0 + min(c[1] for c in parts)
    gx1 = x0 + max(c[0] + c[2] for c in parts)
    gy1 = y0 + max(c[1] + c[3] for c in parts)
    return (gx0, gy0, gx1, gy1)


def _read_raised_superscript(gray: npt.NDArray, wd: OCRWord) -> str | None:
    """Read the exponent beside a bare ``10`` word (``None`` when absent).

    A dropped superscript leaves readable ink: a small floating component
    right of the base, above its baseline. Single-character OCR decides the
    digit; low-confidence reads refuse rather than forge a decade.
    """
    h, w = gray.shape[:2]
    bh = max(1, wd.h)
    rx0, rx1 = max(0, wd.x + wd.w - int(0.6 * bh)), min(w, wd.x + wd.w + int(1.2 * bh))
    ry0, ry1 = max(0, wd.y - int(0.5 * bh)), min(h, wd.y + int(0.6 * bh))
    if rx1 - rx0 < 4 or ry1 - ry0 < 4:
        return None
    roi = gray[ry0:ry1, rx0:rx1]
    floor = wd.y + wd.h - max(3, 0.15 * bh) - ry0
    cands = [c for c in _ink_comps(roi)
             if 4 <= c[3] <= 0.9 * bh and c[1] > 1 and c[1] + c[3] <= floor
             and c[0] + c[2] / 2.0 >= wd.x + wd.w - 0.6 * bh - rx0]
    if not cands:
        return None
    x0 = rx0 + min(c[0] for c in cands)
    y0 = ry0 + min(c[1] for c in cands)
    x1 = rx0 + max(c[0] + c[2] for c in cands)
    y1 = ry0 + max(c[1] + c[3] for c in cands)
    return _psm8_digit(gray, x0, y0, x1, y1)


def _unambiguous_decade(text: str) -> int | None:
    """Decade exponent for pixel-verified or superscript-free readings.

    Folded ``10^N`` is pixel-verified; face ``100``/``1000`` cannot hide a
    superscript (``10^0`` is 1, not 100). Bare ``10`` and merged ``10N``
    are ambiguous and never pin a run.
    """
    t = text.strip()
    m = re.fullmatch(r"10\^([0-9]+)", t)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"1(0{2,})", t)
    if m:
        return len(m.group(1))
    return None


def _is_ambiguous_ten(text: str) -> bool:
    """Whether a reading may hide a decade superscript (bare or merged)."""
    t = text.strip()
    return bool(re.fullmatch(r"10[1-9]", t) or re.fullmatch(r"10\W*", t))


def _repair_pitch_decades(
    bottom: list[OCRWord],
    new_text: dict[int, tuple[str, tuple[int, int, int, int]]],
) -> None:
    """Pitch-implied decade for ambiguous middles (geometry backstop).

    Pixel evidence (folds) wins whenever it exists: only UNFOLDED ambiguous
    readings (``102`` face, bare ``10``) are reinterpreted, and only caught
    between two pitch-even exact-decade pins with consecutive exponents.
    Three pixel positions plus two decade values force the middle; a
    genuine ``102`` Hz tick never sits exactly at the 10^3 gridline.
    """
    def eff(wd: OCRWord) -> str:
        return new_text[id(wd)][0] if id(wd) in new_text else wd.text.strip()

    def box(wd: OCRWord) -> tuple[int, int, int, int]:
        return new_text[id(wd)][1] if id(wd) in new_text else (wd.x, wd.y, wd.w, wd.h)

    # Nearest pins on each side (not sorted triples): duplicate reads of
    # one label interleave sorted order and would wedge triples apart.
    # Same-spot words (a folded duplicate of the middle itself) never pin.
    pins = [(wd.x + wd.w / 2.0, _unambiguous_decade(eff(wd)))
            for wd in bottom if _unambiguous_decade(eff(wd)) is not None]
    for wd in bottom:
        if id(wd) in new_text or not _is_ambiguous_ten(eff(wd)):
            continue
        xb = wd.x + wd.w / 2.0
        left = [(xa, ka) for xa, ka in pins if xa < xb - 15.0]
        right = [(xc, kc) for xc, kc in pins if xc > xb + 15.0]
        if not left or not right:
            continue
        xa, ka = max(left, key=lambda p: p[0])
        xc, kc = min(right, key=lambda p: p[0])
        if kc - ka != 2:
            continue
        d1, d2 = xb - xa, xc - xb
        if abs(d1 - d2) > max(8.0, 0.03 * (d1 + d2) / 2.0):
            continue
        new_text[id(wd)] = (f"10^{ka + 1}", box(wd))


def _is_raised_suffix(base: OCRWord, dg: OCRWord) -> bool:
    """Whether a small digit word is ``base``'s split-off superscript."""
    if not re.fullmatch(r"\d{1,2}", dg.text.strip()):
        return False
    if dg.h > 0.7 * base.h:
        return False
    dcx, dcy = dg.x + dg.w / 2.0, dg.y + dg.h / 2.0
    return (base.x + base.w - 3 <= dcx <= base.x + base.w + 1.5 * base.h
            and dcy <= base.y + 0.5 * base.h)


def resolve_superscripts(
    gray_full: npt.NDArray,
    words: Sequence[OCRWord],
    img_h: int,
) -> list[OCRWord]:
    """Fold decade-superscript notations into ``10^N`` tick readings.

    Log-decade labels render as ``10`` plus a raised exponent, and OCR
    mangles them three ways: merged into one word (``103``), split into
    ``10`` plus a small raised word, or reduced to bare ``10`` with the
    exponent left as unparsed ink. Each fold is verified against pixel
    geometry (floating, smaller, right of the base) so genuine numbers
    (``102`` on one baseline) never rewrite. Only bottom-region words are
    considered: y ticks never use this notation.
    """
    gray = np.asarray(gray_full)
    bottom = [wd for wd in words if wd.y + wd.h / 2.0 > 0.6 * img_h]
    new_text: dict[int, tuple[str, tuple[int, int, int, int]]] = {}
    consumed: set[int] = set()
    for wd in bottom:
        t = wd.text.strip()
        if re.fullmatch(r"10[1-9]", t):
            box = _merged_superscript_box(gray, wd)
            digit = _psm8_digit(gray, *box) if box is not None else None
            if digit is not None:
                new_text[id(wd)] = (f"10^{digit}", (wd.x, wd.y, wd.w, wd.h))
    tens = [wd for wd in bottom
            if re.fullmatch(r"10\W*", wd.text.strip()) and id(wd) not in new_text]
    for wd in tens:
        digit = _read_raised_superscript(gray, wd)
        if digit is not None:
            new_text[id(wd)] = (f"10^{digit}", (wd.x, wd.y, wd.w, wd.h))
    smalls = [wd for wd in bottom
              if id(wd) not in new_text and id(wd) not in consumed
              and re.fullmatch(r"\d{1,2}", wd.text.strip())]
    for base in tens:
        if id(base) in new_text:
            continue
        for dg in smalls:
            if id(dg) in consumed:
                continue
            if _is_raised_suffix(base, dg):
                x0 = min(base.x, dg.x)
                y0 = min(base.y, dg.y)
                x1 = max(base.x + base.w, dg.x + dg.w)
                y1 = max(base.y + base.h, dg.y + dg.h)
                new_text[id(base)] = (f"10^{dg.text.strip()}", (x0, y0, x1 - x0, y1 - y0))
                consumed.add(id(dg))
                break
    _repair_pitch_decades(bottom, new_text)
    out: list[OCRWord] = []
    for wd in words:
        if id(wd) in consumed:
            continue
        if id(wd) in new_text:
            text, (x, y, w, h) = new_text[id(wd)]
            out.append(OCRWord(text, x, y, w, h, wd.confidence))
        else:
            out.append(wd)
    return out


def recover_margin_anchors(
    img: npt.NDArray,
    words: Sequence[OCRWord],
    panel: PanelGeometry,
    interior: npt.NDArray,
    source: str = "ocr_unverified",
) -> AxisAnchors:
    """Tick anchors with margin recovery (image-global words + full image).

    Full-image OCR misses small faint tick labels and mangles decade
    superscripts, so short panels re-read the axis margins (tight strips
    that exclude legend rows) with a digit whitelist, fold verified
    superscripts into ``10^N`` readings, and add frame-tick snap targets
    for gridless charts. Returns plain association when nothing is short.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    words2 = resolve_superscripts(gray, words, h)
    ix, iy, iw, ih = (int(v) for v in panel.interior_xywh)
    from graphextract.calibration import detect_frame_ticks
    tick_xs, tick_ys = detect_frame_ticks(gray, panel.interior_xywh)
    # Bottom strip: whole read plus one targeted cell per frame tick. A
    # tick implies its label above it, and the small cell read succeeds
    # where the wide-strip segmentation drops labels beside title words.
    y1 = min(h, iy + ih + max(80, round(0.15 * ih)))
    x0 = max(0, ix - 40)
    x1 = min(w, ix + iw + 40)
    bottom = gray[iy + ih:y1, x0:x1]
    extra = _offset_words(read_margin_ticks(bottom), x0, iy + ih)
    bh, bw = bottom.shape[:2]
    for tx in tick_xs:
        cx = tx + ix - x0
        c0, c1 = max(0, cx - 55), min(bw, cx + 55)
        if c1 - c0 < 20:
            continue
        # Top 60 rows only: labels hug the frame while titles sit deeper,
        # and title words in the same cell steal the segmentation.
        extra += _offset_words(
            read_margin_ticks(bottom[0:min(bh, 60), c0:c1]), x0 + c0, iy + ih)
    # Left strip, then right strip (evidence for a second axis; empty on
    # single-y plots). Strips always run: they only add evidence, and the
    # robust fit keeps the consistent majority.
    lx0 = max(0, ix - max(80, round(0.06 * iw)))
    ly0 = max(0, iy - 20)
    extra += _offset_words(
        read_margin_ticks(gray[ly0:min(h, iy + ih + 20), lx0:ix]), lx0, ly0)
    rx1 = min(w, ix + iw + max(80, round(0.06 * iw)))
    extra += _offset_words(
        read_margin_ticks(gray[ly0:min(h, iy + ih + 20), ix + iw:rx1]), ix + iw, ly0)
    # Strip reads need the same superscript folding as full-image words
    # (bare '10's and merged '10N's); folding is idempotent, so the
    # full-image words pass through unchanged. A second dedup collapses
    # the several reads of one label ('104', '10', '10+') into one.
    merged = _dedup_words(
        resolve_superscripts(gray, _dedup_words(list(words2) + extra), h))
    # Decimal-dot graft runs on image-global words (margin words live
    # outside the interior crop, where a crop-local cell would clip).
    merged = _restore_decimal_dots(gray, merged)
    local = _localize_words(merged, panel)
    anchors, _ = anchors_from_ocr(local, interior, source, tick_xs, tick_ys)
    return anchors


def ocr_anchor_provider(ocr: OCRProvider, source: str = "ocr_unverified"):
    """Adapt an OCRProvider to the pipeline AnchorProvider signature."""
    def provider(panel_id: str, interior: npt.NDArray) -> AxisAnchors:  # noqa: ARG001
        if not ocr.available:
            return AxisAnchors(source="ocr_unavailable")
        gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY) if interior.ndim == 3 else interior
        try:
            words = ocr.read_words(gray)
        except OCRError:
            return AxisAnchors(source="ocr_unavailable")
        words = _restore_decimal_dots(gray, words)
        anchors, _ = anchors_from_ocr(words, interior, source)
        return anchors
    return provider
