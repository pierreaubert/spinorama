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

// **********************************************************************
// *** WARNING DO NOT TOUCH THE MARGINS AND LEGEND LOGIC, DO NOT      ***
// *** CHANGE THE THE SIZE OF THE FONT                                ***
// *** WHY: plotly has a hard time to resize things properly and make ***
// *** very brittle!                                                  ***
// **********************************************************************

// const flags_Contour_Delta = false;

// Measure title text width using canvas measureText and decide if it needs line-breaking.
// Returns true when the plain text (HTML tags stripped) fits within maxWidth
// at the given fontSize using Plotly's default font ("Open Sans", sans-serif).
// Falls back to a rough character-based estimate when canvas is unavailable (e.g. tests).
let _measureCtx = null;
function titleFitsOnOneLine(text, fontSize, maxWidth) {
    const plain = text.replace(/<br\s*\/?>/gi, ' ');
    try {
        if (!_measureCtx) {
            _measureCtx = document.createElement('canvas').getContext('2d');
        }
        _measureCtx.font = fontSize + 'px "Open Sans", sans-serif';
        return _measureCtx.measureText(plain).width <= maxWidth;
    } catch (_) {
        // canvas unavailable (test environment) — rough fallback
        return plain.length * fontSize * 0.55 <= maxWidth;
    }
}

export const knownMeasurements = [
    'CEA2034',
    'CEA2034 Normalized',
    'On Axis',
    'Estimated In-Room Response',
    'Early Reflections',
    'Horizontal Reflections',
    'Vertical Reflections',
    'SPL Horizontal',
    'SPL Horizontal Normalized',
    'SPL Vertical',
    'SPL Vertical Normalized',
    'SPL Horizontal Contour',
    'SPL Horizontal Contour Normalized',
    'SPL Vertical Contour',
    'SPL Vertical Contour Normalized',
    'SPL Horizontal Contour 3D',
    'SPL Horizontal Contour Normalized 3D',
    'SPL Vertical Contour 3D',
    'SPL Vertical Contour Normalized 3D',
    'SPL Horizontal Globe',
    'SPL Horizontal Globe Normalized',
    'SPL Vertical Globe',
    'SPL Vertical Globe Normalized',
    'SPL Horizontal Radar',
    'SPL Vertical Radar',
];

const contourMin = -30;
const contourMax = 3;
const contourColorscale = [
    [0, 'rgb(0,0,168)'],
    [0.1, 'rgb(0,0,200)'],
    [0.2, 'rgb(0,74,255)'],
    [0.3, 'rgb(0,152,255)'],
    [0.4, 'rgb(74,255,161)'],
    [0.5, 'rgb(161,255,74)'],
    [0.6, 'rgb(255,255,0)'],
    [0.7, 'rgb(234,159,0)'],
    [0.8, 'rgb(255,74,0)'],
    [0.9, 'rgb(222,74,0)'],
    [1, 'rgb(253,14,13)'],
];

export const labelShort = {
    // regression
    'Linear Regression': 'Reg',
    'Band ±1.5dB': '±1.5dB',
    'Band ±3dB': '±3dB',
    // PIR
    'Estimated In-Room Response': 'PIR',
    // spin
    'On Axis': 'ON',
    'Listening Window': 'LW',
    'Early Reflections': 'ER',
    'Sound Power': 'SP',
    'Early Reflections DI': 'ERDI',
    'Sound Power DI': 'SPDI',
    // Bounce
    'Ceiling Bounce': 'CB',
    'Floor Bounce': 'FB',
    'Front Wall Bounce': 'FWB',
    'Rear Wall Bounce': 'RWB',
    'Side Wall Bounce': 'SWB',
    // Reflection
    'Ceiling Reflection': 'CR',
    'Floor Reflection': 'FR',
    //
    Front: 'F',
    Rear: 'R',
    Side: 'S',
    //
    'Total Early Reflection': 'TER',
    'Total Horizontal Reflection': 'THR',
    'Total Vertical Reflection': 'TVR',
};

export const labelLong = Object.entries(labelShort).reduce((obj, [k, v]) => {
    obj[v] = k;
    return obj;
}, {});

const graphSmall = 550;

const graphRatio = 1.8;
// Contour plots (frequency × angle): wider than tall since frequency spans ~3 decades
// on a log axis while angle spans 360°. Value matches the visual appearance of the
// old computeDims-based sizing (~1.5-1.6 at typical viewport sizes).
const contourRatio = 1.6;
const squareRatio = 1.0;

const graphMarginLeft = 30;
const graphMarginRight = 30;
const graphMarginTop = 70;
const graphMarginBottom = 30;

const graphMarginLeftSmall = 15;
const graphMarginRightSmall = 5;
const graphMarginTopSmall = 30;
const graphMarginBottomSmall = 40;

const fontSizeH3 = 12;
const fontSizeH4 = 11;
const fontSizeH5 = 10;
const fontSizeH6 = 9;

export function estimateLegendSize(traceNames, fontSize, orientation, entryWidth, availableWidth) {
    const count = traceNames.length;
    const lineHeight = fontSize * 1.6;
    if (orientation === 'v') {
        return {
            width: entryWidth,
            height: count * lineHeight,
            columns: 1,
            rows: count,
        };
    }
    const columns = Math.max(1, Math.floor(availableWidth / entryWidth));
    const rows = Math.ceil(count / columns);
    return {
        width: availableWidth,
        height: rows * lineHeight,
        columns,
        rows,
    };
}

export function shouldUseShortLabels(traceNames, graphWidth, graphHeight, isCompact, isVertical, targetRatio, userLabelConfig) {
    if (userLabelConfig === 'long') return false;
    if (userLabelConfig === 'short') return true;
    if (isCompact) return true;

    // Estimate legend with long labels and check ratio deviation
    const fontSize = 10;
    const charWidth = fontSize * 0.6;
    const maxLen = Math.max(...traceNames.map((n) => n.length));
    const entryWidth = maxLen * charWidth + 30;

    // Compare ratio with long labels vs short labels
    // If long labels make the ratio significantly worse, use short labels
    const shortCharWidth = fontSize * 0.6;
    const shortMaxLen = Math.max(...traceNames.map((n) => (labelShort[n] || n).length));
    const shortEntryWidth = shortMaxLen * shortCharWidth + 30;

    if (isVertical) {
        // Horizontal legend below graph: takes height from plot area
        const longLegend = estimateLegendSize(traceNames, fontSize, 'h', entryWidth, graphWidth);
        const shortLegend = estimateLegendSize(traceNames, fontSize, 'h', shortEntryWidth, graphWidth);
        const longRatio = graphWidth / Math.max(1, graphHeight - longLegend.height);
        const shortRatio = graphWidth / Math.max(1, graphHeight - shortLegend.height);
        const longDev = Math.abs(longRatio - targetRatio) / targetRatio;
        const shortDev = Math.abs(shortRatio - targetRatio) / targetRatio;
        return longDev > 0.15 && longDev > shortDev + 0.05;
    }
    // Horizontal display with vertical legend on right: takes width from plot area
    const longLegend = estimateLegendSize(traceNames, fontSize, 'v', entryWidth, graphWidth);
    const shortLegend = estimateLegendSize(traceNames, fontSize, 'v', shortEntryWidth, graphWidth);
    const longRatio = Math.max(1, graphWidth - longLegend.width) / graphHeight;
    const shortRatio = Math.max(1, graphWidth - shortLegend.width) / graphHeight;
    const longDev = Math.abs(longRatio - targetRatio) / targetRatio;
    const shortDev = Math.abs(shortRatio - targetRatio) / targetRatio;
    return longDev > 0.15 && longDev > shortDev + 0.05;
}

export function isDisplayVertical() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    return windowWidth <= windowHeight;
}

export function isDisplayCompact() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    return windowWidth < graphSmall || windowHeight < graphSmall;
}

