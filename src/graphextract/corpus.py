# -*- coding: utf-8 -*-
"""Annotated corpus (plan-20260810, section 7): inventory, splits, sidecars.

Real images live in ``datas/``; human annotations live in ``annotations/`` as
``<stem>.json`` sidecars. Renderer-exact gold for pilots is generated into
``annotations/synthetic_gold/`` (never mixed into real splits). Splits are
grouped by measurement source so crops/panels/styles of one source never leak
across train/dev/calibration/locked-test.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

ANNOTATION_VERSION = 1


@dataclass
class PanelAnnotation:
    panel_id: str
    envelope_xywh: list[int]
    interior_xywh: list[int]
    title: str = ""
    parent_id: str | None = None


@dataclass
class OcclusionEvent:
    series_id: str
    u_start: int
    u_end: int
    note: str = ""  # e.g. "hidden behind series b", "label overprint"


@dataclass
class SeriesAnnotation:
    series_id: str
    panel_id: str
    label: str
    axis_id: str = "y_left"
    # Dense visible centerline in native pixels; empty when not labelled.
    centerline_uv: list[list[float]] = field(default_factory=list)
    occlusions: list[OcclusionEvent] = field(default_factory=list)
    ambiguous: bool = False


@dataclass
class TickAnnotation:
    axis: str  # x | y_left | y_right
    pixel: float
    value: float
    unit: str
    source: str = "manual"  # manual | ocr_verified | renderer


@dataclass
class ImageAnnotation:
    image_id: str
    sha256: str
    width: int
    height: int
    panels: list[PanelAnnotation] = field(default_factory=list)
    series: list[SeriesAnnotation] = field(default_factory=list)
    ticks: list[TickAnnotation] = field(default_factory=list)
    annotator: str = ""
    status: str = "draft"  # draft | reviewed | locked
    notes: str = ""

    def to_dict(self) -> dict:
        return {"annotation_version": ANNOTATION_VERSION, **asdict(self)}

    @staticmethod
    def from_dict(d: dict) -> ImageAnnotation:
        d = dict(d)
        d.pop("annotation_version", None)
        d["panels"] = [PanelAnnotation(**p) for p in d.get("panels", [])]
        d["series"] = [
            {**s, "occlusions": [OcclusionEvent(**o) for o in s.get("occlusions", [])]}
            for s in d.get("series", [])
        ]
        d["series"] = [SeriesAnnotation(**s) for s in d["series"]]
        d["ticks"] = [TickAnnotation(**t) for t in d.get("ticks", [])]
        return ImageAnnotation(**d)


@dataclass
class CorpusItem:
    path: str
    sha256: str
    width: int
    height: int
    source_group: str
    family: str
    duplicate_group: int = -1


def source_group_for(filename: str) -> str:
    """Group key: manufacturer token (first word) — keeps one product's renders together."""
    stem = Path(filename).stem
    for cut in (" measurement", " Measurement"):
        stem = stem.split(cut)[0]
    return stem.split()[0].lower() if stem.split() else "unknown"


def family_for(filename: str) -> str:
    """Chart family heuristic from filename keywords."""
    t = filename.lower()
    if "step response" in t:
        return "step_response"
    if "thd" in t or "percent" in t:
        return "distortion_percent"
    if "distortion" in t:
        return "distortion_db"
    if "frequency response" in t or "driver" in t:
        return "frequency_response"
    return "other"


