# -*- coding: utf-8 -*-
"""Tests for colour-aware joint assignment in tracking.py.

A pastel curve colour can match achromatic grid pixels through foreground /
background unmixing, so the evidence mask contains full-width grid rows
alongside the curve. Pure-motion assignment then locks onto the perfectly
motion-continuous grid at the first column and never recovers (the stale
prediction vetoes every jump back). Colour-aware costs make the initial
commitment and stale-track recovery follow evidence carrying the series'
own colour, while pure-motion callers observe byte-identical behaviour.
"""

import cv2
import numpy as np
import pytest

from graphextract.evidence import EvidenceLayers, StyleSpec, segment_evidence
from graphextract.schema import SegmentStatus, SeriesResult, SeriesSample
from graphextract.tracking import (
    KNOWN_ASSUMPTIONS,
    TrackConfig,
    _backfill_occluded,
    _bridge_occluded,
    _is_covered,
    _joint_assignment,
    _live_obs,
    _recover_rows,
    _remove_steps,
    resolve_duplicate_claims,
    track_panel,
)


def _dup_tracks(specs):
    """Hand-built single-grid tracks: {sid: [v | None per column]}."""
    tracks = {}
    for sid, vals in specs.items():
        samples = []
        for i, v in enumerate(vals):
            if v is None:
                samples.append(SeriesSample(u=float(i), v=0.0,
                                           status=SegmentStatus.MISSING))
            else:
                samples.append(SeriesSample(u=float(i), v=float(v),
                                           status=SegmentStatus.OBSERVED))
        tracks[sid] = SeriesResult(sid, "p", sid, "y_left", samples)
    return tracks

RED = (0, 0, 255)
BLUE = (255, 0, 0)


def _track(img, styles, series_id, colours, config=None):
    layers = segment_evidence(img, styles)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bg = float(np.median(gray))
    return track_panel(gray, layers, [series_id], bg, config, colours, img)[series_id]


def _diagonal():
    return 220.0, (20.0 - 220.0) / 300.0  # v0 at u=10, slope per column


def _diag_v(u):
    v0, slope = _diagonal()
    return v0 + (u - 10.0) * slope


def _spike_image():
    """Red diagonal with a same-colour vertical bar hanging off it at x=160.

    The bar merges with the diagonal stroke, so default tracking rides the
    merged centroid — a vertical jump artifact of the kind ``no_jump`` removes.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 220), (310, 20), RED, 3)
    cv2.line(img, (160, 118), (160, 220), RED, 2)
    return img


def _pastel_grid_image():
    """Pastel green diagonal over a full-width grey gridline.

    The green matches the grey through unmixing (as on CTA-2034 renders),
    so the mask holds both; the diagonal starts at x=10, leaving a
    grid-only lead-in where honest tracking reports missing.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    img[120:122, :] = (213, 213, 213)
    cv2.line(img, (10, 220), (310, 20), (100, 171, 67), 3)
    return img


def test_color_assignment_prefers_own_curve_over_grid():
    img = _pastel_grid_image()
    style = StyleSpec("g", "G", (100, 171, 67))
    layers = segment_evidence(img, [style])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bg = float(np.median(gray))
    track = track_panel(gray, layers, ["g"], bg, None, {"g": (100, 171, 67)}, img)["g"]
    observed = [s for s in track.samples if s.status is SegmentStatus.OBSERVED]
    assert len(observed) > 250
    # No commitment in the grid-only lead-in before the curve starts.
    assert observed[0].u >= 5
    # Observed positions ride the diagonal, not the grid row at v=120.
    errors = [abs(s.v - (220.0 + (s.u - 10.0) * (20.0 - 220.0) / 300.0))
              for s in observed]
    assert sum(errors) / len(errors) < 4.0


def test_seed_waits_for_own_colour_evidence():
    """Identity commits on colour evidence, not on the first owned column.

    The series' own ink starts at x=20 while admitted foreign fringe spans
    the full width (as navy fringe admitted to PMC12 On Axis). Latching
    the fringe at column zero rides it forever — colour only mildly
    penalises, motion keeps it — so commitment must wait for the
    best-colour evidence inside the seed window.
    """
    teal = (125, 88, 36)  # BGR series colour
    navy = (68, 53, 20)  # BGR foreign fringe, colour distance ~69
    h, w = 120, 64
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.line(img, (0, 80), (w - 1, 80), navy, 3)
    cv2.line(img, (20, 50), (w - 1, 50), teal, 3)
    mask = np.zeros((h, w), np.uint8)
    mask[77:84, :] = 255  # admitted foreign fringe, full width
    mask[47:54, 20:] = 255  # own ink from x=20
    layers = EvidenceLayers(curve_masks={"t": mask},
                            grid_mask=np.zeros((h, w), np.uint8),
                            background_bgr=(255, 255, 255))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    track = track_panel(gray, layers, ["t"], float(np.median(gray)),
                        None, {"t": teal}, img)["t"]
    observed = [s for s in track.samples if s.status is SegmentStatus.OBSERVED]
    assert observed, "own ink never committed"
    assert observed[0].u >= 20, observed[0]
    assert all(abs(s.v - 50.0) < 4.0 for s in observed if s.u >= 20)


def test_seed_prefers_early_good_match_over_later_best():
    """Crowded edges must not defer commitment past real observations.

    Own ink spans the full width but reads slightly mixed near the plot
    edge (colour distance ~6) and exact later (~1), with foreign fringe
    throughout. Commitment fires on the first excellent column instead of
    waiting for the global best.
    """
    teal = (125, 88, 36)  # BGR series colour
    edge = (128, 92, 40)  # BGR slightly mixed edge ink, distance ~6
    navy = (68, 53, 20)  # BGR foreign fringe, colour distance ~69
    h, w = 120, 64
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.line(img, (0, 80), (w - 1, 80), navy, 3)
    cv2.line(img, (0, 50), (11, 50), edge, 3)
    cv2.line(img, (12, 50), (w - 1, 50), teal, 3)
    mask = np.zeros((h, w), np.uint8)
    mask[77:84, :] = 255
    mask[47:54, :] = 255
    layers = EvidenceLayers(curve_masks={"t": mask},
                            grid_mask=np.zeros((h, w), np.uint8),
                            background_bgr=(255, 255, 255))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    track = track_panel(gray, layers, ["t"], float(np.median(gray)),
                        None, {"t": teal}, img)["t"]
    observed = [s for s in track.samples if s.status is SegmentStatus.OBSERVED]
    assert observed, "own ink never committed"
    assert observed[0].u <= 2, observed[0]
    assert all(abs(s.v - 50.0) < 4.0 for s in observed)


def test_tracking_without_colors_matches_legacy_motion():
    """Callers that pass no colours get pure-motion tracking (this also
    pins the legacy default for every existing direct caller)."""
    img = _pastel_grid_image()
    style = StyleSpec("g", "G", (100, 171, 67))
    layers = segment_evidence(img, [style])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bg = float(np.median(gray))
    plain = track_panel(gray, layers, ["g"], bg)["g"]
    assert plain.series_id == "g"
    assert len(plain.samples) == img.shape[1]


def test_known_assumptions_match_config_fields():
    assert set(KNOWN_ASSUMPTIONS) == {"curve_continuous", "no_jump", "assume_overlap"}
    cfg = TrackConfig.from_assumptions(KNOWN_ASSUMPTIONS)
    assert cfg.active_assumptions() == list(KNOWN_ASSUMPTIONS)
    with pytest.raises(ValueError, match="unknown assumption"):
        TrackConfig.from_assumptions(["telepathy"])


def test_no_jump_demotes_vertical_spike_to_missing():
    img = _spike_image()
    styles = [StyleSpec("r", "R", RED)]
    colours = {"r": RED}
    default = _track(img, styles, "r", colours)
    # Authentic failure first: default tracking rides the merged centroid off
    # the diagonal at the bar columns.
    spike = [s for s in default.samples
             if s.status is SegmentStatus.OBSERVED and 157 <= s.u <= 163]
    assert spike
    assert max(abs(s.v - _diag_v(s.u)) for s in spike) > 20.0

    cleaned = _track(img, styles, "r", colours, TrackConfig(no_jump=True))
    by_u = {int(s.u): s for s in cleaned.samples}
    assert all(by_u[u].status is SegmentStatus.MISSING for u in range(159, 162))
    observed = [s for s in cleaned.samples if s.status is SegmentStatus.OBSERVED]
    errors = [abs(s.v - _diag_v(s.u)) for s in observed]
    assert sum(errors) / len(errors) < 4.0
    assert any("no_jump" in r for r in cleaned.review_reasons)


