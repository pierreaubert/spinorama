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

import { urlSite, metadataFilename } from './meta.js';
import { getID } from './misc.js';

export const knownMeasurements = [
    'CEA2034',
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

function processOrigin(origin) {
    if (origin.includes('Vendors-')) {
        return origin.slice(8);
    }
    return origin;
}

function processGraph(name) {
    if (name.includes('CEA2034')) {
        return 'CEA2034';
    } else if (name.includes('Globe')) {
        return name.replace('Globe', 'Contour');
    }
    return name;
}

function getOrigin(metaSpeakers, speaker, origin) {
    // console.log('getOrigin ' + speaker + ' origin=' + origin)
    const measurements = Object.keys(metaSpeakers[speaker].measurements);
    const origins = new Set();
    for (const key in measurements) {
        origins.add(metaSpeakers[speaker].measurements[measurements[key]].origin);
    }
    if (origin == null || origin === '' || !origins.has(origin)) {
        const defaultMeasurement = metaSpeakers[speaker].default_measurement;
        const defaultOrigin = metaSpeakers[speaker].measurements[defaultMeasurement].origin;
        // console.log('getOrigin default=' + defaultOrigin)
        return processOrigin(defaultOrigin);
    }
    return processOrigin(origin);
}

function getVersion(metaSpeakers, speaker, origin, version) {
    const versions = Object.keys(metaSpeakers[speaker].measurements);
    let matches = new Set();
    versions.forEach((val) => {
        const current = metaSpeakers[speaker].measurements[val];
        if (current.origin === origin || origin === '' || origin == null) {
            matches.add(val);
            matches.add(val + '_eq');
        }
    });
    if (version == null || version === '' || !matches.has(version)) {
        const defaultVersion = metaSpeakers[speaker].default_measurement;
        return defaultVersion;
    }
    return version;
}

function getSpeakerUrl(metaSpeakers, graph, speaker, origin, version) {
    // console.log('getSpeakerUrl ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)
    const url =
        urlSite +
        'speakers/' +
        speaker +
        '/' +
        getOrigin(metaSpeakers, speaker, origin) +
        '/' +
        getVersion(metaSpeakers, speaker, origin, version) +
        '/' +
        processGraph(graph) +
        '.json';
    return url;
}

export function getSpeakerData(metaSpeakers, graph, speaker, origin, version) {
    // console.log('getSpeakerData ' + graph + ' speaker=' + speaker + ' origin=' + origin + ' version=' + version)

    const url = getSpeakerUrl(metaSpeakers, graph, speaker, origin, version);
    // console.log('fetching url=' + url)
    const spec = fetch(url)
        .then((response) => response.json())
        .catch((error) => {
            console.log('ERROR getSpeaker failed for ' + url + 'with error: ' + error);
            return null;
        });
    return spec;
}

export function getAllSpeakers(metadata) {
    const metaSpeakers = {};
    const speakers = [];
    metadata.forEach((value) => {
        const speaker = value.brand + ' ' + value.model;
        speakers.push(speaker);
        metaSpeakers[speaker] = value;
    });
    return [metaSpeakers, speakers.sort()];
}

export function getMetadata() {
    const url = urlSite + 'assets/' + metadataFilename;
    // console.log('fetching url=' + url)
    const spec = fetch(url, {
        headers: {
            'Content-Encoding': 'gzip',
            'Content-Type': 'application/json',
        },
    })
        .then((response) => response.json())
        .then((data) => {
            // convert to object
            const metadata = Object.values(data);
            // console.log('metadata '+metadata.length)
            return new Map(
                metadata.map((speaker) => {
                    const key = getID(speaker.brand, speaker.model);
                    return [key, speaker];
                })
            );
        })
        .catch((error) => {
            console.log('ERROR getMetadata for ' + url + 'yield a 404 with error: ' + error);
            return null;
        });
    return spec;
}

export function getMetadataChunked() {
    const url = urlSite + 'assets/' + metadataFilename;
    // console.log('fetching url=' + url)
    const spec = fetch(url, {
        headers: {
            'Content-Encoding': 'gzip',
            'Content-Type': 'application/json',
        },
    })
        .then((response) => response.json())
        .then((data) => {
            // convert to object
            const metadata = Object.values(data);
            // console.log('metadata '+metadata.length)
            return new Map(
                metadata.map((speaker) => {
                    const key = getID(speaker.brand, speaker.model);
                    return [key, speaker];
                })
            );
        })
        .catch((error) => {
            console.log('ERROR getMetadata for ' + url + 'yield a 404 with error: ' + error);
            return null;
        });
    return spec;
}

const graphSmall = 550;
const graphLarge = 1200;
const graphRatio = 1.3;
const graphMarginTop = 30;
const graphMarginBottom = 60;
const graphTitle = 40;
const graphSpacer = graphMarginTop + graphMarginBottom + graphTitle;
const graphExtraPadding = 40;

export function isVertical() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    if (windowWidth <= windowHeight) {
        return true;
    }
    return false;
}

