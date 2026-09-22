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
  (bounded, so sustained swaps are kept for review instead; pairs whose
  both takes are colour-confirmed own ink are exempt, so steep V bottoms
  on real ink survive), and huge
  one-sided teleports demote a bounded window (catching staircases whose
  consecutive jumps shield each other). Assignment itself refuses instant
  teleports: a far cluster tying with occlusion on cost loses the tie, so
  a stale track goes missing instead of silently riding foreign ink that
  happens to share its colour. A motion-refused take resumes at once on
  colour-confirmed ink running ahead of live motion with the prediction
  standing empty or dead-reckoned (review note, never silent), so steep
  V walls are followed instead of coasted or bridged flat; a same-colour
  distractor under covering ink with the prediction intact keeps
  refusing. Any discontinuous resumption restarts motion, so the jump
  seeds neither velocity nor step gates. A track lost for
  ``_REACQUIRE_AFTER`` consecutive uncovered columns is re-acquired to
  the nearest owned cluster within ``_REACQUIRE_MAX_PX`` (hole plus
  review note, never a drawn cliff), so temporary loss stays a short gap
  instead of a stuck track. Past ``_RESEED_AFTER`` lost columns the
  stale prediction is abandoned and the track re-seeds on its best
  colour-confirmed owned cluster at any distance, so stranding past a
  steep bundle recovers in the clean stretch beyond it. Step-demoted spans are never interpolated,
  and ``curve_continuous`` additionally refuses bridges steeper than
  the flank-supported slope, longer than ``_FILL_MAX_GAP``, and sloped
  over empty space, so a dropout re-emerging on another curve stays a
  hole instead of becoming a drawn cliff.
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
    # Re-seed colour gate. Strict (core-grade) by default: near-hue
    # impostor edges score 14-28 while true cores score 0-15, so the
    # loose identity tolerance would re-seed onto foreign ink. Passes
    # that fence the impostor band (dB re-track behind DI-claimed ink)
    # loosen it to admit washed truth the fence verified as in-band.
    reseed_tol: float = 15.0
    # Owned evidence is tracked as observed unless the frame-to-frame jump is
    # larger than this: abrupt jumps become occlusion/missing candidates for
    # review instead of being silently dropped or smoothed over.
    occlusion_penalty: float = 12.0
    smooth_window: int = 0  # 0 disables smoothing; >0 applies Savitzky-Golay for preview only
    curve_continuous: bool = False
    no_jump: bool = False
    max_jump_px: float = 10.0
    assume_overlap: bool = False
    backend: str = "legacy"
    temporal_beam_width: int = 16
    temporal_ambiguity_cost: float = 0.5

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

_RESEED_EDGE_PX = 4
"""Interior margin re-seed targets must clear.

Frame furniture lives in the outer band and matches grey templates
through the box test; a re-seed there rides the frame to the panel
edge. True curve endpoints touch the frame only briefly, so vetoing
the band merely delays their re-seed by a few columns.
"""

_RESEED_AFTER = 200
"""Lost columns before a stranded track re-seeds on confirmed ink.

Re-acquire (``_REACQUIRE_MAX_PX``) only rescues locally stranded tracks;
a track whose prediction froze hundreds of pixels from its curve (past
a steep bundle its own pixels barely survive) never comes back. After
this many consecutive lost columns the stale prediction carries no
information, so the track re-seeds on its best colour-confirmed owned
cluster at any distance and restarts fresh. Transient holes never reach
the wait, and sibling latches stay demotable downstream.
"""

_CONFIRM_TOL = 25.0
"""Unmixing score within which a take counts as colour-confirmed identity.

Looser than ``_RESID_TOL`` (which prices colour into take costs): thin
pale true strokes score 15-22 while full cores sit near zero, so identity
exemptions (teleport tie-breaks, Tier 1 cuts) admit pale truth. Measured
margins on vendor plots: pale true ink 5-22, grey grid fringe ~24, dark
impostor cores (navy, saturated foreign hues) 34+. Near-hue pale fringe
(navy fringe vs teal scores ~10) still passes: it is guarded instead by
the motion gap bound and re-acquisition, never by this tolerance.
"""

_SEED_SCAN_COLS = 256
"""Look-ahead window for identity commitment (see ``_seed_columns``).

Wide enough to see past crowded lead-in merges: a series buried under
coincident ink for the first columns (PMC10-4 On Axis hides under the
bundle for ~80) must still find its own core-grade evidence before
committing, or it latches foreign fringe for good. Costs one prescan
pass at most; series committing early stop it immediately.
"""

_SEED_DIST_TOL = 10.0
"""Unmixing score that counts as an excellent seed match.

True ink unmixes against its template near zero at any mixture level;
cross-ink confusion sits an order of magnitude higher (PMC10-4 navy
fringe vs teal scores ~35, its core ~68). The first excellent column
commits, so crowded plot edges — where the true match is good but a
cleaner column comes later — do not defer the seed past real
observations.
"""

_RESID_TOL = 15.0
"""Unmixing score within which a take pays no colour cost.

Take costs use foreground/background unmixing residual (see
``_segment_scores``), not Euclidean distance: Euclidean conflates how
much ink a pixel holds with which ink it is, so a vivid foreign fringe
(navy core scores ~68) wins takes over faint true fringe (~150) and the
track latches the wrong ink for good (PMC10-4 On Axis rode the bottom
DI fringe; Early Reflections stalled wherever blue ran thin). True ink
scores 0-15 at any mixture level while foreign hues, grid, and text
stay an order of magnitude higher, so costs above this tolerance refuse
all but motion-exact evidence. Measured margin on vendor plots: true
ink 0-15, nearest impostor (navy fringe, grey grid) 34+.
"""

_TAINT_PENALTY = 6.0
"""Extra take cost for foreign-tainted candidates at identity commitment.

With no motion history every candidate ties at zero motion and colour
decides; shared-hue impostor fringe unmixes core-grade (Ascilab SPDI
re-seeded onto dB ink at score 7.9), so colour ties and set order picks
the band. Candidates touching foreign claims pay this penalty, but only
while a clean candidate shares the column, so overlay plots whose every
candidate is tainted behave exactly as before. It applies at identity
commitment only (first take, or re-seed after a long loss whose stale
prediction is meaningless), so crossings and gap re-acquisition keep
today's motion-led behaviour.
"""

_COVER_MAX = 1.3
"""Largest implied ink fraction that still counts as the template's ink.

Coverage is a fraction: pixels much darker than the template (black cores
against a grey template score near zero at coverage ~1.8) are a different
ink, mirroring ``mixture_match``. True strokes sit at or below 1.0;
legend-core sampling keeps template error small.
"""

_SEED_COVER_FLOOR = 0.35
"""Minimum coverage for the seed fallback's preferred candidate.

Without an excellent column the fallback takes the best-scoring owned
column, and a lone lucky fringe-soup pixel (coverage ~0.3) outranks the
true thin stroke (coverage ~0.4+) it should have seeded on. Preferring
substantial-coverage candidates commits identity on real ink; when no
column qualifies the unconstrained best still applies, preserving the
old behaviour for faint series.
"""

_SEED_MIN_RUN = 3
"""Consecutive owned columns that count as substantial seed ink.

A track seeds where its curve starts, not on the first blip: isolated
1-2 column owned fragments (unread glyph fringe, JPEG speckle) must
never commit an identity, or the track strands on a frozen prediction
far from its curve with no recovery in reach.
"""


