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

import Plotly from 'plotly.js-dist-min';
import { setPlotForMeasurement } from './plot.js';
import {
    colorPalettes,
    contourColorscales,
    loadConfigFromStorage,
    saveConfigToStorage,
    createConfigMenu,
    applyConfig,
} from './plot-config.js';

export function displayGraph(measurementName, jsonName, divName, graphSpec) {
    // Ensure divName is either a string ID or an HTMLElement
    if (typeof divName !== 'string' && !(divName instanceof HTMLElement)) {
        console.error('Error: divName must be a string ID or HTMLElement', divName);
        return Promise.reject(new Error('Invalid divName parameter'));
    }
    // Create a config object for this graph, loading from storage if available
    const config = loadConfigFromStorage(measurementName);

    async function run() {
        const w = window.innerWidth;
        const h = window.innerHeight;

        const title = graphSpec.layout.title.text;
        let graphOptions = setPlotForMeasurement(measurementName, [title], [graphSpec], w, h, 1);

        if (graphOptions?.length >= 1) {
            let options = graphOptions[0];
            if (jsonName.indexOf('3D') !== -1) {
                if (options.layout) {
                    options.layout.shapes = null;
                }
            }

            // Apply initial configuration
            options = applyConfig(options, config);

            // Create configuration menu first
            createConfigMenu(divName, config, (updatedConfig) => {
                // Save updated configuration to local storage
                saveConfigToStorage(updatedConfig);
                // Apply updated configuration and redraw the plot
                const updatedOptions = applyConfig(JSON.parse(JSON.stringify(options)), updatedConfig);
                // Get the actual element if divName is a string ID
                const targetElement = typeof divName === 'string' ? document.getElementById(divName) : divName;
                if (!targetElement) {
                    console.error(`Error: Target element not found for updating plot`);
                    return;
                }
                Plotly.react(divName, updatedOptions.data, updatedOptions.layout, updatedOptions.config);
            });

            // Plot the graph
            // Get the actual element if divName is a string ID
            const targetElement = typeof divName === 'string' ? document.getElementById(divName) : divName;
            if (!targetElement) {
                console.error(`Error: Target element not found for plotting`);
                return;
            }
            await Plotly.newPlot(targetElement, options);
        }
    }

    return run();
}

// Export the color palettes and contour colorscales for use in other modules
export { colorPalettes, contourColorscales };
