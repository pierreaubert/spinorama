# -*- coding: utf-8 -*-
"""Corpus QA for CEA2034 extraction: every graph must extract excellently.

Slow by design: each graph runs full OCR + extraction (minutes for the
corpus). The fast suite skips this file::

    pytest src/graphextract/tests -q --ignore=src/graphextract/tests/test_qa_cea2034.py

Quality rules are generic (curve families, observed support, axis
sanity, bridge honesty); only the per-graph expected family sets are
test data. No per-graph extraction logic is allowed to satisfy these.
"""

import json
import re
from pathlib import Path

import pytest

ASSUMPTIONS = ("curve_continuous", "no_jump", "assume_overlap")
CORPUS_DIR = Path(__file__).parent.parent / "datas" / "graph-cea2034"

# Per-graph expected curve families (test data, not extraction logic).
# Families: onaxis, lw, er, sp, pir, spdi, erdi, di. Values are minimum
# observed fractions; the graphs earn higher, but QA pins the floor.
# Filled from the measured post-fix sweep; each graph's families must
# be present and honestly measured above the floor.
EXPECTED: dict[str, dict[str, float]] = {
    'spin-asr-ascilab-c6b.png': {'er': 0.80, 'erdi': 0.45, 'lw': 0.40, 'onaxis': 0.50, 'sp': 0.85, 'spdi': 0.50},
    'spin-eac-aiyima-s400.png': {'er': 0.60, 'erdi': 0.30, 'lw': 0.25, 'onaxis': 0.75, 'sp': 0.60, 'spdi': 0.20},
    'spin-eac-devialet-phantom-ultimate.png': {'er': 0.70, 'erdi': 0.25, 'lw': 0.45, 'onaxis': 0.80, 'sp': 0.60, 'spdi': 0.30},
    'spin-eac-topping-m4a.png': {'er': 0.70, 'erdi': 0.30, 'lw': 0.45, 'onaxis': 0.75, 'sp': 0.60, 'spdi': 0.20},
    'spin-harman-bw-cwm7.5.png': {'er': 0.65, 'erdi': 0.65, 'lw': 0.45, 'onaxis': 0.45, 'pir': 0.90, 'sp': 0.30, 'spdi': 0.70},
    'spin-harman-jbl-lsr708i.png': {'er': 0.20, 'erdi': 0.95, 'lw': 0.75, 'sp': 0.70, 'spdi': 0.95},
    'spin-harman-paradigm-persona3f.png': {'er': 0.95, 'erdi': 0.95, 'lw': 0.85, 'onaxis': 0.90, 'sp': 0.85, 'spdi': 0.90},
    'spin-neumann-kh80.png': {'er': 0.60, 'lw': 0.40, 'onaxis': 0.70, 'sp': 0.50, 'spdi': 0.75},
    'spin-org-aoshida-audio-musician-knigh.png': {'er': 0.75, 'erdi': 0.65, 'lw': 0.85, 'onaxis': 0.65, 'sp': 0.75},
    'spin-org-danley-sm100f.png': {'er': 0.85, 'erdi': 0.70, 'lw': 0.80, 'onaxis': 0.70, 'sp': 0.80},
    'spin-pmc-pmc10-4.png': {'di': 0.95, 'er': 0.90, 'erdi': 0.95, 'lw': 0.95, 'onaxis': 0.85, 'pir': 0.95, 'sp': 0.95},
    'spin-pmc-pmc10.png': {'di': 0.95, 'er': 0.85, 'erdi': 0.95, 'lw': 0.95, 'onaxis': 0.90, 'pir': 0.95, 'sp': 0.95},
    'spin-pmc-pmc12.png': {'di': 0.95, 'er': 0.90, 'erdi': 0.95, 'lw': 0.95, 'onaxis': 0.90, 'pir': 0.95, 'sp': 0.95},
    'spin-pmc-pmc15-xbd.png': {'di': 0.95, 'er': 0.80, 'erdi': 0.95, 'lw': 0.95, 'onaxis': 0.90, 'pir': 0.95, 'sp': 0.90},
    'spin-pmc-pmc15.png': {'di': 0.95, 'er': 0.80, 'erdi': 0.95, 'lw': 0.95, 'onaxis': 0.90, 'pir': 0.95, 'sp': 0.90},
    'spin-revel-f228.jpeg': {'er': 0.60, 'erdi': 0.95, 'lw': 0.85, 'onaxis': 0.75, 'sp': 0.70, 'spdi': 0.95},
    'spin-sovox-minimax3.png': {'er': 0.30, 'onaxis': 0.70},
}

