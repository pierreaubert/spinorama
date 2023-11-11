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

import { urlSite } from './misc.js';
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
    if (origin == null || origin === '') {
        const defaultMeasurement = metaSpeakers[speaker].default_measurement;
        const defaultOrigin = metaSpeakers[speaker].measurements[defaultMeasurement].origin;
        // console.log('getOrigin default=' + defaultOrigin)
        return processOrigin(defaultOrigin);
    }
    return processOrigin(origin);
}

function getVersion(metaSpeakers, speaker, origin, version) {
    if (version == null || version === '') {
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
    const url = urlSite + 'assets/metadata.json';
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
const graphLarge = 900;
const graphRatio = 1.414;
const graphMarginTop = 30;
const graphMarginBottom = 40;
const graphTitle = 30;
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

function computeDims(windowWidth, windowHeight, is_vertical, is_compact) {
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
            // portraint
            width = Math.min(graphLarge, windowWidth);
            height = Math.min(windowHeight, windowWidth / graphRatio + graphSpacer);
        } else {
            // landscape
            height = Math.min(windowHeight, windowWidth / 2);
            width = Math.min(windowWidth, windowHeight / graphRatio + graphSpacer);
        }
    }
    return [width, height];
}

function setGraphOptions(spin, windowWidth, windowHeight) {
    let datas = null;
    let layout = null;
    let config = null;
    // console.log('layout and data: ' + spin.length + ' w='+windowWidth+' h='+windowHeight)
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

    function computeXaxis() {
        if (layout.xaxis) {
            layout.xaxis.title = 'SPL (dB) v.s. Frequency (Hz)';
            layout.xaxis.font = {
                size: 10,
                color: '#000',
            };
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
                layout.xaxis.title = title;
            }
            if (layout.xaxis) {
                layout.xaxis.autotick = false;
            }
        }
    }

    function computeYaxis() {
        // hide axis to recover some space on mobile
        if (is_compact && is_vertical) {
            if (layout.yaxis) {
                layout.yaxis.visible = false;
            }
            if (layout.yaxis2) {
                layout.yaxis2.visible = false;
            }
        }
        if (layout.yaxis) {
            layout.yaxis.dtick = 1;
        }
    }

    function computeTitle() {
        let title = '';
        if (spin[0].layout && spin[0].layout.title && spin[0].layout.title.text) {
            title = spin[0].layout.title.text;
        }
        if (spin.length === 2 && spin[1].layout && spin[1].layout.title && spin[1].layout.title.text) {
            title += '<br> v.s. ' + spin[0].layout.title.text;
        }

        if (is_compact) {
            layout.title.font = {
                size: 10,
                color: '#000',
            };
            if (title === '' && datas[0].legendgrouptitle) {
                title = datas[0].legendgrouptitle.text;
            }
            layout.title = {
                text: title,
                font: {
                    size: 10 + windowWidth / 300,
                    color: '#000',
                },
                xref: 'paper',
                // title start sligthly on the right
                x: 0.0,
                // keep title below modBar if title is long
                y: 0.975,
            };
        } else {
            layout.title.font = {
                size: 12 + windowWidth / 300,
                color: '#000',
            };
        }
    }

    function computeMargin() {
        if (is_compact) {
            if (is_vertical) {
                // get legend horizontal below the graph
                layout.margin = {
                    l: 5,
                    r: 5,
                    t: graphMarginTop,
                    b: graphMarginBottom,
                };
            } else {
                // get legend horizontal below the graph
                layout.margin = {
                    l: 15,
                    r: 15,
                    t: 20,
                    b: graphMarginBottom,
                };
            }
        } else {
            // right margin depends on a if we have a second axis or not.
            let offset = 25;
            if (layout.yaxis2) {
                offset = 0;
            }
            layout.margin = {
                l: 15,
                r: 15 + offset,
                t: graphMarginTop * 2,
                b: graphMarginBottom,
            };
        }
    }

    function computeLegend() {
        if (is_vertical) {
            layout.legend = {
                orientation: 'h',
                y: -0.2,
                x: 0,
                xanchor: 'bottom',
                yanchor: 'left',
                groupclick: 'toggleitem',
            };
        } else {
            layout.legend = {
                orientation: 'h',
                y: -0.25,
                x: 0.5,
                xanchor: 'bottom',
                yanchor: 'center',
                groupclick: 'toggleitem',
            };
        }
        if (!is_compact) {
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
            layout.font = { size: 11 + windowWidth / 300 };
        }
    }

    function computeColorbar() {
        if (is_compact) {
            for (let k = 0; k < datas.length; k++) {
                if (datas[k].colorbar) {
                    datas[k].colorbar.x = 0.5;
                    datas[k].colorbar.xanchor = 'center';
                    // datas[k].colorbar.xref = 'container';
                    datas[k].colorbar.y = -0.45;
                    datas[k].colorbar.yanchor = 'bottom';
                    datas[k].colorbar.len = 1.0;
                    datas[k].colorbar.lenmode = 'fraction';
                    datas[k].colorbar.thickness = 15;
                    datas[k].colorbar.thicknessmode = 'pixels';
                    datas[k].colorbar.orientation = 'h';
                    datas[k].colorbar.title = {
                        text: 'Contours: SPL (3dB steps)',
                        font: {
                            size: 10,
                        },
                        side: 'bottom',
                    };
                }
            }
        }
    }

    if (layout != null && datas != null) {
        [layout.width, layout.height] = computeDims(windowWidth, windowHeight, is_vertical, is_compact);
        computeFont();
        computeXaxis();
        computeYaxis();
        computeTitle(); // before legend
        computeLegend();
        computeLabel();
        computeModbar();
        computeColorbar();
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
    return [setGraphOptions(speakerGraphs, width, height)];
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
    return [setGraphOptions(speakerGraphs, width, height)];
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
            let options = setGraphOptions([{ data: speakerGraphs[i].data, layout: speakerGraphs[i].layout }], width, height);
            if (i == 0 && isCompact()) {
                // remove the axis to have the 2 graphs closer together
                options.layout.xaxis.visible = false;
                options.layout.showlegend = false;
                options.data[0].showscale = false;
                options.layout.margin.b = 0;
                options.layout.height -= 80; // size in pixel of xaxis + colorbar
            }
            graphsConfigs.push(options);
        }
    }

    return graphsConfigs;
}

