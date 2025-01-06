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

import { setGraph } from './plot.js';

export function displayGraph(measurementName, jsonName, divName, graphSpec) {
    async function run() {
        const w = window.innerWidth;
        const h = window.innerHeight;

        const title = graphSpec.layout.title.text;
        const graphOptions = setGraph(measurementName, [title], [graphSpec], w, h, 1);

        if (graphOptions?.length >= 1) {
            let options = graphOptions[0];
            if (jsonName.indexOf('3D') !== -1) {
                if (options.layout && options.layout?.shapes) {
                    options.layout.shapes = null;
                }
            }

            Plotly.newPlot(divName, options);
        }
    }

    return run();
}
