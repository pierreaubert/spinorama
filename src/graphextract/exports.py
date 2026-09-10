# -*- coding: utf-8 -*-
"""Exports: canonical JSON (with uncertainty sidecars) and WPD compatibility.

WPD ``datasetColl`` cannot express gaps, identities, or uncertainty, so the
adapter emits one dataset per contiguous OBSERVED run, named with stable
``image/panel/series`` IDs that survive empty or repeated titles. The full
canonical document (statuses, alternatives, calibration anchors) is the primary
artifact; WPD is a derived, lossy view.
"""

from __future__ import annotations

import json
from pathlib import Path

from graphextract.schema import DocumentResult, SegmentStatus, SeriesResult


def document_to_json(doc: DocumentResult) -> dict:
    return doc.to_dict()


def write_canonical(doc: DocumentResult, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(document_to_json(doc), indent=2) + "\n", encoding="utf-8")
    return path


def _observed_runs(series: SeriesResult) -> list[list[tuple[float, float]]]:
    """Split OBSERVED samples into contiguous runs; gaps stay gaps."""
    runs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for s in series.samples:
        if s.status is SegmentStatus.OBSERVED and s.value_x is not None and s.value_y is not None:
            cur.append((s.value_x, s.value_y))
        else:
            if cur:
                runs.append(cur)
                cur = []
    if cur:
        runs.append(cur)
    return runs


def to_wpd_json(doc: DocumentResult) -> dict:
    """WPD datasetColl keyed by stable IDs; one dataset per observed run."""
    coll: list[dict] = []
    for panel in doc.panels:
        for series in panel.series:
            for i, run in enumerate(_observed_runs(series)):
                name = f"{doc.image_id}/{panel.panel.panel_id.split('#')[-1]}/{series.series_id}"
                if len(_observed_runs(series)) > 1:
                    name += f"#seg{i}"
                if series.label and series.label != series.series_id:
                    name += f" {series.label}"
                coll.append({"name": name,
                             "data": [{"value": [x, y]} for x, y in run]})
    return {"datasetColl": coll}
