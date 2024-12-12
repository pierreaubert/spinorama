// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

const flags_Contour_Delta = false;

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

const labelShort = {
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

const graphSmall = 550;
const graphLarge = 1200;

const graphRatio = 1.4;

const graphMarginLeft = 30;
const graphMarginRight = 30;

const graphMarginTop = 60;
const graphMarginBottom = 60;
const graphMarginTopSmall = 30;
const graphMarginBottomSmall = 30;

const graphTitle = 40;
const graphSpacer = graphMarginTop + graphMarginBottom + graphTitle;
const graphExtraPadding = 40;

const graphLegendWidth = 164;

const fontSizeH1 = 16;
const fontSizeH2 = 14;
const fontSizeH3 = 12;
const fontSizeH4 = 11;
const fontSizeH5 = 10;
const fontSizeH6 = 9;

export function isDisplayVertical() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    if (windowWidth <= windowHeight) {
        return true;
    }
    return false;
}

export function isDisplayCompact() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    if (windowWidth < graphSmall || windowHeight < graphSmall) {
        return true;
    }
    return false;
}

export function computeDims(windowWidth, windowHeight, isVertical, isCompact, nbGraphs) {
    let width = windowWidth;
    let height = windowHeight;
    if (isCompact) {
        if (isVertical) {
            // portraint
            width = windowWidth;
            height = Math.min(windowHeight, windowWidth / graphRatio + graphMarginTop + graphMarginBottom + graphExtraPadding);
        } else {
            // landscape
            width = windowWidth - graphExtraPadding;
            height = Math.min(windowHeight, windowWidth / graphRatio + graphSpacer);
        }
    } else {
        if (isVertical) {
            width = Math.min(graphLarge, windowWidth - graphMarginRight);
            height = windowWidth / graphRatio + graphMarginTop + graphMarginBottom + graphExtraPadding;
        } else {
            width = Math.min(graphLarge, windowWidth - graphMarginRight - graphExtraPadding);
            const graphWidth = width - graphMarginLeft - graphLegendWidth;
            height = graphWidth / graphRatio;
        }
        if (nbGraphs > 1) {
            if (!isVertical) {
                width = windowWidth / nbGraphs;
                height = Math.min(height, width / graphRatio) + graphMarginTop + graphMarginBottom + graphExtraPadding;
            }
        }
    }
    let ratio = (height / width).toFixed(2);
    if (width > height) {
        ratio = (width / height).toFixed(2);
    }
    width = Math.round(width);
    height = Math.round(height);

    console.info(
        'Window(' +
            windowHeight +
            ', ' +
            windowHeight +
            ') and width=' +
            width +
            ' heigth=' +
            height +
            ' ratio=' +
            ratio +
            '#graphs=' +
            nbGraphs
    );

    return [width, height];
}