def test_remove_jumps_demotes_isolated_spike():
    """Hampel pass demotes an isolated observed spike to missing."""
    from graphextract.tracking import _remove_jumps
    seq = _obs_seq([100.0] * 10 + [130.0] + [100.0] * 10)
    assert _remove_jumps(seq, 10.0) == 1
    assert seq[10].status is SegmentStatus.MISSING
    assert all(s.status is SegmentStatus.OBSERVED
               for i, s in enumerate(seq) if i != 10)


def _gapped_line_image():
    """Red horizontal with a blank 20-column gap; nothing to hide behind."""
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 120), (99, 120), RED, 3)
    cv2.line(img, (120, 120), (310, 120), RED, 3)
    return img


def test_curve_continuous_bridges_interior_gap_only():
    img = _gapped_line_image()
    styles = [StyleSpec("r", "R", RED)]
    colours = {"r": RED}
    default = _track(img, styles, "r", colours)
    assert all(s.status is SegmentStatus.MISSING
               for s in default.samples if 102 <= s.u < 118)

    bridged = _track(img, styles, "r", colours, TrackConfig(curve_continuous=True))
    inner = [s for s in bridged.samples if 102 <= s.u < 118]
    assert inner
    assert all(s.status is SegmentStatus.INTERPOLATED for s in inner)
    assert all(abs(s.v - 120.0) < 2.0 for s in inner)
    # Continuity cannot invent endpoints: the lead-in stays missing
    # (evidence bleed starts the observed run at u=8).
    assert all(s.status is SegmentStatus.MISSING for s in bridged.samples if s.u < 8)
    assert not any(s.status is SegmentStatus.OBSERVED for s in inner)
    assert any("curve_continuous" in r for r in bridged.review_reasons)


def _overlap_image(with_cover):
    """Red line with a gap at x in [50, 70); optional blue cover over the gap."""
    img = np.full((240, 320, 3), 255, np.uint8)
    if with_cover:
        cv2.line(img, (40, 100), (80, 100), BLUE, 3)
    cv2.line(img, (10, 100), (49, 100), RED, 3)
    cv2.line(img, (70, 100), (110, 100), RED, 3)
    return img


def test_assume_overlap_continues_hidden_track_under_merged_ink():
    styles = [StyleSpec("r", "R", RED), StyleSpec("b", "B", BLUE)]
    colours = {"r": RED}
    img = _overlap_image(with_cover=True)
    default = _track(img, styles, "r", colours)
    assert all(s.status is SegmentStatus.MISSING
               for s in default.samples if 54 <= s.u <= 66)

    kept = _track(img, styles, "r", colours, TrackConfig(assume_overlap=True))
    inner = [s for s in kept.samples if 54 <= s.u <= 66]
    assert inner
    assert all(s.status is SegmentStatus.INFERRED_OCCLUSION for s in inner)
    assert all(abs(s.v - 100.0) < 3.0 for s in inner)
    # Identity survives the merge: observed red resumes on both sides.
    assert any(s.status is SegmentStatus.OBSERVED for s in kept.samples if s.u < 50)
    assert any(s.status is SegmentStatus.OBSERVED for s in kept.samples if s.u > 70)
    assert any("assume_overlap" in r for r in kept.review_reasons)


def test_assume_overlap_keeps_true_gaps_missing():
    """No ink over the gap means nothing to hide behind: still missing."""
    img = _overlap_image(with_cover=False)
    styles = [StyleSpec("r", "R", RED)]
    kept = _track(img, styles, "r", colours={"r": RED},
                  config=TrackConfig(assume_overlap=True))
    assert all(s.status is SegmentStatus.MISSING
               for s in kept.samples if 54 <= s.u <= 66)
    assert kept.review_reasons == []


def _buried_start_image():
    """Blue cover line from x=10; red only emerges from under it at x=70."""
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 100), (110, 100), BLUE, 3)
    cv2.line(img, (70, 100), (110, 100), RED, 3)
    return img


def test_assume_overlap_backfills_buried_lead_in():
    """A curve buried under merged ink from the first column has no motion
    prior, so forward occlusion never engages: the lead-in stays missing
    without the flag and is backfilled as occlusion with it."""
    styles = [StyleSpec("r", "R", RED), StyleSpec("b", "B", BLUE)]
    colours = {"r": RED}
    img = _buried_start_image()
    default = _track(img, styles, "r", colours)
    lead = [s for s in default.samples if s.u < 60]
    assert lead
    assert all(s.status is SegmentStatus.MISSING for s in lead)

    kept = _track(img, styles, "r", colours, TrackConfig(assume_overlap=True))
    inner = [s for s in kept.samples if 20 <= s.u <= 55]
    assert inner
    assert all(s.status is SegmentStatus.INFERRED_OCCLUSION for s in inner)
    assert all(abs(s.v - 100.0) < 4.0 for s in inner)
    # Nothing to hide behind before the cover starts: still missing.
    assert all(s.status is SegmentStatus.MISSING for s in kept.samples if s.u < 8)
    assert any("assume_overlap" in r for r in kept.review_reasons)


def _short_cover_image():
    """Blue cover only spans x=[40, 80]; red emerges from under it at x=70."""
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (40, 100), (80, 100), BLUE, 3)
    cv2.line(img, (70, 100), (110, 100), RED, 3)
    return img


def test_assume_overlap_backfill_stops_where_cover_ends():
    """The backward walk stops at empty columns instead of inventing ink."""
    styles = [StyleSpec("r", "R", RED), StyleSpec("b", "B", BLUE)]
    colours = {"r": RED}
    kept = _track(_short_cover_image(), styles, "r", colours,
                  TrackConfig(assume_overlap=True))
    inner = [s for s in kept.samples if 45 <= s.u <= 64]
    assert inner
    assert all(s.status is SegmentStatus.INFERRED_OCCLUSION for s in inner)
    assert all(s.status is SegmentStatus.MISSING for s in kept.samples if s.u < 38)


def _stale_cover_image():
    """Red ends at x=50; blue holds red's level to x=80, then dives away."""
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 100), (150, 100), BLUE, 3)
    cv2.line(img, (80, 100), (110, 140), BLUE, 3)
    cv2.line(img, (110, 140), (150, 140), BLUE, 3)
    cv2.line(img, (10, 100), (49, 100), RED, 3)
    return img


def test_assume_overlap_stops_coasting_stale_predictions():
    """Dead reckoning ends where freshness ends, not where cover ends.

    Blue holds red's level long after red's ink ends, then dives away.
    Coasting the frozen prediction under that foreign cover fabricates a
    flat line (PMC10-4 Early Reflections drifted 25 dB off); past the
    lost threshold the honest answer is missing.
    """
    styles = [StyleSpec("r", "R", RED), StyleSpec("b", "B", BLUE)]
    kept = _track(_stale_cover_image(), styles, "r", {"r": RED},
                  TrackConfig(assume_overlap=True))
    assert any(s.status is SegmentStatus.OBSERVED for s in kept.samples if s.u < 50)
    fresh = [s for s in kept.samples if 54 <= s.u <= 60]
    assert fresh
    assert all(s.status is SegmentStatus.INFERRED_OCCLUSION for s in fresh)
    # Blue still covers the frozen level here: only the freshness gate
    # keeps these missing instead of coasting.
    stale = [s for s in kept.samples if 64 <= s.u <= 78]
    assert stale
    assert all(s.status is SegmentStatus.MISSING for s in stale)
    assert any("assume_overlap" in r for r in kept.review_reasons)


def test_is_covered_matches_forward_occlusion_rule():
    assert _is_covered([[98, 99, 100, 101]], 100.0, 1.0)
    assert not _is_covered([], 100.0, 1.0)
    assert not _is_covered([[90], [110]], 100.0, 1.0)
    # Partially merged bundles split into adjacent clusters still cover.
    assert _is_covered([[98, 99, 100], [103, 104, 105]], 101.0, 1.0)
    # Adjacent rows count as covering even with zero tolerance: pixel rows
    # are unit samples while tracked levels are continuous, so a level
    # sitting exactly between two ink rows is half a pixel from ink. This
    # ±1px rule is what makes the predicate mirror forward occlusion.
    assert _is_covered([[98, 99, 100], [103, 104, 105]], 101.0, 0.0)


