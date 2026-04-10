// -*- coding: utf-8 -*-
// Tests for plot-config.js
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

import { describe, expect, it } from 'vitest';
import { applyConfig, defaultConfig } from './plot-config.js';

function makeOptions(overrides = {}) {
    return {
        layout: {
            paper_bgcolor: '#f0f0f0',
            plot_bgcolor: '#f0f0f0',
            font: { color: '#000000' },
            xaxis: { gridcolor: '#cccccc', linecolor: '#000000', zerolinecolor: '#000000' },
            yaxis: { gridcolor: '#cccccc', linecolor: '#000000', zerolinecolor: '#000000' },
            legend: { font: { size: 12 } },
            margin: { l: 10, r: 10, t: 10, b: 10 },
            ...overrides,
        },
        data: [],
    };
}

describe('applyConfig - theme application', () => {
    it('light theme sets correct bgcolor and font colors', () => {
        const options = makeOptions();
        const config = { ...structuredClone(defaultConfig), theme: 'light' };
        const result = applyConfig(options, config);

        expect(result.layout.paper_bgcolor).toBe('#faf8ff');
        expect(result.layout.plot_bgcolor).toBe('#faf8ff');
        expect(result.layout.font.color).toBe('#1b1b21');
        expect(result.layout.xaxis.gridcolor).toBe('rgba(0,0,0,0.22)');
        expect(result.layout.yaxis.gridcolor).toBe('rgba(0,0,0,0.22)');
    });

    it('dark theme sets correct bgcolor and font colors', () => {
        const options = makeOptions();
        const config = { ...structuredClone(defaultConfig), theme: 'dark' };
        const result = applyConfig(options, config);

        expect(result.layout.paper_bgcolor).toBe('#131318');
        expect(result.layout.plot_bgcolor).toBe('#1f1f25');
        expect(result.layout.font.color).toBe('#e3e1e9');
        expect(result.layout.xaxis.gridcolor).toBe('rgba(255,255,255,0.22)');
        expect(result.layout.xaxis.linecolor).toBe('#c6c5d0');
        expect(result.layout.xaxis.zerolinecolor).toBe('#45464f');
    });

    it('default theme leaves layout unchanged', () => {
        const options = makeOptions();
        const config = { ...structuredClone(defaultConfig), theme: 'default' };
        const result = applyConfig(options, config);

        expect(result.layout.paper_bgcolor).toBe('#f0f0f0');
        expect(result.layout.plot_bgcolor).toBe('#f0f0f0');
        expect(result.layout.font.color).toBe('#000000');
    });
});

