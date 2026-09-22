"""Experimental whole-path beam search over native curve evidence.

Unlike column assignment, hypotheses retain their history until future evidence
has been scored. Competing paths are exported, not silently resolved by order.
This backend does not infer invisible ink or require one series per pixel.
"""

from dataclasses import dataclass, replace
import math

import numpy as np

from graphextract.schema import SegmentStatus, SeriesResult, SeriesSample


@dataclass
class _Node:
    cost: float
    y: float | None
    velocity: float
    gap: int
    sample: SeriesSample | None
    parent: object


def _unroll(node):
    samples = []
    while node.sample is not None:
        samples.append(replace(node.sample))
        node = node.parent
    return list(reversed(samples))


def mark_indistinguishable(tracks, colors):
    """A learned shape prior cannot establish identities with identical styles.

    There is currently no dash/anchor identity constraint in this backend. Keep
    geometry, but require review rather than naming indistinguishable ink.
    """
    for sid, result in tracks.items():
        if sid not in colors or not any(
            other != sid and tuple(color) == tuple(colors[sid]) for other, color in colors.items()
        ):
            continue
        for sample in result.samples:
            if sample.status is SegmentStatus.OBSERVED:
                sample.status = SegmentStatus.AMBIGUOUS
        note = "identical series colors require an independent identity constraint"
        if note not in result.review_reasons:
            result.review_reasons.append(note)


def track_temporal(
    gray, layers, series_ids, config, series_colors=None, color_img=None, foreign_avoid=None
):
    from graphextract.tracking import _segment_scores

    height, width = gray.shape[:2]
    outputs = {}
    probabilities = getattr(layers, "curve_probabilities", {})
    for sid in series_ids:
        mask = layers.curve_masks.get(sid, np.zeros_like(gray))
        if mask.shape != gray.shape:
            raise ValueError("curve mask shape differs from image")
        prob = probabilities.get(sid)
        if prob is not None and (
            prob.shape != gray.shape
            or not np.isfinite(prob).all()
            or np.any((prob < 0) | (prob > 1))
        ):
            raise ValueError("curve probabilities must be finite, same shape, and in [0,1]")
        color = (series_colors or {}).get(sid)
        beam = [_Node(0.0, None, 0.0, 0, None, None)]
        for u in range(width):
            rows = np.flatnonzero(mask[:, u])
            groups = np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1) if len(rows) else []
            scores = None
            if color is not None and color_img is not None:
                scores, _ = _segment_scores(
                    color_img[:, u].astype(float),
                    np.asarray(color, float),
                    np.asarray(layers.background_bgr, float)[None],
                )
            candidates = []
            for group in groups:
                weights = (
                    prob[group, u]
                    if prob is not None
                    else np.maximum(1, 255 - gray[group, u].astype(float))
                )
                y = float(np.average(group, weights=weights + 1e-6))
                unary = (
                    -math.log(max(float(prob[group, u].max()), 1e-6)) if prob is not None else 0.0
                )
                if scores is not None:
                    unary += float(scores[group].min()) / 12.0
                # Tall annotation/grid strokes are weak evidence of a centerline.
                unary += max(0, len(group) - 5) * 0.15
                if foreign_avoid is not None and sid in foreign_avoid:
                    unary += 2.0 * float(np.mean(foreign_avoid[sid][group, u] > 0))
                candidates.append((y, unary, max(0.5, len(group) / 2)))
            candidates = sorted(candidates, key=lambda c: c[1])[:12]
            expanded = []
            for node in beam:
                for y, unary, halfwidth in candidates:
                    step = (y - node.y) / (node.gap + 1) if node.y is not None else 0.0
                    motion = (
                        0.35 * abs(step - node.velocity) + 0.015 * abs(step)
                        if node.y is not None
                        else 0.0
                    )
                    expanded.append(
                        _Node(
                            node.cost + unary + motion,
                            y,
                            step,
                            0,
                            SeriesSample(float(u), y, half_width_px=halfwidth),
                            node,
                        )
                    )
                # No measurement is manufactured across blank or rejected columns.
                gap = node.gap + 1
                expanded.append(
                    _Node(
                        node.cost + 2.5,
                        node.y if gap <= 12 else None,
                        node.velocity if gap <= 12 else 0.0,
                        gap,
                        SeriesSample(float(u), node.y or 0.0, SegmentStatus.MISSING),
                        node,
                    )
                )
            # Preserve spatial and velocity diversity; two histories may converge
            # to the same state and still represent an unresolved earlier branch.
            counts = {}
            beam = []
            for node in sorted(expanded, key=lambda n: n.cost):
                key = (
                    None if node.y is None else round(node.y),
                    round(node.velocity * 2),
                    min(node.gap, 13),
                )
                if counts.get(key, 0) >= 2:
                    continue
                counts[key] = counts.get(key, 0) + 1
                beam.append(node)
                if len(beam) >= config.temporal_beam_width:
                    break
        best = _unroll(beam[0])
        result = SeriesResult(sid, "", sid, "y_left", best)
        for node in beam[1:]:
            if node.cost - beam[0].cost > config.temporal_ambiguity_cost:
                continue
            alt = _unroll(node)
            differs = [
                i
                for i, (a, b) in enumerate(zip(best, alt))
                if (a.status is not b.status or abs(a.v - b.v) > 1.0)
            ]
            if not differs:
                continue
            result.alternatives.append(alt)
            for i in differs:
                if best[i].status is SegmentStatus.OBSERVED:
                    best[i].status = SegmentStatus.AMBIGUOUS
                    best[i].half_width_px = max(best[i].half_width_px, abs(best[i].v - alt[i].v))
            if len(result.alternatives) >= 3:
                break
        if result.alternatives:
            result.review_reasons.append("temporal search retains competing trajectories")
        for i, sample in enumerate(best):
            if (
                sample.status is SegmentStatus.OBSERVED
                and color is not None
                and color_img is not None
            ):
                r = int(np.clip(round(sample.v), 0, height - 1))
                score, _ = _segment_scores(
                    color_img[r : r + 1, i].astype(float),
                    np.asarray(color, float),
                    np.asarray(layers.background_bgr, float)[None],
                )
                if score[0] <= 15:
                    result.confirmed.add(i)
        outputs[sid] = result
    mark_indistinguishable(outputs, series_colors or {})
    return outputs
