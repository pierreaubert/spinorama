// -*- coding: utf-8 -*-
// Tests for graph.js
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

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Mock Plotly
vi.mock('plotly.js-dist-min', () => ({
    default: {
        newPlot: vi.fn(),
        react: vi.fn(),
    },
}));

// Mock plot.js
vi.mock('./plot.js', () => ({
    setPlotForMeasurement: vi.fn().mockImplementation((_measurementName, _speakerNames, _speakerGraphs, _w, _h, _n) => {
        return [
            {
                data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
                layout: {
                    title: { text: 'Test Graph' },
                    xaxis: { showgrid: true },
                    yaxis: { showgrid: true },
                    legend: { x: 1, y: 0.5 },
                },
                config: {},
            },
        ];
    }),
}));

// Mock graph-config.js
vi.mock('./plot-config.js', () => ({
    loadConfigFromStorage: vi.fn().mockReturnValue({
        theme: 'light',
        font: { family: 'Arial, sans-serif', size: 12, color: '#333333' },
        grid: true,
        legend: { position: 'right', show: true },
        margin: { l: 50, r: 50, t: 80, b: 50 },
        colors: { palette: 'default' },
        layout: { direction: 'horizontal' },
        contour: { colorscale: 'default' },
    }),
    saveConfigToStorage: vi.fn(),
    createConfigMenu: vi.fn(),
    initGlobalConfigPanel: vi.fn(),
    applyConfig: vi.fn().mockImplementation((options, _config) => options),
}));

// Import after mocking
import { displayGraph } from './graph.js';
import { setPlotForMeasurement } from './plot.js';
import Plotly from 'plotly.js-dist-min';