describe('applyConfig - legend position presets', () => {
    const positions = {
        right: { x: 1.0, y: 1.0, xanchor: 'left', yanchor: 'auto', orientation: 'v' },
        left: { x: 0.0, y: 1.0, xanchor: 'right', yanchor: 'auto', orientation: 'v' },
        top: { x: 0.5, y: 1.0, xanchor: 'center', yanchor: 'bottom', orientation: 'h' },
        bottom: { x: 0.5, y: -0.1, xanchor: 'center', yanchor: 'top', orientation: 'h' },
    };

    for (const [position, expected] of Object.entries(positions)) {
        it(`position "${position}" sets correct x, y, xanchor, yanchor, orientation`, () => {
            const options = makeOptions();
            const config = structuredClone(defaultConfig);
            config.legend.position = position;
            const result = applyConfig(options, config);

            expect(result.layout.legend.x).toBeCloseTo(expected.x, 2);
            expect(result.layout.legend.y).toBeCloseTo(expected.y, 2);
            expect(result.layout.legend.xanchor).toBe(expected.xanchor);
            expect(result.layout.legend.yanchor).toBe(expected.yanchor);
            expect(result.layout.legend.orientation).toBe(expected.orientation);
        });

        it(`position "${position}" works with custom margins`, () => {
            const options = makeOptions();
            options.layout.margin = { l: 80, r: 80, t: 80, b: 80 };
            const config = structuredClone(defaultConfig);
            config.legend.position = position;
            const result = applyConfig(options, config);

            expect(result.layout.legend.x).toBeCloseTo(expected.x, 2);
            expect(result.layout.legend.y).toBeCloseTo(expected.y, 2);
            expect(result.layout.legend.xanchor).toBe(expected.xanchor);
            expect(result.layout.legend.yanchor).toBe(expected.yanchor);
        });

        it(`position "${position}" works with zero margins`, () => {
            const options = makeOptions();
            options.layout.margin = { l: 0, r: 0, t: 0, b: 0 };
            const config = structuredClone(defaultConfig);
            config.legend.position = position;
            const result = applyConfig(options, config);

            expect(result.layout.legend.xanchor).toBe(expected.xanchor);
            expect(result.layout.legend.yanchor).toBe(expected.yanchor);
        });

        it(`position "${position}" with legend hidden does not show legend`, () => {
            const options = makeOptions();
            options.data = [{ name: 'trace1' }];
            const config = structuredClone(defaultConfig);
            config.legend.position = position;
            config.legend.show = false;
            const result = applyConfig(options, config);

            expect(result.layout.showlegend).toBe(false);
            expect(result.data[0].showlegend).toBe(false);
        });

        it(`position "${position}" with legend shown keeps legend visible`, () => {
            const options = makeOptions();
            options.data = [{ name: 'trace1' }];
            const config = structuredClone(defaultConfig);
            config.legend.position = position;
            config.legend.show = true;
            const result = applyConfig(options, config);

            expect(result.layout.showlegend).toBe(true);
            expect(result.data[0].showlegend).toBe(true);
        });
    }

    it('position "right" places legend at x=1.0 with xanchor=left (outside plot)', () => {
        const options = makeOptions();
        const config = structuredClone(defaultConfig);
        config.legend.position = 'right';
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBe(1.0);
        expect(result.layout.legend.xanchor).toBe('left');
        expect(result.layout.legend.orientation).toBe('v');
    });

    it('position "default" does not modify legend position', () => {
        const options = makeOptions();
        options.layout.legend = { x: 0.7, y: 0.3, xanchor: 'auto', yanchor: 'auto' };
        const config = structuredClone(defaultConfig);
        config.legend.position = 'default';
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeCloseTo(0.7, 2);
        expect(result.layout.legend.y).toBeCloseTo(0.3, 2);
    });

    it('position with offset adjusts final position', () => {
        const options = makeOptions();
        const config = structuredClone(defaultConfig);
        config.legend.position = 'right';
        config.legend.xoffset = 0.1;
        config.legend.yoffset = -0.2;
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeCloseTo(1.1, 2);
        expect(result.layout.legend.y).toBeCloseTo(0.8, 2);
    });

    it('offset of 0 does not modify position', () => {
        const options = makeOptions();
        options.layout.legend = { x: 0.5, y: 0.5 };
        const config = structuredClone(defaultConfig);
        config.legend.position = 'default';
        config.legend.xoffset = 0;
        config.legend.yoffset = 0;
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeCloseTo(0.5, 2);
        expect(result.layout.legend.y).toBeCloseTo(0.5, 2);
    });

    it('offset works when layout has no initial legend position', () => {
        const options = makeOptions();
        // no legend set in layout
        const config = structuredClone(defaultConfig);
        config.legend.xoffset = 0.3;
        config.legend.yoffset = -0.1;
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeCloseTo(0.3, 2);
        expect(result.layout.legend.y).toBeCloseTo(-0.1, 2);
    });

    it('legend.show defaults to true in defaultConfig', () => {
        expect(defaultConfig.legend.show).toBe(true);
    });
});

