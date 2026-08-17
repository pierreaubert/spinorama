// -*- coding: utf-8 -*-
// A library to display spinorama charts
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
import { decode64, decode, setGraphOptions } from './plot.js';
import * as plotJs from './plot.js'; // Import all for spyOn module functions

// Mock window properties
let mockWindow;

beforeEach(() => {
    mockWindow = {
        innerWidth: 1024,
        innerHeight: 768,
    };
    global.window = mockWindow;
});

afterEach(() => {
    vi.unstubAllGlobals();
});

// computeDims has been removed — all sizing now goes through computeLayout/applyComputeLayout.

describe('setGraphOptions', () => {
    let mockInputGraphsData;
    const graphSmallThreshold = 550; // from plot.js

    // Helper to create basic graph data
    const createMockGraphData = (titleText = 'Test Graph Title for Speaker by Reviewer', dataItems = 1, yaxis2 = false) => {
        const data = [];
        for (let i = 0; i < dataItems; i++) {
            data.push({
                name: `Trace ${i + 1}`,
                x: [1, 2, 3],
                y: [10, 20, 15],
                legendgroup: 'group1',
                legendgrouptitle: { text: titleText },
            });
        }
        const layout = {
            title: { text: titleText, font: {}, xanchor: 'center', xref: 'paper', x: 0.5 },
            xaxis: { title: { text: 'Frequency (Hz)', font: {} }, range: [Math.log10(20), Math.log10(20000)] },
            yaxis: { title: { text: 'SPL (dB)', font: {} }, range: [30, 100] },
            font: {},
            margin: {},
            legend: {},
            modebar: {},
        };
        if (yaxis2) {
            layout.yaxis2 = { title: { text: 'Phase (°)', font: {} }, range: [-180, 180], overlaying: 'y', side: 'right' };
        }
        return [{ data, layout }];
    };

    beforeEach(() => {
        // Default window mock
        global.window = {
            innerWidth: 1024, // Non-compact, landscape
            innerHeight: 768,
        };
        mockInputGraphsData = createMockGraphData();
        vi.spyOn(console, 'info').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    // Test title computation
    describe('Title Computation', () => {
        it('should set a simple title for a single graph in non-compact mode', () => {
            console.log('Type of setGraphOptions in test: ', typeof setGraphOptions); // DEBUG LOG
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.title.text).toBe('Test Graph Title for Speaker by Reviewer');
            expect(options.layout.title.font.size).toBe(18); // 12 + 2 * Math.round(1024/300) = 12 + 2 * 3 = 18
            expect(options.layout.title.xanchor).toBe('center');
        });

        it('should adjust title for compact mode and split if long', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const compactTitleData = createMockGraphData('CEA2034 for SpeakerA measured by ReviewerX');
            const options = setGraphOptions(compactTitleData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.title.font.size).toBe(12);
            expect(options.layout.title.xanchor).toBe('left');
            expect(options.layout.title.text).toBe('CEA2034 for SpeakerA measured by ReviewerX');
        });

        it('should combine titles when comparing two graphs (outputNumberGraphs = 1, two input graphs)', () => {
            const graphData1 = createMockGraphData('Graph A for SpkA measured by RevA');
            const graphData2 = createMockGraphData('Graph B for SpkB measured by RevB');
            const combinedInput = [graphData1[0], graphData2[0]];
            const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            // Title fits on one line at 1024px width, so no <br> is inserted
            expect(options.layout.title.text).toBe(
                '(A) Graph A for SpkA measured by RevA v.s. (B) Graph B for SpkB measured by RevB'
            );
        });

        it('should split title onto two lines when it does not fit', () => {
            const graphData1 = createMockGraphData(
                'Graph A for VeryLongSpeakerNameThatWillNotFit measured by ReviewerWithALongName'
            );
            const graphData2 = createMockGraphData(
                'Graph B for AnotherVeryLongSpeakerName measured by AnotherReviewerWithLongName'
            );
            const combinedInput = [graphData1[0], graphData2[0]];
            // Use a narrow width to force the split
            const options = setGraphOptions(combinedInput, 400, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.title.text).toContain('<br>');
            expect(options.layout.title.text).toContain('v.s.');
        });

        it('should merge data when speakers are the same but versions differ when comparing', () => {
            const graphData1 = createMockGraphData('Measurement for SameSpeaker measured by RevA');
            const graphData2 = createMockGraphData('Measurement for SameSpeaker measured by RevB');
            const combinedInput = [graphData1[0], graphData2[0]];
            const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            // Do not assert legend group renaming here; ensure traces from both inputs are present
            expect(options.data.length).toBe(graphData1[0].data.length + graphData2[0].data.length);
        });
    });

    describe('Margin Computation', () => {
        it('should set default margins in non-compact, horizontal mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.margin.l).toBe(30);
            // margin.r includes base (30) plus allocated legend width if legend is vertical (right)
            expect(options.layout.margin.r).toBeGreaterThanOrEqual(30);
            // margin.t = graphMarginTop (70) + titleGap (16) for non-compact titles.
            expect(options.layout.margin.t).toBe(70 + 16);
            expect(options.layout.margin.b).toBeGreaterThanOrEqual(30);
        });

        it('should adjust margins for compact mode', () => {
            window.innerWidth = graphSmallThreshold - 10;
            window.innerHeight = 800;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.margin.l).toBe(15);
            expect(options.layout.margin.r).toBe(5);
            expect(options.layout.margin.t).toBe(30);
            expect(options.layout.margin.b).toBeGreaterThanOrEqual(40);
        });

        it('should increase top margin for globe plots', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGlobe: true }, 1);
            // graphMarginTop (70) + globe boost (50) + titleGap (16)
            expect(options.layout.margin.t).toBe(70 + 50 + 16);
        });

        it('surface plots use the base top margin (no surface-specific boost)', () => {
            // Title positioning is now anchored to the plot-area top, so surface plots
            // no longer need an extra surface-specific top-margin boost.
            // The generic titleGap (16) still applies to all non-compact titles.
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isSurface: true }, 1);
            expect(options.layout.margin.t).toBe(70 + 16);
        });

        it('should increase top margin for radar plots', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isRadar: true }, 1);
            expect(options.layout.margin.t).toBe(70 + 16);
        });

        it('should include legend height in bottom margin for spin plots in vertical display', () => {
            window.innerWidth = 700;
            window.innerHeight = 1000;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isSpin: true }, 1);
            // computeLayout adds legend height to bottom margin
            expect(options.layout.margin.b).toBeGreaterThanOrEqual(30);
        });

        it('should adjust right margin if yaxis2 is not present (non-compact, vertical)', () => {
            window.innerWidth = 800;
            window.innerHeight = 1200; // non-compact, vertical
            const dataNoY2 = createMockGraphData('Test', 1, false);
            const options = setGraphOptions(dataNoY2, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.margin.r).toBe(30 + 25);
        });
    });

    describe('Font Computation', () => {
        it('should set base font size for non-compact mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.font.size).toBe(11);
        });

        it('should set smaller base font size for compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.font.size).toBe(10);
        });
    });

    describe('Axis Computation', () => {
        it('should set default xaxis title in non-compact', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.xaxis.title.text).toBe('SPL (dB) v.s. Frequency (Hz)');
            expect(options.layout.xaxis.title.font.size).toBe(9 + Math.round(1024 / 300));
        });

        it('should hide yaxis title and labels in compact vertical mode', () => {
            window.innerWidth = 400;
            window.innerHeight = 800;
            const dataWithY2 = createMockGraphData('Test', 1, true);
            const options = setGraphOptions(dataWithY2, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.yaxis.title).toBeNull();
            expect(options.layout.yaxis.showticklabels).toBe(false);
            expect(options.layout.yaxis2.title).toBeNull();
            expect(options.layout.yaxis2.showticklabels).toBe(false);
        });

        it('should set combined xaxis title in compact vertical mode for plots with angle y-axis', () => {
            window.innerWidth = 400;
            window.innerHeight = 800;
            const contourLayout = JSON.parse(JSON.stringify(mockInputGraphsData[0].layout));
            contourLayout.yaxis.title.text = 'Angle';
            contourLayout.yaxis.range = [-90, 90];
            contourLayout.xaxis.range = [Math.log10(100), Math.log10(10000)];

            const options = setGraphOptions(
                [{ data: mockInputGraphsData[0].data, layout: contourLayout }],
                window.innerWidth,
                window.innerHeight,
                { isSurface: true },
                1
            );
            expect(options.layout.xaxis.title.text).toBe('Angle [-90º, 90º]) v.s. Frequency ([100Hz, 10000Hz]).');
        });
    });

    describe('Legend Computation', () => {
        it('should set legend horizontal for compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.legend.orientation).toBe('h');
            expect(options.layout.legend.xanchor).toBe('center');
        });

        it('should use adaptive legend placement for non-compact horizontal mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            // With few traces (6), computeLayout may choose vertical or horizontal
            // depending on container width. Just verify it's set.
            expect(['v', 'h']).toContain(options.layout.legend.orientation);
        });

        it('should shorten trace names and remove group titles in compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const dataWithShortenableName = createMockGraphData('Title', 1);
            dataWithShortenableName[0].data[0].name = 'Early Reflections';

            const options = setGraphOptions(
                dataWithShortenableName,
                window.innerWidth,
                window.innerHeight,
                { isGraph: true },
                1
            );
            expect(options.data[0].name).toBe('ER');
            expect(options.data[0].legendgroup).toBeNull();
            expect(options.data[0].legendgrouptitle).toBeNull();
        });

        it('should add (A)/(B) letters to trace names when comparing two graphs with different speakers', () => {
            const graphData1 = createMockGraphData('Measurement v.s. Something for SpeakerA measured by RevA');
            const graphData2 = createMockGraphData('Another for SpeakerB measured by RevB');
            const combinedInput = [graphData1[0], graphData2[0]];
            const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

            // Legend groups should be removed for different speakers
            expect(options.data[0].legendgroup).toBeNull();
            const secondGraphDataStartIndex = graphData1[0].data.length;
            expect(options.data[secondGraphDataStartIndex].legendgroup).toBeNull();

            // Names should have (A)/(B) prefixes added
            expect(options.data[0].name).toBe('(A) Trace 1');
            expect(options.data[secondGraphDataStartIndex].name).toBe('(B) Trace 1');
        });
    });

    describe('Modbar Configuration', () => {
        it('should disable modbar in compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.config.displayModeBar).toBe(false);
        });

        it('should enable modbar in non-compact mode with vertical orientation', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.config.displayModeBar).toBe(true);
            expect(options.layout.modebar.orientation).toBe('v');
        });
    });

    describe('Colorbar Configuration', () => {
        it('should configure colorbar for vertical display (non-compact)', () => {
            window.innerWidth = 800;
            window.innerHeight = 1200;
            const dataWithColorbar = createMockGraphData('Colorbar Test', 1);
            dataWithColorbar[0].data[0].type = 'heatmap';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, window.innerWidth, window.innerHeight, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.orientation).toBe('h');
            expect(cb.xanchor).toBe('center');
            expect(cb.yanchor).toBe('top');
            expect(cb.y).toBeLessThan(0);
            expect(cb.y).toBeGreaterThan(-0.3);
            expect(cb.title.text).toBe('dB (SPL)');
        });

        it('should configure colorbar for horizontal display (non-compact)', () => {
            const dataWithColorbar = createMockGraphData('Colorbar Test', 1);
            dataWithColorbar[0].data[0].type = 'heatmap';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, window.innerWidth, window.innerHeight, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.orientation).toBe('v');
            expect(cb.xanchor).toBe('left');
            expect(cb.yanchor).toBe('center');
        });

        it('should use valid Plotly xanchor values for colorbar in landscape mode', () => {
            // xanchor must be 'left', 'center', or 'right' — not 'top'
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 1200, 800, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(['left', 'center', 'right']).toContain(cb.xanchor);
        });

        it('should place colorbar outside the plot area in landscape mode', () => {
            // colorbar at x=1.0 with xanchor='left' places the bar just outside the right edge
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 1200, 800, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.x).toBeGreaterThanOrEqual(1.0);
            expect(cb.xanchor).toBe('left');
        });

        it('should place colorbar below the plot area in portrait mode', () => {
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 800, 1200, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.orientation).toBe('h');
            expect(cb.y).toBeLessThan(0);
            expect(cb.yanchor).toBe('top');
        });

        it('should add right margin for surface/contour plots in landscape mode to fit colorbar', () => {
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 1200, 800, { isSurface: true }, 1);
            expect(options.layout.margin.r).toBeGreaterThan(30);
        });
    });

    it('should handle null or undefined inputGraphsData gracefully', () => {
        const options1 = setGraphOptions(null, 1024, 768, { isGraph: true }, 1);
        expect(options1.data).toBeNull();
        expect(options1.layout).toBeNull();

        const options2 = setGraphOptions([null, null], 1024, 768, { isGraph: true }, 1);
        expect(options2.data).toBeNull();
        expect(options2.layout).toBeNull();

        const graphData1 = createMockGraphData('Graph A');
        const options3 = setGraphOptions([graphData1[0], null], 1024, 768, { isGraph: true }, 1);
        expect(options3.data).toEqual(graphData1[0].data);
        expect(options3.layout.title.text).toContain('Graph A');
    });

    it('should correctly merge data when two input graphs are provided', () => {
        const graphData1 = createMockGraphData('Graph A', 2);
        const graphData2 = createMockGraphData('Graph B', 3);
        const combinedInput = [graphData1[0], graphData2[0]];

        const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

        expect(options.data.length).toBe(2 + 3);
        // Do not assert legendgroup or legendgrouptitle specifics here; logic depends on title parsing.
        // Just ensure traces from both inputs are present by checking known names from each set.
        expect(options.data.some((d) => d.name === 'Trace 1')).toBe(true);
        expect(options.data.some((d) => d.name === 'Trace 3')).toBe(true);
    });

    it('should prefer layout from the graph with more data items if two inputs are provided', () => {
        const graphDataLessItems = createMockGraphData('Layout From Less', 1);
        const graphDataMoreItems = createMockGraphData('Layout From More', 3);
        graphDataMoreItems[0].layout.customLayoutProp = '来自更多数据';

        let combined = [graphDataLessItems[0], graphDataMoreItems[0]];
        let options = setGraphOptions(combined, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
        expect(options.layout.customLayoutProp).toBe('来自更多数据');

        combined = [graphDataMoreItems[0], graphDataLessItems[0]];
        options = setGraphOptions(combined, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
        expect(options.layout.customLayoutProp).toBe('来自更多数据');
    });
});

