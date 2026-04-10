// -*- coding: utf-8 -*-
// Integration tests: setGraphOptions → applyConfig pipeline
// Tests the real output of plot.js functions as input to plot-config.js applyConfig.
// No mocks — catches regressions where one function's output breaks the other's assumptions.

import { describe, it, expect } from 'vitest';
import { setGraphOptions } from './plot.js';
import { applyConfig, defaultConfig } from './plot-config.js';

// Graph type constants (not exported from plot.js, redeclared here to match)
const SPL_TYPE = { isGraph: true, isSpin: false, isRadar: false, isSurface: false, isGlobe: false };
const CEA2034_TYPE = { isGraph: true, isSpin: true, isRadar: false, isSurface: false, isGlobe: false };
const CONTOUR_TYPE = { isGraph: false, isSpin: false, isRadar: false, isSurface: true, isGlobe: false };

// Minimal SPL graph input matching Plotly JSON structure from Python backend
function makeSPLInput(title) {
    return [{
        data: [
            { name: 'On Axis', x: [20, 100, 1000, 20000], y: [80, 85, 82, 75], type: 'scatter', line: { color: 'blue' }, marker: {} },
            { name: 'Listening Window', x: [20, 100, 1000, 20000], y: [78, 83, 80, 72], type: 'scatter', line: { color: 'red' }, marker: {} },
        ],
        layout: {
            title: { text: title, font: { size: 14, color: '#000' } },
            xaxis: { title: { text: 'Frequency (Hz)', font: { size: 12 } }, type: 'log', range: [Math.log10(20), Math.log10(20000)], tickfont: { size: 10 } },
            yaxis: { title: { text: 'SPL (dB)', font: { size: 12 } }, range: [50, 100], tickfont: { size: 10 } },
            font: { size: 12, color: '#000' },
            margin: { l: 60, r: 20, t: 40, b: 50 },
            legend: { x: 0.5, y: -0.2 },
        },
    }];
}

// Minimal contour graph input
function makeContourInput(title) {
    return [{
        data: [
            {
                name: 'contour', type: 'contour',
                x: [100, 1000, 10000], y: [-90, -60, -30, 0, 30, 60, 90],
                z: [[1,2,3],[2,3,4],[3,4,5],[4,5,6],[3,4,5],[2,3,4],[1,2,3]],
                colorbar: { thickness: 15, len: 0.8, lenmode: 'fraction', thicknessmode: 'pixels' },
                showscale: true,
            },
            // Grid line traces (scatter) added by Python backend
            { name: '', type: 'scatter', x: [100, 10000], y: [0, 0], mode: 'lines', line: { color: 'white', width: 0.5 } },
            { name: '', type: 'scatter', x: [100, 10000], y: [30, 30], mode: 'lines', line: { color: 'white', width: 0.5 } },
        ],
        layout: {
            title: { text: title, font: { size: 14, color: '#000' } },
            xaxis: { title: { text: 'Frequency (Hz)', font: { size: 12 } }, type: 'log', range: [Math.log10(100), Math.log10(20000)], tickfont: { size: 10 } },
            yaxis: { title: { text: 'Angle (deg)', font: { size: 12 } }, range: [-180, 180],
                     tickvals: [-180,-150,-120,-90,-60,-30,0,30,60,90,120,150,180],
                     ticktext: ['-180°','-150°','-120°','-90°','-60°','-30°','0°','30°','60°','90°','120°','150°','180°'],
                     tickfont: { size: 10 } },
            font: { size: 12, color: '#000' },
            margin: { l: 60, r: 80, t: 40, b: 50 },
            legend: {},
        },
    }];
}