def _frame_rows(union: npt.NDArray, height: int) -> set[int]:
    """Interior rows belonging to the top/bottom plot frame.

    The interior often starts a few pixels above the frame (detection
    slack), so a fixed edge band misses it while a wide one eats
    curves. Frame rows instead are measured: panel-spanning ink runs
    (90%+ of columns) in the top/bottom twentieth of the panel,
    dilated past antialiased skirts. Images without a detectable frame
    fall back to the fixed re-seed edge band.
    """
    rows: set[int] = set()
    w = union.shape[1]
    zone = max(8, height // 20)
    with np.errstate(all="ignore"):
        frac = (union > 0).sum(axis=1) / max(1, w)
    for r in list(range(0, zone)) + list(range(height - zone, height)):
        if 0 <= r < height and frac[r] >= 0.9:
            rows.update(range(max(0, r - 3), min(height, r + 4)))
    if not rows:
        rows.update(range(0, _RESEED_EDGE_PX))
        rows.update(range(max(0, height - _RESEED_EDGE_PX), height))
    return rows


def _seed_run_columns(mask: npt.NDArray, width: int) -> set[int]:
    """Columns belonging to an owned run of ``_SEED_MIN_RUN`` or more."""
    cols = [x for x in range(width) if (mask[:, x] > 0).any()]
    runs: set[int] = set()
    i = 0
    while i < len(cols):
        j = i
        while j + 1 < len(cols) and cols[j + 1] == cols[j] + 1:
            j += 1
        if j - i + 1 >= _SEED_MIN_RUN:
            runs.update(cols[i:j + 1])
        i = j + 1
    return runs


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


def _segment_scores(
    col_pixels: npt.NDArray,
    ref: npt.NDArray,
    bg: npt.NDArray,
) -> tuple[npt.NDArray, npt.NDArray]:
    """Per-pixel foreground/background unmixing against ``ref``.

    Euclidean distance to the template conflates *how much* ink a pixel
    holds (coverage) with *which* ink it is (hue): a half-white fringe of
    the true colour scores ~150 while a foreign dark core scores ~68, so
    ordering evidence by it prefers vivid impostors over faint truth.
    The residual to the template/background segment separates hue from
    coverage: any mixture level of the true colour scores near zero,
    foreign hues stay an order of magnitude higher. Mirrors
    ``mixture_match``. Returns (score, coverage) with coverage the median
    implied ink fraction; background pixels score infinite regardless of
    residual, since 0% ink matches every template.
    """
    denom = bg - ref
    sig = np.abs(denom) > 20.0
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.where(sig, (bg - col_pixels) / np.where(sig, denom, 1.0), np.nan)
    with np.errstate(all="ignore"):
        mid = np.nanmedian(alpha, axis=1)
        spread = np.nanmax(alpha, axis=1) - np.nanmin(alpha, axis=1)
    pred = mid[:, None] * ref + (1.0 - mid[:, None]) * bg
    resid = np.max(np.abs(col_pixels - pred), axis=1)
    scores = resid + 100.0 * spread
    # A background pixel is a perfect 0%-coverage "match" for every
    # template; like ``mixture_match`` demand substantial coverage before
    # a pixel counts as evidence at all. Coverage past ``_COVER_MAX`` is
    # darker-than-template ink (a different colour), never the template.
    scores = np.where((mid >= 0.2) & (mid <= _COVER_MAX), scores, np.inf)
    scores = np.where(np.isfinite(scores), scores, np.inf)
    return scores, np.where(np.isfinite(mid), mid, -1.0)


def _colour_best_dists(
    series_ids: list[str],
    owned: dict[str, set[int]],
    clusters: list[list[int]],
    owned_masks: dict[str, npt.NDArray] | None,
    color_col: npt.NDArray | None,
    series_colors: dict[str, tuple[int, int, int]] | None,
) -> dict[tuple[str, int], float]:
    """Best colour distance from each owned cluster to its series colour.

    Frame-to-frame assignment costs; empty when colour is unavailable.
    """
    series_colors = series_colors or {}
    best_dist: dict[tuple[str, int], float] = {}
    if owned_masks is None or color_col is None:
        return best_dist
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
    return best_dist


_CLEAN_RUN_MIN = 5
"""Minimum consecutive flagged columns that count as committable ink.

Deferral waits for clean ink runs (dash strokes span dozens of
columns); isolated clean pixels are hue noise, and waiting for them
would strand overlay plots — whose truth is tainted throughout — on
leaks instead of their own ink.
"""


def _run_gate(flags: npt.NDArray, min_run: int) -> npt.NDArray:
    """Keep only flags belonging to runs of ``min_run`` or more."""
    flags = np.asarray(flags).reshape(-1)
    out = np.zeros(len(flags), dtype=bool)
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(flags) and flags[j + 1]:
            j += 1
        if j - i + 1 >= min_run:
            out[i:j + 1] = True
        i = j + 1
    return out


def _clean_commit_flags(
    union: npt.NDArray,
    owned_mask: npt.NDArray,
    color_img: npt.NDArray,
    ref_bgr: tuple[int, int, int],
    bg_bgr: tuple[int, int, int],
    avoid_mask: npt.NDArray,
    min_gap_px: int,
    reseed_tol: float,
) -> tuple[npt.NDArray, npt.NDArray]:
    """Per-column clean-commitment flags for steered identity commitment.

    Returns ``(excellent, qualifying)`` boolean vectors over columns: a
    column is flagged when an owned cluster clear of foreign claims
    carries a pixel passing the seed-excellence gate (``_SEED_DIST_TOL``
    plus the core-coverage band, mirroring ``_seed_columns``) or the
    re-seed gate (``reseed_tol``, mirroring ``_maybe_reseed``).
    Frame-touching clusters never flag (frame furniture unmixes
    core-grade on dark templates), and neither do the edge strips
    ``_maybe_reseed`` cannot commit on. Flags keep only runs of
    ``_CLEAN_RUN_MIN`` or more: deferral waits for ink runs, never
    for isolated noise pixels. Columns are independent: the caller
    derives first-clean seeds and clean-ahead re-seed waits.
    """
    h, w = int(np.asarray(union).shape[0]), int(np.asarray(union).shape[1])
    exc = np.zeros(w, dtype=bool)
    qual = np.zeros(w, dtype=bool)
    frame = _frame_rows(union, h)
    own = np.asarray(owned_mask) > 0
    av = np.asarray(avoid_mask) > 0
    ref_arr = np.array(ref_bgr, dtype=float)
    bg = np.array(bg_bgr, dtype=float).reshape(1, 3)
    for x in range(_RESEED_EDGE_PX, w - _RESEED_EDGE_PX):
        if not (own[:, x] & ~av[:, x]).any():
            continue
        clusters = _clusters(np.asarray(union)[:, x], min_gap_px)
        if not clusters:
            continue
        col_pixels = np.asarray(color_img)[:, x].reshape(-1, 3).astype(float)
        scores, coverage = _segment_scores(col_pixels, ref_arr, bg)
        own_col = own[:, x]
        av_col = av[:, x]
        for c in clusters:
            if any(r in frame for r in c):
                continue
            rows = [r for r in c if own_col[r]]
            if not rows or any(av_col[r] for r in rows):
                continue
            if float(scores[rows].min()) <= reseed_tol:
                qual[x] = True
            if any(scores[r] <= _SEED_DIST_TOL
                   and 0.6 <= coverage[r] <= 1.15 for r in rows):
                exc[x] = True
            if exc[x] and qual[x]:
                break
    return _run_gate(exc, _CLEAN_RUN_MIN), _run_gate(qual, _CLEAN_RUN_MIN)


def _seed_columns(
    union: npt.NDArray,
    owned: dict[str, npt.NDArray],
    series_ids: list[str],
    series_colors: dict[str, tuple[int, int, int]] | None,
    color_img: npt.NDArray | None,
    bg_bgr: tuple[int, int, int] | None,
    min_gap_px: int,
    width: int,
    clean_seed: dict[str, int] | None = None,
) -> dict[str, int]:
    """First column where each series should commit to its identity.

    With no motion history every owned cluster ties at zero motion, so a
    series whose true ink is absent from the leftmost columns latches onto
    whatever foreign fringe its mask admits (PMC12 On Axis rode the navy
    Reflections-Dl fringe for the whole plot) and motion then keeps it
    there: colour can only mildly penalise, never evict. Scanning the
    first ``_SEED_SCAN_COLS`` columns for each series' best-colour owned
    cluster and staying missing before it commits identity on evidence
    instead of position. Clusters score by foreground/background unmixing
    residual (see ``_segment_scores``), not Euclidean distance, so faint
    true fringe outranks vivid foreign fringe. The first column within
    ``_SEED_DIST_TOL`` of the template commits, so crowded edges do not
    defer past real observations; without an excellent column the window's
    best substantial-coverage column wins (``_SEED_COVER_FLOOR``), else the
    unconstrained best. Series with nothing owned in the window seed on
    the first substantial owned run (``_SEED_MIN_RUN``) past it instead
    of column zero: committing on the first blip wherever it appears
    strands the track on a frozen prediction far from its curve (a
    backward pass behind an excluded legend strip seeds glyph fringe
    and never reaches the curve end). Series with no run anywhere, or
    no colour information at all, keep column zero and behave exactly
    as before. ``clean_seed`` optionally pins a series to its first
    clean-excellent column (see ``_clean_commit_flags``), deferring
    past tainted-only impostor ink; unpinned series behave exactly as
    without it.
    """
    seed = {sid: 0 for sid in series_ids}
    pinned = clean_seed or {}
    if series_colors is None or color_img is None or bg_bgr is None:
        for sid, col in pinned.items():
            if sid in seed:
                seed[sid] = col
        return seed
    bg = np.array(bg_bgr, dtype=float).reshape(1, 3)
    height = int(np.asarray(color_img).shape[0])
    frame = _frame_rows(union, height)
    wanted = {sid for sid in series_ids
              if series_colors.get(sid) is not None and sid not in pinned}
    run_cols = {sid: _seed_run_columns(owned[sid], width) for sid in series_ids}
    first_good: dict[str, int] = {}
    best_any: dict[str, tuple[float, int]] = {}
    best_sub: dict[str, tuple[float, int]] = {}
    for x in range(min(_SEED_SCAN_COLS, width)):
        clusters = _clusters(union[:, x], min_gap_px)
        if not clusters:
            continue
        owned_masks = {sid: owned[sid][:, x] > 0 for sid in series_ids}
        col_pixels = np.asarray(color_img)[:, x].reshape(-1, 3).astype(float)
        for sid in series_ids:
            if sid in pinned:
                continue
            ref = series_colors.get(sid)
            if ref is None:
                continue
            own_col = owned_masks.get(sid)
            if own_col is None:
                continue
            scores, coverage = _segment_scores(
                col_pixels, np.array(ref, dtype=float), bg)
            for c in clusters:
                if any(r in frame for r in c):
                    # Frame furniture scores perfectly on dark templates
                    # and would hand identity to a frame ride; the
                    # re-seed veto applies to seeding too.
                    continue
                rows = [r for r in c if own_col[r]]
                if not rows:
                    continue
                col_scores = scores[rows]
                dist = float(col_scores.min())
                # Core-grade commitment only: low-coverage soup pixels can
                # unmix near the segment by luck (PMC10-4 lead-in), so an
                # excellent score also needs a solid ink fraction on the
                # same pixel. Faint true lines still seed through the
                # best-column fallback.
                if (sid not in first_good
                        and any(scores[r] <= _SEED_DIST_TOL
                                and 0.6 <= coverage[r] <= 1.15 for r in rows)):
                    first_good[sid] = x
                if sid not in best_any or dist < best_any[sid][0]:
                    best_any[sid] = (dist, x)
                # Fallback preference: a lone lucky fringe pixel (coverage
                # ~0.3) otherwise outranks the true thin stroke (~0.4+).
                # Columns without a substantial pixel keep the
                # unconstrained best, so faint series behave as before.
                cover = float(coverage[rows[int(np.argmin(col_scores))]])
                if (cover >= _SEED_COVER_FLOOR
                        and (sid not in best_sub or dist < best_sub[sid][0])):
                    best_sub[sid] = (dist, x)
        if len(first_good) == len(wanted):
            break
    for sid in series_ids:
        if sid in pinned:
            seed[sid] = pinned[sid]
        elif sid in first_good:
            seed[sid] = first_good[sid]
        elif sid in best_sub:
            seed[sid] = best_sub[sid][1]
        elif sid in best_any:
            seed[sid] = best_any[sid][1]
        elif run_cols[sid]:
            seed[sid] = min(run_cols[sid])
    return seed


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
    bg_bgr: tuple[int, int, int] | None = None,
    avoid_cols: dict[str, npt.NDArray] | None = None,
) -> dict[str, int | None]:
    """Assign clusters to series minimising motion + colour + occlusion cost.

    A series may only take a cluster containing its own evidence pixels;
    several series may share one cluster (coincident overlap). Unassigned
    series become occlusion/missing candidates downstream.

    Cost per series is capped motion plus the unmixing score of the
    cluster's best own-evidence pixel against the series colour, beyond
    ``_RESID_TOL``: with no motion history every cluster ties at zero
    motion, so evidence colour (not set order) decides the initial
    commitment; a stale prediction can still recover to far evidence
    carrying its own colour, while foreign-coloured evidence keeps
    losing to occlusion. Unmixing (not Euclidean) distance keeps thin
    fringe-dominated strokes scoring near zero on their own evidence at
    any mixture level. Without colour information the cost reduces
    exactly to the legacy motion + occlusion; with colours but no
    background the legacy Euclidean term applies instead.
    ``avoid_cols`` optionally maps a series to its foreign-claim column
    vector: prediction-less takes (identity commitment) on tainted
    clusters pay ``_TAINT_PENALTY`` while a clean cluster shares the
    column, so shared-hue impostor fringe loses to the series' own ink.
    """
    series_colors = series_colors or {}
    use_color = (owned_masks is not None and color_col is not None
                 and len(clusters) == len(centroids))
    use_resid = use_color and bg_bgr is not None
    best_dist = ({} if use_resid else
                 (_colour_best_dists(series_ids, owned, clusters, owned_masks,
                                     color_col, series_colors)
                  if use_color else {}))
    resid_best: dict[tuple[str, int], float] = {}
    if use_resid:
        assert owned_masks is not None and color_col is not None
        col_pixels = np.asarray(color_col).reshape(-1, 3).astype(float)
        bg = np.array(bg_bgr, dtype=float).reshape(1, 3)
        for sid in series_ids:
            ref = series_colors.get(sid)
            own_col = owned_masks.get(sid)
            if ref is None or own_col is None:
                continue
            scores, _ = _segment_scores(col_pixels, np.array(ref, dtype=float), bg)
            for c in owned.get(sid, set()):
                rows = [r for r in clusters[c] if own_col[r]]
                if rows:
                    resid_best[(sid, c)] = float(scores[rows].min())

    tainted: set[tuple[str, int]] = set()
    clean_exists: dict[str, bool] = {}
    if avoid_cols is not None:
        for sid in series_ids:
            av = avoid_cols.get(sid)
            if av is None:
                continue
            av_col = np.asarray(av).reshape(-1) > 0
            own_col = (owned_masks.get(sid)
                       if owned_masks is not None else None)
            any_clean = False
            for c in owned.get(sid, set()):
                rows = [r for r in clusters[c]
                        if (own_col is None or own_col[r])
                        and 0 <= r < len(av_col)]
                if not rows:
                    continue
                if any(av_col[r] for r in rows):
                    tainted.add((sid, c))
                else:
                    any_clean = True
            clean_exists[sid] = any_clean

    def single_cost(sid: str, c: int | None) -> float:
        if c is None:
            return occlusion_penalty
        pred = predictions.get(sid)
        motion = abs(centroids[c] - pred) if pred is not None else 0.0
        total = min(motion, occlusion_penalty)
        if use_resid:
            total += max(0.0, resid_best.get((sid, c), float("inf")) - _RESID_TOL)
        elif use_color:
            dist = best_dist.get((sid, c), float("inf"))
            total += color_weight * max(0.0, dist - color_tol)
        if (pred is None and clean_exists.get(sid)
                and (sid, c) in tainted):
            total += _TAINT_PENALTY
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
            """Count capped-motion takes: jumps no smooth curve makes.

            A take on colour-confirmed evidence (best own pixel unmixes
            within ``_CONFIRM_TOL``) inside ``_REACQUIRE_MAX_PX`` is recovery,
            not a teleport: merged union clusters park their centroid
            between nearby strokes, so a stale prediction can sit a full
            penalty past its own ink while the ink itself is unambiguous
            (PMC15 On Axis dived past its teal dip and never came back).
            Dark impostor cores still count (navy cores score 55+); near-hue
            pale fringe passes the tolerance and is guarded instead by the
            motion gap bound and re-acquisition.
            """
            n = 0
            for s, c in h.items():
                if c is None:
                    continue
                pred = predictions.get(s)
                if pred is None:
                    continue
                gap = abs(centroids[c] - pred)
                if gap < occlusion_penalty:
                    continue
                if (gap <= _REACQUIRE_MAX_PX
                        and resid_best.get((s, c), float("inf")) <= _CONFIRM_TOL):
                    continue
                n += 1
            return n

        if prefer_stay_on_ties:
            options = sorted(nxt, key=lambda h: (cost(h), teleports(h)))[:beam_width]
        else:
            options = sorted(nxt, key=cost)[:beam_width]
    return options[0]


