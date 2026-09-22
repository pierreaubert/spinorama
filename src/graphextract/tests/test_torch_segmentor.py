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


def test_multilabel_overlap_supervision_and_checkpoint(tmp_path):
    from graphextract.torch_segmentor import (
        MultiLabelConvSeg, multilabel_targets, predict_multilabel_probabilities,
        segmentation_metrics, train_multilabel_segmentor,
    )
    masks = {"a":np.zeros((32,32),np.uint8), "b":np.zeros((32,32),np.uint8)}
    masks["a"][14:17] = 255
    masks["b"][:,14:17] = 255
    target = multilabel_targets(masks,["a","b"])
    assert (target[:,15,15] == 1).all()
    image = np.full((32,32,3),255,np.uint8)
    image[masks["a"]>0] = (0,0,220)
    image[masks["b"]>0] = (220,0,0)
    model,history = train_multilabel_segmentor([(image,masks)],["a","b"],epochs=8)
    assert history["loss_end"] < history["loss_start"]
    probabilities = predict_multilabel_probabilities(model,image)
    assert all(p.shape==(32,32) and np.isfinite(p).all() for p in probabilities.values())
    loaded = MultiLabelConvSeg.load(model.save(tmp_path/"multi.pt"))
    assert np.array_equal(predict_multilabel_probabilities(loaded,image)["a"], probabilities["a"])
    empty = {sid:np.zeros((32,32)) for sid in masks}
    assert all(m["f1"]==0 for m in segmentation_metrics(empty,masks).values())


def test_multilabel_heads_can_predict_shared_pixels():
    from graphextract.torch_segmentor import MultiLabelConvSeg, predict_multilabel_probabilities
    model = MultiLabelConvSeg(["a","b"])
    with torch.no_grad():
        for parameter in model.net.parameters():
            parameter.zero_()
        model.net[-1].bias.fill_(3.0)
    probabilities = predict_multilabel_probabilities(model,np.zeros((8,8,3),np.uint8))
    assert ((probabilities["a"]>0.9) & (probabilities["b"]>0.9)).all()
