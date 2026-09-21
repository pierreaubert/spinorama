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


AnchorProvider = Callable[[str, npt.NDArray], AxisAnchors]


_DI_LABEL_TOKENS = frozenset({"directivity", "index", "di", "dl"})
"""Label words marking a directivity curve (right-hand axis).

``dl`` covers Tesseract's common misread of the ``DI`` suffix
(``Reflections Dl``); whole-word matching keeps labels like
``Estimated In-Room`` on the left axis.
"""


def _axis_for_label(label: str) -> str:
    """Right-hand axis for directivity labels, left axis otherwise."""
    import re
    # Tesseract drops inter-word spaces ('OnAxis', 'PowerDI') and reads
    # capital I as a pipe ('PowerD|'): split camel boundaries and fold
    # pipes before tokenising, so fused DI suffixes still route right.
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
                  " ", label.replace("|", "I"))
    tokens = text.lower().replace("-", " ").split()
    if any(t in _DI_LABEL_TOKENS for t in tokens):
        return "y_right"
    return "y_left"


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
    """
    from graphextract.calibration import parse_di_offset, solve_di_offset
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
    for tr in di_tracks:
        explicit = parse_di_offset(tr.label or "")
        if explicit is not None:
            solved[tr.series_id] = explicit
            stated.add(tr.series_id)
            continue
        pix = {s.u: s.v for s in tr.samples
               if s.status is SegmentStatus.OBSERVED}
        hit = solve_di_offset(pix, refs, left.a, left.b)
        if hit is None:
            tr.review_reasons.append(
                "directivity offset unidentified: no reference pair explains "
                "this track; stays on dB")
            continue
        off, (la, lb), iqr, n = hit
        # A parallel measured curve can solve as DI with the offset of a
        # flat reference: accept the identity only when the implied DI
        # values sit in a plausible directivity range.
        divals = [(v - left.b) / left.a - off for v in pix.values()]
        med = float(np.median(divals))
        iqr_v = float(np.subtract(*np.percentile(divals, [75, 25])))
        if not (-15.0 <= med <= 30.0 and iqr_v <= 15.0):
            tr.review_reasons.append(
                f"directivity offset {off:.1f}dB rejected: implied DI "
                f"median {med:.1f}dB outside plausible range; stays on dB")
            continue
        solved[tr.series_id] = off
        tr.review_reasons.append(
            f"directivity offset {off:.1f}dB from {la} - {lb} "
            f"(IQR {iqr:.2f}dB, n={n})")
    if not solved:
        return
    pool = [off for sid, off in solved.items() if sid in stated] or list(solved.values())
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


def _prune_supplement_track(tr: SeriesResult) -> bool:
    """Drop phantom tracks from legend-free fallback seeding.

    Generic curve_N seeds cannot be verified by name, so structural
    phantoms must go by support: near-zero observed support (fringe and
    duplicate seeds) or a pixel-flat observed path (a gridline latched
    instead of a curve). Legend-named series never reach here; they flag
    for review instead of vanishing.
    """
    from graphextract.schema import SegmentStatus

    n = len(tr.samples)
    if n == 0:
        return True
    obs_v = [float(s.v) for s in tr.samples
             if s.status is SegmentStatus.OBSERVED]
    if len(obs_v) < 0.05 * n:
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
                               ScaleType.LINEAR),
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
                                       ScaleType.LINEAR)
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
    from graphextract.semantics import snap_legend_seeds
    styles = snap_legend_seeds(interior, list(styles))
    gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY) if interior.ndim == 3 else interior
    layers: EvidenceLayers = segment_evidence(interior, styles)
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
        tracks.update(track_panel(gray, layers, [spec.series_id],
                                  float(np.median(gray)), track_config,
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
            tracks.update(track_panel(gray, _masked(observed_only), [spec.series_id],
                                      float(np.median(gray)), track_config,
                                      {spec.series_id: spec.bgr}, interior))
            tracks[spec.series_id].review_reasons.append(
                "directivity re-track with dB-claimed ink masked")
            if tracks[spec.series_id].observed_support() < 0.15 * len(
                    tracks[spec.series_id].samples):
                # Starved: dB measurements alone did not fence the seed
                # (fragmented dB evidence leaves its ink unclaimed), so
                # retry behind the full dB path and keep the stronger
                # track. Either way the support lands in the review queue.
                alt = track_panel(gray, _masked(full), [spec.series_id],
                                  float(np.median(gray)), track_config,
                                  {spec.series_id: spec.bgr}, interior)
                if alt[spec.series_id].observed_support() > tracks[
                        spec.series_id].observed_support():
                    tracks.update(alt)
                    tracks[spec.series_id].review_reasons.append(
                        "directivity re-track kept full-path mask variant")
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
    yr = axes.get("y_right")
    if calibration_resolved and ("y_right" not in axes
                                 or (yr is not None and yr.unit == "unknown")):
        # A right axis with unknown unit is decorative ticks, not a
        # measurement: verified offset identity supersedes it, while a
        # failed proof keeps the anchored fit as fallback.
        _recover_di_right_axis(result, axes, tracks)
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
        for s in tr.samples:
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
            res = run_panel(img, pg.panel_id, interior,
                            (pg.interior_xywh[0], pg.interior_xywh[1]),
                            anchors, styles, track_config,
                            supplement_discovery=supplement_discovery)
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