def _take_rows(
    own_rows: list[int],
    pred: float,
    fresh: bool,
    recent_step: float,
    min_gap: int,
    max_jump: float,
) -> tuple[list[int] | None, float | None]:
    """Owned rows a live track follows inside one merged cluster.

    A merged union cluster can park a same-colour distractor stroke
    (fringe, show-through) beside faint true ink; the whole-cluster mean
    then hands the track to whichever stroke holds more pixels even with
    a live motion prediction sitting on the true one (PMC15 Early
    Reflections dove 15px onto the EIR fringe and rode it for 30+
    columns, staircase-shielded from every post-hoc jump guard). While
    the prediction is fresh (observed recently, or continuously hidden
    under covering ink), follow the gap-separated group nearest to it
    instead of the mean.

    Returns (rows, centre); rows is None when even the nearest
    evidence sits too far off the live prediction to be the continuing
    curve: the downstream occlusion/missing path then coasts honest
    motion (or leaves a bridgable hole) and the existing
    far-teleport-tie note records the refusal. Stale tracks keep the
    legacy whole-cluster mean so recovery still snaps to the strongest
    ink. The motion allowance (``_STEP_ISOLATION`` times the recent
    step) keeps steep-but-smooth slopes and V corners taking: only
    jumps no recent motion supports are refused. Centre is the
    nearest-group mean (whole-cluster mean when stale).
    """
    if not own_rows:
        return [], None
    if fresh:
        groups: list[list[int]] = [[own_rows[0]]]
        for r in own_rows[1:]:
            if r - groups[-1][-1] <= min_gap:
                groups[-1].append(r)
            else:
                groups.append([r])
        near = min(groups, key=lambda g: abs(sum(g) / len(g) - pred)) \
            if len(groups) > 1 else own_rows
        centre = sum(near) / len(near)
        if abs(centre - pred) > max(max_jump, _STEP_ISOLATION * recent_step):
            return None, centre
        return near, centre
    return own_rows, sum(own_rows) / len(own_rows)