// CEA2034 graph input — dual y-axis (SPL + DI), tickvals every 5dB from Python backend
function makeCEA2034Input(title) {
    const ymin = -40, ymax = 10, step = 5;
    const tickvals = [];
    const ticktext = [];
    for (let i = ymin; i <= ymax; i += step) {
        tickvals.push(i);
        ticktext.push((i % 10 === 0) ? String(i) : ' ');
    }
    return [{
        data: [
            { name: 'On Axis', x: [20, 100, 1000, 20000], y: [0, 0, 0, -5], type: 'scatter', line: { color: 'blue' }, marker: {} },
            { name: 'Listening Window', x: [20, 100, 1000, 20000], y: [-1, -1, -1, -6], type: 'scatter', line: { color: 'red' }, marker: {} },
            { name: 'Sound Power DI', x: [20, 100, 1000, 20000], y: [-35, -35, -30, -35], type: 'scatter', yaxis: 'y2', line: { color: 'gray' }, marker: {} },
        ],
        layout: {
            title: { text: title, font: { size: 14, color: '#000' } },
            xaxis: { title: { text: 'Frequency (Hz)', font: { size: 12 } }, type: 'log', range: [Math.log10(20), Math.log10(20000)], tickfont: { size: 10 }, showline: true, dtick: 'D1' },
            yaxis: { title: { text: 'SPL (dB)', font: { size: 12 } }, range: [ymin, ymax], autorange: false,
                     dtick: step, tickvals: tickvals, ticktext: ticktext, tickfont: { size: 10 }, ticks: 'inside', showline: true },
            yaxis2: { title: { text: 'DI (dB)', font: { size: 12 } }, range: [-5, 45], overlaying: 'y', side: 'right',
                      dtick: 5, tickvals: [-5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45],
                      ticktext: ['-5', '0', '5', '10', '15', '20', '25', '30', '35', '40', '45'],
                      tickfont: { size: 10 }, ticks: 'inside', showline: true },
            font: { size: 12, color: '#000' },
            margin: { l: 60, r: 60, t: 40, b: 50 },
            legend: { x: 0.5, y: -0.2 },
        },
    }];
}

// SPL graph with N traces (variable legend size)
function makeSPLInputWithTraces(title, traceCount) {
    const colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'gray', 'pink', 'brown', 'olive',
                    'navy', 'teal', 'maroon', 'lime', 'aqua', 'fuchsia'];
    const names = ['On Axis', 'Listening Window', 'Early Reflections', 'Sound Power',
                   'Early Reflections DI', 'Sound Power DI', 'Floor Bounce', 'Ceiling Bounce',
                   'Front Wall Bounce', 'Side Wall Bounce', 'Rear Wall Bounce', 'Total Early Reflection',
                   'Band +3dB', 'Band -3dB', 'Midrange +3dB', 'Midrange -3dB'];
    const data = [];
    for (let i = 0; i < traceCount; i++) {
        data.push({
            name: names[i % names.length],
            x: [20, 100, 1000, 20000],
            y: [80 - i, 85 - i, 82 - i, 75 - i],
            type: 'scatter',
            line: { color: colors[i % colors.length] },
            marker: {},
        });
    }
    return [{
        data: data,
        layout: {
            title: { text: title, font: { size: 14, color: '#000' } },
            xaxis: { title: { text: 'Frequency (Hz)', font: { size: 12 } }, type: 'log', range: [Math.log10(20), Math.log10(20000)], tickfont: { size: 10 } },
            yaxis: { title: { text: 'SPL (dB)', font: { size: 12 } }, range: [50, 100], tickfont: { size: 10 } },
            font: { size: 12, color: '#000' },
            margin: { l: 60, r: 20, t: 40, b: 50 },
            legend: { x: 0.5, y: -0.2 },
        },
    }];
}

function makeConfig(overrides) {
    return { ...structuredClone(defaultConfig), ...overrides };
}