describe('applyConfig - legend offset range', () => {
    it('allows legend offset up to 1.0 with position set', () => {
        const options = makeOptions();
        const config = structuredClone(defaultConfig);
        config.legend.position = 'top';
        config.legend.xoffset = 1.0;
        config.legend.yoffset = 1.0;
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeCloseTo(1.5, 2);
        expect(result.layout.legend.y).toBeCloseTo(2.0, 2);
    });

    it('allows legend offset down to -1.0 with position set', () => {
        const options = makeOptions();
        const config = structuredClone(defaultConfig);
        config.legend.position = 'top';
        config.legend.xoffset = -1.0;
        config.legend.yoffset = -1.0;
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeCloseTo(-0.5, 2);
        expect(result.layout.legend.y).toBeCloseTo(0.0, 2);
    });
});

describe('applyConfig - legend group title font', () => {
    it('enforces legendgrouptitle font size >= legend font size', () => {
        const options = makeOptions();
        options.data = [
            {
                name: 'trace1',
                legendgrouptitle: { text: 'Speaker A', font: { size: 8 } },
            },
        ];
        const config = structuredClone(defaultConfig);
        const result = applyConfig(options, config);

        // Legend font size is 12 in our mock, so group title should be at least 12
        expect(result.data[0].legendgrouptitle.font.size).toBe(12);
    });

    it('keeps legendgrouptitle font size when already >= legend font size', () => {
        const options = makeOptions();
        options.data = [
            {
                name: 'trace1',
                legendgrouptitle: { text: 'Speaker A', font: { size: 16 } },
            },
        ];
        const config = structuredClone(defaultConfig);
        const result = applyConfig(options, config);

        expect(result.data[0].legendgrouptitle.font.size).toBe(16);
    });

    it('creates font object when legendgrouptitle has text but no font', () => {
        const options = makeOptions();
        options.data = [
            {
                name: 'trace1',
                legendgrouptitle: { text: 'Speaker A' },
            },
        ];
        const config = structuredClone(defaultConfig);
        const result = applyConfig(options, config);

        expect(result.data[0].legendgrouptitle.font.size).toBe(12);
    });

    it('does not modify traces without legendgrouptitle', () => {
        const options = makeOptions();
        options.data = [{ name: 'trace1' }];
        const config = structuredClone(defaultConfig);
        const result = applyConfig(options, config);

        expect(result.data[0].legendgrouptitle).toBeUndefined();
    });
});

describe('applyConfig - annotations visibility', () => {
    it('hides layout annotations when annotations.show is false', () => {
        const options = makeOptions({
            annotations: [
                { text: 'slope', visible: true },
                { text: 'smoothness', visible: true },
            ],
        });
        const config = structuredClone(defaultConfig);
        config.annotations.show = false;
        const result = applyConfig(options, config);

        expect(result.layout.annotations[0].visible).toBe(false);
        expect(result.layout.annotations[1].visible).toBe(false);
    });

    it('shows layout annotations when annotations.show is true', () => {
        const options = makeOptions({
            annotations: [{ text: 'slope', visible: false }],
        });
        const config = structuredClone(defaultConfig);
        config.annotations.show = true;
        const result = applyConfig(options, config);

        expect(result.layout.annotations[0].visible).toBe(true);
    });
});