def _flat_seq(n_before, n_obs, v=100.0):
    seq = [SeriesSample(u=float(i), v=0.0, status=SegmentStatus.MISSING)
           for i in range(n_before)]
    seq += [SeriesSample(u=float(n_before + i), v=v, status=SegmentStatus.OBSERVED)
            for i in range(n_obs)]
    return seq


def test_backfill_walks_every_observed_block():
    """Each observed block extends left independently; earlier blocks are
    never overwritten."""
    seq = _flat_seq(10, 6)  # observed block at 10..15
    seq[4] = SeriesSample(u=4.0, v=100.0, status=SegmentStatus.OBSERVED)
    seq[5] = SeriesSample(u=5.0, v=100.0, status=SegmentStatus.OBSERVED)
    filled = _backfill_occluded(seq, lambda x: [[98, 99, 100, 101]])  # noqa: E731
    assert filled == 8  # 9..6 from the later block, 3..0 from the earlier
    assert all(seq[i].status is SegmentStatus.INFERRED_OCCLUSION
               for i in list(range(0, 4)) + list(range(6, 10)))
    assert all(seq[i].status is SegmentStatus.OBSERVED
               for i in (4, 5, 10, 11, 12, 13, 14, 15))


def test_backfill_follows_motion_not_centroid():
    """Backfilled positions extrapolate block motion; a wide covering
    cluster gates but never pulls the level."""
    seq = [SeriesSample(u=float(i), v=0.0, status=SegmentStatus.MISSING)
           for i in range(10)]
    seq += [SeriesSample(u=10.0, v=100.0, status=SegmentStatus.OBSERVED),
            SeriesSample(u=11.0, v=98.0, status=SegmentStatus.OBSERVED),
            SeriesSample(u=12.0, v=96.0, status=SegmentStatus.OBSERVED)]
    filled = _backfill_occluded(seq, lambda x: [[100, 101, 102]])  # noqa: E731
    assert filled == 3
    assert seq[9].status is SegmentStatus.INFERRED_OCCLUSION
    # Motion (102, 104, 106), not the cluster centroid (101.0).
    assert seq[9].v == 102.0
    assert seq[8].v == 104.0
    assert seq[7].v == 106.0


def _skip_seq():
    seq = [SeriesSample(u=float(i), v=100.0, status=SegmentStatus.OBSERVED)
           for i in range(5)]
    seq += [SeriesSample(u=float(5 + i), v=0.0, status=SegmentStatus.MISSING)
            for i in range(10)]
    seq += [SeriesSample(u=float(15 + i), v=100.0, status=SegmentStatus.OBSERVED)
            for i in range(5)]
    return seq, set(range(5, 15))


def test_bridge_occluded_fills_covered_skip_run():
    seq, skip = _skip_seq()
    filled = _bridge_occluded(seq, skip, lambda t: [[98, 99, 100, 101]])  # noqa: E731
    assert filled == 10
    assert all(s.status is SegmentStatus.INFERRED_OCCLUSION for s in seq[5:15])
    assert all(s.v == 100.0 for s in seq[5:15])
    assert all(s.status is SegmentStatus.OBSERVED for s in seq[:5] + seq[15:])


def test_bridge_occluded_refuses_uncovered_run():
    seq, skip = _skip_seq()
    filled = _bridge_occluded(seq, skip, lambda t: [])  # noqa: E731
    assert filled == 0
    assert all(s.status is SegmentStatus.MISSING for s in seq[5:15])


def test_bridge_occluded_refuses_steep_bridge_with_flat_flanks():
    """Covered or not, a steep bridge between flat flanks is an identity
    break, not a burial: leave it missing."""
    seq, skip = _skip_seq()
    for s in seq[15:]:
        s.v = 200.0
    filled = _bridge_occluded(seq, skip, lambda t: [[0, 250]])  # noqa: E731
    assert filled == 0
    assert all(s.status is SegmentStatus.MISSING for s in seq[5:15])


def test_bridge_occluded_ignores_runs_without_skip():
    """Plain missing runs are curve_continuous territory, not the bridge's."""
    seq, _skip = _skip_seq()
    filled = _bridge_occluded(seq, frozenset(), lambda t, v, tol: 100.0)  # noqa: E731
    assert filled == 0
    assert all(s.status is SegmentStatus.MISSING for s in seq[5:15])


def _obs_seq(values):
    return [SeriesSample(u=float(i), v=float(v), status=SegmentStatus.OBSERVED)
            for i, v in enumerate(values)]


def test_remove_steps_demotes_short_side_of_isolated_cliff():
    # Startup hijack shape: 5 samples on merged ink, then the true level.
    seq = _obs_seq([100.0] * 5 + [70.0] * 20)
    idx, long_kept = _remove_steps(seq, 10.0)
    assert idx == set(range(5))
    assert long_kept == 0
    assert [s.status for s in seq[:5]] == [SegmentStatus.MISSING] * 5
    assert all(s.status is SegmentStatus.OBSERVED for s in seq[5:])


def test_remove_steps_keeps_steep_smooth_slopes_and_knees():
    seq = _obs_seq([16.0 * i for i in range(30)])
    assert _remove_steps(seq, 10.0) == (set(), 0)
    assert all(s.status is SegmentStatus.OBSERVED for s in seq)
    # Abrupt but sustained steepening is a knee, not a step.
    seq = _obs_seq([1.0 * i for i in range(5)] + [5.0 + 16.0 * i for i in range(10)])
    assert _remove_steps(seq, 10.0) == (set(), 0)


def test_remove_steps_keeps_lone_pairs_and_respects_missing():
    seq = _obs_seq([0.0, 50.0])
    assert _remove_steps(seq, 10.0) == (set(), 0)
    seq = _obs_seq([100.0] * 4)
    seq[2].status = SegmentStatus.MISSING
    assert _remove_steps(seq, 10.0) == (set(), 0)


def test_remove_steps_exempts_colour_confirmed_pairs():
    """A steep corner on confirmed own ink is a V bottom, not a hijack.

    PMC15 Early Reflections: takes ride the true dip down and out, with a
    refinement overshoot at the exit corner tripping the isolation test.
    Demoting the shorter side would delete the whole dip bottom, so pairs
    whose both takes are colour-confirmed survive. One unconfirmed side
    still convicts, and far leaps stay exposed through the distance bound.
    """
    dip = [100.0] * 10 + [94.0, 88.0, 82.0, 76.0, 70.0, 70.0, 83.0] + [83.0] * 10
    # The +13 exit corner (pair 15->16) trips the isolation test, so the
    # shorter recovery side goes without an exemption.
    seq = _obs_seq(dip)
    idx, _ = _remove_steps(seq, 10.0)
    assert idx == set(range(16, 27))
    seq = _obs_seq(dip)
    idx, _ = _remove_steps(seq, 10.0, frozenset({15, 16}))
    assert idx == set()
    assert all(s.status is SegmentStatus.OBSERVED for s in seq)
    # Only one side confirmed: the cut still fires.
    seq = _obs_seq(dip)
    idx, _ = _remove_steps(seq, 10.0, frozenset({15}))
    assert idx == set(range(16, 27))
    # Far leap even when confirmed: Tier 2 (which has no exemption) still
    # demotes the staircase foot neighbourhood.
    seq = _obs_seq([730.0] * 30 + [951.0, 1044.0] + [1144.0] * 30)
    idx, _ = _remove_steps(seq, 10.0, frozenset({30, 31, 32, 33}))
    assert 30 in idx and 31 in idx


def test_remove_steps_keeps_sustained_swap_for_review():
    # Long-vs-long single step: demoting either side could destroy true
    # data, so both survive and the block is counted as unresolved.
    seq = _obs_seq([100.0] * 200 + [70.0] * 200)
    idx, long_kept = _remove_steps(seq, 10.0)
    assert idx == set()
    assert long_kept == 1
    assert all(s.status is SegmentStatus.OBSERVED for s in seq)