export function isCompact() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    if (windowWidth < graphSmall || windowHeight < graphSmall) {
        return true;
    }
    return false;
}

function computeDims(windowWidth, windowHeight, is_vertical, is_compact, nb_graphs) {
    let width = windowWidth;
    let height = windowHeight;
    if (is_compact) {
        if (is_vertical) {
            // portraint
            width = windowWidth;
            height = Math.min(windowHeight, windowWidth / graphRatio + graphSpacer);
        } else {
            // landscape
            width = windowWidth - graphExtraPadding;
            height = Math.min(windowHeight, windowWidth / graphRatio + graphSpacer);
        }
    } else {
        if (is_vertical) {
            width = Math.min(graphLarge, windowWidth);
            height = windowWidth / graphRatio + graphSpacer;
            if (height > windowHeight) {
                height = windowHeight;
                width = height * graphRatio - graphSpacer;
            }
        } else {
            height = Math.min(graphLarge, windowHeight);
            width = windowHeight * graphRatio - graphSpacer;
            if (width > windowWidth) {
                width = windowWidth - graphSpacer;
                height = Math.min(windowHeight, width / graphRatio);
            }
        }
        // if (nb_graphs > 1) {
        //    if (is_vertical) {
        //        height /= nb_graphs;
        //        width = height * graphRatio;
        //    } else {
        //        width /= nb_graphs;
        //        height = width / graphRatio;
        //    }
        // }
    }
    width = Math.round(width);
    height = Math.round(height);
    let ratio = (height / width).toFixed(2);
    if (width > height) {
        ratio = (width / height).toFixed(2);
    }
    console.log(
        'DEBUG: Window(' +
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
            nb_graphs
    );
    return [width, height];
}