def _recover_rows(
    own_rows: list[int],
    pred: float,
    min_gap: int,
    scores: npt.NDArray,
    lo: int,
    vel: float,
    last_obs_v: float | None,
    covered: bool,
) -> list[int] | None:
    """Prediction-nearest owned group when it is the curve running ahead.

    Admission for a motion-refused take to resume on: the nearest
    gap-separated owned group whose best pixel unmixes against the series
    colour within ``_CONFIRM_TOL`` and whose centre sits within
    ``_REACQUIRE_MAX_PX`` of the prediction. Two further gates keep a
    same-colour distractor refused: the ink must lie ahead of live motion
    (same direction from the last observed level as the velocity, which a
    static prediction under cover never has) and the prediction must not
    be a live coast under covering ink (a curve hidden under merged ink
    with its prediction intact coasts; a dead-reckoned prediction that
    drifted far past its last sighting, or a level standing empty,
    follows confirmed ink). Without this path a steep V wall strands the
    track while its own curve dives away, and the strand gets coasted or
    bridged flat across real dips (PMC10-4 Window/ER). Returns None when
    any gate fails: the refusal stands.
    """
    if not own_rows or last_obs_v is None or covered:
        return None
    groups: list[list[int]] = [[own_rows[0]]]
    for r in own_rows[1:]:
        if r - groups[-1][-1] <= min_gap:
            groups[-1].append(r)
        else:
            groups.append([r])
    near = min(groups, key=lambda g: abs(sum(g) / len(g) - pred))
    centre = sum(near) / len(near)
    if (centre - last_obs_v) * vel <= 0:
        return None
    if abs(centre - pred) > _REACQUIRE_MAX_PX:
        return None
    if min(float(scores[r - lo]) for r in near) > _CONFIRM_TOL:
        return None
    return near


def _live_obs(seqs: list[SeriesSample], break_at: int, limit: int) -> list[float]:
    """Newest-first observed values after the latest motion break.

    A discontinuous resumption (recovery/episode/stale jump take) restarts
    motion at its index: earlier takes must not seed velocity or step
    gates, or the jump inflates both and the track runs away on the next
    columns (PMC10-4 ER left its dip wall with vel +12 and a 120px gate
    and wandered onto neighbour ink for the rest of the panel).
    """
    out: list[float] = []
    for i in range(len(seqs) - 1, break_at, -1):
        if seqs[i].status is SegmentStatus.OBSERVED:
            out.append(seqs[i].v)
            if len(out) >= limit:
                break
    return out