def test_remove_steps_window_demotes_staircase_foot():
    # pmc12 shape in native pixels: consecutive huge jumps shield each
    # other from the isolation rule; the huge one-sided foot jump still
    # fires Tier 2 and its window swallows the staircase treads.
    seq = _obs_seq([730.0] * 30 + [951.0, 1044.0] + [1144.0] * 30)
    idx, _ = _remove_steps(seq, 10.0)
    assert 30 in idx and 31 in idx  # treads demoted via the foot window
    assert all(s.status is SegmentStatus.OBSERVED for s in seq[:24])
    assert all(s.status is SegmentStatus.OBSERVED for s in seq[38:])


def test_fill_continuous_skips_identity_breaks():
    from graphextract.tracking import _fill_continuous
    # Step-demoted span between disagreeing flanks stays missing: bridging
    # it would fabricate a ramp across an ambiguous identity.
    seq = _obs_seq([100.0] * 3 + [0.0] * 3 + [70.0] * 3)
    for s in seq[3:6]:
        s.status = SegmentStatus.MISSING
    filled, _, _ = _fill_continuous(seq, skip={3, 4, 5})
    assert filled == 0
    assert all(s.status is SegmentStatus.MISSING for s in seq[3:6])
    # Same geometry without the skip bridges normally.
    filled, gaps, refused = _fill_continuous(seq)
    assert (filled, gaps, refused) == (3, 1, 0)


def test_fill_continuous_refuses_steep_bridges():
    from graphextract.tracking import _fill_continuous
    # Dropout re-emerging on another curve: flanks flat, bridge absurd
    # (native-pixel scale, as in production).
    seq = _obs_seq([1400.0] * 4 + [0.0] * 2 + [700.0] * 4)
    for s in seq[4:6]:
        s.status = SegmentStatus.MISSING
    filled, gaps, refused = _fill_continuous(seq)
    assert (filled, gaps, refused) == (0, 0, 1)
    # Same gap inside a steep rolloff: flanks support the slope, fill it.
    seq = _obs_seq([float(200 - 16 * i) for i in range(4)] + [0.0] * 2
                   + [float(200 - 16 * i) for i in range(6, 10)])
    for s in seq[4:6]:
        s.status = SegmentStatus.MISSING
    filled, gaps, refused = _fill_continuous(seq)
    assert (filled, gaps, refused) == (2, 1, 0)


def test_duplicate_claim_demotes_cliffed_intruder():
    owner = [70.0] * 40
    intruder = [100.0] * 10 + [70.0] * 20 + [100.0] * 10
    demoted = resolve_duplicate_claims(_dup_tracks({"o": owner, "x": intruder}), 10.0)
    assert demoted["x"] == set(range(10, 30))
    assert demoted["o"] == set()
    tracks = _dup_tracks({"o": owner, "x": intruder})
    resolve_duplicate_claims(tracks, 10.0)
    assert all(s.status is SegmentStatus.MISSING for s in tracks["x"].samples[10:30])
    assert all(s.status is SegmentStatus.OBSERVED for s in tracks["o"].samples)


def test_duplicate_claim_keeps_genuine_merges():
    # Smooth converge, shared run, smooth diverge: nobody cliffed, keep both.
    a = [80.0] * 5 + [78.0, 76.0, 74.0, 72.0] + [70.0] * 20 + [72.0, 74.0, 76.0, 78.0] + [80.0] * 5
    b = [70.0] * 42
    demoted = resolve_duplicate_claims(_dup_tracks({"a": a, "b": b}), 10.0)
    assert demoted == {"a": set(), "b": set()}


def test_duplicate_claim_exempts_colour_confirmed_takes():
    """Colour-confirmed coincidence is a genuine merge, not a hijack.

    PMC10-4's crowded midrange coincides for hundreds of columns with
    ripple cliffs on every side, so the cliff judge mass-demoted true
    takes (597 Early Reflections samples). Takes unmixing within tolerance
    of their own colour are on own ink by construction: both-confirmed
    spans survive whole, and a confirmed owner keeps its ink while only
    the unconfirmed intruder goes.
    """
    owner = [70.0] * 40
    intruder = [100.0] * 10 + [70.0] * 20 + [100.0] * 10
    both = {"o": set(range(40)), "x": set(range(40))}
    demoted = resolve_duplicate_claims(_dup_tracks({"o": owner, "x": intruder}),
                                       10.0, both)
    assert demoted == {"o": set(), "x": set()}
    # Confirmed owner, unconfirmed intruder: only the intruder goes.
    demoted = resolve_duplicate_claims(_dup_tracks({"o": owner, "x": intruder}),
                                       10.0, {"o": set(range(40)), "x": set()})
    assert demoted["x"] == set(range(10, 30))
    assert demoted["o"] == set()
    # Both cliffed (mirrored swap), only one side confirmed: the
    # unconfirmed side goes, the confirmed side stays.
    c = [100.0] * 10 + [70.0] * 20 + [100.0] * 10
    d = [50.0] * 10 + [70.0] * 20 + [50.0] * 10
    demoted = resolve_duplicate_claims(_dup_tracks({"c": c, "d": d}),
                                       10.0, {"c": set(), "d": set(range(40))})
    assert demoted["c"] == set(range(10, 30))
    assert demoted["d"] == set()


def test_duplicate_claim_demotes_mirrored_swaps():
    # Both teleport onto the shared level and off again: both rode the
    # wrong ink through the middle, so both spans go.
    c = [100.0] * 10 + [70.0] * 20 + [100.0] * 10
    d = [50.0] * 10 + [70.0] * 20 + [50.0] * 10
    demoted = resolve_duplicate_claims(_dup_tracks({"c": c, "d": d}), 10.0)
    assert demoted == {"c": set(range(10, 30)), "d": set(range(10, 30))}


def test_duplicate_claim_counts_missing_gap_cliffs_but_not_distant_ones():
    owner = [70.0] * 40
    # 3-column dropout then re-emergence far away: counts as entry cliff.
    intruder = [100.0] * 10 + [None] * 3 + [70.0] * 20 + [100.0] * 7
    demoted = resolve_duplicate_claims(_dup_tracks({"o": owner, "x": intruder}), 10.0)
    assert demoted["x"] == set(range(13, 33))
    # 30-column dropout: distant change is movement, not a cliff; the
    # exit cliff alone still convicts (exactly one side cliffed).
    owner = [70.0] * 50
    intruder = [100.0] * 5 + [None] * 30 + [70.0] * 10 + [100.0] * 5
    demoted = resolve_duplicate_claims(_dup_tracks({"o": owner, "x": intruder}), 10.0)
    assert demoted["x"] == set(range(35, 45))


def test_duplicate_claim_ignores_short_spans():
    owner = [70.0] * 20
    intruder = [100.0] * 8 + [70.0] * 4 + [100.0] * 8
    demoted = resolve_duplicate_claims(_dup_tracks({"o": owner, "x": intruder}), 10.0)
    assert demoted == {"o": set(), "x": set()}


def test_joint_assignment_prefers_stay_on_tied_far_jump():
    """A far cluster tying occlusion on cost loses the tie under no_jump.

    Capped motion makes any jump beyond ``occlusion_penalty`` cost exactly
    as much as going missing; legacy order takes the jump (silent
    teleport onto foreign ink that shares the colour), while the no_jump
    ordering stays missing so the track can re-acquire honestly later.
    Near evidence still captures immediately under both orderings.
    """
    centroids = [100.0]
    clusters = [[98, 99, 100, 101, 102]]
    legacy = _joint_assignment(centroids, clusters, {"r": 0.0}, {"r": {0}}, ["r"], 4, 12.0)
    assert legacy == {"r": 0}
    stayed = _joint_assignment(
        centroids, clusters, {"r": 0.0}, {"r": {0}}, ["r"], 4, 12.0, prefer_stay_on_ties=True
    )
    assert stayed == {"r": None}
    near = _joint_assignment(
        [5.0], [[3, 4, 5, 6, 7]], {"r": 0.0}, {"r": {0}}, ["r"], 4, 12.0,
        prefer_stay_on_ties=True,
    )
    assert near == {"r": 0}


def _colour_column(height, rows, bgr):
    """Single image column: white background with ``rows`` painted ``bgr``."""
    col = np.full((height, 3), 255, np.uint8)
    col[rows] = bgr
    return col


