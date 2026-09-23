# -*- coding: utf-8 -*-
"""Jina-OCR fallback for axis anchors when Tesseract delivers nothing.

The model emits text without boxes, so tick values pair to grid lines by
reading order: transcription blocks group one axis at a time, and grid
lines ARE the ticks, so an exact count match on both axes is strong
evidence. Anything else fails closed (no anchors, no guessing).

Fallback anchors carry source ``jina_fallback`` at 0.5 confidence and the
caller must flag the panel for manual review: the model occasionally
emits hallucinated filler tables.
"""

from __future__ import annotations

import numpy.typing as npt
from spinorama import logger

from graphextract.calibration import ScaleType, detect_grid_lines, parse_tick_label
from graphextract.jina_ocr import GRAPH_PROMPT
from graphextract.pipeline import AxisAnchors
from graphextract.schema import TickAnchor

FALLBACK_SOURCE = "jina_fallback"
FALLBACK_CONFIDENCE = 0.5


def _parse_values(text: str) -> list[float]:
    """Numeric values in reading order (k/Hz/decade forms folded)."""
    values: list[float] = []
    for token in text.replace(",", " ").split():
        parsed = parse_tick_label(token)
        if parsed is not None:
            values.append(parsed[0])
    return values


def _strictly_increasing(values: list[float]) -> bool:
    return len(values) >= 2 and all(b > a for a, b in zip(values, values[1:]))


def _x_ratio(x_vals: list[float]) -> float:
    """Span ratio of an x candidate; non-positive values can never be log ticks."""
    if min(x_vals) <= 0:
        return 0.0
    return max(x_vals) / min(x_vals)


def split_axis_values(
    values: list[float], n_x: int, n_y: int
) -> tuple[list[float], list[float]] | None:
    """Split a reading-order value list into (x, y) by exact grid counts.

    Tries every split point in both orientations. Candidates need distinct,
    strictly increasing values with >= 2 anchors per axis. Among candidates,
    prefers the log-like assignment (widest x span ratio, then narrowest y
    band); an exact tie fails closed with None, as does no match.
    """
    if n_x < 2 or n_y < 2 or len(values) != n_x + n_y:
        return None

    def _candidate(side_x: list[float], side_y: list[float]):
        x_vals, y_vals = sorted(set(side_x)), sorted(set(side_y))
        if len(x_vals) != n_x or len(y_vals) != n_y:
            return None
        if not _strictly_increasing(x_vals) or not _strictly_increasing(y_vals):
            return None
        return (x_vals, y_vals)

    matches = []
    for cut in range(1, len(values)):
        head, tail = values[:cut], values[cut:]
        if len(head) == n_x and len(tail) == n_y:
            hit = _candidate(head, tail)
            if hit is not None:
                matches.append(hit)
        if len(head) == n_y and len(tail) == n_x:
            hit = _candidate(tail, head)
            if hit is not None and hit not in matches:
                matches.append(hit)
    if not matches:
        return None

    def _rank_key(match: tuple[list[float], list[float]]) -> tuple[float, float]:
        x_vals, y_vals = match
        return (_x_ratio(x_vals), -(max(y_vals) - min(y_vals)))

    ranked = sorted(matches, key=_rank_key, reverse=True)
    best = ranked[0]
    best_key = _rank_key(best)
    for other in ranked[1:]:
        if _rank_key(other) == best_key:
            return None
    return best


def _route_y(y_vals: list[float]) -> str:
    """Which y side a recovered block belongs to, by SPL plausibility.

    A left SPL axis reaches high (80 dB+); a low-only block (DI, phase)
    belongs on the right. Documented heuristic, covered by the review flag.
    """
    return "y_left" if max(y_vals) >= 60 else "y_right"