def track_panel(
    gray: npt.NDArray,
    layers: EvidenceLayers,
    series_ids: list[str],
    bg_value: float,
    config: TrackConfig | None = None,
    series_colors: dict[str, tuple[int, int, int]] | None = None,
    color_img: npt.NDArray | None = None,
    foreign_avoid: dict[str, npt.NDArray] | None = None,
) -> dict[str, SeriesResult]:
    """Track every series over integer columns; see module docstring for states.

    ``series_colors`` with a BGR ``color_img`` enables colour-aware
    assignment (initial commitment and stale-track recovery follow evidence
    that looks like the series); without them tracking is pure motion,
    exactly as before. ``foreign_avoid`` optionally maps a series to
    foreign-claim rows (same shape as its owned mask): identity
    commitment prefers clean candidates over tainted ones and defers
    tainted-only commitments while clean ink is coming (see
    ``_clean_commit_flags``, ``_joint_assignment`` and
    ``_maybe_reseed``).
    """
    cfg = config or TrackConfig()
    if cfg.backend == "temporal":
        if cfg.active_assumptions():
            raise ValueError("temporal backend does not implement legacy assumptions")
        if cfg.temporal_beam_width < 2 or cfg.temporal_ambiguity_cost < 0:
            raise ValueError("invalid temporal search settings")
        from graphextract.temporal import track_temporal
        return track_temporal(gray, layers, series_ids, cfg, series_colors,
                              color_img, foreign_avoid)
    if cfg.backend != "legacy":
        raise ValueError(f"unknown tracking backend: {cfg.backend}")

    h, w = gray.shape[:2]
    # Union mask clusters define candidate positions per column. The
    # inclusive union (gridlines included) keeps candidacy stable while
    # ownership stays grid-subtracted, so grid-coloured series observe
    # coverage and occlusion honestly but never ride grid ink.
    if layers.union_mask is not None:
        union = layers.union_mask
    else:
        union = np.zeros((h, w), dtype=np.uint8)
        for m in layers.curve_masks.values():
            union = np.bitwise_or(union, m)
    owned: dict[str, npt.NDArray] = {
        sid: layers.curve_masks.get(sid, np.zeros((h, w), np.uint8)) for sid in series_ids
    }
    use_color = (series_colors is not None and color_img is not None
                 and color_img.ndim == 3
                 and color_img.shape[0] == h and color_img.shape[1] == w)
    frame_rows = _frame_rows(union, h)
    clean_seed: dict[str, int] | None = None
    clean_ahead: dict[str, npt.NDArray] = {}
    if (foreign_avoid is not None and use_color and series_colors
            and layers.background_bgr is not None):
        assert color_img is not None  # narrowed by use_color above
        for sid in series_ids:
            av = foreign_avoid.get(sid)
            ref = series_colors.get(sid)
            if av is None or ref is None:
                continue
            exc, qual = _clean_commit_flags(
                union, owned[sid], color_img, ref,
                layers.background_bgr, av, cfg.min_gap_px, cfg.reseed_tol)
            if exc.any():
                if clean_seed is None:
                    clean_seed = {}
                clean_seed[sid] = int(np.nonzero(exc)[0][0])
            rev = np.logical_or.accumulate(qual[::-1])[::-1]
            ahead = np.zeros(w, dtype=bool)
            ahead[:-1] = rev[1:]
            clean_ahead[sid] = ahead

    seed_cols = _seed_columns(union, owned, series_ids, series_colors,
                              color_img if use_color else None,
                              layers.background_bgr if use_color else None,
                              cfg.min_gap_px, w, clean_seed)
    confirmed: dict[str, set[int]] = {sid: set() for sid in series_ids}
    last_y: dict[str, float | None] = {sid: None for sid in series_ids}
    last_v: dict[str, float | None] = {sid: None for sid in series_ids}
    vel: dict[str, float] = {sid: 0.0 for sid in series_ids}
    occl_run: dict[str, int] = {sid: 0 for sid in series_ids}
    fresh_run: dict[str, int] = {sid: 0 for sid in series_ids}
    last_refused_x: dict[str, int] = {sid: -10 ** 9 for sid in series_ids}
    episode_ref: dict[str, float | None] = {sid: None for sid in series_ids}
    stale_hold: dict[str, bool] = {sid: False for sid in series_ids}
    lost_run: dict[str, int] = {sid: 0 for sid in series_ids}
    since_obs: dict[str, int] = {sid: 0 for sid in series_ids}
    stayed: dict[str, int] = {sid: 0 for sid in series_ids}
    overlap_kept: dict[str, int] = {sid: 0 for sid in series_ids}
    seqs_notes: dict[str, list[str]] = {sid: [] for sid in series_ids}
    step_skip: dict[str, set[int]] = {sid: set() for sid in series_ids}
    recoveries: dict[str, int] = {sid: 0 for sid in series_ids}
    motion_breaks: dict[str, int] = {sid: -1 for sid in series_ids}
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
                since_obs[sid] += 1
                fresh_run[sid] += 1
            continue
        centroids = [float(sum(c) / len(c)) for c in clusters]
        owned_idx: dict[str, set[int]] = {}
        for sid in series_ids:
            own_col = owned[sid][:, x] > 0
            owned_idx[sid] = {i for i, c in enumerate(clusters) if own_col[c].any()}
            if x < seed_cols.get(sid, 0):
                # Identity not committed yet: holding the take keeps a
                # foreign fringe from becoming a permanent seed (see
                # _seed_columns). Flows through the normal missing path.
                owned_idx[sid] = set()
            elif last_y[sid] is None:
                # Uncommitted takes skip frame clusters: frame furniture
                # scores perfectly on dark templates and would hand
                # identity to a frame ride. Committed tracks keep frame
                # access for genuine endpoints at the plot edge.
                owned_idx[sid] = {
                    i for i in owned_idx[sid]
                    if not any(r in frame_rows for r in clusters[i])}
        owned_masks: dict[str, npt.NDArray] | None = None
        color_col: npt.NDArray | None = None
        if use_color:
            assert color_img is not None  # narrowed by use_color above
            owned_masks = {sid: owned[sid][:, x] > 0 for sid in series_ids}
            color_col = np.asarray(color_img)[:, x].reshape(-1, 3)
        avoid_cols: dict[str, npt.NDArray] | None = None
        if foreign_avoid is not None:
            avoid_cols = {
                sid: np.asarray(foreign_avoid[sid])[:, x] > 0
                for sid in series_ids
                if sid in foreign_avoid and foreign_avoid[sid] is not None
            }
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
            bg_bgr=layers.background_bgr if use_color else None,
            avoid_cols=avoid_cols,
        )
        for sid in series_ids:
            c = assignment[sid]
            pred = last_v[sid] if last_v[sid] is not None else last_y[sid]
            if (c is not None and pred is None and sid in clean_ahead
                    and bool(clean_ahead[sid][x])
                    and avoid_cols is not None
                    and sid in avoid_cols):
                # Uncommitted take on tainted ink while clean ink runs
                # are coming: wait for the clean commitment instead of
                # latching impostor fringe and drifting onto it (the
                # re-seed deferral covers stale tracks; committed
                # tracks never wait, so crossings are unaffected).
                av_col = np.asarray(avoid_cols[sid]).reshape(-1)
                own_col = owned[sid][:, x] > 0
                rows = [r for r in clusters[c]
                        if own_col[r] and 0 <= r < len(av_col)]
                if rows and any(av_col[r] for r in rows):
                    c = None
            follow_rows: list[int] | None = None
            just_refused = False
            obs_v: list[float] = []
            recent_step = 0.0
            if c is not None and cfg.no_jump and pred is not None:
                lo, hi = clusters[c][0], clusters[c][-1]
                own_rows = [r for r in range(lo, hi + 1) if owned[sid][r, x] > 0]
                obs_v = _live_obs(seqs[sid], motion_breaks[sid], 4)
                for a, b in zip(obs_v, obs_v[1:]):
                    recent_step = max(recent_step, abs(a - b))
                follow_rows, refuse_centre = _take_rows(
                    own_rows, pred, fresh_run[sid] < _REACQUIRE_AFTER,
                    recent_step, cfg.min_gap_px, cfg.occlusion_penalty)
                just_refused = follow_rows is None
                if (just_refused and use_color and color_col is not None
                        and series_colors):
                    # Colour-confirmed recovery: the assignment admitted
                    # this cluster (same-colour ink within reach) but the
                    # motion gate refused it. Refusing genuine reappearing
                    # ink strands the track on a frozen prediction while
                    # its own curve dives down a steep wall, and the
                    # strand gets coasted or bridged flat across a real
                    # dip. Retake the prediction-nearest confirmed group
                    # and let motion restart from it instead.
                    rec_ref = series_colors.get(sid)
                    bg_bgr = layers.background_bgr
                    if rec_ref is not None and bg_bgr is not None:
                        span = np.asarray(color_col)[lo:hi + 1].reshape(-1, 3).astype(float)
                        rec_scores, _ = _segment_scores(
                            span, np.array(rec_ref, dtype=float),
                            np.array(bg_bgr, dtype=float).reshape(1, 3))
                        rec_covered = any(
                            cl[0] - 1 <= pred <= cl[-1] + 1 for cl in clusters)
                        last_seen = obs_v[0] if obs_v else None
                        live_coast = (rec_covered and last_seen is not None
                                      and abs(pred - last_seen)
                                      <= cfg.occlusion_penalty)
                        near = _recover_rows(
                            own_rows, pred, cfg.min_gap_px, rec_scores, lo,
                            vel[sid], last_seen, live_coast)
                        if near is not None:
                            follow_rows = near
                            just_refused = False
                            recoveries[sid] += 1
                if just_refused:
                    # Far same-colour distractor, not the continuing curve:
                    # fall through to occlusion/missing instead of taking it.
                    assert refuse_centre is not None  # refusals report a level
                    last_refused_x[sid] = x
                    ref = episode_ref[sid]
                    if ref is None:
                        episode_ref[sid] = refuse_centre
                    elif abs(refuse_centre - ref) > cfg.occlusion_penalty:
                        # The refused level moved: the situation changed
                        # (truth turning, distractor handing off), so end
                        # the episode and let stale recovery take over
                        # instead of coasting a dead reckoning past it.
                        episode_ref[sid] = None
                        fresh_run[sid] = _REACQUIRE_AFTER
                        just_refused = False
                        follow_rows = own_rows
                    c = None if just_refused else c
            has_own = c is not None and bool((owned[sid][clusters[c][0]:clusters[c][-1] + 1, x] > 0).any())
            if c is None or not has_own:
                # Evidence belongs to another series (or nobody): occluded or missing.
                others_claim = any(
                    (owned[o][:, x] > 0).any() for o in series_ids if o != sid
                )
                covered = (pred is not None and any(
                    cl[0] - 1 <= pred <= cl[-1] + 1 for cl in clusters))
                if (cfg.assume_overlap and covered
                        and (since_obs[sid] < _REACQUIRE_AFTER or just_refused)):
                    # Hidden under merged ink: follow motion instead of
                    # dropping to missing, with widening uncertainty. Only
                    # while the prediction is fresh: ink covering a stale
                    # prediction is usually a foreign curve drifting
                    # through, and coasting it fabricates values (PMC10-4
                    # Early Reflections drifted 25 dB off). Past the lost
                    # threshold the honest answer is missing; re-acquire
                    # and bridging handle recovery. The exception is a
                    # just-refused same-colour distractor: the refusal is
                    # positive evidence the hidden curve is still there
                    # (its show-through is what got refused), so the coast
                    # continues while the distractor persists instead of
                    # expiring into a stale fringe ride. A truly ended
                    # curve offers no owned ink to refuse, so that case
                    # still ages out exactly as before.
                    assert pred is not None  # narrowed by covered above
                    occl_run[sid] += 1
                    overlap_kept[sid] += 1
                    lost_run[sid] = 0
                    since_obs[sid] += 1
                    # ``fresh_run`` pauses on refused columns (coasted or
                    # missing alike): the prediction stays live while its
                    # distractor is still being refused, so the episode
                    # sustains itself without going stale. Clean gaps age
                    # it out again, ending the episode.
                    if not just_refused:
                        fresh_run[sid] += 1
                        episode_ref[sid] = None
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
                since_obs[sid] += 1
                if not just_refused:
                    fresh_run[sid] += 1
                    episode_ref[sid] = None
                if (
                    cfg.no_jump
                    and lost_run[sid] % _REACQUIRE_AFTER == 0
                    and x - last_refused_x.get(sid, -10 ** 9) > _REACQUIRE_AFTER
                    and _maybe_reacquire(sid, pred, owned_idx[sid], centroids, last_y, last_v, vel)
                    is not None
                ):
                    seqs_notes[sid].append(
                        f"no_jump: re-acquired after {lost_run[sid]} lost columns (u={x})"
                    )
                    lost_run[sid] = 0
                elif (
                    cfg.no_jump
                    and use_color
                    and lost_run[sid] >= _RESEED_AFTER
                    and color_col is not None
                    and owned_masks is not None
                    and series_colors
                    and series_colors.get(sid) is not None
                    and layers.background_bgr is not None
                ):
                    reseeded = _maybe_reseed(
                        sid, x, w, h, owned_idx[sid], clusters, centroids,
                        owned_masks[sid], color_col, series_colors[sid],
                        layers.background_bgr, cfg.reseed_tol,
                        last_y, last_v, vel,
                        (avoid_cols or {}).get(sid),
                        clean_ahead.get(sid))
                    if reseeded is not None:
                        _, score = reseeded
                        seqs_notes[sid].append(
                            f"no_jump: re-seeded after {lost_run[sid]} lost "
                            f"columns (u={x}, score={score:.1f})"
                        )
                        lost_run[sid] = 0
                continue
            # Refine within this series' own evidence inside the shared cluster,
            # so nearby (but distinct) curves do not pull each other.
            # ``follow_rows`` (when set) is the prediction-nearest owned
            # group, so a stronger same-colour distractor sharing the
            # cluster cannot outvote faint true ink by pixel count.
            lo, hi = clusters[c][0], clusters[c][-1]
            if follow_rows is None:
                follow_rows = [r for r in range(lo, hi + 1) if owned[sid][r, x] > 0]
            guess = float(sum(follow_rows) / len(follow_rows)) if follow_rows else centroids[c]
            win_lo = max(0, int(guess) - 3)
            win_hi = min(h, int(guess) + 4)
            wts = (owned[sid][win_lo:win_hi, x] > 0).astype(float)
            wts = wts if wts.any() else None
            center, half = refine_centerline(gray, x, guess, bg_value, weights=wts)
            if cfg.no_jump and use_color and color_col is not None:
                ref = series_colors.get(sid) if series_colors else None
                bg_bgr = layers.background_bgr
                if ref is not None and bg_bgr is not None:
                    take_rows = [r for r in clusters[c] if owned[sid][r, x] > 0]
                    if take_rows:
                        span = np.asarray(color_col)[lo:hi + 1].reshape(-1, 3).astype(float)
                        bg_arr = np.array(bg_bgr, dtype=float).reshape(1, 3)
                        scores, _ = _segment_scores(
                            span, np.array(ref, dtype=float), bg_arr)
                        if (float(scores[[r - lo for r in take_rows]].min())
                                <= _CONFIRM_TOL):
                            confirmed[sid].add(len(seqs[sid]))
            seqs[sid].append(SeriesSample(u=float(x), v=center, status=SegmentStatus.OBSERVED,
                                         half_width_px=half))
            last_y[sid] = center
            occl_run[sid] = 0
            lost_run[sid] = 0
            since_obs[sid] = 0
            fresh_run[sid] = 0
            episode_ref[sid] = None
            if obs_v and abs(center - obs_v[0]) > max(
                    cfg.occlusion_penalty, _STEP_ISOLATION * recent_step):
                # Discontinuous resumption (recovery/episode/stale jump):
                # the step exceeds what a live motion gate would admit, so
                # restart motion here instead of seeding velocity and step
                # gates with the jump and running away on the next columns.
                motion_breaks[sid] = len(seqs[sid]) - 1
                last_v[sid] = center
                vel[sid] = 0.0
            else:
                recent = _live_obs(seqs[sid], motion_breaks[sid], 6)[::-1]
                last_v[sid] = recent[-1] + (recent[-1] - recent[0]) / max(1, len(recent) - 1) \
                    if len(recent) >= 2 else recent[-1] if recent else None
                vel[sid] = ((recent[-1] - recent[0]) / (len(recent) - 1)
                            if len(recent) >= 2 else 0.0)

    if cfg.no_jump:
        for sid in series_ids:
            demoted = _remove_jumps(seqs[sid], cfg.max_jump_px)
            step_idx, long_kept = _remove_steps(seqs[sid], cfg.max_jump_px,
                                               confirmed[sid])
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
    cover_cache: dict[int, list[list[int]]] = {}

    def clusters_at(x: int) -> list[list[int]]:
        if x not in cover_cache:
            cover_cache[x] = _clusters(union[:, x], cfg.min_gap_px)
        return cover_cache[x]

    if cfg.curve_continuous:
        for sid in series_ids:
            filled, gaps, refused = _fill_continuous(
                seqs[sid], step_skip.get(sid, frozenset()), clusters_at)
            if filled:
                seqs_notes[sid].append(
                    f"curve_continuous: {filled} samples interpolated across {gaps} gaps")
            if refused:
                seqs_notes[sid].append(
                    f"curve_continuous: {refused} bridges refused")
    if cfg.assume_overlap:
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
                                    review_reasons=seqs_notes[sid],
                                    confirmed=set(confirmed[sid]))
        if cfg.assume_overlap and overlap_kept[sid]:
            results[sid].review_reasons.append(
                f"assume_overlap: {overlap_kept[sid]} samples continued under merged ink")
        if cfg.no_jump and stayed[sid]:
            results[sid].review_reasons.append(
                f"no_jump: {stayed[sid]} far-teleport ties refused (stayed missing)"
            )
        if cfg.no_jump and recoveries[sid]:
            results[sid].review_reasons.append(
                f"no_jump: {recoveries[sid]} colour-confirmed recovery takes"
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


def _maybe_reseed(
    sid: str,
    x: int,
    width: int,
    height: int,
    owned_here: set[int],
    clusters: list[list[int]],
    centroids: list[float],
    own_col: npt.NDArray,
    col_pixels: npt.NDArray,
    ref_bgr: tuple[int, int, int],
    bg_bgr: tuple[int, int, int],
    tol: float,
    last_y: dict[str, float | None],
    last_v: dict[str, float | None],
    vel: dict[str, float],
    avoid_col: npt.NDArray | None = None,
    clean_ahead: npt.NDArray | None = None,
) -> tuple[float, float] | None:
    """Re-seed a long-lost track on its best confirmed owned cluster.

    Colour (not proximity) picks the target: the stale prediction is
    meaningless after ``_RESEED_AFTER`` lost columns, while the best
    unmixing score still identifies the curve (true cores score ~0-15,
    near-hue impostor edges 28+). Only clusters with a pixel within
    ``tol`` qualify — the config default is core-grade (``_RESID_TOL``)
    since the looser identity tolerance would admit sibling edges and
    re-seed onto foreign ink — and the target must clear the frame
    band (``_RESEED_EDGE_PX``), since frame furniture matches grey
    templates and would hand the resumed track a frame ride.
    ``avoid_col`` optionally marks foreign-claim rows: qualifying
    tainted clusters rank ``_TAINT_PENALTY`` worse while a clean
    cluster qualifies, so shared-hue impostor fringe (which unmixes
    core-grade) loses to the series' own ink. ``clean_ahead``
    optionally marks columns with qualifying clean ink strictly
    ahead: a tainted winner waits while one is coming and commits
    only when none is (overlay ink, plot end, or merged truth at a
    convergence). Resumption restarts with zero velocity. Returns
    (level, score), or None when nothing qualifies and the track
    stays lost.
    """
    if not owned_here:
        return None
    if x < _RESEED_EDGE_PX or x > width - 1 - _RESEED_EDGE_PX:
        return None
    scores, _ = _segment_scores(
        np.asarray(col_pixels, dtype=float), np.array(ref_bgr, dtype=float),
        np.array(bg_bgr, dtype=float).reshape(1, 3))
    av = np.asarray(avoid_col).reshape(-1) > 0 if avoid_col is not None else None
    cands: list[tuple[float, bool, int]] = []
    for c in owned_here:
        rows = [r for r in clusters[c] if own_col[r]]
        if not rows:
            continue
        dist = float(np.min(scores[rows]))
        if dist > tol:
            continue
        tainted = bool(av is not None
                       and any(av[r] for r in rows if 0 <= r < len(av)))
        cands.append((dist, tainted, c))
    if not cands:
        return None
    clean_ok = av is not None and any(not t for _, t, _ in cands)

    def _rank(t: tuple[float, bool, int]) -> float:
        return t[0] + (_TAINT_PENALTY if (clean_ok and t[1]) else 0.0)

    dist, tainted_win, c = min(cands, key=_rank)
    if tainted_win and clean_ahead is not None:
        ahead = np.asarray(clean_ahead).reshape(-1)
        if 0 <= x < len(ahead) and bool(ahead[x]):
            return None
    best = (dist, c)
    level = float(centroids[best[1]])
    if level < _RESEED_EDGE_PX or level > height - 1 - _RESEED_EDGE_PX:
        return None
    last_y[sid] = level
    last_v[sid] = level
    vel[sid] = 0.0
    return level, best[0]


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


def _remove_steps(seq: list[SeriesSample], tol_px: float,
                  keep: frozenset[int] | set[int] = frozenset()) -> tuple[set[int], int]:
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
    A pair whose both takes are colour-confirmed own ink (``keep``) within
    ``_REACQUIRE_MAX_PX`` is exempt: a steep V bottom or recovery corner
    on real ink trips the isolation test, but confirmed colour proves no
    foreign curve is involved (PMC15 Early Reflections lost its whole dip
    bottom to a refinement overshoot at the exit corner). Hijack jumps
    always land on or leave from foreign ink, so at least one side stays
    unconfirmed and the cut still fires; far same-hue leaps stay exposed
    through the distance bound and Tier 2.
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
        if (i in keep and i + 1 in keep and jump <= _REACQUIRE_MAX_PX):
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
        best = max(range(len(pieces)),
                   key=lambda k: (pieces[k][1] - pieces[k][0], -k))
        for k, (a, b) in enumerate(pieces):
            if k == best or b - a + 1 > _MAX_HIJACK_LEN:
                if k != best:
                    long_kept += 1
                continue
            for t in range(a, b + 1):
                seq[t].status = SegmentStatus.MISSING
                demoted.add(t)
        i = j + 1
    return demoted, long_kept


_FILL_MAX_GAP = 96
"""Longest run ``curve_continuous`` may bridge.

Per-column slope checks go blind on long gaps (any level change looks
shallow per column), so length itself is capped: dash gaps and dropout
fills measure in the tens of columns, while hundred-column bridges
always join takes on different curves across empty space.
"""

_FILL_SLOPED_BLIND_MAX = 48
"""Longest sloped bridge over columns without merged ink."""

_FILL_FLAT_PX = 10.0
"""Level agreement within which a blind bridge counts as flat."""

_FILL_MIN_COVER = 0.6
"""Merged-ink cover fraction along the bridge path that counts as seen.

A sloped bridge over seen ink follows a dropout inside a rolloff; the
same slope over empty space is a guess, and only short ones (steep
rolloffs) or flat ones (dash gaps on a level line) are safe to draw.
"""


def _fill_continuous(seq: list[SeriesSample],
                     skip: frozenset[int] | set[int] = frozenset(),
                     clusters_at=None) -> tuple[int, int, int]:
    """Linearly bridge interior non-OBSERVED runs flanked by OBSERVED samples.

    Filled samples become INTERPOLATED, never OBSERVED, so measurement stays
    distinguishable from inference in the canonical document. Leading and
    trailing gaps stay MISSING: continuity cannot invent endpoints. Runs
    containing ``skip`` indices (identity breaks rejected by ``no_jump``
    step demotion) are left MISSING: bridging them would fabricate a ramp
    across an ambiguous identity. Runs past ``_FILL_MAX_GAP`` are left
    MISSING: the flanks sit on different curves. Over merged ink (cover
    fraction from ``clusters_at`` past ``_FILL_MIN_COVER``) the flank
    slope check decides; over empty space only flat (``_FILL_FLAT_PX``)
    or short (``_FILL_SLOPED_BLIND_MAX``) bridges draw. A bridge steeper
    than ``_STEP_ISOLATION`` times the steepest flank slope (floored at
    ``_BRIDGE_FLOOR_PX`` per column) is likewise refused: flat flanks
    promise a flat truth, so a dropout re-emerging far away on another
    curve stays a hole instead of becoming a drawn cliff — while a dropout
    inside a steep rolloff still fills via flank support. Returns (filled
    samples, bridged gaps, refused bridges).
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
            length = j - i
            v0, v1 = seq[i - 1].v, seq[j].v
            blind = False
            if clusters_at is not None:
                span = j - i + 1
                covered = 0
                for t in range(i, j):
                    frac = (t - i + 1) / span
                    if _is_covered(clusters_at(t), v0 + frac * (v1 - v0),
                                   _BRIDGE_COVER_TOL_PX):
                        covered += 1
                blind = covered / length < _FILL_MIN_COVER
            if length > _FILL_MAX_GAP:
                refused += 1
            elif (blind and length > _FILL_SLOPED_BLIND_MAX
                    and abs(v1 - v0) > _FILL_FLAT_PX):
                refused += 1
            else:
                lo = abs(seq[i - 1].v - seq[i - 2].v) if i >= 2 and obs[i - 2] else 0.0
                hi = abs(seq[j + 1].v - seq[j].v) if j + 1 < n and obs[j + 1] else 0.0
                slope = abs(v1 - v0) / (j - i + 1)
                if slope <= _STEP_ISOLATION * max(lo, hi, _BRIDGE_FLOOR_PX):
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
                             tol_px: float,
                             confirmed: dict[str, set[int]] | None = None,
                             ) -> dict[str, set[int]]:
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
    untouched. Samples whose takes are colour-confirmed own ink
    (``confirmed``) are never demoted: coincidence of two confirmed
    tracks is a genuine merge, and a hijack always lands on or leaves
    from foreign ink, so at least its take side stays unconfirmed.
    Samples must share the column grid. Demoted spans stay
    MISSING (never interpolated): the ink belongs to the other series.
    Returns demoted indices per series.
    """
    sids = sorted(tracks)
    demoted: dict[str, set[int]] = {sid: set() for sid in sids}
    confirmed = confirmed or {}
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
                                confirmed.get(sids[ia], frozenset()),
                                confirmed.get(sids[ib], frozenset()),
                                demoted[sids[ia]], demoted[sids[ib]])
                i = j + 1
    return demoted


