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

describe('layoutAnnotations', () => {
    it('moves visible annotations into distinct readable positions', () => {
        const options = makeOptions();
        layoutAnnotations(options);

        const [first, second] = options.layout.annotations;
        expect(first.visible).toBe(true);
        expect(second.visible).toBe(true);
        expect(first.ay).toBeGreaterThan(0);
        expect(first.ax !== second.ax || first.ay !== second.ay).toBe(true);
        expect(first.axref).toBe('pixel');
        expect(first.ayref).toBe('pixel');
        expect(first.bgcolor).toBe('rgba(255, 255, 255, 0.86)');
        expect(first.borderwidth).toBe(1);
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
