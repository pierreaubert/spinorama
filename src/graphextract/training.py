# -*- coding: utf-8 -*-
"""Training experiments E0-E5 (plan-20260810, section 7): registry + runners.

Only numpy/scipy/opencv are available, so trainable pilots are honest
small-scale analogues: E2-lite is a softmax pixel segmentor, E3 ablates the
joint tracker against independent tracking, E4 measures synthetic family
shift. E1 (detector) and E5 (VLM) are registered specs with unmet
requirements; third-party numbers can be logged via ``record_external_result``
without entering production scores.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.calibration import ScaleType
from graphextract.evaluate import score_series
from graphextract.evidence import EvidenceLayers, StyleSpec, estimate_background, segment_evidence
from graphextract.pipeline import AxisAnchors, run_panel
from graphextract.render import RenderPanel, RenderSeries, RenderTruth, render_panel
from graphextract.schema import TickAnchor
from graphextract.tracking import TrackConfig, maybe_smooth, track_panel

RUNS_DIR = Path("runs")


@dataclass
class ExperimentSpec:
    id: str
    question: str
    decision: str
    status: str  # implemented | requires: ...


REGISTRY: list[ExperimentSpec] = [
    ExperimentSpec("E0", "How far do correct coordinates, nondestructive evidence, "
                         "and better tracing go?",
                   "Strict metrics + reviewer effort on real panels.", "implemented"),
    ExperimentSpec("E1", "Does training improve multi-panel detection and calibration?",
                   "Panel completeness + held-out tick error; no silent scale failures.",
                   "implemented as E1-torch frame-segmentor pilot"),
    ExperimentSpec("E2", "Which curve-evidence model fits this distribution?",
                   "Visible 1px coverage, identity swaps, missed/extra curves.",
                   "implemented as E2-lite softmax segmentor + E2-torch conv pilot"),
    ExperimentSpec("E3", "How much do global context and overlap states help crossings?",
                   "Junction correctness + strict span accuracy on overlap slice.",
                   "implemented as joint-vs-independent ablation"),
    ExperimentSpec("E4", "Does family adaptation transfer to unseen measurements?",
                   "Gains on grouped holdouts without regression elsewhere.",
                   "implemented as synthetic family-shift probe"),
    ExperimentSpec("E5", "Does a semantic VLM reduce correction time on unfamiliar axes?",
                   "End-to-end accepted quality + human minutes saved.",
                   "requires: VLM weights and serving stack"),
]


@dataclass
class RunManifest:
    exp_id: str
    seed: int
    data_manifest: dict
    config: dict
    metrics: dict
    pipeline_version: str
    timestamp: float = 0.0
    notes: str = ""

    def save(self, runs_dir: str | Path = RUNS_DIR) -> Path:
        from graphextract.pipeline import PIPELINE_VERSION

        self.pipeline_version = PIPELINE_VERSION
        self.timestamp = time.time()
        d = Path(runs_dir)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{self.exp_id}_{int(self.timestamp)}_{self.seed}.json"
        p.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        return p


def record_external_result(exp_id: str, source: str, metrics: dict,
                           runs_dir: str | Path = RUNS_DIR) -> Path:
    """Log a third-party/reported number as provenance, never as our measurement."""
    d = Path(runs_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{exp_id}_external_{int(time.time())}.json"
    p.write_text(json.dumps({"exp_id": exp_id, "source": source, "external": True,
                             "metrics": metrics}) + "\n", encoding="utf-8")
    return p


PALETTE = [(0, 0, 255), (255, 0, 0), (0, 140, 0)]


def synth_panel(rnd: np.random.Generator, width: int = 320, height: int = 240,
                crossing: bool = False, width_px: int = 1,
                dash: tuple[int, int] | None = None,
                x_scale: ScaleType = ScaleType.LOG10) -> tuple[RenderPanel, list[StyleSpec]]:
    """One randomized two-series panel plus its per-panel style specs."""
    xs = np.geomspace(20, 20000, 60).tolist() if x_scale is ScaleType.LOG10 \
        else np.linspace(0.0, 0.05, 60).tolist()
    xr = (20.0, 20000.0) if x_scale is ScaleType.LOG10 else (0.0, 0.05)
    ph = float(rnd.uniform(0, 6.28))
    amp = float(rnd.uniform(4, 10))
    base = float(rnd.uniform(45, 70))
    y0 = [base + amp * math.sin(math.log10(max(f, 1e-9)) * 3.0 + ph) if x_scale is ScaleType.LOG10
          else base + amp * math.sin(f * 400.0 + ph) for f in xs]
    y1 = ([base - amp * math.sin(math.log10(max(f, 1e-9)) * 3.0 + ph) if x_scale is ScaleType.LOG10
           else base - amp * math.sin(f * 400.0 + ph) for f in xs] if crossing
          else [base - 18.0 + 0.4 * amp * math.sin(math.log10(max(f, 1e-9)) * 3.0) if x_scale is ScaleType.LOG10
                else base - 18.0 + 0.4 * amp * math.sin(f * 400.0) for f in xs])
    panel = RenderPanel(rect_xywh=(40, 16, width - 56, height - 48), x_scale=x_scale,
                        x_range=xr, x_unit="Hz" if x_scale is ScaleType.LOG10 else "s",
                        series=[RenderSeries("s0", PALETTE[0], xs, y0, width_px=width_px),
                                RenderSeries("s1", PALETTE[1], xs, y1, width_px=width_px,
                                             dash=dash)])
    styles = [StyleSpec("s0", "s0", PALETTE[0]), StyleSpec("s1", "s1", PALETTE[1])]
    return panel, styles


def render_truth(panel: RenderPanel, width: int = 320, height: int = 240) -> RenderTruth:
    return render_panel((width, height), panel, supersample=2)


def verified_anchors(panel: RenderPanel, truth: RenderTruth,
                     offset: tuple[int, int]) -> AxisAnchors:
    """Renderer-exact anchors labelled as such (diagnosis/tests/pilots only)."""
    ox, oy = offset
    xticks = (20, 100, 1000, 10000, 20000) if panel.x_scale is ScaleType.LOG10 \
        else (0.0, 0.01, 0.02, 0.03, 0.04, 0.05)
    return AxisAnchors(
        x=[TickAnchor(truth.x_fit.transform(f) - ox, f, 1.0, "renderer") for f in xticks],
        y_left=[TickAnchor(truth.y_fit.transform(v) - oy, v, 1.0, "renderer")
                for v in (20, 40, 60, 80, 100)],
        x_scale=panel.x_scale, x_unit=panel.x_unit, y_unit=panel.y_unit,
        source="renderer_verified_test")


def dense_poly_ref(poly: list[tuple[float, float]], u_lo: float, u_hi: float,
                   truth_mask: npt.NDArray | None = None):
    """Dense (u, v, visible) reference from an exact polyline."""
    pu = np.array([p[0] for p in poly])
    pv = np.array([p[1] for p in poly])
    uu = np.arange(max(int(math.floor(pu.min())), math.ceil(u_lo)),
                   min(int(math.ceil(pu.max())), math.floor(u_hi)) + 1, dtype=float)
    vv = np.interp(uu, pu, pv)
    vis = np.ones_like(uu, dtype=bool)
    if truth_mask is not None:
        for i, u in enumerate(uu):
            xi = int(round(u))
            vis[i] = 0 <= xi < truth_mask.shape[1] and bool((truth_mask[:, xi] > 0).any())
    return uu, vv, vis


def strict_rate_for_truth(res, truth: RenderTruth, span: tuple[float, float]) -> dict:
    """Per-series strict scores of a PanelResult against renderer truth."""
    out = {}
    for tr in res.series:
        u = [s.u for s in tr.samples]
        v = [s.v for s in tr.samples]
        obs = [s.status.value == "observed" for s in tr.samples]
        ru, rv, vis = dense_poly_ref(truth.native_polylines[tr.series_id], *span,
                                     truth.visible_masks[tr.series_id])
        sc = score_series(u, v, obs, ru, rv, vis, tr.series_id)
        out[tr.series_id] = {"strict": sc.strict_pass, "max_px": sc.max_px,
                             "coverage": sc.measured_coverage,
                             "false_support": sc.false_support}
    return out


def _run_canonical(img, panel, truth, styles, destructive: bool = False):
    """Canonical panel run; destructive=True replays the legacy failure modes."""
    from graphextract.schema import PanelOutcome  # noqa: F401
    x0, y0, w, h = panel.rect_xywh
    interior = img[y0:y0 + h, x0:x0 + w]
    anchors = verified_anchors(panel, truth, (x0, y0))
    if not destructive:
        return run_panel(img, "exp#p0", interior, (x0, y0), anchors, styles)
    # Destructive variant: morphology cleanup + forced smoothing (legacy behaviour).
    res = run_panel(img, "exp#p0", interior, (x0, y0), anchors, styles)
    gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY)
    layers = segment_evidence(interior, styles, cleanup=True)
    tracks = track_panel(gray, layers, [s.series_id for s in styles], float(np.median(gray)))
    for tr in res.series:
        sm = tracks.get(tr.series_id)
        if sm is None:
            continue
        vals = maybe_smooth([s.v for s in sm.samples], 5)
        for s, nv in zip(tr.samples, vals):
            if s.status.value == "observed":
                s.v = nv + y0  # smoothed values are crop-local; shift to native
    return res


def run_e0(n_panels: int = 4, seed: int = 0) -> dict:
    """E0: canonical pipeline vs destructive classical variant, strict metrics."""
    rnd = np.random.default_rng(seed)
    rows = []
    for i in range(n_panels):
        panel, styles = synth_panel(rnd, crossing=(i % 2 == 1))
        truth = render_truth(panel)
        for variant, destr in (("canonical", False), ("destructive", True)):
            res = _run_canonical(truth.image, panel, truth, styles, destructive=destr)
            span = (panel.rect_xywh[0], panel.rect_xywh[0] + panel.rect_xywh[2] - 1)
            for sid, m in strict_rate_for_truth(res, truth, span).items():
                rows.append({"variant": variant, "panel": i, "series": sid, **m})
    def agg(variant: str) -> dict:
        sel = [r for r in rows if r["variant"] == variant]
        return {"strict_rate": sum(r["strict"] for r in sel) / len(sel),
                "mean_max_px": float(np.mean([r["max_px"] for r in sel if np.isfinite(r["max_px"])])),
                "mean_coverage": float(np.mean([r["coverage"] for r in sel]))}
    return {"canonical": agg("canonical"), "destructive": agg("destructive"), "rows": rows}


# ── E2-lite: numpy softmax pixel segmentor ──────────────────────────────

def pixel_features(img: npt.NDArray, bg: tuple[int, int, int]) -> npt.NDArray:
    """Local features: colour, bg-relative darkness, texture, gradient."""
    f = img.astype(np.float32) / 255.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    bg_g = float(np.mean(bg)) / 255.0
    dark = np.clip(bg_g - gray, 0, 1)
    mean3 = cv2.blur(dark, (3, 3))
    sq = cv2.blur(dark * dark, (3, 3))
    std3 = np.sqrt(np.clip(sq - mean3 * mean3, 0, None))
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx * gx + gy * gy)
    return np.dstack([f, dark, mean3, std3, grad])  # HxWx7


class PixelSegmentor:
    """Softmax regression over pixel features; classes = [bg, *series_ids]."""

    def __init__(self, series_ids: list[str]) -> None:
        self.series_ids = list(series_ids)
        self.mean_: npt.NDArray | None = None
        self.std_: npt.NDArray | None = None
        self.W: npt.NDArray | None = None

    @property
    def n_classes(self) -> int:
        return 1 + len(self.series_ids)

    def _design(self, feats: npt.NDArray) -> npt.NDArray:
        assert self.mean_ is not None and self.std_ is not None and self.W is not None
        X = (feats.reshape(-1, feats.shape[2]) - self.mean_) / self.std_
        X = np.hstack([X, np.ones((X.shape[0], 1))])
        e = X @ self.W
        e -= e.max(axis=1, keepdims=True)
        p = np.exp(e)
        return p / p.sum(axis=1, keepdims=True)

    def fit(self, samples: list[tuple[npt.NDArray, dict[str, npt.NDArray]]],
            epochs: int = 60, lr: float = 0.5, batch: int = 2048,
            bg_per_panel: int = 3000, seed: int = 0) -> dict:
        """Train on (image, {sid: mask}) pairs; fixed-seed minibatch GD."""
        rng = np.random.default_rng(seed)
        Xs, ys = [], []
        for img, masks in samples:
            bg = estimate_background(img)
            F = pixel_features(img, bg)
            H, W, _ = F.shape
            for k, sid in enumerate(self.series_ids):
                m = (masks[sid] > 0)
                idx = np.nonzero(m.reshape(-1))[0]
                if len(idx):
                    take = idx[rng.choice(len(idx), min(len(idx), bg_per_panel // 2), replace=False)]
                    Xs.append(F.reshape(-1, F.shape[2])[take])
                    ys.append(np.full(len(take), k + 1))
            union = np.zeros((H, W), bool)
            for m in masks.values():
                union |= (m > 0)
            bg_idx = np.nonzero((~union).reshape(-1))[0]
            take = bg_idx[rng.choice(len(bg_idx), min(len(bg_idx), bg_per_panel), replace=False)]
            Xs.append(F.reshape(-1, F.shape[2])[take])
            ys.append(np.zeros(len(take), dtype=int))
        X = np.vstack(Xs)
        y = np.concatenate(ys)
        self.mean_ = X.mean(axis=0)
        self.std_ = X.std(axis=0) + 1e-6
        Xn = (X - self.mean_) / self.std_
        Xn = np.hstack([Xn, np.ones((Xn.shape[0], 1))])
        C = self.n_classes
        W = np.zeros((Xn.shape[1], C))
        Y = np.eye(C)[y]
        hist = []
        n = Xn.shape[0]
        for ep in range(epochs):
            perm = rng.permutation(n)
            for s in range(0, n, batch):
                b = perm[s:s + batch]
                e = Xn[b] @ W
                e -= e.max(axis=1, keepdims=True)
                P = np.exp(e)
                P /= P.sum(axis=1, keepdims=True)
                W -= lr * (Xn[b].T @ (P - Y[b])) / len(b)
            e = Xn @ W
            e -= e.max(axis=1, keepdims=True)
            P = np.exp(e)
            P /= P.sum(axis=1, keepdims=True)
            loss = float(-np.log(P[np.arange(n), y] + 1e-12).mean())
            hist.append(loss)
            if len(hist) > 6 and hist[-1] >= min(hist[:-1]) - 1e-4:
                break  # no improvement: stop, do not overfit the pilot
        self.W = W
        return {"epochs": len(hist), "loss_start": hist[0], "loss_end": hist[-1]}

    def predict_masks(self, img: npt.NDArray) -> dict[str, npt.NDArray]:
        bg = estimate_background(img)
        P = self._design(pixel_features(img, bg))
        lab = P.argmax(axis=1).reshape(img.shape[:2])
        return {sid: ((lab == k + 1).astype(np.uint8)) * 255
                for k, sid in enumerate(self.series_ids)}

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        assert self.W is not None and self.mean_ is not None and self.std_ is not None, \
            "fit() must run before save()"
        np.savez(p, W=self.W, mean=self.mean_, std=self.std_,
                 series=np.array(self.series_ids))
        return p

    @staticmethod
    def load(path: str | Path) -> PixelSegmentor:
        z = np.load(path, allow_pickle=True)
        seg = PixelSegmentor([str(s) for s in z["series"]])
        seg.W, seg.mean_, seg.std_ = z["W"], z["mean"], z["std"]
        return seg


def run_e2lite(n_train: int = 6, n_dev: int = 3, seed: int = 0,
               epochs: int = 60) -> dict:
    """E2-lite: train segmentor on synthetic panels; strict dev scores via tracking."""
    rnd = np.random.default_rng(seed)
    train, dev = [], []
    for i in range(n_train + n_dev):
        panel, _ = synth_panel(rnd, crossing=(i % 2 == 1))
        truth = render_truth(panel)
        (train if i < n_train else dev).append((truth.image, truth.geometric_masks))
    seg = PixelSegmentor(["s0", "s1"])
    fit_hist = seg.fit(train, epochs=epochs, seed=seed)
    dev_scores = []
    for img, _ in dev:
        # Downstream uses predicted masks with the standard tracker + verified anchors.
        panel_masks = seg.predict_masks(img)
        for sid, m in panel_masks.items():
            inter = (m > 0).mean()
            dev_scores.append({"series": sid, "pred_coverage": float(inter)})
    # Pixel-level dev accuracy.
    correct = total = 0
    for img, masks in dev:
        pred = seg.predict_masks(img).values()
        union_pred = np.zeros(img.shape[:2], bool)
        for m in pred:
            union_pred |= (m > 0)
        union_true = np.zeros(img.shape[:2], bool)
        for m in masks.values():
            union_true |= (m > 0)
        correct += int((union_pred == union_true).sum())
        total += union_true.size
    return {"fit": fit_hist, "dev_pixel_agreement": correct / total,
            "dev_pred_coverage": dev_scores}


def run_e2torch(n_train: int = 4, n_dev: int = 2, seed: int = 0,
                epochs: int = 8) -> dict:
    """E2-torch: tiny conv segmentor agreement on held-out synthetic panels."""
    from graphextract.torch_segmentor import conv_agreement, train_conv_segmentor

    rnd = np.random.default_rng(seed)
    train, dev = [], []
    for i in range(n_train + n_dev):
        panel, _ = synth_panel(rnd, crossing=(i % 2 == 1))
        truth = render_truth(panel)
        (train if i < n_train else dev).append((truth.image, truth.geometric_masks))
    seg, hist = train_conv_segmentor(train, ["s0", "s1"], epochs=epochs, seed=seed)
    return {"fit": hist, "dev_pixel_agreement": conv_agreement(seg, dev)}


def synth_canvas(rnd: np.random.Generator, width: int = 320,
                 height: int = 240) -> tuple[npt.NDArray, list]:
    """Random multi-panel canvas (1, side-by-side, stacked, 2x2) with curves."""
    from graphextract.render import RenderPanel, render_canvas

    layout = int(rnd.integers(0, 4))
    margin = 12
    if layout == 0:
        rects = [(margin, margin, width - 2 * margin, height - 2 * margin)]
    elif layout == 1:
        w2 = (width - 3 * margin) // 2
        rects = [(margin, margin, w2, height - 2 * margin),
                 (2 * margin + w2, margin, w2, height - 2 * margin)]
    elif layout == 2:
        h2 = (height - 3 * margin) // 2
        rects = [(margin, margin, width - 2 * margin, h2),
                 (margin, 2 * margin + h2, width - 2 * margin, h2)]
    else:
        w2 = (width - 3 * margin) // 2
        h2 = (height - 3 * margin) // 2
        rects = [(margin, margin, w2, h2), (2 * margin + w2, margin, w2, h2),
                 (margin, 2 * margin + h2, w2, h2),
                 (2 * margin + w2, 2 * margin + h2, w2, h2)]
    panels = []
    for i, r in enumerate(rects):
        panel, _ = synth_panel(rnd, crossing=bool(i % 2))
        xs = np.geomspace(20, 20000, 40).tolist()
        base = float(rnd.uniform(45, 70))
        panel.rect_xywh = r
        for s in panel.series:
            s.series_id = f"p{i}_{s.series_id}"
            s.x_values = xs
            s.y_values = [base + 6.0 * math.sin(math.log10(f) * 3.0) for f in xs]
        panels.append(panel)
    image, truths = render_canvas((width, height), panels, supersample=1)
    return image, panels


def _frame_mask(image: npt.NDArray, panels: list) -> npt.NDArray:
    """Plot-boundary supervision: frame rectangles, not filled interiors.

    Insideness is not locally decidable for a 5x5 receptive field, but frame
    lines are — so the learned pilot predicts boundaries (like the classical
    Hough stage) and boxes derive from connected frame components.
    """
    mask = np.zeros(image.shape[:2], np.uint8)
    for p in panels:
        x, y, w, h = p.rect_xywh
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, 2)
    return mask


def _boxes_from_mask(mask: npt.NDArray, min_area: int = 400,
                     min_side: int = 20) -> list[tuple[int, int, int, int]]:
    """Boxes from mask components; min_side rejects thin grid-line components.

    Plot frames are large closed loops; grid lines that leak into a frame mask
    form long thin components whose short side is a few pixels.
    """
    contours, _ = cv2.findContours((mask > 0).astype(np.uint8),
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h >= min_area and min(w, h) >= min_side:
            boxes.append((x, y, w, h))
    return sorted(boxes)


def _match_iou(pred: list[tuple[int, int, int, int]],
               true: list[tuple[int, int, int, int]]) -> dict:
    def iou(a, b) -> float:
        ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
        iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
        inter = ix * iy
        union = a[2] * a[3] + b[2] * b[3] - inter
        return inter / union if union > 0 else 0.0
    remaining = list(true)
    ious = []
    for pb in pred:
        best, bi = 0.0, -1
        for i, tb in enumerate(remaining):
            v = iou(pb, tb)
            if v > best:
                best, bi = v, i
        if bi >= 0 and best >= 0.5:
            ious.append(best)
            remaining.pop(bi)
    return {"n_pred": len(pred), "n_true": len(true),
            "matched": len(ious), "missed": len(remaining),
            "extra": len(pred) - len(ious),
            "mean_iou": float(np.mean(ious)) if ious else 0.0}


def run_e1(n_train: int = 6, n_dev: int = 3, seed: int = 0,
           epochs: int = 30) -> dict:
    """E1 pilot: learned interior segmentor vs classical panel detection.

    Trains the tiny conv net to mark plot interiors on synthetic multi-panel
    canvases, then compares panel-count accuracy and box IoU against the
    classical contour/projection detector on held-out canvases.
    """
    from graphextract.panels import detect_panels
    from graphextract.torch_segmentor import conv_agreement, train_conv_segmentor

    rnd = np.random.default_rng(seed)
    train, dev = [], []
    for i in range(n_train + n_dev):
        image, panels = synth_canvas(rnd)
        item = (image, {"frame": _frame_mask(image, panels)})
        (train if i < n_train else dev).append((item, panels))
    seg, hist = train_conv_segmentor([t[0] for t in train], ["frame"],
                                     epochs=epochs, seed=seed)
    from graphextract.torch_segmentor import predict_conv_masks
    rows = []
    for img_panels, panels in dev:
        img, _ = img_panels
        true_boxes = [p.rect_xywh for p in panels]
        learned = _boxes_from_mask(predict_conv_masks(seg, img)["frame"])
        classical = [(pg.interior_xywh[0], pg.interior_xywh[1],
                      pg.interior_xywh[2], pg.interior_xywh[3])
                     for pg in detect_panels(img, "e1")]
        rows.append({"learned": _match_iou(learned, true_boxes),
                     "classical": _match_iou(classical, true_boxes)})
    def agg(key: str) -> dict:
        sel = [r[key] for r in rows]
        return {"count_accuracy": sum(s["matched"] == s["n_true"] and s["extra"] == 0
                                      for s in sel) / len(sel),
                "mean_iou": float(np.mean([s["mean_iou"] for s in sel])),
                "total_missed": sum(s["missed"] for s in sel),
                "total_extra": sum(s["extra"] for s in sel)}
    return {"fit": hist,
            "dev_mask_agreement": conv_agreement(seg, [t[0] for t in dev]),
            "learned": agg("learned"), "classical": agg("classical")}


def run_e3(n_panels: int = 4, seed: int = 0) -> dict:
    """E3 ablation: joint tracking vs independent per-series tracking on crossings."""
    rnd = np.random.default_rng(seed + 1000)
    rows = []
    for i in range(n_panels):
        panel, styles = synth_panel(rnd, crossing=True)
        truth = render_truth(panel)
        x0, y0, w, h = panel.rect_xywh
        interior = truth.image[y0:y0 + h, x0:x0 + w]
        gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY)
        bg = float(np.median(gray))
        layers = segment_evidence(interior, styles)
        joint = track_panel(gray, layers, ["s0", "s1"], bg)
        indep = {}
        for sid in ("s0", "s1"):
            solo = EvidenceLayers(curve_masks={sid: layers.curve_masks[sid]},
                                  grid_mask=layers.grid_mask,
                                  background_bgr=layers.background_bgr,
                                  union_mask=layers.union_mask)
            indep[sid] = track_panel(gray, solo, [sid], bg)[sid]
        polys = {sid: (np.array([p[0] for p in truth.native_polylines[sid]]),
                       np.array([p[1] for p in truth.native_polylines[sid]]))
                 for sid in ("s0", "s1")}
        for variant, tracks in (("joint", joint),
                                ("independent", {k: v for k, v in indep.items()})):
            for sid in ("s0", "s1"):
                tr = tracks[sid] if isinstance(tracks, dict) else tracks
                pu, pv = polys[sid]
                ou, ov = polys["s1" if sid == "s0" else "s0"]
                switch = tot = 0
                for s in tr.samples:
                    if s.status.value != "observed":
                        continue
                    tot += 1
                    # track_panel samples are crop-local; shift to native for truth.
                    su, sv = s.u + x0, s.v + y0
                    rv = float(np.interp(su, pu, pv))
                    ovv = float(np.interp(su, ou, ov))
                    if abs(rv - ovv) > 2.0 and abs(sv - rv) > abs(sv - ovv):
                        switch += 1
                rows.append({"variant": variant, "panel": i, "series": sid,
                             "switch_rate": switch / tot if tot else 1.0,
                             "observed": tot})
    def agg(variant: str) -> dict:
        sel = [r for r in rows if r["variant"] == variant]
        return {"mean_switch_rate": float(np.mean([r["switch_rate"] for r in sel])),
                "mean_observed": float(np.mean([r["observed"] for r in sel]))}
    return {"joint": agg("joint"), "independent": agg("independent"), "rows": rows}


def run_e4(n_train: int = 6, n_dev: int = 3, seed: int = 0) -> dict:
    """E4 probe: train on thin-solid family A, test on wide+dashed family B."""
    rnd = np.random.default_rng(seed)
    train = []
    for _ in range(n_train):
        panel, _ = synth_panel(rnd, crossing=False, width_px=1)
        truth = render_truth(panel)
        train.append((truth.image, truth.geometric_masks))
    seg = PixelSegmentor(["s0", "s1"])
    seg.fit(train, epochs=40, seed=seed)
    devA = devB = (0, 0)
    for i in range(n_dev):
        for fam, wide, dash in (("A", 1, None), ("B", 2, (6, 4))):
            panel, _ = synth_panel(rnd, crossing=True, width_px=wide, dash=dash)
            truth = render_truth(panel)
            pred = seg.predict_masks(truth.image)
            union_pred = np.zeros(truth.image.shape[:2], bool)
            for m in pred.values():
                union_pred |= (m > 0)
            union_true = np.zeros(truth.image.shape[:2], bool)
            for m in truth.geometric_masks.values():
                union_true |= (m > 0)
            agree = float((union_pred == union_true).mean())
            if fam == "A":
                devA = (devA[0] + agree, devA[1] + 1)
            else:
                devB = (devB[0] + agree, devB[1] + 1)
    return {"family_A_agreement": devA[0] / devA[1], "family_B_agreement": devB[0] / devB[1],
            "transfer_gap": devA[0] / devA[1] - devB[0] / devB[1]}