describe('applyConfig - trendlines visibility', () => {
    it('hides trend line traces when trendlines.show is false', () => {
        const options = makeOptions();
        options.data = [
            { name: 'On Axis', type: 'scatter' },
            { name: 'Band ±3dB', type: 'scatter' },
            { name: 'Band ±1.5dB', type: 'scatter' },
            { name: 'Midrange ±3dB', type: 'scatter' },
            { name: 'Linear interpolation', type: 'scatter' },
        ];
        const config = structuredClone(defaultConfig);
        config.trendlines.show = false;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBeUndefined();
        expect(result.data[1].visible).toBe(false);
        expect(result.data[2].visible).toBe(false);
        expect(result.data[3].visible).toBe(false);
        expect(result.data[4].visible).toBe(false);
    });

    it('shows trend line traces when trendlines.show is true (overrides Python visible=false)', () => {
        const options = makeOptions();
        options.data = [
            { name: 'Band ±3dB', type: 'scatter', visible: false },
            { name: 'On Axis', type: 'scatter' },
        ];
        const config = structuredClone(defaultConfig);
        config.trendlines.show = true;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(true);
        expect(result.data[1].visible).toBeUndefined();
    });

    it('handles CEA2034 slope traces', () => {
        const options = makeOptions();
        options.data = [
            { name: 'Sound Power slope', type: 'scatter', visible: false },
            { name: 'Listening Window slope', type: 'scatter', visible: false },
            { name: 'Early Reflections DI slope', type: 'scatter', visible: false },
            { name: 'On Axis', type: 'scatter' },
        ];
        const config = structuredClone(defaultConfig);
        config.trendlines.show = true;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(true);
        expect(result.data[1].visible).toBe(true);
        expect(result.data[2].visible).toBe(true);
        expect(result.data[3].visible).toBeUndefined();
    });

    it('does not affect recommended zone traces', () => {
        const options = makeOptions();
        options.data = [
            { name: 'recommended SP zone', type: 'scatter', visible: false },
            { name: 'Band ±3dB', type: 'scatter' },
        ];
        const config = structuredClone(defaultConfig);
        config.trendlines.show = false;
        config.zones.show = true;
        const result = applyConfig(options, config);

        // zones are controlled by zones config, not trendlines
        expect(result.data[0].visible).toBe(true);
        expect(result.data[1].visible).toBe(false);
    });
});

describe('applyConfig - recommended zones visibility', () => {
    it('hides recommended zone traces when zones.show is false', () => {
        const options = makeOptions();
        options.data = [
            { name: 'recommended SP zone', type: 'scatter' },
            { name: 'recommended LW zone', type: 'scatter' },
            { name: 'On Axis', type: 'scatter' },
        ];
        const config = structuredClone(defaultConfig);
        config.zones.show = false;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(false);
        expect(result.data[1].visible).toBe(false);
        expect(result.data[2].visible).toBeUndefined();
    });

    it('shows recommended zone traces when zones.show is true', () => {
        const options = makeOptions();
        options.data = [{ name: 'recommended SP zone', type: 'scatter', visible: false }];
        const config = structuredClone(defaultConfig);
        config.zones.show = true;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(true);
    });

    it('per-speaker zone visibility in compare mode', () => {
        const options = makeOptions();
        options.data = [
            { name: 'recommended SP zone', type: 'scatter', legendgroup: 'speaker0' },
            { name: 'recommended SP zone', type: 'scatter', legendgroup: 'speaker1' },
        ];
        const config = structuredClone(defaultConfig);
        config.zones.showA = true;
        config.zones.showB = false;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(true);
        expect(result.data[1].visible).toBe(false);
    });
});

