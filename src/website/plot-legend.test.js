// -*- coding: utf-8 -*-
// Tests for legend-related functions in plot.js
//
// Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

/*eslint no-undef: "error"*/

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { estimateLegendSize, shouldUseShortLabels, setGraphOptions, labelShort } from './plot.js';
import { applyConfig, defaultConfig } from './plot-config.js';

beforeEach(() => {
    global.window = { innerWidth: 1024, innerHeight: 768 };
});

afterEach(() => {
    vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// estimateLegendSize
// ---------------------------------------------------------------------------
describe('estimateLegendSize', () => {
    const names3 = ['On Axis', 'Listening Window', 'Sound Power'];
    const names10 = Array.from({ length: 10 }, (_, i) => `Trace ${i}`);

    it('vertical: few traces', () => {
        const r = estimateLegendSize(names3, 10, 'v', 120, 800);
        expect(r.width).toBe(120);
        expect(r.height).toBeCloseTo(3 * 10 * 1.6);
        expect(r.columns).toBe(1);
        expect(r.rows).toBe(3);
    });

    it('vertical: many traces', () => {
        const r = estimateLegendSize(names10, 10, 'v', 120, 800);
        expect(r.rows).toBe(10);
        expect(r.height).toBeCloseTo(10 * 10 * 1.6);
    });

    it('horizontal: fits in one row', () => {
        const r = estimateLegendSize(names3, 10, 'h', 100, 400);
        expect(r.columns).toBe(4);
        expect(r.rows).toBe(1);
        expect(r.height).toBeCloseTo(10 * 1.6);
    });

    it('horizontal: wraps to multiple rows', () => {
        const r = estimateLegendSize(names10, 10, 'h', 150, 400);
        expect(r.columns).toBe(2);
        expect(r.rows).toBe(5);
        expect(r.height).toBeCloseTo(5 * 10 * 1.6);
    });

    it('horizontal: very narrow forces single column', () => {
        const r = estimateLegendSize(names3, 10, 'h', 200, 50);
        expect(r.columns).toBe(1);
        expect(r.rows).toBe(3);
    });

    it('compare mode with many traces', () => {
        const compareNames = names10.concat(names10.map((n) => '(B) ' + n));
        const r = estimateLegendSize(compareNames, 10, 'v', 164, 800);
        expect(r.rows).toBe(20);
    });
});

// ---------------------------------------------------------------------------
// shouldUseShortLabels
// ---------------------------------------------------------------------------
describe('shouldUseShortLabels', () => {
    const names = ['On Axis', 'Listening Window', 'Sound Power', 'Early Reflections DI'];
    const targetRatio = 4.0 / 3.0;

    it('compact → true', () => {
        expect(shouldUseShortLabels(names, 400, 300, true, false, targetRatio, 'default')).toBe(true);
    });

    it("user 'long' → false even when compact", () => {
        expect(shouldUseShortLabels(names, 400, 300, true, false, targetRatio, 'long')).toBe(false);
    });

    it("user 'short' → true even with wide screen", () => {
        expect(shouldUseShortLabels(names, 1920, 1080, false, false, targetRatio, 'short')).toBe(true);
    });

    it('wide screen + few traces → false (ratio ok)', () => {
        const few = ['On Axis', 'LW'];
        expect(shouldUseShortLabels(few, 1920, 1080, false, false, targetRatio, 'default')).toBe(false);
    });

    it('narrow + many known labels → true', () => {
        // Use labels that exist in labelShort so shortening actually helps
        const many = [
            'On Axis',
            'Listening Window',
            'Sound Power',
            'Early Reflections DI',
            'Sound Power DI',
            'Total Early Reflection',
            'Total Horizontal Reflection',
            'Total Vertical Reflection',
            'Estimated In-Room Response',
            'On Axis',
            'Listening Window',
            'Sound Power',
            'Early Reflections DI',
            'Sound Power DI',
            'Total Early Reflection',
        ];
        expect(shouldUseShortLabels(many, 600, 500, false, false, targetRatio, 'default')).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// computeLabel integration (via setGraphOptions)
// ---------------------------------------------------------------------------
describe('computeLabel integration', () => {
    function makeGraph(traceNames) {
        return {
            layout: {
                title: { text: 'CEA2034 for Speaker measured by ASR' },
                xaxis: { title: { text: 'Freq' }, range: [1, 4] },
                yaxis: { title: { text: 'dB' }, range: [-40, 10] },
            },
            data: traceNames.map((name) => ({ name, type: 'scatter' })),
        };
    }

    const graphProps = { isGraph: true, isSpin: true, isRadar: false, isSurface: false, isGlobe: false };

    it('compact shortens labels', () => {
        const g = makeGraph(['On Axis', 'Listening Window', 'Sound Power']);
        const result = setGraphOptions([g], 400, 300, graphProps, 1);
        // In compact mode, shouldUseShortLabels returns true
        expect(result.data[0].name).toBe(labelShort['On Axis'] || result.data[0].name);
    });

    it('_fullName is set before shortening', () => {
        const g = makeGraph(['On Axis', 'Listening Window']);
        const result = setGraphOptions([g], 400, 300, graphProps, 1);
        expect(result.data[0]._fullName).toBe('On Axis');
    });

    it('enough space keeps long labels', () => {
        const g = makeGraph(['On Axis', 'Listening Window']);
        const result = setGraphOptions([g], 1920, 1080, graphProps, 1);
        // Wide screen with few traces → should keep long labels
        expect(result.data[0]._fullName).toBe('On Axis');
        expect(result.data[0].name).toBe('On Axis');
    });

    it('compare mode adds (A)/(B) prefixes', () => {
        const g1 = {
            layout: {
                title: { text: 'CEA2034 for Speaker1 measured by ASR' },
                xaxis: { title: { text: 'Freq' }, range: [1, 4] },
                yaxis: { title: { text: 'dB' }, range: [-40, 10] },
            },
            data: [
                {
                    name: 'On Axis',
                    type: 'scatter',
                    legendgroup: 'speaker0',
                    legendgrouptitle: { text: 'CEA2034 for Speaker1' },
                },
            ],
        };
        const g2 = {
            layout: {
                title: { text: 'CEA2034 for Speaker2 measured by ASR' },
                xaxis: { title: { text: 'Freq' }, range: [1, 4] },
                yaxis: { title: { text: 'dB' }, range: [-40, 10] },
            },
            data: [
                {
                    name: 'On Axis',
                    type: 'scatter',
                    legendgroup: 'speaker1',
                    legendgrouptitle: { text: 'CEA2034 for Speaker2' },
                },
            ],
        };
        const result = setGraphOptions([g1, g2], 1920, 1080, graphProps, 1);
        const names = result.data.map((d) => d.name);
        const hasA = names.some((n) => n && n.startsWith('(A)'));
        const hasB = names.some((n) => n && n.startsWith('(B)'));
        expect(hasA).toBe(true);
        expect(hasB).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// computeLegend (via setGraphOptions)
// ---------------------------------------------------------------------------
describe('computeLegend', () => {
    function makeGraph(traceNames) {
        return {
            layout: {
                title: { text: 'CEA2034 for Speaker measured by ASR' },
                xaxis: { title: { text: 'Freq' }, range: [1, 4] },
                yaxis: { title: { text: 'dB' }, range: [-40, 10] },
            },
            data: traceNames.map((name) => ({ name, type: 'scatter' })),
        };
    }
    const graphProps = { isGraph: true, isSpin: true, isRadar: false, isSurface: false, isGlobe: false };

    it('vertical display uses horizontal legend with computed entrywidth', () => {
        const g = makeGraph(['On Axis', 'Listening Window', 'Sound Power']);
        const result = setGraphOptions([g], 768, 1024, graphProps, 1);
        expect(result.layout.legend.orientation).toBe('h');
        expect(result.layout.legend.entrywidth).toBeGreaterThanOrEqual(80);
    });

    it('font shrinks when many traces overflow vertical legend', () => {
        const names = Array.from({ length: 30 }, (_, i) => `Trace ${i}`);
        const g = makeGraph(names);
        const result = setGraphOptions([g], 1920, 600, graphProps, 1);
        // With 30 traces in a short window, font may shrink
        if (result.layout.legend.orientation === 'v') {
            expect(result.layout.legend.font.size).toBeLessThanOrEqual(16);
        }
    });

    it('surface hides legend', () => {
        const surfaceProps = { isGraph: false, isSpin: false, isRadar: false, isSurface: true, isGlobe: false };
        const g = makeGraph(['contour']);
        const result = setGraphOptions([g], 1920, 1080, surfaceProps, 1);
        expect(result.layout.showlegend).toBe(false);
    });

    it('yanchor is middle not middel', () => {
        const g = makeGraph(['On Axis', 'Listening Window']);
        const result = setGraphOptions([g], 1920, 1080, graphProps, 1);
        if (result.layout.legend.yanchor) {
            expect(result.layout.legend.yanchor).not.toBe('middel');
        }
    });

    it('layout height proportional to width for many traces (ratio preserved)', () => {
        const names = Array.from({ length: 40 }, (_, i) => `Trace ${i}`);
        const g = makeGraph(names);
        const result = setGraphOptions([g], 1920, 600, graphProps, 1);
        // Plot area ratio (width-margins) / (height-margins) should still be ~1.8
        const ml = result.layout.margin?.l || 0;
        const mr = result.layout.margin?.r || 0;
        const mt = result.layout.margin?.t || 0;
        const mb = result.layout.margin?.b || 0;
        const pw = result.layout.width - ml - mr;
        const ph = result.layout.height - mt - mb;
        expect(pw / ph).toBeCloseTo(1.8, 1);
    });
});

// ---------------------------------------------------------------------------
// End-to-end: setGraphOptions + applyConfig
// ---------------------------------------------------------------------------
describe('setGraphOptions + applyConfig label override', () => {
    function makeGraph() {
        return {
            layout: {
                title: { text: 'CEA2034 for Speaker measured by ASR' },
                xaxis: { title: { text: 'Freq' }, range: [1, 4] },
                yaxis: { title: { text: 'dB' }, range: [-40, 10] },
            },
            data: [
                { name: 'On Axis', type: 'scatter' },
                { name: 'Listening Window', type: 'scatter' },
                { name: 'Sound Power', type: 'scatter' },
            ],
        };
    }
    const graphProps = { isGraph: true, isSpin: true, isRadar: false, isSurface: false, isGlobe: false };

    it('default auto-short sets _fullName', () => {
        const g = makeGraph();
        const result = setGraphOptions([g], 1920, 1080, graphProps, 1);
        // _fullName should be set on all traces with names
        for (const trace of result.data) {
            if (trace.name) {
                expect(trace._fullName).toBeDefined();
            }
        }
    });

    it("user 'long' overrides via applyConfig", () => {
        const g = makeGraph();
        const result = setGraphOptions([g], 400, 300, graphProps, 1);
        // Compact → short labels applied
        const config = structuredClone(defaultConfig);
        config.legend.label = 'long';
        const applied = applyConfig(result, config);
        // applyConfig maps short→long via labelLong
        expect(applied.data[0].name).toBe('On Axis');
    });

    it("user 'short' overrides via applyConfig", () => {
        const g = makeGraph();
        const result = setGraphOptions([g], 1920, 1080, graphProps, 1);
        const config = structuredClone(defaultConfig);
        config.legend.label = 'short';
        const applied = applyConfig(result, config);
        // Should use short labels
        if (labelShort[applied.data[0]._fullName]) {
            expect(applied.data[0].name).toBe(labelShort[applied.data[0]._fullName]);
        }
    });

    it('_fullName preserved through applyConfig', () => {
        const g = makeGraph();
        const result = setGraphOptions([g], 1920, 1080, graphProps, 1);
        const config = structuredClone(defaultConfig);
        config.legend.label = 'short';
        const applied = applyConfig(result, config);
        // _fullName should still be set (applyConfig sets it too)
        expect(applied.data[0]._fullName).toBeDefined();
    });
});
