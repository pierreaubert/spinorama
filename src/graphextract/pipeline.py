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


def _empty_anchors(_panel_id: str, _img: npt.NDArray) -> AxisAnchors:
    return AxisAnchors()


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
        if anchors.y_right:
            axes["y_right"] = fit_axis(anchors.y_right, AxisRole.Y_RIGHT,
                                       anchors.y_right_unit or "unknown", ScaleType.LINEAR)
    except CalibrationUnresolved as exc:
        calibration_resolved = False
        axes = {}
        result.outcome = PanelOutcome.PARTIAL_REVIEW
        result.review_reasons.append(f"calibration unresolved: {exc.reason}")
        result.review_reasons += [f"needed: {n}" for n in exc.needed]

    gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY) if interior.ndim == 3 else interior
    layers: EvidenceLayers = segment_evidence(interior, styles)
    # Each series tracks against its own colour evidence independently:
    # joint assignment cannot disambiguate converged same-plot curves any
    # better than motion already does, while its ties resolve by set order
    # (init lottery with permanent lock-in). track_panel keeps its joint
    # form for direct multi-series callers.
    tracks: dict[str, SeriesResult] = {}
    for spec in styles:
        tracks.update(track_panel(gray, layers, [spec.series_id],
                                  float(np.median(gray)), track_config,
                                  {spec.series_id: spec.bgr}, interior))
    ox, oy = interior_offset
    if track_config is not None and track_config.no_jump:
        dupes = resolve_duplicate_claims(tracks, track_config.max_jump_px)
        for sid, idx in dupes.items():
            if idx:
                tracks[sid].review_reasons.append(
                    f"duplicate_claim: {len(idx)} shared-ink samples demoted to missing")
    for sid, tr in tracks.items():
        tr.panel_id = panel_id
        style = next((x for x in styles if x.series_id == sid), None)
        if style:
            tr.label = style.label
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
) -> DocumentResult:
    """End-to-end image-only extraction with per-panel failure isolation.

    ``words`` (optional full-image OCR words in image-global coordinates)
    feeds tick-stack panel splits and, when a panel's provider yields no
    anchors at all, margin-aware anchor recovery: tick labels live outside
    the plot frame, so interior-only reads stay empty on real charts. An
    explicit provider result always wins; words only fill a total void.
    """
    from graphextract.ocr_adapters import panel_anchors_from_words

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
            if words is not None and not anchors.x and not anchors.y_left and not anchors.y_right:
                anchors = panel_anchors_from_words(words, pg, interior)
            res = run_panel(img, pg.panel_id, interior,
                            (pg.interior_xywh[0], pg.interior_xywh[1]),
                            anchors, styles, track_config)
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