def _judge_ride(a: SeriesResult, oa: list[bool], b: SeriesResult, ob: list[bool],
                i: int, j: int, n: int, tol_px: float,
                conf_a: frozenset[int] | set[int],
                conf_b: frozenset[int] | set[int],
                dem_a: set[int], dem_b: set[int]) -> None:
    """Demote whichever claimant's extended ride shows an unexcused cliff."""
    for series, obs, conf, dem in ((a, oa, conf_a, dem_a), (b, ob, conf_b, dem_b)):
        l, r = _extend_ride(series.samples, obs, i, j, tol_px)
        states = {_edge_state(series.samples, obs, l, -1, tol_px),
                  _edge_state(series.samples, obs, r, +1, tol_px)}
        pristine = (l == 0) or (r == n - 1)
        if "cliff" in states and "smooth" not in states and not pristine:
            for t in range(l, r + 1):
                if series.samples[t].status in _DRAWN and t not in conf:
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


_MERGE_RANK = {
    SegmentStatus.OBSERVED: 4,
    SegmentStatus.INFERRED_OCCLUSION: 3,
    SegmentStatus.INFERRED_DASH_GAP: 3,
    SegmentStatus.INTERPOLATED: 2,
    SegmentStatus.AMBIGUOUS: 1,
    SegmentStatus.MISSING: 0,
}
"""Status priority for directional merge: measured beats inferred."""