def ahash(img: npt.NDArray) -> int:
    """64-bit average hash for near-duplicate detection."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA).astype(float)
    diff = (small[:, 1:] > small[:, :-1]).flatten()
    h = 0
    for b in diff:
        h = (h << 1) | int(bool(b))
    return h


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def build_inventory(datas_dir: str | Path) -> list[CorpusItem]:
    """Scan PNGs; assign duplicate groups (exact sha or ahash distance <= 5).

    Derived ``*.overlay.png`` visualisations are skipped: they are
    extraction products, not source images, and inventorying them would
    corrupt duplicate groups and train/test splits.
    """
    items: list[CorpusItem] = []
    hashes: list[int] = []
    for path in sorted(Path(datas_dir).glob("*.png")):
        if path.name.endswith(".overlay.png"):
            continue
        img = cv2.imread(str(path))
        if img is None:
            continue
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        h, w = img.shape[:2]
        items.append(CorpusItem(
            path=path.name, sha256=sha, width=w, height=h,
            source_group=source_group_for(path.name), family=family_for(path.name),
        ))
        hashes.append(ahash(img))
    parent = list(range(len(items)))
    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i].sha256 == items[j].sha256 or _hamming(hashes[i], hashes[j]) <= 5:
                parent[find(i)] = find(j)
    groups: dict[int, int] = {}
    for i, it in enumerate(items):
        r = find(i)
        groups.setdefault(r, len(groups))
        it.duplicate_group = groups[r]
    return items


def assign_splits(items: list[CorpusItem], seed: int = 0) -> dict[str, list[str]]:
    """Group-aware split: whole source groups stay together (greedy fill)."""
    import random
    groups: dict[str, list[CorpusItem]] = {}
    for it in items:
        groups.setdefault(it.source_group, []).append(it)
    names = sorted(groups)
    rnd = random.Random(seed)
    rnd.shuffle(names)
    total = len(items)
    targets = {"train": 0.7 * total, "dev": 0.1 * total,
               "calibration": 0.1 * total, "locked_test": 0.1 * total}
    splits: dict[str, list[str]] = {k: [] for k in targets}
    order = ["train", "dev", "calibration", "locked_test"]
    for name in names:
        # Put the group where the shortfall is largest (locked_test last resort excluded
        # only if another split still needs items... simpler: largest relative shortfall).
        def shortfall(k: str) -> float:
            return targets[k] - len(splits[k]) if targets[k] > 0 else float("-inf")
        # Keep at least one group for locked_test when possible.
        best = max(order, key=shortfall)
        splits[best] += [it.path for it in groups[name]]
    # Guarantee a non-empty locked_test when there are >= 2 groups, moving a
    # whole group so source integrity is never broken for the guarantee.
    if not splits["locked_test"] and len(names) >= 2:
        donor = min(names, key=lambda n: len(groups[n]))
        for split in order:
            splits[split] = [p for p in splits[split]
                             if p not in {it.path for it in groups[donor]}]
        splits["locked_test"] += [it.path for it in groups[donor]]
    return splits


def annotation_path(annotations_dir: str | Path, image_name: str) -> Path:
    return Path(annotations_dir) / (Path(image_name).stem + ".json")


def save_annotation(annotations_dir: str | Path, annot: ImageAnnotation) -> Path:
    p = annotation_path(annotations_dir, annot.image_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(annot.to_dict(), indent=2) + "\n", encoding="utf-8")
    return p


def load_annotation(path: str | Path) -> ImageAnnotation:
    return ImageAnnotation.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def validate_annotation(annot: ImageAnnotation, image_bytes_sha: str | None = None) -> list[str]:
    """Check sidecar consistency; returns error strings (empty = valid)."""
    errs: list[str] = []
    if image_bytes_sha and annot.sha256 != image_bytes_sha:
        errs.append("sha256 mismatch: annotation is for a different rendering")
    panel_ids = {p.panel_id for p in annot.panels}
    for p in annot.panels:
        for box, name in ((p.envelope_xywh, "envelope"), (p.interior_xywh, "interior")):
            x, y, w, h = box
            if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > annot.width or y + h > annot.height:
                errs.append(f"panel {p.panel_id}: {name} box outside image")
    for s in annot.series:
        if s.panel_id not in panel_ids:
            errs.append(f"series {s.series_id}: unknown panel {s.panel_id}")
        for o in s.occlusions:
            if o.u_end < o.u_start:
                errs.append(f"series {s.series_id}: inverted occlusion interval")
    for t in annot.ticks:
        if t.axis not in ("x", "y_left", "y_right"):
            errs.append(f"tick: unknown axis {t.axis}")
        if not np.isfinite(t.value) or not np.isfinite(t.pixel):
            errs.append("tick: non-finite pixel/value")
    if annot.status not in ("draft", "reviewed", "locked"):
        errs.append(f"unknown status {annot.status}")
    return errs


def generate_synthetic_gold(out_dir: str | Path, n_panels: int = 6,
                            seed: int = 0, width: int = 320, height: int = 240) -> Path:
    """Render exact-label gold panels (image + annotation sidecar + manifest).

    This is machine gold for pilots and regression tests — never a substitute
    for human labels of real images, and never mixed into real splits.
    """
    import math
    import random
    from graphextract.render import RenderPanel, RenderSeries, render_panel

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(seed)
    palette = [(0, 0, 255), (255, 0, 0), (0, 140, 0)]
    manifest = {"generator": "generate_synthetic_gold", "seed": seed, "items": []}
    for i in range(n_panels):
        xs = np.geomspace(20, 20000, 60).tolist()
        series = []
        for k in range(rnd.choice([1, 2])):
            phase = rnd.uniform(0, 6.28)
            ys = [60.0 + rnd.uniform(4, 10) * math.sin(math.log10(f) * 3.0 + phase)
                  + rnd.uniform(-8, 8) for f in xs]
            series.append(RenderSeries(f"s{k}", palette[k % 3], xs, ys,
                                       width_px=rnd.choice([1, 2])))
        panel = RenderPanel(rect_xywh=(40, 16, width - 56, height - 48), series=series)
        truth = render_panel((width, height), panel, supersample=2)
        name = f"synth_{i:03d}.png"
        cv2.imwrite(str(out / name), truth.image)
        sha = hashlib.sha256((out / name).read_bytes()).hexdigest()
        x0, y0, w, h = panel.rect_xywh
        annot = ImageAnnotation(
            image_id=name, sha256=sha, width=width, height=height,
            panels=[PanelAnnotation(f"{name}#p0", [0, 0, width, height], [x0, y0, w, h])],
            series=[SeriesAnnotation(
                s.series_id, f"{name}#p0", s.series_id,
                centerline_uv=[[u, v] for u, v in truth.native_polylines[s.series_id]])
                for s in series],
            ticks=[TickAnnotation("x", truth.x_fit.transform(f), f, "Hz", "renderer")
                   for f in (20, 100, 1000, 10000, 20000)]
            + [TickAnnotation("y_left", truth.y_fit.transform(v), v, "dB", "renderer")
               for v in (20, 40, 60, 80, 100)],
            annotator="generate_synthetic_gold", status="locked",
            notes="machine gold; renderer-exact",
        )
        save_annotation(out, annot)
        manifest["items"].append({"image": name, "series": [s.series_id for s in series]})
    mp = out / "manifest.json"
    mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return mp