// Compute graph layout with guaranteed plot-area aspect ratio.
// The plot area (data region inside axes) always satisfies plotAreaH = plotAreaW / ratio.
// Legend and margins are additive — they never reduce the plot area dimensions.
//
// Algorithm (3 passes):
//   1. Pick base margins (before legend).
//   2. Decide legend strategy — vertical (right) or horizontal (bottom) — and how much
//      space it needs. Scale font down to 8px if needed to reduce legend height.
//   3. Add legend space to the appropriate margin, compute plotW from the reduced width,
//      enforce plotH = plotW / ratio, return total width/height and legend config.
export function computeLayout(containerWidth, isVertical, isCompact, graphProps, traceCount, maxLabelLen, hasYaxis2, ratio, fontDelta) {
    const minFont = 8;
    const baseFont = isCompact ? fontSizeH5 : fontSizeH5 + fontDelta;
    const isPolar = graphProps.isRadar || graphProps.isGlobe;

    // --- Pass 1: Base margins (before legend allocation) ---
    let margin;
    if (isCompact) {
        margin = { l: graphMarginLeftSmall, r: graphMarginRightSmall, t: graphMarginTopSmall, b: graphMarginBottomSmall };
    } else {
        // Right margin: add 25px if no yaxis2 (to leave room for the right tick labels when mirrored).
        // Polar plots don't have a yaxis2 tick margin concept, so skip the offset.
        const offsetR = isPolar || hasYaxis2 ? 0 : 25;
        margin = {
            l: graphMarginLeft,
            r: graphMarginRight + offsetR,
            t: graphMarginTop,
            b: graphMarginBottom,
        };
        if (graphProps.isSurface && !isVertical) margin.r += 60;
        if (graphProps.isGlobe) margin.t += 50;
        if (graphProps.isSurface) margin.t += 20;
    }

    // --- Pass 2: Decide legend strategy and compute its footprint ---
    // Surface/radar/globe hide the legend entirely (they use colorbars or have
    // no trace-based legend to show).
    let legend;
    if (graphProps.isSurface || isPolar) {
        legend = { orientation: 'h', font: baseFont, height: 0, width: 0, entryWidth: 0, hidden: true };
    } else if (traceCount === 0) {
        legend = { orientation: 'h', font: baseFont, height: 0, width: 0, entryWidth: 0 };
    } else if (isCompact || isVertical) {
        // Compact or portrait: horizontal legend below the plot.
        // Scale font down to 8px if legend would be too tall (>60% of plot height).
        const plotAreaW_avail = containerWidth - margin.l - margin.r;
        let font = baseFont;
        let legendH = 0;
        let entryW = 60;
        while (font >= minFont) {
            entryW = Math.max(60, maxLabelLen * font * 0.6 + 50);
            const cols = Math.max(1, Math.floor(plotAreaW_avail / entryW));
            const rows = Math.ceil(traceCount / cols);
            legendH = rows * font * 1.8 + 10;
            const plotAreaH = plotAreaW_avail / ratio;
            if (legendH <= plotAreaH * 0.6 || font <= minFont) break;
            font -= 1;
        }
        legend = { orientation: 'h', font, height: legendH, width: 0, entryWidth: entryW };
    } else {
        // Landscape: try vertical (right) legend first. Fall back to horizontal if it won't fit
        // or if there are too many traces for a vertical legend.
        // Width per entry: icon marker (~24px) + label text (maxLabelLen * 0.6 * fontSize)
        //                  + left/right padding (~16px). Capped at 280px so very long
        //                  labels don't starve the plot area; labels longer than that
        //                  will be truncated by Plotly (rare — SPL-style names fit).
        const legendW = Math.min(Math.max(80, maxLabelLen * baseFont * 0.62 + 40), 280);
        const plotAreaW_rightLegend = containerWidth - margin.l - margin.r - legendW;
        const plotAreaH_rightLegend = plotAreaW_rightLegend / ratio;
        const legendH_needed = traceCount * baseFont * 1.6 + 10;

        const canFitVertical =
            traceCount > 0 &&
            traceCount <= 10 &&
            plotAreaW_rightLegend >= 300 &&
            legendH_needed <= plotAreaH_rightLegend * 0.95;

        if (canFitVertical) {
            legend = { orientation: 'v', font: baseFont, height: legendH_needed, width: legendW, entryWidth: legendW };
        } else {
            // Horizontal (bottom) legend with font scaling.
            const plotAreaW_avail = containerWidth - margin.l - margin.r;
            let font = baseFont;
            let legendH = 0;
            let entryW = 60;
            while (font >= minFont) {
                entryW = Math.max(60, maxLabelLen * font * 0.6 + 50);
                const cols = Math.max(1, Math.floor(plotAreaW_avail / entryW));
                const rows = Math.ceil(traceCount / cols);
                legendH = rows * font * 1.8 + 10;
                const plotAreaH = plotAreaW_avail / ratio;
                if (legendH <= plotAreaH * 0.5 || font <= minFont) break;
                font -= 1;
            }
            legend = { orientation: 'h', font, height: legendH, width: 0, entryWidth: entryW };
        }
    }

    // --- Pass 3: Allocate legend/title space into margins, then compute dimensions ---
    // Small padding between plot elements (in pixels).
    const legendPad = 8;

    // Reserve space for the x-axis title, which Plotly draws inside margin.b.
    // Polar plots (radar/globe) don't have an x-axis title, so skip this.
    if (!isPolar) {
        // In compact-vertical mode the title is a long descriptive string (~55 chars at fontSizeH6)
        // that may wrap to 2 lines at narrow widths. In other modes it's a short 1-line title.
        const xTitleFont = fontSizeH6 + fontDelta;
        const xTitleLineH = xTitleFont * 1.4;
        const xTitleH = (isCompact && isVertical) ? (xTitleLineH * 2 + 6) : (xTitleLineH + 6);
        margin.b += xTitleH;
    }

    if (!legend.hidden && legend.height > 0) {
        if (legend.orientation === 'v') {
            margin.r += legend.width + legendPad;
        } else {
            margin.b += legend.height + legendPad;
        }
    }

    // For square-ratio plots (radar/globe) in a landscape container, we'd otherwise
    // get an extremely wide plot area. Cap the plot width so the square plot area is
    // not unreasonably large (use the smaller of containerWidth and available height-based width).
    let plotAreaW = Math.max(1, containerWidth - margin.l - margin.r);
    if (Math.abs(ratio - 1.0) < 0.01) {
        // Square plot: the caller usually passes a containerWidth from the DOM, and
        // we keep the square sized to the width. This yields a tall plot in landscape
        // viewports — same as before.
    }
    const plotAreaH = plotAreaW / ratio;
    const totalW = containerWidth;
    const totalH = plotAreaH + margin.t + margin.b;

    return {
        width: totalW,
        height: totalH,
        margin: margin,
        legend: legend,
        plotArea: { w: plotAreaW, h: plotAreaH },
    };
}

const GraphProperties = Object.freeze({
    CEA2034: {
        isGraph: true,
        isSpin: true,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'CEA2034 Normalized': {
        isGraph: true,
        isSpin: true,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'On Axis': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'Estimated In-Room Response': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'Early Reflections': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'Horizontal Reflections': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'Vertical Reflections': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'SPL Horizontal': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'SPL Horizontal Normalized': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'SPL Vertical': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'SPL Vertical Normalized': {
        isGraph: true,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: false,
    },
    'SPL Horizontal Contour': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Horizontal Contour Normalized': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Vertical Contour': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Vertical Contour Normalized': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Horizontal Contour 3D': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Horizontal Contour Normalized 3D': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Vertical Contour 3D': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Vertical Contour Normalized 3D': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
        isGlobe: false,
    },
    'SPL Horizontal Globe': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: true,
    },
    'SPL Horizontal Globe Normalized': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: true,
    },
    'SPL Vertical Globe': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: true,
    },
    'SPL Vertical Globe Normalized': {
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: false,
        isGlobe: true,
    },
    'SPL Horizontal Radar': {
        isGraph: false,
        isSpin: false,
        isRadar: true,
        isSurface: false,
        isGlobe: false,
    },
    'SPL Vertical Radar': {
        isGraph: false,
        isSpin: false,
        isRadar: true,
        isSurface: false,
        isGlobe: false,
    },
});

