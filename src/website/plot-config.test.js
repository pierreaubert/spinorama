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

        expect(result.layout.paper_bgcolor).toBe('#ffffff');
        expect(result.layout.plot_bgcolor).toBe('#ffffff');
        expect(result.layout.font.color).toBe('#333333');
        expect(result.layout.xaxis.gridcolor).toBe('#e0e0e0');
        expect(result.layout.yaxis.gridcolor).toBe('#e0e0e0');
    });

    it('dark theme sets correct bgcolor and font colors', () => {
        const options = makeOptions();
        const config = { ...structuredClone(defaultConfig), theme: 'dark' };
        const result = applyConfig(options, config);

        expect(result.layout.paper_bgcolor).toBe('#1a1a2e');
        expect(result.layout.plot_bgcolor).toBe('#16213e');
        expect(result.layout.font.color).toBe('#e0e0e0');
        expect(result.layout.xaxis.gridcolor).toBe('#3a3a5c');
        expect(result.layout.xaxis.linecolor).toBe('#e0e0e0');
        expect(result.layout.xaxis.zerolinecolor).toBe('#5a5a7c');
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

describe('applyConfig - legend offset range', () => {
    it('allows legend offset up to 1.0', () => {
        const options = makeOptions();
        const config = structuredClone(defaultConfig);
        config.legend.xoffset = 1.0;
        config.legend.yoffset = 1.0;
        const result = applyConfig(options, config);

        // Legend position should have the offset applied
        expect(result.layout.legend.x).toBeGreaterThanOrEqual(1.0);
        expect(result.layout.legend.y).toBeGreaterThanOrEqual(1.0);
    });

    it('allows legend offset down to -1.0', () => {
        const options = makeOptions();
        const config = structuredClone(defaultConfig);
        config.legend.xoffset = -1.0;
        config.legend.yoffset = -1.0;
        const result = applyConfig(options, config);

        expect(result.layout.legend.x).toBeLessThanOrEqual(0);
        expect(result.layout.legend.y).toBeLessThanOrEqual(0);
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