function setGraphOptions(spin, windowWidth, windowHeight, nb_graphs) {
    let datas = null;
    let layout = null;
    let config = null;
    // console.log('layout and data: ' + spin.length + ' w=' + windowWidth + ' h=' + windowHeight);
    if (spin.length === 1) {
        layout = spin[0].layout;
        datas = spin[0].data;
    } else if (spin.length === 2) {
        if (spin[0] != null && spin[1] != null) {
            layout = spin[0].layout;
            datas = spin[0].data.concat(spin[1].data);
        } else if (spin[0] != null) {
            layout = spin[0].layout;
            datas = spin[0].data;
        } else if (spin[1] != null) {
            layout = spin[1].layout;
            datas = spin[1].data;
        }
    }

    const is_vertical = isVertical();
    const is_compact = isCompact();
    const single_graph = nb_graphs == 1;
    let is_radar = false;
    let is_globe = false;
    let is_spin = false;
    let fontDelta = 0;
    if (!is_compact) {
        fontDelta = Math.round(windowWidth / 300);
    }

    function computeXaxis() {
        if (layout.xaxis && layout.xaxis.title) {
            layout.xaxis.title.text = 'SPL (dB) v.s. Frequency (Hz)';
            layout.xaxis.title.font = {
                size: 10 + fontDelta,
                color: '#000',
            };
            layout.xaxis.automargin = 'height';
            layout.xaxis.side = 'bottom';
        }
        if (is_compact) {
            if (is_vertical && layout.yaxis && layout.yaxis.title) {
                const freq_min = Math.round(Math.pow(10, layout.xaxis.range[0]));
                const freq_max = Math.round(Math.pow(10, layout.xaxis.range[1]));
                let title = '';
                if (layout.yaxis.title.text && layout.yaxis.title.text === 'Angle') {
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
        if (is_compact && is_vertical) {
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
        if (spin[0] && spin[0].layout && spin[0].layout.title && spin[0].layout.title.text) {
            title = spin[0].layout.title.text;
        }
        if (!single_graph && spin[1] && spin[1].layout && spin[1].layout.title && spin[1].layout.title.text) {
            title += '<br> v.s. ' + spin[1].layout.title.text;
        }
        if (title === '' && datas[0].legendgrouptitle && datas[0].legendgrouptitle.title) {
            title = datas[0].legendgrouptitle.text;
        }
        if (title.indexOf('CEA2034') !== -1) {
            is_spin = true;
        }
        if (is_compact) {
            layout.title.font = {
                size: 10 + fontDelta,
                color: '#000',
            };
            if (single_graph) {
                // split title on 2 lines
                const measured_pos = title.indexOf(' measured ');
                if (measured_pos !== -1) {
                    title = title.slice(0, measured_pos) + ' <br>' + title.slice(measured_pos + 1);
                }
            }
            layout.title = {
                text: title,
                font: {
                    size: 10 + fontDelta,
                    color: '#000',
                },
                xref: 'paper',
                xanchor: 'left',
                // title start sligthly on the right
                x: 0.0,
                // keep title below modBar if title is long
                // yref: 'paper',
                // yanchor: 'top',
                // y: 1.15,
            };
        } else {
            layout.title = {
                text: title,
                font: {
                    size: 12 + fontDelta,
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
        if (is_compact) {
            // get legend horizontal below the graph
            layout.margin = {
                l: 10,
                r: 10,
                t: graphMarginTop,
                b: graphMarginBottom + 10,
            };
        } else {
            // right margin depends on a if we have a second axis or not.
            let offset = 25;
            if (layout.yaxis2) {
                offset = 0;
            }
            layout.margin = {
                l: 15,
                r: 15 + offset,
                t: graphMarginTop,
                b: graphMarginBottom * 2,
            };
        }
        if (is_globe) {
            layout.margin.t += 50;
        }
        if (is_radar) {
            layout.margin.t += 100;
        }
        if (is_spin) {
            layout.margin.b += 100;
            layout.height += 100;
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
        // how many columns in legend?
        const groups = new Set();
        for (let k = 0; k < datas.length; k++) {
            if (datas[k].legendgroup) {
                groups.add(datas[k].legendgroup);
            }
        }
        const countColumns = Array.from(groups).length;
        if (single_graph) {
            for (let k = 0; k < datas.length; k++) {
                datas[k].legendgroup = null;
                datas[k].legendgrouptitle = null;
            }
        } else if (!is_compact && layout.width > graphLarge) {
            for (let k = 0; k < datas.length; k++) {
                const title = datas[k].legendgrouptitle;
                if (title && title.text) {
                    const pos_vs = title.text.indexOf(' v.s. ');
                    if (pos_vs !== -1) {
                        datas[k].legendgrouptitle.text = title.text.slice(0, pos_vs);
                    }
                }
            }
        }
        if (is_radar || is_globe) {
            layout.height += (datas.length * 20) / countColumns;
        }
    }

    function computePolar() {
        const polars = ['polar', 'polar2', 'polar3', 'polar4'];
        if (layout['polar4'] && is_compact) {
            is_radar = true;
            layout.height = layout.width * 4;
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
            layout.polar2.domain.y = [start + len * 1 + gap, start + len * 2 + gap];
            layout.polar3.domain.y = [start + len * 2 + gap * 2, start + len * 3 + gap * 2];
            layout.polar.domain.y = [start + len * 3 + gap * 3, start + len * 4 + gap * 3];
            // move legend up
            layout.legend.x = 0.5;
            layout.legend.xanchor = 'center';
            layout.legend.y = 0.0;
        }
        for (let i in polars) {
            const polar = polars[i];
            if (!layout[polar]) {
                layout[polar] = {};
                is_globe = true;
            }
            layout[polar].bargap = 0;
            layout[polar].hole = 0.05;
        }
    }

    function computeLabel() {
        if (is_compact) {
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
        if (is_compact) {
            // remove mod bar
            config = {
                responsive: true,
                displayModeBar: false,
            };
        } else {
            layout.modebar = {
                orientation: 'v',
            };
            config = {
                responsive: true,
                displayModeBar: true,
            };
        }
    }

    function computeFont() {
        if (is_compact) {
            layout.font = { size: 10 };
        } else {
            layout.font = { size: 12 + fontDelta };
        }
    }

    function computeColorbar() {
        for (let k = 0; k < datas.length; k++) {
            if (datas[k].colorbar) {
                datas[k].colorbar.x = 0.5;
                datas[k].colorbar.xanchor = 'center';
                datas[k].colorbar.y = -0.35;
                datas[k].colorbar.yanchor = 'bottom';
                datas[k].colorbar.len = 1.0;
                datas[k].colorbar.lenmode = 'fraction';
                datas[k].colorbar.thickness = 15;
                datas[k].colorbar.thicknessmode = 'pixels';
                datas[k].colorbar.orientation = 'h';
                datas[k].colorbar.title = {
                    text: 'Contours: SPL (3dB steps)',
                    font: {
                        size: 10 + fontDelta,
                    },
                    side: 'bottom',
                };
            }
        }
    }

    if (layout != null && datas != null) {
        [layout.width, layout.height] = computeDims(windowWidth, windowHeight, is_vertical, is_compact, nb_graphs);
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
        console.log('Error: No graph available');
    }
    return { data: datas, layout: layout, config: config };
}

export function setCEA2034(speakerNames, speakerGraphs, width, height) {
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
    return [setGraphOptions(speakerGraphs, width, height, speakerGraphs.length)];
}

export function setGraph(speakerNames, speakerGraphs, width, height) {
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
    return [setGraphOptions(speakerGraphs, width, height, speakerGraphs.length)];
}

export function setRadar(speakerNames, speakerGraphs, width, height) {
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

export function setContour(speakerNames, speakerGraphs, width, height) {
    // console.log('setContour got ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            for (const j in speakerGraphs[i].data) {
                speakerGraphs[i].data[j].legendgroup = 'speaker' + i;
                speakerGraphs[i].data[j].legendgrouptitle = { text: speakerNames[i] };
            }
            let options = setGraphOptions(
                [{ data: speakerGraphs[i].data, layout: speakerGraphs[i].layout }],
                width,
                height,
                speakerGraphs.length
            );
            if (i == 0 && isCompact() && speakerGraphs.length > 1) {
                // remove the axis to have the 2 graphs closer together
                options.layout.xaxis.visible = false;
                options.layout.showlegend = false;
                options.data[0].showscale = false;
                options.layout.margin.b = 0;
                options.layout.margin.l = 15; // annoyingly the second graph has a label that shift the graphs
                // size                  xaxis colorbar xticks
                options.layout.height -= 14.5 + 63.5 + 44;
            }
            graphsConfigs.push(options);
        }
    }

    return graphsConfigs;
}

export function setGlobe(speakerNames, speakerGraphs, width, height) {
    // console.log('setGlobe ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            let polarData = [];
            for (const j in speakerGraphs[i].data) {
                const x = speakerGraphs[i].data[j].x;
                const y = speakerGraphs[i].data[j].y;
                const z = speakerGraphs[i].data[j].z;
                if (!z) {
                    continue;
                }
                const r = [];
                // r is x (len of y times)
                for (let k1 = 0; k1 < x.length; k1++) {
                    for (let k2 = 0; k2 < y.length - 1; k2++) {
                        r.push(Math.log10(x[k1]));
                    }
                }
                // theta is y (len of x times)
                let theta = [];
                for (let k = 0; k < x.length; k++) {
                    for (let k2 = 0; k2 < y.length - 1; k2++) {
                        theta.push(y[k2]);
                    }
                }
                theta = theta.flat();
                // color is z unravelled
                // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].x=' + x.length)
                // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].y=' + y.length)
                // console.log('debug: len(speakerGraphs[' + i + '].data[' + j + '].z=' + z.length)
                const color = [];
                for (let k1 = 0; k1 < x.length; k1++) {
                    for (let k2 = 0; k2 < y.length - 1; k2++) {
                        let val = z[k2][k1];
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
                                size: 11,
                            },
                            text: 'dB (SPL)',
                            side: 'bottom',
                        },
                        orientation: 'h',
                        xanchor: 'center',
                        yanchor: 'bottom',
                        yref: 'container',
                        y: 0.0,
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
                options.data[0].marker.showscale = false;
                options.layout.margin.l += 60;
                options.layout.margin.r += 60;
            }
            graphsConfigs.push(options);
        }
    }
    return graphsConfigs;
}

export function setSurface(speakerNames, speakerGraphs, width, height) {
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
            graphsConfigs.push(options);
        }
    }
    return graphsConfigs;
}

export function assignOptions(textArray, selector, textSelected) {
    // console.log('assignOptions: selected = ' + textSelected)
    // textArray.forEach( item => // console.log('assignOptions: '+item));
    while (selector.firstChild) {
        selector.firstChild.remove();
    }
    for (let i = 0; i < textArray.length; i++) {
        const currentOption = document.createElement('option');
        currentOption.value = textArray[i];
        currentOption.text = textArray[i].replace('Vendors-', '').replace('vendor-pattern-', 'Pattern ');
        if (textArray[i] === textSelected) {
            currentOption.selected = true;
        }
        if (textArray.length === 1) {
            currentOption.disabled = true;
        }
        selector.appendChild(currentOption);
    }
}