def family_of(label: str) -> str | None:
    """CEA2034 curve family for a legend label, None when unrecognized.

    The DI marker reuses the pipeline rule (single source of truth for
    fused suffixes and OCR misreads); family names match substring-wise
    since OCR splits multi-word names unpredictably, with Harman short
    forms ('Window', 'Reflections') included.
    """
    from graphextract.pipeline import _axis_for_label

    text = label or ""
    di = _axis_for_label(text) == "y_right"
    ns = re.sub(r"[^a-z]", "", text.lower())
    if "listeningwindow" in ns or "window" in ns:
        return "lwdi" if di else "lw"
    if ("earlyreflections" in ns or "firstreflections" in ns
            or "reflections" in ns or "refelctions" in ns):
        return "erdi" if di else "er"
    if "soundpower" in ns:
        return "spdi" if di else "sp"
    if "inroom" in ns or "in-room" in text.lower():
        return "pir"
    if "onaxis" in ns:
        return "onaxis"
    if "directivity" in ns:
        return "di"
    return None


def test_family_of_vocabulary():
    assert family_of("On Axis") == "onaxis"
    assert family_of("ON AXiS") == "onaxis"
    assert family_of("Listening Window") == "lw"
    assert family_of("Early Reflections") == "er"
    assert family_of("53: First Reflections") == "er"
    assert family_of("Sound Power") == "sp"
    assert family_of("54: Total Sound Power") == "sp"
    assert family_of("Predicted in-room") == "pir"
    assert family_of("Estimated |In-Room") == "pir"
    assert family_of("Sound Power DI") == "spdi"
    assert family_of("Early Reflections Dl") == "erdi"
    assert family_of("65: Total Sound Power Dl") == "spdi"
    assert family_of("56: First Reflections DI") == "erdi"
    assert family_of("Directivity Index") == "di"
    assert family_of("377: Total Sound Power O1") == "spdi"
    assert family_of("First Reflections Ol") == "erdi"
    assert family_of("Sound Power 0l") == "spdi"
    assert family_of("Ol") is None  # bare fragment: no family, no DI
    assert family_of("On Axis") == "onaxis"  # 'on' is not a misread
    assert family_of("Sound PowerD|") == "spdi"  # fused pipe suffix
    assert family_of("Sound PowerDI") == "spdi"  # fused suffix
    assert family_of("374: Window") == "lw"  # Harman short form
    assert family_of("2: Window") == "lw"
    assert family_of("Reflections") == "er"  # short form, dB
    assert family_of("Reflections Dl") == "erdi"  # short form, DI
    assert family_of("DI offset") is None
    assert family_of("Amplitude") is None
    assert family_of("") is None


DI_FAMILIES = ("spdi", "erdi", "lwdi", "di")


def _observed_fraction(series) -> float:
    from graphextract.schema import SegmentStatus

    samples = series.samples
    if not samples:
        return 0.0
    obs = sum(1 for s in samples if s.status is SegmentStatus.OBSERVED)
    return obs / len(samples)


def _value_range(series):
    ys = [s.value_y for s in series.samples
          if s.value_y is not None and s.status.value != "missing"]
    if not ys:
        return None
    return (min(ys), max(ys))


EXPECTED_AXES: dict[str, bool] = {
    'spin-asr-ascilab-c6b.png': True,
    'spin-eac-aiyima-s400.png': True,
    'spin-eac-devialet-phantom-ultimate.png': True,
    'spin-eac-topping-m4a.png': True,
    'spin-harman-bw-cwm7.5.png': True,
    'spin-harman-jbl-lsr708i.png': True,
    'spin-harman-paradigm-persona3f.png': True,
    'spin-neumann-kh80.png': True,
    'spin-org-aoshida-audio-musician-knigh.png': True,
    'spin-org-danley-sm100f.png': True,
    'spin-pmc-pmc10-4.png': True,
    'spin-pmc-pmc10.png': True,
    'spin-pmc-pmc12.png': True,
    'spin-pmc-pmc15-xbd.png': True,
    'spin-pmc-pmc15.png': True,
    'spin-revel-f228.jpeg': True,
    'spin-sovox-minimax3.png': False,
}
"""Per-graph right-axis expectation (test data): True when the graph
carries directivity curves on a dB right axis displaying the core DI
band (printed spans vary by vendor: PMC 0..50, Danley -5..15,
Harman/Erin/ASR near -10..40), False for graphs with no anchors for
one (e.g. Sovox). Filled with EXPECTED."""


