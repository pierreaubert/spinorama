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
    'On Axis': ['top', 'upper', 'middle'],
    'Listening Window': ['top', 'upper', 'middle'],
    'Early Reflections': ['middle', 'upper', 'lower'],
    'Sound Power': ['upper', 'middle', 'lower'],
    'Early Reflections DI': ['upper', 'top', 'middle', 'lower', 'bottom'],
    'Sound Power DI': ['upper', 'top', 'middle', 'lower', 'bottom'],
};

const ANNOTATION_DIRECTIONS = {
    'On Axis': 'above',
    'Listening Window': 'above',
    'Early Reflections DI': 'above',
    'Sound Power DI': 'above',
};

const TRACE_CLEARANCE = 14;
const MIN_LEADER_LENGTH = 48;

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

function expandRect(rect, padding) {
    return [rect[0] - padding, rect[1] - padding, rect[2] + padding, rect[3] + padding];
}

function pointsEqual(first, second) {
    return Math.abs(first[0] - second[0]) < 0.001 && Math.abs(first[1] - second[1]) < 0.001;
}

function cross(first, second, third) {
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0]);
}

function between(value, first, second) {
    return value >= Math.min(first, second) - 0.001 && value <= Math.max(first, second) + 0.001;
}

function segmentsIntersect(firstStart, firstEnd, secondStart, secondEnd) {
    // Arrows sharing an anchor are allowed to fan out independently.
    if (
        pointsEqual(firstStart, secondStart) ||
        pointsEqual(firstStart, secondEnd) ||
        pointsEqual(firstEnd, secondStart) ||
        pointsEqual(firstEnd, secondEnd)
    ) {
        return false;
    }

    const firstCross = cross(firstStart, firstEnd, secondStart);
    const secondCross = cross(firstStart, firstEnd, secondEnd);
    const thirdCross = cross(secondStart, secondEnd, firstStart);
    const fourthCross = cross(secondStart, secondEnd, firstEnd);
    const firstProper = (firstCross > 0 && secondCross < 0) || (firstCross < 0 && secondCross > 0);
    const secondProper = (thirdCross > 0 && fourthCross < 0) || (thirdCross < 0 && fourthCross > 0);
    if (firstProper && secondProper) return true;

    return (
        (Math.abs(firstCross) < 0.001 &&
            between(secondStart[0], firstStart[0], firstEnd[0]) &&
            between(secondStart[1], firstStart[1], firstEnd[1])) ||
        (Math.abs(secondCross) < 0.001 &&
            between(secondEnd[0], firstStart[0], firstEnd[0]) &&
            between(secondEnd[1], firstStart[1], firstEnd[1])) ||
        (Math.abs(thirdCross) < 0.001 &&
            between(firstStart[0], secondStart[0], secondEnd[0]) &&
            between(firstStart[1], secondStart[1], secondEnd[1])) ||
        (Math.abs(fourthCross) < 0.001 &&
            between(firstEnd[0], secondStart[0], secondEnd[0]) &&
            between(firstEnd[1], secondStart[1], secondEnd[1]))
    );
}

function pointInRect(point, rect) {
    return point[0] > rect[0] && point[0] < rect[2] && point[1] > rect[1] && point[1] < rect[3];
}

function segmentCrossesRect(start, end, rect) {
    // An arrow that starts inside a label is already attached to that label's
    // curve; do not make the fallback solver hide every candidate in that case.
    if (pointInRect(start, rect)) return false;
    if (pointInRect(end, rect)) return true;
    const edges = [
        [
            [rect[0], rect[1]],
            [rect[2], rect[1]],
        ],
        [
            [rect[2], rect[1]],
            [rect[2], rect[3]],
        ],
        [
            [rect[2], rect[3]],
            [rect[0], rect[3]],
        ],
        [
            [rect[0], rect[3]],
            [rect[0], rect[1]],
        ],
    ];
    return edges.some(([edgeStart, edgeEnd]) => segmentsIntersect(start, end, edgeStart, edgeEnd));
}

function annotationKey(annotation) {
    if (typeof annotation.name === 'string') {
        if (annotation.name.startsWith('layout-hidden:')) return annotation.name.slice('layout-hidden:'.length);
        if (annotation.name.startsWith('spinorama:')) return annotation.name.slice('spinorama:'.length);
    }
    return '';
}

function isStaticAnnotation(annotation) {
    return typeof annotation.name === 'string' && annotation.name.startsWith('static:');
}

