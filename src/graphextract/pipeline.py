# -*- coding: utf-8 -*-
"""Canonical extraction pipeline: ingest -> panels -> axes -> evidence -> track.

Per-panel isolation: one panel's failure never overwrites another's data.
The production path takes no oracle inputs; renderer truth enters only through
tests via explicitly labelled verified anchors. Uncalibrated panels produce
review requirements, never guessed measurements.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Sequence

import cv2
import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from graphextract.ocr_adapters import OCRWord

from graphextract.calibration import CalibrationUnresolved, ScaleType, fit_axis
from graphextract.evidence import EvidenceLayers, StyleSpec, estimate_background, segment_evidence
from graphextract.panels import detect_panels
from graphextract.schema import (
    AxisFit,
    AxisRole,
    DocumentResult,
    PanelOutcome,
    PanelResult,
    TickAnchor,
)
from graphextract.tracking import (
    KNOWN_ASSUMPTIONS,
    SeriesResult,
    TrackConfig,
    resolve_duplicate_claims,
    track_panel,
    track_sid_bidirectional,
)
from graphextract.semantics import (  # noqa: E402 - re-export
    _axis_for_label,
    _family_words,
)

PIPELINE_VERSION = "0.1.0"


@dataclass
class AxisAnchors:
    x: list[TickAnchor] = field(default_factory=list)
    y_left: list[TickAnchor] = field(default_factory=list)
    y_right: list[TickAnchor] = field(default_factory=list)
    x_scale: ScaleType | None = None
    x_unit: str = ""
    y_unit: str = ""
    y_right_unit: str = ""
    source: str = "unknown"  # ocr_unverified | user_verified | renderer_verified_test | ...
    y_scale: ScaleType | None = None
    y_right_scale: ScaleType | None = None


AnchorProvider = Callable[[str, npt.NDArray], AxisAnchors]


def _empty_anchors(_panel_id: str, _img: npt.NDArray) -> AxisAnchors:
    return AxisAnchors()


def _merge_anchors(first: AxisAnchors, second: AxisAnchors) -> AxisAnchors:
    """Union two anchor sets, deduplicating shared ticks.

    The interior-only provider read and the margin recovery see the same
    ticks through different words; duplicates (same pixel and value) keep
    the provider's copy (a verified source wins ties). Conflicting values
    at one pixel both survive: the robust fit rejects the misread.
    """
    def _union(primary: list, fallback: list) -> list:
        out = list(primary)
        seen = {(round(a.pixel), a.value) for a in out}
        for a in fallback:
            if (round(a.pixel), a.value) not in seen:
                seen.add((round(a.pixel), a.value))
                out.append(a)
        return out

    merged = AxisAnchors(
        x=_union(first.x, second.x),
        y_left=_union(first.y_left, second.y_left),
        y_right=_union(first.y_right, second.y_right),
        x_scale=first.x_scale or second.x_scale,
        y_scale=first.y_scale or second.y_scale,
        y_right_scale=first.y_right_scale or second.y_right_scale,
        x_unit=first.x_unit or second.x_unit,
        y_unit=first.y_unit or second.y_unit,
        y_right_unit=first.y_right_unit or second.y_right_unit,
        source=(first.source if first.x or first.y_left or first.y_right
                else second.source),
    )
    return merged


def _claimed_mask(
    tracks: dict[str, SeriesResult],
    h: int,
    w: int,
    observed_only: bool = True,
) -> npt.NDArray:
    """Pixel mask of ink claimed by finished tracks (interior-local).

    Every claimed sample takes its centre row ± half width; one
    dilation catches antialiased skirts, so a later series seeding on the
    same hue cannot latch the claimed stroke's fringe. By default only
    measurements claim: interpolated filler must not fence off bands it
    merely crosses. The full-path variant (missing excluded) is the
    fallback when measurements alone leave a seed unfenced.
    """
    from graphextract.schema import SegmentStatus

    mask = np.zeros((h, w), dtype=np.uint8)
    for tr in tracks.values():
        for s in tr.samples:
            if observed_only:
                if s.status is not SegmentStatus.OBSERVED:
                    continue
            elif s.status is SegmentStatus.MISSING:
                continue
            c = int(round(float(s.u)))
            r = int(round(float(s.v)))
            hw = max(1, int(round(float(getattr(s, "half_width_px", 1.0)))))
            if 0 <= c < w:
                mask[max(0, r - hw):min(h, r + hw + 1), c] = 255
    return cv2.dilate(mask, np.ones((3, 3), np.uint8))


_SPLIT_DB_FRAC = 0.8
"""Largest dB-hued fraction below a split candidate that still splits.

