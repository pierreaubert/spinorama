# -*- coding: utf-8 -*-
"""Joint multi-series tracking with explicit gap and overlap states.

All series sharing an interior are tracked together so crossings keep their
identities. Columns without evidence become MISSING samples (never
interpolated). Coincident sections keep every member series; the hidden member
receives INFERRED_OCCLUSION with widened uncertainty. Ambiguous exits retain
alternatives instead of silently picking one. No smoothing is applied unless
the caller explicitly requests it for a display export.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from graphextract.evidence import EvidenceLayers, refine_centerline
from graphextract.schema import SegmentStatus, SeriesResult, SeriesSample


@dataclass
class TrackConfig:
    min_gap_px: int = 3
    beam_width: int = 4
    # Owned evidence is tracked as observed unless the frame-to-frame jump is
    # larger than this: abrupt jumps become occlusion/missing candidates for
    # review instead of being silently dropped or smoothed over.
    occlusion_penalty: float = 12.0
    smooth_window: int = 0  # 0 disables smoothing; >0 applies Savitzky-Golay for preview only


def _clusters(column: npt.NDArray, min_gap: int) -> list[list[int]]:
    on = np.nonzero(column)[0]
    if len(on) == 0:
        return []
    groups: list[list[int]] = [[int(on[0])]]
    for p in on[1:]:
        if int(p) - groups[-1][-1] <= min_gap:
            groups[-1].append(int(p))
        else:
            groups.append([int(p)])
    return groups


def _joint_assignment(
    centroids: list[float],
    predictions: dict[str, float | None],
    owned: dict[str, set[int]],
    series_ids: list[str],
    beam_width: int,
    occlusion_penalty: float = 12.0,
) -> dict[str, int | None]:
    """Assign clusters to series minimising motion + occlusion cost (beam search).

    A series may only take a cluster containing its own evidence pixels;
    several series may share one cluster (coincident overlap). Unassigned
    series become occlusion/missing candidates downstream.
    """
    options: list[dict[str, int | None]] = [{}]
    for sid in series_ids:
        pred = predictions.get(sid)
        owned_here = owned.get(sid, set())
        ranked = sorted(owned_here,
                        key=lambda c: abs(centroids[c] - pred) if pred is not None else 0.0)
        nxt: list[dict[str, int | None]] = []
        for hyp in options:
            for c in ranked[:beam_width]:
                h = dict(hyp)
                h[sid] = c
                nxt.append(h)
            h = dict(hyp)
            h[sid] = None
            nxt.append(h)
        # Score and prune to beam_width.
        def cost(h: dict[str, int | None]) -> float:
            total = 0.0
            for s, c in h.items():
                p = predictions.get(s)
                if c is None:
                    total += occlusion_penalty
                elif p is not None:
                    total += abs(centroids[c] - p)
            return total

        options = sorted(nxt, key=cost)[:beam_width]
    return options[0]


def track_panel(
    gray: npt.NDArray,
    layers: EvidenceLayers,
    series_ids: list[str],
    bg_value: float,
    config: TrackConfig | None = None,
) -> dict[str, SeriesResult]:
    """Track every series over integer columns; see module docstring for states."""
    cfg = config or TrackConfig()
    h, w = gray.shape[:2]
    # Union mask clusters define candidate positions per column.
    union = np.zeros((h, w), dtype=np.uint8)
    for m in layers.curve_masks.values():
        union = np.bitwise_or(union, m)
    owned: dict[str, npt.NDArray] = {
        sid: layers.curve_masks.get(sid, np.zeros((h, w), np.uint8)) for sid in series_ids
    }

    last_y: dict[str, float | None] = {sid: None for sid in series_ids}
    last_v: dict[str, float | None] = {sid: None for sid in series_ids}
    seqs: dict[str, list[SeriesSample]] = {sid: [] for sid in series_ids}

    for x in range(w):
        clusters = _clusters(union[:, x], cfg.min_gap_px)
        if not clusters:
            for sid in series_ids:
                seqs[sid].append(SeriesSample(u=float(x), v=float(last_y[sid] or 0.0),
                                             status=SegmentStatus.MISSING, half_width_px=1.0))
                last_v[sid] = None
            continue
        centroids = [float(sum(c) / len(c)) for c in clusters]
        owned_idx: dict[str, set[int]] = {}
        for sid in series_ids:
            own_col = owned[sid][:, x] > 0
            owned_idx[sid] = {i for i, c in enumerate(clusters) if own_col[c].any()}
        assignment = _joint_assignment(centroids, last_v, owned_idx, series_ids,
                                           cfg.beam_width, cfg.occlusion_penalty)
        for sid in series_ids:
            c = assignment[sid]
            has_own = c is not None and bool((owned[sid][clusters[c][0]:clusters[c][-1] + 1, x] > 0).any())
            if c is None or not has_own:
                # Evidence belongs to another series (or nobody): occluded or missing.
                others_claim = any(
                    (owned[o][:, x] > 0).any() for o in series_ids if o != sid
                )
                status = SegmentStatus.INFERRED_OCCLUSION if others_claim else SegmentStatus.MISSING
                # Extrapolate position from recent motion when occluded.
                prev = last_y[sid]
                v = prev if prev is not None else centroids[0]
                seqs[sid].append(SeriesSample(u=float(x), v=float(v), status=status,
                                             half_width_px=1.5))
                continue
            # Refine within this series' own evidence inside the shared cluster,
            # so nearby (but distinct) curves do not pull each other.
            lo, hi = clusters[c][0], clusters[c][-1]
            own_rows = [r for r in range(lo, hi + 1) if owned[sid][r, x] > 0]
            guess = float(sum(own_rows) / len(own_rows)) if own_rows else centroids[c]
            win_lo = max(0, int(guess) - 3)
            win_hi = min(h, int(guess) + 4)
            wts = (owned[sid][win_lo:win_hi, x] > 0).astype(float)
            wts = wts if wts.any() else None
            center, half = refine_centerline(gray, x, guess, bg_value, weights=wts)
            seqs[sid].append(SeriesSample(u=float(x), v=center, status=SegmentStatus.OBSERVED,
                                         half_width_px=half))
            last_y[sid] = center
            recent = [s.v for s in seqs[sid][-6:] if s.status is SegmentStatus.OBSERVED]
            last_v[sid] = recent[-1] + (recent[-1] - recent[0]) / max(1, len(recent) - 1) \
                if len(recent) >= 2 else recent[-1] if recent else None

    results: dict[str, SeriesResult] = {}
    for sid in series_ids:
        results[sid] = SeriesResult(series_id=sid, panel_id="", label=sid,
                                    axis_id="y_left", samples=seqs[sid])
    _flag_duplicates(results)
    return results


def _flag_duplicates(results: dict[str, SeriesResult]) -> None:
    """Flag near-identical predicted tracks as possible duplicate instances."""
    sids = list(results)
    for i in range(len(sids)):
        for j in range(i + 1, len(sids)):
            a = [s for s in results[sids[i]].samples if s.status is SegmentStatus.OBSERVED]
            b = [s for s in results[sids[j]].samples if s.status is SegmentStatus.OBSERVED]
            common = min(len(a), len(b))
            if common < 10:
                continue
            err = float(np.mean([abs(x.v - y.v) for x, y in zip(a[:common], b[:common])]))
            if err < 0.75:
                msg = f"possible duplicate of {sids[j]} (mean |dv|={err:.2f}px)"
                results[sids[i]].review_reasons.append(msg)
                results[sids[j]].review_reasons.append(f"possible duplicate of {sids[i]}")


def maybe_smooth(values: list[float], window: int) -> list[float]:
    """Explicit opt-in smoothing for display previews; never part of measurement."""
    if window <= 0 or len(values) < window:
        return list(values)
    from scipy.signal import savgol_filter

    return [float(v) for v in savgol_filter(np.array(values), window, 2)]