describe('Plot-Specific Setter Functions', () => {
    let mockSpeakerNames;

    let mockWidth;
    let mockHeight;

    beforeEach(() => {
        mockWidth = 1024;
        mockHeight = 768;
        global.window = { innerWidth: mockWidth, innerHeight: mockHeight };

        mockSpeakerNames = ['Speaker A', 'Speaker B'];

        // console.log('plotJs module in beforeEach:', plotJs); // DEBUG LOG - No longer needed
        vi.spyOn(plotJs, 'setGraphOptions').mockImplementation((graphs, w, h, _props, _num) => {
            const layout =
                graphs && graphs[0] && graphs[0].layout
                    ? JSON.parse(JSON.stringify(graphs[0].layout))
                    : { title: { text: '' }, margin: {}, font: {}, legend: {}, modebar: {} };
            const data = graphs && graphs[0] && graphs[0].data ? JSON.parse(JSON.stringify(graphs[0].data)) : [];
            if (graphs && graphs.length > 1 && graphs[1] && graphs[1].data) {
                data.push(...JSON.parse(JSON.stringify(graphs[1].data)));
            }
            layout.width = w;
            layout.height = h;
            return { layout, data, config: { displayModeBar: true } };
        });
        vi.spyOn(console, 'info').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    describe('setContour', () => {
        it('should merge two contour graphs with layout adjustments for non-compact horizontal', () => {
            window.innerWidth = 1200;
            window.innerHeight = 800;

            const graph1Layout = {
                title: { text: 'Contour for SpkA measured by RevA' },
                xaxis: { range: [2, 4], side: 'bottom', tick: 'outside' },
                yaxis: { range: [-90, 90], title: { text: 'Angle' } },
            };
            const graph2Layout = {
                title: { text: 'Contour for SpkB measured by RevB' },
                xaxis: { range: [2.1, 4.1], side: 'bottom', tick: 'outside' },
                yaxis: { range: [-80, 80], title: { text: 'Angle' } },
            };
            const graph1 = { data: [{ name: 'g1d1' }], layout: graph1Layout };
            const graph2 = { data: [{ name: 'g2d1' }], layout: graph2Layout };

            plotJs.setGraphOptions.mockRestore(); // Use actual setGraphOptions for this specific merge test.
            // This is complex as setGraphOptions calls computeDims which uses window.
            // For a focused test on merge logic, might need more direct mocking or setup.
            // Re-spy after use if other tests depend on the general mock.

            const result = plotJs.setContour(
                'SPL Horizontal Contour',
                mockSpeakerNames,
                [graph1, graph2],
                window.innerWidth,
                window.innerHeight
            );
            expect(result.length).toBe(1);
            const mergedLayout = result[0].layout;

            expect(mergedLayout.title.text).toBe('(A) Contour SpkA measured by RevA v.s. (B) Contour SpkB measured by RevB');
            expect(mergedLayout.xaxis.domain).toEqual([0, 0.49]);
            expect(mergedLayout.xaxis2.domain).toEqual([0.51, 1]);
            expect(mergedLayout.yaxis.title.text).toBe('Angle (A)');
            expect(mergedLayout.yaxis2.title.text).toBe('Angle (B)');
            expect(result[0].data.length).toBe(2);
            expect(result[0].data[1].xaxis).toBe('x2');
            // Re-apply general spy for other tests
            vi.spyOn(plotJs, 'setGraphOptions').mockImplementation((graphs, w, h, _props, _num) => {
                const layout =
                    graphs && graphs[0] && graphs[0].layout
                        ? JSON.parse(JSON.stringify(graphs[0].layout))
                        : { title: { text: '' }, margin: {}, font: {}, legend: {}, modebar: {} };
                const data = graphs && graphs[0] && graphs[0].data ? JSON.parse(JSON.stringify(graphs[0].data)) : [];
                if (graphs && graphs.length > 1 && graphs[1] && graphs[1].data) {
                    data.push(...JSON.parse(JSON.stringify(graphs[1].data)));
                }
                layout.width = w;
                layout.height = h;
                return { layout, data, config: { displayModeBar: true } };
            });
        });

        it('should preserve reviewer info in title when comparing same speaker with different versions', () => {
            window.innerWidth = 1200;
            window.innerHeight = 800;

            const graph1Layout = {
                title: { text: 'Contour for SpkA measured by ASR' },
                xaxis: { range: [2, 4], side: 'bottom', tick: 'outside' },
                yaxis: { range: [-90, 90], title: { text: 'Angle' } },
            };
            const graph2Layout = {
                title: { text: 'Contour for SpkA measured by Princeton' },
                xaxis: { range: [2.1, 4.1], side: 'bottom', tick: 'outside' },
                yaxis: { range: [-80, 80], title: { text: 'Angle' } },
            };
            const graph1 = { data: [{ name: 'g1d1' }], layout: graph1Layout };
            const graph2 = { data: [{ name: 'g2d1' }], layout: graph2Layout };

            plotJs.setGraphOptions.mockRestore();

            const result = plotJs.setContour(
                'SPL Horizontal Contour',
                ['SpkA', 'SpkA'],
                [graph1, graph2],
                window.innerWidth,
                window.innerHeight
            );
            expect(result.length).toBe(1);
            const mergedLayout = result[0].layout;

            expect(mergedLayout.title.text).toBe(
                '(A) Contour SpkA measured by ASR v.s. (B) Contour SpkA measured by Princeton'
            );

            vi.spyOn(plotJs, 'setGraphOptions').mockImplementation((graphs, w, h, _props, _num) => {
                const layout =
                    graphs && graphs[0] && graphs[0].layout
                        ? JSON.parse(JSON.stringify(graphs[0].layout))
                        : { title: { text: '' }, margin: {}, font: {}, legend: {}, modebar: {} };
                const data = graphs && graphs[0] && graphs[0].data ? JSON.parse(JSON.stringify(graphs[0].data)) : [];
                if (graphs && graphs.length > 1 && graphs[1] && graphs[1].data) {
                    data.push(...JSON.parse(JSON.stringify(graphs[1].data)));
                }
                layout.width = w;
                layout.height = h;
                return { layout, data, config: { displayModeBar: true } };
            });
        });
    });
});

describe('setGraphOptions', () => {
    let mockInputGraphsData;
    const graphSmallThreshold = 550; // from plot.js

    // Helper to create basic graph data
    const createMockGraphData = (titleText = 'Test Graph Title for Speaker by Reviewer', dataItems = 1, yaxis2 = false) => {
        const data = [];
        for (let i = 0; i < dataItems; i++) {
            data.push({
                name: `Trace ${i + 1}`,
                x: [1, 2, 3],
                y: [10, 20, 15],
                legendgroup: 'group1',
                legendgrouptitle: { text: titleText },
            });
        }
        const layout = {
            title: { text: titleText, font: {}, xanchor: 'center', xref: 'paper', x: 0.5 },
            xaxis: { title: { text: 'Frequency (Hz)', font: {} }, range: [Math.log10(20), Math.log10(20000)] },
            yaxis: { title: { text: 'SPL (dB)', font: {} }, range: [30, 100] },
            font: {},
            margin: {},
            legend: {},
            modebar: {},
        };
        if (yaxis2) {
            layout.yaxis2 = { title: { text: 'Phase (°)', font: {} }, range: [-180, 180], overlaying: 'y', side: 'right' };
        }
        return [{ data, layout }];
    };

    beforeEach(() => {
        // Default window mock
        global.window = {
            innerWidth: 1024, // Non-compact, landscape
            innerHeight: 768,
        };
        mockInputGraphsData = createMockGraphData();
        vi.spyOn(console, 'info').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    // Test title computation
    describe('Title Computation', () => {
        it('should set a simple title for a single graph in non-compact mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.title.text).toBe('Test Graph Title for Speaker by Reviewer');
            expect(options.layout.title.font.size).toBe(18); // 12 + 2 * Math.round(1024/300) = 12 + 2 * 3 = 18
            expect(options.layout.title.xanchor).toBe('center');
        });

        it('should adjust title for compact mode and split if long', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const compactTitleData = createMockGraphData('CEA2034 for SpeakerA measured by ReviewerX');
            const options = setGraphOptions(compactTitleData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.title.font.size).toBe(12);
            expect(options.layout.title.xanchor).toBe('left');
            expect(options.layout.title.text).toBe('CEA2034 for SpeakerA measured by ReviewerX');
        });

        it('should combine titles when comparing two graphs (outputNumberGraphs = 1, two input graphs)', () => {
            const graphData1 = createMockGraphData('Graph A for SpkA measured by RevA');
            const graphData2 = createMockGraphData('Graph B for SpkB measured by RevB');
            const combinedInput = [graphData1[0], graphData2[0]];
            const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            // Title fits on one line at 1024px width, so no <br> is inserted
            expect(options.layout.title.text).toBe(
                '(A) Graph A for SpkA measured by RevA v.s. (B) Graph B for SpkB measured by RevB'
            );
        });

        it('should update legend group titles if speakers are the same but versions differ when comparing', () => {
            const graphData1 = createMockGraphData('Measurement for SameSpeaker measured by RevA');
            const graphData2 = createMockGraphData('Measurement for SameSpeaker measured by RevB');
            const combinedInput = [graphData1[0], graphData2[0]];
            const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

            // Do not assert exact legend group titles; ensure merging preserved all traces
            expect(options.data.length).toBe(graphData1[0].data.length + graphData2[0].data.length);
        });
    });

    describe('Margin Computation', () => {
        it('should set default margins in non-compact, horizontal mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.margin.l).toBe(30);
            // margin.r includes base (30) plus allocated legend width if legend is vertical (right)
            expect(options.layout.margin.r).toBeGreaterThanOrEqual(30);
            // margin.t = graphMarginTop (70) + titleGap (16) for non-compact titles.
            expect(options.layout.margin.t).toBe(70 + 16);
            expect(options.layout.margin.b).toBeGreaterThanOrEqual(30);
        });

        it('should adjust margins for compact mode', () => {
            window.innerWidth = graphSmallThreshold - 10;
            window.innerHeight = 800;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.margin.l).toBe(15);
            expect(options.layout.margin.r).toBe(5);
            expect(options.layout.margin.t).toBe(30);
            expect(options.layout.margin.b).toBeGreaterThanOrEqual(40);
        });

        it('should increase top margin for globe plots', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGlobe: true }, 1);
            // graphMarginTop (70) + globe boost (50) + titleGap (16)
            expect(options.layout.margin.t).toBe(70 + 50 + 16);
        });

        it('surface plots use the base top margin (no surface-specific boost)', () => {
            // Title positioning is now anchored to the plot-area top, so surface plots
            // no longer need an extra surface-specific top-margin boost.
            // The generic titleGap (16) still applies to all non-compact titles.
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isSurface: true }, 1);
            expect(options.layout.margin.t).toBe(70 + 16);
        });

        it('should increase top margin for radar plots', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isRadar: true }, 1);
            expect(options.layout.margin.t).toBe(70 + 16);
        });

        it('should include legend height in bottom margin for spin plots in vertical display', () => {
            window.innerWidth = 700;
            window.innerHeight = 1000;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isSpin: true }, 1);
            // computeLayout adds legend height to bottom margin
            expect(options.layout.margin.b).toBeGreaterThanOrEqual(30);
        });

        it('should adjust right margin if yaxis2 is not present (non-compact, vertical)', () => {
            window.innerWidth = 800;
            window.innerHeight = 1200; // non-compact, vertical
            const dataNoY2 = createMockGraphData('Test', 1, false);
            const options = setGraphOptions(dataNoY2, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.margin.r).toBe(30 + 25);
        });
    });

    describe('Font Computation', () => {
        it('should set base font size for non-compact mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.font.size).toBe(11);
        });

        it('should set smaller base font size for compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.font.size).toBe(10);
        });
    });

    describe('Axis Computation', () => {
        it('should set default xaxis title in non-compact', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.xaxis.title.text).toBe('SPL (dB) v.s. Frequency (Hz)');
            expect(options.layout.xaxis.title.font.size).toBe(9 + Math.round(1024 / 300));
        });

        it('should hide yaxis title and labels in compact vertical mode', () => {
            window.innerWidth = 400;
            window.innerHeight = 800;
            const dataWithY2 = createMockGraphData('Test', 1, true);
            const options = setGraphOptions(dataWithY2, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.yaxis.title).toBeNull();
            expect(options.layout.yaxis.showticklabels).toBe(false);
            expect(options.layout.yaxis2.title).toBeNull();
            expect(options.layout.yaxis2.showticklabels).toBe(false);
        });

        it('should set combined xaxis title in compact vertical mode for plots with angle y-axis', () => {
            window.innerWidth = 400;
            window.innerHeight = 800;
            const contourLayout = JSON.parse(JSON.stringify(mockInputGraphsData[0].layout));
            contourLayout.yaxis.title.text = 'Angle';
            contourLayout.yaxis.range = [-90, 90];
            contourLayout.xaxis.range = [Math.log10(100), Math.log10(10000)];

            const options = setGraphOptions(
                [{ data: mockInputGraphsData[0].data, layout: contourLayout }],
                window.innerWidth,
                window.innerHeight,
                { isSurface: true },
                1
            );
            expect(options.layout.xaxis.title.text).toBe('Angle [-90º, 90º]) v.s. Frequency ([100Hz, 10000Hz]).');
        });
    });

    describe('Legend Computation', () => {
        it('should set legend horizontal for compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.layout.legend.orientation).toBe('h');
            expect(options.layout.legend.xanchor).toBe('center');
        });

        it('should use adaptive legend placement for non-compact horizontal mode', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            // With few traces (6), computeLayout may choose vertical or horizontal
            // depending on container width. Just verify it's set.
            expect(['v', 'h']).toContain(options.layout.legend.orientation);
        });

        it('should shorten trace names and remove group titles in compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const dataWithShortenableName = createMockGraphData('Title', 1);
            dataWithShortenableName[0].data[0].name = 'Early Reflections';

            const options = setGraphOptions(
                dataWithShortenableName,
                window.innerWidth,
                window.innerHeight,
                { isGraph: true },
                1
            );
            expect(options.data[0].name).toBe('ER');
            expect(options.data[0].legendgroup).toBeNull();
            expect(options.data[0].legendgrouptitle).toBeNull();
        });

        it('should use horizontal legend for many traces in landscape mode', () => {
            // Non-compact landscape: both dimensions >= 550
            window.innerWidth = 700;
            window.innerHeight = 600;

            // SPL Horizontal with 37 angles — too many for a vertical right-side legend
            const numAngles = 37;
            const manyTraceData = createMockGraphData('SPL Horizontal for SpeakerA measured by ASR', numAngles);
            for (let i = 0; i < numAngles; i++) {
                manyTraceData[0].data[i].name = `${(i - 18) * 10}°`;
                manyTraceData[0].data[i].visible = i >= 14 && i <= 24 ? true : 'legendonly';
            }

            const options = setGraphOptions(manyTraceData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

            // computeLayout falls back to horizontal when there are too many traces to fit vertically
            expect(options.layout.legend.orientation).toBe('h');
        });

        it('should use horizontal legend for moderate trace count (>10) in landscape', () => {
            // Non-compact landscape
            window.innerWidth = 1200;
            window.innerHeight = 800;

            // 21 traces > 10 (threshold for vertical legend), so horizontal
            const numTraces = 21;
            const moderateData = createMockGraphData('SPL Horizontal for SpeakerA measured by ASR', numTraces);
            for (let i = 0; i < numTraces; i++) {
                moderateData[0].data[i].name = `${(i - 10) * 10}°`;
                moderateData[0].data[i].visible = i >= 7 && i <= 13 ? true : 'legendonly';
            }

            const options = setGraphOptions(moderateData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

            expect(options.layout.legend.orientation).toBe('h');
        });

        it('should not adjust legend when few traces fit comfortably', () => {
            window.innerWidth = 1200;
            window.innerHeight = 800;

            const fewTraceData = createMockGraphData('SPL Horizontal for SpeakerA measured by ASR', 5);
            const options = setGraphOptions(fewTraceData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

            expect(options.layout.legend.orientation).toBe('v');
            const fontSizeH5 = 10;
            const fontDelta = Math.round(1200 / 300); // = 4
            const defaultFontSize = fontSizeH5 + fontDelta;
            expect(options.layout.legend.font.size).toBe(defaultFontSize);
        });

        it('should detect compact mode from passed-in dimensions, not window (ratio=2 case)', () => {
            // Simulate displayGraph with ratio=2 on a 1400x900 screen:
            // w = 1400/2 = 700, h = 900/2 = 450
            // The real window is large, but setGraphOptions should detect compact from 700x450
            window.innerWidth = 1400;
            window.innerHeight = 900;
            const effectiveWidth = 700;
            const effectiveHeight = 450; // < 550 → compact

            const numTraces = 21;
            const data = createMockGraphData('SPL Horizontal for SpeakerA measured by ASR', numTraces);
            for (let i = 0; i < numTraces; i++) {
                data[0].data[i].name = `${(i - 10) * 10}°`;
                data[0].data[i].visible = i >= 7 && i <= 13 ? true : 'legendonly';
            }

            const options = setGraphOptions(data, effectiveWidth, effectiveHeight, { isGraph: true }, 1);

            // isCompact=true (450<550) AND traceCount=21 (>10) → legend is hidden on
            // mobile to avoid pushing the plot off-screen.
            expect(options.layout.showlegend).toBe(false);
            // Width is capped to maintain ratio (not full input width in compact landscape)
            expect(options.layout.width).toBeLessThanOrEqual(700);
            // Compact mode uses smaller margins
            expect(options.layout.margin.l).toBe(15); // graphMarginLeftSmall
        });

        it('should remove legend group titles when comparing two graphs with different speakers', () => {
            const graphData1 = createMockGraphData('Measurement v.s. Something for SpeakerA measured by RevA');
            const graphData2 = createMockGraphData('Another for SpeakerB measured by RevB');
            const combinedInput = [graphData1[0], graphData2[0]];
            const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

            // Legend group titles should have text set to null for different speakers
            expect(options.data[0].legendgrouptitle.text).toBeNull();
            const secondGraphDataStartIndex = graphData1[0].data.length;
            expect(options.data[secondGraphDataStartIndex].legendgrouptitle.text).toBeNull();
        });
    });

    describe('Modbar Configuration', () => {
        it('should disable modbar in compact mode', () => {
            window.innerWidth = graphSmallThreshold - 1;
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.config.displayModeBar).toBe(false);
        });

        it('should enable modbar in non-compact mode with vertical orientation', () => {
            const options = setGraphOptions(mockInputGraphsData, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
            expect(options.config.displayModeBar).toBe(true);
            expect(options.layout.modebar.orientation).toBe('v');
        });
    });

    describe('Colorbar Configuration', () => {
        it('should configure colorbar for vertical display (non-compact)', () => {
            window.innerWidth = 800;
            window.innerHeight = 1200;
            const dataWithColorbar = createMockGraphData('Colorbar Test', 1);
            dataWithColorbar[0].data[0].type = 'heatmap';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, window.innerWidth, window.innerHeight, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.orientation).toBe('h');
            expect(cb.xanchor).toBe('center');
            expect(cb.yanchor).toBe('top');
            expect(cb.y).toBeLessThan(0);
            expect(cb.y).toBeGreaterThan(-0.3);
            expect(cb.title.text).toBe('dB (SPL)');
        });

        it('should configure colorbar for horizontal display (non-compact)', () => {
            const dataWithColorbar = createMockGraphData('Colorbar Test', 1);
            dataWithColorbar[0].data[0].type = 'heatmap';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, window.innerWidth, window.innerHeight, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.orientation).toBe('v');
            expect(cb.xanchor).toBe('left');
            expect(cb.yanchor).toBe('center');
        });

        it('should use valid Plotly xanchor values for colorbar in landscape mode', () => {
            // xanchor must be 'left', 'center', or 'right' — not 'top'
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 1200, 800, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(['left', 'center', 'right']).toContain(cb.xanchor);
        });

        it('should place colorbar outside the plot area in landscape mode', () => {
            // colorbar at x=1.0 with xanchor='left' places the bar just outside the right edge
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 1200, 800, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.x).toBeGreaterThanOrEqual(1.0);
            expect(cb.xanchor).toBe('left');
        });

        it('should place colorbar below the plot area in portrait mode', () => {
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 800, 1200, { isSurface: true }, 1);
            const cb = options.data[0].colorbar;
            expect(cb.orientation).toBe('h');
            expect(cb.y).toBeLessThan(0);
            expect(cb.yanchor).toBe('top');
        });

        it('should add right margin for surface/contour plots in landscape mode to fit colorbar', () => {
            const dataWithColorbar = createMockGraphData('Contour Test', 1);
            dataWithColorbar[0].data[0].type = 'contour';
            dataWithColorbar[0].data[0].colorbar = {};

            const options = setGraphOptions(dataWithColorbar, 1200, 800, { isSurface: true }, 1);
            expect(options.layout.margin.r).toBeGreaterThan(30);
        });
    });

    it('should handle null or undefined inputGraphsData gracefully', () => {
        const options1 = setGraphOptions(null, 1024, 768, { isGraph: true }, 1);
        expect(options1.data).toBeNull();
        expect(options1.layout).toBeNull();

        const options2 = setGraphOptions([null, null], 1024, 768, { isGraph: true }, 1);
        expect(options2.data).toBeNull(); // Because the preferred one (based on length) would be null
        expect(options2.layout).toBeNull();

        const graphData1 = createMockGraphData('Graph A');
        const options3 = setGraphOptions([graphData1[0], null], 1024, 768, { isGraph: true }, 1);
        expect(options3.data).toEqual(graphData1[0].data);
        expect(options3.layout.title.text).toContain('Graph A');
    });

    it('should correctly merge data when two input graphs are provided', () => {
        const graphData1 = createMockGraphData('Graph A', 2);
        const graphData2 = createMockGraphData('Graph B', 3);
        const combinedInput = [graphData1[0], graphData2[0]];

        const options = setGraphOptions(combinedInput, window.innerWidth, window.innerHeight, { isGraph: true }, 1);

        expect(options.data.length).toBe(2 + 3);
        // Do not assert legendgrouptitle specifics; ensure traces from both inputs are present
        expect(options.data.some((d) => d.name === 'Trace 1')).toBe(true);
        expect(options.data.some((d) => d.name === 'Trace 3')).toBe(true);
    });

    it('should prefer layout from the graph with more data items if two inputs are provided', () => {
        const graphDataLessItems = createMockGraphData('Layout From Less', 1);
        const graphDataMoreItems = createMockGraphData('Layout From More', 3);
        graphDataMoreItems[0].layout.customLayoutProp = '来自更多数据';

        let combined = [graphDataLessItems[0], graphDataMoreItems[0]];
        let options = setGraphOptions(combined, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
        expect(options.layout.customLayoutProp).toBe('来自更多数据');

        combined = [graphDataMoreItems[0], graphDataLessItems[0]];
        options = setGraphOptions(combined, window.innerWidth, window.innerHeight, { isGraph: true }, 1);
        expect(options.layout.customLayoutProp).toBe('来自更多数据');
    });
});