def _take_with_colour(pred, centroid, rows, paint, template, **kwargs):
    """One tied far jump with explicit column colour evidence."""
    height = 240
    masks = {"r": np.zeros(height, dtype=bool)}
    masks["r"][rows] = True
    bg_bgr = kwargs.pop("bg_bgr", (255, 255, 255))
    return _joint_assignment(
        [centroid], [list(rows)], {"r": pred}, {"r": {0}}, ["r"], 4, 12.0,
        owned_masks=masks, color_col=_colour_column(height, rows, paint),
        series_colors={"r": template}, prefer_stay_on_ties=True,
        bg_bgr=bg_bgr, **kwargs)


def test_joint_assignment_recovers_to_colour_confirmed_ink_on_ties():
    """A tied far take still wins when the series' own colour confirms it.

    Merged union clusters park their centroid between nearby strokes, so a
    stale prediction can sit a full penalty past its own ink while the ink
    itself is unambiguous (PMC15 On Axis dived past its teal dip and the
    track never came back). Colour confirmation distinguishes recovery
    from teleport: foreign hues, far leaps, and colour-blind callers keep
    losing the tie and staying missing.
    """
    rows = list(range(98, 103))
    # Own colour 40px away: capped motion ties occlusion, colour breaks it.
    assert _take_with_colour(60.0, 100.0, rows, RED, RED) == {"r": 0}
    # Same tie without unmixing confirmation stays missing.
    assert _take_with_colour(60.0, 100.0, rows, RED, RED,
                             bg_bgr=None) == {"r": None}
    # Foreign hue at the same distance keeps losing the tie.
    assert _take_with_colour(60.0, 100.0, rows, BLUE, RED) == {"r": None}
    # Even confirmed ink stays missing past re-acquisition reach.
    assert _take_with_colour(0.0, 100.0, rows, RED, RED) == {"r": None}


def _hijack_image():
    """Red line, red decoy far below it, red resuming elsewhere.

    The decoy carries the series colour, so legacy assignment teleports
    onto it (same failure as the pmc12 On Axis / Reflections-DI confusion,
    where two navy curves share one colour identity). The resuming line
    sits beyond instant-capture reach, so only delayed re-acquisition
    brings the track back.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 100), (60, 100), RED, 3)
    cv2.line(img, (70, 200), (100, 200), RED, 3)
    cv2.line(img, (110, 140), (200, 140), RED, 3)
    return img


def test_no_jump_reacquires_lost_track_after_hole():
    img = _hijack_image()
    styles = [StyleSpec("r", "R", RED)]
    # Authentic failure first: default tracking teleports onto the decoy.
    default = _track(img, styles, "r", {"r": RED})
    assert any(s.status is SegmentStatus.OBSERVED and abs(s.v - 200.0) < 6.0
               for s in default.samples if 70 <= s.u < 100)

    kept = _track(img, styles, "r", {"r": RED}, TrackConfig(no_jump=True))
    # The decoy is never ridden (endpoint and antialiased bleed only ever
    # carry the neighbouring levels) ...
    assert not any(s.status is SegmentStatus.OBSERVED and abs(s.v - 200.0) < 8.0
                   for s in kept.samples if 65 <= s.u <= 125)
    # ... and the track resumes on the continuing line. Recovery is direct
    # (colour-confirmed ink inside re-acquisition reach wins its tie), so
    # no hole and no re-acquisition note remain.
    resumed = [s for s in kept.samples
               if s.status is SegmentStatus.OBSERVED and s.u >= 115]
    assert len(resumed) >= 40
    assert all(abs(s.v - 140.0) < 6.0 for s in resumed)
    assert any(s.status is SegmentStatus.OBSERVED and 110 <= s.u < 115
               and abs(s.v - 140.0) < 6.0 for s in kept.samples)
    assert not any("re-acquir" in r for r in kept.review_reasons)


def test_no_jump_reacquires_lost_track_without_colour():
    """Colour-blind callers still re-acquire lost tracks with a review note.

    Without unmixing confirmation every far take keeps losing its tie, so
    the track stays missing across the decoy and snaps back to the
    resuming line through delayed re-acquisition instead of direct
    recovery.
    """
    img = _hijack_image()
    layers = segment_evidence(img, [StyleSpec("r", "R", RED)])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kept = track_panel(gray, layers, ["r"], float(np.median(gray)),
                       TrackConfig(no_jump=True), None, None)["r"]
    assert not any(s.status is SegmentStatus.OBSERVED and abs(s.v - 200.0) < 8.0
                   for s in kept.samples if 65 <= s.u <= 125)
    resumed = [s for s in kept.samples
               if s.status is SegmentStatus.OBSERVED and s.u >= 115]
    assert len(resumed) >= 40
    assert all(abs(s.v - 140.0) < 6.0 for s in resumed)
    assert any("re-acquir" in r for r in kept.review_reasons)


def test_no_jump_then_continuous_compose_on_spike():
    img = _spike_image()
    styles = [StyleSpec("r", "R", RED)]
    composed = _track(img, styles, "r", {"r": RED},
                      TrackConfig(no_jump=True, curve_continuous=True))
    by_u = {int(s.u): s for s in composed.samples}
    bridged = [by_u[u] for u in range(159, 162)]
    assert all(s.status is SegmentStatus.INTERPOLATED for s in bridged)
    assert all(abs(s.v - _diag_v(s.u)) < 3.0 for s in bridged)


def _merged_distractor_image():
    """Red line with a same-colour distractor joined by a foreign hairline.

    A blue 1px vertical bar at x=100 merges the union cluster across the
    red line (y=100) and a parallel red distractor (y=130), while only
    red rows count as owned. The whole-cluster mean sits ~20px off the
    live prediction; the prediction-nearest owned group holds the line.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 100), (200, 100), RED, 3)
    cv2.line(img, (100, 130), (140, 130), RED, 3)
    cv2.line(img, (100, 99), (100, 131), BLUE, 1)
    return img


def test_no_jump_take_prefers_prediction_nearest_owned_group():
    img = _merged_distractor_image()
    styles = [StyleSpec("r", "R", RED), StyleSpec("b", "B", BLUE)]
    tracked = _track(img, styles, "r", {"r": RED}, TrackConfig(no_jump=True))
    by_u = {int(s.u): s for s in tracked.samples}
    assert by_u[100].status is SegmentStatus.OBSERVED
    assert abs(by_u[100].v - 100.0) < 6.0
    near = [by_u[u] for u in range(95, 106)
            if by_u[u].status is SegmentStatus.OBSERVED]
    assert near
    assert sum(abs(s.v - 100.0) for s in near) / len(near) < 4.0


