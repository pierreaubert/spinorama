"""Reproducible extraction comparisons and hash-locked real-image evaluation.

Synthetic results isolate geometry and are explicitly oracle diagnostics. Real
manifest runs call the image-only CLI path; annotations never reach extraction.
Use --help for commands. A report does not certify production acceptance.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time

import cv2
import numpy as np

from graphextract.evaluate import score_series
from graphextract.evidence import StyleSpec, segment_evidence
from graphextract.schema import SegmentStatus
from graphextract.tracking import TrackConfig, track_sid_bidirectional


def stress_cases(seed=104729, count=12):
    """Frozen v1 diagnostic families, including identical hues and notches.

    Ground truth is the rendered integer centerline; visibility follows final
    draw order, dash gaps and overprints. Compression changes only the input.
    """
    rng = np.random.default_rng(seed)
    families = ("crossing", "notch", "dashes", "near_colors", "same_color", "jpeg")
    for k in range(count):
        h, w = 128, 192
        u = np.arange(w)
        family = families[k % len(families)]
        paths = [
            np.rint(35 + 0.28 * u + 4 * np.sin(u / 19)),
            np.rint(94 - 0.28 * u + 4 * np.cos(u / 23)),
        ]
        if family == "notch":
            paths[0] = np.rint(35 + 65 * np.exp(-(((u - 100) / 7) ** 2)) + 5 * np.sin(u / 17))
        colors = [
            (int(rng.integers(0, 60)), int(rng.integers(0, 80)), 210),
            (210, int(rng.integers(0, 80)), int(rng.integers(0, 60))),
        ]
        if family == "near_colors":
            colors[1] = tuple(min(255, c + 18) for c in colors[0])
        if family == "same_color":
            colors[1] = colors[0]
        image = np.full((h, w, 3), 255, np.uint8)
        image[::32] = 220
        masks = {}
        for j, path in enumerate(paths):
            mask = np.zeros((h, w), np.uint8)
            mask[path.astype(int), u] = 255
            if family == "dashes":
                mask[:, (u + 3 * j) % 13 >= 8] = 0
            if family in ("jpeg", "near_colors"):
                mask = cv2.dilate(mask, np.ones((3, 1), np.uint8))
            image[mask > 0] = colors[j]
            for prior in masks.values():
                prior[mask > 0] = 0
            masks[f"s{j}"] = mask
        if family == "jpeg":
            cv2.rectangle(image, (75, 45), (115, 65), (255, 255, 255), -1)
            cv2.putText(image, "label", (76, 59), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
            for mask in masks.values():
                mask[45:66, 75:116] = 0
            ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 65])
            if not ok:
                raise ValueError("JPEG encoding failed")
            image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        yield {
            "id": f"v1-{seed}-{k:03d}-{family}",
            "family": family,
            "image": image,
            "styles": [StyleSpec(f"s{j}", f"s{j}", c) for j, c in enumerate(colors)],
            "paths": paths,
            "masks": masks,
        }


def _score_track(track, path, visible):
    return score_series(
        [s.u for s in track.samples],
        [s.v for s in track.samples],
        [s.status is SegmentStatus.OBSERVED for s in track.samples],
        np.arange(len(path)),
        np.asarray(path),
        visible,
        track.series_id,
    )


def score_scalar_field(field, truth):
    """Coverage and interval containment against independently known scalar values.

    NaN reference cells are occluded/unverifiable; claiming them is false support.
    Reporting only containment would reward abstaining everywhere, so coverage
    and accepted counts are always included.
    """
    truth = np.asarray(truth, float)
    if truth.shape != field.valid.shape:
        raise ValueError("scalar reference shape differs from extraction")
    supported = np.isfinite(truth)
    accepted = field.valid & supported
    contained = accepted & (field.lower <= truth) & (truth <= field.upper)
    widths = (field.upper - field.lower)[accepted]
    return {
        "n_reference": int(supported.sum()),
        "n_accepted": int(accepted.sum()),
        "visible_coverage": float(accepted.sum() / max(1, supported.sum())),
        "interval_containment": float(contained.sum() / max(1, accepted.sum())),
        "mean_interval_width": float(np.mean(widths)) if widths.size else None,
        "false_support": float((field.valid & ~supported).sum() / max(1, field.valid.sum())),
    }


def contour_diagnostics(allow_band_mixtures=True):
    """Discrete lobed scalar field, then a compressed rendering of the same gold."""
    from graphextract.contours import extract_field

    yy, xx = np.mgrid[:80, :120]
    truth = -14 + 14 * np.exp(-(((yy - 40) / 25) ** 2)) + 2 * np.sin(xx / 13)
    truth = np.clip(truth, -14.99, 2.99)
    edges = [-15, -12, -9, -6, -3, 0, 3]
    palette = np.array(
        [
            (180, 20, 10),
            (220, 100, 10),
            (190, 210, 20),
            (20, 220, 160),
            (10, 170, 230),
            (10, 30, 230),
        ],
        np.uint8,
    )
    image = np.full((110, 135, 3), 255, np.uint8)
    image[5:85, 5:125] = palette[np.digitize(truth, edges) - 1]
    for i in range(6):
        image[96:104, 5 + 20 * i : 25 + 20 * i] = palette[i]
    image[45, 5:125] = 230
    gold = truth.copy()
    gold[40] = np.nan
    config = {
        "plot_xywh": [5, 5, 120, 80],
        "colorbar_xywh": [5, 96, 120, 8],
        "band_edges": edges,
        "allow_band_mixtures": allow_band_mixtures,
        "unit": "dB",
        "x": {"scale": "log10", "anchors": [[5, 100], [65, 1000], [125, 10000]], "unit": "Hz"},
        "y": {"scale": "linear", "anchors": [[5, 90], [45, 0], [85, -90]], "unit": "deg"},
    }
    report = []
    for compression in (None, 70):
        rendered = image
        if compression is not None:
            ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, compression])
            if not ok:
                raise ValueError("JPEG encoding failed")
            rendered = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        field = extract_field(rendered, config)
        report.append(
            {
                "jpeg_quality": compression,
                "image_sha256": hashlib.sha256(rendered.tobytes()).hexdigest(),
                **score_scalar_field(field, gold),
            }
        )
    return report


def synthetic_comparison(seed=104729, count=12, learned=False):
    if count < 1:
        raise ValueError("positive case count required")
    model = None
    if learned:
        from graphextract.torch_segmentor import train_multilabel_segmentor

        # Independent generator seed, never fit on evaluation cases.
        training = list(stress_cases(seed + 1, 12))
        model, _ = train_multilabel_segmentor(
            [(c["image"], c["masks"]) for c in training], ["s0", "s1"], epochs=20
        )
    records = []
    for case in stress_cases(seed, count):
        image, styles = case["image"], case["styles"]
        layers = segment_evidence(image, styles)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        colors = {s.series_id: s.bgr for s in styles}
        variants = ["legacy", "temporal"] + (["temporal_multilabel"] if learned else [])
        record = {
            "id": case["id"],
            "family": case["family"],
            "image_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
            "variants": {},
        }
        for variant in variants:
            if variant == "temporal_multilabel":
                from graphextract.torch_segmentor import predict_multilabel_probabilities

                layers.curve_probabilities = predict_multilabel_probabilities(model, image)
            started = time.perf_counter()
            scores = []
            for j, style in enumerate(styles):
                tr = track_sid_bidirectional(
                    gray,
                    layers,
                    style.series_id,
                    255,
                    TrackConfig(backend="legacy" if variant == "legacy" else "temporal"),
                    colors,
                    image,
                )[style.series_id]
                visible = (
                    case["masks"][style.series_id][
                        case["paths"][j].astype(int), np.arange(image.shape[1])
                    ]
                    > 0
                )
                scores.append(asdict(_score_track(tr, case["paths"][j], visible)))
            record["variants"][variant] = {
                "seconds": time.perf_counter() - started,
                "series": scores,
            }
        records.append(record)
    summary = {}
    for variant in records[0]["variants"]:
        scores = [s for r in records for s in r["variants"][variant]["series"]]
        summary[variant] = {
            "strict_series": sum(s["strict_pass"] for s in scores),
            "n_series": len(scores),
            "mean_visible_coverage": float(np.mean([s["measured_coverage"] for s in scores])),
            "mean_false_support": float(np.mean([s["false_support"] for s in scores])),
            "n_series_with_observations": int(sum(np.isfinite(s["p95_px"]) for s in scores)),
            "mean_p95_px_observed_series": (
                float(np.mean([s["p95_px"] for s in scores if np.isfinite(s["p95_px"])]))
                if any(np.isfinite(s["p95_px"]) for s in scores)
                else None
            ),
        }
    return {
        "benchmark_version": 1,
        "mode": "synthetic_tracking_diagnostic",
        "oracle_inputs_used": ["plot_geometry", "series_count", "series_colors"],
        "seed": seed,
        "summary": summary,
        "cases": records,
        "contour_diagnostics": contour_diagnostics(),
    }


def load_locked_manifest(path):
    """Validate hashes, annotation status, and source/duplicate split isolation."""
    from graphextract.corpus import load_annotation, validate_annotation

    path = Path(path)
    data = json.loads(path.read_text())
    if data.get("version") != 1 or not data.get("cases"):
        raise ValueError("expected nonempty version 1 locked manifest")
    groups, hashes, ids = {}, {}, set()
    result = []
    for case in data["cases"]:
        if case["id"] in ids or case["split"] not in ("train", "dev", "calibration", "locked_test"):
            raise ValueError("duplicate ID or invalid split")
        ids.add(case["id"])
        image, annotation = path.parent / case["image"], path.parent / case["annotation"]
        for file, key in ((image, "image_sha256"), (annotation, "annotation_sha256")):
            if hashlib.sha256(file.read_bytes()).hexdigest() != case[key]:
                raise ValueError(f"hash mismatch: {file}")
        for mapping, key in ((groups, case["source_group"]), (hashes, case["image_sha256"])):
            if not key or mapping.setdefault(key, case["split"]) != case["split"]:
                raise ValueError("source or duplicate image leaks across splits")
        ann = load_annotation(annotation)
        errors = validate_annotation(ann, case["image_sha256"])
        if errors or ann.status != "locked" or not ann.panels or not ann.series:
            raise ValueError(f"invalid/unlocked annotation: {annotation}: {errors}")
        raster = cv2.imread(str(image))
        if raster is None or raster.shape[:2] != (ann.height, ann.width):
            raise ValueError("annotation dimensions differ from image")
        if not ann.ticks or (len(ann.panels) > 1 and any(t.panel_id is None for t in ann.ticks)):
            raise ValueError("calibration gold required; multi-panel ticks need panel_id")
        # Matching is semantic, never best-curve rematching that conceals swaps.
        for panel in ann.panels:
            labels = [s.label for s in ann.series if s.panel_id == panel.panel_id]
            if len(labels) != len(set(labels)) or not all(labels):
                raise ValueError("unique nonempty annotated labels required per panel")
        result.append((case, image, ann))
    return result


def evaluate_manifest(path, split="locked_test", tracker="legacy"):
    from graphextract.cli import extract_image
    from scipy.optimize import linear_sum_assignment

    cases = load_locked_manifest(path)
    records = []
    with tempfile.TemporaryDirectory() as temp:
        for case, image, ann in cases:
            if case["split"] != split:
                continue
            started = time.perf_counter()
            try:
                doc = extract_image(
                    image, Path(temp) / "result.json", Path(temp) / "overlay.png", tracker=tracker
                )
            except Exception as exc:
                records.append({"id": case["id"], "complete": False, "error": str(exc)})
                continue
            # Geometry-only one-to-one panel matching. No curve-shape matching.
            overlaps = np.zeros((len(ann.panels), len(doc.panels)))
            for i, a in enumerate(ann.panels):
                ax, ay, aw, ah = a.interior_xywh
                for j, b in enumerate(doc.panels):
                    bx, by, bw, bh = b.panel.interior_xywh
                    inter = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
                        0, min(ay + ah, by + bh) - max(ay, by)
                    )
                    overlaps[i, j] = inter / max(1, aw * ah + bw * bh - inter)
            rows, cols = linear_sum_assignment(-overlaps)
            matched = {i: j for i, j in zip(rows, cols) if overlaps[i, j] >= 0.5}
            scores, failures = [], []
            if len(matched) != len(ann.panels) or len(matched) != len(doc.panels):
                failures.append("missing or extra panels")
            for i, panel in enumerate(ann.panels):
                expected = [s for s in ann.series if s.panel_id == panel.panel_id]
                predicted = doc.panels[matched[i]].series if i in matched else []
                predicted_panel = doc.panels[matched[i]] if i in matched else None
                calibration = [t for t in ann.ticks if t.panel_id in (None, panel.panel_id)]
                required_axes = {"x"} | {s.axis_id for s in expected}
                for axis in required_axes:
                    ticks = [t for t in calibration if t.axis == axis]
                    fit = predicted_panel.axes.get(axis) if predicted_panel else None
                    if fit is None or len(ticks) < 2:
                        failures.append(f"{panel.panel_id}: missing calibrated {axis}")
                        continue
                    try:
                        errors = [abs(fit.transform(t.value) - t.pixel) for t in ticks]
                        if (
                            not np.isfinite(errors).all()
                            or max(errors) > 1
                            or any(t.unit != fit.unit for t in ticks)
                        ):
                            failures.append(f"{panel.panel_id}: incorrect {axis} calibration/units")
                    except (ValueError, OverflowError):
                        failures.append(f"{panel.panel_id}: invalid {axis} transform")
                if sorted(s.label for s in expected) != sorted(s.label for s in predicted):
                    failures.append(f"{panel.panel_id}: missing/extra identities")
                for ref in expected:
                    uv = np.asarray(ref.centerline_uv, float)
                    if uv.ndim != 2 or uv.shape[1] != 2 or len(uv) < 2:
                        raise ValueError("dense native reference required")
                    if np.any(np.diff(uv[:, 0]) > 1.001):
                        raise ValueError("sparse gold polylines are not dense visible references")
                    # Require dense columns; never interpolate through unannotated holes.
                    visible = np.ones(len(uv), bool)
                    for occlusion in ref.occlusions:
                        visible &= ~(
                            (uv[:, 0] >= occlusion.u_start) & (uv[:, 0] <= occlusion.u_end)
                        )
                    pred = next((s for s in predicted if s.label == ref.label), None)
                    samples = pred.samples if pred else []
                    score = score_series(
                        [s.u for s in samples],
                        [s.v for s in samples],
                        [s.status is SegmentStatus.OBSERVED for s in samples],
                        uv[:, 0],
                        uv[:, 1],
                        visible,
                        ref.series_id,
                    )
                    scores.append(asdict(score))
                    if pred is None or pred.axis_id != ref.axis_id or ref.ambiguous:
                        failures.append(f"{ref.series_id}: missing/wrong axis/ambiguous gold")
            records.append(
                {
                    "id": case["id"],
                    "series": scores,
                    "failures": failures,
                    "complete": not failures
                    and bool(scores)
                    and all(s["strict_pass"] for s in scores),
                    "seconds": time.perf_counter() - started,
                }
            )
    if not records:
        raise ValueError("requested split is empty")
    return {
        "benchmark_version": 1,
        "mode": "image_only",
        "oracle_inputs_used": False,
        "manifest_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "tracker": tracker,
        "split": split,
        "cases": records,
        "complete_images": sum(r["complete"] for r in records),
        "n_images": len(records),
    }


def _finite_json(value):
    if isinstance(value, dict):
        return {k: _finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite_json(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="hash-locked real annotation manifest")
    parser.add_argument("--split", default="locked_test")
    parser.add_argument("--tracker", choices=("legacy", "temporal"), default="legacy")
    parser.add_argument("--seed", type=int, default=104729)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--learned", action="store_true", help="also train/test multilabel pilot")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = (
        evaluate_manifest(args.manifest, args.split, args.tracker)
        if args.manifest
        else synthetic_comparison(args.seed, args.count, args.learned)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(_finite_json(report), indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            _finite_json(
                report.get(
                    "summary",
                    {k: report[k] for k in ("complete_images", "n_images") if k in report},
                )
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