_NEEDS_BACKWARD_GAP = 12
"""Backward pass runs only past this unexplained gap: short holes bridge
exactly, while long losses (overlap, haze latch) may re-acquire from the
right. Matches the tracker's own lost horizon."""

_AGREE_TOL_PX = 8.0
_AGREE_MIN_COLUMNS = 10
_AGREE_MIN_FRACTION = 0.3
"""Backward acceptance: on mutually observed columns the passes must
agree within tolerance a substantial fraction of the time, or the
backward track followed a different attractor (legend latch, haze)
and is rejected wholesale."""

_DENSITY_MARGIN = 3
"""Neighbourhood-density tie-break margin: the sparser side wins ties
only on a clear observed majority, so single-column density noise
cannot flip adjacent columns opposite ways (sawtooth)."""


def _needs_backward(tr: SeriesResult) -> bool:
    """True when the forward track leaves a long unexplained gap.

    Occluded runs need nothing (the same ink covers the backward pass),
    but missing/interpolated/ambiguous runs may resolve from the other
    side, where the prediction approaches the evidence instead of
    drifting from a stale loss.
    """
    gap = 0
    for s in tr.samples:
        if s.status in (SegmentStatus.MISSING, SegmentStatus.INTERPOLATED,
                        SegmentStatus.AMBIGUOUS):
            gap += 1
            if gap >= _NEEDS_BACKWARD_GAP:
                return True
        else:
            gap = 0
    return False