export function setGraphOptions(inputGraphsData, windowWidth, windowHeight, outputGraphProperties, outputNumberGraphs) {
    let datas = null;
    let layout = null;
    let config = null;

    if (!inputGraphsData || inputGraphsData.length === 0) {
        return { data: null, layout: null, config: null };
    }

    // console.log('layout and data: ' + inputGraphsData.length + ' w=' + windowWidth + ' h=' + windowHeight);
    if (inputGraphsData.length === 1) {
        if (!inputGraphsData[0]) {
            // Handle if the single item itself is null/undefined
            return { data: null, layout: null, config: null };
        }
        layout = inputGraphsData[0].layout;
        datas = inputGraphsData[0].data;
    } else if (inputGraphsData.length === 2) {
        const graph1 = inputGraphsData[0];
        const graph2 = inputGraphsData[1];

        if (graph1 && graph1.data && graph1.layout && graph2 && graph2.data && graph2.layout) {
            let best = 0;
            const len0 = graph1.data.length; // Already checked graph1.data
            const len1 = graph2.data.length; // Already checked graph2.data
            if (len1 > len0) {
                best = 1;
            }
            layout = inputGraphsData[best].layout;
            datas = graph1.data.concat(graph2.data);
        } else if (graph1 && graph1.data && graph1.layout) {
            layout = graph1.layout;
            datas = graph1.data;
        } else if (graph2 && graph2.data && graph2.layout) {
            layout = graph2.layout;
            datas = graph2.data;
        } else {
            // Both are null or malformed
            return { data: null, layout: null, config: null };
        }
    }

    // Set zorder: grid (default 0) -> bands (-2) -> band lines (-1) -> SPL curves (1)
    if (datas != null) {
        for (let k = 0; k < datas.length; k++) {
            const trace = datas[k];
            if (trace.fill) {
                trace.zorder = -2;
            } else if (trace.name && (trace.name.indexOf('Midrange') !== -1 || trace.name.indexOf('Linear') !== -1 || trace.name.indexOf('Reg') !== -1)) {
                trace.zorder = -1;
            } else {
                trace.zorder = 1;
            }
        }
    }

    // If after the above logic, layout or datas are still null (e.g. inputGraphsData had unexpected structure)
    if (layout === null || datas === null) {
        console.log('Error: No valid graph data to process in setGraphOptions');
        return { data: null, layout: null, config: null };
    }

    const isVertical = windowWidth <= windowHeight;
    const isCompact = windowWidth < graphSmall || windowHeight < graphSmall;

    let fontDelta = 0;
    if (!isCompact) {
        fontDelta = Math.round(windowWidth / 300);
    }

    function computeXaxis() {
        if (layout.xaxis && layout.xaxis.title) {
            layout.xaxis.title.text = 'SPL (dB) v.s. Frequency (Hz)';
            layout.xaxis.title.font = {
                size: fontSizeH6 + fontDelta,
                color: '#000',
            };
            layout.xaxis.automargin = 'height';
            layout.xaxis.side = 'bottom';
        }
        // For log-scale frequency axes, add minor grid lines at the 2..9 subticks
        // of each decade so the log scale is easier to read. applyConfig() assigns
        // theme-appropriate colors.
        if (layout.xaxis && layout.xaxis.type === 'log') {
            layout.xaxis.minor = {
                dtick: 'D1',
                ticks: layout.xaxis.ticks || 'inside',
                ticklen: 2,
                showgrid: true,
                gridcolor: 'rgba(0,0,0,0.07)',
            };
        }
        if (isCompact) {
            if (isVertical && layout?.yaxis && layout.yaxis.title && layout?.xaxis?.range) {
                const freq_min = Math.round(Math.pow(10, layout.xaxis.range[0]));
                const freq_max = Math.round(Math.pow(10, layout.xaxis.range[1]));
                let title = '';
                if (layout?.yaxis.title.text === 'Angle') {
                    title =
                        'Angle [' +
                        layout.yaxis.range[0] +
                        'º, ' +
                        layout.yaxis.range[1] +
                        'º]) v.s. Frequency ([' +
                        freq_min +
                        'Hz, ' +
                        freq_max +
                        'Hz]).';
                } else {
                    title =
                        'SPL (dB [' +
                        layout.yaxis.range[0] +
                        ', ' +
                        layout.yaxis.range[1] +
                        ']) v.s. Frequency ([' +
                        freq_min +
                        'Hz, ' +
                        freq_max +
                        'Hz]).';
                }
                layout.xaxis.title.text = title;
                layout.xaxis.title.standoff = 10;
            }
        }
    }

    // Upgrade an SPL axis in-place so that:
    //   - Major grid lines (prominent) are drawn every 5 dB
    //   - Minor grid lines (faint) + tick marks are drawn every 1 dB
    //   - Labels appear every 5 dB
    //
    // Safety rules:
    //   - Never touches yaxis2 (DI axis in CEA2034 has custom semantics).
    //   - Never touches axes with non-numeric or non-integer ranges.
    //   - Never touches contour angle axes (title === 'Angle').
    //
    // Handles two source cases:
    //   1) Backend provided tickvals every 1 dB with labels only every 10 dB
    //      (On Axis, Early Reflections, ...): replace with dtick=5 + minor dtick=1.
    //   2) Backend provided tickvals every 5 dB with labels every 10 dB
    //      (CEA2034 yaxis): keep tickvals but relabel all of them.
    function upgradeSplYaxis(ax) {
        if (!ax) return;
        if (ax.title && ax.title.text === 'Angle') return;
        if (!ax.range || ax.range.length < 2) return;
        const rMin = ax.range[0];
        const rMax = ax.range[1];
        if (!Number.isFinite(rMin) || !Number.isFinite(rMax)) return;
        const span = Math.abs(rMax - rMin);
        if (span < 10 || span > 100) return;

        // Detect whether tickvals are 5-dB multiples only (case 2) or finer (case 1)
        let useTickvalsPath = false;
        if (Array.isArray(ax.tickvals) && ax.tickvals.length > 0) {
            const allInt = ax.tickvals.every((v) => Number.isInteger(v));
            const allDiv5 = allInt && ax.tickvals.every((v) => v % 5 === 0);
            if (allInt && allDiv5) {
                useTickvalsPath = true;
            }
        }

        if (useTickvalsPath) {
            // Case 2: keep 5-dB tickvals, relabel every position
            ax.ticktext = ax.tickvals.map((v) => String(v));
            ax.tickmode = 'array';
            // Add 1-dB minor grid on top of the 5-dB major ticks
            ax.minor = {
                dtick: 1,
                ticks: ax.ticks || 'inside',
                ticklen: 2,
                showgrid: true,
                gridcolor: 'rgba(0,0,0,0.07)',
            };
        } else {
            // Case 1: replace any 1-dB tickvals with dtick=5 so Plotly draws
            // major grid lines only every 5 dB. Minor ticks fill in every 1 dB.
            delete ax.tickvals;
            delete ax.ticktext;
            delete ax.tickmode;
            ax.dtick = 5;
            ax.minor = {
                dtick: 1,
                ticks: ax.ticks || 'inside',
                ticklen: 2,
                showgrid: true,
                gridcolor: 'rgba(0,0,0,0.07)',
            };
        }
    }

    function computeYaxis() {
        // hide axis to recover some space on mobile
        if (isCompact && isVertical) {
            if (layout.yaxis) {
                layout.yaxis.showticklabels = false;
                layout.yaxis.showgrid = true;
                layout.yaxis.showline = false;
                layout.yaxis.zeroline = false;
                layout.yaxis.title = null;
                layout.yaxis.tickfont = { size: 10 };
                layout.yaxis.mirror = 'ticks';
            }
            if (layout.yaxis2) {
                layout.yaxis2.title = null;
                layout.yaxis2.showticklabels = false;
                layout.yaxis2.visible = false;
            }
        }
        if (layout.yaxis) {
            if (layout.yaxis.nticks) {
                delete layout.yaxis.dtick;
                delete layout.yaxis.tickvals;
                delete layout.yaxis.ticktext;
            } else if (layout.yaxis.tickvals) {
                // Axis with explicit tickvals — preserve and upgrade with 1-dB minor
                // ticks + 5-dB labels for SPL-like axes.
                layout.yaxis.constrain = 'domain';
                upgradeSplYaxis(layout.yaxis);
            } else {
                // No tickvals: use major ticks every 5 dB, minor ticks every 1 dB
                layout.yaxis.dtick = 5;
                layout.yaxis.minor = {
                    dtick: 1,
                    ticks: layout.yaxis.ticks || 'inside',
                    ticklen: 2,
                    showgrid: true,
                    gridcolor: 'rgba(0,0,0,0.07)',
                };
            }
            if (layout.yaxis.title) {
                layout.yaxis.title.font = {
                    size: fontSizeH6 + fontDelta,
                    color: '#000',
                };
            }
        }
        if (layout.yaxis2) {
            if (layout.yaxis2.nticks) {
                delete layout.yaxis2.dtick;
                delete layout.yaxis2.tickvals;
                delete layout.yaxis2.ticktext;
            } else if (layout.yaxis2.tickvals) {
                // yaxis2 (e.g. CEA2034 DI axis): preserve tickvals as-is.
                // DI axis has custom semantics where tick positions don't match
                // displayed labels, so we deliberately avoid any tick/label override.
                layout.yaxis2.constrain = 'domain';
            } else {
                layout.yaxis2.dtick = 5;
                layout.yaxis2.minor = {
                    dtick: 1,
                    ticks: layout.yaxis2.ticks || 'inside',
                    ticklen: 2,
                    showgrid: true,
                    gridcolor: 'rgba(0,0,0,0.07)',
                };
            }
            if (layout.yaxis2.title) {
                layout.yaxis2.title.font = {
                    size: fontSizeH6 + fontDelta,
                    color: '#000',
                };
            }
        }
    }

    function addInitialLetter(text, letter) {
        if (text.startsWith('(A) ') || text.startsWith('(B) ')) {
            return text;
        }
        return '(' + letter + ') ' + text;
    }

    function computeTitle() {
        let title = '';
        let pos0for = -1;
        let pos0by = -1;
        let speaker0 = '';
        let version0 = '';
        let br0 = '';
        if (inputGraphsData[0] && inputGraphsData[0]?.layout.title.text) {
            if (inputGraphsData[1]) {
                title = addInitialLetter(inputGraphsData[0].layout.title.text, 'A');
            } else {
                title = inputGraphsData[0].layout.title.text;
            }
            pos0for = inputGraphsData[0].layout.title.text.indexOf(' for ');
            pos0by = inputGraphsData[0].layout.title.text.indexOf(' measured by ');
            speaker0 = inputGraphsData[0].layout.title.text.slice(pos0for, pos0by);
            version0 = inputGraphsData[0].layout.title.text.slice(pos0by + 13);
            br0 = inputGraphsData[0].layout.title.text.indexOf('<br>');
        }
        if (outputNumberGraphs === 1 && inputGraphsData[1] && inputGraphsData[1]?.layout.title.text) {
            const titlePart = br0 === -1 ? title : title.slice(0, br0);
            const titleB = addInitialLetter(inputGraphsData[1].layout.title.text, 'B');
            const pos1for = inputGraphsData[1].layout.title.text.indexOf(' for ');
            const pos1by = inputGraphsData[1].layout.title.text.indexOf(' measured by ');
            const speaker1 = inputGraphsData[1].layout.title.text.slice(pos1for, pos1by);
            const version1 = inputGraphsData[1].layout.title.text.slice(pos1by + 13);
            if (speaker0 === speaker1) {
                const prefix = inputGraphsData[0].layout.title.text.slice(0, pos0by);
                const suffixA = inputGraphsData[0].layout.title.text.slice(pos0by + 13);
                const suffixB = inputGraphsData[1].layout.title.text.slice(pos1by + 13);
                const singleLine = prefix + ' measured by (A) ' + suffixA + ' v.s. by (B) ' + suffixB;
                const titleFontSize = isCompact ? fontSizeH3 : fontSizeH3 + 2 * fontDelta;
                const sep = titleFitsOnOneLine(singleLine, titleFontSize, windowWidth) ? ' ' : '<br> ';
                title = prefix + sep + 'measured by (A) ' + suffixA + ' v.s. by (B) ' + suffixB;
            } else {
                // Build single-line version first, add <br> only if it doesn't fit
                const singleLine = titlePart + ' v.s. ' + titleB;
                const titleFontSize = isCompact ? fontSizeH3 : fontSizeH3 + 2 * fontDelta;
                if (titleFitsOnOneLine(singleLine, titleFontSize, windowWidth)) {
                    title = singleLine;
                } else {
                    title = titlePart + '<br> v.s. ' + titleB;
                }
                // Add (A) or (B)
                if (inputGraphsData[1]) {
                    for (let i = 0; i < datas.length; i++) {
                        if (datas[i]?.legendgrouptitle?.text) {
                            if (datas[i].legendgrouptitle.text.indexOf(speaker0.slice(5)) !== -1) {
                                if (datas[i].name) {
                                    datas[i].name = addInitialLetter(datas[i].name, 'A');
                                }
                            }
                            if (datas[i].legendgrouptitle.text.indexOf(speaker1.slice(5)) !== -1) {
                                if (datas[i].name) {
                                    datas[i].name = addInitialLetter(datas[i].name, 'B');
                                }
                            }
                            // remove legendgroup since people like to add/remove a curve with a click
                            datas[i].legendgrouptitle.text = null;
                            datas[i].legendgroup = null;
                        }
                    }
                }
            }
        }
        if (isCompact) {
            if (outputNumberGraphs === 1) {
                const doSplit = !titleFitsOnOneLine(title, fontSizeH3, windowWidth);
                if (doSplit) {
                    // split title on 2 lines
                    const measured_pos = title.indexOf(' measured ');
                    if (measured_pos !== -1) {
                        const vs_pos = title.indexOf(' v.s. ');
                        if (vs_pos === -1) {
                            title = title.slice(0, measured_pos) + ' <br>' + title.slice(measured_pos + 1);
                        }
                    }
                }
            }
            layout.title = {
                text: title,
                font: {
                    size: fontSizeH3,
                    color: '#000',
                },
                xref: 'paper',
                xanchor: 'left',
                x: 0.0,
            };
        } else {
            layout.title = {
                text: title,
                font: {
                    size: fontSizeH3 + 2 * fontDelta,
                    color: '#000',
                },
                // automargin: true,
                xref: 'paper',
                xanchor: 'center',
                // title start sligthly on the right
                x: 0.5,
                // keep title below modBar if title is long
                yref: 'container',
                yanchor: 'top',
                y: 1.025,
            };
        }
    }

    // Apply computeLayout() output (width, height, margin, legend) to the Plotly layout object.
    // layout.width must be set to the target container width before calling this.
    // Everything else — total height, margins, legend placement — is derived here so the
    // plot-area aspect ratio is guaranteed.
    function applyComputeLayout(ratio) {
        // Count visible traces and find the longest label (used for legend sizing).
        let traceCount = 0;
        let maxLabelLen = 0;
        for (let k = 0; k < datas.length; k++) {
            const t = datas[k];
            if (t.visible !== false && t.showlegend !== false) {
                traceCount++;
                if (t.name && t.name.length > maxLabelLen) maxLabelLen = t.name.length;
            }
        }

        const containerWidth = layout.width;
        const result = computeLayout(
            containerWidth,
            isVertical,
            isCompact,
            outputGraphProperties,
            traceCount,
            maxLabelLen,
            !!layout.yaxis2,
            ratio,
            fontDelta
        );

        layout.width = result.width;
        layout.height = result.height;
        layout.margin = result.margin;

        if (result.legend.hidden) {
            layout.showlegend = false;
            layout.legend = {};
        } else {
            // Compute Plotly legend positioning from the decided orientation.
            // - Horizontal: pinned to the bottom of the CONTAINER (not plot-area), so the
            //   x-axis title sits above it inside the bottom margin and they don't overlap.
            // - Vertical: placed to the right of plot, anchored at left so it grows rightward into margin.r.
            if (result.legend.orientation === 'v') {
                layout.legend = {
                    orientation: 'v',
                    xref: 'paper',
                    yref: 'paper',
                    xanchor: 'left',
                    yanchor: 'middle',
                    x: 1.02,
                    y: 0.5,
                    font: { size: result.legend.font },
                    entrywidth: result.legend.entryWidth,
                    entrywidthmode: 'pixels',
                    itemwidth: 20,
                    groupclick: 'toggleitem',
                };
            } else {
                layout.legend = {
                    orientation: 'h',
                    xref: 'container',
                    yref: 'container',
                    xanchor: 'center',
                    yanchor: 'bottom',
                    x: 0.5,
                    y: 0.005,
                    font: { size: result.legend.font },
                    entrywidth: result.legend.entryWidth,
                    entrywidthmode: 'pixels',
                    itemwidth: 20,
                    groupclick: 'toggleitem',
                };
            }
        }
    }

    // Handle legendgroup cleanup and group-title truncation (independent of sizing).
    // Must run BEFORE applyComputeLayout() so that legendgroup cleanup affects the
    // visible-trace count used for legend sizing.
    function computeLegendGroups() {
        const groups = new Set();
        for (let k = 0; k < datas.length; k++) {
            if (datas[k].legendgroup) {
                groups.add(datas[k].legendgroup);
            }
        }
        if (groups.size === 1) {
            for (let k = 0; k < datas.length; k++) {
                datas[k].legendgroup = null;
                datas[k].legendgrouptitle = null;
            }
        } else if (!isCompact && groups.size > 1) {
            for (let k = 0; k < datas.length; k++) {
                const title = datas[k].legendgrouptitle;
                if (title?.text) {
                    const pos_vs = title.text.indexOf(' v.s. ');
                    if (pos_vs !== -1) {
                        datas[k].legendgrouptitle.text = title.text.slice(0, pos_vs);
                    }
                    // Only truncate at ' for ' if we're not dealing with same speaker comparisons
                    const pos_for = title.text.indexOf(' for ');
                    if (pos_for !== -1) {
                        const needsVersionInfo =
                            outputNumberGraphs === 1 &&
                            inputGraphsData[1] &&
                            inputGraphsData[0]?.layout.title.text &&
                            inputGraphsData[1]?.layout.title.text;
                        if (needsVersionInfo) {
                            const pos0for = inputGraphsData[0].layout.title.text.indexOf(' for ');
                            const pos0by = inputGraphsData[0].layout.title.text.indexOf(' measured by ');
                            const pos1for = inputGraphsData[1].layout.title.text.indexOf(' for ');
                            const pos1by = inputGraphsData[1].layout.title.text.indexOf(' measured by ');
                            const speaker0 = inputGraphsData[0].layout.title.text.slice(pos0for, pos0by);
                            const speaker1 = inputGraphsData[1].layout.title.text.slice(pos1for, pos1by);
                            if (speaker0 !== speaker1) {
                                datas[k].legendgrouptitle.text = title.text.slice(0, pos_for);
                            }
                        } else {
                            datas[k].legendgrouptitle.text = title.text.slice(0, pos_for);
                        }
                    }
                }
            }
        }

        // Surface plots: hide all traces from the legend entirely.
        if (outputGraphProperties.isSurface) {
            for (let k = 0; k < datas.length; k++) {
                datas[k].showlegend = false;
                if (k > 0) {
                    datas[k].showscale = false;
                }
            }
        }
    }

    function computePolar() {
        if (!layout) {
            return;
        }
        const polars = ['polar', 'polar2', 'polar3', 'polar4'];
        if (layout['polar4'] && isCompact && outputGraphProperties.isRadar) {
            layout.height = layout.width * 4;
            // fill defaults
            polars.forEach((polar) => {
                if (!layout[polar].domain) {
                    layout[polar]['domain'] = {};
                    layout[polar]['domain']['x'] = [0, 1];
                    layout[polar]['domain']['y'] = [0, 1];
                }
            });
            // full width
            layout.polar.domain.x = [0, 1];
            layout.polar2.domain.x = [0, 1];
            layout.polar3.domain.x = [0, 1];
            layout.polar4.domain.x = [0, 1];
            // split in 4
            const start = 0.04;
            const len = 0.2;
            const gap = 0.05;
            layout.polar4.domain.y = [start, start + len];
            layout.polar3.domain.y = [start + len * 2 + gap * 2, start + len * 3 + gap * 2];
            layout.polar2.domain.y = [start + len + gap, start + len * 2 + gap];
            layout.polar.domain.y = [start + len * 3 + gap * 3, start + len * 4 + gap * 3];
            // move legend up
            layout.legend.x = 0.5;
            layout.legend.xanchor = 'center';
            layout.legend.y = 0.0;
        }
        if (outputGraphProperties.isGlobe) {
            for (let i in polars) {
                const polar = polars[i];
                if (!layout[polar]) {
                    layout[polar] = {};
                }
                layout[polar].bargap = 0;
                layout[polar].hole = 0.05;
            }
        }
    }

    function computeLabel(userLabelConfig) {
        const traceNames = datas.filter((d) => d.name).map((d) => d.name);
        let ratio = graphRatio;
        if (outputGraphProperties.isSurface) {
            ratio = contourRatio;
        } else if (outputGraphProperties.isRadar || outputGraphProperties.isGlobe) {
            ratio = squareRatio;
        }
        const useShort = shouldUseShortLabels(
            traceNames,
            layout.width,
            layout.height,
            isCompact,
            isVertical,
            ratio,
            userLabelConfig || 'default'
        );

        for (let k = 0; k < datas.length; k++) {
            if (isCompact) {
                if (isVertical || inputGraphsData.length === 1) {
                    datas[k].legendgroup = null;
                    datas[k].legendgrouptitle = null;
                }
            }
            if (datas[k].name) {
                datas[k]._fullName = datas[k].name;
                if (useShort && labelShort[datas[k].name]) {
                    datas[k].name = labelShort[datas[k].name];
                }
            }
        }
    }

    function computeModbar() {
        if (isCompact) {
            // remove mod bar
            config = {
                responsive: false,
                displayModeBar: false,
            };
        } else {
            layout.modebar = {
                orientation: 'v',
            };
            config = {
                responsive: false,
                displayModeBar: true,
            };
        }
    }

    function computeFont() {
        if (isCompact) {
            layout.font = { size: fontSizeH5 };
        } else {
            layout.font = { size: fontSizeH4 };
        }
    }

    function computeColorbar() {
        for (let k = 0; k < datas.length; k++) {
            if (datas[k].colorbar) {
                datas[k].colorbar.xref = 'paper';
                datas[k].colorbar.yref = 'paper';
                if (isVertical) {
                    datas[k].colorbar.orientation = 'h';
                    datas[k].colorbar.xanchor = 'center';
                    datas[k].colorbar.x = 0.5;
                    datas[k].colorbar.yanchor = 'bottom';
                    datas[k].colorbar.y = -0.5;
                    if (isCompact) {
                        datas[k].colorbar.y = -0.7;
                    }
                } else {
                    datas[k].colorbar.orientation = 'v';
                    datas[k].colorbar.xanchor = 'left';
                    datas[k].colorbar.yanchor = 'center';
                    datas[k].colorbar.x = 1.0;
                    datas[k].colorbar.yref = 'paper';
                    datas[k].colorbar.y = 0.5;
                }
                datas[k].colorbar.xpad = 20;
                datas[k].colorbar.ypad = 20;
                datas[k].colorbar.len = 0.8;
                datas[k].colorbar.lenmode = 'fraction';
                datas[k].colorbar.thickness = 15;
                datas[k].colorbar.thicknessmode = 'pixels';
                datas[k].colorbar.tickfont = {
                    size: fontSizeH6,
                };
                datas[k].colorbar.title = {
                    text: 'dB (SPL)',
                    font: {
                        size: fontSizeH5,
                    },
                    side: 'bottom',
                };
            }
        }
    }

    if (layout != null && datas != null) {
        let ratio = graphRatio;
        if (outputGraphProperties.isSurface) {
            ratio = contourRatio;
        } else if (outputGraphProperties.isRadar || outputGraphProperties.isGlobe) {
            ratio = squareRatio;
        }
        // All graphs (SPL, CEA2034, contour, radar, globe) go through applyComputeLayout.
        // The caller passes the actual DOM container width as `windowWidth`; computeLayout
        // is the single source of truth for width/height/margins/legend, so we seed
        // layout.width with the container width and let applyComputeLayout derive the rest.
        layout.width = windowWidth;
        layout.height = windowHeight; // temporary — applyComputeLayout will overwrite

        computeFont();
        computeXaxis();
        computeYaxis();
        computeTitle(); // before legend
        computeLegendGroups(); // cleanup legendgroup/legendgrouptitle on traces
        computeLabel();
        computeModbar();
        computeColorbar();
        computePolar();

        applyComputeLayout(ratio);
    } else {
        // should be a pop up
        console.log('Error: No graph is available');
    }

    /*
    console.log(
        'margin = {t: ' +
            layout.margin.t +
            ', b: ' +
            layout.margin.b +
            ', l: ' +
            layout.margin.l +
            ', r: ' +
            layout.margin.r +
            '}'
    );
*/
    return { data: datas, layout: layout, config: config, _graphType: outputGraphProperties };
}

