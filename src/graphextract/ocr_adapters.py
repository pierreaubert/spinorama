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
                    img_w: int, img_h: int, snap_px: int = 12) -> TickAssociation:
    """Snap parsed tick words to the nearest grid line; drop the rest honestly."""
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
            if dist > snap_px:
                assoc.unmatched.append(f"{wd.text!r}: {dist:.0f}px from nearest grid line")
                continue
            conf = max(0.1, wd.confidence * (1.0 - dist / snap_px))
            assoc.x.append(TickAnchor(float(gx), value, conf, "ocr"))
        else:
            # Y-axis label: left strip feeds y_left, right strip y_right,
            # position from horizontal grid in both cases.
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


_PAREN_UNIT = re.compile(r"\(\s*(khz|hz|ms|s|db|%)\s*\)", re.IGNORECASE)


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


def infer_axis_spec(words: list[OCRWord]) -> tuple[ScaleType | None, str, str]:
    """Majority-vote scale/unit from parsed label kinds; None scale = undecided."""
    kinds: list[str] = []
    for wd in words:
        parsed = parse_tick_label(wd.text)
        if parsed is not None:
            kinds.append(parsed[1])
    if not kinds:
        return _paren_spec(words)
    x_kinds = [k for k in kinds if k in ("freq", "time")]
    if x_kinds:
        top = max(set(x_kinds), key=x_kinds.count)
        return (ScaleType.LOG10, "Hz", "dB") if top == "freq" else (ScaleType.LINEAR, "s", "")
    y_kinds = [k for k in kinds if k in ("percent", "db")]
    if y_kinds:
        top = max(set(y_kinds), key=y_kinds.count)
        return None, "", ("%" if top == "percent" else "dB")
    return _paren_spec(words)


def anchors_from_ocr(words: list[OCRWord], interior: npt.NDArray,
                     source: str = "ocr_unverified") -> tuple[AxisAnchors, list[str]]:
    """Build AxisAnchors from OCR words + grid geometry (crop-local pixels)."""
    h, w = interior.shape[:2]
    grid_xs, grid_ys = detect_grid_lines(interior)
    assoc = associate_ticks(words, grid_xs, grid_ys, w, h)
    x_scale, x_unit, y_unit = infer_axis_spec(words)
    return (AxisAnchors(x=assoc.x, y_left=assoc.y_left, y_right=assoc.y_right,
                        x_scale=x_scale,
                        x_unit=x_unit, y_unit=y_unit or "dB", source=source),
            assoc.unmatched)


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
    ix, iy, _iw, _ih = panel.interior_xywh
    ex, ey, ew, eh = panel.envelope_xywh
    mx = max(margin_min_px, int(margin_frac * ew))
    my = max(margin_min_px, int(margin_frac * eh))
    local = []
    for wd in words:
        cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
        if ex - mx <= cx <= ex + ew + mx and ey - my <= cy <= ey + eh + my:
            local.append(OCRWord(wd.text, wd.x - ix, wd.y - iy, wd.w, wd.h, wd.confidence))
    anchors, _unmatched = anchors_from_ocr(local, interior, source)
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
        anchors, _ = anchors_from_ocr(words, interior, source)
        return anchors
    return provider
