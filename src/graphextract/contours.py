"""Digitize discrete filled contours as interval-valued scalar fields.

Geometry may be detected, but numerical calibration is always explicit. A band
is an interval, never a measurement of its midpoint. Unknown pixels stay NaN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from graphextract.calibration import fit_axis
from graphextract.schema import AxisFit, AxisRole, ScaleType, TickAnchor


@dataclass
class ColorBand:
    bgr: tuple[int, int, int]
    lower: float
    upper: float


@dataclass
class ContourResult:
    level: float
    paths: list[list[list[float]]]
    method: str = "marching_squares_on_band_midpoints"
    status: str = "interpolated"


@dataclass
class ScalarFieldResult:
    x: np.ndarray
    y: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    valid: np.ndarray
    color_residual: np.ndarray
    band_index: np.ndarray
    bands: list[ColorBand]
    plot_xywh: tuple[int, int, int, int]
    colorbar_xywh: tuple[int, int, int, int]
    x_fit: AxisFit
    y_fit: AxisFit
    unit: str
    provenance: dict = field(default_factory=dict)

    def resample(self, x, y) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Nearest native cell, with out-of-image and masked values left unknown.

        In particular, no interpolation bridges a gridline or narrows an interval.
        """
        x, y = np.asarray(x, float), np.asarray(y, float)
        if x.ndim != 1 or y.ndim != 1 or not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("resampling coordinates must be finite 1D vectors")
        if (self.x_fit.scale is ScaleType.LOG10 and np.any(x <= 0)) or (
            self.y_fit.scale is ScaleType.LOG10 and np.any(y <= 0)
        ):
            raise ValueError("logarithmic coordinates must be positive")
        px, py, w, h = self.plot_xywh
        u = np.array([self.x_fit.transform(v) - px for v in x])
        v = np.array([self.y_fit.transform(z) - py for z in y])
        inside = (
            (v[:, None] >= -1e-6)
            & (v[:, None] <= h - 1 + 1e-6)
            & (u[None, :] >= -1e-6)
            & (u[None, :] <= w - 1 + 1e-6)
        )
        iu = np.clip(np.rint(u).astype(int), 0, w - 1)
        iv = np.clip(np.rint(v).astype(int), 0, h - 1)
        valid = inside & self.valid[np.ix_(iv, iu)]
        return (
            np.where(valid, self.lower[np.ix_(iv, iu)], np.nan),
            np.where(valid, self.upper[np.ix_(iv, iu)], np.nan),
            valid,
        )

    def contours(self, levels) -> list[ContourResult]:
        """Optional derived paths; midpoint interpolation is not measured data."""
        z = (self.lower + self.upper) / 2
        # Interpolate in native pixels (log frequency is linear on the raster).
        px, py, _, _ = self.plot_xywh
        return [
            ContourResult(
                float(level),
                [
                    [[self.x_fit.invert(u + px), self.y_fit.invert(v + py)] for u, v in path]
                    for path in _marching_paths(z, self.valid & np.isfinite(z), float(level))
                ],
            )
            for level in levels
        ]


def _marching_paths(z, valid, level):
    """March fully observed cells, preserving open paths, loops, and components.

    Edge IDs join neighboring cells exactly; no coordinate-rounding merge can
    connect separate lobes. Bilinear saddle determinant resolves four crossings.
    """
    if not np.isfinite(level):
        raise ValueError("contour levels must be finite")
    full = valid[:-1, :-1] & valid[:-1, 1:] & valid[1:, :-1] & valid[1:, 1:]
    high = z >= level
    mixed = (
        (high[:-1, :-1] != high[:-1, 1:])
        | (high[:-1, :-1] != high[1:, :-1])
        | (high[:-1, :-1] != high[1:, 1:])
    )
    points, neighbors = {}, {}
    for r, c in zip(*np.where(full & mixed)):
        corners = [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]
        keys = [(0, r, c), (1, r, c + 1), (0, r + 1, c), (1, r, c)]
        hits = {}
        for k in range(4):
            ar, ac = corners[k]
            br, bc = corners[(k + 1) % 4]
            if high[ar, ac] == high[br, bc]:
                continue
            t = (level - z[ar, ac]) / (z[br, bc] - z[ar, ac])
            key = keys[k]
            points[key] = (float(ac + t * (bc - ac)), float(ar + t * (br - ar)))
            hits[k] = key
        if len(hits) == 2:
            connections = [tuple(hits)]
        elif len(hits) == 4:
            a, b, cval, d = [z[r0, c0] - level for r0, c0 in corners]
            connections = [(0, 1), (2, 3)] if a * cval - b * d >= 0 else [(0, 3), (1, 2)]
        else:
            continue
        for i, j in connections:
            left, right = hits[i], hits[j]
            neighbors.setdefault(left, set()).add(right)
            neighbors.setdefault(right, set()).add(left)
    paths = []
    # Open endpoints first; remaining connected components are cycles.
    starts = [p for p, adj in neighbors.items() if len(adj) == 1] + list(neighbors)
    for start in starts:
        if not neighbors[start]:
            continue
        path, current = [points[start]], start
        while neighbors[current]:
            following = min(neighbors[current])
            neighbors[current].remove(following)
            neighbors[following].remove(current)
            path.append(points[following])
            current = following
            if current == start:
                break
        if len(path) > 1:
            paths.append(path)
    return paths


