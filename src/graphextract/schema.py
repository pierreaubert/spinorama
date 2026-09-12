# -*- coding: utf-8 -*-
"""Canonical result schema for graph extraction (plan-20260810, section 6F).

Native coordinate convention: original image pixels, top-left pixel center at
``(0, 0)``, x right, y down. All tolerances are expressed in native pixels.
Internal positions are continuous floats; every stored transform records the
image dimensions, content hash, and crop offsets it applies to.

Legacy modules (``eval_extraction.py``, ``spinorama.extract``) are kept
unchanged as the comparison baseline; new code builds on these types.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class SegmentStatus(str, Enum):
    """Observation status of one extracted sample."""

    OBSERVED = "observed"
    INFERRED_OCCLUSION = "inferred_occlusion"
    INTERPOLATED = "interpolated"
    INFERRED_DASH_GAP = "inferred_dash_gap"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


class PanelOutcome(str, Enum):
    """Structured per-panel result (replaces a single success flag)."""

    COMPLETE = "complete"
    PARTIAL_REVIEW = "partial_review"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class ScaleType(str, Enum):
    LINEAR = "linear"
    LOG10 = "log10"


class AxisRole(str, Enum):
    X = "x"
    Y_LEFT = "y_left"
    Y_RIGHT = "y_right"


@dataclass
class TickAnchor:
    """One pixel <-> value correspondence from OCR, grid, or annotation."""

    pixel: float
    value: float
    confidence: float = 1.0
    source: str = "ocr"  # ocr | grid | annotation | renderer | manual


@dataclass
class AxisFit:
    """Explicit coordinate transform: pixel = a * t + b.

    t is the raw value for linear axes and log10(value) for log10 axes.
    """

    role: AxisRole
    scale: ScaleType
    unit: str
    a: float
    b: float
    anchors_used: list[TickAnchor] = field(default_factory=list)
    residual_px_rms: float = 0.0
    residual_px_max: float = 0.0
    method: str = "unknown"
    reversed: bool = False

    def transform(self, value: float) -> float:
        """Map a data value to a native pixel coordinate."""
        import math

        t = math.log10(value) if self.scale is ScaleType.LOG10 else value
        return self.a * t + self.b

    def invert(self, pixel: float) -> float:
        """Map a native pixel coordinate back to a data value."""
        t = (pixel - self.b) / self.a
        return 10.0**t if self.scale is ScaleType.LOG10 else t

    def to_dict(self) -> dict:
        d = asdict(self)
        d["role"] = self.role.value
        d["scale"] = self.scale.value
        return d


@dataclass
class PanelGeometry:
    """Panel envelope (with labels/legend context) and plot interior."""

    panel_id: str
    envelope_xywh: tuple[int, int, int, int]
    interior_xywh: tuple[int, int, int, int]
    image_width: int
    image_height: int
    title: str = ""
    parent_id: str | None = None
    shared_x_with: str | None = None
    interior_confidence: str = "low"  # low | refined | verified
    detection_method: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SeriesSample:
    """One extracted sample in native pixel coordinates."""

    u: float  # continuous native x pixel
    v: float  # continuous native y pixel
    status: SegmentStatus = SegmentStatus.OBSERVED
    half_width_px: float = 0.5  # positional uncertainty interval half-width
    value_x: float | None = None  # mapped data values (None when uncalibrated)
    value_y: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class SeriesResult:
    series_id: str
    panel_id: str
    label: str
    axis_id: str
    samples: list[SeriesSample] = field(default_factory=list)
    alternatives: list[list[SeriesSample]] = field(default_factory=list)
    review_reasons: list[str] = field(default_factory=list)

    def observed_support(self) -> int:
        return sum(1 for s in self.samples if s.status is SegmentStatus.OBSERVED)

    def to_dict(self) -> dict:
        return {
            "series_id": self.series_id,
            "panel_id": self.panel_id,
            "label": self.label,
            "axis_id": self.axis_id,
            "samples": [s.to_dict() for s in self.samples],
            "alternatives": [[s.to_dict() for s in alt] for alt in self.alternatives],
            "review_reasons": list(self.review_reasons),
        }


@dataclass
class PanelResult:
    panel: PanelGeometry
    axes: dict[str, AxisFit] = field(default_factory=dict)
    series: list[SeriesResult] = field(default_factory=list)
    outcome: PanelOutcome = PanelOutcome.FAILED
    review_reasons: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "panel": self.panel.to_dict(),
            "axes": {k: v.to_dict() for k, v in self.axes.items()},
            "series": [s.to_dict() for s in self.series],
            "outcome": self.outcome.value,
            "review_reasons": list(self.review_reasons),
            "provenance": dict(self.provenance),
        }


@dataclass
class DocumentResult:
    document_id: str
    image_id: str
    image_width: int
    image_height: int
    image_sha256: str
    panels: list[PanelResult] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "document_id": self.document_id,
            "image_id": self.image_id,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "image_sha256": self.image_sha256,
            "panels": [p.to_dict() for p in self.panels],
            "provenance": dict(self.provenance),
        }
