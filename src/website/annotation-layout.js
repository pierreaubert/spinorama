// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
//
// Collision-aware browser-side placement for Plotly annotations.

const LANE_FRACTIONS = {
    top: 0.12,
    upper: 0.28,
    middle: 0.5,
    lower: 0.7,
    bottom: 0.86,
};

const ANNOTATION_PRIORITIES = {
    'On Axis': 100,
    'Listening Window': 95,
    'Early Reflections': 80,
    'Sound Power': 75,
    'Early Reflections DI': 70,
    'Sound Power DI': 65,
};

const ANNOTATION_LANES = {
    'On Axis': ['lower', 'bottom', 'middle'],
    'Listening Window': ['lower', 'bottom', 'middle'],
    'Early Reflections': ['middle', 'upper', 'lower'],
    'Sound Power': ['upper', 'middle', 'lower'],
    'Early Reflections DI': ['lower', 'bottom', 'middle'],
    'Sound Power DI': ['bottom', 'lower', 'middle'],
};

function finite(value) {
    return typeof value === 'number' && Number.isFinite(value);
}

function rangeFor(layout, axis) {
    const range = layout[axis]?.range;
    if (Array.isArray(range) && range.length >= 2 && finite(Number(range[0])) && finite(Number(range[1]))) {
        return [Number(range[0]), Number(range[1])];
    }
    return axis === 'xaxis' ? [1.3, 4.3] : [-45, 5];
}

function valueToPixel(value, range, start, end) {
    if (range[1] === range[0]) return (start + end) / 2;
    const fraction = (value - range[0]) / (range[1] - range[0]);
    return start + fraction * (end - start);
}

function rectFromCenter(center, size) {
    return [center[0] - size[0] / 2, center[1] - size[1] / 2, center[0] + size[0] / 2, center[1] + size[1] / 2];
}

function rectOverlap(first, second) {
    const left = Math.max(first[0], second[0]);
    const top = Math.max(first[1], second[1]);
    const right = Math.min(first[2], second[2]);
    const bottom = Math.min(first[3], second[3]);
    if (right <= left || bottom <= top) return 0;
    return (right - left) * (bottom - top);
}

function annotationKey(annotation) {
    if (typeof annotation.name === 'string') {
        if (annotation.name.startsWith('layout-hidden:')) return annotation.name.slice('layout-hidden:'.length);
        if (annotation.name.startsWith('spinorama:')) return annotation.name.slice('spinorama:'.length);
    }
    return '';
}

function estimateSize(annotation, layout) {
    const fontSize = Number(annotation.font?.size || layout.font?.size || 10);
    const text = String(annotation.text || '');
    const lines = text.split('<br>');
    const longest = Math.max(1, ...lines.map((line) => line.length));
    const pad = 5;
    return [longest * fontSize * 0.62 + 2 * pad + 2, lines.length * fontSize * 1.35 + 2 * pad + 2];
}

function annotationAnchor(annotation, geometry) {
    if (annotation.xref && annotation.xref !== 'x') return null;
    const yref = annotation.yref || 'y';
    if (yref !== 'y' && yref !== 'y2') return null;
    if (!finite(Number(annotation.x)) || !finite(Number(annotation.y))) return null;

    let x = Number(annotation.x);
    if (geometry.xLog && x > geometry.xRange[1] + 0.5 && x > 0) x = Math.log10(x);
    const xPixel = valueToPixel(x, geometry.xRange, geometry.left, geometry.right);
    const yPixel = valueToPixel(Number(annotation.y), geometry.yRanges[yref], geometry.bottom, geometry.top);
    return { point: [xPixel, yPixel], yref };
}

function tracePoints(options, geometry) {
    const points = { y: [], y2: [] };
    for (const trace of options.data || []) {
        if (trace.visible === false || trace.visible === 'legendonly' || !Array.isArray(trace.x) || !Array.isArray(trace.y)) {
            continue;
        }
        const yref = trace.yaxis === 'y2' ? 'y2' : 'y';
        const limit = Math.min(trace.x.length, trace.y.length);
        for (let index = 0; index < limit; index++) {
            const rawX = Number(trace.x[index]);
            const y = Number(trace.y[index]);
            if (!finite(rawX) || !finite(y) || (geometry.xLog && rawX <= 0)) continue;
            const x = geometry.xLog ? Math.log10(rawX) : rawX;
            const xPixel = valueToPixel(x, geometry.xRange, geometry.left, geometry.right);
            const yPixel = valueToPixel(y, geometry.yRanges[yref], geometry.bottom, geometry.top);
            if (xPixel >= geometry.left && xPixel <= geometry.right && yPixel >= geometry.top && yPixel <= geometry.bottom) {
                points[yref].push([xPixel, yPixel]);
            }
        }
    }
    return points;
}

function reservedRects(layout, geometry) {
    const reserved = [[geometry.left, geometry.top, geometry.right, geometry.top + 28]];
    if (layout.showlegend === false || !layout.legend) return reserved;

    const legend = layout.legend;
    const x = Number(legend.x);
    const y = Number(legend.y);
    if (!finite(x) || !finite(y)) return reserved;
    if (y >= 0.94) reserved.push([geometry.left, geometry.top, geometry.right, geometry.top + 48]);
    if (y <= 0.06) reserved.push([geometry.left, geometry.bottom - 48, geometry.right, geometry.bottom]);
    if (x >= 0.94) reserved.push([geometry.right - 130, geometry.top, geometry.right, geometry.bottom]);
    if (x <= 0.06) reserved.push([geometry.left, geometry.top, geometry.left + 130, geometry.bottom]);
    return reserved;
}