def _covered_distractor_image():
    """Red gap under a blue cover, with a red distractor inside the gap.

    Blue holds red's level across the whole gap, so the motion prediction
    stays live under cover for the full 20 columns. The distractor must
    stay refused past the usual lost threshold: freshness pauses while
    merged ink covers the path, and the resuming line is still taken
    promptly because the prediction never went stale.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (90, 100), (170, 100), BLUE, 3)
    cv2.line(img, (10, 100), (99, 100), RED, 3)
    cv2.line(img, (121, 100), (210, 100), RED, 3)
    cv2.line(img, (105, 130), (118, 130), RED, 3)
    return img


def test_no_jump_refusal_survives_cover_paused_freshness():
    img = _covered_distractor_image()
    styles = [StyleSpec("r", "R", RED), StyleSpec("b", "B", BLUE)]
    tracked = _track(img, styles, "r", {"r": RED},
                     TrackConfig(no_jump=True, assume_overlap=True))
    assert not any(s.status is SegmentStatus.OBSERVED and abs(s.v - 100.0) > 12.0
                   for s in tracked.samples if 100 <= s.u <= 120)
    coast = [s for s in tracked.samples if 105 <= s.u <= 111]
    assert coast
    assert any(s.status is SegmentStatus.INFERRED_OCCLUSION for s in coast)
    resumed = [s for s in tracked.samples
               if s.status is SegmentStatus.OBSERVED and 121 <= s.u <= 130]
    assert len(resumed) >= 5
    assert all(abs(s.v - 100.0) < 6.0 for s in resumed)


def _confirmed_scores(rows, lo=0, span=200, good=0.0, bad=100.0):
    """Fake unmixing scores: ``rows`` confirm, everything else refuses."""
    scores = np.full(span, bad)
    for r in rows:
        scores[r - lo] = good
    return scores


def test_recover_rows_takes_confirmed_runahead():
    scores = _confirmed_scores([50, 51, 52])
    assert _recover_rows([50, 51, 52], 30.0, 3, scores, 0,
                         2.0, 28.0, False) == [50, 51, 52]


def test_recover_rows_takes_runahead_above():
    scores = _confirmed_scores([10, 11])
    assert _recover_rows([10, 11], 30.0, 3, scores, 0,
                         -2.0, 32.0, False) == [10, 11]


def test_recover_rows_prefers_nearest_group():
    scores = _confirmed_scores([28, 29, 60, 61])
    assert _recover_rows([28, 29, 60, 61], 30.0, 3, scores, 0,
                         2.0, 22.0, False) == [28, 29]


def test_recover_rows_refuses_live_coast_under_cover():
    # Same-colour distractor under covering ink with the prediction intact
    # (zero drift): coast even with live motion toward the ink, exactly as
    # test_no_jump_refusal_survives_cover_paused_freshness.
    scores = _confirmed_scores([128, 129, 130, 131, 132])
    assert _recover_rows([128, 129, 130, 131, 132], 100.0, 3, scores, 0,
                         2.0, 100.0, True) is None


def test_recover_rows_refuses_static_prediction():
    scores = _confirmed_scores([50, 51, 52])
    assert _recover_rows([50, 51, 52], 30.0, 3, scores, 0,
                         0.0, 30.0, False) is None


def test_recover_rows_refuses_ink_behind_motion():
    scores = _confirmed_scores([50, 51, 52])
    assert _recover_rows([50, 51, 52], 30.0, 3, scores, 0,
                         -2.0, 28.0, False) is None


def test_recover_rows_refuses_unconfirmed_ink():
    scores = _confirmed_scores([])
    assert _recover_rows([50, 51, 52], 30.0, 3, scores, 0,
                         2.0, 28.0, False) is None


def test_recover_rows_refuses_out_of_reach_ink():
    scores = _confirmed_scores([200, 201], span=300)
    assert _recover_rows([200, 201], 30.0, 3, scores, 0,
                         2.0, 28.0, False) is None


def test_recover_rows_refuses_without_history():
    scores = _confirmed_scores([50, 51, 52])
    assert _recover_rows([50, 51, 52], 30.0, 3, scores, 0,
                         2.0, None, False) is None
    assert _recover_rows([], 30.0, 3, scores, 0, 2.0, 28.0, False) is None


def _obs_seq(vals):
    return [SeriesSample(u=float(i), v=float(v), status=SegmentStatus.OBSERVED)
            for i, v in enumerate(vals)]


def test_live_obs_returns_newest_first_with_limit():
    seq = _obs_seq([10.0, 20.0, 30.0, 40.0, 50.0])
    assert _live_obs(seq, -1, 4) == [50.0, 40.0, 30.0, 20.0]
    assert _live_obs(seq, -1, 2) == [50.0, 40.0]


def test_live_obs_truncates_at_motion_break():
    seq = _obs_seq([10.0, 20.0, 100.0, 102.0])
    assert _live_obs(seq, 1, 4) == [102.0, 100.0]
    assert _live_obs(seq, 3, 4) == []


def test_live_obs_skips_non_observed():
    seq = _obs_seq([10.0, 20.0, 30.0])
    seq[1] = SeriesSample(u=1.0, v=0.0, status=SegmentStatus.MISSING)
    assert _live_obs(seq, -1, 4) == [30.0, 10.0]


def _riser_wall_image():
    """Gentle rise, one 16px riser across a small gap, gentle rise again.

    The riser exceeds the motion gate from a live prediction, so refusal
    logic sees it; it is confirmed same-colour ink ahead of live motion
    with the prediction standing empty, so recovery must take it instead
    of leaving a bridged hole.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 100), (95, 117), RED, 2)
    cv2.line(img, (101, 133), (101, 135), RED, 2)
    cv2.line(img, (103, 136), (200, 155), RED, 2)
    return img


def test_no_jump_recovers_confirmed_riser_wall():
    tracked = _track(_riser_wall_image(), [StyleSpec("r", "R", RED)], "r",
                     {"r": RED}, TrackConfig(no_jump=True))
    by_u = {int(s.u): s for s in tracked.samples}
    assert by_u[101].status is SegmentStatus.OBSERVED
    assert abs(by_u[101].v - 134.0) < 6.0
    wall = [by_u[u] for u in range(101, 113)]
    assert all(s.status is SegmentStatus.OBSERVED for s in wall)
    assert any("recovery" in reason for reason in tracked.review_reasons)


def _lure_resume_image():
    """Flat line, clean gap, resumption with a parallel same-colour lure.

    The stale whole-mean resumption take jumps 40px; without a motion
    restart the jump seeds velocity and step gates and the track rides the
    lure. With the restart the track resumes on its own ink and ignores it.
    """
    img = np.full((240, 320, 3), 255, np.uint8)
    cv2.line(img, (10, 100), (60, 100), RED, 3)
    cv2.line(img, (81, 140), (200, 140), RED, 3)
    cv2.line(img, (81, 175), (200, 175), RED, 3)
    return img


def test_jump_resumption_restarts_motion_ignores_lure():
    tracked = _track(_lure_resume_image(), [StyleSpec("r", "R", RED)], "r",
                     {"r": RED}, TrackConfig(no_jump=True))
    by_u = {int(s.u): s for s in tracked.samples}
    resumed = [by_u[u] for u in range(85, 151)]
    assert all(s.status is SegmentStatus.OBSERVED for s in resumed)
    assert all(abs(s.v - 140.0) < 6.0 for s in resumed)
    assert not any(s.status is SegmentStatus.OBSERVED and abs(s.v - 175.0) < 6.0
                   for s in tracked.samples if 82 <= s.u <= 200)


def test_segment_scores_reject_darker_than_template():
    """Take costs honour the same over-coverage bound as the evidence
    mask: a black core scores near zero against a grey template at
    coverage ~1.8, so without the cap every take and colour-confirmed
    recovery prefers foreign dark ink (Devialet grey rode black)."""
    from graphextract.tracking import _segment_scores

    bg = np.array((255, 255, 255), float).reshape(1, 3)
    gray = np.array((113, 113, 113), float)
    scores, _ = _segment_scores(np.array([(0, 0, 0)], float), gray, bg)
    assert not np.isfinite(scores[0])
    scores, _ = _segment_scores(np.array([(140, 140, 140)], float), gray, bg)
    assert scores[0] <= 15.0


def test_seed_fallback_prefers_substantial_coverage():
    """Without an excellent column the seed takes the best
    substantial-coverage column, not a lone lucky fringe pixel: thin
    soup unmixes near any template at coverage ~0.3 and outranks the
    true thin stroke (~0.5) it should seed on (Devialet orange)."""
    from graphextract.tracking import _seed_columns

    teal = (125, 88, 36)
    white = np.full((60, 64, 3), 255, np.uint8)
    fringe = (0.3 * np.array(teal) + 0.7 * 255).astype(np.uint8)
    core = (0.5 * np.array(teal) + 0.5 * 255).astype(np.uint8)
    color = white.copy()
    color[20, 5] = fringe
    color[40, 10] = core
    union = np.zeros((60, 64), bool)
    union[20, 5] = True
    union[40, 10] = True
    owned = {"t": np.zeros((60, 64), bool)}
    owned["t"][20, 5] = True
    owned["t"][40, 10] = True
    seeds = _seed_columns(union, owned, ["t"], {"t": teal}, color,
                          (255, 255, 255), 3, 64)
    assert seeds["t"] == 10


def _missing_gap_seq(left_v, gap_len, right_v, flank=4):
    seq = _obs_seq([float(left_v)] * flank + [0.0] * gap_len + [float(right_v)] * flank)
    for s in seq[flank:flank + gap_len]:
        s.status = SegmentStatus.MISSING
    return seq


