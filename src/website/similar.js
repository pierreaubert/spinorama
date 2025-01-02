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

import Plotly from 'plotly-dist-min';

import { getMetadata, assignOptions, getSpeakerData } from './download.js';
import { knownMeasurements, setCEA2034, setContour, setGraph, setGlobe, setRadar, setSurface } from './plot.js';

function getNearSpeakers(metadata) {
    const metaSpeakers = {};
    const speakers = [];
    metadata.forEach(function (value) {
        const speaker = value.brand + ' ' + value.model;
        if (value.nearest && value.nearest.length > 0) {
            speakers.push(speaker);
            metaSpeakers[speaker] = value;
        }
    });
    return [metaSpeakers, speakers.sort()];
}

getMetadata()
    .then((metadata) => {
        const urlSimilar = '/similar.html?';

        const queryString = window.location.search;
        const urlParams = new URLSearchParams(queryString);

        const plotContainer = document.querySelector('[data-num="0"');
        const formContainer = plotContainer.querySelector('.plotForm');
        const graphSelector = formContainer.querySelector('#similar-select-graph');
        const speakerSelector = formContainer.querySelector('#similar-select-speaker');

        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;

        const [metaSpeakers, speakers] = getNearSpeakers(metadata);

        function plot(measurement, speakersName, speakersGraph) {
            // console.log('plot: ' + speakersName.length + ' names and ' + speakersGraph.length + ' graphs')
            async function run() {
                Promise.all(speakersGraph).then((graphs) => {
                    // console.log('plot: resolved ' + graphs.length + ' graphs')
                    for (let i = 0; i < graphs.length - 1; i++) {
                        let graphOptions = [null];
                        const currentGraphs = [graphs[0], graphs[i + 1]];
                        const currentNames = [speakersName[0] + ' v.s. ' + speakersName[i + 1], speakersName[i + 1]];
                        if (measurement === 'CEA2034') {
                            graphOptions = setCEA2034(measurement, currentNames, currentGraphs, windowWidth, windowHeight);
                        } else if (
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
                            graphOptions = setGraph(measurement, currentNames, currentGraphs, windowWidth, windowHeight);
                        } else if (measurement === 'SPL Horizontal Radar' || measurement === 'SPL Vertical Radar') {
                            graphOptions = setRadar(currentNames, currentGraphs, windowWidth, windowHeight);
                        } else if (
                            measurement === 'SPL Horizontal Contour' ||
                            measurement === 'SPL Vertical Contour' ||
                            measurement === 'SPL Horizontal Contour Normalized' ||
                            measurement === 'SPL Vertical Contour Normalized'
                        ) {
                            graphOptions = setContour(measurement, currentNames, currentGraphs, windowWidth, windowHeight);
                        } else if (
                            measurement === 'SPL Horizontal 3D' ||
                            measurement === 'SPL Vertical 3D' ||
                            measurement === 'SPL Horizontal 3D Normalized' ||
                            measurement === 'SPL Vertical 3D Normalized'
                        ) {
                            graphOptions = setSurface(measurement, currentNames, currentGraphs, windowWidth, windowHeight);
                        } else if (
                            measurement === 'SPL Horizontal Globe' ||
                            measurement === 'SPL Vertical Globe' ||
                            measurement === 'SPL Horizontal Globe Normalized' ||
                            measurement === 'SPL Vertical Globe Normalized'
                        ) {
                            graphOptions = setGlobe(measurement, currentNames, currentGraphs, windowWidth, windowHeight);
                        }
                        if (graphOptions?.length === 1) {
                            let options = graphOptions[0];
                            options.layout.title = currentNames[0];
                            Plotly.newPlot('plot' + i, options);
                        } else if (graphOptions?.length === 2) {
                            if (i === 0) {
                                let options0 = graphOptions[0];
                                options0.layout.title = speakersName[0];
                                Plotly.newPlot('plot0', options0);
                                let options1 = graphOptions[1];
                                options1.layout.title = speakersName[1];
                                Plotly.newPlot('plot1', options1);
                            } else {
                                const pos = i + 1;
                                let options = graphOptions[1];
                                options.layout.title = speakersName[pos];
                                Plotly.newPlot('plot' + pos, options);
                            }
                        }
                    }
                    return null;
                });
            }
            run();
        }

        function buildInitSpeakers(speakers) {
            if (urlParams.has('speaker0')) {
                const speaker0 = urlParams.get('speaker0');
                if (speaker0.length > 3) {
                    return speaker0;
                }
            }
            return speakers[Math.floor(Math.random() * speakers.length)];
        }

        function updatePlots() {
            const speakerName = speakerSelector.value;
            const graphName = graphSelector.value;
            const names = [];
            const graphs = [];
            // console.log('speaker >' + speakerName + '< graph >' + graphName + '<');
            graphs.push(getSpeakerData(metaSpeakers, graphName, speakerName, null, null));
            names[0] = speakerName;
            if (metaSpeakers[names[0]].nearest !== null) {
                const similars = metaSpeakers[names[0]].nearest;
                for (let i = 0; i < similars.length; i++) {
                    // console.log('adding '+similars[i][1])
                    names.push(similars[i][1]);
                    graphs.push(getSpeakerData(metaSpeakers, graphName, similars[i][1], null, null));
                }
            }
            urlParams.set('measurement', graphName);
            urlParams.set('speaker0', speakerName);
            history.pushState({ page: 1 }, 'Change measurement', urlSimilar + urlParams.toString());
            plot(graphName, names, graphs);
        }

        assignOptions(speakers, speakerSelector, buildInitSpeakers(speakers));
        assignOptions(knownMeasurements, graphSelector, knownMeasurements[0]);

        // add listeners
        graphSelector.addEventListener('change', updatePlots, false);
        speakerSelector.addEventListener('change', updatePlots, false);

        updatePlots();
    })
    .catch((err) => console.log(err.message));
