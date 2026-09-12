# -*- coding: utf-8 -*-
"""Joint multi-series tracking with explicit gap and overlap states.

All series sharing an interior are tracked together so crossings keep their
identities. Columns without evidence become MISSING samples (never
interpolated). Coincident sections keep every member series; the hidden member
receives INFERRED_OCCLUSION with widened uncertainty. Ambiguous exits retain
alternatives instead of silently picking one. No smoothing is applied unless
the caller explicitly requests it for a display export.

Opt-in assumptions (``TrackConfig.from_assumptions``) relax the default
evidence-only contract for callers who know more about their charts:

- ``curve_continuous``: the curve has no jumps on the x-axis, so interior
  non-observed runs flanked by OBSERVED samples are linearly bridged and
  marked INTERPOLATED (never OBSERVED). Leading/trailing gaps stay MISSING.
- ``no_jump``: vertical jumps are unlikely, so OBSERVED samples spiking off
  the local median by more than ``max_jump_px`` are demoted to MISSING,
  isolated adjacent-column steps keep only their longest smooth side
  (bounded, so sustained swaps are kept for review instead), and huge
  one-sided teleports demote a bounded window (catching staircases whose
  consecutive jumps shield each other). Assignment itself refuses instant
  teleports: a far cluster tying with occlusion on cost loses the tie, so
  a stale track goes missing instead of silently riding foreign ink that
  happens to share its colour. A track lost for ``_REACQUIRE_AFTER``
  consecutive uncovered columns is re-acquired to the nearest owned
  cluster within ``_REACQUIRE_MAX_PX`` (hole plus review note, never a
  drawn cliff), so temporary loss stays a short gap instead of a stuck
  track. Step-demoted spans are never interpolated,
  and ``curve_continuous`` additionally refuses bridges
  steeper than the flank-supported slope, so a dropout re-emerging on
  another curve stays a hole instead of becoming a drawn cliff.
- ``assume_overlap``: when curves merge, hidden members are assumed present
  underneath: a series with a live motion prediction keeps an
  INFERRED_OCCLUSION track through columns whose merged ink covers the
  prediction, instead of dropping to MISSING. Two extensions close the
  remaining holes. Buried stretches never build a live prediction, so from
  every observed block the track is extended left along seeded motion
  while merged ink covers the path (positions follow motion only; the ink
  gates, never pulls). Interior runs
  rejected by ``no_jump`` step demotion are bridged when the straight
  flank-to-flank bridge passes the continuity slope check and merged ink
  covers it end to end. Columns with no ink at all, predictions pointing
  at empty space, and flank-unsupported steep bridges stay MISSING.

Every assumption leaves a trace: interpolated/occlusion statuses in the
canonical samples, per-series review notes, and the panel provenance record.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from graphextract.evidence import EvidenceLayers, refine_centerline
from graphextract.schema import SegmentStatus, SeriesResult, SeriesSample

KNOWN_ASSUMPTIONS = ("curve_continuous", "no_jump", "assume_overlap")
"""Assumption names accepted by ``TrackConfig.from_assumptions`` and ``--assumptions``."""


@dataclass
class TrackConfig:
    min_gap_px: int = 3
    beam_width: int = 4
    # Owned evidence is tracked as observed unless the frame-to-frame jump is
    # larger than this: abrupt jumps become occlusion/missing candidates for
    # review instead of being silently dropped or smoothed over.
    occlusion_penalty: float = 12.0
    smooth_window: int = 0  # 0 disables smoothing; >0 applies Savitzky-Golay for preview only
    curve_continuous: bool = False
    no_jump: bool = False
    max_jump_px: float = 10.0
    assume_overlap: bool = False

    @classmethod
    def from_assumptions(cls, names: Iterable[str], **overrides) -> TrackConfig:
        """Build a config with the named assumptions enabled; rejects unknowns."""
        cfg = cls(**overrides)
        unknown = [n for n in names if n not in KNOWN_ASSUMPTIONS]
        if unknown:
            raise ValueError(
                f"unknown assumption(s) {unknown}; known: {list(KNOWN_ASSUMPTIONS)}"
            )
        for name in names:
            setattr(cfg, name, True)
        return cfg

    def active_assumptions(self) -> list[str]:
        """Enabled assumption names in canonical order."""
        return [n for n in KNOWN_ASSUMPTIONS if getattr(self, n, False)]


_REACQUIRE_AFTER = 12
"""Uncovered columns without an assignment before a lost track re-acquires."""

_REACQUIRE_MAX_PX = 64.0
"""Widest snap a re-acquiring track may take to the nearest owned cluster."""


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
    clusters: list[list[int]],
    predictions: dict[str, float | None],
    owned: dict[str, set[int]],
    series_ids: list[str],
    beam_width: int,
    occlusion_penalty: float = 12.0,
    owned_masks: dict[str, npt.NDArray] | None = None,
    color_col: npt.NDArray | None = None,
    series_colors: dict[str, tuple[int, int, int]] | None = None,
    color_weight: float = 0.1,
    color_tol: float = 20.0,
    *,
    prefer_stay_on_ties: bool = False,
) -> dict[str, int | None]:
    """Assign clusters to series minimising motion + colour + occlusion cost.

    A series may only take a cluster containing its own evidence pixels;
    several series may share one cluster (coincident overlap). Unassigned
    series become occlusion/missing candidates downstream.

    Cost per series is capped motion plus the colour distance from the
    cluster's best own-evidence pixel to the series colour, beyond
    tolerance: with no motion history every cluster ties at zero motion,
    so evidence colour (not set order) decides the initial commitment; a
    stale prediction can still recover to far evidence carrying its own
    colour, while foreign-coloured evidence keeps losing to occlusion.
    Best-pixel (not median) keeps thin fringe-dominated strokes scoring
    near zero on their own evidence. Without colour information the cost
    reduces exactly to the legacy motion + occlusion.

    With ``prefer_stay_on_ties`` (the ``no_jump`` contract), hypotheses
    with fewer capped-motion teleports win cost ties, so a stale track
    goes missing instead of instantly riding far ink whose fringe pixels
    happen to score within tolerance. Strict cost wins are unaffected:
    near evidence still captures immediately.
    """
    series_colors = series_colors or {}
    use_color = (owned_masks is not None and color_col is not None
                 and len(clusters) == len(centroids))
    best_dist: dict[tuple[str, int], float] = {}
    if use_color:
        assert owned_masks is not None and color_col is not None
        col_pixels = np.asarray(color_col).reshape(-1, 3).astype(float)
        for sid in series_ids:
            ref = series_colors.get(sid)
            own_col = owned_masks.get(sid)
            if ref is None or own_col is None:
                continue
            ref_arr = np.array(ref, dtype=float)
            for c in owned.get(sid, set()):
                rows = [r for r in clusters[c] if own_col[r]]
                if rows:
                    best_dist[(sid, c)] = float(
                        np.linalg.norm(col_pixels[rows] - ref_arr, axis=1).min())

    def single_cost(sid: str, c: int | None) -> float:
        if c is None:
            return occlusion_penalty
        pred = predictions.get(sid)
        motion = abs(centroids[c] - pred) if pred is not None else 0.0
        total = min(motion, occlusion_penalty)
        if use_color:
            dist = best_dist.get((sid, c), float("inf"))
            total += color_weight * max(0.0, dist - color_tol)
        return total

    options: list[dict[str, int | None]] = [{}]
    for sid in series_ids:
        owned_here = owned.get(sid, set())
        ranked = sorted(owned_here, key=lambda c: single_cost(sid, c))
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
            return sum(single_cost(s, c) for s, c in h.items())

        def teleports(h: dict[str, int | None]) -> int:
            """Count capped-motion takes: jumps no smooth curve makes."""
            n = 0
            for s, c in h.items():
                if c is None:
                    continue
                pred = predictions.get(s)
                if pred is not None and abs(centroids[c] - pred) >= occlusion_penalty:
                    n += 1
            return n

        if prefer_stay_on_ties:
            options = sorted(nxt, key=lambda h: (cost(h), teleports(h)))[:beam_width]
        else:
            options = sorted(nxt, key=cost)[:beam_width]
    return options[0]


def track_panel(
    gray: npt.NDArray,
    layers: EvidenceLayers,
    series_ids: list[str],
    bg_value: float,
    config: TrackConfig | None = None,
    series_colors: dict[str, tuple[int, int, int]] | None = None,
    color_img: npt.NDArray | None = None,
) -> dict[str, SeriesResult]:
    """Track every series over integer columns; see module docstring for states.

    ``series_colors`` with a BGR ``color_img`` enables colour-aware
    assignment (initial commitment and stale-track recovery follow evidence
    that looks like the series); without them tracking is pure motion,
    exactly as before.
    """
    cfg = config or TrackConfig()
    h, w = gray.shape[:2]
    # Union mask clusters define candidate positions per column.
    union = np.zeros((h, w), dtype=np.uint8)
    for m in layers.curve_masks.values():
        union = np.bitwise_or(union, m)
    owned: dict[str, npt.NDArray] = {
        sid: layers.curve_masks.get(sid, np.zeros((h, w), np.uint8)) for sid in series_ids
    }
    use_color = (series_colors is not None and color_img is not None
                 and color_img.ndim == 3
                 and color_img.shape[0] == h and color_img.shape[1] == w)

    last_y: dict[str, float | None] = {sid: None for sid in series_ids}
    last_v: dict[str, float | None] = {sid: None for sid in series_ids}
    vel: dict[str, float] = {sid: 0.0 for sid in series_ids}
    occl_run: dict[str, int] = {sid: 0 for sid in series_ids}
    lost_run: dict[str, int] = {sid: 0 for sid in series_ids}
    stayed: dict[str, int] = {sid: 0 for sid in series_ids}
    overlap_kept: dict[str, int] = {sid: 0 for sid in series_ids}
    seqs_notes: dict[str, list[str]] = {sid: [] for sid in series_ids}
    step_skip: dict[str, set[int]] = {sid: set() for sid in series_ids}
    seqs: dict[str, list[SeriesSample]] = {sid: [] for sid in series_ids}

    for x in range(w):
        clusters = _clusters(union[:, x], cfg.min_gap_px)
        if not clusters:
            for sid in series_ids:
                seqs[sid].append(SeriesSample(u=float(x), v=float(last_y[sid] or 0.0),
                                             status=SegmentStatus.MISSING, half_width_px=1.0))
                last_v[sid] = None
                occl_run[sid] = 0
                lost_run[sid] = 0
            continue
        centroids = [float(sum(c) / len(c)) for c in clusters]
        owned_idx: dict[str, set[int]] = {}
        for sid in series_ids:
            own_col = owned[sid][:, x] > 0
            owned_idx[sid] = {i for i, c in enumerate(clusters) if own_col[c].any()}
        owned_masks: dict[str, npt.NDArray] | None = None
        color_col: npt.NDArray | None = None
        if use_color:
            assert color_img is not None  # narrowed by use_color above
            owned_masks = {sid: owned[sid][:, x] > 0 for sid in series_ids}
            color_col = np.asarray(color_img)[:, x].reshape(-1, 3)
        # Effective prediction: after an empty gap the velocity memory is
        # gone but the last observed level persists. Costing motion from
        # the frozen level (instead of zero) keeps post-gap capture honest:
        # reappearing ink nearby still wins immediately, while far ink must
        # tie-or-lose against occlusion instead of teleporting for free.
        effective = {
            sid: last_v[sid] if last_v[sid] is not None else last_y[sid] for sid in series_ids
        }
        assignment = _joint_assignment(
            centroids,
            clusters,
            effective,
            owned_idx,
            series_ids,
            cfg.beam_width,
            cfg.occlusion_penalty,
            owned_masks,
            color_col,
            series_colors,
            prefer_stay_on_ties=cfg.no_jump,
        )
        for sid in series_ids:
            c = assignment[sid]
            has_own = c is not None and bool((owned[sid][clusters[c][0]:clusters[c][-1] + 1, x] > 0).any())
            if c is None or not has_own:
                # Evidence belongs to another series (or nobody): occluded or missing.
                others_claim = any(
                    (owned[o][:, x] > 0).any() for o in series_ids if o != sid
                )
                pred = last_v[sid] if last_v[sid] is not None else last_y[sid]
                covered = (pred is not None and any(
                    cl[0] - 1 <= pred <= cl[-1] + 1 for cl in clusters))
                if cfg.assume_overlap and covered:
                    # Hidden under merged ink: follow motion instead of
                    # dropping to missing, with widening uncertainty.
                    assert pred is not None  # narrowed by covered above
                    occl_run[sid] += 1
                    overlap_kept[sid] += 1
                    lost_run[sid] = 0
                    seqs[sid].append(SeriesSample(
                        u=float(x), v=float(pred),
                        status=SegmentStatus.INFERRED_OCCLUSION,
                        half_width_px=min(6.0, 1.5 + 0.1 * occl_run[sid])))
                    last_y[sid] = float(pred)
                    last_v[sid] = float(pred) + vel[sid]
                    continue
                occl_run[sid] = 0
                status = SegmentStatus.INFERRED_OCCLUSION if others_claim else SegmentStatus.MISSING
                # Extrapolate position from recent motion when occluded.
                prev = last_y[sid]
                v = prev if prev is not None else centroids[0]
                seqs[sid].append(SeriesSample(u=float(x), v=float(v), status=status,
                                             half_width_px=1.5))
                if (cfg.no_jump and c is None and pred is not None and any(
                        abs(centroids[t] - pred) >= cfg.occlusion_penalty
                        for t in owned_idx[sid])):
                    # A far owned cluster lost the tie to occlusion: the
                    # track stays missing instead of teleporting. Counted
                    # here so the assumption leaves its usual trace.
                    stayed[sid] += 1
                lost_run[sid] += 1
                if (
                    cfg.no_jump
                    and lost_run[sid] % _REACQUIRE_AFTER == 0
                    and _maybe_reacquire(sid, pred, owned_idx[sid], centroids, last_y, last_v, vel)
                    is not None
                ):
                    seqs_notes[sid].append(
                        f"no_jump: re-acquired after {lost_run[sid]} lost columns (u={x})"
                    )
                    lost_run[sid] = 0
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
            occl_run[sid] = 0
            lost_run[sid] = 0
            recent = [s.v for s in seqs[sid][-6:] if s.status is SegmentStatus.OBSERVED]
            last_v[sid] = recent[-1] + (recent[-1] - recent[0]) / max(1, len(recent) - 1) \
                if len(recent) >= 2 else recent[-1] if recent else None
            vel[sid] = (recent[-1] - recent[0]) / (len(recent) - 1) if len(recent) >= 2 else 0.0

    if cfg.no_jump:
        for sid in series_ids:
            demoted = _remove_jumps(seqs[sid], cfg.max_jump_px)
            step_idx, long_kept = _remove_steps(seqs[sid], cfg.max_jump_px)
            parts = []
            if demoted:
                parts.append(f"{demoted} spike")
            if step_idx:
                parts.append(f"{len(step_idx)} step")
            if parts:
                seqs_notes[sid].append(
                    f"no_jump: {' and '.join(parts)} samples demoted to missing")
            if long_kept:
                seqs_notes[sid].append(
                    f"no_jump: {long_kept} long steps kept for review")
            step_skip[sid] = step_idx
    if cfg.curve_continuous:
        for sid in series_ids:
            filled, gaps, refused = _fill_continuous(
                seqs[sid], step_skip.get(sid, frozenset()))
            if filled:
                seqs_notes[sid].append(
                    f"curve_continuous: {filled} samples interpolated across {gaps} gaps")
            if refused:
                seqs_notes[sid].append(
                    f"curve_continuous: {refused} steep bridges refused")
    if cfg.assume_overlap:
        cover_cache: dict[int, list[list[int]]] = {}

        def clusters_at(x: int) -> list[list[int]]:
            if x not in cover_cache:
                cover_cache[x] = _clusters(union[:, x], cfg.min_gap_px)
            return cover_cache[x]

        for sid in series_ids:
            backfilled = _backfill_occluded(seqs[sid], clusters_at)
            bridged = 0
            if step_skip.get(sid):
                bridged = _bridge_occluded(seqs[sid], step_skip[sid], clusters_at)
            if backfilled:
                seqs_notes[sid].append(
                    f"assume_overlap: {backfilled} samples backfilled "
                    f"under merged ink")
            if bridged:
                seqs_notes[sid].append(
                    f"assume_overlap: {bridged} samples bridged under merged "
                    f"ink across step breaks")

    results: dict[str, SeriesResult] = {}
    for sid in series_ids:
        results[sid] = SeriesResult(series_id=sid, panel_id="", label=sid,
                                    axis_id="y_left", samples=seqs[sid],
                                    review_reasons=seqs_notes[sid])
        if cfg.assume_overlap and overlap_kept[sid]:
            results[sid].review_reasons.append(
                f"assume_overlap: {overlap_kept[sid]} samples continued under merged ink")
        if cfg.no_jump and stayed[sid]:
            results[sid].review_reasons.append(
                f"no_jump: {stayed[sid]} far-teleport ties refused (stayed missing)"
            )
    _flag_duplicates(results)
    return results


def _maybe_reacquire(
    sid: str,
    pred: float | None,
    owned_here: set[int],
    centroids: list[float],
    last_y: dict[str, float | None],
    last_v: dict[str, float | None],
    vel: dict[str, float],
) -> float | None:
    """Snap a lost prediction to the nearest owned cluster within reach.

    A track whose prediction has seen no usable update for a while is
    stale: the next owned ink is usually the continuing curve, not a far
    coincidence. Snaps are bounded by ``_REACQUIRE_MAX_PX`` and restart
    with zero velocity, so resumption is a fresh run after an honest hole
    (with a review note) instead of a drawn teleport. Returns the snapped
    level, or None when nothing qualifies and the track stays lost.
    """
    if pred is None or not owned_here:
        return None
    snap = min(owned_here, key=lambda c: abs(centroids[c] - pred))
    level = float(centroids[snap])
    if abs(level - pred) > _REACQUIRE_MAX_PX:
        return None
    last_y[sid] = level
    last_v[sid] = level
    vel[sid] = 0.0
    return level


def _remove_jumps(seq: list[SeriesSample], tol_px: float) -> int:
    """Demote OBSERVED samples spiking vertically off the local median.

    Single Hampel-style pass over a snapshot of positions: a sample whose
    ``|v - median|`` over the ±4 neighbouring OBSERVED samples exceeds
    ``tol_px`` becomes MISSING. Windows with fewer than 5 observed samples
    are left alone. Spikes wider than half the window (over 4 columns), and
    sharp legitimate tips only a column or two wide, are indistinguishable
    from jumps at this locality — the tolerance floors that ambiguity.
    """
    demoted = 0
    obs_idx = [i for i, s in enumerate(seq) if s.status is SegmentStatus.OBSERVED]
    pos = {i: seq[i].v for i in obs_idx}
    for k, i in enumerate(obs_idx):
        window = [pos[j] for j in obs_idx[max(0, k - 4):k + 5]]
        if len(window) < 5:
            continue
        if abs(pos[i] - float(np.median(window))) > tol_px:
            seq[i].status = SegmentStatus.MISSING
            demoted += 1
    return demoted


_STEP_ISOLATION = 3.0
_STEP_WINDOW = 6
_STEP_ABS_FACTOR = 10.0
_MAX_HIJACK_LEN = 64
_BRIDGE_FLOOR_PX = 3.0
_DUP_MIN_LEN = 6
_DUP_MAX_GAP = 12
_DUP_EXTEND_CAP = 128


def _remove_steps(seq: list[SeriesSample], tol_px: float) -> tuple[set[int], int]:
    """Demote identity-hijack sides of vertical steps.

    Two tiers. Tier 1: a column-adjacent OBSERVED pair whose ``|dv|``
    exceeds ``tol_px`` and more than ``_STEP_ISOLATION`` times both
    neighbouring adjacent deltas is an isolated jump, not a steep-but-
    smooth slope (whose consecutive deltas are all large) or a knee
    (whose jump matches the sustained new slope). Each maximal observed
    block is split at Tier 1 steps into smooth pieces; every piece of at
    most ``_MAX_HIJACK_LEN`` samples is demoted except the longest (ties
    keep the first). The length bound rules out catastrophic demotion on
    sustained swaps: those need cross-series reasoning, so blocks left
    with steps between two kept pieces are counted as unresolved instead.
    Tier 2: a pair jumping more than ``_STEP_ABS_FACTOR`` times tolerance
    with a small-or-missing delta on at least one side is a huge one-sided
    teleport no smooth curve makes in one column (e.g. the foot of a
    staircase whose consecutive jumps shield each other from Tier 1).
    Tier 2 demotes a bounded ``_STEP_WINDOW`` neighbourhood around the
    pair — wide enough to swallow short staircases whole, too narrow to
    destroy a track. Pairs without a neighbouring delta (lone two-sample
    blocks) cannot be judged and are kept. Returns (demoted sample
    indices, unresolved long-step count) so ``curve_continuous`` can
    refuse to interpolate across identity breaks.
    """
    n = len(seq)
    obs = [s.status is SegmentStatus.OBSERVED for s in seq]

    def delta(i: int) -> float:
        return seq[i + 1].v - seq[i].v

    tier1: set[int] = set()
    for i in range(n - 1):
        if not (obs[i] and obs[i + 1]):
            continue
        jump = abs(delta(i))
        if jump <= tol_px:
            continue
        prev_d = abs(delta(i - 1)) if i - 1 >= 0 and obs[i - 1] else None
        next_d = abs(delta(i + 1)) if i + 2 < n and obs[i + 2] else None
        neigh = [d for d in (prev_d, next_d) if d is not None]
        if neigh and all(jump > _STEP_ISOLATION * d for d in neigh):
            tier1.add(i)
    demoted: set[int] = set()
    for i in range(n - 1):
        if not (obs[i] and obs[i + 1]) or i in tier1:
            continue
        jump = abs(delta(i))
        if jump <= _STEP_ABS_FACTOR * tol_px:
            continue
        prev_d = abs(delta(i - 1)) if i - 1 >= 0 and obs[i - 1] else None
        next_d = abs(delta(i + 1)) if i + 2 < n and obs[i + 2] else None
        small = [d is None or d < jump / _STEP_ISOLATION for d in (prev_d, next_d)]
        if any(small):
            for t in range(max(0, i - _STEP_WINDOW + 1), min(n, i + _STEP_WINDOW + 1)):
                if obs[t]:
                    seq[t].status = SegmentStatus.MISSING
                    demoted.add(t)
    for t in demoted:
        obs[t] = False
    long_kept = 0
    i = 0
    while i < n:
        if not obs[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and obs[j + 1]:
            j += 1
        cuts = sorted(s for s in tier1 if i <= s < j)
        bounds = [i - 1] + cuts + [j]
        pieces = [(bounds[k] + 1, bounds[k + 1]) for k in range(len(bounds) - 1)]
        keep = max(range(len(pieces)),
                   key=lambda k: (pieces[k][1] - pieces[k][0], -k))
        for k, (a, b) in enumerate(pieces):
            if k == keep or b - a + 1 > _MAX_HIJACK_LEN:
                if k != keep:
                    long_kept += 1
                continue
            for t in range(a, b + 1):
                seq[t].status = SegmentStatus.MISSING
                demoted.add(t)
        i = j + 1
    return demoted, long_kept


def _fill_continuous(seq: list[SeriesSample],
                     skip: frozenset[int] | set[int] = frozenset()) -> tuple[int, int, int]:
    """Linearly bridge interior non-OBSERVED runs flanked by OBSERVED samples.

    Filled samples become INTERPOLATED, never OBSERVED, so measurement stays
    distinguishable from inference in the canonical document. Leading and
    trailing gaps stay MISSING: continuity cannot invent endpoints. Runs
    containing ``skip`` indices (identity breaks rejected by ``no_jump``
    step demotion) are left MISSING: bridging them would fabricate a ramp
    across an ambiguous identity. A bridge steeper than ``_STEP_ISOLATION``
    times the steepest flank slope (floored at ``_BRIDGE_FLOOR_PX`` per
    column) is likewise refused: flat flanks promise a flat truth, so a
    dropout re-emerging far away on another curve stays a hole instead of
    becoming a drawn cliff — while a dropout inside a steep rolloff still
    fills via flank support. Returns (filled samples, bridged gaps,
    refused steep bridges).
    """
    filled = gaps = refused = 0
    n = len(seq)
    obs = [s.status is SegmentStatus.OBSERVED for s in seq]
    i = 0
    while i < n:
        if obs[i]:
            i += 1
            continue
        j = i
        while j < n and not obs[j]:
            j += 1
        if i > 0 and j < n and not any(t in skip for t in range(i, j)):
            lo = abs(seq[i - 1].v - seq[i - 2].v) if i >= 2 and obs[i - 2] else 0.0
            hi = abs(seq[j + 1].v - seq[j].v) if j + 1 < n and obs[j + 1] else 0.0
            slope = abs(seq[j].v - seq[i - 1].v) / (j - i + 1)
            if slope <= _STEP_ISOLATION * max(lo, hi, _BRIDGE_FLOOR_PX):
                v0, v1 = seq[i - 1].v, seq[j].v
                hw = max(seq[i - 1].half_width_px, seq[j].half_width_px)
                span = j - i + 1
                for t in range(i, j):
                    frac = (t - i + 1) / span
                    seq[t].v = v0 + frac * (v1 - v0)
                    seq[t].half_width_px = hw + 0.25 * min(t - i + 1, j - t)
                    seq[t].status = SegmentStatus.INTERPOLATED
                    filled += 1
                gaps += 1
            else:
                refused += 1
        i = j
    return filled, gaps, refused


_BACKFILL_CAP = 256
_BACKFILL_GATE0 = 3.0
_BACKFILL_GATE_SLOPE = 0.05
_BACKFILL_GATE_MAX = 6.0
_BACKFILL_MAX_VEL = 25.0
_BRIDGE_COVER_TOL_PX = 1.0


def _is_covered(clusters: list[list[int]], v: float, tol_px: float) -> bool:
    """True when merged ink covers level ``v`` (±1px + ``tol``).

    Mirrors the forward occlusion rule: any covering cluster confirms the
    motion-following track, including partially merged bundles split into
    several adjacent clusters. Empty space returns False. The ink only
    gates, never pulls, so nearby splits cannot bend the level.
    """
    return any(c[0] - 1 - tol_px <= v <= c[-1] + 1 + tol_px for c in clusters)


def _backfill_occluded(seq: list[SeriesSample], clusters_at) -> int:
    """Walk INFERRED_OCCLUSION left from every OBSERVED block.

    A series buried under merged ink never builds the motion prior that
    forward occlusion needs, so buried stretches drop to MISSING with a
    frozen prediction. From each observed block, seed velocity with the
    median per-column slope of the block's first few observed samples and
    walk left over MISSING columns while merged ink covers the
    back-extrapolated level. Positions follow pure motion (like forward
    occlusion) — the ink only gates, never pulls — so drift beyond the
    widening gate stops the walk instead of bending it. Non-MISSING columns
    (observed, or already claimed occlusion) are never overwritten. Each
    block walks at most ``_BACKFILL_CAP`` columns. Returns the backfilled
    count.
    """
    n = len(seq)
    is_obs = [s.status is SegmentStatus.OBSERVED for s in seq]
    filled = 0
    i = 0
    while i < n:
        if not is_obs[i]:
            i += 1
            continue
        j = i
        while j < n and is_obs[j]:
            j += 1
        window = list(range(i, min(j, i + 8)))
        slopes = [(seq[b].v - seq[a].v) / (b - a)
                  for a, b in zip(window, window[1:]) if b > a]
        if slopes:
            vel = float(np.median(slopes))
            vel = max(-_BACKFILL_MAX_VEL, min(_BACKFILL_MAX_VEL, vel))
            pred = seq[i].v - vel
            x = i - 1
            run = 0
            while x >= 0 and run < _BACKFILL_CAP:
                if seq[x].status is not SegmentStatus.MISSING:
                    break
                gate = min(_BACKFILL_GATE0 + _BACKFILL_GATE_SLOPE * run,
                           _BACKFILL_GATE_MAX)
                if not _is_covered(clusters_at(x), pred, gate):
                    break
                seq[x].v = pred
                seq[x].status = SegmentStatus.INFERRED_OCCLUSION
                seq[x].half_width_px = min(6.0, 1.5 + 0.1 * (run + 1))
                pred -= vel
                filled += 1
                run += 1
                x -= 1
        i = j
    return filled


def _bridge_occluded(seq: list[SeriesSample],
                     skip: frozenset[int] | set[int],
                     clusters_at, tol_px: float = _BRIDGE_COVER_TOL_PX) -> int:
    """Fill ``no_jump``-rejected interior runs covered end-to-end by ink.

    Runs containing ``skip`` indices flanked by OBSERVED samples on both
    sides are re-examined: when the straight bridge between the flanks
    passes the ``_fill_continuous`` flank-slope check and merged ink covers
    the bridge level at every column, the hidden curve is assumed present
    and the run becomes INFERRED_OCCLUSION instead of MISSING. Partially
    covered or flank-unsupported runs stay MISSING. Returns the filled
    count.
    """
    filled = 0
    n = len(seq)
    obs = [s.status is SegmentStatus.OBSERVED for s in seq]
    i = 0
    while i < n:
        if obs[i]:
            i += 1
            continue
        j = i
        while j < n and not obs[j]:
            j += 1
        if i > 0 and j < n and any(t in skip for t in range(i, j)):
            lo = abs(seq[i - 1].v - seq[i - 2].v) if i >= 2 and obs[i - 2] else 0.0
            hi = abs(seq[j + 1].v - seq[j].v) if j + 1 < n and obs[j + 1] else 0.0
            slope = abs(seq[j].v - seq[i - 1].v) / (j - i + 1)
            if slope <= _STEP_ISOLATION * max(lo, hi, _BRIDGE_FLOOR_PX):
                v0, v1 = seq[i - 1].v, seq[j].v
                span = j - i + 1
                levels = [v0 + (t - i + 1) / span * (v1 - v0) for t in range(i, j)]
                if all(_is_covered(clusters_at(t), v, tol_px)
                       for t, v in zip(range(i, j), levels)):
                    hw = max(seq[i - 1].half_width_px, seq[j].half_width_px)
                    for k, t in enumerate(range(i, j)):
                        seq[t].v = levels[k]
                        seq[t].half_width_px = hw + 0.25 * min(k + 1, j - t)
                        seq[t].status = SegmentStatus.INFERRED_OCCLUSION
                    filled += j - i
        i = j
    return filled


_DRAWN = (SegmentStatus.OBSERVED, SegmentStatus.INTERPOLATED)


def _edge_state(samples: list[SeriesSample], obs: list[bool],
                k: int, direction: int, tol_px: float) -> str:
    """Classify the track just outside span edge ``k``.

    Returns ``"smooth"`` (witnessed continuity: an adjacent-observed step
    matching the outward trend, or a nearby resumption at the predicted
    level), ``"cliff"`` (an observed jump — adjacent or across a short
    gap — far off the outward trend: a teleport, never a slope), or
    ``"void"`` (track edge or nothing observed within ``_DUP_MAX_GAP``).
    """
    n = len(samples)
    m = k + direction
    if m < 0 or m >= n:
        return "void"
    if obs[m]:
        return "cliff" if _surprise(samples, obs, k, m, direction, tol_px) else "smooth"
    gap = 0
    while 0 <= m < n and not obs[m] and gap < _DUP_MAX_GAP:
        m += direction
        gap += 1
    if not (0 <= m < n and obs[m]):
        return "void"
    return "cliff" if _surprise(samples, obs, k, m, direction, tol_px) else "smooth"


def _surprise(samples: list[SeriesSample], obs: list[bool],
              k: int, m: int, direction: int, tol_px: float) -> bool:
    """True when the level at ``m`` defies extrapolation from ``k``."""
    n = len(samples)
    o = m + direction
    slope = 0.0
    if 0 <= o < n and obs[o]:
        slope = samples[o].v - samples[m].v
    return abs(samples[m].v - (samples[k].v + slope * (m - k))) > tol_px


def _extend_ride(samples: list[SeriesSample], obs: list[bool], l: int, r: int,
                tol_px: float) -> tuple[int, int]:
    """Stretch a coincidence span over the claimant's drawn continuity.

    Extension follows OBSERVED and INTERPOLATED samples (what the plots
    draw) outward from the span, stopping at MISSING, the track edge, an
    outward cliff (never absorb the evidence), or ``_DUP_EXTEND_CAP``
    columns past the span on each side.
    """
    n = len(samples)
    lo, hi = l, r
    while lo - 1 >= max(0, l - _DUP_EXTEND_CAP) and samples[lo - 1].status in _DRAWN:
        if obs[lo - 1] and _surprise(samples, obs, lo, lo - 1, -1, tol_px):
            break
        lo -= 1
    while hi + 1 < min(n, r + _DUP_EXTEND_CAP + 1) and samples[hi + 1].status in _DRAWN:
        if obs[hi + 1] and _surprise(samples, obs, hi, hi + 1, +1, tol_px):
            break
        hi += 1
    return lo, hi


def resolve_duplicate_claims(tracks: dict[str, SeriesResult],
                             tol_px: float) -> dict[str, set[int]]:
    """Demote sustained wrong-graph riding where series coincide.

    When two series' OBSERVED tracks coincide within ``tol_px`` for at
    least ``_DUP_MIN_LEN`` consecutive columns, one of them is riding the
    other's ink — so the span is stretched over each claimant's drawn
    continuity (bounded by ``_DUP_EXTEND_CAP``) and its boundaries are
    classified. The intruder is the claimant showing a cliff at a span
    boundary with no smooth or pristine boundary anywhere: an observed
    jump far off the outward trend, or a resumption far off prediction
    across a short gap. Genuine merges (smooth everywhere), edge-started
    tracks (pristine boundary), steep-slope exits (surprise-free), and
    spans involving non-OBSERVED samples (occlusion, interpolation) stay
    untouched. Samples must share the column grid. Demoted spans stay
    MISSING (never interpolated): the ink belongs to the other series.
    Returns demoted indices per series.
    """
    sids = sorted(tracks)
    demoted: dict[str, set[int]] = {sid: set() for sid in sids}
    for ia in range(len(sids)):
        for ib in range(ia + 1, len(sids)):
            a, b = tracks[sids[ia]], tracks[sids[ib]]
            n = min(len(a.samples), len(b.samples))
            oa = [s.status is SegmentStatus.OBSERVED for s in a.samples]
            ob = [s.status is SegmentStatus.OBSERVED for s in b.samples]
            i = 0
            while i < n:
                if not (oa[i] and ob[i]) or abs(a.samples[i].v - b.samples[i].v) > tol_px:
                    i += 1
                    continue
                j = i
                while (j + 1 < n and oa[j + 1] and ob[j + 1]
                       and abs(a.samples[j + 1].v - b.samples[j + 1].v) <= tol_px):
                    j += 1
                if j - i + 1 >= _DUP_MIN_LEN:
                    _judge_ride(a, oa, b, ob, i, j, n, tol_px,
                                demoted[sids[ia]], demoted[sids[ib]])
                i = j + 1
    return demoted


def _judge_ride(a: SeriesResult, oa: list[bool], b: SeriesResult, ob: list[bool],
                i: int, j: int, n: int, tol_px: float,
                dem_a: set[int], dem_b: set[int]) -> None:
    """Demote whichever claimant's extended ride shows an unexcused cliff."""
    for series, obs, dem in ((a, oa, dem_a), (b, ob, dem_b)):
        l, r = _extend_ride(series.samples, obs, i, j, tol_px)
        states = {_edge_state(series.samples, obs, l, -1, tol_px),
                  _edge_state(series.samples, obs, r, +1, tol_px)}
        pristine = (l == 0) or (r == n - 1)
        if "cliff" in states and "smooth" not in states and not pristine:
            for t in range(l, r + 1):
                if series.samples[t].status in _DRAWN:
                    series.samples[t].status = SegmentStatus.MISSING
                    obs[t] = False
                    dem.add(t)


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