def test_fill_continuous_refuses_marathon_gaps():
    from graphextract.tracking import _fill_continuous
    # Sovox-PIR shape: flanks 430 columns apart on different curves. The
    # per-column slope looks shallow, so length itself must refuse.
    seq = _missing_gap_seq(635.0, 430, 278.0)
    filled, gaps, refused = _fill_continuous(seq, clusters_at=lambda x: [])
    assert (filled, gaps, refused) == (0, 0, 1)


def test_fill_continuous_allows_flat_blind_dash_gaps():
    from graphextract.tracking import _fill_continuous
    # Topping-ERDI shape: an 85-column level run over empty space (dash
    # gaps on a flat zero line). Flat flanks promise a flat truth.
    seq = _missing_gap_seq(694.0, 85, 692.2)
    filled, gaps, refused = _fill_continuous(seq, clusters_at=lambda x: [])
    assert (filled, gaps, refused) == (85, 1, 0)


def test_fill_continuous_refuses_sloped_blind_runs():
    from graphextract.tracking import _fill_continuous
    # BW-64 shape: 60px of rise over 64 empty columns is a guess, not a
    # dropout, even though the length cap alone would allow it.
    seq = _missing_gap_seq(1112.0, 64, 1052.0)
    filled, gaps, refused = _fill_continuous(seq, clusters_at=lambda x: [])
    assert (filled, gaps, refused) == (0, 0, 1)
    # Short sloped blind runs still fill via flank support (steep rolloff).
    seq = _missing_gap_seq(600.0, 30, 540.0)
    filled, gaps, refused = _fill_continuous(seq, clusters_at=lambda x: [])
    assert (filled, gaps, refused) == (30, 1, 0)


def test_fill_continuous_allows_sloped_runs_over_ink():
    from graphextract.tracking import _fill_continuous
    # PMC10-4 shape: 78px of rise over 58 columns with merged ink under
    # the whole path is a dropout inside a rolloff, not an identity jump.
    seq = _missing_gap_seq(400.0, 58, 322.0)
    v0, v1 = 400.0, 322.0

    def along(x):
        level = v0 + (v1 - v0) * (x - 4 + 1) / 59.0
        return [[int(round(level))]]

    filled, gaps, refused = _fill_continuous(seq, clusters_at=along)
    assert (filled, gaps, refused) == (58, 1, 0)


def test_seed_columns_skip_empty_window_to_first_run():
    from graphextract.tracking import _seed_columns
    # Backward-pass shape: an excluded edge strip leaves the whole scan
    # window empty, with blips before the true run. The seed must be the
    # run start, never column zero (which would grab the first blip).
    teal = (125, 88, 36)
    color = np.full((60, 320, 3), 255, np.uint8)
    core = (0.5 * np.array(teal) + 0.5 * 255).astype(np.uint8)
    color[40, 10] = core  # lone blip inside the window
    color[40, 270:276] = core  # true run past the window
    union = np.zeros((60, 320), bool)
    union[40, 10] = True
    union[40, 270:276] = True
    owned = {"t": np.zeros((60, 320), bool)}
    # Window blip is not owned (excluded fringe); the run is.
    owned["t"][40, 270:276] = True
    seeds = _seed_columns(union, owned, ["t"], {"t": teal}, color,
                          (255, 255, 255), 3, 320)
    assert seeds["t"] == 270


def _commitment_column():
    """Two core-grade owned clusters for one series: tainted (row 20)
    hugging foreign claims, clean (row 40) clear of them."""
    teal = (125, 88, 36)
    color_col = np.full((60, 3), 255.0)
    core = 0.5 * np.array(teal) + 0.5 * 255
    color_col[20] = core
    color_col[40] = core
    clusters = [[20], [40]]
    centroids = [20.0, 40.0]
    owned_masks = {"t": np.zeros(60, bool)}
    owned_masks["t"][[20, 40]] = True
    avoid = np.zeros(60, np.uint8)
    avoid[10:30] = 255
    return (teal, color_col, clusters, centroids, owned_masks, avoid)


def test_commitment_prefers_clean_over_tainted():
    from graphextract.tracking import _joint_assignment
    # Convergence shape: without motion history both clusters tie and
    # colour ties too (shared hues unmix core-grade), so set order
    # would pick the band. The taint penalty must elect the clean ink.
    teal, color_col, clusters, centroids, owned_masks, avoid = (
        _commitment_column())
    got = _joint_assignment(
        centroids, clusters, {"t": None}, {"t": {0, 1}}, ["t"], 2,
        12.0, owned_masks, color_col, {"t": teal},
        bg_bgr=(255, 255, 255), avoid_cols={"t": avoid})
    assert got["t"] == 1


def test_commitment_tainted_fallback_matches_unsteered():
    from graphextract.tracking import _joint_assignment
    # Overlay shape: every candidate hugs foreign claims, so the steer
    # must behave exactly as without it (here the lower-cost cluster).
    teal, color_col, clusters, centroids, owned_masks, _ = (
        _commitment_column())
    avoid = np.zeros(60, np.uint8)
    avoid[10:50] = 255
    kwargs = dict(centroids=centroids, clusters=clusters,
                  predictions={"t": None}, owned={"t": {0, 1}},
                  series_ids=["t"], beam_width=2,
                  occlusion_penalty=12.0, owned_masks=owned_masks,
                  color_col=color_col, series_colors={"t": teal},
                  bg_bgr=(255, 255, 255))
    base = _joint_assignment(**kwargs)
    steered = _joint_assignment(**kwargs, avoid_cols={"t": avoid})
    assert steered["t"] == base["t"]


def test_commitment_penalty_ignores_committed_tracks():
    from graphextract.tracking import _joint_assignment
    # A live prediction pays no taint penalty: crossings keep today's
    # motion-led behaviour even when a clean cluster shares the column.
    teal, color_col, clusters, centroids, owned_masks, avoid = (
        _commitment_column())
    got = _joint_assignment(
        centroids, clusters, {"t": 20.0}, {"t": {0, 1}}, ["t"], 2,
        12.0, owned_masks, color_col, {"t": teal},
        bg_bgr=(255, 255, 255), avoid_cols={"t": avoid})
    assert got["t"] == 0


def test_maybe_reseed_prefers_clean_qualifier():
    from graphextract.tracking import _TAINT_PENALTY, _maybe_reseed, _segment_scores
    # Ascilab-SPDI shape: the impostor unmixes core-grade (better raw
    # score than the true dash), so colour alone re-seeds onto foreign
    # ink; the taint penalty must flip the ranking to the clean dash.
    teal = (125, 88, 36)
    col_pixels = np.full((60, 3), 255.0)
    col_pixels[20] = 0.7 * np.array(teal) + 0.3 * 255  # impostor, best raw
    col_pixels[40] = 0.5 * np.array(teal) + 0.5 * 255 + (3, 0, 0)
    scores, _ = _segment_scores(col_pixels, np.array(teal, dtype=float),
                                np.full((1, 3), 255.0))
    assert scores[20] < scores[40] < scores[20] + _TAINT_PENALTY <= 15.0
    clusters = [[20], [40]]
    centroids = [20.0, 40.0]
    own_col = np.zeros(60, bool)
    own_col[[20, 40]] = True
    avoid = np.zeros(60, np.uint8)
    avoid[10:30] = 255
    last_y: dict = {"t": 200.0}
    last_v: dict = {"t": 200.0}
    vel: dict = {"t": 0.0}
    plain = _maybe_reseed("t", 100, 320, 60, {0, 1}, clusters,
                          centroids, own_col, col_pixels, teal,
                          (255, 255, 255), 15.0, last_y, last_v, vel)
    assert plain is not None and plain[0] == 20.0
    last_y["t"] = last_v["t"] = 200.0
    steered = _maybe_reseed("t", 100, 320, 60, {0, 1}, clusters,
                            centroids, own_col, col_pixels, teal,
                            (255, 255, 255), 15.0, last_y, last_v, vel,
                            avoid)
    assert steered is not None and steered[0] == 40.0