export function setCEA2034(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setCEA2034 got ' + speakerGraphs.length + ' graphs')
    let legendShift = 0;
    for (let i = 0; i < speakerGraphs.length; i++) {
        if (speakerGraphs[i] != null) {
            // console.log('adding graph ' + i)
            for (const trace in speakerGraphs[i].data) {
                speakerGraphs[i].data[trace].legendgroup = 'speaker' + i;
                speakerGraphs[i].data[trace].legendgrouptitle = {
                    text: speakerNames[i],
                };
                if (i % 2 === 1) {
                    speakerGraphs[i].data[trace].line = { dash: 'dashdot' };
                }
                /* pierre
                if (speakerGraphs.length > 1 && !isCompact) {
                    // hide recommended zones by default
                    if (
                        'name' in speakerGraphs[i].data[trace] &&
                        speakerGraphs[i].data[trace].name.indexOf('recommended') === 0
                    ) {
                        speakerGraphs[i].data[trace]['visible'] = 'legendonly';
                        speakerGraphs[i].data[trace]['legendrank'] = 2000;
                        legendShift += 1;
                    } else if (
                        'name' in speakerGraphs[i].data[trace] &&
                        (speakerGraphs[i].data[trace].name.indexOf('no data') !== -1 ||
                            speakerGraphs[i].data[trace].name.indexOf('N/A') !== -1)
                    ) {
                        speakerGraphs[i].data[trace]['legendrank'] = 4000;
                        legendShift += 1;
                    } else if ('line' in speakerGraphs[i].data[trace] && speakerGraphs[i].data[trace].x.length < 10) {
                        speakerGraphs[i].data[trace]['visible'] = 'legendonly';
                        legendShift += 1;
                        speakerGraphs[i].data[trace]['legendrank'] = 3000;
                    }
                }
*/
            }
        }
    }
    let option = setGraphOptions(speakerGraphs, width, height, GraphProperties[measurement], 1);

    // move the legend2 such that they do not overlap
    if (option.layout.legend2) {
        if (!isDisplayVertical()) {
            option.layout.legend.y = 0.75;
        }
        option.layout.legend2.x = 0;
        option.layout.legend2.yanchor = 'bottom';
        if (isDisplayVertical()) {
            option.layout.legend2.y = -1.75;
        } else {
            option.layout.legend2.y = -0.75;
        }
        option.layout.height += 22 * 14;
    }

    return [option];
}

