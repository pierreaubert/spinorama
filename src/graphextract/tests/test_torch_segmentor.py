# -*- coding: utf-8 -*-
"""Tests for torch_segmentor.py: loss decreases, masks sane, IO round-trips."""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from graphextract.torch_segmentor import (
    TinyConvSeg,
    conv_agreement,
    predict_conv_masks,
    train_conv_segmentor,
)
from graphextract.training import render_truth, synth_panel


def _panels(n: int = 3, seed: int = 0):
    rnd = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        panel, _ = synth_panel(rnd, crossing=True)
        truth = render_truth(panel)
        out.append((truth.image, truth.geometric_masks))
    return out


def test_conv_pilot_learns_and_saves(tmp_path):
    panels = _panels()
    seg, hist = train_conv_segmentor(panels, ["s0", "s1"], epochs=8, seed=0)
    assert hist["loss_end"] < hist["loss_start"]
    assert isinstance(seg, TinyConvSeg) and seg.n_classes == 3
    assert conv_agreement(seg, panels) > 0.85
    p = seg.save(tmp_path / "conv.pt")
    seg2 = TinyConvSeg.load(p)
    a = predict_conv_masks(seg, panels[0][0])["s0"]
    b = predict_conv_masks(seg2, panels[0][0])["s0"]
    assert (a == b).all() and a.mean() > 0  # finds curve pixels


def test_conv_masks_feed_tracker_without_crash():
    import cv2
    from graphextract.evidence import EvidenceLayers, estimate_background
    from graphextract.tracking import track_panel

    panels = _panels(n=1)
    seg, _ = train_conv_segmentor(panels, ["s0", "s1"], epochs=2, seed=0)
    img = panels[0][0]
    layers = EvidenceLayers(curve_masks=predict_conv_masks(seg, img),
                            grid_mask=np.zeros(img.shape[:2], np.uint8),
                            background_bgr=estimate_background(img))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tracks = track_panel(gray, layers, ["s0", "s1"], float(np.median(gray)))
    assert set(tracks) == {"s0", "s1"}
    assert all(len(t.samples) == img.shape[1] for t in tracks.values())