describe('applyConfig - per-speaker compare mode', () => {
    it('hides trendlines for speaker A only', () => {
        const options = makeOptions();
        options.data = [
            { name: 'Band ±3dB', type: 'scatter', legendgroup: 'speaker0' },
            { name: 'Band ±3dB', type: 'scatter', legendgroup: 'speaker1' },
            { name: 'On Axis', type: 'scatter', legendgroup: 'speaker0' },
        ];
        const config = structuredClone(defaultConfig);
        config.trendlines.showA = false;
        config.trendlines.showB = true;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(false);
        expect(result.data[1].visible).toBe(true);
        expect(result.data[2].visible).toBeUndefined();
    });

    it('hides trendlines for speaker B only', () => {
        const options = makeOptions();
        options.data = [
            { name: 'Sound Power slope', type: 'scatter', legendgroup: 'speaker0' },
            { name: 'Sound Power slope', type: 'scatter', legendgroup: 'speaker1' },
        ];
        const config = structuredClone(defaultConfig);
        config.trendlines.showA = true;
        config.trendlines.showB = false;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(true);
        expect(result.data[1].visible).toBe(false);
    });

    it('hides annotations for speaker A only', () => {
        const options = makeOptions({
            annotations: [
                { text: 'slope A', _speakerIndex: 0 },
                { text: 'slope B', _speakerIndex: 1 },
            ],
        });
        const config = structuredClone(defaultConfig);
        config.annotations.showA = false;
        config.annotations.showB = true;
        const result = applyConfig(options, config);

        expect(result.layout.annotations[0].visible).toBe(false);
        expect(result.layout.annotations[1].visible).toBe(true);
    });

    it('hides annotations for speaker B only', () => {
        const options = makeOptions({
            annotations: [
                { text: 'slope A', _speakerIndex: 0 },
                { text: 'slope B', _speakerIndex: 1 },
            ],
        });
        const config = structuredClone(defaultConfig);
        config.annotations.showA = true;
        config.annotations.showB = false;
        const result = applyConfig(options, config);

        expect(result.layout.annotations[0].visible).toBe(true);
        expect(result.layout.annotations[1].visible).toBe(false);
    });

    it('falls back to global show for traces without legendgroup', () => {
        const options = makeOptions();
        options.data = [{ name: 'Band ±3dB', type: 'scatter' }];
        const config = structuredClone(defaultConfig);
        config.trendlines.show = false;
        config.trendlines.showA = true;
        config.trendlines.showB = true;
        const result = applyConfig(options, config);

        expect(result.data[0].visible).toBe(false);
    });

    it('falls back to global show for annotations without _speakerIndex', () => {
        const options = makeOptions({
            annotations: [{ text: 'slope' }],
        });
        const config = structuredClone(defaultConfig);
        config.annotations.show = false;
        config.annotations.showA = true;
        config.annotations.showB = true;
        const result = applyConfig(options, config);

        expect(result.layout.annotations[0].visible).toBe(false);
    });
});

describe('applyConfig - dark palette auto-selection', () => {
    it('auto-selects dark palette when theme is dark and palette is default', () => {
        const options = {
            layout: {
                paper_bgcolor: '#f0f0f0',
                plot_bgcolor: '#f0f0f0',
                font: { color: '#000' },
                xaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                yaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                margin: { l: 10, r: 10, t: 10, b: 10 },
            },
            data: [
                { type: 'scatter', line: { color: 'blue' }, marker: {} },
            ],
        };
        const config = { ...structuredClone(defaultConfig), theme: 'dark', colors: { palette: 'default' } };
        const result = applyConfig(options, config);
        // dark palette should have been applied — first color is rgb(185, 195, 255)
        expect(result.data[0].line.color).toBe('rgb(185, 195, 255)');
    });

    it('does not auto-select dark palette when user chose a specific palette', () => {
        const options = {
            layout: {
                paper_bgcolor: '#f0f0f0',
                plot_bgcolor: '#f0f0f0',
                font: { color: '#000' },
                xaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                yaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                margin: { l: 10, r: 10, t: 10, b: 10 },
            },
            data: [
                { type: 'scatter', line: { color: 'blue' }, marker: {} },
            ],
        };
        const config = { ...structuredClone(defaultConfig), theme: 'dark', colors: { palette: 'vibrant' } };
        const result = applyConfig(options, config);
        // vibrant palette first color: rgb(255, 107, 107)
        expect(result.data[0].line.color).toBe('rgb(255, 107, 107)');
    });

    it('does not auto-select dark palette in light theme', () => {
        const options = {
            layout: {
                paper_bgcolor: '#f0f0f0',
                plot_bgcolor: '#f0f0f0',
                font: { color: '#000' },
                xaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                yaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                margin: { l: 10, r: 10, t: 10, b: 10 },
            },
            data: [
                { type: 'scatter', line: { color: 'blue' }, marker: {} },
            ],
        };
        const config = { ...structuredClone(defaultConfig), theme: 'light', colors: { palette: 'default' } };
        const result = applyConfig(options, config);
        // default palette not applied when palette is 'default' in light mode
        expect(result.data[0].line.color).toBe('blue');
    });
});

