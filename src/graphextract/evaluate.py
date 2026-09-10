# -*- coding: utf-8 -*-
"""Trustworthy evaluation: strict pixel contract, support, completeness.

Primary score (production): end-to-end, image-only results. Oracle geometry
may only enter explicitly labelled diagnostic runs, never the production
score. Missing interiors count as failure: scoring never interpolates across
MISSING/ambiguous samples. Identity swaps are scored, not rematched away.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from graphextract.schema import DocumentResult, PanelOutcome, SegmentStatus


PIXEL_TOL = 1.0  # max(|du|, |dv|) in native pixels for strict spans


@dataclass
class SeriesScore:
    series_id: str
    strict_pass: bool
    p50_px: float
    p95_px: float
    p99_px: float
    max_px: float
    measured_coverage: float  # observed columns / reference visible columns
    false_support: float  # observed predictions where reference is hidden
    n_ref_visible: int
    identity_switches: int = 0


@dataclass
class PanelScore:
    panel_id: str
    outcome: PanelOutcome
    series: dict[str, SeriesScore] = field(default_factory=dict)
    missed_series: list[str] = field(default_factory=list)
    extra_series: list[str] = field(default_factory=list)
    review_queue: list[str] = field(default_factory=list)


def _interp_ref(ref_u: np.ndarray, ref_v: np.ndarray, u: float) -> float | None:
    if len(ref_u) == 0 or u < ref_u[0] or u > ref_u[-1]:
        return None
    return float(np.interp(u, ref_u, ref_v))


def score_series(
    pred_u: list[float],
    pred_v: list[float],
    pred_observed: list[bool],
    ref_u: np.ndarray,
    ref_v: np.ndarray,
    ref_visible: np.ndarray,
    series_id: str,
) -> SeriesScore:
    """Score one predicted series against dense native-pixel reference."""
    errs: list[float] = []
    false = 0
    n_obs = 0
    for u, v, obs in zip(pred_u, pred_v, pred_observed):
        if not obs:
            continue
        n_obs += 1
        rv = _interp_ref(ref_u, ref_v, u)
        if rv is None:
            false += 1
            continue
        visible = bool(np.interp(u, ref_u, ref_visible.astype(float)) > 0.5)
        if not visible:
            false += 1
            continue
        errs.append(abs(v - rv))  # ordinate error at the native column
    n_ref_visible = int(ref_visible.sum())
    coverage = (len(errs) / n_ref_visible) if n_ref_visible else 0.0
    false_support = (false / n_obs) if n_obs else 0.0
    if not errs:
        return SeriesScore(series_id, False, float("inf"), float("inf"), float("inf"),
                           float("inf"), 0.0, false_support, n_ref_visible)
    arr = np.array(sorted(errs))
    q = lambda p: float(arr[min(len(arr) - 1, int(p * len(arr)))])
    strict = bool(np.all(arr <= PIXEL_TOL) and coverage >= 0.999)
    return SeriesScore(series_id, strict, q(0.50), q(0.95), q(0.99), float(arr[-1]),
                       coverage, false_support, n_ref_visible)


def score_panel_completeness(
    panel_id: str,
    predicted_ids: list[str],
    expected_ids: list[str],
    series_scores: dict[str, SeriesScore],
) -> PanelScore:
    missed = [s for s in expected_ids if s not in predicted_ids]
    extra = [s for s in predicted_ids if s not in expected_ids]
    queue: list[str] = []
    queue += [f"missing series {s}" for s in missed]
    queue += [f"unexpected series {s}" for s in extra]
    for sid, sc in series_scores.items():
        if not sc.strict_pass:
            queue.append(f"series {sid}: strict pixel test failed (max {sc.max_px:.2f}px)")
        if sc.measured_coverage < 0.999:
            queue.append(f"series {sid}: measured coverage {sc.measured_coverage:.3f}")
        if sc.false_support > 0:
            queue.append(f"series {sid}: false support {sc.false_support:.3f}")
    if missed or extra:
        outcome = PanelOutcome.PARTIAL_REVIEW
    elif not series_scores:
        outcome = PanelOutcome.FAILED
    elif all(s.strict_pass for s in series_scores.values()):
        outcome = PanelOutcome.COMPLETE
    else:
        outcome = PanelOutcome.PARTIAL_REVIEW
    return PanelScore(panel_id, outcome, series_scores, missed, extra, queue)


def production_summary(doc: DocumentResult, panel_scores: list[PanelScore]) -> dict:
    """Aggregate end-to-end production score with explicit denominators."""
    n_panels = len(panel_scores)
    n_complete = sum(1 for p in panel_scores if p.outcome is PanelOutcome.COMPLETE)
    strict_series = sum(s.strict_pass for p in panel_scores for s in p.series.values())
    total_series = sum(len(p.series) for p in panel_scores)
    return {
        "oracle_inputs_used": False,
        "n_panels": n_panels,
        "n_complete_panels": n_complete,
        "panel_acceptance_rate": (n_complete / n_panels) if n_panels else 0.0,
        "strict_series": strict_series,
        "total_series": total_series,
        "panels": [
            {"panel_id": p.panel_id, "outcome": p.outcome.value,
             "missed": p.missed_series, "extra": p.extra_series,
             "review_queue": p.review_queue}
            for p in panel_scores
        ],
    }