export function setGlobe(speakerNames, speakerGraphs) {
    // console.log('setGlobe ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    const config = {
        responsive: true,
        displayModeBar: true,
    };
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
                currentPolarData.marker = {
                    autocolorscale: false,
                    colorscale: contourColorscale,
                    color: color,
                    colorbar: {
                        title: {
                            text: 'dB (SPL)',
                        },
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
            let layout = speakerGraphs[i].layout;
            layout.polar = {
                bargap: 0,
                hole: 0.05,
            };
            graphsConfigs.push({
                data: polarData,
                layout: layout,
                config: config,
            });
        }
    }
    return graphsConfigs;
}

export function setSurface(speakerNames, speakerGraphs, width, height) {
    // console.log('setSurface ' + speakerNames.length + ' names and ' + speakerGraphs.length + ' graphs')
    const graphsConfigs = [];
    const config = {
        responsive: true,
        displayModeBar: true,
    };
    for (const i in speakerGraphs) {
        if (speakerGraphs[i]) {
            let surfaceData = [];
            for (const j in speakerGraphs[i].data) {
                surfaceData.push(speakerGraphs[i].data[j]);
            }
            const layout = speakerGraphs[i].layout;
            layout.width = width;
            layout.height = height - 100;
            graphsConfigs.push({
                data: surfaceData,
                layout: layout,
                config: config,
            });
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
        currentOption.text = textArray[i];
        if (textArray[i] === textSelected) {
            currentOption.selected = true;
        }
        if (textArray.length === 1) {
            currentOption.disabled = true;
        }
        selector.appendChild(currentOption);
    }
}

export function updateVersion(metaSpeakers, speaker, selector, origin, value) {
    // update possible version(s) for matching speaker and origin
    // console.log('update version for ' + speaker + ' origin=' + origin + ' value=' + value)
    const versions = Object.keys(metaSpeakers[speaker].measurements);
    let matches = [];
    versions.forEach((val) => {
        const current = metaSpeakers[speaker].measurements[val];
        if (current.origin === origin || origin === '' || origin == null) {
            matches.push(val);
        }
    });
    if (metaSpeakers[speaker].eqs != null) {
        const matchesEQ = [];
        for (const key in matches) {
            matchesEQ.push(matches[key] + '_eq');
        }
        matches = matches.concat(matchesEQ);
    }
    if (value != null) {
        assignOptions(matches, selector, value);
    } else {
        assignOptions(matches, selector, selector.value);
    }
}

export function updateOrigin(metaSpeakers, speaker, originSelector, versionSelector, origin, version) {
    // console.log('updateOrigin for ' + speaker + ' with origin ' + origin + ' version=' + version)
    const measurements = Object.keys(metaSpeakers[speaker].measurements);
    const origins = new Set();
    for (const key in measurements) {
        origins.add(metaSpeakers[speaker].measurements[measurements[key]].origin);
    }
    const [first] = origins;
    // console.log('updateOrigin found this possible origins: ' + origins.size + ' first=' + first)
    // origins.forEach(item => console.log('updateOrigin: ' + item))
    if (origin != null) {
        assignOptions(Array.from(origins), originSelector, origin);
    } else {
        assignOptions(Array.from(origins), originSelector, first);
    }
    updateVersion(metaSpeakers, speaker, versionSelector, originSelector.value, version);
}