function candidateCenters(annotation, key, anchor, size, geometry) {
    const laneNames = [...(ANNOTATION_LANES[key] || ['middle', 'lower', 'upper'])];
    for (const lane of Object.keys(LANE_FRACTIONS)) {
        if (!laneNames.includes(lane)) laneNames.push(lane);
    }

    const xMin = geometry.left + size[0] / 2 + 5;
    const xMax = geometry.right - size[0] / 2 - 5;
    const yMin = geometry.top + size[1] / 2 + 5;
    const yMax = geometry.bottom - size[1] / 2 - 5;
    if (xMin > xMax || yMin > yMax) return [];

    const candidates = [];
    const seen = new Set();
    const add = (center, laneRank) => {
        const clamped = [Math.min(xMax, Math.max(xMin, center[0])), Math.min(yMax, Math.max(yMin, center[1]))];
        const identity = `${Math.round(clamped[0])}:${Math.round(clamped[1])}`;
        if (!seen.has(identity)) {
            seen.add(identity);
            candidates.push({ center: clamped, laneRank });
        }
    };

    laneNames.forEach((lane, laneRank) => {
        const y = geometry.top + LANE_FRACTIONS[lane] * (geometry.bottom - geometry.top);
        [0, -100, 100, -190, 190].forEach((dx) => add([anchor[0] + dx, y], laneRank));
    });
    [
        [0, -70],
        [0, 70],
        [-100, -55],
        [100, -55],
        [-100, 55],
        [100, 55],
        [0, -125],
        [0, 125],
    ].forEach(([dx, dy], index) => add([anchor[0] + dx, anchor[1] + dy], laneNames.length + index));
    return candidates;
}

function metadata(annotation, index) {
    const key = annotationKey(annotation);
    const speaker = Number.isInteger(annotation._speakerIndex) ? annotation._speakerIndex : 0;
    return {
        key,
        speaker,
        priority: ANNOTATION_PRIORITIES[key] || Math.max(1, 50 - index),
    };
}

/**
 * Recompute visible annotation positions after layout/config/resize changes.
 * The solver operates on one Plotly layout, so compare graphs naturally share
 * one collision set while hidden speaker A/B labels do not consume space.
 */
export function layoutAnnotations(options) {
    const layout = options?.layout;
    const annotations = layout?.annotations;
    if (!layout || !Array.isArray(annotations) || annotations.length === 0) return options;

    const width = Number(layout.width || 1200);
    const height = Number(layout.height || 800);
    const margin = layout.margin || {};
    const geometry = {
        left: Number(margin.l || 0),
        right: width - Number(margin.r || 0),
        top: Number(margin.t || 0),
        bottom: height - Number(margin.b || 0),
        xRange: rangeFor(layout, 'xaxis'),
        yRanges: { y: rangeFor(layout, 'yaxis'), y2: rangeFor(layout, 'yaxis2') },
        xLog: layout.xaxis?.type === 'log',
    };
    if (geometry.right <= geometry.left || geometry.bottom <= geometry.top) return options;

    const curves = tracePoints(options, geometry);
    const reserved = reservedRects(layout, geometry);
    const occupied = [];
    const candidates = [];

    annotations.forEach((annotation, index) => {
        if (annotation.visible === false || annotation.visible === 'legendonly') return;
        const anchor = annotationAnchor(annotation, geometry);
        if (!anchor) return;
        const info = metadata(annotation, index);
        candidates.push({
            annotation,
            index,
            anchor: anchor.point,
            yref: anchor.yref,
            info,
            size: estimateSize(annotation, layout),
        });
    });
    candidates.sort((first, second) => {
        if (second.info.priority !== first.info.priority) return second.info.priority - first.info.priority;
        if (first.info.speaker !== second.info.speaker) return first.info.speaker - second.info.speaker;
        return first.index - second.index;
    });

    for (const item of candidates) {
        let best = null;
        for (const candidate of candidateCenters(item.annotation, item.info.key, item.anchor, item.size, geometry)) {
            const rect = rectFromCenter(candidate.center, item.size);
            if (occupied.some((other) => rectOverlap(rect, other) > 0)) continue;
            if (reserved.some((other) => rectOverlap(rect, other) > 0)) continue;

            let curvePenalty = 0;
            for (const point of curves[item.yref]) {
                if (rectOverlap(rect, rectFromCenter(point, [5, 5])) > 0) curvePenalty += 4;
            }
            const distance = Math.hypot(candidate.center[0] - item.anchor[0], candidate.center[1] - item.anchor[1]);
            const score = candidate.laneRank * 15 + distance * 0.025 + curvePenalty;
            if (!best || score < best.score) best = { score, center: candidate.center, rect };
        }

        if (!best) {
            item.annotation.visible = false;
            continue;
        }
        occupied.push(best.rect);
        item.annotation.bgcolor = item.annotation.bgcolor || 'rgba(255, 255, 255, 0.86)';
        item.annotation.borderpad = item.annotation.borderpad ?? 3;
        item.annotation.borderwidth = item.annotation.borderwidth ?? 1;
        item.annotation.xanchor = 'center';
        item.annotation.yanchor = 'middle';
        item.annotation.axref = 'pixel';
        item.annotation.ayref = 'pixel';
        item.annotation.ax = Math.round(best.center[0] - item.anchor[0]);
        item.annotation.ay = Math.round(best.center[1] - item.anchor[1]);
    }
    return options;
}
