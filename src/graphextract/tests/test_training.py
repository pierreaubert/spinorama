# -*- coding: utf-8 -*-
"""Tests for training.py: registry, E0/E2-lite/E3/E4 runners, segmentor IO."""

import numpy as np
import pytest

from graphextract.training import (
    REGISTRY,
    PixelSegmentor,
    RunManifest,
    record_external_result,
    render_truth,
    run_e0,
    run_e1,
    run_e2lite,
    run_e2torch,
    run_e3,
    run_e4,
    synth_panel,
)


def test_registry_covers_e0_to_e5_with_honest_status():
    ids = [s.id for s in REGISTRY]
    assert ids == ["E0", "E1", "E2", "E3", "E4", "E5"]
    runnable = {s.id for s in REGISTRY if s.status == "implemented"
                or s.status.startswith("implemented ")}
    assert {"E0", "E1", "E3"}.issubset(runnable)
    for s in REGISTRY:
        if s.id == "E5":
            assert s.status.startswith("requires:")


def test_run_manifest_and_external_log(tmp_path):
    m = RunManifest(exp_id="E0", seed=0, data_manifest={"n": 2},
                    config={}, metrics={"strict_rate": 1.0}, pipeline_version="")
    p = m.save(tmp_path)
    assert p.exists() and m.timestamp > 0 and m.pipeline_version
    q = record_external_result("E5", "some-paper", {"acc": 0.9}, tmp_path)
    assert q.exists()


def test_e0_canonical_beats_destructive():
    out = run_e0(n_panels=2, seed=0)
    assert len(out["rows"]) == 2 * 2 * 2  # panels x variants x series
    can, des = out["canonical"], out["destructive"]
    assert 0.0 <= can["strict_rate"] <= 1.0
    assert can["mean_coverage"] >= 0.99
    assert can["mean_max_px"] <= des["mean_max_px"] + 0.5
    maxes = {(r["panel"], r["series"]): r["max_px"] for r in out["rows"]
             if r["variant"] == "canonical"}
    dmaxes = {(r["panel"], r["series"]): r["max_px"] for r in out["rows"]
              if r["variant"] == "destructive"}
    assert any(abs(maxes[k] - dmaxes[k]) > 1e-9 for k in maxes)  # variants truly differ
    assert all(r["strict"] for r in out["rows"]
               if r["variant"] == "canonical" and r["panel"] == 0)


def test_segmentor_learns_and_round_trips(tmp_path):
    rnd = np.random.default_rng(0)
    samples = []
    for _ in range(3):
        panel, _ = synth_panel(rnd)
        truth = render_truth(panel)
        samples.append((truth.image, truth.geometric_masks))
    seg = PixelSegmentor(["s0", "s1"])
    hist = seg.fit(samples, epochs=30, seed=0)
    assert hist["loss_end"] < hist["loss_start"]
    assert hist["epochs"] <= 30
    p = seg.save(tmp_path / "seg.npz")
    seg2 = PixelSegmentor.load(p)
    pred = seg2.predict_masks(samples[0][0])
    union = np.zeros(samples[0][0].shape[:2], bool)
    for m in pred.values():
        union |= (m > 0)
    assert union.mean() > 0.001  # finds curve pixels, not just background


def test_e2lite_reports_pixel_agreement():
    out = run_e2lite(n_train=4, n_dev=2, seed=0, epochs=20)
    assert out["fit"]["loss_end"] < out["fit"]["loss_start"]
    assert out["dev_pixel_agreement"] > 0.85


def test_e1_learned_ties_classical_on_clean_synthetic():
    out = run_e1(n_train=4, n_dev=2, seed=0, epochs=30)
    assert out["fit"]["loss_end"] < out["fit"]["loss_start"]
    assert out["classical"]["count_accuracy"] == 1.0
    assert out["classical"]["mean_iou"] > 0.9
    assert out["learned"]["count_accuracy"] >= 0.5
    assert out["learned"]["mean_iou"] > 0.5
    assert out["dev_mask_agreement"] > 0.9


def test_e2torch_reports_dev_agreement():
    torch = pytest.importorskip("torch")
    del torch
    out = run_e2torch(n_train=4, n_dev=2, seed=0, epochs=8)
    assert out["fit"]["loss_end"] < out["fit"]["loss_start"]
    assert out["dev_pixel_agreement"] > 0.85


def test_e3_ablation_runs_without_identity_regression():
    out = run_e3(n_panels=2, seed=0)
    assert out["joint"]["mean_switch_rate"] <= 0.05
    assert out["joint"]["mean_switch_rate"] <= out["independent"]["mean_switch_rate"] + 1e-9


def test_e4_reports_transfer_gap():
    out = run_e4(n_train=4, n_dev=2, seed=0)
    assert 0.0 <= out["family_B_agreement"] <= out["family_A_agreement"] <= 1.0
    assert out["transfer_gap"] >= 0.0
