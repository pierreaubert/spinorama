# -*- coding: utf-8 -*-
"""Torch conv segmentor pilot (E2, plan-20260810 section 7).

A minimal fully-convolutional network (two 3x3 layers + 1x1 head, ~3k
params) trained on synthetic gold with exact masks. CPU-sized by design:
320x240 panels, a handful of epochs. Overlapping pixels (claimed by two
series) are excluded from the loss — a single integer label cannot encode
coincident curves, so the pilot refuses to supervise them rather than
teaching a wrong answer. Requires torch; import it lazily so the rest of
the package works without it.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise ImportError("torch is required for the conv segmentor pilot") from exc
    return torch


class TinyConvSeg:
    """Two-layer conv segmentor; classes = [background, *series_ids]."""

    def __init__(self, series_ids: list[str], width: int = 16) -> None:
        torch = _torch()
        self.series_ids = list(series_ids)
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(3, width, 3, padding=1), torch.nn.ReLU(),
            torch.nn.Conv2d(width, width, 3, padding=1), torch.nn.ReLU(),
            torch.nn.Conv2d(width, 1 + len(series_ids), 1),
        )

    @property
    def n_classes(self) -> int:
        return 1 + len(self.series_ids)

    def save(self, path: str | Path) -> Path:
        torch = _torch()
        p = Path(path)
        torch.save({"state": self.net.state_dict(), "series": self.series_ids}, p)
        return p

    @staticmethod
    def load(path: str | Path) -> TinyConvSeg:
        torch = _torch()
        blob = torch.load(path, map_location="cpu", weights_only=True)
        seg = TinyConvSeg([str(s) for s in blob["series"]])
        seg.net.load_state_dict(blob["state"])
        return seg


def _norm(t):
    """Fixed input standardization; must match between train and predict."""
    return (t - 0.5) / 0.5


def _batch(panels: list[tuple[npt.NDArray, dict[str, npt.NDArray]]],
           series_ids: list[str]):
    """Stack panels into (image tensor, label tensor, loss-weight tensor)."""
    torch = _torch()
    imgs, labels, weights = [], [], []
    for img, masks in panels:
        t = _norm(torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1))
        lab = torch.zeros(img.shape[:2], dtype=torch.long)
        claims = torch.zeros(img.shape[:2], dtype=torch.long)
        for k, sid in enumerate(series_ids):
            m = torch.from_numpy((masks[sid] > 0).astype(np.int64))
            lab = torch.where(m > 0, torch.tensor(k + 1), lab)  # later series on top
            claims += m
        w = torch.where(claims > 1, torch.tensor(0.0), torch.tensor(1.0))
        imgs.append(t)
        labels.append(lab)
        weights.append(w)
    return torch.stack(imgs), torch.stack(labels), torch.stack(weights)


def train_conv_segmentor(panels: list[tuple[npt.NDArray, dict[str, npt.NDArray]]],
                         series_ids: list[str], epochs: int = 8, lr: float = 0.05,
                         seed: int = 0) -> tuple[TinyConvSeg, dict]:
    """Full-image supervised training on CPU; returns (model, history)."""
    torch = _torch()
    torch.manual_seed(seed)
    seg = TinyConvSeg(series_ids)
    X, Y, W = _batch(panels, series_ids)
    counts = [(Y == c).sum().item() for c in range(seg.n_classes)]
    total = sum(counts)
    class_w = torch.tensor([total / max(1, c) for c in counts])
    opt = torch.optim.Adam(seg.net.parameters(), lr=min(lr, 0.01))
    hist = []
    for _ in range(epochs):
        opt.zero_grad()
        logits = seg.net(X)
        loss = torch.nn.functional.cross_entropy(
            logits, Y, weight=class_w, reduction="none")
        (loss * W).mean().backward()
        opt.step()
        with torch.no_grad():
            l2 = torch.nn.functional.cross_entropy(
                seg.net(X), Y, weight=class_w, reduction="none")
            hist.append(float((l2 * W).mean()))
    return seg, {"epochs": len(hist), "loss_start": hist[0], "loss_end": hist[-1]}


def predict_conv_masks(seg: TinyConvSeg, img: npt.NDArray) -> dict[str, npt.NDArray]:
    """Argmax masks per series id."""
    torch = _torch()
    seg.net.eval()
    with torch.no_grad():
        t = _norm(torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1)).unsqueeze(0)
        lab = seg.net(t).argmax(dim=1).squeeze(0).numpy()
    return {sid: ((lab == k + 1).astype(np.uint8)) * 255
            for k, sid in enumerate(seg.series_ids)}


def conv_agreement(seg: TinyConvSeg,
                   panels: list[tuple[npt.NDArray, dict[str, npt.NDArray]]]) -> float:
    """Pixel agreement of argmax masks vs union of exact masks."""
    correct = total = 0
    for img, masks in panels:
        union_pred = np.zeros(img.shape[:2], bool)
        for m in predict_conv_masks(seg, img).values():
            union_pred |= (m > 0)
        union_true = np.zeros(img.shape[:2], bool)
        for m in masks.values():
            union_true |= (m > 0)
        correct += int((union_pred == union_true).sum())
        total += union_true.size
    return correct / total


class MultiLabelConvSeg:
    """Multiscale independent series logits; overlapping memberships are allowed.

    This is an experimental fixed-series model. Scores indicate geometric
    hypotheses, not proof of visible ink. Use independent real-data validation
    before deploying a checkpoint outside its training palette/style family.
    """

    def __init__(self, series_ids: list[str], width: int = 16):
        torch = _torch()
        if not series_ids or len(set(series_ids)) != len(series_ids):
            raise ValueError("nonempty unique series IDs required")
        self.series_ids, self.width = list(series_ids), width
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(3, width, 3, padding=1), torch.nn.ReLU(),
            torch.nn.Conv2d(width, width, 3, dilation=2, padding=2), torch.nn.ReLU(),
            torch.nn.Conv2d(width, width, 3, dilation=4, padding=4), torch.nn.ReLU(),
            torch.nn.Conv2d(width, len(series_ids), 1))

    def save(self, path):
        path = Path(path)
        _torch().save({"version": 1, "kind": "multilabel", "series": self.series_ids,
                       "width": self.width, "state": self.net.state_dict()}, path)
        return path

    @staticmethod
    def load(path):
        blob = _torch().load(path, map_location="cpu", weights_only=True)
        if blob.get("kind") != "multilabel" or blob.get("version") != 1:
            raise ValueError("not a supported multilabel checkpoint")
        model = MultiLabelConvSeg(blob["series"], blob["width"])
        model.net.load_state_dict(blob["state"])
        return model


def multilabel_targets(masks, series_ids):
    """Retain all labels at crossings instead of masking the hard examples."""
    return np.stack([(np.asarray(masks[sid]) > 0).astype(np.float32) for sid in series_ids])


def train_multilabel_segmentor(panels, series_ids, epochs=20, lr=0.003, seed=0):
    torch = _torch()
    if not panels or epochs < 1 or lr <= 0:
        raise ValueError("positive training settings and nonempty panels required")
    torch.manual_seed(seed)
    model = MultiLabelConvSeg(series_ids)
    images = torch.stack([_norm(torch.from_numpy(img.astype(np.float32)/255).permute(2,0,1))
                          for img, _ in panels])
    targets = torch.from_numpy(np.stack([multilabel_targets(masks, series_ids)
                                        for _, masks in panels]))
    positives = targets.sum(dim=(0,2,3))
    if bool((positives == 0).any()):
        raise ValueError("every requested series needs positive training evidence")
    total = targets.shape[0]*targets.shape[2]*targets.shape[3]
    weights = ((total-positives)/positives).clamp(1,100)[None,:,None,None]
    optimizer = torch.optim.Adam(model.net.parameters(), lr=lr)

    def loss():
        return torch.nn.functional.binary_cross_entropy_with_logits(
            model.net(images), targets, pos_weight=weights)

    with torch.no_grad():
        start = float(loss())
    for _ in range(epochs):
        optimizer.zero_grad()
        loss().backward()
        optimizer.step()
    with torch.no_grad():
        end = float(loss())
    return model, {"loss_start": start, "loss_end": end, "epochs": epochs}


def predict_multilabel_probabilities(model, image):
    torch = _torch()
    model.net.eval()
    with torch.no_grad():
        tensor = _norm(torch.from_numpy(image.astype(np.float32)/255).permute(2,0,1))[None]
        probabilities = model.net(tensor).sigmoid()[0].numpy()
    return {sid: probabilities[k] for k, sid in enumerate(model.series_ids)}


def segmentation_metrics(probabilities, masks, threshold=0.5):
    """Per-series foreground metrics; background agreement is not accuracy."""
    if set(probabilities) != set(masks):
        raise ValueError("prediction and reference series differ")
    result = {}
    for sid, p in probabilities.items():
        pred, truth = np.asarray(p) >= threshold, np.asarray(masks[sid]) > 0
        if pred.shape != truth.shape:
            raise ValueError("prediction and reference shapes differ")
        tp, fp, fn = (int((pred & truth).sum()), int((pred & ~truth).sum()),
                      int((~pred & truth).sum()))
        result[sid] = {"precision": tp/max(1,tp+fp), "recall": tp/max(1,tp+fn),
                       "f1": 2*tp/max(1,2*tp+fp+fn), "iou": tp/max(1,tp+fp+fn)}
    return result
