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
const graphLarge = 800;

const graphRatio = 4.0 / 3.0;

const graphMarginLeft = 30;
const graphMarginRight = 30;

const graphMarginTop = 60;
const graphMarginBottom = 30;
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
    return windowWidth <= windowHeight;

}

export function isDisplayCompact() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    return windowWidth < graphSmall || windowHeight < graphSmall;

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
            width = windowWidth - graphMarginLeft - graphMarginRight;
            const graphWidth = Math.min(graphLarge, width - 2 * graphExtraPadding);
            height = graphWidth / graphRatio + graphMarginTop + graphMarginBottom;
        } else {
            width = windowWidth - graphMarginRight - graphMarginLeft;
            const graphWidth = Math.min(graphLarge, width - graphLegendWidth - 2 * graphExtraPadding);
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
            windowWidth +
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

    function computeXaxis() {
        if (layout.axis && layout.xaxis.title) {
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
        }
        if (outputGraphProperties.isRadar) {
            layout.margin.t += 100;
        }
        if (outputGraphProperties.isSpin && isVertical) {
            layout.margin.b += 150;
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
        if (!isCompact) {
            if (!isVertical) {
                layout.legend.orientation = 'v';
                layout.legend.y = 0.5;
                layout.legend.x = 0.95;
                layout.legend.xanchor = 'bottom';
                layout.legend.yanchor = 'middle';
                layout.legend.entrywidth = graphLegendWidth;
            }
            /* not working as is
	       } else {
		layout.legend.orientation = 'h';
		layout.legend.y = y_shift;
		layout.legend.x = 0.5;
		layout.legend.xanchor = 'center';
		layout.legend.yanchor = 'bottom';
		if (outputGraphProperties.isSpin) {
		    layout.height += 200;
		    layout.margin.bottom -= 100;
		    }
		    }
*/
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
                    const pos_vs = title.text.indexOf(' v.s. ');
                    if (pos_vs !== -1) {
                        datas[k].legendgrouptitle.text = title.text.slice(0, pos_vs);
                    }
                    const pos_for = title.text.indexOf(' for ');
                    if (pos_for !== -1) {
                        datas[k].legendgrouptitle.text = title.text.slice(0, pos_for);
                    }
                }
            }
        }
        if (outputGraphProperties.isRadar || outputGraphProperties.isGlobe) {
            layout.height += (datas.length * 20) / countColumns;
        }

        if (outputGraphProperties.isSpin && layout.legend2) {
            layout.legend2.title.font.size = 12;
            layout.legend2.font.size = 10;
        }

        /*
	if (outputGraphProperties.isSpin && layout.legend2 && !isCompact && isVertical) {
	    layout.legend.x = 0.2;
	    layout.legend2.x = 0.7;
	    layout.legend2.y = layout.legend.y;
	    layout.legend2.xanchor = layout.legend.xanchor;
	    layout.legend2.yanchor = layout.legend.yanchor;
	    layout.legend2.xref = layout.legend.xref;
	    layout.legend2.yref = layout.legend.yref;
	    layout.legend2.orientation = 'h';
	    layout.legend2.title = null;
    }
*/
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
            layout.polar4.domain.y = [start, start + len ];
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
                datas[k].colorbar.yref = 'paper';
                if (isVertical) {
                    datas[k].colorbar.orientation = 'h';
                    datas[k].colorbar.xanchor = 'center';
                    datas[k].colorbar.x = 0.5;
                    datas[k].colorbar.yanchor = 'bottom';
                    datas[k].colorbar.y = -0.3;
                    if (isCompact) {
                        datas[k].colorbar.y = -0.7;
                    }
                } else {
                    datas[k].colorbar.orientation = 'v';
                    datas[k].colorbar.xanchor = 'top';
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
                    "size": fontSizeH6,
                };
                datas[k].colorbar.title = {
                        "text": 'dB (SPL)',
                        "font": {
                            "size": fontSizeH5,
                        },
                        "side": 'bottom',
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
                if (speakerGraphs.length > 1) {
                    // hide recommended zones by default
                    if (
                        'name' in speakerGraphs[i].data[trace] &&
                        speakerGraphs[i].data[trace].name.indexOf('recommended') === 0
                    ) {
                        speakerGraphs[i].data[trace]['visible'] = 'legendonly';
                    } else if ('line' in speakerGraphs[i].data[trace] && speakerGraphs[i].data[trace].x.length < 10) {
                        speakerGraphs[i].data[trace]['visible'] = false;
                    }
                }
            }
        }
    }
    let option = setGraphOptions(speakerGraphs, width, height, 1, GraphProperties[measurement]);
    option.layout.height += 4 * 14;

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

    // hide annotations if we compare 2 graphs
    if (speakerGraphs.length > 1) {
        if ('annotations' in option.layout) {
            for (let i = 0; i < option.layout.annotations.length; i++) {
                option.layout.annotations[i]['visible'] = false;
            }
        }
    }
    return [option];
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
                    speakerGraphs.length > 1 &&
                    name != null &&
                    (name === 'Band ±3dB' ||
                        name === 'Band ±1.5dB' ||
                        name === 'Midrange Band +3dB' ||
                        name === 'Midrange Band -3dB')
                ) {
                    speakerGraphs[i].data[trace].visible = 'legendonly';
                }
                if (speakerGraphs.length > 1) {
                    if (
                        'name' in speakerGraphs[i].data[trace] &&
                        speakerGraphs[i].data[trace].name.indexOf('recommended') === 0
                    ) {
                        speakerGraphs[i].data[trace]['visible'] = 'legendonly';
                    }
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
    let option = setGraphOptions(speakerGraphs, width, height, 1, GraphProperties[measurement]);
    if (measurement === 'On Axis' || measurement === 'Vertical Reflections') {
        option.layout.height -= 3 * 14;
    } else if (measurement === 'SPL Horizontal' || measurement === 'SPL Vertical') {
        option.layout.height += 6 * 14;
    } else if (measurement === 'SPL Horizontal Normalized' || measurement === 'SPL Vertical Normalized') {
        option.layout.height += 6 * 14;
    }
    return [option];
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
            let options = setGraphOptions([{ data: speakerGraphs[i].data, layout: speakerGraphs[i].layout }], width, height, 2);
            // this shapes are not working in 3D thus removing them
            if (options.layout && options.layout?.shapes) {
                options.layout.shapes = null;
            }
            graphsConfigs.push(options);
        }
    }
    if (speakerGraphs.length <= 1) {
        return graphsConfigs;
    }

    // merge the 2 graphs
    let mergedConfig = {
        data: [],
        layout: structuredClone(graphsConfigs[0].layout),
        config: structuredClone(graphsConfigs[0].config),
    };
    mergedConfig.layout.width = Math.min(600, window.innerWidth);
    if (isDisplayCompact()) {
        mergedConfig.layout.height = mergedConfig.layout.width + 280;
        mergedConfig.layout.margin = {
            t: 160, // double lines title + axis
            r: 10, // colorbar horizontal
            l: 10,
            b: 120,
        };
    } else {
        mergedConfig.layout.height = mergedConfig.layout.width + 240;
        mergedConfig.layout.margin = {
            t: 160, // double lines title + axis
            r: 100, // colorbar
        };
    }
    function split(title) {
        const pos_for = title.indexOf(' for ');
        const pos_measured = title.indexOf(' measured ');
        const measurement = title.slice(0, pos_for);
        const speaker = title.slice(pos_for + 5, pos_measured);
        const reviewer = title.slice(pos_measured + 1);
        return [measurement, speaker, reviewer];
    }
    const split0 = split(graphsConfigs[0].layout.title.text);
    const split1 = split(graphsConfigs[1].layout.title.text);
    const title = '(A) ' + split0[0] + ' ' + split0[1] + ' <br>v.s. (B) ' + split1[0] + ' ' + split1[1];
    mergedConfig.layout.title = {
        text: title,
        font: { size: 14 },
    };
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
                if (i === '0') {
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
                        trace.colorbar.x = 1.25;
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
                } else {
                    trace.showscale = false;
                }
            }
            mergedConfig.data.push(trace);
        }
    }
    const range0 = graphsConfigs[0].layout.xaxis.range;
    const range1 = graphsConfigs[1].layout.xaxis.range;
    const range = [Math.min(range0[0], range1[0]), Math.max(range0[1], range1[1])];

    mergedConfig.layout.xaxis.side = 'top';
    mergedConfig.layout.xaxis.tick = 'outside';
    mergedConfig.layout.xaxis.range = range;

    mergedConfig.layout.xaxis2.side = 'bottom';
    mergedConfig.layout.xaxis2.tick = 'outside';
    mergedConfig.layout.xaxis2.range = range;
    mergedConfig.layout.xaxis2['anchor'] = 'y2';

    mergedConfig.layout.yaxis.tick = 'outside';
    if (mergedConfig.layout.yaxis.title && mergedConfig.layout.yaxis.title.text) {
        mergedConfig.layout.yaxis.title.text = 'Angle (A)';
    }
    mergedConfig.layout.yaxis['domain'] = [0.51, 1];

    mergedConfig.layout.yaxis2.tick = 'outside';
    if (mergedConfig.layout.yaxis2.title && mergedConfig.layout.yaxis2.title.text) {
        mergedConfig.layout.yaxis2.title.text = 'Angle (B)';
    }
    mergedConfig.layout.yaxis2['domain'] = [0, 0.49];

    return [mergedConfig];
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