const MAX_DYNAMIC_LEADER_LENGTH = 260;
const MIN_HORIZONTAL_LEADER_OFFSET = 24;

export function prepareAnnotationLayout(options) {
    const annotations = options?.layout?.annotations;
    if (!Array.isArray(annotations)) return options;
    for (const annotation of annotations) {
        if (typeof annotation.name !== 'string') continue;
        if (annotation.name.startsWith('layout-hidden:')) {
            annotation.name = `spinorama:${annotation.name.slice('layout-hidden:'.length)}`;
            annotation.visible = true;
        } else if (annotation.name.startsWith('static:')) {
            annotation.name = `spinorama:${annotation.name.slice('static:'.length)}`;
            annotation.visible = true;
        }
    }
    return options;
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
    const points = { y: [], y2: [], all: [], segments: { y: [], y2: [], all: [] } };
    for (const trace of options.data || []) {
        if (trace.visible === false || trace.visible === 'legendonly' || !Array.isArray(trace.x) || !Array.isArray(trace.y)) {
            continue;
        }
        const yref = trace.yaxis === 'y2' ? 'y2' : 'y';
        const limit = Math.min(trace.x.length, trace.y.length);
        let previous = null;
        for (let index = 0; index < limit; index++) {
            const rawX = Number(trace.x[index]);
            const y = Number(trace.y[index]);
            if (!finite(rawX) || !finite(y) || (geometry.xLog && rawX <= 0)) {
                previous = null;
                continue;
            }
            const x = geometry.xLog ? Math.log10(rawX) : rawX;
            const xPixel = valueToPixel(x, geometry.xRange, geometry.left, geometry.right);
            const yPixel = valueToPixel(y, geometry.yRanges[yref], geometry.bottom, geometry.top);
            if (xPixel >= geometry.left && xPixel <= geometry.right && yPixel >= geometry.top && yPixel <= geometry.bottom) {
                const point = [xPixel, yPixel];
                points[yref].push(point);
                points.all.push(point);
                if (previous) {
                    const segment = [previous, point];
                    points.segments[yref].push(segment);
                    points.segments.all.push(segment);
                }
                previous = point;
            } else {
                previous = null;
            }
        }
    }
    return points;
}

function reservedRects(layout, geometry) {
    // The title lives in Plotly's top margin, outside the plot rectangle. Do
    // not reserve the first plot pixels: that space is often the only place
    // where a label can sit above a high SPL curve.
    const reserved = [];
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

    // Try short, local offsets before the full semantic lanes. A directional
    // constraint in layoutAnnotations decides whether an above/below offset
    // is valid, while the distance term keeps arrows compact whenever space
    // permits it.
    const verticalOffset = Math.max(24, size[1] / 2 + TRACE_CLEARANCE + 6);
    const localOffsets = [
        [0, -verticalOffset],
        [0, verticalOffset],
        [-48, -verticalOffset],
        [48, -verticalOffset],
        [-48, verticalOffset],
        [48, verticalOffset],
        [0, -2 * verticalOffset],
        [0, 2 * verticalOffset],
        [-96, -2 * verticalOffset],
        [96, -2 * verticalOffset],
        [-96, 2 * verticalOffset],
        [96, 2 * verticalOffset],
        [-144, -2 * verticalOffset],
        [144, -2 * verticalOffset],
        [-192, -2 * verticalOffset],
        [192, -2 * verticalOffset],
    ];
    localOffsets.forEach(([dx, dy], index) => add([anchor[0] + dx, anchor[1] + dy], laneNames.length + index));

    laneNames.forEach((lane, laneRank) => {
        const y = geometry.top + LANE_FRACTIONS[lane] * (geometry.bottom - geometry.top);
        [0, -100, 100, -190, 190, -280, 280, -360, 360].forEach((dx) => add([anchor[0] + dx, y], laneRank));
    });
    return candidates;
}

function directionPenalty(direction, anchor, center) {
    if (direction === 'above') return center[1] >= anchor[1] ? 1000 + center[1] - anchor[1] : 0;
    if (direction === 'below') return center[1] <= anchor[1] ? 1000 + anchor[1] - center[1] : 0;
    return 0;
}