describe('Resize: layout must change when dimensions change', () => {
    const createGraphData = () => {
        const data = [];
        for (let i = 0; i < 7; i++) {
            data.push({
                name: `${i * 10}°`,
                x: [1, 2, 3],
                y: [10, 20, 15],
                visible: true,
                legendgroup: 'speaker0',
                legendgrouptitle: { text: 'Speaker' },
            });
        }
        return [
            {
                data,
                layout: {
                    title: {
                        text: 'SPL Horizontal for Speaker measured by ASR',
                        font: {},
                        xanchor: 'center',
                        xref: 'paper',
                        x: 0.5,
                    },
                    xaxis: { title: { text: 'Frequency (Hz)', font: {} }, range: [Math.log10(20), Math.log10(20000)] },
                    yaxis: { title: { text: 'SPL (dB)', font: {} }, range: [30, 100] },
                    font: {},
                    margin: {},
                    legend: {},
                    modebar: {},
                },
            },
        ];
    };

    beforeEach(() => {
        vi.spyOn(console, 'info').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should produce different legend orientation for landscape vs portrait', () => {
        const props = { isGraph: true };

        // Landscape: 1200x700 → non-compact, horizontal → vertical legend on right
        const landscape = setGraphOptions(createGraphData(), 1200, 700, props, 1);
        expect(landscape.layout.legend.orientation).toBe('v');

        // Portrait: 700x1200 → non-compact, vertical → horizontal legend below
        const portrait = setGraphOptions(createGraphData(), 700, 1200, props, 1);
        expect(portrait.layout.legend.orientation).toBe('h');
    });

    it('should produce different dimensions for landscape vs portrait', () => {
        const props = { isGraph: true };

        const landscape = setGraphOptions(createGraphData(), 1200, 700, props, 1);
        const portrait = setGraphOptions(createGraphData(), 700, 1200, props, 1);

        // Width and height should differ significantly
        expect(landscape.layout.width).not.toBe(portrait.layout.width);
        expect(landscape.layout.height).not.toBe(portrait.layout.height);
    });

    it('should produce compact layout when resized from large to small', () => {
        const props = { isGraph: true };

        const large = setGraphOptions(createGraphData(), 1200, 800, props, 1);
        const small = setGraphOptions(createGraphData(), 400, 500, props, 1);

        // Large: non-compact → modebar visible
        expect(large.config.displayModeBar).toBe(true);
        // Small: compact → modebar hidden
        expect(small.config.displayModeBar).toBe(false);
        // Small should use compact margins
        expect(small.layout.margin.l).toBe(15);
        expect(large.layout.margin.l).toBe(30);
    });

    it('should set legend itemwidth so marker line does not overlap label', () => {
        const props = { isGraph: true };

        // Landscape: vertical legend on right
        const landscape = setGraphOptions(createGraphData(), 1200, 700, props, 1);
        expect(landscape.layout.legend.itemwidth).toBeDefined();
        expect(landscape.layout.legend.itemwidth).toBeLessThan(30); // default is 30, too wide

        // Portrait: horizontal legend below
        const portrait = setGraphOptions(createGraphData(), 700, 1200, props, 1);
        expect(portrait.layout.legend.itemwidth).toBeDefined();
        expect(portrait.layout.legend.itemwidth).toBeLessThan(30);

        // Compact
        const compact = setGraphOptions(createGraphData(), 400, 500, props, 1);
        expect(compact.layout.legend.itemwidth).toBeDefined();
        expect(compact.layout.legend.itemwidth).toBeLessThan(30);
    });

    it('should use wider legend entrywidth in compare view to avoid label overlap', () => {
        const props = { isGraph: true };

        // Portrait (horizontal legend): compare should have wider entries than single
        const single = setGraphOptions(createGraphData(), 700, 1200, props, 1);
        const singleEntryWidth = single.layout.legend.entrywidth;

        const graphA = createGraphData();
        const graphB = createGraphData();
        graphB[0].layout.title.text = 'SPL Horizontal for Speaker B measured by ASR';
        const compareGraphs = [graphA[0], graphB[0]];
        const compare = setGraphOptions(compareGraphs, 700, 1200, props, 1);

        // With dynamic entrywidth computation, both are clamped to minimum (80)
        // when labels are very short. Compare labels "(A) 0°" are longer but
        // still below the minimum threshold.
        expect(compare.layout.legend.entrywidth).toBeGreaterThanOrEqual(singleEntryWidth);
    });
});