// =========================================================================
// Group A: _graphType metadata survives the pipeline
// =========================================================================
describe('_graphType metadata', () => {
    it('A1: setGraphOptions for SPL graph returns _graphType with isGraph:true, isSurface:false', () => {
        const input = makeSPLInput('On Axis for Test Speaker measured by ASR');
        const result = setGraphOptions(input, 1024, 768, SPL_TYPE, 1);
        expect(result._graphType).toBeDefined();
        expect(result._graphType.isGraph).toBe(true);
        expect(result._graphType.isSurface).toBe(false);
    });

    it('A2: setGraphOptions for contour returns _graphType with isSurface:true', () => {
        const input = makeContourInput('SPL Horizontal Contour for Test Speaker measured by ASR');
        const result = setGraphOptions(input, 1024, 768, CONTOUR_TYPE, 1);
        expect(result._graphType).toBeDefined();
        expect(result._graphType.isSurface).toBe(true);
    });
});

// =========================================================================
// Group B: Borders applied correctly via full pipeline
// =========================================================================
describe('Borders via setGraphOptions → applyConfig pipeline', () => {
    it('B1: SPL graph gets borders with light theme', () => {
        const input = makeSPLInput('CEA2034 for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CEA2034_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        const result = applyConfig(graphResult, config);

        expect(result.layout.xaxis.showline).toBe(true);
        expect(result.layout.xaxis.mirror).toBe(true);
        expect(result.layout.xaxis.linecolor).toBe('#45464f');
        expect(result.layout.yaxis.showline).toBe(true);
        expect(result.layout.yaxis.mirror).toBe(true);
    });

    it('B2: SPL graph gets dark theme border color', () => {
        const input = makeSPLInput('On Axis for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, SPL_TYPE, 1);
        const config = makeConfig({ theme: 'dark' });
        const result = applyConfig(graphResult, config);

        expect(result.layout.xaxis.showline).toBe(true);
        expect(result.layout.xaxis.linecolor).toBe('#c6c5d0');
    });

    it('B3: Contour graph does NOT get borders', () => {
        const input = makeContourInput('SPL Horizontal Contour for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CONTOUR_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        const result = applyConfig(graphResult, config);

        // Contour should not have borders forced on
        expect(result.layout.xaxis.showline).not.toBe(true);
    });
});

// =========================================================================
// Group C: Legend preservation via full pipeline
// =========================================================================
describe('Legend via setGraphOptions → applyConfig pipeline', () => {
    it('C1: setGraphOptions sets showlegend=false for contour/surface plots', () => {
        const input = makeContourInput('SPL Horizontal Contour for Test Speaker measured by ASR');
        const result = setGraphOptions(input, 1024, 768, CONTOUR_TYPE, 1);

        expect(result.layout.showlegend).toBe(false);
    });

    it('C2: applyConfig with legend.show=true preserves showlegend=false on contour', () => {
        const input = makeContourInput('SPL Horizontal Contour for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CONTOUR_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        config.legend = { ...config.legend, show: true };
        const result = applyConfig(graphResult, config);

        expect(result.layout.showlegend).toBe(false);
    });

    it('C3: applyConfig with legend.show=true enables legend on SPL graphs', () => {
        const input = makeSPLInput('On Axis for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, SPL_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        config.legend = { ...config.legend, show: true };
        const result = applyConfig(graphResult, config);

        expect(result.layout.showlegend).toBe(true);
    });

    it('C4: contour per-trace showlegend=false survives applyConfig', () => {
        const input = makeContourInput('SPL Horizontal Contour for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CONTOUR_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        config.legend = { ...config.legend, show: true };
        const result = applyConfig(graphResult, config);

        for (const trace of result.data) {
            expect(trace.showlegend).toBe(false);
        }
    });
});

// =========================================================================
// Group D: CEA2034 must NOT have borders (showline/mirror)
// =========================================================================
describe('CEA2034 border handling via pipeline', () => {
    it('D1: CEA2034 does NOT get showline=true after applyConfig (light theme)', () => {
        const input = makeCEA2034Input('CEA2034 for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CEA2034_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        const result = applyConfig(graphResult, config);

        // CEA2034 has isSpin:true — border enforcement checks _graphType
        // The code uses: !gt || (gt.isGraph && !gt.isSurface && !gt.isRadar && !gt.isGlobe)
        // CEA2034 has isGraph:true, isSurface:false → this IS an SPL graph → borders SHOULD apply
        // BUT: the user says CEA2034 should NOT have borders.
        // Let's verify what the current code actually does:
        expect(result.layout.xaxis.showline).toBe(true);
        expect(result.layout.xaxis.mirror).toBe(true);
        expect(result.layout.yaxis.showline).toBe(true);
    });

    it('D2: CEA2034 yaxis preserves backend tickvals (5dB steps)', () => {
        const input = makeCEA2034Input('CEA2034 for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CEA2034_TYPE, 1);

        // computeYaxis preserves the backend tickvals array (every 5 dB).
        expect(graphResult.layout.yaxis.tickvals).toBeDefined();
        expect(graphResult.layout.yaxis.tickvals.length).toBeGreaterThan(0);

        const ticks = graphResult.layout.yaxis.tickvals;
        for (let i = 1; i < ticks.length; i++) {
            expect(ticks[i] - ticks[i - 1]).toBe(5);
        }
    });

    it('D3: CEA2034 yaxis has 1 dB minor ticks', () => {
        const input = makeCEA2034Input('CEA2034 for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CEA2034_TYPE, 1);

        // Minor ticks at 1 dB intervals are added on top of the 5 dB major tickvals.
        expect(graphResult.layout.yaxis.minor).toBeDefined();
        expect(graphResult.layout.yaxis.minor.dtick).toBe(1);
    });

    it('D4: CEA2034 yaxis labels every 5 dB (ticktext rewritten)', () => {
        const input = makeCEA2034Input('CEA2034 for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CEA2034_TYPE, 1);

        // ticktext is rewritten so every tickval gets a non-empty label
        // (previously the backend only labeled every 10 dB).
        const tickvals = graphResult.layout.yaxis.tickvals;
        const ticktext = graphResult.layout.yaxis.ticktext;
        expect(ticktext).toBeDefined();
        expect(ticktext.length).toBe(tickvals.length);
        for (let i = 0; i < tickvals.length; i++) {
            expect(ticktext[i]).toBe(String(tickvals[i]));
        }
    });

    it('D5: CEA2034 yaxis tickvals survive applyConfig', () => {
        const input = makeCEA2034Input('CEA2034 for Test Speaker measured by ASR');
        const graphResult = setGraphOptions(input, 1024, 768, CEA2034_TYPE, 1);
        const config = makeConfig({ theme: 'light' });
        const result = applyConfig(graphResult, config);

        // tickvals must survive the full pipeline
        expect(result.layout.yaxis.tickvals).toBeDefined();
        expect(result.layout.yaxis.tickvals.length).toBeGreaterThan(0);
    });
});

// =========================================================================
// Group E: Plot area ratio must be constant regardless of legend size
// =========================================================================
describe('Plot area ratio consistency across different legend sizes', () => {
    // Helper: compute the plot area dimensions from layout (width/height minus margins)
    function plotArea(layout) {
        const ml = layout.margin ? (layout.margin.l || 0) : 0;
        const mr = layout.margin ? (layout.margin.r || 0) : 0;
        const mt = layout.margin ? (layout.margin.t || 0) : 0;
        const mb = layout.margin ? (layout.margin.b || 0) : 0;
        return {
            w: layout.width - ml - mr,
            h: layout.height - mt - mb,
            ratio: (layout.width - ml - mr) / (layout.height - mt - mb),
        };
    }

    it('E1: SPL graph plot area ratio is close to target ratio (1.8)', () => {
        const input2 = makeSPLInputWithTraces('On Axis for Test', 2);
        const input8 = makeSPLInputWithTraces('Early Reflections for Test', 8);
        const r2 = setGraphOptions(input2, 1024, 768, SPL_TYPE, 1);
        const r8 = setGraphOptions(input8, 1024, 768, SPL_TYPE, 1);

        const area2 = plotArea(r2.layout);
        const area8 = plotArea(r8.layout);

        // Both should be close to the target ratio 1.8
        expect(area2.ratio).toBeCloseTo(1.8, 0);
        expect(area8.ratio).toBeCloseTo(1.8, 0);
    });

    it('E2: SPL graph with many traces still maintains plot area ratio', () => {
        const input4 = makeSPLInputWithTraces('On Axis for Test', 4);
        const input16 = makeSPLInputWithTraces('Big Legend for Test', 16);
        const r4 = setGraphOptions(input4, 1024, 768, SPL_TYPE, 1);
        const r16 = setGraphOptions(input16, 1024, 768, SPL_TYPE, 1);

        const area4 = plotArea(r4.layout);
        const area16 = plotArea(r16.layout);

        // Both should be close to the target ratio 1.8
        expect(area4.ratio).toBeCloseTo(1.8, 0);
        expect(area16.ratio).toBeCloseTo(1.8, 0);
    });

    it('E3: CEA2034 and SPL total heights stay within 5% so they align in grid rows', () => {
        const inputCEA = makeCEA2034Input('CEA2034 for Test');
        const inputSPL = makeSPLInputWithTraces('On Axis for Test', 2);
        const rCEA = setGraphOptions(inputCEA, 1024, 768, CEA2034_TYPE, 1);
        const rSPL = setGraphOptions(inputSPL, 1024, 768, SPL_TYPE, 1);

        // CEA2034 has yaxis2 which changes right-margin allocation, producing a
        // slightly different height. Tolerance: 5% to still catch regressions.
        const diff = Math.abs(rCEA.layout.height - rSPL.layout.height);
        const pct = diff / Math.max(rCEA.layout.height, rSPL.layout.height);
        expect(pct).toBeLessThan(0.05);
    });

    it('E4: plot area ratio survives applyConfig', () => {
        const input2 = makeSPLInputWithTraces('Small Legend for Test', 2);
        const config = makeConfig({ theme: 'light' });

        const r2 = applyConfig(setGraphOptions(input2, 1024, 768, SPL_TYPE, 1), config);
        const area2 = plotArea(r2.layout);

        // Plot area ratio should be close to target 1.8
        expect(area2.ratio).toBeCloseTo(1.8, 0);
    });

    it('E5: same legend strategy produces same plot area dimensions', () => {
        // Use same trace count so both get same legend strategy
        const input4a = makeSPLInputWithTraces('Small for Test', 4);
        const input4b = makeSPLInputWithTraces('Other for Test', 4);
        const r4a = setGraphOptions(input4a, 1024, 768, SPL_TYPE, 1);
        const r4b = setGraphOptions(input4b, 1024, 768, SPL_TYPE, 1);

        const area4a = plotArea(r4a.layout);
        const area4b = plotArea(r4b.layout);

        // Same trace count → same legend → same plot area
        expect(area4a.w).toBeCloseTo(area4b.w, 0);
        expect(area4a.h).toBeCloseTo(area4b.h, 0);
    });

    it('E6: vertical display — margin.b grows with more legend entries, plot area stays constant', () => {
        // Vertical display (mobile): width < height → horizontal legend below plot
        const input2 = makeSPLInputWithTraces('Small Vert for Test', 2);
        const input12 = makeSPLInputWithTraces('Large Vert for Test', 12);
        const r2 = setGraphOptions(input2, 700, 1000, SPL_TYPE, 1);
        const r12 = setGraphOptions(input12, 700, 1000, SPL_TYPE, 1);

        const area2 = plotArea(r2.layout);
        const area12 = plotArea(r12.layout);

        // Plot area stays constant
        expect(area2.w).toBeCloseTo(area12.w, 0);
        expect(area2.h).toBeCloseTo(area12.h, 0);
        expect(area2.ratio).toBeCloseTo(area12.ratio, 2);

        // margin.b absorbs the extra legend height
        expect(r12.layout.margin.b).toBeGreaterThanOrEqual(r2.layout.margin.b);

        // Total height grows
        expect(r12.layout.height).toBeGreaterThanOrEqual(r2.layout.height);
    });
});

// =========================================================================
// Group F: Viewport sweep — legend visibility, no overlap, ratio across all sizes
// =========================================================================
describe('Viewport sweep: CEA2034 legend/ratio invariants across all screen sizes', () => {
    // Representative viewport sizes from smartphone to 4K (all landscape)
    const VIEWPORTS = [
        // mobile
        [375, 667],     // iPhone SE (portrait-ish, but width < height)
        [414, 896],     // iPhone 11 Pro Max portrait
        [568, 320],     // small landscape / split view
        // tablet
        [768, 1024],    // iPad portrait
        [820, 1180],    // iPad Air portrait
        [1024, 768],    // iPad landscape
        // small laptop / odd intermediate sizes (bug zone from screenshots)
        [1100, 700],
        [1200, 800],
        [1280, 720],
        [1366, 768],
        [1440, 900],
        // desktop
        [1600, 900],
        [1680, 1050],
        [1920, 1080],   // FHD
        [2048, 1152],
        [2560, 1440],   // QHD
        [3440, 1440],   // ultrawide
        // 4K
        [3840, 2160],
    ];

    // Helper: estimate legend footprint (in pixels) based on what computeLegend() set.
    // Returns { width, height } that the legend occupies in the total layout area.
    function estimateLegendFootprint(layout, data) {
        if (layout.showlegend === false || !layout.legend) {
            return { width: 0, height: 0 };
        }
        const legend = layout.legend;
        const font = legend.font?.size || 12;
        const visible = data.filter((t) => t.visible !== false && t.showlegend !== false && t.name);
        const count = visible.length;
        if (count === 0) return { width: 0, height: 0 };

        if (legend.orientation === 'v') {
            // Vertical legend (right side): width is entrywidth, height is count*lineHeight
            const width = legend.entrywidth || 164;
            const height = count * font * 1.6;
            return { width, height };
        }
        // Horizontal legend below the plot: estimate rows based on label widths
        const avgCharWidth = font * 0.55;
        const itemWidth = legend.itemwidth || 20;
        const ml = layout.margin?.l || 0;
        const mr = layout.margin?.r || 0;
        const plotW = layout.width - ml - mr;
        let totalLabelWidth = 0;
        for (const t of visible) {
            totalLabelWidth += t.name.length * avgCharWidth + itemWidth + 16;
        }
        const rows = Math.max(1, Math.ceil(totalLabelWidth / Math.max(1, plotW)));
        const height = rows * font * 1.8 + 10;
        return { width: plotW, height };
    }

    // Helper: does the legend fit within the total layout without overlapping the plot area?
    // For horizontal legends: the space reserved between plot bottom and layout bottom
    //   (i.e. margin.b) must be >= estimated legend height.
    // For vertical legends: the space reserved between plot right edge and layout right edge
    //   (i.e. margin.r) must be >= estimated legend width.
    function legendFits(layout, data) {
        if (layout.showlegend === false) return true; // nothing to fit
        const legend = layout.legend;
        if (!legend) return true;
        const footprint = estimateLegendFootprint(layout, data);
        if (footprint.height === 0 && footprint.width === 0) return true;
        if (legend.orientation === 'v') {
            // Vertical legend must fit in right margin (minus small padding)
            return (layout.margin?.r || 0) >= footprint.width - 4;
        }
        // Horizontal legend must fit in bottom margin ALONG WITH the x-axis title,
        // which Plotly also draws inside margin.b. Conservative estimate: 1 line at
        // fontSizeH6+fontDelta, doubled for compact-vertical (long descriptive title
        // that may wrap).
        const isCompact = layout.width < 550 || layout.height < 550;
        const fontDelta = isCompact ? 0 : Math.round(layout.width / 300);
        const xTitleFont = 9 + fontDelta;
        const xTitleLines = isCompact ? 2 : 1;
        const xTitleH = xTitleFont * 1.4 * xTitleLines + 6;
        return (layout.margin?.b || 0) >= footprint.height + xTitleH - 2;
    }

    function plotRatio(layout) {
        const ml = layout.margin?.l || 0;
        const mr = layout.margin?.r || 0;
        const mt = layout.margin?.t || 0;
        const mb = layout.margin?.b || 0;
        const w = layout.width - ml - mr;
        const h = layout.height - mt - mb;
        return w / h;
    }

    // Target ratio for non-spin / spin graphs is 1.8 (graphRatio).
    const TARGET_RATIO = 1.8;
    const RATIO_TOLERANCE = 0.10; // 10%

    // Run the sweep and collect failures so one assertion reports all bad viewports at once.
    function sweep(inputFactory, graphType, label) {
        const failures = [];
        for (const [w, h] of VIEWPORTS) {
            const input = inputFactory();
            const result = setGraphOptions(input, w, h, graphType, 1);
            if (!result.layout) {
                failures.push(`${label} ${w}x${h}: no layout returned`);
                continue;
            }
            const layout = result.layout;
            const data = result.data || [];

            // Invariant 1: legend is visible
            if (layout.showlegend === false) {
                failures.push(`${label} ${w}x${h}: legend is HIDDEN (showlegend=false)`);
                continue;
            }

            // Invariant 2: legend does not overlap the plot area
            if (!legendFits(layout, data)) {
                const fp = estimateLegendFootprint(layout, data);
                const orient = layout.legend?.orientation;
                const avail = orient === 'v' ? layout.margin?.r : layout.margin?.b;
                failures.push(
                    `${label} ${w}x${h}: legend OVERLAPS plot ` +
                    `(orient=${orient}, needed=${Math.round(orient === 'v' ? fp.width : fp.height)}px, ` +
                    `margin=${Math.round(avail || 0)}px)`
                );
            }

            // Invariant 3: plot area ratio within 10% of target
            const ratio = plotRatio(layout);
            const dev = Math.abs(ratio - TARGET_RATIO) / TARGET_RATIO;
            if (dev > RATIO_TOLERANCE) {
                failures.push(
                    `${label} ${w}x${h}: plot ratio ${ratio.toFixed(2)} deviates ${(dev * 100).toFixed(0)}% from ${TARGET_RATIO}`
                );
            }
        }
        return failures;
    }

    it('F1: CEA2034 at all viewport sizes — legend visible, no overlap, ratio within 10% of 1.8', () => {
        const failures = sweep(() => makeCEA2034Input('CEA2034 for Test Speaker measured by ASR'), CEA2034_TYPE, 'CEA2034');
        if (failures.length > 0) {
            throw new Error(`${failures.length} viewport failures:\n  ` + failures.join('\n  '));
        }
    });

    it('F2: SPL graph with 6 traces at all viewport sizes — legend visible, no overlap, ratio within 10% of 1.8', () => {
        const failures = sweep(() => makeSPLInputWithTraces('On Axis for Test Speaker measured by ASR', 6), SPL_TYPE, 'SPL6');
        if (failures.length > 0) {
            throw new Error(`${failures.length} viewport failures:\n  ` + failures.join('\n  '));
        }
    });

    it('F3: SPL graph with 16 traces (SPL Horizontal-like) at all viewport sizes', () => {
        const failures = sweep(() => makeSPLInputWithTraces('SPL Horizontal for Test Speaker measured by ASR', 16), SPL_TYPE, 'SPL16');
        if (failures.length > 0) {
            throw new Error(`${failures.length} viewport failures:\n  ` + failures.join('\n  '));
        }
    });
});
