# -*- coding: utf-8 -*-
"""Source-truth pairing (plan-20260810, section 7): match images to measurements.

Ground truth comes from the existing ``spinorama.loaders.klippel`` parser —
the same values the site itself renders — plus a per-file grid audit (the
loader assumes all curves share column 0's grid; the audit proves it per
file instead of trusting it globally). ``pairing_verdict`` decides whether an
extracted image curve matches a source curve; anything above threshold is
reported unpaired with its best RMS as evidence, never force-matched.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

PAIR_RMS_THRESHOLD_DB = 1.5  # extraction-grade agreement, not family resemblance


@dataclass
class SourceTruth:
    speaker: str
    version_path: str
    orientation: str  # horizontal | vertical
    title: str
    freq_hz: np.ndarray
    curves: dict[str, np.ndarray] = field(default_factory=dict)
    sha256: str = ""
    grids_identical: bool = False


def audit_grids(path: str | Path) -> dict:
    """Per-curve row counts + grid identity for one Klippel multi-column export."""
    raw = pd.read_csv(path, sep="\t", header=None, engine="python")
    ncols = raw.shape[1]
    grids = [np.asarray(pd.to_numeric(raw.iloc[3:, k], errors="coerce"),
                        dtype=float)
             for k in range(0, ncols, 2)]
    base = grids[0]
    return {
        "n_curves": len(grids),
        "rows_per_curve": [int(np.isfinite(g).sum()) for g in grids],
        "grids_identical": all(np.array_equal(g, base, equal_nan=True) for g in grids),
        "freq_min": float(np.nanmin(base)),
        "freq_max": float(np.nanmax(base)),
    }


def _recover_shadow() -> bool:
    """Evict a repo-root shadow package so the real spinorama can import.

    Returns True when recovery was attempted. Only a shadow is evicted: a
    module whose directory provably lacks the loaders submodule.
    """
    import os
    import sys

    if "spinorama.loaders" in sys.modules:
        return False
    candidate = Path(os.environ.get(
        "SPINORAMA_SRC", "/Users/pierre/src/spinorama/src"))
    bogus_file = getattr(sys.modules.get("spinorama"), "__file__", "") or ""
    shadow = bool(bogus_file) and not (Path(bogus_file).parent / "loaders").is_dir()
    if candidate.is_dir() and shadow:
        sys.modules.pop("spinorama", None)
        sys.path.insert(0, str(candidate))
        return True
    return False


def require_spinorama_parser():
    """Import the canonical parser, recovering from repo-root shadowing."""
    try:
        from spinorama.loaders.klippel import parse_graph_freq_klippel
        return parse_graph_freq_klippel
    except ImportError:
        pass
    if _recover_shadow():
        from spinorama.loaders.klippel import parse_graph_freq_klippel
        return parse_graph_freq_klippel
    raise ImportError(
        "spinorama.loaders.klippel is not importable; set SPINORAMA_SRC to a "
        "spinorama checkout src/ or pass parse_func= explicitly")


def _default_parser(path: str):
    return require_spinorama_parser()(path)


def load_spin_truth(speaker_dir: str | Path, orientation: str = "horizontal",
                    parse_func=None) -> SourceTruth:
    """Load SPL source truth via the canonical spinorama parser + grid audit."""
    name = "SPL Horizontal.txt" if orientation == "horizontal" else "SPL Vertical.txt"
    path = Path(speaker_dir) / name
    ok, (title, df) = (parse_func or _default_parser)(str(path))
    if not ok:
        raise ValueError(f"parser failed for {path}")
    audit = audit_grids(path)
    freq = df["Freq"].to_numpy(dtype=float)
    curves = {c: df[c].to_numpy(dtype=float) for c in df.columns if c != "Freq"}
    return SourceTruth(
        speaker=Path(speaker_dir).parent.name, version_path=str(path),
        orientation=orientation, title=title, freq_hz=freq, curves=curves,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        grids_identical=audit["grids_identical"])


def match_curve(extracted_xy: list[tuple[float, float]], truth_freq: np.ndarray,
                truth_vals: np.ndarray, n_grid: int = 200) -> dict:
    """RMS agreement of one extracted curve vs one source curve on a log grid."""
    ex = np.asarray(extracted_xy, dtype=float)
    lo = max(float(ex[:, 0].min()), float(truth_freq.min()))
    hi = min(float(ex[:, 0].max()), float(truth_freq.max()))
    if hi <= lo or len(ex) < 2:
        return {"rms_db": float("inf"), "overlap_hz": [lo, hi], "n": 0}
    g = np.geomspace(lo, hi, n_grid)
    a = np.interp(np.log10(g), np.log10(ex[:, 0]), ex[:, 1])
    b = np.interp(np.log10(g), np.log10(truth_freq), truth_vals)
    return {"rms_db": float(np.sqrt(np.mean((a - b) ** 2))),
            "overlap_hz": [lo, hi], "n": n_grid}


def pairing_verdict(extracted: dict[str, list[tuple[float, float]]],
                    truth: SourceTruth,
                    threshold_db: float = PAIR_RMS_THRESHOLD_DB) -> dict:
    """Best source candidate per extracted series + paired/unpaired verdict."""
    verdict: dict = {"truth_sha256": truth.sha256,
                     "grids_identical": truth.grids_identical, "series": {}}
    for sid, pts in extracted.items():
        scored = [(name, match_curve(pts, truth.freq_hz, vals))
                  for name, vals in truth.curves.items()]
        scored.sort(key=lambda kv: kv[1]["rms_db"])
        best_name, best = scored[0]
        verdict["series"][sid] = {
            "best_candidate": best_name, "best_rms_db": best["rms_db"],
            "overlap_hz": best["overlap_hz"],
            "paired": bool(best["rms_db"] <= threshold_db),
        }
    return verdict


NO_SOURCE = "no-source-export"


@dataclass
class ImageCensus:
    image_id: str
    width: int
    height: int
    sha256: str
    panels: list[dict] = field(default_factory=list)
    ocr: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)
    verdict: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def census_image(img, image_id: str, ocr, truth: SourceTruth | None = None,
                 styles=None, anchor_source: str = "ocr_unverified",
                 threshold_db: float = PAIR_RMS_THRESHOLD_DB,
                 jina_reader=None) -> ImageCensus:
    """One-image pairing census: detection + OCR readability + verdict if possible.

    Extraction runs only when both source truth and curve styles are supplied
    (single largest detected panel). Otherwise the census records why scoring
    is blocked instead of inventing it. When Tesseract yields no anchors and
    ``jina_reader`` (a loaded JinaOCRReader) is supplied, the Jina-OCR
    fallback is attempted; its anchors demand manual review.
    """
    from graphextract.ocr_adapters import anchors_from_ocr
    from graphextract.panels import detect_panels

    h, w = img.shape[:2]
    sha = hashlib.sha256(np.ascontiguousarray(img).tobytes()).hexdigest()
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        words = ocr.read_words(gray)
    except Exception:
        words = []
    panels = detect_panels(img, image_id, words=words or None)
    census = ImageCensus(image_id=image_id, width=w, height=h, sha256=sha)
    for pg in panels:
        census.panels.append({
            "panel_id": pg.panel_id, "envelope_xywh": list(pg.envelope_xywh),
            "interior_xywh": list(pg.interior_xywh),
            "interior_confidence": pg.interior_confidence,
            "detection_method": pg.detection_method})
    census.ocr = {"n_words": len(words), "nx_anchors": 0, "ny_anchors": 0,
                  "x_scale": None, "x_unit": "", "y_unit": "", "unmatched": 0,
                  "detection_method": panels[0].detection_method if panels else None}
    anchors = None
    if panels and words:
        pg = max(panels, key=lambda p: p.interior_xywh[2] * p.interior_xywh[3])
        x0, y0, pw, ph = pg.interior_xywh
        shifted = [replace(wd, x=wd.x - x0, y=wd.y - y0) for wd in words]
        anchors, unmatched = anchors_from_ocr(
            shifted, img[y0:y0 + ph, x0:x0 + pw], source=anchor_source)
        census.ocr.update({
            "nx_anchors": len(anchors.x), "ny_anchors": len(anchors.y_left),
            "x_scale": anchors.x_scale.value if anchors.x_scale else None,
            "x_unit": anchors.x_unit, "y_unit": anchors.y_unit,
            "unmatched": len(unmatched)})
    if (
        panels
        and jina_reader is not None
        and (anchors is None or (not anchors.x and not anchors.y_left
                                 and not anchors.y_right))
    ):
        from graphextract.jina_fallback import maybe_jina_fallback

        pg = max(panels, key=lambda p: p.interior_xywh[2] * p.interior_xywh[3])
        x0, y0, pw, ph = pg.interior_xywh
        ex0, ey0, pew, peh = pg.envelope_xywh
        anchors, jina_status = maybe_jina_fallback(
            img[ey0:ey0 + peh, ex0:ex0 + pew],
            img[y0:y0 + ph, x0:x0 + pw],
            image_id, jina_reader)
        census.ocr.update({
            "fallback": jina_status,
            "anchor_source": anchors.source if anchors is not None else anchor_source,
            "needs_review": jina_status.get("needs_review", False),
        })
        if anchors is not None:
            census.ocr.update({
                "nx_anchors": len(anchors.x), "ny_anchors": len(anchors.y_left),
                "x_scale": anchors.x_scale.value if anchors.x_scale else None,
                "x_unit": anchors.x_unit, "y_unit": anchors.y_unit})
    if truth is None or styles is None or anchors is None:
        census.source = {"status": NO_SOURCE,
                         "reason": "no SPL export covers these curves" if truth is None
                         else "no curve styles supplied for extraction"}
        return census
    from graphextract.pipeline import run_panel

    x0, y0, pw, ph = max(panels, key=lambda p: p.interior_xywh[2] * p.interior_xywh[3]).interior_xywh
    res = run_panel(img, f"{image_id}#pX", img[y0:y0 + ph, x0:x0 + pw],
                    (x0, y0), anchors, styles)
    extracted = {s.series_id: [(q.value_x, q.value_y) for q in s.samples
                               if q.status.value == "observed"
                               and q.value_x is not None and q.value_y is not None]
                 for s in res.series}
    census.source = {"status": "candidate", "truth_sha256": truth.sha256,
                     "outcome": res.outcome.value}
    census.verdict = pairing_verdict(extracted, truth, threshold_db)
    return census


def write_pairing_manifest(out_path: str | Path, image_id: str,
                           verdicts: dict) -> Path:
    """Machine-readable record of what paired and what did not, with evidence."""
    p = Path(out_path)
    p.write_text(json.dumps({"image_id": image_id, "verdicts": verdicts,
                             "threshold_db": PAIR_RMS_THRESHOLD_DB},
                            indent=2) + "\n", encoding="utf-8")
    return p