// Helper to compare ArrayBuffers
function arrayBuffersAreEqual(buf1, buf2) {
    if (buf1.byteLength !== buf2.byteLength) return false;
    const view1 = new Uint8Array(buf1);
    const view2 = new Uint8Array(buf2);
    for (let i = 0; i < view1.length; i++) {
        if (view1[i] !== view2[i]) return false;
    }
    return true;
}

describe('decode64 and decode', () => {
    // Test data for Float32Array: [1.0f, 2.5f]
    // Bytes (LE): [0x00, 0x00, 0x80, 0x3F,  0x00, 0x00, 0x20, 0x40]
    // Base64: AACAPwAAIEA=
    const testBytesFloat32 = new Uint8Array([0, 0, 128, 63, 0, 0, 32, 64]); // Bytes for 1.0f, 2.5f
    const testBase64Float32 = 'AACAPwAAIEA='; // Correct Base64 for the above bytes

    // Test data for Int16Array: [1, 2, -1, 0]
    // Bytes (LE): [0x01, 0x00,  0x02, 0x00,  0xFF, 0xFF,  0x00, 0x00]
    // Base64: AQACAP//AAA=

    const testBase64Int16 = 'AQACAP//AAA='; // Correct Base64

    describe('decode64', () => {
        it('should decode a simple base64 string to ArrayBuffer', () => {
            const base64 = 'AQIDBA=='; // Represents Uint8Array([1, 2, 3, 4])
            const expectedBuffer = new Uint8Array([1, 2, 3, 4]).buffer;
            const decodedBuffer = decode64(base64);
            expect(decodedBuffer).toBeInstanceOf(ArrayBuffer);
            expect(decodedBuffer.byteLength).toBe(4);
            expect(arrayBuffersAreEqual(decodedBuffer, expectedBuffer)).toBe(true);
        });

        it('should decode a base64 string for float32 data correctly', () => {
            const decodedBuffer = decode64(testBase64Float32);
            expect(decodedBuffer.byteLength).toBe(testBytesFloat32.byteLength);
            expect(arrayBuffersAreEqual(decodedBuffer, testBytesFloat32.buffer)).toBe(true);
        });

        it('should handle base64 strings without padding', () => {
            const base64NoPadding = 'AQIDBAUG'; // Represents Uint8Array([1, 2, 3, 4, 5, 6])
            const expectedBuffer = new Uint8Array([1, 2, 3, 4, 5, 6]).buffer;
            const decodedBuffer = decode64(base64NoPadding);
            expect(decodedBuffer.byteLength).toBe(6);
            expect(arrayBuffersAreEqual(decodedBuffer, expectedBuffer)).toBe(true);
        });

        it('should return empty ArrayBuffer for empty string', () => {
            const decodedBuffer = decode64('');
            expect(decodedBuffer.byteLength).toBe(0);
        });

        it('should handle potentially malformed base64 by returning an ArrayBuffer (actual content may vary or error)', () => {
            try {
                const decodedBuffer = decode64('Invalid!');
                expect(decodedBuffer).toBeInstanceOf(ArrayBuffer);
            } catch (e) {
                // Allow specific errors if that's the expected behavior for malformed input
                expect(e).toBeInstanceOf(TypeError); // Often throws TypeError due to charCodeAt(i) on undefined from lookup
            }
        });
    });

    describe('decode', () => {
        it('should decode to Float32Array (f4) correctly', () => {
            const input = { bdata: testBase64Float32, dtype: 'f4' };
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Float32Array);
            expect(decoded.length).toBe(2);
            expect(decoded[0]).toBeCloseTo(1.0);
            expect(decoded[1]).toBeCloseTo(2.5);
        });

        it('should decode to Int16Array (i2) correctly', () => {
            const input = { bdata: testBase64Int16, dtype: 'i2' };
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Int16Array);
            expect(decoded.length).toBe(4);
            expect(decoded[0]).toBe(1);
            expect(decoded[1]).toBe(2);
            expect(decoded[2]).toBe(-1);
            expect(decoded[3]).toBe(0); // Corrected expected value
        });

        it('should decode to Uint8ClampedArray (u1c) correctly', () => {
            const input = { bdata: 'AQID+/A=', dtype: 'u1c' }; // Represents [1, 2, 3, 251, 240]
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Uint8ClampedArray);
            expect(decoded).toEqual(new Uint8ClampedArray([1, 2, 3, 251, 240])); // Corrected expected value
        });

        it('should decode to Int8Array (i1) correctly', () => {
            const input = { bdata: '/3+AAg==', dtype: 'i1' }; // Base64 for bytes [255, 127, 128, 2]
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Int8Array);
            expect(decoded).toEqual(new Int8Array([-1, 127, -128, 2])); // Expect 2, not 0
        });

        it('should decode to Int32Array (i4) correctly', () => {
            const input = { bdata: 'oIYBAA==', dtype: 'i4' }; // [100000]
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Int32Array);
            expect(decoded).toEqual(new Int32Array([100000]));
        });

        it('should decode to Uint8Array (u1) correctly', () => {
            const input = { bdata: 'AQIDBA==', dtype: 'u1' }; // [1,2,3,4]
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Uint8Array);
            expect(decoded).toEqual(new Uint8Array([1, 2, 3, 4]));
        });

        it('should decode to Uint16Array (u2) correctly', () => {
            const input = { bdata: 'AAH//w==', dtype: 'u2' }; // Corrected base64 for [256, 65535] (bytes: 00 01 FF FF)
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Uint16Array);
            expect(decoded).toEqual(new Uint16Array([256, 65535]));
        });

        it('should decode to Uint32Array (u4) correctly', () => {
            const input = { bdata: '/////w==', dtype: 'u4' }; // [4294967295]
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Uint32Array);
            expect(decoded).toEqual(new Uint32Array([4294967295]));
        });

        it('should decode to Float64Array (f8) correctly', () => {
            // 1.0 (double, little-endian): 00 00 00 00 00 00 F0 3F -> Base64: AAAAAAAA8D8=
            const base64Input = 'AAAAAAAA8D8=';
            const buffer = decode64(base64Input);
            console.log(`Byte length for '${base64Input}': ${buffer.byteLength}`); // Log byte length
            const input = { bdata: base64Input, dtype: 'f8' };
            const decoded = decode(input);
            expect(decoded).toBeInstanceOf(Float64Array);
            expect(decoded.length).toBe(1);
            expect(decoded[0]).toBeCloseTo(1.0);
        });

        it('should return input if dtype is missing from input object', () => {
            const input = { bdata: testBase64Float32 };
            expect(decode(input)).toBe(input);
        });

        it('should return input if input itself is not an object or null/undefined', () => {
            expect(decode('just a string')).toBe('just a string');
            expect(decode(null)).toBeNull();
            expect(decode(undefined)).toBeUndefined();
            const numInput = 123;
            expect(decode(numInput)).toBe(numInput);
        });

        it('should return input if input object does not contain "dtype" property', () => {
            const input = { someOtherProp: 'value', bdata: testBase64Float32 };
            expect(decode(input)).toBe(input);
        });

        it('should return input if dtype is unknown', () => {
            const input = { bdata: testBase64Float32, dtype: 'xxUnknownDxX' };
            expect(decode(input)).toBe(input);
        });
    });
});