function showMinMaxMeasurements(datas) {
    let results = new Map();
    for (let i in datas) {
        let speaker_name = 'Speaker';
        if (datas[i].legendgrouptitle && datas[i].legendgrouptitle.text !== null) {
            speaker_name = datas[i].legendgrouptitle.text;
        }
        if (datas[i].x && datas[i].x.length > 0) {
            if (results.has(speaker_name)) {
                results.set(speaker_name, Math.min(results.get(speaker_name), datas[i].x[0]));
            } else {
                results.set(speaker_name, datas[i].x[0]);
            }
        }
    }
    return results;
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
        isGraph: false,
        isSpin: false,
        isRadar: false,
        isSurface: true,
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

function setGraphOptions(inputGraphsData, windowWidth, windowHeight, outputGraphProperties, outputNumberGraphs) {
    let datas = null;
    let layout = null;
    let config = null;
    // console.log('layout and data: ' + inputGraphsData.length + ' w=' + windowWidth + ' h=' + windowHeight);
    if (inputGraphsData.length === 1) {
        layout = inputGraphsData[0].layout;
        datas = inputGraphsData[0].data;
    } else if (inputGraphsData.length === 2) {
        if (inputGraphsData[0] != null && inputGraphsData[1] != null) {
            layout = inputGraphsData[0].layout;
            datas = inputGraphsData[0].data.concat(inputGraphsData[1].data);
        } else if (inputGraphsData[0] != null) {
            layout = inputGraphsData[0].layout;
            datas = inputGraphsData[0].data;
        } else if (inputGraphsData[1] != null) {
            layout = inputGraphsData[1].layout;
            datas = inputGraphsData[1].data;
        }
    }

    const isVertical = isDisplayVertical();
    const isCompact = isDisplayCompact();

    let fontDelta = 0;
    if (!isCompact) {
        fontDelta = Math.round(windowWidth / 300);
    }

    function displayMeasurementsLimits(datas) {
        let shapes = [];
        const mins = showMinMaxMeasurements(datas);
        let title = '';
        mins.forEach((min_freq, speaker_name) => {
            if (min_freq > 40) {
                if (title.length > 1) {
                    title += '<br>';
                }
                title += 'No data below ' + Math.round(min_freq) + 'Hz';
                if (speaker_name !== 'Speaker') {
                    title += ' for ' + speaker_name;
                }
            }
        });
        let i = 0;
        mins.forEach((min_freq) => {
            // or maybe you need , _
            if (min_freq > 40) {
                let shape = {
                    type: 'rect',
                    xref: 'x',
                    yref: 'y',
                    x0: 20,
                    y0: -45,
                    x1: min_freq,
                    y1: 5,
                    fillcolor: '#d3d3d3',
                    opacity: 0.2,
                    line: { width: 2 },
                };
                if (i == 0) {
                    shape.label = {
                        text: title,
                        font: { size: fontSizeH5, color: 'green' },
                        textposition: 'top center',
                    };
                }
                shapes.push(shape);
                i += 1;
            }
        });
        return shapes;
    }

    function computeXaxis() {
        if (layout?.axis && layout.xaxis.title) {
            layout.xaxis.title.text = 'SPL (dB) v.s. Frequency (Hz)';
            layout.xaxis.title.font = {
                size: fontSizeH6,
                color: '#000',
            };
            layout.xaxis.automargin = 'height';
            layout.xaxis.side = 'bottom';
        }
        if (isCompact) {
            if (isVertical && layout?.yaxis && layout.yaxis.title) {
                const freq_min = Math.round(Math.pow(10, layout.xaxis.range[0]));
                const freq_max = Math.round(Math.pow(10, layout.xaxis.range[1]));
                let title = '';
                if (layout?.yaxis.title.text === 'Angle') {
                    title =
                        'Angle [' +
                        layout.yaxis.range[0] +
                        'º, ' +
                        layout.yaxis.range[1] +
                        'º]) v.s. Frequency (Hz [' +
                        freq_min +
                        ', ' +
                        freq_max +
                        ']).';
                } else {
                    title =
                        'SPL (dB [' +
                        layout.yaxis.range[0] +
                        ', ' +
                        layout.yaxis.range[1] +
                        ']) v.s. Frequency (Hz [' +
                        freq_min +
                        ', ' +
                        freq_max +
                        ']).';
                }
                layout.xaxis.title.text = title;
                layout.xaxis.title.standoff = 0;
            }
        }
    }

    function computeYaxis() {
        // hide axis to recover some space on mobile
        if (isCompact && isVertical) {
            if (layout.yaxis) {
                layout.yaxis.title = null;
                layout.yaxis.showticklabels = false;
                layout.yaxis.automargin = 'height';
            }
            if (layout.yaxis2) {
                layout.yaxis2.title = null;
                layout.yaxis2.showticklabels = false;
            }
        }
        if (layout.yaxis) {
            layout.yaxis.dtick = 1;
        }
    }

    function computeTitle() {
        let title = '';
        let pos0for = -1;
        let pos0by = -1;
        let speaker0 = '';
        let version0 = '';
        if (inputGraphsData[0] && inputGraphsData[0]?.layout.title.text) {
            title = inputGraphsData[0].layout.title.text;
            pos0for = inputGraphsData[0].layout.title.text.indexOf(' for ');
            pos0by = inputGraphsData[0].layout.title.text.indexOf(' measured by ');
            speaker0 = inputGraphsData[0].layout.title.text.slice(pos0for, pos0by);
            version0 = inputGraphsData[0].layout.title.text.slice(pos0by + 13);
        }
        if (outputNumberGraphs === 1 && inputGraphsData[1] && inputGraphsData[1]?.layout.title.text) {
            title += '<br> v.s. ' + inputGraphsData[1].layout.title.text;
            const pos1for = inputGraphsData[1].layout.title.text.indexOf(' for ');
            const pos1by = inputGraphsData[1].layout.title.text.indexOf(' measured by ');
            const speaker1 = inputGraphsData[1].layout.title.text.slice(pos1for, pos1by);
            const version1 = inputGraphsData[1].layout.title.text.slice(pos1by + 13);
            if (speaker0 === speaker1) {
                // if we have 1 speaker with 2 measurements, add some infos to make the difference explicit
                datas[0].legendgrouptitle.text += ' (' + version0 + ')';
                const offset = datas.length / 2;
                datas[offset].legendgrouptitle.text += ' (' + version1 + ')';
            }
        }
        if (title === '' && datas[0]?.legendgrouptitle.title) {
            title = datas[0].legendgrouptitle.text;
        }
        if (isCompact) {
            layout.title.font = {
                size: fontSizeH3,
                color: '#000',
            };
            if (outputNumberGraphs === 1) {
                // split title on 2 lines
                const measured_pos = title.indexOf(' measured ');
                if (measured_pos !== -1) {
                    const vs_pos = title.indexOf(' v.s. ');
                    if (vs_pos !== -1) {
                    } else {
                        title = title.slice(0, measured_pos) + ' <br>' + title.slice(measured_pos + 1);
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
                    size: fontSizeH1,
                    color: '#000',
                },
                xref: 'paper',
                xanchor: 'center',
                // title start sligthly on the right
                x: 0.5,
                // keep title below modBar if title is long
                // yref: 'paper',
                // yanchor: 'top',
                // y: 1.15,
            };
        }
    }

    function computeMargin() {
        if (isCompact) {
            // get legend horizontal below the graph
            layout.margin = {
                l: 10,
                r: 10,
                t: graphMarginTop / 2,
                b: graphMarginBottom / 2,
            };
        } else {
            // right margin depends on a if we have a second axis or not.
            let offsetSecondYAxis = 25;
            if (layout.yaxis2) {
                offsetSecondYAxis = 0;
            }
            if (isVertical) {
                layout.margin = {
                    l: graphMarginLeft,
                    r: graphMarginRight + offsetSecondYAxis,
                    t: graphMarginTop,
                    b: graphMarginBottom,
                };
            } else {
                layout.margin = {
                    l: graphMarginLeft,
                    r: graphMarginRight,
                    t: graphMarginTop,
                    b: graphMarginBottom,
                };
            }
        }
        if (outputGraphProperties.isGlobe) {
            layout.margin.t += 50;
        }
        if (outputGraphProperties.isSurface) {
            layout.margin.t += 30;
            layout.margin.b += 100;
        }
        if (outputGraphProperties.isRadar) {
            layout.margin.t += 100;
        }
        if (outputGraphProperties.isSpin && isVertical) {
            layout.margin.b += 100;
        }
    }

    function computeLegend() {
        const y_shift = 0.3;
        layout.legend = {
            orientation: 'h',
            y: -y_shift,
            x: 0.5,
            xref: 'container',
            xanchor: 'center',
            yanchor: 'bottom',
            yref: 'container',
            groupclick: 'toggleitem',
        };
        if (!isCompact && !isVertical) {
            layout.legend.orientation = 'v';
            layout.legend.y = 1.0;
            layout.legend.x = 0.85;
            layout.legend.xanchor = 'bottom';
            layout.legend.yanchor = 'top';
            layout.legend.width = graphLegendWidth;
        }
        // how many columns in legend?
        const groups = new Set();
        for (let k = 0; k < datas.length; k++) {
            if (datas[k].legendgroup) {
                groups.add(datas[k].legendgroup);
            }
        }
        const countColumns = Array.from(groups).length;
        if (outputNumberGraphs === 1 && isVertical) {
            for (let k = 0; k < datas.length; k++) {
                datas[k].legendgroup = null;
                datas[k].legendgrouptitle = null;
            }
        } else if (!isCompact) {
            for (let k = 0; k < datas.length; k++) {
                const title = datas[k].legendgrouptitle;
                if (title?.text) {
                    const pos_vs = title.text.indexOf(' for ');
                    if (pos_vs !== -1) {
                        datas[k].legendgrouptitle.text = title.text.slice(0, pos_vs);
                    }
                }
            }
        }
        if (outputGraphProperties.isRadar || outputGraphProperties.isGlobe) {
            layout.height += (datas.length * 20) / countColumns;
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
            layout.polar4.domain.y = [start, start + len * 1];
            layout.polar3.domain.y = [start + len * 2 + gap * 2, start + len * 3 + gap * 2];
            layout.polar2.domain.y = [start + len * 1 + gap, start + len * 2 + gap];
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

    function computeLabel() {
        if (isCompact) {
            // shorten labels
            for (let k = 0; k < datas.length; k++) {
                // remove group
                datas[k].legendgroup = null;
                datas[k].legendgrouptitle = null;
                if (datas[k].name && labelShort[datas[k].name]) {
                    // shorten labels
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
                datas[k].colorbar.xanchor = 'center';
                datas[k].colorbar.x = 0.5;
                datas[k].colorbar.xpad = 20;
                datas[k].colorbar.yref = 'paper';
                datas[k].colorbar.yanchor = 'bottom';
                datas[k].colorbar.y = -0.4;
                if (isCompact) {
                    datas[k].colorbar.y = -0.7;
                }
                datas[k].colorbar.ypad = 20;
                datas[k].colorbar.len = 0.8;
                datas[k].colorbar.lenmode = 'fraction';
                datas[k].colorbar.thickness = 15;
                datas[k].colorbar.thicknessmode = 'pixels';
                datas[k].colorbar.orientation = 'h';
                datas[k].colorbar.title = {
                    font: {
                        size: fontSizeH4,
                    },
                    side: 'bottom',
                };
            }
        }
    }

    if (layout != null && datas != null) {
        [layout.width, layout.height] = computeDims(windowWidth, windowHeight, isVertical, isCompact, outputNumberGraphs);
        computeFont();
        computeXaxis();
        computeYaxis();
        computeTitle(); // before legend
        computeLegend();
        computeLabel();
        computeModbar();
        computeColorbar();
        computePolar();
        layout.shapes = displayMeasurementsLimits(datas);
        computeMargin(); // must be last
    } else {
        // should be a pop up
        console.log('Error: No graph is available');
    }
    return { data: datas, layout: layout, config: config };
}

export function setCEA2034(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setCEA2034 got ' + speakerGraphs.length + ' graphs')
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
            }
        }
    }
    return [setGraphOptions(speakerGraphs, width, height, 1, GraphProperties[measurement])];
}

export function setGraph(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setGraph got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    for (const i in speakerGraphs) {
        if (speakerGraphs[i] != null) {
            // console.log('adding graph ' + i)
            for (const trace in speakerGraphs[i].data) {
                const name = speakerGraphs[i].data[trace].name;
                // hide yellow bands since when you have more than one it is difficult to see the graphs
                // also remove the midrange lines for the same reason
                if (
                    i > 0 && // keep only the first one
                    name != null &&
                    (name == 'Band ±3dB' ||
                        name == 'Band ±1.5dB' ||
                        name == 'Midrange Band +3dB' ||
                        name == 'Midrange Band -3dB')
                ) {
                    speakerGraphs[i].data[trace].visible = false;
                }
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
    return [setGraphOptions(speakerGraphs, width, height, GraphProperties[measurement])];
}

export function setRadar(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setRadar got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    for (const i in speakerGraphs) {
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
            }
        }
    }
    const options = setGraphOptions(speakerGraphs, width, height, 1);
    options.layout.height += 20 * 12;
    options.layout.margin.t += 40;
    return [options];
}

export function setContour(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setContour got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            for (const j in speakerGraphs[i].data) {
                speakerGraphs[i].data[j].legendgroup = 'speaker' + i;
                speakerGraphs[i].data[j].legendgrouptitle = { text: speakerNames[i] };
            }
            let options = setGraphOptions([{ data: speakerGraphs[i].data, layout: speakerGraphs[i].layout }], width, height, 2);
            options.layout.margin.t = graphMarginTop / 2;
            if (isDisplayCompact() && speakerGraphs.length > 1) {
                if (i === 0) {
                    // remove the axis to have the 2 graphs closer together
                    options.layout.xaxis.visible = false;
                    options.layout.showlegend = false;
                    options.data[0].showscale = false;
                    options.layout.margin.b = 0;
                } else {
                    options.data[0].colorbar.y = -0.6;
                }
            }
            // this shapes are not working in 3D thus removing them
            if (options.layout && options.layout?.shapes) {
                options.layout.shapes = null;
            }
            graphsConfigs.push(options);
        }
    }
    return graphsConfigs;
}

export function setGlobe(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setGlobe ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            let polarData = [];
            for (const j in speakerGraphs[i].data) {
                const freq = speakerGraphs[i].data[j].x;
                const angle = speakerGraphs[i].data[j].y;
                const spl = speakerGraphs[i].data[j].z;
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
                        let val = spl[k2][k1];
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
                        y: -0.5,
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
                speakerGraphs.length
            );
            if (speakerGraphs.length > 1 && i == 0) {
                options.layout.margin.l += 60;
                options.layout.margin.r += 60;
            }
            graphsConfigs.push(options);
        }
    }
    return graphsConfigs;
}

export function setSurface(measurement, speakerNames, speakerGraphs, width, height) {
    // console.log('setSurface ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
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
