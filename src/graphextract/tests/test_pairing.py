# -*- coding: utf-8 -*-
"""Tests for pairing.py: parser interop, grid audit, verdict, manifest."""

import json
import os

import numpy as np
import pytest

from graphextract.pairing import (
    audit_grids,
    load_spin_truth,
    match_curve,
    pairing_verdict,
    write_pairing_manifest,
)

MEASUREMENTS = os.environ.get(
    "SPINORAMA_MEASUREMENTS", "/Users/pierre/src/spinorama/datas/measurements")
ASCI_H = f"{MEASUREMENTS}/AsciLab C8C/asr-v2-20260323"


def _fixture_txt(path, drop_second_curve_row: bool = False):
    lines = ['"SPL Horizontal"\t\t\t',
             '"On-Axis"\t"10°"\t\t',
             '"Frequency / Hz"\t"SPL / dB"\t"Frequency / Hz"\t"SPL / dB"']
    freqs = [20.0, 25.0, 31.5, 40.0]
    for i, f in enumerate(freqs):
        if drop_second_curve_row and i == 1:
            lines.append(f"{f}\t{90.0 + i}\t\t")
        else:
            lines.append(f"{f}\t{90.0 + i}\t{f}\t{80.0 + i}")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def _needs_spinorama():
    from graphextract.pairing import require_spinorama_parser
    try:
        require_spinorama_parser()
    except ImportError:
        pytest.skip("spinorama checkout not importable")
    return True


def _stub_parse_func(path):
    import pandas as pd
    audit = audit_grids(path)
    assert audit["grids_identical"] is True
    freq = np.array([20.0, 25.0, 31.5, 40.0])
    return True, ("t", pd.DataFrame({"Freq": freq, "On Axis": [90.0, 91.0, 92.0, 93.0],
                                     "10°": [80.0, 81.0, 82.0, 83.0]}))


def test_parser_seam_accepts_injected_func(tmp_path):
    _fixture_txt(tmp_path / "SPL Horizontal.txt")
    truth = load_spin_truth(tmp_path, "horizontal", parse_func=_stub_parse_func)
    assert set(truth.curves) == {"On Axis", "10°"}
    assert truth.curves["On Axis"].tolist() == [90.0, 91.0, 92.0, 93.0]


def test_fixture_parses_with_shared_grid(tmp_path):
    _needs_spinorama()
    p = tmp_path / "SPL Horizontal.txt"
    _fixture_txt(p)
    audit = audit_grids(p)
    assert audit["n_curves"] == 2 and audit["grids_identical"] is True
    assert audit["rows_per_curve"] == [4, 4]
    truth = load_spin_truth(tmp_path, "horizontal")
    assert set(truth.curves) == {"On Axis", "10°"}
    assert truth.grids_identical is True
    assert truth.curves["On Axis"].tolist() == [90.0, 91.0, 92.0, 93.0]


def test_ragged_grid_is_flagged_not_silently_aligned(tmp_path):
    p = tmp_path / "SPL Horizontal.txt"
    _fixture_txt(p, drop_second_curve_row=True)
    audit = audit_grids(p)
    assert audit["grids_identical"] is False
    assert audit["rows_per_curve"] == [4, 3]


def test_verdict_pairs_exact_and_rejects_shift():
    freq = np.geomspace(20, 20000, 50)
    vals = 90.0 + 5 * np.sin(np.log10(freq))
    pts = list(zip(freq.tolist(), vals.tolist()))
    ok = match_curve(pts, freq, vals)
    assert ok["rms_db"] < 1e-9
    shifted = match_curve([(x, y + 5.0) for x, y in pts], freq, vals)
    assert abs(shifted["rms_db"] - 5.0) < 0.05


def test_verdict_dict_marks_unpaired_with_evidence():
    from graphextract.pairing import SourceTruth
    freq = np.geomspace(20, 20000, 50)
    truth = SourceTruth("spk", "p", "horizontal", "t", freq,
                        {"On Axis": np.full(50, 90.0)}, "sha", True)
    v = pairing_verdict({"s": [(float(f), 95.0) for f in freq]}, truth)
    assert v["series"]["s"]["paired"] is False
    assert v["series"]["s"]["best_rms_db"] == pytest.approx(5.0)
    v2 = pairing_verdict({"s": [(float(f), 90.0) for f in freq]}, truth)
    assert v2["series"]["s"]["paired"] is True


def test_manifest_round_trip(tmp_path):
    p = write_pairing_manifest(tmp_path / "m.json", "img",
                               {"horizontal": {"series": {}}})
    assert json.loads(p.read_text())["image_id"] == "img"


def test_census_without_source_records_blocker():
    import cv2

    from graphextract.ocr_adapters import StubOCR
    from graphextract.pairing import NO_SOURCE, census_image

    img = np.full((200, 300, 3), 255, np.uint8)
    cv2.rectangle(img, (30, 20), (270, 160), (0, 0, 0), 2)
    census = census_image(img, "synth", StubOCR([]))
    assert census.width == 300 and len(census.panels) >= 1
    assert census.ocr["n_words"] == 0
    assert census.source["status"] == NO_SOURCE and census.verdict is None
    d = census.to_dict()
    assert d["image_id"] == "synth" and d["sha256"] == census.sha256


def test_census_with_source_runs_verdict():
    from graphextract.ocr_adapters import OCRWord, StubOCR
    from graphextract.pairing import SourceTruth, census_image

    from tests.helpers import log_sine_panel, styles_ab

    img, panel, truth = log_sine_panel()
    x0, y0, w, h = panel.rect_xywh
    words = []
    for f in (100, 1000, 10000):
        gx = truth.x_fit.transform(f)
        words.append(OCRWord(f"{int(f)}hz", int(gx - 14), y0 + h - 16, 28, 12, 0.95))
    for v in (40, 60, 80):
        gy = truth.y_fit.transform(v)
        words.append(OCRWord(str(int(v)), x0 + 4, int(gy - 6), 20, 12, 0.95))
    # Frame-border ticks ('100' top, '20' bottom): association must not crash
    # even when the 1px-offset detected interior leaves them unsnapped.
    for v in (100, 20):
        gy = truth.y_fit.transform(v)
        words.append(OCRWord(str(int(v)), x0 + 4, int(gy - 6), 20, 12, 0.95))
    freq = np.geomspace(20, 20000, 120)
    y_a = np.array([60.0 + 8.0 * np.sin(np.log10(f) * 4.0) for f in freq])
    y_b = np.array([40.0 + 4.0 * np.sin(np.log10(f) * 4.0) for f in freq])
    src = SourceTruth("synth", "p", "horizontal", "t", freq,
                      {"a": y_a, "b": y_b}, "sha", True)
    census = census_image(img, "synth", StubOCR(words), truth=src,
                          styles=styles_ab())
    assert census.source["status"] == "candidate"
    assert census.ocr["nx_anchors"] >= 3 and census.ocr["ny_anchors"] >= 3
    assert census.ocr["x_scale"] == "log10"
    assert all(s["paired"] for s in census.verdict["series"].values())


@pytest.mark.skipif(not os.path.isdir(ASCI_H), reason="measurements checkout missing")
def test_real_asciilab_file_parses_clean():
    _needs_spinorama()
    truth = load_spin_truth(ASCI_H, "horizontal")
    assert len(truth.curves) == 36
    assert truth.grids_identical is True
    assert all(np.isfinite(v).all() for v in truth.curves.values())
    assert truth.freq_hz.min() >= 20.0 and truth.freq_hz.max() <= 20000.0