def test_clean_commit_flags_mark_clean_columns():
    from graphextract.tracking import _clean_commit_flags
    # Column 10 carries a tainted core-grade cluster only; columns
    # 40-44 a clean run; column 20 an isolated clean pixel (noise, no
    # run); column 30 is empty; column 2 is clean but inside the edge
    # strip reseeds cannot commit on.
    teal = (125, 88, 36)
    color = np.full((60, 64, 3), 255, np.uint8)
    core = (0.7 * np.array(teal) + 0.3 * 255).astype(np.uint8)
    for x in (10, 20, 2, 40, 41, 42, 43, 44):
        color[40, x] = core
    union = np.zeros((60, 64), bool)
    for x in (10, 20, 2, 40, 41, 42, 43, 44):
        union[40, x] = True
    owned = union.copy()
    avoid = np.zeros((60, 64), np.uint8)
    avoid[30:50, 10] = 255
    exc, qual = _clean_commit_flags(union, owned, color, teal,
                                    (255, 255, 255), avoid, 3, 15.0)
    assert not exc[10] and not qual[10]
    assert not exc[20] and not qual[20]
    assert exc[40:45].all() and qual[40:45].all()
    assert not exc[30] and not qual[30]
    assert not exc[2] and not qual[2]


def test_seed_columns_clean_seed_override_pins_column():
    from graphextract.tracking import _seed_columns
    # The window's first excellent column is tainted; the caller pins
    # the seed to the first clean-excellent column past it instead.
    teal = (125, 88, 36)
    color = np.full((60, 320, 3), 255, np.uint8)
    core = (0.7 * np.array(teal) + 0.3 * 255).astype(np.uint8)
    color[20, 40] = core
    color[40, 100] = core
    union = np.zeros((60, 320), bool)
    union[20, 40] = True
    union[40, 100] = True
    owned = {"t": union.copy()}
    base = _seed_columns(union, owned, ["t"], {"t": teal}, color,
                         (255, 255, 255), 3, 320)
    assert base["t"] == 40
    pinned = _seed_columns(union, owned, ["t"], {"t": teal}, color,
                           (255, 255, 255), 3, 320, {"t": 100})
    assert pinned["t"] == 100


def test_maybe_reseed_defers_tainted_while_clean_ahead():
    from graphextract.tracking import _maybe_reseed
    # Dash-gap shape: only tainted impostor ink qualifies here, so the
    # re-seed waits while clean ink is coming and commits only when
    # none is (overlay ink or merged truth at a convergence).
    teal = (125, 88, 36)
    col_pixels = np.full((60, 3), 255.0)
    col_pixels[20] = 0.7 * np.array(teal) + 0.3 * 255
    clusters = [[20]]
    centroids = [20.0]
    own_col = np.zeros(60, bool)
    own_col[20] = True
    avoid = np.zeros(60, np.uint8)
    avoid[10:30] = 255
    ahead = np.zeros(320, bool)
    ahead[100] = True
    last_y: dict = {"t": 200.0}
    last_v: dict = {"t": 200.0}
    vel: dict = {"t": 0.0}
    assert _maybe_reseed("t", 100, 320, 60, {0}, clusters, centroids,
                         own_col, col_pixels, teal, (255, 255, 255),
                         15.0, last_y, last_v, vel, avoid, ahead) is None
    last_y["t"] = last_v["t"] = 200.0
    ahead[100] = False
    got = _maybe_reseed("t", 100, 320, 60, {0}, clusters, centroids,
                        own_col, col_pixels, teal, (255, 255, 255),
                        15.0, last_y, last_v, vel, avoid, ahead)
    assert got is not None and got[0] == 20.0


def test_reacquire_snaps_nearest_within_reach():
    from graphextract.tracking import _maybe_reacquire
    # Recovery stays proximity-led: twin hues unmix in overlapping
    # ranges, so colour cannot rank the snap without latching the
    # darker twin; the consensus offset proof absorbs hop residue.
    last_y: dict = {"t": 30.0}
    last_v: dict = {"t": 30.0}
    vel: dict = {"t": 0.0}
    assert _maybe_reacquire("t", 30.0, {0, 1}, [20.0, 40.0],
                            last_y, last_v, vel) == 20.0
    assert _maybe_reacquire("t", 30.0, {1}, [20.0, 40.0],
                            last_y, last_v, vel) == 40.0
    assert _maybe_reacquire("t", 30.0, {0}, [200.0],
                            last_y, last_v, vel) is None


def test_maybe_reseed_snaps_to_best_confirmed_cluster():
    import numpy as np

    from graphextract.tracking import _maybe_reseed
    teal = (125, 88, 36)
    col = np.full((60, 3), 255.0)
    col[10] = (0.9 * np.array(teal) + 0.1 * 255)  # near-hue impostor edge
    col[40] = np.array(teal, dtype=float)  # true core, far away
    clusters = [[10], [40]]
    centroids = [10.0, 40.0]
    own_col = np.zeros(60, bool)
    own_col[[10, 40]] = True
    last_y = {"t": 12.0}
    last_v = {"t": 12.0}
    vel = {"t": 0.0}
    # Colour (not proximity) picks the target: the stale prediction sits
    # on the impostor, but the true core unmixes better.
    hit = _maybe_reseed("t", 30, 64, 60, {0, 1}, clusters, centroids,
                        own_col, col, teal, (255, 255, 255), 15.0,
                        last_y, last_v, vel)
    assert hit is not None
    level, score = hit
    assert level == 40.0
    assert score <= 15.0
    assert last_y["t"] == 40.0 and last_v["t"] == 40.0 and vel["t"] == 0.0
    # Nothing confirmed: the track stays lost.
    last_y["t"] = 12.0
    miss = _maybe_reseed("t", 30, 64, 60, {0}, clusters, centroids, own_col,
                         col, (30, 200, 30), (255, 255, 255), 15.0,
                         last_y, last_v, vel)
    assert miss is None
    assert last_y["t"] == 12.0
    # Frame-band targets vetoed even when confirmed: frame furniture
    # matches grey templates and would hand the track a frame ride.
    frame_col = np.full((60, 3), 255.0)
    frame_col[2] = np.array(teal, dtype=float)
    fown = np.zeros(60, bool)
    fown[2] = True
    last_y["t"] = 50.0
    assert _maybe_reseed("t", 30, 64, 60, {0}, [[2]], [2.0], fown,
                         frame_col, teal, (255, 255, 255), 15.0,
                         last_y, last_v, vel) is None
    assert last_y["t"] == 50.0


def test_seed_skips_frame_band_clusters():
    """Identity never commits on frame furniture: a black top frame scores
    perfectly on a black template, so uncommitted takes skip frame-band
    clusters and the track rides its curve, not the frame."""
    black = (11, 5, 14)
    h, w = 120, 64
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.line(img, (0, 1), (w - 1, 1), (0, 0, 0), 2)
    cv2.line(img, (0, 60), (w - 1, 60), (16, 13, 17), 2)
    mask = np.zeros((h, w), np.uint8)
    mask[0:3, :] = 255  # top frame rows, owned ink
    mask[59:62, :] = 255  # black curve
    layers = EvidenceLayers(curve_masks={"t": mask},
                            grid_mask=np.zeros((h, w), np.uint8),
                            background_bgr=(255, 255, 255))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    track = track_panel(gray, layers, ["t"], float(np.median(gray)),
                        None, {"t": black}, img)["t"]
    observed = [s for s in track.samples if s.status is SegmentStatus.OBSERVED]
    assert observed, "curve never committed"
    assert all(abs(s.v - 60.0) < 4.0 for s in observed), observed[:5]
    # Slack frame: the interior starts above the frame, so the veto must
    # measure frame rows instead of trusting a fixed edge band.
    img2 = np.full((h, w, 3), 255, np.uint8)
    cv2.line(img2, (0, 7), (w - 1, 7), (0, 0, 0), 2)
    cv2.line(img2, (0, 60), (w - 1, 60), (16, 13, 17), 2)
    mask2 = np.zeros((h, w), np.uint8)
    mask2[6:9, :] = 255
    mask2[59:62, :] = 255
    layers2 = EvidenceLayers(curve_masks={"t": mask2},
                             grid_mask=np.zeros((h, w), np.uint8),
                             background_bgr=(255, 255, 255))
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    track2 = track_panel(gray2, layers2, ["t"], float(np.median(gray2)),
                         None, {"t": black}, img2)["t"]
    observed2 = [s for s in track2.samples if s.status is SegmentStatus.OBSERVED]
    assert observed2, "curve never committed past slack frame"
    assert all(abs(s.v - 60.0) < 4.0 for s in observed2), observed2[:5]
