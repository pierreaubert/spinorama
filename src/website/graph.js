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
import { loadConfigFromStorage, initGlobalConfigPanel, applyConfig } from './plot-config.js';

function detectTheme() {
    try {
        const attr = document.documentElement.getAttribute('data-theme');
        if (attr === 'dark') return 'dark';
        if (attr === 'light') return 'light';
        if (window.matchMedia) {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
    } catch (_) { /* test environment */ }
    return 'light';
}

export function displayGraph(measurementName, jsonName, divName, graphSpec, withConfig, ratio) {
    if (typeof divName !== 'string' && !(divName instanceof HTMLElement)) {
        console.error('Error: divName must be a string ID or HTMLElement', divName);
        return Promise.reject(new Error('Invalid divName parameter'));
    }

    function getConfig() {
        const config = loadConfigFromStorage(measurementName);
        config.theme = detectTheme();
        return config;
    }

    function getColumnRatio() {
        try {
            var cols = parseInt(document.documentElement.getAttribute('data-graph-cols') || '1');
            if (cols > 1) return cols;
        } catch (_) {}
        return 1;
    }

    function computeOptions(config) {
        const effectiveRatio = ratio * getColumnRatio();
        const w = window.innerWidth / effectiveRatio;
        const h = window.innerHeight / effectiveRatio;

        let title = measurementName;
        if (graphSpec.layout && graphSpec.layout.title && graphSpec.layout.title.text) {
            title = graphSpec.layout.title.text;
        }
        const graphOptions = setPlotForMeasurement(measurementName, [title], [graphSpec], w, h, 1);

        if (!graphOptions?.length) {
            return null;
        }

        let options = graphOptions[0];

        if (jsonName.indexOf('3D') !== -1) {
            if (options.layout) {
                options.layout.shapes = null;
            }
        }

        // Always apply config (theme colors, palette, etc.)
        options = applyConfig(options, config);

        // Configure Plotly for compact non-interactive mode if needed
        if (!withConfig) {
            if (!options.config) {
                options.config = {};
            }
            options.config.displayModeBar = false;
            options.config.staticPlot = true;
            options.config.editable = false;
            options.config.scrollZoom = false;
            options.config.doubleClick = false;
            options.config.showTips = false;
            options.config.responsive = true;

            // hide legend for small static previews (non-interactive, can't toggle)
            if (ratio > 1 && options.layout) {
                options.layout.showlegend = false;
            }

            // reduce the size of title if ratio > 1
            if (ratio > 1 && options.layout) {
                const w = window.innerWidth;
                const d = w / 550;
                if (options.layout.title && options.layout.title.font) {
                    options.layout.title.font.size = 10 + d;
                }
                if (options.layout.xaxis && options.layout.xaxis.title && options.layout.xaxis.title.font) {
                    options.layout.xaxis.title.font.size = 9 + d;
                }
                if (options.layout.xaxis && options.layout.xaxis.tickfont) {
                    options.layout.xaxis.tickfont.size = 8 + d;
                }
                if (options.layout.yaxis && options.layout.yaxis.title && options.layout.yaxis.title.font) {
                    options.layout.yaxis.title.font.size = 9 + d;
                }
                if (options.layout.yaxis && options.layout.yaxis.tickfont) {
                    options.layout.yaxis.tickfont.size = 8 + d;
                }
            }
        }

        return options;
    }

    async function run() {
        const config = getConfig();
        const options = computeOptions(config);
        if (!options) {
            return;
        }

        // Initialize the global config panel (once, on first interactive graph)
        if (withConfig) {
            initGlobalConfigPanel(config);
        }

        const targetElement = typeof divName === 'string' ? document.getElementById(divName) : divName;
        if (!targetElement) {
            console.error(`Error: Target element not found for plotting`);
            return;
        }
        await Plotly.newPlot(targetElement, options);

        // Re-render ALL graphs when config or theme changes
        window.addEventListener('spinorama-config-change', () => {
            const newConfig = getConfig();
            const newOptions = computeOptions(newConfig);
            if (newOptions) {
                Plotly.react(targetElement, newOptions.data, newOptions.layout, newOptions.config);
            }
        });

        // Set up resize handler
        let resizeTimer = null;
        window.addEventListener('resize', () => {
            if (resizeTimer) {
                clearTimeout(resizeTimer);
            }
            resizeTimer = setTimeout(() => {
                const newConfig = getConfig();
                const newOptions = computeOptions(newConfig);
                if (newOptions) {
                    Plotly.react(targetElement, newOptions.data, newOptions.layout, newOptions.config);
                }
            }, 150);
        });
    }

    return run();
}
