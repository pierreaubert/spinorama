# -*- coding: utf-8 -*-
"""OCR/tick adapters: word boxes -> grid-snapped tick anchors -> AxisAnchors.

OCR reads text regions; tick *positions* come from grid/frame geometry, never
from text-box centers. Unreadable or unassociable scales yield empty anchors
(review requirement downstream), never guessed values. Tesseract is optional:
when absent the provider reports ``ocr_unavailable`` instead of failing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import cv2
import numpy.typing as npt

from graphextract.calibration import ScaleType, detect_grid_lines, parse_tick_label
from graphextract.pipeline import AxisAnchors
from graphextract.schema import TickAnchor


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
    unmatched: list[str] = field(default_factory=list)


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
            # Y-axis label: lives in the left strip, position from horizontal grid.
            if cx > 0.3 * img_w:
                assoc.unmatched.append(f"{wd.text!r}: y-like label outside left strip")
                continue
            if not grid_ys:
                assoc.unmatched.append(f"{wd.text!r}: no horizontal grid to snap to")
                continue
            gy = min(grid_ys, key=lambda g: abs(g - cy))
            dist = abs(gy - cy)
            if dist > snap_px:
                assoc.unmatched.append(f"{wd.text!r}: {dist:.0f}px from nearest grid line")
                continue
            conf = max(0.1, wd.confidence * (1.0 - dist / snap_px))
            assoc.y_left.append(TickAnchor(float(gy), value, conf, "ocr"))
    return assoc


def infer_axis_spec(words: list[OCRWord]) -> tuple[ScaleType | None, str, str]:
    """Majority-vote scale/unit from parsed label kinds; None scale = undecided."""
    kinds: list[str] = []
    for wd in words:
        parsed = parse_tick_label(wd.text)
        if parsed is not None:
            kinds.append(parsed[1])
    if not kinds:
        return None, "", ""
    x_kinds = [k for k in kinds if k in ("freq", "time")]
    if x_kinds:
        top = max(set(x_kinds), key=x_kinds.count)
        return (ScaleType.LOG10, "Hz", "dB") if top == "freq" else (ScaleType.LINEAR, "s", "")
    y_kinds = [k for k in kinds if k in ("percent", "db")]
    if y_kinds:
        top = max(set(y_kinds), key=y_kinds.count)
        return None, "", ("%" if top == "percent" else "dB")
    return None, "", ""


def anchors_from_ocr(words: list[OCRWord], interior: npt.NDArray,
                     source: str = "ocr_unverified") -> tuple[AxisAnchors, list[str]]:
    """Build AxisAnchors from OCR words + grid geometry (crop-local pixels)."""
    h, w = interior.shape[:2]
    grid_xs, grid_ys = detect_grid_lines(interior)
    assoc = associate_ticks(words, grid_xs, grid_ys, w, h)
    x_scale, x_unit, y_unit = infer_axis_spec(words)
    return (AxisAnchors(x=assoc.x, y_left=assoc.y_left, x_scale=x_scale,
                        x_unit=x_unit, y_unit=y_unit or "dB", source=source),
            assoc.unmatched)


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
