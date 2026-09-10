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

from graphextract.schema import PanelOutcome, PanelResult

FEATURES = ("support_frac", "calib_resid_px", "n_review", "min_anchor_conf",
            "has_duplicates", "n_series")


def panel_features(panel: PanelResult) -> dict[str, float]:
    """Production-computable acceptance features for one panel."""
    supports = [s.observed_support() / max(1, len(s.samples)) for s in panel.series]
    support_frac = float(np.mean(supports)) if supports else 0.0
    resid = max([f.residual_px_max for f in panel.axes.values()] or [0.0])
    if not panel.axes:
        resid = 99.0  # uncalibrated: worst-case sentinel, never hidden
    confs = [t.confidence for f in panel.axes.values() for t in f.anchors_used]
    dup = any("duplicate" in r for s in panel.series for r in s.review_reasons)
    return {
        "support_frac": support_frac,
        "calib_resid_px": float(resid),
        "n_review": float(len(panel.review_reasons)
                          + sum(len(s.review_reasons) for s in panel.series)),
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
        np.savez(p, coef=self.model.coef_, intercept=self.model.intercept_,
                 classes=self.model.classes_, features=np.array(FEATURES))
        return p

    @staticmethod
    def load(path: str | Path) -> ConfidenceCalibrator:
        z = np.load(path, allow_pickle=True)
        cal = ConfidenceCalibrator()
        cal.model.coef_, cal.model.intercept_, cal.model.classes_ = (
            z["coef"], z["intercept"], z["classes"])
        cal._fit = True
        return cal


@dataclass
class AcceptancePoint:
    threshold: float
    precision: float
    coverage: float
    n_accepted: int


def select_threshold(probas: npt.NDArray, labels: list[bool],
                     target_precision: float = 0.995) -> AcceptancePoint:
    """Highest-coverage threshold whose empirical precision meets the target.

    Raises when no threshold on this calibration set substantiates the target —
    a small pilot cannot license the production claim.
    """
    y = np.array(labels, dtype=bool)
    if len(y) == 0:
        raise ValueError("empty calibration set")
    best: AcceptancePoint | None = None
    for thr in sorted(set(float(p) for p in probas)):
        accepted = probas >= thr
        n = int(accepted.sum())
        if n == 0:
            continue
        prec = float(y[accepted].mean())
        if prec >= target_precision and (best is None or n > best.n_accepted):
            best = AcceptancePoint(thr, prec, n / len(y), n)
    if best is None:
        raise ValueError(
            f"target precision {target_precision} not substantiated by "
            f"{len(y)} calibration cases (best observed "
            f"{max(float(y[probas >= t].mean()) for t in set(float(p) for p in probas) if (probas >= t).any()):.3f})")
    return best


def auto_acceptable(panel: PanelResult, calibrator: ConfidenceCalibrator,
                    threshold: float) -> bool:
    """Production gate: calibrated confidence only; review/failed never pass."""
    if panel.outcome not in (PanelOutcome.COMPLETE, PanelOutcome.PARTIAL_REVIEW):
        return False
    return bool(calibrator.predict_proba([panel])[0] >= threshold)