def _box(image, box):
    if len(box) != 4 or any(int(v) != v for v in box):
        raise ValueError("boxes require four integer pixel coordinates")
    x, y, w, h = map(int, box)
    if x < 0 or y < 0 or min(w, h) < 2 or x + w > image.shape[1] or y + h > image.shape[0]:
        raise ValueError("box outside image or too small")
    return x, y, w, h


def detect_regions(image) -> tuple[tuple, tuple]:
    """Find a large colored rectangle and a separate thin colorbar candidate.

    Detection uses morphology only for region proposals, never field evidence.
    Neutral palettes and ambiguous layouts need explicit boxes.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = ((hsv[..., 1] > 65) & (hsv[..., 2] > 40)).astype(np.uint8)
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    components, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in components]
    boxes = [
        b
        for b in boxes
        if min(b[2:]) >= 5
        and b[2] * b[3] > 200
        and mask[b[1] : b[1] + b[3], b[0] : b[0] + b[2]].mean() > 0.6
    ]
    plots = [b for b in boxes if min(b[2:]) > 40 and max(b[2:]) / min(b[2:]) < 12]
    if not plots:
        raise ValueError("plot not detected; supply plot_xywh")
    plot = max(plots, key=lambda b: b[2] * b[3])
    bars = [b for b in boxes if b != plot and max(b[2:]) / min(b[2:]) > 5]
    if len(bars) != 1:
        raise ValueError("colorbar detection ambiguous; supply colorbar_xywh")
    return tuple(plot), tuple(bars[0])


def sample_bands(
    image, box, edges, *, reverse=False, boundaries=None, extend_min=False, extend_max=False
) -> list[ColorBand]:
    """Read each band away from borders. Edges are ordered numerical levels.

    Unequal physical band widths require normalized boundaries (0..1); otherwise
    equal widths are explicit in the calibration contract. Reverse handles bars
    whose numeric values decrease left-to-right or top-to-bottom.
    """
    x, y, w, h = _box(image, box)
    edges = np.asarray(edges, float)
    if (
        edges.ndim != 1
        or len(edges) < 3
        or not np.isfinite(edges).all()
        or np.any(np.diff(edges) <= 0)
    ):
        raise ValueError("at least three strictly increasing finite band edges required")
    n = len(edges) - 1
    bounds = np.asarray(boundaries if boundaries is not None else np.linspace(0, 1, n + 1))
    if (
        bounds.shape != edges.shape
        or bounds[0] != 0
        or bounds[-1] != 1
        or np.any(np.diff(bounds) <= 0)
    ):
        raise ValueError("band boundaries must increase from 0 to 1, one per edge")
    crop = image[y : y + h, x : x + w]
    if h > w:
        crop = np.transpose(crop, (1, 0, 2))
    if reverse:
        crop = crop[:, ::-1]
    palette = []
    for i in range(n):
        # The middle half excludes dark outlines and JPEG fringes.
        a = int((0.75 * bounds[i] + 0.25 * bounds[i + 1]) * crop.shape[1])
        b = int((0.25 * bounds[i] + 0.75 * bounds[i + 1]) * crop.shape[1])
        core = crop[
            crop.shape[0] // 4 : max(crop.shape[0] // 4 + 1, 3 * crop.shape[0] // 4),
            a : max(a + 1, b),
        ]
        if not core.size:
            raise ValueError("colorbar resolution insufficient for requested bands")
        color = tuple(int(v) for v in np.median(core.reshape(-1, 3), axis=0))
        palette.append(ColorBand(color, float(edges[i]), float(edges[i + 1])))
    if extend_min:
        palette[0].lower = -np.inf
    if extend_max:
        palette[-1].upper = np.inf
    return palette


def _fit(config, key, role):
    spec = config[key]
    anchors = [TickAnchor(float(p), float(v), source="manual") for p, v in spec["anchors"]]
    return fit_axis(anchors, role, spec.get("unit", ""), ScaleType(spec["scale"]))


def extract_field(image, config) -> ScalarFieldResult:
    """Extract a discrete palette using explicit, reviewable calibration."""
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("expected uint8 BGR image")
    if "plot_xywh" not in config or "colorbar_xywh" not in config:
        plot, bar = detect_regions(image)
    else:
        plot, bar = config["plot_xywh"], config["colorbar_xywh"]
    plot = _box(image, config.get("plot_xywh", plot))
    bar = _box(image, config.get("colorbar_xywh", bar))
    bands = sample_bands(
        image,
        bar,
        config["band_edges"],
        reverse=config.get("reverse_colorbar", False),
        boundaries=config.get("band_boundaries"),
        extend_min=config.get("extend_min", False),
        extend_max=config.get("extend_max", False),
    )
    xfit, yfit = _fit(config, "x", AxisRole.X), _fit(config, "y", AxisRole.Y_LEFT)
    px, py, w, h = plot
    crop = image[py : py + h, px : px + w]
    # OpenCV float Lab has physical L*,a*,b* units; uint8 Lab does not.
    lab = cv2.cvtColor(crop.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    colors = np.asarray([b.bgr for b in bands], np.float32)[None] / 255
    colors = cv2.cvtColor(colors, cv2.COLOR_BGR2LAB)[0]
    pairwise = np.linalg.norm(colors[:, None] - colors[None, :], axis=2)
    np.fill_diagonal(pairwise, np.inf)
    if pairwise.min() < 3:
        raise ValueError("palette repeats or cannot distinguish levels; color inversion ambiguous")
    limit = float(config.get("max_delta_e", 8.0))
    margin = float(config.get("min_color_margin", 2.0))
    if not np.isfinite(limit) or not np.isfinite(margin) or limit <= 0 or margin < 0:
        raise ValueError("invalid color tolerances")
    indices = np.empty((h, w), np.int16)
    residual = np.empty((h, w), np.float32)
    valid = np.zeros((h, w), bool)
    for row in range(0, h, 64):  # bounded memory on large scans
        dist = np.linalg.norm(lab[row : row + 64, :, None] - colors, axis=3)
        order = np.argsort(dist, axis=2)
        best = np.take_along_axis(dist, order[..., :2], axis=2)
        indices[row : row + 64] = order[..., 0]
        residual[row : row + 64] = best[..., 0]
        valid[row : row + 64] = (best[..., 0] <= limit) & (best[..., 1] - best[..., 0] >= margin)
    low = np.asarray([b.lower for b in bands])[indices]
    high = np.asarray([b.upper for b in bands])[indices]
    if config.get("allow_band_mixtures", True):
        # Compression/antialiasing can mix adjacent filled regions. Such pixels
        # support the UNION of the two intervals, never an interpolated scalar.
        # Black outlines and white gridlines are not compositing backgrounds here.
        palette = np.asarray([b.bgr for b in bands], np.float32) / 255
        pixels = crop.astype(np.float32) / 255
        for row in range(0, h, 64):
            block = pixels[row : row + 64]
            best = np.full(block.shape[:2], np.inf)
            second = best.copy()
            pair = np.zeros(block.shape[:2], int)
            for j in range(len(bands) - 1):
                delta = palette[j + 1] - palette[j]
                t = np.sum((block - palette[j]) * delta, axis=2) / np.sum(delta * delta)
                prediction = palette[j] + np.clip(t, 0, 1)[..., None] * delta
                distance = np.linalg.norm(
                    cv2.cvtColor(prediction, cv2.COLOR_BGR2LAB) - lab[row : row + 64], axis=2
                )
                distance = np.where((t > 0.1) & (t < 0.9), distance, np.inf)
                improved = distance < best
                second = np.where(improved, best, np.minimum(second, distance))
                pair = np.where(improved, j, pair)
                best = np.minimum(best, distance)
            # Fixed conservative model-residual limit; uncertainty grows in value
            # space, not by loosening the palette matching threshold.
            unique = np.isfinite(best) & (second > best + 2)
            use = unique & (best <= 3) & (residual[row : row + 64] > best + 2)
            low[row : row + 64][use] = np.asarray([b.lower for b in bands])[pair[use]]
            high[row : row + 64][use] = np.asarray([b.upper for b in bands])[pair[use] + 1]
            indices[row : row + 64][use] = -2
            residual[row : row + 64][use] = best[use]
            valid[row : row + 64][use] = True
    # User-specified overprints are unknown regardless of palette coincidence.
    for box in config.get("exclude_xywh", []):
        ex, ey, ew, eh = _box(image, box)
        valid[
            max(0, ey - py) : max(0, min(h, ey + eh - py)),
            max(0, ex - px) : max(0, min(w, ex + ew - px)),
        ] = False
    return ScalarFieldResult(
        np.asarray([xfit.invert(u) for u in range(px, px + w)]),
        np.asarray([yfit.invert(v) for v in range(py, py + h)]),
        np.where(valid, low, np.nan),
        np.where(valid, high, np.nan),
        valid,
        residual,
        np.where(valid, indices, -1),
        bands,
        plot,
        bar,
        xfit,
        yfit,
        config.get("unit", ""),
        {
            "calibration": config,
            "method": "discrete_palette",
            "uncertainty": "band_interval",
            "adjacent_band_mixtures": bool(config.get("allow_band_mixtures", True)),
            "inpainting": False,
        },
    )


def write_field(result, image, image_path, output_json, output_overlay):
    """JSON metadata + lossless NPZ field + visual reconstruction; strict JSON."""
    output_json, output_overlay = Path(output_json), Path(output_overlay)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_overlay.parent.mkdir(parents=True, exist_ok=True)
    array_path = output_json.with_suffix(".npz")
    outputs = {p.resolve() for p in (output_json, output_overlay, array_path)}
    if len(outputs) != 3 or Path(image_path).resolve() in outputs:
        raise ValueError("field outputs must be distinct and must not overwrite the source image")
    np.savez_compressed(
        array_path,
        x=result.x,
        y=result.y,
        lower=result.lower,
        upper=result.upper,
        valid=result.valid,
        band_index=result.band_index,
        color_residual=result.color_residual,
    )
    metadata = {
        "schema_version": 1,
        "kind": "scalar_field",
        "unit": result.unit,
        "arrays": array_path.name,
        "shape": list(result.valid.shape),
        "band_index_convention": "0..N-1=single band; -1=unknown; -2=adjacent-band union",
        "color_residual_units": "CIE76 Lab distance to fitted color model",
        "valid_fraction": float(result.valid.mean()),
        "plot_xywh": result.plot_xywh,
        "colorbar_xywh": result.colorbar_xywh,
        "axes": {"x": result.x_fit.to_dict(), "y": result.y_fit.to_dict()},
        "bands": [
            {
                "bgr": b.bgr,
                "lower": b.lower if np.isfinite(b.lower) else None,
                "upper": b.upper if np.isfinite(b.upper) else None,
            }
            for b in result.bands
        ],
        "open_bound_convention": "null lower=-infinity; null upper=+infinity",
        "image_sha256": hashlib.sha256(Path(image_path).read_bytes()).hexdigest(),
        "provenance": result.provenance,
    }
    output_json.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    preview = image.copy()
    px, py, w, h = result.plot_xywh
    patch = preview[py : py + h, px : px + w]
    colors = np.asarray([b.bgr for b in result.bands], np.uint8)
    pure = result.band_index >= 0
    patch[pure] = colors[result.band_index[pure]]
    patch[~result.valid] = (180, 180, 180)
    if not cv2.imwrite(str(output_overlay), preview):
        raise ValueError(f"could not write {output_overlay}")
    return metadata