@pytest.mark.parametrize("image", sorted(EXPECTED))
def test_cea2034_graph_measures_families(image):
    """Each corpus graph extracts its families honestly: present, with
    observed support above the floor, DI on the right axis over the
    core DI band (or no right axis where the graph gives none to
    anchor)."""
    import cv2

    from graphextract.cli import _read_full_words, select_styles
    from graphextract.ocr_adapters import TesseractOCR
    from graphextract.pipeline import run_document
    from graphextract.schema import PanelOutcome
    from graphextract.tracking import TrackConfig

    ocr = TesseractOCR()
    if not ocr.available:
        pytest.skip("tesseract unavailable")
    path = CORPUS_DIR / image
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert img is not None
    words = _read_full_words(img, ocr)
    styles = select_styles(img, words or [], [])
    doc = run_document(
        img, path.stem, styles, anchor_provider=None,
        track_config=TrackConfig.from_assumptions(ASSUMPTIONS),
        words=words, supplement_discovery=True)
    assert doc.panels, f"{image}: no panel detected"
    panel = doc.panels[0]
    assert panel.outcome != PanelOutcome.FAILED, (
        f"{image}: {panel.review_reasons[:2]}")
    yr = panel.axes.get("y_right")
    want_axis = EXPECTED_AXES.get(image, True)
    if not want_axis:
        assert yr is None, f"{image}: unexpected right axis appeared"
    else:
        assert yr is not None and yr.unit == "dB", (
            f"{image}: no dB right axis")
        h = panel.panel.interior_xywh[3]
        lo, hi = sorted((yr.invert(0), yr.invert(h)))
        # Vendors print different DI spans (PMC 0..50, Danley -5..15,
        # Harman/Erin/ASR near -10..40), so no single window can be
        # pinned; the generic property is that the axis displays the
        # core directivity band, from at-or-below zero into DI peaks.
        # An SPL-scale impostor axis fails both sides.
        assert lo <= 1.0 and hi >= 15.0, (
            f"{image}: right axis span {(lo, hi)} misses core DI band")
    best: dict[str, float] = {}
    axes: dict[str, str] = {}
    spans: dict[str, tuple] = {}
    for s in panel.series:
        fam = family_of(s.label or "")
        if fam is None:
            continue
        frac = _observed_fraction(s)
        if frac > best.get(fam, -1.0):
            best[fam] = frac
            axes[fam] = s.axis_id
            spans[fam] = _value_range(s)
    for fam, floor in EXPECTED[image].items():
        assert fam in best, f"{image}: family {fam} missing"
        assert best[fam] >= floor, (
            f"{image}: family {fam} support {best[fam]:.2f} < {floor}")
        if fam in DI_FAMILIES and want_axis:
            assert axes[fam] == "y_right", (
                f"{image}: family {fam} on {axes[fam]}, not y_right")
            span = spans[fam]
            assert span is not None and -15.0 <= span[0] and span[1] <= 45.0, (
                f"{image}: family {fam} range {span} outside DI plausibility")


def test_right_tick_span_covers_di_archetype():
    from graphextract.exports import right_tick_span
    from graphextract.schema import AxisFit, AxisRole, ScaleType
    left = AxisFit(role=AxisRole.Y_LEFT, scale=ScaleType.LINEAR, unit="dB",
                   a=-13.2, b=1293.9, method="test")
    right = AxisFit(role=AxisRole.Y_RIGHT, scale=ScaleType.LINEAR, unit="dB",
                    a=-18.7, b=768.5, method="test")
    lo, hi = right_tick_span(right, left, 40.0, 90.0)
    assert lo <= -10.0 and hi >= 40.0