export function setGraph(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setGraph got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const isCompact = width < graphSmall || height < graphSmall;
    for (const i in speakerGraphs) {
        if (speakerGraphs[i] != null) {
            // console.log('adding graph ' + i)
            for (const trace in speakerGraphs[i].data) {
                // Trendline and zone visibility is now controlled by the config menu
                // via applyConfig() with per-speaker toggles (showA/showB)
                speakerGraphs[i].data[trace].legendgroup = 'speaker' + i;
                speakerGraphs[i].data[trace].legendgrouptitle = {
                    text: speakerNames[i],
                };
                if (i % 2 === 1) {
                    speakerGraphs[i].data[trace].line = { dash: 'dashdot' };
                }
            }
        }
    }
    let option = setGraphOptions(speakerGraphs, width, height, GraphProperties[measurement], 1);
    return [option];
}

export function setRadar(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setRadar got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    for (const i in speakerGraphs) {
        if (speakerGraphs[i] != null) {
            // console.log('adding graph ' + i)
            for (const trace in speakerGraphs[i].data) {
                speakerGraphs[i].data[trace].legendgroup = null;
                speakerGraphs[i].data[trace].legendgrouptitle = {
                    text: speakerNames[i],
                };
                if (i % 2 === 1) {
                    speakerGraphs[i].data[trace].line = { dash: 'dashdot' };
                }
            }
        }
    }
    const options = setGraphOptions(speakerGraphs, width, height, GraphProperties[measurement], 1);
    return [options];
}