describe('Graph Display', () => {
    let dom;
    let window;
    let document;

    beforeEach(() => {
        // Set up a DOM environment
        dom = new JSDOM('<!DOCTYPE html><html><body><div id="test-graph"></div></body></html>', {
            url: 'http://localhost/',
            runScripts: 'dangerously',
        });
        window = dom.window;
        document = window.document;

        // Create localStorage mock
        const localStorageMock = (() => {
            let store = {};
            return {
                getItem: (key) => store[key] || null,
                setItem: (key, value) => {
                    store[key] = value.toString();
                },
                removeItem: (key) => {
                    delete store[key];
                },
                clear: () => {
                    store = {};
                },
            };
        })();

        // Mock window properties
        global.window = window;
        global.document = document;
        global.HTMLElement = window.HTMLElement;
        global.Element = window.Element;
        global.Plotly = Plotly;
        global.localStorage = localStorageMock;

        // Mock localStorage using Object.defineProperty since it's read-only
        Object.defineProperty(window, 'localStorage', {
            value: localStorageMock,
            writable: true,
            configurable: true,
        });

        window.innerWidth = 1024;
        window.innerHeight = 768;

        // Reset mocks
        vi.clearAllMocks();
    });

    afterEach(() => {
        // Clean up
        delete global.window;
        delete global.document;
        delete global.HTMLElement;
        delete global.Element;
        delete global.Plotly;
        delete global.localStorage;
    });

    test('displayGraph calls setPlotForMeasurement with correct parameters', async () => {
        // Create a sample graph spec
        const graphSpec = {
            layout: {
                title: { text: 'Test Graph' },
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        // Call displayGraph
        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1);

        // Check if setPlotForMeasurement was called with correct parameters
        expect(setPlotForMeasurement).toHaveBeenCalledWith('On Axis', ['Test Graph'], [graphSpec], 1024, 768, 1);
    });

    test('displayGraph calls Plotly.newPlot with correct parameters', async () => {
        // Create a sample graph spec
        const graphSpec = {
            layout: {
                title: { text: 'Test Graph' },
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        // Call displayGraph
        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1);

        // Check if Plotly.newPlot was called
        expect(Plotly.newPlot).toHaveBeenCalled();
        const callArgs = Plotly.newPlot.mock.calls[0];
        // The element is the ID or the element itself which should be the DIV
        expect(callArgs[0]).toBe(document.getElementById('test-graph'));
        expect(callArgs[1]).toBeDefined();
    });

    test('3D plots have shapes removed', async () => {
        // Create a sample 3D graph spec
        const graphSpec = {
            layout: {
                title: { text: 'Test 3D Graph' },
                shapes: [{ type: 'line' }],
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], z: [1, 2, 3], type: 'scatter3d' }],
        };

        // Call displayGraph with a 3D jsonName
        await displayGraph('SPL Horizontal Contour 3D', 'test3D.json', 'test-graph', graphSpec, true, 1);

        // Check if shapes were removed
        const callArgs = Plotly.newPlot.mock.calls[0];
        expect(callArgs[1].layout.shapes).toBeNull();
    });

    test('displayGraph loads configuration from storage', async () => {
        // Create a sample graph spec
        const graphSpec = {
            layout: {
                title: { text: 'Test Graph' },
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        // Call displayGraph
        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1);

        // Check if Plotly.newPlot was called
        expect(Plotly.newPlot).toHaveBeenCalled();
    });

    test('displayGraph handles error gracefully', async () => {
        // Create a sample graph spec
        const graphSpec = {
            layout: {
                title: { text: 'Test Graph' },
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        // This should not throw an error
        await expect(displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1)).resolves.not.toThrow();
    });

    test('displayGraph hides legend for static preview graphs (ratio > 1)', async () => {
        const graphSpec = {
            layout: {
                title: { text: 'SPL Horizontal for Speaker measured by ASR' },
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('SPL Horizontal', 'test.json', 'test-graph', graphSpec, false, 2);

        expect(Plotly.newPlot).toHaveBeenCalled();
        const callArgs = Plotly.newPlot.mock.calls[0];
        const options = callArgs[1];
        expect(options.layout.showlegend).toBe(false);
        expect(options.config.staticPlot).toBe(true);
    });

    test('displayGraph keeps legend for full-size interactive graphs (ratio = 1)', async () => {
        const graphSpec = {
            layout: {
                title: { text: 'SPL Horizontal for Speaker measured by ASR' },
                legend: { x: 1, y: 0.5 },
            },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('SPL Horizontal', 'test.json', 'test-graph', graphSpec, true, 1);

        expect(Plotly.newPlot).toHaveBeenCalled();
        const callArgs = Plotly.newPlot.mock.calls[0];
        const options = callArgs[1];
        // Legend should NOT be hidden for ratio=1 interactive graphs
        expect(options.layout.showlegend).not.toBe(false);
    });

    test('displayGraph registers resize listener for interactive graphs (withConfig=true)', async () => {
        const addEventSpy = vi.spyOn(window, 'addEventListener');

        const graphSpec = {
            layout: { title: { text: 'Test Graph' } },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1);

        const resizeCalls = addEventSpy.mock.calls.filter((c) => c[0] === 'resize');
        expect(resizeCalls.length).toBeGreaterThanOrEqual(1);

        addEventSpy.mockRestore();
    });

    test('displayGraph registers resize and config-change listeners even for static previews', async () => {
        const addEventSpy = vi.spyOn(window, 'addEventListener');

        const graphSpec = {
            layout: { title: { text: 'Test Graph' } },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, false, 2);

        const resizeCalls = addEventSpy.mock.calls.filter((c) => c[0] === 'resize');
        expect(resizeCalls.length).toBeGreaterThanOrEqual(1);

        const configChangeCalls = addEventSpy.mock.calls.filter((c) => c[0] === 'spinorama-config-change');
        expect(configChangeCalls.length).toBeGreaterThanOrEqual(1);

        addEventSpy.mockRestore();
    });

    test('displayGraph recomputes layout on resize with new dimensions', async () => {
        const graphSpec = {
            layout: { title: { text: 'Test Graph' } },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1);

        // Initial call: 1024x768
        expect(setPlotForMeasurement).toHaveBeenCalledWith('On Axis', ['Test Graph'], [graphSpec], 1024, 768, 1);

        // Simulate resize to portrait
        window.innerWidth = 600;
        window.innerHeight = 1000;

        // Trigger the resize handler
        window.dispatchEvent(new window.Event('resize'));

        // Wait for debounce (150ms)
        await new Promise((resolve) => setTimeout(resolve, 200));

        // Should have been called again with new dimensions
        const calls = setPlotForMeasurement.mock.calls;
        const lastCall = calls[calls.length - 1];
        expect(lastCall[3]).toBe(600);
        expect(lastCall[4]).toBe(1000);

        // Plotly.react should have been called for the re-render
        expect(Plotly.react).toHaveBeenCalled();
    });

    test('displayGraph handles target element correctly', async () => {
        // Create a sample graph spec with different data
        const graphSpec = {
            layout: {
                title: { text: 'Different Graph' },
            },
            data: [{ x: [4, 5, 6], y: [4, 5, 6], type: 'scatter' }],
        };

        // Call displayGraph
        await displayGraph('Different Plot', 'different.json', 'test-graph', graphSpec, true, 1);

        // Check if setPlotForMeasurement was called with the new parameters
        expect(setPlotForMeasurement).toHaveBeenCalledWith('Different Plot', ['Different Graph'], [graphSpec], 1024, 768, 1);

        // Check if Plotly.newPlot was called
        expect(Plotly.newPlot).toHaveBeenCalled();
    });

    test('applyConfig is called for all graphs including withConfig=false', async () => {
        const { applyConfig } = await import('./plot-config.js');
        applyConfig.mockClear();

        const graphSpec = {
            layout: { title: { text: 'Static Graph' } },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, false, 2);
        expect(applyConfig).toHaveBeenCalled();
    });

    test('spinorama-config-change event triggers Plotly.react for withConfig=false graphs', async () => {
        Plotly.react.mockClear();

        const graphSpec = {
            layout: { title: { text: 'Static Graph' } },
            data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
        };

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, false, 2);
        Plotly.react.mockClear();

        window.dispatchEvent(new window.CustomEvent('spinorama-config-change'));
        // Allow microtask to process
        await new Promise((resolve) => setTimeout(resolve, 50));
        expect(Plotly.react).toHaveBeenCalled();
    });

    test('initGlobalConfigPanel is called only for withConfig=true', async () => {
        const { initGlobalConfigPanel } = await import('./plot-config.js');
        initGlobalConfigPanel.mockClear();

        const graphSpec = {
            layout: { title: { text: 'Test' } },
            data: [{ x: [1], y: [1], type: 'scatter' }],
        };

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, false, 2);
        expect(initGlobalConfigPanel).not.toHaveBeenCalled();

        await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec, true, 1);
        expect(initGlobalConfigPanel).toHaveBeenCalled();
    });
});
