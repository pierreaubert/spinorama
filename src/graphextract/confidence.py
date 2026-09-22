# -*- coding: utf-8 -*-
"""Confidence calibration for automatic acceptance (plan-20260810, section 9).

Confidence estimates the joint event of correct geometry, calibration, and
identity. This module fits that estimator on *observed outcomes* (strict
pass/fail on gold), never on softmax scores or ensemble agreement. Features
are production-computable (no truth input); labels come from gold evaluation.

Automatic acceptance needs a calibrated threshold: the plan's production claim
(~99.5% acceptance precision) requires hundreds of independent cases, so
``select_threshold`` reports the empirical precision/coverage trade-off and
refuses targets the calibration set cannot substantiate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from sklearn.linear_model import LogisticRegression
from scipy.stats import beta

from graphextract.schema import PanelOutcome, PanelResult, SegmentStatus

FEATURES = (
    "support_frac",
    "calib_resid_px",
    "n_review",
    "min_anchor_conf",
    "has_duplicates",
    "n_series",
    "min_support_frac",
    "max_missing_run_frac",
    "alternative_frac",
)


def panel_features(panel: PanelResult) -> dict[str, float]:
    """Production-computable acceptance features for one panel."""
    supports = [s.observed_support() / max(1, len(s.samples)) for s in panel.series]
    support_frac = float(np.mean(supports)) if supports else 0.0
    resid = max([f.residual_px_max for f in panel.axes.values()] or [0.0])
    if not panel.axes:
        resid = 99.0  # uncalibrated: worst-case sentinel, never hidden
    confs = [t.confidence for f in panel.axes.values() for t in f.anchors_used]
    dup = any("duplicate" in r for s in panel.series for r in s.review_reasons)
    longest = 0.0
    for series in panel.series:
        run = best = 0
        for sample in series.samples:
            run = run + 1 if sample.status is not SegmentStatus.OBSERVED else 0
            best = max(best, run)
        longest = max(longest, best / max(1, len(series.samples)))
    return {
        "min_support_frac": min(supports, default=0.0),
        "max_missing_run_frac": longest,
        "alternative_frac": sum(bool(s.alternatives) for s in panel.series)
        / max(1, len(panel.series)),
        "support_frac": support_frac,
        "calib_resid_px": float(resid),
        "n_review": float(
            len(panel.review_reasons) + sum(len(s.review_reasons) for s in panel.series)
        ),
        "min_anchor_conf": float(min(confs)) if confs else 0.0,
        "has_duplicates": float(dup),
        "n_series": float(len(panel.series)),
    }


def feature_matrix(panels: list[PanelResult]) -> npt.NDArray:
    return np.array([[panel_features(p)[k] for k in FEATURES] for p in panels])


class ConfidenceCalibrator:
    """Logistic P(strict pass) over acceptance features, fit on gold outcomes."""

    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=2000)
        self._fit = False

    def fit(self, panels: list[PanelResult], labels: list[bool]) -> dict:
        """Fit on gold outcomes; returns Brier score vs a constant baseline."""
        if len(panels) < 3:
            raise ValueError("need at least 3 calibration panels")
        if len(set(labels)) < 2:
            raise ValueError("calibration labels must contain both outcomes")
        X = feature_matrix(panels)
        y = np.array(labels, dtype=int)
        self.model.fit(X, y)
        self._fit = True
        proba = self.model.predict_proba(X)[:, 1]
        brier = float(np.mean((proba - y) ** 2))
        base = float(np.mean((y.mean() - y) ** 2))
        return {"brier": brier, "baseline_brier": base, "n": len(y)}

    def predict_proba(self, panels: list[PanelResult]) -> npt.NDArray:
        if not self._fit:
            raise ValueError("calibrator is not fit")
        return self.model.predict_proba(feature_matrix(panels))[:, 1]

    def save(self, path: str | Path) -> Path:
        if not self._fit:
            raise ValueError("calibrator is not fit")
        p = Path(path)
        np.savez(
            p,
            coef=self.model.coef_,
            intercept=self.model.intercept_,
            classes=self.model.classes_,
            features=np.array(FEATURES),
        )
        return p

    @staticmethod
    def load(path: str | Path) -> ConfidenceCalibrator:
        z = np.load(path, allow_pickle=True)
        if tuple(z["features"].tolist()) != FEATURES:
            raise ValueError("confidence feature schema changed; refit the calibrator")
        cal = ConfidenceCalibrator()
        cal.model.coef_, cal.model.intercept_, cal.model.classes_ = (
            z["coef"],
            z["intercept"],
            z["classes"],
        )
        cal._fit = True
        return cal


@dataclass
class AcceptancePoint:
    threshold: float
    precision: float
    coverage: float
    n_accepted: int
    precision_lower_bound: float
    confidence: float
    stage: str


def _validation_arrays(probas, labels, target_precision, confidence, min_accepted):
    p = np.asarray(probas, dtype=float)
    y = np.asarray(labels, dtype=bool)
    if p.ndim != 1 or y.shape != p.shape or not len(p):
        raise ValueError("non-empty, equally sized 1D probabilities and labels required")
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("probabilities must be finite and in [0, 1]")
    if not 0 < target_precision <= 1 or not 0 < confidence < 1 or min_accepted < 1:
        raise ValueError("invalid precision, confidence, or minimum support")
    return p, y


def _acceptance_point(p, y, threshold, alpha, confidence, stage):
    accepted = p >= threshold
    n = int(accepted.sum())
    k = int(y[accepted].sum())
    lower = float(beta.ppf(alpha, k, n - k + 1)) if k else 0.0
    return AcceptancePoint(
        float(threshold), k / n if n else 0.0, n / len(y), n, lower, confidence, stage
    )


def select_threshold(
    probas: npt.NDArray,
    labels: list[bool],
    target_precision: float = 0.995,
    *,
    confidence: float = 0.95,
    min_accepted: int = 30,
) -> AcceptancePoint:
    """Select on calibration data; simultaneous one-sided exact binomial bounds.

    Bonferroni correction accounts for searching several thresholds. Labels must
    be independent cases, not pixels/crops from the same source. A selected
    threshold still needs validate_threshold on a disjoint, untouched test set.
    The classifier itself must be fit on a separate training set.
    """
    p, y = _validation_arrays(probas, labels, target_precision, confidence, min_accepted)
    candidates = np.unique(p)
    alpha = (1 - confidence) / len(candidates)
    for threshold in candidates:  # ascending: maximum accepted coverage first
        point = _acceptance_point(p, y, threshold, alpha, confidence, "calibration")
        if point.n_accepted >= min_accepted and point.precision_lower_bound >= target_precision:
            return point
    raise ValueError(
        f"target precision {target_precision} not substantiated by confidence "
        f"bounds on {len(y)} calibration cases"
    )


def validate_threshold(
    probas,
    labels,
    threshold: float,
    target_precision: float = 0.995,
    *,
    confidence: float = 0.95,
    min_accepted: int = 30,
) -> AcceptancePoint:
    """Validate a previously frozen threshold once on independent held-out cases."""
    p, y = _validation_arrays(probas, labels, target_precision, confidence, min_accepted)
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite and in [0, 1]")
    point = _acceptance_point(p, y, threshold, 1 - confidence, confidence, "held_out")
    if point.n_accepted < min_accepted or point.precision_lower_bound < target_precision:
        raise ValueError("held-out cases do not substantiate the frozen acceptance threshold")
    return point


def auto_acceptable(
    panel: PanelResult, calibrator: ConfidenceCalibrator, threshold: AcceptancePoint
) -> bool:
    """Conservative runtime gate requiring a held-out validation result.

    A raw float or a threshold merely selected on calibration data is not an
    acceptance certificate. Persist the validation result alongside the model.
    """
    if not isinstance(threshold, AcceptancePoint) or threshold.stage != "held_out":
        return False
    if (
        panel.outcome is not PanelOutcome.COMPLETE
        or not panel.series
        or panel.review_reasons
        or "x" not in panel.axes
    ):
        return False
    if not np.isfinite(threshold.threshold) or not 0 <= threshold.threshold <= 1:
        return False
    if any(
        not np.isfinite([fit.a, fit.b, fit.residual_px_max]).all() or fit.a == 0
        for fit in panel.axes.values()
    ):
        return False
    for series in panel.series:
        if (
            series.axis_id not in panel.axes
            or not series.samples
            or series.review_reasons
            or series.alternatives
            or any(s.status is not SegmentStatus.OBSERVED for s in series.samples)
        ):
            return False
        if any(not np.isfinite([s.u, s.v, s.half_width_px]).all() for s in series.samples):
            return False
    return bool(calibrator.predict_proba([panel])[0] >= threshold.threshold)