export function setContour(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setContour got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    let len = 1;
    if (speakerGraphs.length > 1) {
        len = 2;
    }
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            let options = setGraphOptions(
                [{ data: speakerGraphs[i].data, layout: speakerGraphs[i].layout }],
                width,
                height,
                GraphProperties[measurement],
                len
            );
            // do not show the legend
            options.layout.showlegend = false;
            // this shapes are not working in 3D thus removing them
            if (options.layout && options.layout?.shapes) {
                options.layout.shapes = null;
            }
            graphsConfigs.push(options);
        }
    }
    // The merge code below only makes sense when we have at least 2 valid graphs.
    // Return early for single-speaker or if one of the inputs failed to produce a layout.
    if (graphsConfigs.length < 2) {
        return graphsConfigs;
    }

    // merge the 2 graphs
    let mergedConfig = {
        data: [],
        layout: structuredClone(graphsConfigs[0].layout),
        config: structuredClone(graphsConfigs[0].config),
    };
    // Target per-sub-plot aspect ratio (width/height) — matches single-contour contourRatio.
    const CONTOUR_RATIO = 1.6;
    if (isDisplayCompact() || isDisplayVertical()) {
        // Compact or portrait: stack the two contours vertically (yaxis + yaxis2
        // domains split top/bottom) so each contour uses the full width.
        // Each sub-plot height = plotW / ratio; total height = 2 * sub-plot + margins.
        const totalW = isDisplayCompact() ? window.innerWidth : window.innerWidth - graphMarginRight;
        const marginT = 160; // double-line title + axis
        const marginB = isDisplayCompact() ? 120 : 60;
        const marginL = 10;
        const marginR = isDisplayCompact() ? 10 : 100; // colorbar
        const plotW = Math.max(1, totalW - marginL - marginR);
        const subPlotH = plotW / CONTOUR_RATIO;
        const gap = 40; // space between the two sub-plots
        mergedConfig.layout.width = totalW;
        mergedConfig.layout.height = marginT + marginB + 2 * subPlotH + gap;
        mergedConfig.layout.margin = { t: marginT, b: marginB, l: marginL, r: marginR };
    } else {
        // Non-compact horizontal: place the two contours side by side
        // (xaxis domains [0, 0.49] and [0.51, 1]).
        // Each sub-plot has half the plot width → plotH = (plotW * 0.49) / ratio.
        const totalW = window.innerWidth;
        const marginT = 60;
        const marginB = 40;
        const marginL = 30;
        const marginR = 80; // colorbar at right
        const plotW = Math.max(1, totalW - marginL - marginR);
        const subPlotW = plotW * 0.49;
        const plotH = subPlotW / CONTOUR_RATIO;
        mergedConfig.layout.width = totalW;
        mergedConfig.layout.height = marginT + marginB + plotH;
        mergedConfig.layout.margin = { t: marginT, b: marginB, l: marginL, r: marginR };
    }
    // customise title
    function split(title) {
        const pos_for = title.indexOf(' for ');
        const pos_by = title.indexOf(' by ');
        const measurement = title.slice(0, pos_for);
        const speaker = title.slice(pos_for + 5, pos_by);
        const reviewer = title.slice(pos_by + 4);
        return [measurement, speaker, reviewer];
    }
    let title = '';
    if (graphsConfigs.length > 1) {
        const split0 = split(graphsConfigs[0].layout.title.text);
        const split1 = split(graphsConfigs[1].layout.title.text);
        const singleLine =
            '(A) ' +
            split0[0] +
            ' ' +
            split0[1] +
            ' by ' +
            split0[2] +
            ' v.s. (B) ' +
            split1[0] +
            ' ' +
            split1[1] +
            ' by ' +
            split1[2];
        if (titleFitsOnOneLine(singleLine, 14, window.innerWidth)) {
            title = singleLine;
        } else {
            title =
                '(A) ' +
                split0[0] +
                ' ' +
                split0[1] +
                ' by ' +
                split0[2] +
                ' <br>v.s. (B) ' +
                split1[0] +
                ' ' +
                split1[1] +
                ' by ' +
                split1[2];
        }
    } else if (graphsConfigs.length === 1) {
        title = graphsConfigs[0].layout.title.text;
    }
    mergedConfig.layout.title = {
        text: title,
        font: { size: 14 },
    };
    // merge axis
    for (const i in graphsConfigs) {
        const config = graphsConfigs[i];
        const offset = (parseInt(i) + 1).toString();
        if (i !== '0') {
            mergedConfig.layout['xaxis' + offset] = structuredClone(mergedConfig.layout.xaxis);
            mergedConfig.layout['yaxis' + offset] = structuredClone(mergedConfig.layout.yaxis);
        }
        for (const j in config.data) {
            let trace = structuredClone(config.data[j]);
            if (i !== '0') {
                trace['xaxis'] = 'x' + offset;
                trace['yaxis'] = 'y' + offset;
            }
            if (trace?.colorbar) {
                trace.showscale = false;
                if (i === '0') {
                    trace.showscale = true;
                    trace.colorbar.xref = 'paper';
                    trace.colorbar.yref = 'paper';
                    if (isDisplayCompact()) {
                        trace.colorbar.orientation = 'h';
                        trace.colorbar.x = 0.5;
                        trace.colorbar.xanchor = 'center';
                        trace.colorbar.y = -0.4;
                        trace.colorbar.yanchor = 'bottom';
                        trace.colorbar.len = 1.0;
                    } else {
                        trace.colorbar.orientation = 'v';
                        trace.colorbar.x = 1.15;
                        if (isDisplayCompact()) {
                            trace.colorbar.x = 1.25;
                        }
                        trace.colorbar.xanchor = 'right';
                        trace.colorbar.y = 0.5;
                        trace.colorbar.yanchor = 'center';
                        trace.colorbar.len = 0.6;
                    }
                    trace.colorbar.thickness = 15;
                    trace.colorbar.title = {
                        text: 'db (SPL)',
                        side: 'bottom',
                        font: { size: 10 },
                    };
                }
            }
            mergedConfig.data.push(trace);
        }
    }

    if (isDisplayCompact() || isDisplayVertical()) {
        mergedConfig.layout.xaxis.side = 'top';
        mergedConfig.layout.xaxis.tick = 'outside';

        if (mergedConfig.layout?.xaxis2) {
            mergedConfig.layout.xaxis2.side = 'bottom';
            mergedConfig.layout.xaxis2.tick = 'outside';
            mergedConfig.layout.xaxis2['anchor'] = 'y2';
        }

        mergedConfig.layout.yaxis.tick = 'outside';
        if (mergedConfig.layout.yaxis.title && mergedConfig.layout.yaxis.title.text) {
            mergedConfig.layout.yaxis.title.text = 'Angle (A)';
        }

        if (mergedConfig.layout?.yaxis2) {
            mergedConfig.layout.yaxis2.tick = 'outside';
            if (mergedConfig.layout.yaxis2.title && mergedConfig.layout.yaxis2.title.text) {
                mergedConfig.layout.yaxis2.title.text = 'Angle (B)';
            }
        }

        if (graphsConfigs.length > 1) {
            const range0 = graphsConfigs[0].layout.xaxis.range;
            const range1 = graphsConfigs[1].layout.xaxis.range;
            const range = [Math.min(range0[0], range1[0]), Math.max(range0[1], range1[1])];
            mergedConfig.layout.xaxis.range = range;
            mergedConfig.layout.yaxis['domain'] = [0.51, 1];
            mergedConfig.layout.xaxis2.range = range;
            mergedConfig.layout.yaxis2['domain'] = [0, 0.49];
        } else {
            mergedConfig.layout.xaxis.range = graphsConfigs[0].layout.xaxis.range;
            mergedConfig.layout.yaxis['domain'] = [0.51, 1];
        }
    } else {
        mergedConfig.layout.xaxis.side = 'bottom';
        mergedConfig.layout.xaxis.tick = 'outside';

        mergedConfig.layout.yaxis.tick = 'outside';
        if (mergedConfig.layout.yaxis.title && mergedConfig.layout.yaxis.title.text) {
            mergedConfig.layout.yaxis.title.text = 'Angle (A)';
        }

        if (mergedConfig.layout.xaxis2) {
            mergedConfig.layout.xaxis2.side = 'bottom';
            mergedConfig.layout.xaxis2.tick = 'outside';
            mergedConfig.layout.xaxis2['domain'] = [0.51, 1];
        }
        if (mergedConfig.layout.yaxis2) {
            mergedConfig.layout.yaxis2.side = 'right';
            mergedConfig.layout.yaxis2.tick = 'outside';
            mergedConfig.layout.yaxis2['anchor'] = 'x2';
            if (mergedConfig.layout.yaxis2.title && mergedConfig.layout.yaxis2.title.text) {
                mergedConfig.layout.yaxis2.title.text = 'Angle (B)';
            }
        }

        mergedConfig.layout.xaxis['domain'] = [0, 0.49];

        if (graphsConfigs.length >= 2) {
            const range0 = graphsConfigs[0].layout.yaxis.range;
            const range1 = graphsConfigs[1].layout.yaxis.range;
            const range = [Math.min(range0[0], range1[0]), Math.max(range0[1], range1[1])];
            mergedConfig.layout.yaxis.range = range;
            if (mergedConfig.layout.yaxis2) mergedConfig.layout.yaxis2.range = range;
        }
    }

    return [mergedConfig];
}