Below-gap ink clearly continuing the measured band (four dB strokes
in five) rejects the split; twin-tie and DI-hued ink splits.
"""


def _band_split_row(
    db_masks: list[npt.NDArray],
    di_masks: list[npt.NDArray],
    interior: npt.NDArray,
    db_bgr: list[tuple[int, int, int]],
    di_bgr: list[tuple[int, int, int]],
) -> int | None:
    """Global measured/directivity split row, or None without one.

    Same-hue decoys hide in untracked measured dips below every
    track-defined floor (Ascilab SPDI committed on a Sound Power dip
    no track claims), so the floor comes from evidence, not tracks:
    the deepest row-occupancy gap in the measured ink whose below-gap
    ink is directivity-hued. Twin leaks occupy directivity rows but
    never the separation itself; gaps with nothing below steer
    nowhere and are skipped. Overlay plots offer no surviving gap
    and return None, disabling steering exactly. Ties classify
    directivity-ward: twin hues are equidistant by construction.
    """
    if not db_masks or not db_bgr or not di_bgr:
        return None
    h, w = int(interior.shape[0]), int(interior.shape[1])
    occ = np.zeros(h, dtype=bool)
    for m in db_masks:
        occ |= np.asarray(m).reshape(h, w).max(axis=1) > 0
    if not occ.any():
        return None
    gaps: list[tuple[int, int]] = []
    r = 0
    while r < h:
        if occ[r]:
            r += 1
            continue
        j = r
        while j + 1 < h and not occ[j + 1]:
            j += 1
        gaps.append((r, j))
        r = j + 1
    ink2d = np.zeros((h, w), dtype=bool)
    for m in list(db_masks) + list(di_masks):
        ink2d |= np.asarray(m).reshape(h, w) > 0
    rows2d = np.repeat(np.arange(h), w).reshape(h, w)
    px = np.asarray(interior).reshape(-1, 3).astype(float)
    flat_ink = ink2d.reshape(-1)
    flat_rows = rows2d.reshape(-1)
    db_ref = np.array(db_bgr, dtype=float).reshape(-1, 3)
    di_ref = np.array(di_bgr, dtype=float).reshape(-1, 3)
    for top, _ in sorted(gaps, reverse=True):
        sel = flat_rows > top
        if not sel.any():
            continue
        ink = flat_ink & sel
        if not ink.any():
            continue
        cand = px[ink]
        if len(cand) > 20000:
            cand = cand[:: len(cand) // 20000]
        d_db = np.linalg.norm(cand[:, None, :] - db_ref[None, :, :],
                              axis=2).min(axis=1)
        d_di = np.linalg.norm(cand[:, None, :] - di_ref[None, :, :],
                              axis=2).min(axis=1)
        frac_db = float((d_db < d_di - 1e-9).mean())
        if frac_db <= _SPLIT_DB_FRAC:
            return top - 1
    return None


def _recover_di_right_axis(
    result: PanelResult,
    axes: dict[str, AxisFit],
    tracks: dict[str, SeriesResult],
) -> None:
    """Right axis for directivity curves from the plotted offset.

    Some vendors plot DI curves shifted up by a fixed dB offset sharing the
    panel (same pixels per dB) without printing right ticks. The offset is
    authoritative when stated in the label (``(Offset:45dB)``); otherwise the
    DI identity (DI = A - B over measured curves) recovers it per series via
    ``solve_di_offset``. Stated offsets define the shared axis; inferred ones
    must agree with each other (and with stated ones) within 2dB, else the
    shift stays unproven and DI curves remain on dB, flagged for review.
    Family-less directivity markers (``DI offset`` zero lines) never vote
    in the pool: their fringe tracks solve stray offsets that would veto
    the family curves.
    """
    from graphextract.calibration import (
        _consensus_di_offset,
        parse_di_offset,
        solve_di_offset,
    )
    from graphextract.schema import SegmentStatus

    left = axes.get("y_left")
    if left is None:
        return
    di_tracks = [tr for tr in tracks.values()
                 if tr.label and _axis_for_label(tr.label) == "y_right"]
    if not di_tracks:
        return
    def _obs(tr: SeriesResult) -> dict[float, float]:
        return {s.u: s.v for s in tr.samples
                if s.status is SegmentStatus.OBSERVED}

    refs = [(tr.label or tr.series_id, _obs(tr))
            for tr in tracks.values()
            if not (tr.label and _axis_for_label(tr.label) == "y_right")]
    refs = [(label, vals) for label, vals in refs if len(vals) >= 10]
    solved: dict[str, float] = {}
    stated: set[str] = set()
    unproven: dict[str, str] = {}
    for tr in di_tracks:
        explicit = parse_di_offset(tr.label or "")
        if explicit is not None:
            solved[tr.series_id] = explicit
            stated.add(tr.series_id)
            continue
        pix = {s.u: s.v for s in tr.samples
               if s.status is SegmentStatus.OBSERVED}
        hit = solve_di_offset(pix, refs, left.a, left.b)
        via = ""
        if hit is None:
            chit = _consensus_di_offset(pix, refs, left.a, left.b)
            if chit is not None:
                off, (la, lb), frac, n = chit
                hit = (off, (la, lb), 0.0, n)
                via = f"consensus peak {frac:.0%} in 0.75dB"
        if hit is None:
            unproven[tr.series_id] = (
                "directivity offset unidentified: no reference pair "
                "explains this track")
            continue
        off, (la, lb), iqr, n = hit
        # A parallel measured curve can solve as DI with the offset of a
        # flat reference: accept the identity only when the implied DI
        # values sit in a plausible directivity range.
        divals = [(v - left.b) / left.a - off for v in pix.values()]
        med = float(np.median(divals))
        iqr_v = float(np.subtract(*np.percentile(divals, [75, 25])))
        if not (-15.0 <= med <= 30.0 and iqr_v <= 15.0):
            unproven[tr.series_id] = (
                f"directivity offset {off:.1f}dB rejected: implied DI "
                f"median {med:.1f}dB outside plausible range")
            continue
        solved[tr.series_id] = off
        tr.review_reasons.append(
            f"directivity offset {off:.1f}dB from {la} - {lb} "
            f"({via or f'IQR {iqr:.2f}dB'}, n={n})")
        fam = _family_words(tr.label or "") - {"offset"}
        if fam and not any(fam & _family_words(r) for r in (la, lb)):
            tr.review_reasons.append(
                f"twin swap suspected: {tr.label} solves with "
                f"{la} - {lb} (no shared family word)")
    if not solved:
        # Unproven offsets keep the anchored right-axis fit when one was
        # measured (direct ticks beat derived identity); only with no
        # right axis at all do DI curves stay on dB.
        for sid, detail in unproven.items():
            if "y_right" in axes:
                tracks[sid].review_reasons.append(
                    detail + "; anchored right-axis fit retained")
            else:
                tracks[sid].review_reasons.append(detail + "; stays on dB")
        if "y_right" in axes and unproven:
            result.review_reasons.append(
                "directivity offsets unproven; anchored right-axis fit "
                "retained")
        return
    def _has_family(sid: str) -> bool:
        tr = tracks.get(sid)
        return bool(tr is not None and tr.label
                    and (_family_words(tr.label) - {"offset"}))

    pool = [off for sid, off in solved.items()
            if sid in stated or _has_family(sid)] or list(solved.values())
    if max(pool) - min(pool) > 2.0:
        result.review_reasons.append(
            "directivity offsets disagree "
            f"({', '.join(f'{s}={o:.1f}' for s, o in sorted(solved.items()))}); "
            "right axis refused, DI curves stay on dB")
        return
    offset = float(sum(pool) / len(pool))
    axes["y_right"] = AxisFit(
        role=AxisRole.Y_RIGHT, scale=ScaleType.LINEAR, unit="dB",
        a=left.a, b=left.b + left.a * offset, method="di_offset_identity")
    for sid, off in solved.items():
        if abs(off - offset) <= 2.0:
            tracks[sid].axis_id = "y_right"
        else:
            tracks[sid].review_reasons.append(
                f"offset {off:.1f}dB disagrees with shared {offset:.1f}dB; "
                "stays on dB")
    result.provenance["di_offset_db"] = offset
    result.review_reasons.append(
        f"right axis from directivity offset {offset:.1f}dB")


def _demote_di_duplicates(tracks: dict[str, SeriesResult],
                          di_ids: set[str],
                          interior: npt.NDArray,
                          seed_bgr: dict[str, tuple[int, int, int]]) -> None:
    """Demote DI samples sitting on dB ink (or outside the plot) to missing.

    A same-paint DI seed latches dB-ink stretches the dB track only
    interpolated (unmasked at seeding): through the right axis those read
    as DI values tens of dB off. A DI sample within 2px of a measured
    sample, on ink matching the DI seed hue, duplicates the measured
    curve; samples outside the frame are lost-tracker extrapolation. Both
    go missing honestly instead of poisoning the series. Different-paint
    parallels are never duplicates: the ink-hue check keeps them.
    """
    from graphextract.schema import SegmentStatus

    h, w = interior.shape[:2]
    px = interior.astype(int)
    for sid in di_ids:
        tr = tracks.get(sid)
        if tr is None:
            continue
        demoted = 0
        for s in tr.samples:
            if s.status is SegmentStatus.MISSING:
                continue
            c, r = int(round(float(s.u))), int(round(float(s.v)))
            if c < 0 or c >= w or r < -2 or r > h + 2:
                s.status = SegmentStatus.MISSING
                demoted += 1
        if demoted:
            tr.review_reasons.append(
                f"directivity outside-plot samples demoted to missing: {demoted}")
    db_paths: set[tuple[int, int]] = set()
    for sid, tr in tracks.items():
        if sid in di_ids:
            continue
        for s in tr.samples:
            if s.status is SegmentStatus.MISSING:
                continue
            db_paths.add((int(round(float(s.u))), int(round(float(s.v)))))
    if not db_paths:
        return
    for sid in di_ids:
        tr = tracks.get(sid)
        ref = seed_bgr.get(sid)
        if tr is None or ref is None:
            continue
        ref_arr = np.array(ref)
        dupes = 0
        for s in tr.samples:
            if s.status is SegmentStatus.MISSING:
                continue
            c, r = int(round(float(s.u))), int(round(float(s.v)))
            if not (0 <= c < w and 0 <= r < h):
                continue
            if int(np.max(np.abs(px[r, c] - ref_arr))) > 60:
                continue
            hit = False
            for dc in (-2, -1, 0, 1, 2):
                for dr in (-2, -1, 0, 1, 2):
                    if (c + dc, r + dr) in db_paths:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                s.status = SegmentStatus.MISSING
                dupes += 1
        if dupes:
            tr.review_reasons.append(
                f"directivity samples on measured-curve ink demoted: {dupes}")


def _demote_thin_di_samples(tracks: dict[str, SeriesResult],
                            di_ids: set[str]) -> None:
    """Demote unsolvable directivity samples to missing.

    Fewer observed samples than the offset solvers need means no
    reference pair can ever explain the track, so its points ship only
    junk values: they go missing honestly instead of poisoning the
    series. The series itself stays (legend-named series flag for
    review instead of vanishing). Stated-offset tracks stay whatever
    their support: the label is the measurement.
    """
    from graphextract.calibration import parse_di_offset
    from graphextract.schema import SegmentStatus

    for sid in sorted(di_ids):
        tr = tracks.get(sid)
        if tr is None or parse_di_offset(tr.label or "") is not None:
            continue
        if tr.observed_support() >= _SWAP_MIN_OBS:
            continue
        demoted = 0
        for s in tr.samples:
            if s.status is not SegmentStatus.MISSING:
                s.status = SegmentStatus.MISSING
                demoted += 1
        if demoted:
            tr.review_reasons.append(
                f"thin unproven directivity ({tr.observed_support()} "
                f"observed): {demoted} samples demoted to missing")


_SWAP_COLOR_DIST = 40.0
_SWAP_MIN_SEP_DB = 10.0
_SWAP_MARGIN_DB = 5.0
_SWAP_ANCHOR_SPREAD_DB = 5.0
_SWAP_MIN_OBS = 10
_SWAP_ANCHOR_MIN_RANGE_PX = 10.0
_ENFORCE_OFF_DB = 10.0
_ENFORCE_HOME_DB = 5.0
_ENFORCE_MIN_SUPPORT_FRAC = 0.3
_SEED_AVOID_FRAC = 0.045
_SEED_AVOID_MIN_PX = 16


def _db_consensus(tracks: dict[str, SeriesResult],
                  di_ids: set[str],
                  seed_bgr: dict[str, tuple[int, int, int]],
                  px_per_db: float) -> float | None:
    """Median level of unique-paint measured tracks, or None.

    Unique-paint measured tracks cannot mislatch bands, so their tight
    median is the measured band's level. None without anchors, with a
    split band, or with pixel-flat almost-tracks only.
    """
    from graphextract.schema import SegmentStatus

    if px_per_db <= 0:
        return None
    med: dict[str, float] = {}
    span: dict[str, float] = {}
    for sid, tr in tracks.items():
        vv = sorted(float(s.v) for s in tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS:
            med[sid] = vv[len(vv) // 2]
            span[sid] = vv[-1] - vv[0]
    di_colors = [np.array(seed_bgr[sid], dtype=float) for sid in di_ids
                 if sid in seed_bgr]
    anchors = []
    for sid, tr in tracks.items():
        if sid in di_ids or sid not in med or sid not in seed_bgr:
            continue
        ref = np.array(seed_bgr[sid], dtype=float)
        if di_colors and min(float(np.linalg.norm(ref - c))
                             for c in di_colors) <= _SWAP_COLOR_DIST:
            continue  # paired paint: swappable itself, never an anchor
        if span[sid] < _SWAP_ANCHOR_MIN_RANGE_PX:
            continue  # pixel-flat: a frame ride, not a measured curve
        anchors.append(med[sid])
    if not anchors:
        return None
    ranked = sorted(anchors)
    if len(anchors) >= 2 and (ranked[-1] - ranked[0]
                              > _SWAP_ANCHOR_SPREAD_DB * px_per_db):
        return None
    return ranked[len(ranked) // 2]


def _swap_crossed_bands(tracks: dict[str, SeriesResult],
                        di_ids: set[str],
                        seed_bgr: dict[str, tuple[int, int, int]],
                        px_per_db: float) -> None:
    """Exchange samples of same-paint dB/DI pairs sitting in each other's band.

    A measured curve and its directivity sibling share one paint in two
    bands; the seed commits on colour alone, so the dB track can latch
    DI ink and the fenced DI re-track then takes the dB band, leaving
    both labels on the wrong curves with high support each. Unique-paint
    measured tracks cannot mislatch this way, so their tight level
    consensus judges the pairs: a DI member sitting in the measured band
    while its same-paint dB sibling sits a separated band away swaps
    samples (labels stay). Overlapping bands, loose consensus, thin
    support, and pixel-flat almost-tracks (frame rides) keep their
    tracks untouched.
    """
    from graphextract.schema import SegmentStatus

    consensus = _db_consensus(tracks, di_ids, seed_bgr, px_per_db)
    if consensus is None:
        return
    med: dict[str, float] = {}
    for sid, tr in tracks.items():
        vv = sorted(float(s.v) for s in tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS:
            med[sid] = vv[len(vv) // 2]
    db_ids = [sid for sid in tracks if sid not in di_ids]
    done: set[str] = set()
    for sid in sorted(di_ids):
        if sid not in med or sid not in seed_bgr or sid in done:
            continue
        ref = np.array(seed_bgr[sid], dtype=float)
        sib = next(
            (cand for cand in db_ids
             if cand in med and cand in seed_bgr and cand not in done
             and float(np.linalg.norm(
                 ref - np.array(seed_bgr[cand], dtype=float)))
             <= _SWAP_COLOR_DIST),
            None)
        if sib is None:
            continue
        sep = abs(med[sib] - med[sid]) / px_per_db
        if sep < _SWAP_MIN_SEP_DB:
            continue
        far = abs(med[sib] - consensus) / px_per_db
        near = abs(med[sid] - consensus) / px_per_db
        if near + _SWAP_MARGIN_DB >= far:
            continue
        done.add(sid)
        done.add(sib)
        tracks[sib].samples, tracks[sid].samples = (
            tracks[sid].samples, tracks[sib].samples)
        tracks[sib].confirmed, tracks[sid].confirmed = (
            tracks[sid].confirmed, tracks[sib].confirmed)
        tracks[sib].alternatives, tracks[sid].alternatives = (
            tracks[sid].alternatives, tracks[sib].alternatives)
        tracks[sib].review_reasons.append(
            f"same-paint band swap with {sid}: took its band "
            f"(was {far:.1f}dB off the measured consensus, "
            f"sibling {near:.1f}dB)")
        tracks[sid].review_reasons.append(
            f"same-paint band swap with {sib}: took its band "
            f"(was sitting in the measured band, "
            f"sibling {far:.1f}dB off)")


def _enforce_db_bands(tracks: dict[str, SeriesResult],
                      di_ids: set[str],
                      seed_bgr: dict[str, tuple[int, int, int]],
                      px_per_db: float,
                      gray: npt.NDArray,
                      layers,
                      interior: npt.NDArray,
                      track_config) -> None:
    """Re-track measured series latched in a foreign band.

    Same-paint measured siblings share one band; when one sits in the
    consensus band and another a separated band away, the far member
    latched foreign ink (a swap only fixes crossed dB/DI pairs, not a
    measured duplicate of a directivity track). The far member
    re-tracks behind its own observed path dilated past the band and
    keeps the re-track when it lands home with solid support,
    otherwise it keeps its samples and flags for review.
    """
    from dataclasses import replace as _replace

    from graphextract.schema import SegmentStatus
    from graphextract.tracking import track_sid_bidirectional

    consensus = _db_consensus(tracks, di_ids, seed_bgr, px_per_db)
    if consensus is None:
        return
    med: dict[str, float] = {}
    for sid, tr in tracks.items():
        vv = sorted(float(s.v) for s in tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS:
            med[sid] = vv[len(vv) // 2]
    db_ids = [sid for sid in tracks if sid not in di_ids]
    for sid in sorted(db_ids):
        if sid not in med or sid not in seed_bgr:
            continue
        if abs(med[sid] - consensus) / px_per_db < _ENFORCE_OFF_DB:
            continue
        ref = np.array(seed_bgr[sid], dtype=float)
        home = next(
            (cand for cand in db_ids
             if cand != sid and cand in med and cand in seed_bgr
             and float(np.linalg.norm(
                 ref - np.array(seed_bgr[cand], dtype=float)))
             <= _SWAP_COLOR_DIST
             and abs(med[cand] - consensus) / px_per_db <= _ENFORCE_HOME_DB
             and tracks[cand].observed_support()
             >= _ENFORCE_MIN_SUPPORT_FRAC * len(tracks[cand].samples)),
            None)
        if home is None:
            continue
        tr = tracks[sid]
        fence = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
        for s in tr.samples:
            if s.status is not SegmentStatus.OBSERVED:
                continue
            c, r = int(round(float(s.u))), int(round(float(s.v)))
            if 0 <= c < gray.shape[1] and 0 <= r < gray.shape[0]:
                fence[r, c] = 255
        fence = cv2.dilate(fence, np.ones((41, 41), np.uint8))
        fenced = _replace(
            layers,
            curve_masks={k: (m & ~fence) if k == sid else m
                         for k, m in layers.curve_masks.items()})
        alt = track_sid_bidirectional(
            gray, fenced, sid, float(np.median(gray)), track_config,
            {sid: seed_bgr[sid]}, interior)
        alt_tr = alt[sid]
        vv = sorted(float(s.v) for s in alt_tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS and (
                abs(vv[len(vv) // 2] - consensus) / px_per_db
                <= _ENFORCE_HOME_DB
                and alt_tr.observed_support()
                >= _ENFORCE_MIN_SUPPORT_FRAC * len(alt_tr.samples)):
            alt_tr.review_reasons.append(
                f"measured band enforcement: re-tracked off foreign ink "
                f"into the consensus band (was "
                f"{abs(med[sid] - consensus) / px_per_db:.1f}dB off)")
            alt_tr.label, alt_tr.panel_id = tr.label, tr.panel_id
            tracks[sid] = alt_tr
        else:
            tr.review_reasons.append(
                f"measured band enforcement refused: re-track "
                f"({alt_tr.observed_support()} observed) missed the "
                f"consensus band")


def _enforce_db_split(tracks: dict[str, SeriesResult],
                      di_ids: set[str],
                      seed_bgr: dict[str, tuple[int, int, int]],
                      split: int | None,
                      gray: npt.NDArray,
                      layers,
                      interior: npt.NDArray,
                      track_config) -> None:
    """Re-track measured series sitting fully past the band split.

    The evidence split separates the measured band from the offset
    directivity band by construction, so a measured track whose median
    observed row lies past the split latched foreign ink even when no
    same-paint home sibling exists for the consensus enforcement
    (dashed twins seed the far band first and never come back). The
    re-track fences the series' own observed path and every row past
    the split, then keeps the re-track when its median lands home with
    solid support; otherwise the samples stay and flag for review.
    A same-family or same-paint directivity twin must exist, else
    overlay plots (no split) and legitimately low measured curves keep
    their tracks untouched; the keep-condition is the backstop when
    the split itself misfired.
    """
    from dataclasses import replace as _replace

    from graphextract.schema import SegmentStatus
    from graphextract.tracking import track_sid_bidirectional

    if split is None:
        return
    med: dict[str, float] = {}
    for sid, tr in tracks.items():
        vv = sorted(float(s.v) for s in tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS:
            med[sid] = vv[len(vv) // 2]
    db_ids = [sid for sid in tracks if sid not in di_ids]
    for sid in sorted(db_ids):
        if sid not in med or sid not in seed_bgr:
            continue
        if med[sid] <= split:
            continue
        ref = np.array(seed_bgr[sid], dtype=float)
        fam = _family_words(tracks[sid].label or "")
        twin = next(
            (cand for cand in sorted(di_ids)
             if cand in med and cand in seed_bgr
             and (float(np.linalg.norm(
                 ref - np.array(seed_bgr[cand], dtype=float)))
                 <= _SWAP_COLOR_DIST
                 or (fam and (fam <= _family_words(
                     tracks[cand].label or "")
                     or _family_words(tracks[cand].label or "") <= fam)))),
            None)
        if twin is None:
            continue
        tr = tracks[sid]
        fence = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
        for s in tr.samples:
            if s.status is not SegmentStatus.OBSERVED:
                continue
            c, r = int(round(float(s.u))), int(round(float(s.v)))
            if 0 <= c < gray.shape[1] and 0 <= r < gray.shape[0]:
                fence[r, c] = 255
        fence = cv2.dilate(fence, np.ones((41, 41), np.uint8))
        fence[split + 1:, :] = 255
        union = (layers.union_mask & ~fence
                 if layers.union_mask is not None else None)
        fenced = _replace(
            layers, union_mask=union,
            curve_masks={k: (m & ~fence) if k == sid else m
                         for k, m in layers.curve_masks.items()})
        alt = track_sid_bidirectional(
            gray, fenced, sid, float(np.median(gray)), track_config,
            {sid: seed_bgr[sid]}, interior)
        alt_tr = alt[sid]
        vv = sorted(float(s.v) for s in alt_tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS and (
                vv[len(vv) // 2] < split
                and alt_tr.observed_support()
                >= _ENFORCE_MIN_SUPPORT_FRAC * len(alt_tr.samples)):
            alt_tr.review_reasons.append(
                f"measured split enforcement: re-tracked off foreign ink "
                f"above row {split} (twin {twin} holds the far band)")
            alt_tr.label, alt_tr.panel_id = tr.label, tr.panel_id
            tracks[sid] = alt_tr
        else:
            tr.review_reasons.append(
                f"measured split enforcement refused: re-track "
                f"({alt_tr.observed_support()} observed) missed the "
                f"home band past row {split}")


def _enforce_di_split(tracks: dict[str, SeriesResult],
                      di_ids: set[str],
                      seed_bgr: dict[str, tuple[int, int, int]],
                      split: int | None,
                      gray: npt.NDArray,
                      layers,
                      interior: npt.NDArray,
                      track_config) -> None:
    """Re-track directivity series sitting mostly past the split.

    Mirror of :func:`_enforce_db_split`: a directivity track whose
    median observed row lies above the split latched measured ink
    (dashed twins seed the far band first and never come back). The
    re-track fences the series' own observed path and every row above
    the split, then keeps the re-track when its median lands home with
    solid support; otherwise the samples stay and flag for review. A
    same-family or same-paint measured twin must exist, else
    legitimately high directivity curves keep their tracks untouched;
    the keep-condition is the backstop when the split itself misfired.
    """
    from dataclasses import replace as _replace

    from graphextract.schema import SegmentStatus
    from graphextract.tracking import track_sid_bidirectional

    if split is None:
        return
    med: dict[str, float] = {}
    for sid, tr in tracks.items():
        vv = sorted(float(s.v) for s in tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS:
            med[sid] = vv[len(vv) // 2]
    db_ids = [sid for sid in tracks if sid not in di_ids]
    for sid in sorted(di_ids):
        if sid not in med or sid not in seed_bgr:
            continue
        if med[sid] > split:
            continue
        ref = np.array(seed_bgr[sid], dtype=float)
        fam = _family_words(tracks[sid].label or "")
        twin = next(
            (cand for cand in sorted(db_ids)
             if cand in med and cand in seed_bgr
             and (float(np.linalg.norm(
                 ref - np.array(seed_bgr[cand], dtype=float)))
                 <= _SWAP_COLOR_DIST
                 or (fam and (fam <= _family_words(
                     tracks[cand].label or "")
                     or _family_words(tracks[cand].label or "") <= fam)))),
            None)
        if twin is None:
            continue
        tr = tracks[sid]
        fence = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
        for s in tr.samples:
            if s.status is not SegmentStatus.OBSERVED:
                continue
            c, r = int(round(float(s.u))), int(round(float(s.v)))
            if 0 <= c < gray.shape[1] and 0 <= r < gray.shape[0]:
                fence[r, c] = 255
        fence = cv2.dilate(fence, np.ones((41, 41), np.uint8))
        fence[:split + 1, :] = 255
        union = (layers.union_mask & ~fence
                 if layers.union_mask is not None else None)
        fenced = _replace(
            layers, union_mask=union,
            curve_masks={k: (m & ~fence) if k == sid else m
                         for k, m in layers.curve_masks.items()})
        alt = track_sid_bidirectional(
            gray, fenced, sid, float(np.median(gray)), track_config,
            {sid: seed_bgr[sid]}, interior)
        alt_tr = alt[sid]
        vv = sorted(float(s.v) for s in alt_tr.samples
                    if s.status is SegmentStatus.OBSERVED)
        if len(vv) >= _SWAP_MIN_OBS and (
                vv[len(vv) // 2] > split
                and alt_tr.observed_support()
                >= _ENFORCE_MIN_SUPPORT_FRAC * len(alt_tr.samples)):
            alt_tr.review_reasons.append(
                f"directivity split enforcement: re-tracked off foreign "
                f"ink below row {split} (twin {twin} holds the home band)")
            alt_tr.label, alt_tr.panel_id = tr.label, tr.panel_id
            tracks[sid] = alt_tr
        else:
            tr.review_reasons.append(
                f"directivity split enforcement refused: re-track "
                f"({alt_tr.observed_support()} observed) missed the "
                f"home band below row {split}")


def _prune_supplement_track(tr: SeriesResult) -> bool:
    """Drop phantom tracks from legend-free fallback seeding.

    Generic curve_N seeds cannot be verified by name, so structural
    phantoms must go by support: under twelve percent observed support
    (fringe and duplicate seeds, re-seed churn hopping same-hue
    fragments) or a pixel-flat observed path (a gridline latched
    instead of a curve). Legend-named series never reach here; they flag
    for review instead of vanishing.
    """
    from graphextract.schema import SegmentStatus

    n = len(tr.samples)
    if n == 0:
        return True
    obs_v = [float(s.v) for s in tr.samples
             if s.status is SegmentStatus.OBSERVED]
    if len(obs_v) < 0.12 * n:
        return True
    if len(obs_v) >= 50 and max(obs_v) - min(obs_v) < 3.0:
        return True
    return False


def _crop(img: npt.NDArray, xywh: tuple[int, int, int, int]) -> npt.NDArray:
    x, y, w, h = xywh
    return img[y:y + h, x:x + w]


def run_panel(
    img: npt.NDArray,
    panel_id: str,
    interior: npt.NDArray,
    interior_offset: tuple[int, int],
    anchors: AxisAnchors,
    styles: list[StyleSpec],
    track_config: TrackConfig | None = None,
    supplement_discovery: bool = False,
    exclude_words: Sequence[tuple[int, int, int, int]] = (),
    segmentor=None,
) -> PanelResult:
    """Run one panel; raises only on unexpected execution failure."""
    from graphextract.schema import PanelGeometry

    geometry = PanelGeometry(
        panel_id=panel_id,
        envelope_xywh=(0, 0, img.shape[1], img.shape[0]),
        interior_xywh=(interior_offset[0], interior_offset[1],
                       interior.shape[1], interior.shape[0]),
        image_width=img.shape[1],
        image_height=img.shape[0],
    )
    result = PanelResult(panel=geometry, provenance={"pipeline": PIPELINE_VERSION})
    if track_config is not None:
        active = [n for n in KNOWN_ASSUMPTIONS if getattr(track_config, n, False)]
        if active:
            result.provenance["assumptions"] = active
    calibration_resolved = True
    try:
        axes: dict[str, AxisFit] = {
            "x": fit_axis(anchors.x, AxisRole.X, anchors.x_unit or "unknown", anchors.x_scale),
            "y_left": fit_axis(anchors.y_left, AxisRole.Y_LEFT, anchors.y_unit or "unknown",
                               anchors.y_scale or ScaleType.LINEAR),
        }
    except CalibrationUnresolved as exc:
        calibration_resolved = False
        axes = {}
        result.outcome = PanelOutcome.PARTIAL_REVIEW
        result.review_reasons.append(f"calibration unresolved: {exc.reason}")
        result.review_reasons += [f"needed: {n}" for n in exc.needed]
    if calibration_resolved and anchors.y_right:
        # The second axis is decorative: a bad right fit must never take
        # down the calibrated main axes (PMC12's right ticks contradict).
        try:
            axes["y_right"] = fit_axis(anchors.y_right, AxisRole.Y_RIGHT,
                                       anchors.y_right_unit or "unknown",
                                       anchors.y_right_scale or ScaleType.LINEAR)
        except CalibrationUnresolved as exc:
            result.review_reasons.append(
                f"right axis uncalibrated, directivity stays on dB: {exc.reason}")

    _supplement = (supplement_discovery and styles and all(
        s.series_id.startswith("curve_") for s in styles))
    if _supplement:
        # Legend-free plots seed from hue peaks, which miss unsaturated
        # black/gray curves entirely. Long interior ink components recover
        # the unseeded curves generically; legend-named styles never reach
        # this path, and explicit --curve colours are never supplemented.
        from graphextract.semantics import seed_fallback_styles
        styles = list(styles) + seed_fallback_styles(
            interior, [s.bgr for s in styles], start=len(styles))
    from graphextract.evidence import detect_grid_mask_thin
    from graphextract.semantics import refine_seed_templates, snap_legend_seeds
    # The grid mask is 1px thin; seed colour measurement dilates past
    # frame skirts and dot halos, which otherwise vote as paint.
    seed_exclude = cv2.dilate(detect_grid_mask_thin(interior),
                              np.ones((5, 5), np.uint8))
    styles = snap_legend_seeds(interior, list(styles),
                               exclude_mask=seed_exclude)
    before = {s.series_id: tuple(s.bgr) for s in styles}
    styles = refine_seed_templates(interior, styles,
                                   exclude_mask=seed_exclude)
    moved = {sid: [before[sid], tuple(s.bgr)] for s in styles
             for sid in [s.series_id] if tuple(s.bgr) != before[sid]}
    if moved:
        result.provenance["seed_refinement"] = moved
    gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY) if interior.ndim == 3 else interior
    layers: EvidenceLayers = segment_evidence(interior, styles,
                                              exclude=exclude_words)
    if segmentor is not None:
        if track_config is None or track_config.backend != "temporal":
            raise ValueError("multilabel segmentor requires temporal tracking")
        if set(segmentor.series_ids) != {spec.series_id for spec in styles}:
            raise ValueError("checkpoint series IDs differ from panel; explicit matching required")
        from graphextract.torch_segmentor import predict_multilabel_probabilities
        layers.curve_probabilities = predict_multilabel_probabilities(segmentor, interior)
        result.provenance["segmentation"] = "multilabel_probabilities_gated_by_native_evidence"
    result.provenance["tracker"] = track_config.backend if track_config else "legacy"

    # Each series tracks against its own colour evidence independently:
    # joint assignment cannot disambiguate converged same-plot curves any
    # better than motion already does, while its ties resolve by set order
    # (init lottery with permanent lock-in). track_panel keeps its joint
    # form for direct multi-series callers.
    tracks: dict[str, SeriesResult] = {}
    di_ids = {s.series_id for s in styles
              if s.label and _axis_for_label(s.label) == "y_right"}
    for spec in styles:
        if spec.series_id in di_ids:
            continue
        tracks.update(track_sid_bidirectional(
            gray, layers, spec.series_id, float(np.median(gray)), track_config,
            {spec.series_id: spec.bgr}, interior))
    if di_ids:
        # Directivity ink shares hues with measured curves but lives in its
        # own offset band; dB tracks lock the shared hues first, so DI seeds
        # commit on dB fringe and can never jump bands. Track DI series
        # with dB-claimed ink masked: the seed then sees only unclaimed ink
        # and commits on its own band. Masking is about seeding, not the
        # axis: an anchored right axis never guides a colour seed, so a
        # same-paint DI seed latches dB ink with or without one.
        db_tracks = {sid: tr for sid, tr in tracks.items() if sid not in di_ids}
        observed_only = _claimed_mask(db_tracks, gray.shape[0], gray.shape[1],
                                      observed_only=True)
        full = _claimed_mask(db_tracks, gray.shape[0], gray.shape[1],
                             observed_only=False)
        # Identity commitment steers away from the measured band: at
        # a convergence the blob's leftover dB ink outscores the thin
        # DI dashes, so DI commits on impostor fringe and motion keeps
        # it in the dB band. The steer is a preference with a clean
        # fallback (see _clean_commit_flags), never an exclusion, so
        # overlay plots whose DI shares dB rows behave exactly as
        # before.
        avoid_half = max(_SEED_AVOID_MIN_PX,
                         int(round(gray.shape[0] * _SEED_AVOID_FRAC)))
        split = _band_split_row(
            [layers.curve_masks[sid] for s in styles
             for sid in [s.series_id]
             if sid not in di_ids and sid in layers.curve_masks],
            [layers.curve_masks[sid] for s in styles
             for sid in [s.series_id]
             if sid in di_ids and sid in layers.curve_masks],
            interior,
            [tuple(s.bgr) for s in styles if s.series_id not in di_ids],
            [tuple(s.bgr) for s in styles if s.series_id in di_ids])
        if split is None:
            di_avoid = None
        else:
            result.provenance["band_split_row"] = int(split)
            di_avoid = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
            di_avoid[:split + avoid_half + 1, :] = 255
        from dataclasses import replace as _replace
        # Sibling DI ink leaks across dark hues (dark-red dash cores
        # unmix into a dark-blue mask near full coverage), offering the
        # tracker a zero-motion attractor at every column so a weak
        # series never climbs its own rising dashes. Fence sibling ink
        # only where this series' own box-core is absent: true dashes
        # carry cores, so truth (including crossings and coincident
        # flats) is never fenced, while leak-only attractors are. The
        # keep-zone dilation covers dash pixels around each core.
        px_img = interior.astype(np.int16)
        own_keep: dict[str, npt.NDArray] = {}
        sib_union: dict[str, npt.NDArray] = {}
        for spec in styles:
            if spec.series_id not in di_ids:
                continue
            ref = np.array(spec.bgr, dtype=np.int16).reshape(1, 1, 3)
            tol = np.array(spec.channel_tol, dtype=np.int16).reshape(1, 1, 3)
            box = (np.all(np.abs(px_img - ref) <= tol, axis=2)
                   .astype(np.uint8)) * 255
            own_keep[spec.series_id] = cv2.dilate(box, np.ones((5, 5), np.uint8))
        for sid in di_ids:
            union = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
            for other, m in layers.curve_masks.items():
                if other in di_ids and other != sid:
                    union |= m
            sib_union[sid] = cv2.dilate(union, np.ones((3, 3), np.uint8))

        def _masked(mask: npt.NDArray):
            zeros = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
            return _replace(
                layers,
                curve_masks={sid: (m & ~mask
                                   & ~(sib_union[sid] & ~own_keep.get(sid, zeros)))
                                   if sid in di_ids else m
                             for sid, m in layers.curve_masks.items()})
        for spec in styles:
            if spec.series_id not in di_ids:
                continue
            tracks.update(track_sid_bidirectional(
                gray, _masked(observed_only), spec.series_id,
                float(np.median(gray)), track_config,
                {spec.series_id: spec.bgr}, interior,
                ({spec.series_id: di_avoid}
                 if di_avoid is not None else None)))
            tracks[spec.series_id].review_reasons.append(
                "directivity re-track with dB-claimed ink masked")
            if tracks[spec.series_id].observed_support() < 0.15 * len(
                    tracks[spec.series_id].samples):
                # Starved: dB measurements alone did not fence the seed
                # (fragmented dB evidence leaves its ink unclaimed), so
                # retry behind the full dB path and keep the stronger
                # track. Either way the support lands in the review queue.
                alt = track_sid_bidirectional(
                    gray, _masked(full), spec.series_id,
                    float(np.median(gray)), track_config,
                    {spec.series_id: spec.bgr}, interior,
                    ({spec.series_id: di_avoid}
                     if di_avoid is not None else None))
                if alt[spec.series_id].observed_support() > tracks[
                        spec.series_id].observed_support():
                    tracks.update(alt)
                    tracks[spec.series_id].review_reasons.append(
                        "directivity re-track kept full-path mask variant")
        # Mutual fencing, other direction: close hues (orange PIR vs
        # dark-red SPDI) match each other's edge pixels, so a dB seed at
        # the far edge can commit on DI-band ink and ride it for the
        # whole pass. Re-track dB series whose path touches DI-claimed
        # ink behind the full DI path mask and keep the stronger track;
        # series nowhere near DI ink skip the extra pass. The fence uses
        # the full path (interpolated filler bridges dash gaps, where
        # unfenced fringe would otherwise seed a hijack) dilated past
        # pale skirts; with the impostor band gone the re-track loosens
        # its re-seed gate to admit washed truth.
        from graphextract.tracking import _CONFIRM_TOL as _RESEED_LOOSE
        di_only = {sid: tr for sid, tr in tracks.items() if sid in di_ids}
        di_claimed = _claimed_mask(di_only, gray.shape[0], gray.shape[1],
                                   observed_only=False)
        di_claimed = cv2.dilate(di_claimed, np.ones((17, 17), np.uint8))
        if split is None:
            db_avoid = None
        else:
            db_avoid = np.zeros((gray.shape[0], gray.shape[1]), np.uint8)
            db_avoid[split + avoid_half:, :] = 255
        if di_claimed.any():
            fenced = _replace(
                layers,
                curve_masks={sid: (m & ~di_claimed) if sid not in di_ids else m
                             for sid, m in layers.curve_masks.items()})
            if track_config is None:
                fenced_cfg = TrackConfig(reseed_tol=_RESEED_LOOSE)
            else:
                fenced_cfg = _replace(track_config, reseed_tol=_RESEED_LOOSE)
            for spec in styles:
                if spec.series_id in di_ids:
                    continue
                tr = tracks.get(spec.series_id)
                if tr is None:
                    continue
                touches = False
                for s in tr.samples:
                    c, r = int(round(float(s.u))), int(round(float(s.v)))
                    if (0 <= c < gray.shape[1] and 0 <= r < gray.shape[0]
                            and di_claimed[r, c]):
                        touches = True
                        break
                if not touches:
                    continue
                alt = track_sid_bidirectional(
                    gray, fenced, spec.series_id, float(np.median(gray)),
                    fenced_cfg, {spec.series_id: spec.bgr}, interior,
                    ({spec.series_id: db_avoid}
                     if db_avoid is not None else None))
                alt_tr = alt[spec.series_id]
                if alt_tr.observed_support() > tr.observed_support():
                    alt_tr.review_reasons.append(
                        "measured re-track with DI-claimed ink masked")
                    tracks[spec.series_id] = alt_tr
                else:
                    tr.review_reasons.append(
                        "measured re-track with DI-claimed ink masked refused "
                        f"({alt_tr.observed_support()} vs "
                        f"{tr.observed_support()} observed)")
    ox, oy = interior_offset
    if track_config is not None and track_config.no_jump:
        dupes = resolve_duplicate_claims(
            tracks, track_config.max_jump_px,
            {sid: tr.confirmed for sid, tr in tracks.items()})
        for sid, idx in dupes.items():
            if idx:
                tracks[sid].review_reasons.append(
                    f"duplicate_claim: {len(idx)} shared-ink samples demoted to missing")
    for sid, tr in tracks.items():
        tr.panel_id = panel_id
        style = next((x for x in styles if x.series_id == sid), None)
        if style:
            tr.label = style.label
    # Duplicate suppression first: the offset identity solves on measured
    # samples, and same-paint dB latches must not vote in it.
    _demote_di_duplicates(tracks, di_ids, interior,
                          {s.series_id: s.bgr for s in styles})
    _demote_thin_di_samples(tracks, di_ids)
    left_fit = axes.get("y_left") if calibration_resolved else None
    if left_fit is not None and di_ids:
        _swap_crossed_bands(tracks, di_ids,
                            {s.series_id: s.bgr for s in styles},
                            abs(left_fit.a))
        _enforce_db_bands(tracks, di_ids,
                          {s.series_id: s.bgr for s in styles},
                          abs(left_fit.a), gray, layers, interior,
                          track_config)
        _enforce_db_split(tracks, di_ids,
                          {s.series_id: s.bgr for s in styles},
                          split, gray, layers, interior,
                          track_config)
        _enforce_di_split(tracks, di_ids,
                          {s.series_id: s.bgr for s in styles},
                          split, gray, layers, interior,
                          track_config)
    yr = axes.get("y_right")
    if calibration_resolved and ("y_right" not in axes
                                 or (yr is not None and yr.unit == "unknown")):
        # A right axis with unknown unit is decorative ticks, not a
        # measurement: verified offset identity supersedes it, while a
        # failed proof keeps the anchored fit as fallback.
        _recover_di_right_axis(result, axes, tracks)
    yr = axes.get("y_right")
    if (yr is not None and yr.unit == "unknown" and yr.method != "di_offset_identity"
            and any(_axis_for_label((tr.label or "")) == "y_right"
                    for tr in tracks.values())):
        # An anchored right axis carrying directivity curves measures dB:
        # DI is a difference of dB curves, whatever the tick labels say.
        yr.unit = "dB"
        result.provenance["y_right_unit_inferred"] = "dB"
    if track_config is not None and track_config.backend == "temporal":
        from graphextract.temporal import mark_indistinguishable
        mark_indistinguishable(tracks, {s.series_id: s.bgr for s in styles})
    for sid, tr in tracks.items():
        if _supplement and _prune_supplement_track(tr):
            result.review_reasons.append(
                f"{sid}: phantom supplement seed dropped "
                f"({tr.observed_support()}/{len(tr.samples)} observed)")
            continue
        if "y_right" in axes:
            tr.axis_id = _axis_for_label(tr.label or "")
        if calibration_resolved:
            xfit, yfit = axes["x"], axes.get(tr.axis_id, axes["y_left"])
        for sequence in [tr.samples, *tr.alternatives]:
            for s in sequence:
                if calibration_resolved:
                    s.value_x = xfit.invert(s.u)
                    s.value_y = yfit.invert(s.v)
                s.u += ox
                s.v += oy
        result.series.append(tr)
        if tr.review_reasons:
            result.review_reasons += [f"{sid}: {r}" for r in tr.review_reasons]

    result.axes = axes
    result.provenance["anchor_source"] = anchors.source
    verified = anchors.source in ("user_verified", "renderer_verified_test")
    low_support = any(
        t.observed_support() < 0.5 * len(t.samples) for t in result.series
    )
    if not verified:
        result.outcome = PanelOutcome.PARTIAL_REVIEW
        result.review_reasons.append(f"anchor source '{anchors.source}' is not verified")
    elif low_support or result.review_reasons:
        result.outcome = PanelOutcome.PARTIAL_REVIEW
    else:
        result.outcome = PanelOutcome.COMPLETE
    return result


def run_document(
    img: npt.NDArray,
    image_id: str,
    styles: list[StyleSpec],
    anchor_provider: AnchorProvider | None = None,
    track_config: TrackConfig | None = None,
    words: Sequence[OCRWord] | None = None,
    supplement_discovery: bool = False,
    segmentor=None,
) -> DocumentResult:
    """End-to-end image-only extraction with per-panel failure isolation.

    ``words`` (optional full-image OCR words in image-global coordinates)
    feeds tick-stack panel splits and margin-aware anchor recovery: tick
    labels live outside the plot frame, so margin words always merge into
    the provider result and the robust fit keeps the consistent majority.
    """
    provider = anchor_provider or _empty_anchors
    sha = hashlib.sha256(np.ascontiguousarray(img).tobytes()).hexdigest()
    doc = DocumentResult(document_id=image_id, image_id=image_id,
                         image_width=img.shape[1], image_height=img.shape[0],
                         image_sha256=sha,
                         provenance={"pipeline": PIPELINE_VERSION,
                                     "oracle_inputs_used": False})
    try:
        panels = detect_panels(img, image_id, words=words)
    except Exception as exc:  # detection itself failed: single failed panel entry
        failed = PanelResult(
            panel=__import__("graphextract.schema", fromlist=["PanelGeometry"]).PanelGeometry(
                panel_id=f"{image_id}#p0", envelope_xywh=(0, 0, img.shape[1], img.shape[0]),
                interior_xywh=(0, 0, img.shape[1], img.shape[0]),
                image_width=img.shape[1], image_height=img.shape[0]),
            outcome=PanelOutcome.FAILED, review_reasons=[f"panel detection failed: {exc}"])
        doc.panels.append(failed)
        return doc
    if not panels:
        return doc
    for pg in panels:
        interior = _crop(img, pg.interior_xywh)
        try:
            anchors = provider(pg.panel_id, interior)
            if words is not None:
                # Margin words are the real tick evidence (interior-only
                # reads trap legend digits as phantom anchors), so margin
                # recovery always merges in: the robust fit keeps the
                # consistent majority either way.
                from graphextract.ocr_adapters import recover_margin_anchors
                anchors = _merge_anchors(
                    anchors, recover_margin_anchors(img, words, pg, interior))
            ox, oy = pg.interior_xywh[0], pg.interior_xywh[1]
            iw, ih = interior.shape[1], interior.shape[0]
            local_words: list[tuple[int, int, int, int]] = []
            if words is not None:
                # Text ink is never curve ink: legend words/keys and
                # in-plot tick digits mask out of tracking evidence, so
                # tracks bridge the occlusion instead of latching text.
                for wd in words:
                    lx, ly = wd.x - ox, wd.y - oy
                    if lx < iw and ly < ih and lx + wd.w > 0 and ly + wd.h > 0:
                        local_words.append((lx, ly, wd.w, wd.h))
            for style in styles:
                # Legend key dashes inside the panel are series-coloured
                # ink that is not the curve: mask them like words so the
                # series cannot seed or latch on its own key.
                if style.key_xywh is not None:
                    kx, ky, kw, kh = style.key_xywh
                    lx, ly = kx - ox, ky - oy
                    if lx < iw and ly < ih and lx + kw > 0 and ly + kh > 0:
                        local_words.append((lx, ly, kw, kh))
            res = run_panel(img, pg.panel_id, interior, (ox, oy),
                            anchors, styles, track_config,
                            supplement_discovery=supplement_discovery,
                            exclude_words=local_words, segmentor=segmentor)
            res.panel = pg  # keep detector's envelope/interior + confidence
        except Exception as exc:
            res = PanelResult(panel=pg, outcome=PanelOutcome.FAILED,
                              review_reasons=[f"execution failure: {type(exc).__name__}: {exc}"])
        doc.panels.append(res)
    return doc


def manifest(doc: DocumentResult) -> dict:
    """Machine-readable run manifest with review queue and provenance."""
    queue: list[dict] = []
    for p in doc.panels:
        for reason in p.review_reasons:
            queue.append({"panel_id": p.panel.panel_id, "reason": reason})
        for s in p.series:
            for reason in s.review_reasons:
                queue.append({"panel_id": p.panel.panel_id,
                              "series_id": s.series_id, "reason": reason})
    return {
        "pipeline": PIPELINE_VERSION,
        "oracle_inputs_used": False,
        "document_id": doc.document_id,
        "image_id": doc.image_id,
        "panels": [
            {"panel_id": p.panel.panel_id, "outcome": p.outcome.value,
             "n_series": len(p.series),
             "observed_support": {s.series_id: s.observed_support() for s in p.series},
             "review_reasons": p.review_reasons}
            for p in doc.panels
        ],
        "review_queue": queue,
    }