def _build_anchors(
    x_vals: list[float], y_vals: list[float],
    grid_xs: list[int], grid_ys: list[int],
) -> AxisAnchors:
    """Pair sorted values to sorted grid lines at fallback confidence."""
    y_side = _route_y(y_vals)
    y_anchors = [TickAnchor(float(gy), v, FALLBACK_CONFIDENCE, FALLBACK_SOURCE)
                 for gy, v in zip(sorted(grid_ys), y_vals)]
    anchors = AxisAnchors(
        x=[TickAnchor(float(gx), v, FALLBACK_CONFIDENCE, FALLBACK_SOURCE)
           for gx, v in zip(sorted(grid_xs), x_vals)],
        source=FALLBACK_SOURCE,
    )
    if y_side == "y_left":
        anchors.y_left = y_anchors
    else:
        anchors.y_right = y_anchors
    if min(x_vals) >= 10 and max(x_vals) / min(x_vals) >= 8:
        anchors.x_scale, anchors.x_unit = ScaleType.LOG10, "Hz"
    if all(-60 <= v <= 150 for v in y_vals):
        if y_side == "y_left":
            anchors.y_unit = "dB"
        else:
            anchors.y_right_unit = "dB"
    return anchors


def fallback_anchors(
    text: str, grid_xs: list[int], grid_ys: list[int]
) -> tuple[AxisAnchors | None, dict]:
    """Build AxisAnchors from transcription text + detected grid lines.

    Dual-y-axis graphs read as three blocks (y, x, y): when the full
    token list cannot split, a leading or trailing extra block is set
    aside and the remainder pairs as usual, reported as ``partial`` with
    an unpaired count. Competing windows rank by log-like x, narrow y,
    then higher y (main SPL axis over DI); ties fail closed, as does
    everything else. Returns (anchors or None, status dict).
    """
    values = _parse_values(text)
    n_x, n_y = len(grid_xs), len(grid_ys)
    split = split_axis_values(values, n_x, n_y)
    if split is not None:
        return _build_anchors(*split, grid_xs, grid_ys), {"status": "ok"}
    need = n_x + n_y
    if len(values) > need >= 4:
        hits = []
        for edge in ("prefix", "suffix"):
            window = values[:need] if edge == "prefix" else values[-need:]
            split = split_axis_values(window, n_x, n_y)
            if split is not None:
                x_vals, y_vals = split
                key = (_x_ratio(x_vals), -(max(y_vals) - min(y_vals)),
                       max(y_vals))
                hits.append((key, edge, split))
        hits.sort(key=lambda h: h[0], reverse=True)
        if hits and (len(hits) == 1 or hits[0][0] != hits[1][0]):
            (_, edge, split) = hits[0]
            anchors = _build_anchors(*split, grid_xs, grid_ys)
            return anchors, {"status": "partial",
                             "unpaired": len(values) - need, "edge": edge}
    return None, {"status": "no_count_match"}


def maybe_jina_fallback(
    panel_crop: npt.NDArray, interior: npt.NDArray, image_id: str, reader
) -> tuple[AxisAnchors | None, dict]:
    """Transcribe a panel crop and attempt fallback anchors.

    The full panel (margins included) is transcribed since ticks live
    outside the plot; grid lines come from the interior crop, matching
    the Tesseract path geometry. ``reader`` is a loaded JinaOCRReader
    (loading 6.7 GB of weights here would surprise callers, so the model
    must be provided, never pulled). Returns (anchors or None, status
    dict for the census record).
    """
    try:
        text = reader.transcribe_array(panel_crop, prompt=GRAPH_PROMPT)
    except Exception as exc:  # noqa: BLE001 -- model failure is a status, not a crash
        return None, {"source": FALLBACK_SOURCE, "status": f"transcribe_failed: {exc}"}
    grid_xs, grid_ys = detect_grid_lines(interior)
    anchors, build_status = fallback_anchors(text, grid_xs, grid_ys)
    if anchors is None:
        return None, {"source": FALLBACK_SOURCE, **build_status}
    n_y = len(anchors.y_left) + len(anchors.y_right)
    logger.warning(
        "Jina-OCR fallback anchors for %s (%d x + %d y ticks, %s): "
        "values are model-generated without box geometry, CHECK THE RESULT manually",
        image_id, len(anchors.x), n_y, build_status["status"],
    )
    return anchors, {"source": FALLBACK_SOURCE, "needs_review": True, **build_status}
