import { describe, expect, it } from 'vitest';

import { layoutAnnotations } from './annotation-layout.js';

function makeOptions(width = 900, height = 600) {
    return {
        data: [
            {
                x: [20, 100, 1000, 10000, 20000],
                y: [0, 1, -1, 0, 1],
                type: 'scatter',
            },
            {
                x: [20, 100, 1000, 10000, 20000],
                y: [5, 5, 5, 5, 5],
                yaxis: 'y2',
                type: 'scatter',
            },
        ],
        layout: {
            width,
            height,
            margin: { l: 70, r: 60, t: 80, b: 50 },
            xaxis: { type: 'log', range: [1.3, 4.3] },
            yaxis: { range: [-45, 5] },
            yaxis2: { range: [-5, 45] },
            annotations: [
                {
                    name: 'spinorama:On Axis',
                    x: 3.5,
                    y: 1,
                    yref: 'y',
                    text: '0.26 db/oct sm 0.58',
                    visible: true,
                },
                {
                    name: 'spinorama:Listening Window',
                    x: 3.8,
                    y: 0,
                    yref: 'y',
                    text: '-0.04 db/oct sm 0.44',
                    visible: true,
                },
            ],
        },
    };
}

function annotationAnchor(annotation, options) {
    const { width, height, margin } = options.layout;
    const left = margin.l;
    const right = width - margin.r;
    const top = margin.t;
    const bottom = height - margin.b;
    const x =
        options.layout.xaxis.type === 'log' && annotation.x > options.layout.xaxis.range[1] + 0.5
            ? Math.log10(annotation.x)
            : annotation.x;
    const xPixel =
        left +
        ((x - options.layout.xaxis.range[0]) / (options.layout.xaxis.range[1] - options.layout.xaxis.range[0])) *
            (right - left);
    const yRange = annotation.yref === 'y2' ? options.layout.yaxis2.range : options.layout.yaxis.range;
    const yPixel = bottom + ((annotation.y - yRange[0]) / (yRange[1] - yRange[0])) * (top - bottom);
    return [xPixel, yPixel];
}

function annotationRect(annotation, options) {
    const anchor = annotationAnchor(annotation, options);
    const center = [anchor[0] + (annotation.ax || 0), anchor[1] + (annotation.ay || 0)];
    const width = String(annotation.text).length * 10 * 0.62 + 12;
    const height = 10 * 1.35 + 12;
    return [center[0] - width / 2, center[1] - height / 2, center[0] + width / 2, center[1] + height / 2];
}

function rectanglesOverlap(first, second) {
    return first[0] < second[2] && second[0] < first[2] && first[1] < second[3] && second[1] < first[3];
}

function segmentsCross(firstStart, firstEnd, secondStart, secondEnd) {
    const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    const first = cross(firstStart, firstEnd, secondStart);
    const second = cross(firstStart, firstEnd, secondEnd);
    const third = cross(secondStart, secondEnd, firstStart);
    const fourth = cross(secondStart, secondEnd, firstEnd);
    return ((first > 0 && second < 0) || (first < 0 && second > 0)) && ((third > 0 && fourth < 0) || (third < 0 && fourth > 0));
}

describe('layoutAnnotations', () => {
    it('moves visible annotations into distinct readable positions', () => {
        const options = makeOptions();
        layoutAnnotations(options);

        const [first, second] = options.layout.annotations;
        expect(first.visible).toBe(true);
        expect(second.visible).toBe(true);
        expect(first.ay).toBeLessThan(0);
        expect(second.ay).toBeLessThan(0);
        expect(Math.hypot(first.ax, first.ay)).toBeGreaterThanOrEqual(48);
        expect(Math.hypot(first.ax, first.ay)).toBeLessThan(200);
        expect(first.ax !== second.ax || first.ay !== second.ay).toBe(true);
        expect(first.axref).toBe('pixel');
        expect(first.ayref).toBe('pixel');
        expect(first.bgcolor).toBe('rgba(255, 255, 255, 0.86)');
        expect(first.borderwidth).toBe(1);
        expect(rectanglesOverlap(annotationRect(first, options), annotationRect(second, options))).toBe(false);

        const firstAnchor = annotationAnchor(first, options);
        const secondAnchor = annotationAnchor(second, options);
        const firstCenter = [firstAnchor[0] + first.ax, firstAnchor[1] + first.ay];
        const secondCenter = [secondAnchor[0] + second.ax, secondAnchor[1] + second.ay];
        expect(segmentsCross(firstAnchor, firstCenter, secondAnchor, secondCenter)).toBe(false);
    });

    it('keeps labels clear of nearby trace points', () => {
        const options = makeOptions();
        options.layout.yaxis.range = [-45, 10];
        options.data[0] = {
            x: [10 ** 3.5, 10 ** 3.8],
            y: [0, -1],
            type: 'scatter',
        };
        options.layout.annotations[0].y = 0;
        options.layout.annotations[1].y = -1;
        layoutAnnotations(options);

        for (const annotation of options.layout.annotations) {
            const anchor = annotationAnchor(annotation, options);
            const rect = annotationRect(annotation, options);
            expect(rect[3]).toBeLessThan(anchor[1] - 10);
        }
    });

    it('keeps directivity labels above curves on the primary axis', () => {
        const options = makeOptions(800, 500);
        options.layout.xaxis = { type: 'linear', range: [0, 1] };
        options.layout.yaxis = { range: [0, 1] };
        options.layout.yaxis2 = { range: [0, 1] };
        options.data = [{ x: [0, 1], y: [0.62, 0.62], type: 'scatter' }];
        options.layout.annotations = [
            {
                name: 'spinorama:Sound Power DI',
                x: 0.5,
                y: 0.5,
                yref: 'y2',
                text: 'directivity label',
                visible: true,
            },
        ];

        layoutAnnotations(options);

        const [annotation] = options.layout.annotations;
        expect(annotation.visible).toBe(true);
        // The primary-axis curve is at pixel y=212. The directivity label
        // must use the open space above it rather than covering the curve.
        expect(annotationRect(annotation, options)[3]).toBeLessThan(212);
    });

    it('solves compare annotations together while honoring speaker visibility', () => {
        const options = makeOptions();
        options.layout.annotations = [
            { ...options.layout.annotations[0], _speakerIndex: 0 },
            { ...options.layout.annotations[0], _speakerIndex: 1, text: '0.31 db/oct sm 0.51' },
        ];
        options.layout.annotations[0].visible = false;
        layoutAnnotations(options);

        expect(options.layout.annotations[0].visible).toBe(false);
        expect(options.layout.annotations[1].visible).toBe(true);
        expect(Number.isFinite(options.layout.annotations[1].ay)).toBe(true);
    });

    it('recomputes pixel offsets for a resized layout', () => {
        const large = makeOptions(900, 600);
        const small = makeOptions(500, 400);
        layoutAnnotations(large);
        layoutAnnotations(small);

        expect(large.layout.annotations[0].ay).not.toBe(small.layout.annotations[0].ay);
    });

    it('does not modify non-axis annotations', () => {
        const options = makeOptions();
        const paperAnnotation = { x: 0.5, y: 0.5, xref: 'paper', yref: 'paper', text: 'note', visible: true };
        options.layout.annotations.push(paperAnnotation);
        layoutAnnotations(options);

        expect(paperAnnotation.ax).toBeUndefined();
        expect(paperAnnotation.ay).toBeUndefined();
    });
});