describe('createConfigMenu is a no-op', () => {
    it('returns immediately without error', async () => {
        const { createConfigMenu } = await import('./plot-config.js');
        createConfigMenu('nonexistent', {}, () => {}, {});
    });
});

describe('applyConfig — _graphType border enforcement', () => {
    function makeBaseOptions(graphType) {
        return {
            layout: {
                xaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                yaxis: { gridcolor: '#ccc', linecolor: '#000', zerolinecolor: '#000' },
                font: { color: '#000' },
                margin: { l: 10, r: 10, t: 10, b: 10 },
            },
            data: [{ type: 'scatter', line: { color: 'blue' }, marker: {} }],
            _graphType: graphType,
        };
    }

    it('F1: sets showline/mirror on SPL graph (_graphType.isGraph=true)', () => {
        const options = makeBaseOptions({ isGraph: true, isSpin: false, isRadar: false, isSurface: false, isGlobe: false });
        const config = { ...structuredClone(defaultConfig), theme: 'light' };
        const result = applyConfig(options, config);
        expect(result.layout.xaxis.showline).toBe(true);
        expect(result.layout.xaxis.mirror).toBe(true);
        expect(result.layout.yaxis.showline).toBe(true);
        expect(result.layout.yaxis.mirror).toBe(true);
    });

    it('F2: does NOT set showline on contour (_graphType.isSurface=true)', () => {
        const options = makeBaseOptions({ isGraph: false, isSpin: false, isRadar: false, isSurface: true, isGlobe: false });
        const config = { ...structuredClone(defaultConfig), theme: 'light' };
        const result = applyConfig(options, config);
        expect(result.layout.xaxis.showline).not.toBe(true);
    });

    it('F3: defaults to SPL behavior when _graphType is missing', () => {
        const options = makeBaseOptions(undefined);
        delete options._graphType;
        const config = { ...structuredClone(defaultConfig), theme: 'light' };
        const result = applyConfig(options, config);
        expect(result.layout.xaxis.showline).toBe(true);
        expect(result.layout.xaxis.mirror).toBe(true);
    });
});

describe('applyConfig — showlegend guards', () => {
    function makeBaseOptions(showlegend) {
        const opts = {
            layout: {
                xaxis: {}, yaxis: {},
                font: { color: '#000' },
                margin: { l: 10, r: 10, t: 10, b: 10 },
            },
            data: [
                { type: 'scatter', name: 'trace1', line: { color: 'blue' }, marker: {} },
            ],
        };
        if (showlegend !== undefined) {
            opts.layout.showlegend = showlegend;
        }
        return opts;
    }

    it('F4: preserves layout.showlegend=false even when config.legend.show=true', () => {
        const options = makeBaseOptions(false);
        const config = { ...structuredClone(defaultConfig), legend: { ...defaultConfig.legend, show: true } };
        const result = applyConfig(options, config);
        expect(result.layout.showlegend).toBe(false);
    });

    it('F5: sets layout.showlegend=true when absent and config.legend.show=true', () => {
        const options = makeBaseOptions(undefined);
        const config = { ...structuredClone(defaultConfig), legend: { ...defaultConfig.legend, show: true } };
        const result = applyConfig(options, config);
        expect(result.layout.showlegend).toBe(true);
    });

    it('F6: preserves per-trace showlegend=false even when config.legend.show=true', () => {
        const options = makeBaseOptions(undefined);
        options.data[0].showlegend = false;
        const config = { ...structuredClone(defaultConfig), legend: { ...defaultConfig.legend, show: true } };
        const result = applyConfig(options, config);
        expect(result.data[0].showlegend).toBe(false);
    });
});