def _flip_layers_horizontal(layers: EvidenceLayers, sid: str | None = None,
                            ) -> EvidenceLayers:
    """Mirror evidence left-right for a backward tracking pass."""
    from dataclasses import replace
    masks = {k: np.ascontiguousarray(np.fliplr(m))
             for k, m in layers.curve_masks.items()
             if sid is None or k == sid}
    union = (np.ascontiguousarray(np.fliplr(layers.union_mask))
             if layers.union_mask is not None else None)
    return replace(layers, curve_masks=masks, union_mask=union,
                   grid_mask=np.ascontiguousarray(np.fliplr(layers.grid_mask)),
                   provenance=dict(layers.provenance))


def _flip_series_back(res: SeriesResult, w: int) -> SeriesResult:
    """Flip a backward track to forward column order."""
    from dataclasses import replace
    n = len(res.samples)
    samples = [replace(s, u=(w - 1.0) - s.u) for s in reversed(res.samples)]
    alts = [[replace(s, u=(w - 1.0) - s.u) for s in reversed(alt)]
            for alt in res.alternatives]
    return SeriesResult(
        series_id=res.series_id, panel_id=res.panel_id, label=res.label,
        axis_id=res.axis_id, samples=samples, alternatives=alts,
        review_reasons=[r + " (reversed pass)" for r in res.review_reasons],
        confirmed={n - 1 - i for i in res.confirmed},
    )


def merge_track_directions(fwd: dict[str, SeriesResult],
                           bwd: dict[str, SeriesResult], w: int,
                           ) -> dict[str, SeriesResult]:
    """Merge forward and flipped-backward tracks column by column.

    Curves have no direction: a forward loss (overlap, latch) often
    re-acquires cleanly from the right. Per column the better sample
    wins by status rank, then colour confirmation, then observed density
    of its neighbourhood (an observation embedded in an observed run
    beats an isolated one), else forward, so complete forward tracks
    pass through byte-identical.
    """
    merged: dict[str, SeriesResult] = {}
    for sid, ftr in fwd.items():
        btr = bwd.get(sid)
        if btr is None or len(btr.samples) != len(ftr.samples):
            merged[sid] = ftr
            continue
        n = len(ftr.samples)
        fobs = [i for i, s in enumerate(ftr.samples)
                if s.status is SegmentStatus.OBSERVED]
        bobs = [i for i, s in enumerate(btr.samples)
                if s.status is SegmentStatus.OBSERVED]
        fdense = [0] * n
        bdense = [0] * n
        for i in fobs:
            for j in range(max(0, i - 5), min(n, i + 6)):
                fdense[j] += 1
        for i in bobs:
            for j in range(max(0, i - 5), min(n, i + 6)):
                bdense[j] += 1
        samples: list[SeriesSample] = []
        confirmed: set[int] = set()
        n_bwd = 0
        for i in range(n):
            fs, bs = ftr.samples[i], btr.samples[i]
            fr, br = _MERGE_RANK[fs.status], _MERGE_RANK[bs.status]
            if br > fr:
                pick, ci = bs, i in btr.confirmed
                n_bwd += 1
            elif fr > br:
                pick, ci = fs, i in ftr.confirmed
            elif (fs.status is SegmentStatus.OBSERVED
                    and (i in btr.confirmed) != (i in ftr.confirmed)):
                if i in btr.confirmed:
                    pick, ci = bs, True
                    n_bwd += 1
                else:
                    pick, ci = fs, True
            elif bdense[i] >= fdense[i] + _DENSITY_MARGIN:
                pick, ci = bs, i in btr.confirmed
                n_bwd += 1
            else:
                pick, ci = fs, i in ftr.confirmed
            samples.append(pick)
            if ci:
                confirmed.add(i)
        reasons = list(ftr.review_reasons) + list(btr.review_reasons)
        if n_bwd:
            reasons.append(f"bidirectional merge: {n_bwd} of {n} samples "
                           "from reversed pass")
        merged[sid] = SeriesResult(
            series_id=ftr.series_id, panel_id=ftr.panel_id, label=ftr.label,
            axis_id=ftr.axis_id, samples=samples,
            alternatives=list(ftr.alternatives) + list(btr.alternatives),
            review_reasons=reasons, confirmed=confirmed)
    return merged


def track_sid_bidirectional(
    gray: npt.NDArray,
    layers: EvidenceLayers,
    sid: str,
    bg_value: float,
    config: TrackConfig | None = None,
    series_colors: dict[str, tuple[int, int, int]] | None = None,
    color_img: npt.NDArray | None = None,
    foreign_avoid: dict[str, npt.NDArray] | None = None,
) -> dict[str, SeriesResult]:
    """Track one series forward, plus backward past long forward gaps.

    The backward pass mirrors every input, tracks, flips back, and merges
    by status rank (see :func:`merge_track_directions`). Complete forward
    tracks skip the second pass entirely.
    """
    if config is not None and config.backend == "temporal":
        return track_panel(gray, layers, [sid], bg_value, config, series_colors,
                           color_img, foreign_avoid)
    fwd = track_panel(gray, layers, [sid], bg_value, config, series_colors,
                      color_img, foreign_avoid)
    if sid not in fwd or not _needs_backward(fwd[sid]):
        return fwd
    h, w = gray.shape[:2]
    gray_f = np.ascontiguousarray(np.fliplr(gray))
    color_f = (np.ascontiguousarray(np.fliplr(color_img))
               if color_img is not None else None)
    layers_f = _flip_layers_horizontal(layers, sid)
    # The backward union must stay global: subsetting it to the series
    # would blind coverage and seeding, so the full flipped union rides.
    if layers.union_mask is None:
        layers_f = _flip_layers_horizontal(layers, None)
    if foreign_avoid is not None and sid in foreign_avoid:
        avoid_f = {sid: np.ascontiguousarray(
            np.fliplr(np.asarray(foreign_avoid[sid])))}
    else:
        avoid_f = None
    bwd = track_panel(gray_f, layers_f, [sid], bg_value, config,
                      series_colors, color_f, avoid_f)
    if sid not in bwd:
        return fwd
    back = _flip_series_back(bwd[sid], w)
    agree = mutual = 0
    for fs, bs in zip(fwd[sid].samples, back.samples):
        if (fs.status is SegmentStatus.OBSERVED
                and bs.status is SegmentStatus.OBSERVED):
            mutual += 1
            if abs(fs.v - bs.v) <= _AGREE_TOL_PX:
                agree += 1
    if mutual >= _AGREE_MIN_COLUMNS and agree / mutual < _AGREE_MIN_FRACTION:
        fwd[sid].review_reasons.append(
            f"reversed pass diverged ({agree}/{mutual} mutually observed "
            "columns agree); kept forward")
        return fwd
    return merge_track_directions(fwd, {sid: back}, w)


def maybe_smooth(values: list[float], window: int) -> list[float]:
    """Explicit opt-in smoothing for display previews; never part of measurement."""
    if window <= 0 or len(values) < window:
        return list(values)
    from scipy.signal import savgol_filter

    return [float(v) for v in savgol_filter(np.array(values), window, 2)]
