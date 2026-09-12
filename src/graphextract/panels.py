# -*- coding: utf-8 -*-
"""Panel detection: envelopes (with label/legend context) plus plot interiors.

Replaces the single-box contour detector (10% area minimum, side-by-side-only
fallback) with envelope/interior separation and arbitrary layouts: single,
side-by-side, stacked, 2x2, and small/inset panels. Panel boxes are proposals;
axis lines and tick evidence refine the interior later. Nothing here guesses
calibration values.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.schema import PanelGeometry


@dataclass
class _Box:
    x: int
    y: int
    w: int
    h: int

    def area(self) -> int:
        return self.w * self.h

    def iou(self, other: _Box) -> float:
        ix = max(0, min(self.x + self.w, other.x + other.w) - max(self.x, other.x))
        iy = max(0, min(self.y + self.h, other.y + other.h) - max(self.y, other.y))
        inter = ix * iy
        union = self.area() + other.area() - inter
        return inter / union if union > 0 else 0.0


def _contour_boxes(
    gray: npt.NDArray,
    img_area: int,
    min_area_ratio: float = 0.02,
    thresh: int = 240,
) -> list[_Box]:
    """Propose envelopes from non-white content contours (low area floor)."""
    _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    inv = cv2.bitwise_not(binary)
    contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[_Box] = []
    for cnt in contours:
        if cv2.contourArea(cnt) < img_area * min_area_ratio:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0.0
        if 0.3 <= aspect <= 6.0 and w > 20 and h > 20:
            boxes.append(_Box(x=x, y=y, w=w, h=h))
    return boxes


def _projection_gaps(profile: npt.NDArray, min_width: int) -> list[tuple[int, int]]:
    """Find sustained low-activity runs in a 1-D activity profile."""
    if profile.size == 0:
        return []
    cutoff = float(np.mean(profile)) * 0.35
    quiet = profile < cutoff
    gaps: list[tuple[int, int]] = []
    start: int | None = None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if i - start >= min_width:
                gaps.append((start, i))
            start = None
    if start is not None and len(profile) - start >= min_width:
        gaps.append((start, len(profile)))
    return gaps


def _split_proposals(gray: npt.NDArray) -> list[_Box]:
    """Propose 1/2/4-way splits from projection-profile gaps (both axes)."""
    h, w = gray.shape[:2]
    edges = cv2.Canny(gray, 30, 100)
    col_activity = np.sum(edges, axis=0).astype(float)
    row_activity = np.sum(edges, axis=1).astype(float)
    # Restrict cut search to the middle half so labels/margins survive.
    mid_w0, mid_w1 = w // 4, 3 * w // 4
    mid_h0, mid_h1 = h // 4, 3 * h // 4
    v_gaps = [g for g in _projection_gaps(col_activity, max(8, w // 60)) if g[0] >= mid_w0 and g[1] <= mid_w1]
    h_gaps = [g for g in _projection_gaps(row_activity, max(8, h // 60)) if g[0] >= mid_h0 and g[1] <= mid_h1]

    boxes = [_Box(0, 0, w, h)]
    if v_gaps:
        mid = (v_gaps[0][0] + v_gaps[0][1]) // 2
        boxes = [_Box(0, 0, mid, h), _Box(mid, 0, w - mid, h)]
    if h_gaps:
        mid = (h_gaps[0][0] + h_gaps[0][1]) // 2
        split: list[_Box] = []
        for b in boxes:
            split.append(_Box(b.x, b.y, b.w, mid - b.y))
            split.append(_Box(b.x, mid, b.w, b.y + b.h - mid))
        boxes = [b for b in split if b.w > 20 and b.h > 20]
    return boxes


def _apply_cuts(gray: npt.NDArray, box: _Box, x1: int, y1: int,
                cw: int, ch: int, v_cuts: list[int], h_cuts: list[int]) -> list[_Box]:
    """Build sub-boxes from cuts; every half must refine to its own frame."""
    if not v_cuts and not h_cuts:
        return [box]
    xs = [0, *sorted(v_cuts), cw]
    ys = [0, *sorted(h_cuts), ch]
    out = []
    for xa, xb in zip(xs[:-1], xs[1:]):
        for ya, yb in zip(ys[:-1], ys[1:]):
            if xb - xa > 0.15 * cw and yb - ya > 0.15 * ch:
                out.append(_Box(x1 + xa, y1 + ya, xb - xa, yb - ya))
    if len(out) <= 1:
        return [box]
    # Every half must contain its own frame; otherwise revert the split.
    for half in out:
        sub = gray[half.y:half.y + half.h, half.x:half.x + half.w]
        if sub.size == 0:
            return [box]
        _, conf = _refine_interior(sub, _Box(0, 0, half.w, half.h))
        if conf != "refined":
            return [box]
    return out


def tick_stack_cuts(words, box: _Box) -> tuple[list[int], list[int]]:
    """Gutter cuts from stacked numeric tick labels (public for review use).

    A column of y-tick labels (or row of x-tick labels) sitting between two
    frames is semantic evidence of a panel boundary that pixel gaps cannot
    show. Returns box-local cut positions.
    """
    from graphextract.calibration import parse_tick_label

    nums = []
    for wd in words:
        try:
            cx, cy = wd.x + wd.w / 2.0, wd.y + wd.h / 2.0
        except AttributeError:
            continue
        if not (box.x <= cx <= box.x + box.w and box.y <= cy <= box.y + box.h):
            continue
        if parse_tick_label(wd.text) is None:
            continue
        nums.append((cx - box.x, cy - box.y))
    v_cuts = _stacked_cuts([p[0] for p in nums], [p[1] for p in nums],
                           box.w, box.h, vertical=True)
    h_cuts = _stacked_cuts([p[1] for p in nums], [p[0] for p in nums],
                           box.h, box.w, vertical=False)
    return v_cuts, h_cuts


def _stacked_cuts(along: list[float], span: list[float], length: int,
                  other: int, vertical: bool) -> list[int]:
    tol = 80 if vertical else 40
    ordered = sorted(range(len(along)), key=lambda i: along[i])
    groups: list[list[int]] = []
    for i in ordered:
        if groups and abs(along[i] - along[groups[-1][-1]]) <= tol:
            groups[-1].append(i)
        else:
            groups.append([i])
    cuts = []
    for g in groups:
        if len(g) < 3:
            continue
        positions = [along[i] for i in g]
        if max(positions) - min(positions) > 100:
            continue  # scattered diagonally (title + ticks + annotations), not one column
        ordered_span = sorted(span[i] for i in g)
        span_extent = ordered_span[-1] - ordered_span[0]
        if span_extent < 0.35 * other:
            continue
        max_gap = max(b - a for a, b in zip(ordered_span[:-1], ordered_span[1:]))
        if max_gap > 0.6 * span_extent:
            continue  # bimodal (e.g. title row + tick row), not one stack
        mid = sum(positions) / len(positions)
        if 0.2 * length <= mid <= 0.8 * length:
            cuts.append(int(mid))
    cuts.sort()
    return [c for i, c in enumerate(cuts) if i == 0 or c - cuts[i - 1] >= 20]


def _dedup(boxes: list[_Box], outer_filter: bool = True) -> list[_Box]:
    boxes = sorted(boxes, key=lambda b: b.area(), reverse=True)
    kept: list[_Box] = []
    for b in boxes:
        if all(b.iou(k) < 0.5 for k in kept):
            kept.append(b)
    if not outer_filter or not kept:
        return kept
    # Drop boxes fully contained in a much larger one (labels inside a panel).
    # Disabled for validated splits, where halves legitimately share a parent.
    outer = [k for k in kept if k.area() >= 0.5 * kept[0].area()]
    return outer if outer else kept


def _refine_interior(gray: npt.NDArray, box: _Box) -> tuple[_Box, str]:
    """Shrink an envelope to the axis frame when long border lines are found.

    Each axis refines independently: an axis without spanning border evidence
    keeps the envelope extent instead of collapsing onto an interior grid
    line. Faint decade strokes that fragment under Hough are recovered
    through the dark-projection pass in calibration.
    """
    from graphextract.calibration import _merge_positions, projection_lines

    h, w = gray.shape[:2]
    x1 = max(0, box.x)
    y1 = max(0, box.y)
    x2 = min(w, box.x + box.w)
    y2 = min(h, box.y + box.h)
    crop = gray[y1:y2, x1:x2]
    if crop.size == 0:
        return box, "low"
    edges = cv2.Canny(crop, 30, 100)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=60,
        minLineLength=int(0.5 * min(crop.shape[:2])), maxLineGap=5,
    )
    verts: list[int] = []
    horiz: list[int] = []
    ch, cw = crop.shape[:2]
    if lines is not None:
        for line in lines:
            lx1, ly1, lx2, ly2 = (int(v) for v in np.asarray(line).reshape(-1))
            if abs(lx2 - lx1) < 3 and abs(ly2 - ly1) > 0.5 * ch:
                verts.append((lx1 + lx2) // 2)
            elif abs(ly2 - ly1) < 3 and abs(lx2 - lx1) > 0.5 * cw:
                horiz.append((ly1 + ly2) // 2)
    proj_x, proj_y = projection_lines(crop)
    verts = _merge_positions(verts, proj_x)
    horiz = _merge_positions(horiz, proj_y)
    ix, refined_axes = _Box(x=x1, y=y1, w=x2 - x1, h=y2 - y1), 0
    if len(verts) >= 2 and max(verts) - min(verts) >= 0.5 * (x2 - x1):
        ix.x, ix.w = x1 + min(verts), max(verts) - min(verts)
        refined_axes += 1
    if len(horiz) >= 2 and max(horiz) - min(horiz) >= 0.5 * (y2 - y1):
        ix.y, ix.h = y1 + min(horiz), max(horiz) - min(horiz)
        refined_axes += 1
    if refined_axes == 2 and ix.w > 0 and ix.h > 0:
        # min/max land on stroke centres; pad by the stroke half-width so
        # the outer frame/grid strokes themselves stay inside the interior.
        # Without this, a 1-2px shave silently drops the outer decade lines
        # and their tick labels can never anchor.
        pad = 3
        x0n, y0n = max(x1, ix.x - pad), max(y1, ix.y - pad)
        x1n, y1n = min(x2, ix.x + ix.w + pad), min(y2, ix.y + ix.h + pad)
        return _Box(x=x0n, y=y0n, w=x1n - x0n, h=y1n - y0n), "refined"
    return ix, "low"


def detect_panels(img: npt.NDArray, image_id: str = "img",
                  words=None) -> list[PanelGeometry]:
    """Detect panel envelopes and interiors in native image coordinates.

    ``words`` (optional OCR words, image-global coordinates) enables a second
    split pass on tick-label stacks for plots bridged by tick labels, where
    no pixel-level gutter exists. Without words the detector stays purely
    geometric.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    boxes = _dedup(_contour_boxes(gray, h * w))
    method = "contours"
    if boxes and words:
        resplit: list[_Box] = []
        for b in boxes:
            vc, hc = tick_stack_cuts(words, b)
            resplit.extend(_apply_cuts(gray, b, b.x, b.y, b.w, b.h, vc, hc))
        if len(resplit) > len(boxes):
            boxes = _dedup(resplit, outer_filter=False)
            method = "contours+tickstack"
    if not boxes:
        boxes = _split_proposals(gray)
        method = "projection_split"
    boxes.sort(key=lambda b: (b.y // max(1, h // 4), b.x))

    panels = []
    for i, box in enumerate(boxes):
        interior, confidence = _refine_interior(gray, box)
        panels.append(
            PanelGeometry(
                panel_id=f"{image_id}#p{i}",
                envelope_xywh=(box.x, box.y, box.w, box.h),
                interior_xywh=(interior.x, interior.y, interior.w, interior.h),
                image_width=w,
                image_height=h,
                interior_confidence=confidence,
                detection_method=method,
            )
        )
    return panels