const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const lookup = typeof Uint8Array === 'undefined' ? [] : new Uint8Array(256);
for (let i = 0; i < chars.length; i++) {
    lookup[chars.charCodeAt(i)] = i;
}

export function decode64(base64) {
    let bufferLength = base64.length * 0.75;
    const len = base64.length;
    if (base64[base64.length - 1] === '=') {
        bufferLength--;
        if (base64[base64.length - 2] === '=') {
            bufferLength--;
        }
    }
    const arraybuffer = new ArrayBuffer(bufferLength);
    const bytes = new Uint8Array(arraybuffer);
    let p = 0;
    for (let i = 0; i < len; i += 4) {
        const encoded1 = lookup[base64.charCodeAt(i)];
        const encoded2 = lookup[base64.charCodeAt(i + 1)];
        const encoded3 = lookup[base64.charCodeAt(i + 2)];
        const encoded4 = lookup[base64.charCodeAt(i + 3)];
        bytes[p++] = (encoded1 << 2) | (encoded2 >> 4);
        bytes[p++] = ((encoded2 & 15) << 4) | (encoded3 >> 2);
        bytes[p++] = ((encoded3 & 3) << 6) | (encoded4 & 63);
    }
    return arraybuffer;
}

export function decode(input) {
    // minimum to decode an array
    if (input?.dtype) {
        const buffer = decode64(input.bdata);
        switch (input.dtype) {
            // clamped
            case 'u1c':
                return new Uint8ClampedArray(buffer);
            // int
            case 'i1':
                return new Int8Array(buffer);
            case 'i2':
                return new Int16Array(buffer);
            case 'i4':
                return new Int32Array(buffer);
            // unsigned int
            case 'u1':
                return new Uint8Array(buffer);
            case 'u2':
                return new Uint16Array(buffer);
            case 'u4':
                return new Uint32Array(buffer);
            // float
            case 'f4':
                if (buffer.byteLength % 4 !== 0) {
                    console.error('Invalid buffer length for Float32Array:', buffer.byteLength);
                    return input;
                }
                return new Float32Array(buffer);
            case 'f8':
                if (buffer.byteLength % 8 !== 0) {
                    console.error('Invalid buffer length for Float64Array:', buffer.byteLength);
                    return input;
                }
                return new Float64Array(buffer);
        }
    }
    return input;
}