function curvePenalty(rect, points, segments) {
    let penalty = 0;
    const clearanceRect = expandRect(rect, TRACE_CLEARANCE);
    for (const point of points) {
        const pointRect = rectFromCenter(point, [5, 5]);
        if (rectOverlap(rect, pointRect) > 0) return Infinity;
        if (rectOverlap(clearanceRect, pointRect) > 0) penalty += 20;
    }
    for (const [start, end] of segments) {
        if (segmentCrossesRect(start, end, rect)) return Infinity;
        if (segmentCrossesRect(start, end, clearanceRect)) penalty += 20;
    }
    return penalty;
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
function layoutAnnotationsFallback(options) {
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
    const arrows = [];
    const candidates = [];

    annotations.forEach((annotation, index) => {
        if (annotation.visible === false || annotation.visible === 'legendonly') return;
        if (isStaticAnnotation(annotation)) return;
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
        const firstDirection = ANNOTATION_DIRECTIONS[first.info.key];
        const secondDirection = ANNOTATION_DIRECTIONS[second.info.key];
        // Labels that share the upper lane are laid out from right to left.
        // This leaves the open space on the left available for the other
        // high-priority curve instead of forcing it below the curves.
        if (firstDirection === 'above' && secondDirection === 'above' && first.info.speaker === second.info.speaker) {
            return second.anchor[0] - first.anchor[0];
        }
        if (second.info.priority !== first.info.priority) return second.info.priority - first.info.priority;
        if (first.info.speaker !== second.info.speaker) return first.info.speaker - second.info.speaker;
        return first.index - second.index;
    });

    for (const item of candidates) {
        let best = null;
        for (const candidate of candidateCenters(item.annotation, item.info.key, item.anchor, item.size, geometry)) {
            const rect = rectFromCenter(candidate.center, item.size);
            if (Math.hypot(candidate.center[0] - item.anchor[0], candidate.center[1] - item.anchor[1]) <= MIN_LEADER_LENGTH) {
                continue;
            }
            if (Math.abs(candidate.center[0] - item.anchor[0]) < MIN_HORIZONTAL_LEADER_OFFSET) continue;
            const direction = ANNOTATION_DIRECTIONS[item.info.key];
            if (directionPenalty(direction, item.anchor, candidate.center) > 0) continue;
            if (occupied.some((other) => rectOverlap(rect, other) > 0)) continue;
            if (reserved.some((other) => rectOverlap(rect, other) > 0)) continue;
            if (arrows.some((arrow) => segmentsIntersect(item.anchor, candidate.center, arrow.start, arrow.end))) continue;
            if (occupied.some((other) => segmentCrossesRect(item.anchor, candidate.center, other))) continue;
            if (arrows.some((arrow) => segmentCrossesRect(arrow.start, arrow.end, rect))) continue;

            const crossAxis = item.yref === 'y2';
            const curveScore = curvePenalty(
                rect,
                crossAxis ? curves.all : curves[item.yref],
                crossAxis ? curves.segments.all : curves.segments[item.yref]
            );
            if (!Number.isFinite(curveScore)) continue;
            const distance = Math.hypot(candidate.center[0] - item.anchor[0], candidate.center[1] - item.anchor[1]);
            const score = distance + candidate.laneRank * 2 + curveScore;
            if (!best || score < best.score) best = { score, center: candidate.center, rect };
        }

        if (!best) {
            item.annotation.visible = false;
            continue;
        }
        occupied.push(best.rect);
        arrows.push({ start: item.anchor, end: best.center });
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

let wasmSolver = null;
let wasmLoad = null;

function loadWasmSolver() {
    if (wasmSolver || wasmLoad) return wasmLoad;
    if (typeof window === 'undefined' || !/^https?:$/.test(window.location?.protocol || '')) {
        return Promise.resolve(null);
    }
    const wasmUrl = '/js/annotations-rust/annotations_rust.js';
    wasmLoad = import(/* @vite-ignore */ wasmUrl)
        .then(async (module) => {
            await module.default();
            wasmSolver = module;
            return module;
        })
        .catch((error) => {
            // Keep the synchronous JavaScript solver as an offline/build fallback.
            console.warn('Rust annotation solver unavailable; using JavaScript fallback.', error);
            return null;
        });
    return wasmLoad;
}

function rustX(value, geometry) {
    return geometry.xLog && value <= geometry.xRange[1] + 0.5 ? 10 ** value : value;
}

function wasmInput(options, layout, geometry, reserved) {
    const rawRequests = [];
    const outputAnnotations = [];
    (layout.annotations || []).forEach((annotation, index) => {
        if (annotation.visible === false || annotation.visible === 'legendonly') return;
        if (isStaticAnnotation(annotation)) return;
        const anchor = annotationAnchor(annotation, geometry);
        if (!anchor) return;
        const info = metadata(annotation, index);
        rawRequests.push([
            info.key,
            rustX(Number(annotation.x), geometry),
            Number(annotation.y),
            anchor.yref,
            String(annotation.text || ''),
            info.priority,
            ANNOTATION_LANES[info.key] || Object.keys(LANE_FRACTIONS),
            ANNOTATION_DIRECTIONS[info.key] || null,
        ]);
        outputAnnotations.push({ annotation, anchor: anchor.point });
    });

    const tracePoints = [];
    const traceSegments = [];
    for (const trace of options.data || []) {
        if (trace.visible === false || trace.visible === 'legendonly' || !Array.isArray(trace.x) || !Array.isArray(trace.y))
            continue;
        const yref = trace.yaxis === 'y2' ? 'y2' : 'y';
        const key = typeof trace.name === 'string' ? trace.name : null;
        let previous = null;
        for (let index = 0; index < Math.min(trace.x.length, trace.y.length); index++) {
            const x = Number(trace.x[index]);
            const y = Number(trace.y[index]);
            if (!finite(x) || !finite(y) || (geometry.xLog && x <= 0)) {
                previous = null;
                continue;
            }
            const dataX = rustX(x, geometry);
            const point = [
                valueToPixel(geometry.xLog ? Math.log10(dataX) : dataX, geometry.xRange, geometry.left, geometry.right),
                valueToPixel(y, geometry.yRanges[yref], geometry.bottom, geometry.top),
            ];
            if (
                point[0] < geometry.left ||
                point[0] > geometry.right ||
                point[1] < geometry.top ||
                point[1] > geometry.bottom
            ) {
                previous = null;
                continue;
            }
            tracePoints.push([dataX, y, yref]);
            if (previous) traceSegments.push([previous[0], previous[1], point[0], point[1], yref, key]);
            previous = point;
        }
    }

    return {
        raw_requests: rawRequests,
        width: Number(layout.width || 1200),
        height: Number(layout.height || 800),
        margin: [
            Number(layout.margin?.l || 0),
            Number(layout.margin?.r || 0),
            Number(layout.margin?.t || 0),
            Number(layout.margin?.b || 0),
        ],
        x_range: geometry.xRange,
        y_ranges: [
            ['y', ...geometry.yRanges.y],
            ['y2', ...geometry.yRanges.y2],
        ],
        x_scale_log: geometry.xLog,
        font_size: Number(layout.font?.size || 10),
        label_pad: 5,
        x_domain: [0, 1],
        y_domain: [0, 1],
        grid_x: [],
        grid_y: [],
        trace_points: tracePoints,
        reserved,
        trace_segments: traceSegments,
        outputAnnotations,
    };
}

function layoutAnnotationsWasm(options) {
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
    const input = wasmInput(options, layout, geometry, reservedRects(layout, geometry));
    const results = wasmSolver.solve_annotations(input);
    const needsDynamicFallback = results.some(
        ([center, hidden], index) =>
            hidden ||
            !Array.isArray(center) ||
            !input.outputAnnotations[index] ||
            Math.hypot(
                center[0] - input.outputAnnotations[index].anchor[0],
                center[1] - input.outputAnnotations[index].anchor[1]
            ) > MAX_DYNAMIC_LEADER_LENGTH
    );
    if (needsDynamicFallback) return layoutAnnotationsFallback(options);
    for (let index = 0; index < results.length; index++) {
        const [center, hidden] = results[index];
        const item = input.outputAnnotations[index];
        if (!item) continue;
        if (hidden || !Array.isArray(center)) {
            item.annotation.visible = false;
            continue;
        }
        item.annotation.bgcolor = item.annotation.bgcolor || 'rgba(255, 255, 255, 0.86)';
        item.annotation.borderpad = item.annotation.borderpad ?? 3;
        item.annotation.borderwidth = item.annotation.borderwidth ?? 1;
        item.annotation.xanchor = 'center';
        item.annotation.yanchor = 'middle';
        item.annotation.axref = 'pixel';
        item.annotation.ayref = 'pixel';
        item.annotation.ax = Math.round(center[0] - item.anchor[0]);
        item.annotation.ay = Math.round(center[1] - item.anchor[1]);
    }
    return options;
}

// Graph modules wait for the small shared solver before their first Plotly
// render.  This makes the browser use the Rust algorithm on initial load,
// while file/offline deployments retain the synchronous JavaScript fallback.
export const annotationLayoutReady = loadWasmSolver();

export function layoutAnnotations(options) {
    return wasmSolver ? layoutAnnotationsWasm(options) : layoutAnnotationsFallback(options);
}