export function setGlobe(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setGlobe ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            let polarData = [];
            for (const j in speakerGraphs[i].data) {
                const freq = decode(speakerGraphs[i].data[j].x);
                const angle = decode(speakerGraphs[i].data[j].y);
                const spl = decode(speakerGraphs[i].data[j].z);
                if (!spl) {
                    continue;
                }
                const r = [];
                // r is x (len of y times)
                for (let k1 = 0; k1 < freq.length; k1++) {
                    for (let k2 = 0; k2 < angle.length - 1; k2++) {
                        r.push(Math.log10(freq[k1]));
                    }
                }
                // theta is y (len of x times)
                let theta = [];
                for (let k = 0; k < freq.length; k++) {
                    for (let k2 = 0; k2 < angle.length - 1; k2++) {
                        theta.push(angle[k2]);
                    }
                }
                theta = theta.flat();
                // color is z unravelled
                // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].x=' + x.length)
                // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].y=' + y.length)
                // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].z=' + z.length)
                const color = [];
                for (let k1 = 0; k1 < freq.length; k1++) {
                    for (let k2 = 0; k2 < angle.length - 1; k2++) {
                        let val = spl[k1 + k2 * freq.length];
                        val = Math.max(contourMin, val);
                        val = Math.min(contourMax, val);
                        color.push(val);
                    }
                }
                let currentPolarData = {};
                currentPolarData.type = 'barpolar';
                currentPolarData.r = r;
                currentPolarData.theta = theta;
                // should be in layout?
                currentPolarData.marker = {
                    autocolorscale: false,
                    colorscale: contourColorscale,
                    color: color,
                    colorbar: {
                        title: {
                            font: {
                                size: fontSizeH4,
                            },
                            text: 'dB (SPL)',
                            side: 'bottom',
                        },
                        orientation: 'h',
                        xanchor: 'center',
                        yanchor: 'bottom',
                        xref: 'paper',
                        yref: 'paper',
                        x: 0.5,
                        y: -0.3,
                        len: 0.8,
                        lenmode: 'fraction',
                        thickness: 15,
                        thicknessmode: 'pixels',
                    },
                    showscale: true,
                    line: {
                        color: null,
                        width: 0,
                    },
                };

                currentPolarData.legendgroup = 'speaker' + i;
                currentPolarData.legendgrouptitle = { text: speakerNames[i] };

                polarData.push(currentPolarData);
            }
            let options = setGraphOptions(
                [{ data: polarData, layout: speakerGraphs[i].layout }],
                width,
                height,
                GraphProperties[measurement],
                speakerGraphs.length
            );
            if (speakerGraphs.length > 1 && i === 0) {
                options.layout.margin.l += 60;
                options.layout.margin.r += 60;
            }
            graphsConfigs.push(options);
        }
    }
    return graphsConfigs;
}

export function setContour3D(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setContour3D ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            let surfaceData = [];
            for (const j in speakerGraphs[i].data) {
                surfaceData.push(speakerGraphs[i].data[j]);
            }
            let options = setGraphOptions(
                [{ data: surfaceData, layout: speakerGraphs[i].layout }],
                width,
                height,
                GraphProperties[measurement],
                speakerGraphs.length
            );
            // this shapes are not working in 3D thus removing them
            let layout = options.layout;
            if (layout && layout?.shapes) {
                layout.shapes = null;
            }
            graphsConfigs.push({ data: options.data, layout: layout, config: options.config });
        }
    }
    return graphsConfigs;
}

export function setPlotForMeasurement(measurement, speakersName, graphs, windowWidth, windowHeight) {
    if (measurement === 'CEA2034' || measurement === 'CEA2034 Normalized') {
        return setCEA2034(measurement, speakersName, graphs, windowWidth, windowHeight);
    }
    if (
        measurement === 'On Axis' ||
        measurement === 'Estimated In-Room Response' ||
        measurement === 'Early Reflections' ||
        measurement === 'SPL Horizontal' ||
        measurement === 'SPL Vertical' ||
        measurement === 'SPL Horizontal Normalized' ||
        measurement === 'SPL Vertical Normalized' ||
        measurement === 'Horizontal Reflections' ||
        measurement === 'Vertical Reflections'
    ) {
        return setGraph(measurement, speakersName, graphs, windowWidth, windowHeight);
    }

    if (measurement === 'SPL Horizontal Radar' || measurement === 'SPL Vertical Radar') {
        return setRadar(measurement, speakersName, graphs, windowWidth, windowHeight);
    }

    if (
        measurement === 'SPL Horizontal Contour' ||
        measurement === 'SPL Vertical Contour' ||
        measurement === 'SPL Horizontal Contour Normalized' ||
        measurement === 'SPL Vertical Contour Normalized'
    ) {
        return setContour(measurement, speakersName, graphs, windowWidth, windowHeight);
    }

    if (
        measurement === 'SPL Horizontal Contour 3D' ||
        measurement === 'SPL Vertical Contour 3D' ||
        measurement === 'SPL Horizontal Contour Normalized 3D' ||
        measurement === 'SPL Vertical Contour Normalized 3D'
    ) {
        return setContour3D(measurement, speakersName, graphs, windowWidth, windowHeight);
    }

    if (
        measurement === 'SPL Horizontal Globe' ||
        measurement === 'SPL Vertical Globe' ||
        measurement === 'SPL Horizontal Globe Normalized' ||
        measurement === 'SPL Vertical Globe Normalized'
    ) {
        return setGlobe(measurement, speakersName, graphs, windowWidth, windowHeight);
    }

    console.error('Measurement ' + measurement + ' is unknown');
    return null;
}
