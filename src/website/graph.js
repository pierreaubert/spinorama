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
    } catch {
        /* test environment */
    }
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
        } catch {}
        return 1;
    }

    // Cache base options (before applyConfig) to avoid recomputing on config changes
    let cachedBaseOptions = null;

    // Measure the actual container width for the target element. Falls back to
    // window.innerWidth / effectiveRatio when the target isn't in the DOM yet.
    function getContainerWidth() {
        const target = typeof divName === 'string' ? document.getElementById(divName) : divName;
        if (target) {
            // Walk up to the first ancestor with non-zero width, since the target
            // itself may be `display: none` or zero-width before first plot.
            let el = target;
            while (el && el.offsetWidth === 0 && el.parentElement) el = el.parentElement;
            if (el && el.offsetWidth > 0) return el.offsetWidth;
        }
        return window.innerWidth / (ratio * getColumnRatio());
    }

    function computeBaseOptions() {
        const w = getContainerWidth();
        const effectiveRatio = ratio * getColumnRatio();
        const h = window.innerHeight / effectiveRatio;

        let title = measurementName;
        if (graphSpec.layout && graphSpec.layout.title && graphSpec.layout.title.text) {
            title = graphSpec.layout.title.text;
        }
        const graphOptions = setPlotForMeasurement(measurementName, [title], [graphSpec], w, h, 1);
        if (!graphOptions?.length) return null;

        let options = graphOptions[0];
        if (jsonName.indexOf('3D') !== -1 && options.layout) {
            options.layout.shapes = null;
        }
        return options;
    }

    // Shallow-clone base options: share heavy data arrays, clone mutable metadata
    function shallowCloneOptions(base) {
        const layout = Object.assign({}, base.layout);
        // Clone nested layout objects that applyConfig mutates
        if (layout.xaxis) layout.xaxis = Object.assign({}, layout.xaxis);
        if (layout.yaxis) layout.yaxis = Object.assign({}, layout.yaxis);
        if (layout.yaxis2) layout.yaxis2 = Object.assign({}, layout.yaxis2);
        if (layout.zaxis) layout.zaxis = Object.assign({}, layout.zaxis);
        if (layout.legend) layout.legend = Object.assign({}, layout.legend);
        if (layout.font) layout.font = Object.assign({}, layout.font);
        if (layout.margin) layout.margin = Object.assign({}, layout.margin);
        // Clone axis title fonts (applyConfig mutates font.size)
        for (const ax of ['xaxis', 'yaxis', 'yaxis2', 'zaxis']) {
            if (layout[ax]?.title?.font) {
                layout[ax].title = Object.assign({}, layout[ax].title);
                layout[ax].title.font = Object.assign({}, layout[ax].title.font);
            }
            if (layout[ax]?.tickfont) layout[ax].tickfont = Object.assign({}, layout[ax].tickfont);
        }
        if (layout.legend?.font) layout.legend.font = Object.assign({}, layout.legend.font);
        if (layout.title?.font) {
            layout.title = Object.assign({}, layout.title);
            layout.title.font = Object.assign({}, layout.title.font);
        }
        // Shallow-clone annotations array (applyConfig sets .visible on each)
        const annotations = layout.annotations ? layout.annotations.map((a) => Object.assign({}, a)) : undefined;
        if (annotations) layout.annotations = annotations;
        // Clone shapes array (applyConfig pushes border shape)
        if (layout.shapes) layout.shapes = layout.shapes.slice();

        // Shallow-clone each trace: share x/y/z data arrays, clone mutable props
        const data = base.data.map((t) => {
            const clone = Object.assign({}, t);
            if (clone.marker) clone.marker = Object.assign({}, clone.marker);
            if (clone.line) clone.line = Object.assign({}, clone.line);
            if (clone.colorbar) clone.colorbar = Object.assign({}, clone.colorbar);
            if (clone.hoverlabel?.font) {
                clone.hoverlabel = Object.assign({}, clone.hoverlabel);
                clone.hoverlabel.font = Object.assign({}, clone.hoverlabel.font);
            }
            if (clone.legendgrouptitle) clone.legendgrouptitle = Object.assign({}, clone.legendgrouptitle);
            return clone;
        });

        return { data, layout, config: base.config ? Object.assign({}, base.config) : {}, _graphType: base._graphType };
    }

    // Compact mode config (computed once, applied on each render)
    let compactConfig = null;
    if (!withConfig && ratio > 1) {
        const d = window.innerWidth / 550;
        compactConfig = {
            titleSize: 10 + d,
            axisTitleSize: 9 + d,
            tickSize: 8 + d,
        };
    }

    function applyConfigAndCompact(baseOptions, config) {
        const options = shallowCloneOptions(baseOptions);
        applyConfig(options, config);

        if (!withConfig) {
            if (!options.config) options.config = {};
            options.config.displayModeBar = false;
            options.config.staticPlot = true;
            options.config.editable = false;
            options.config.scrollZoom = false;
            options.config.doubleClick = false;
            options.config.showTips = false;

            if (ratio > 1 && options.layout) {
                options.layout.showlegend = false;
            }
            if (compactConfig && options.layout) {
                if (options.layout.title?.font) options.layout.title.font.size = compactConfig.titleSize;
                if (options.layout.xaxis?.title?.font) options.layout.xaxis.title.font.size = compactConfig.axisTitleSize;
                if (options.layout.xaxis?.tickfont) options.layout.xaxis.tickfont.size = compactConfig.tickSize;
                if (options.layout.yaxis?.title?.font) options.layout.yaxis.title.font.size = compactConfig.axisTitleSize;
                if (options.layout.yaxis?.tickfont) options.layout.yaxis.tickfont.size = compactConfig.tickSize;
            }
        }
        if (!options.config) options.config = {};
        // We handle resize manually via window.addEventListener('resize'), so disable
        // Plotly's own responsive scaling — it conflicts with our layout recomputation
        // (e.g. scales vertical legends outside the visible area).
        options.config.responsive = false;
        return options;
    }

    async function run() {
        const config = getConfig();
        cachedBaseOptions = computeBaseOptions();
        if (!cachedBaseOptions) return;

        const options = applyConfigAndCompact(cachedBaseOptions, config);

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

        function targetIsRenderable() {
            return targetElement.offsetWidth > 0 && targetElement.offsetHeight > 0;
        }

        let reactQueue = Promise.resolve();
        function reactWhenRenderable(newOptions) {
            if (!targetIsRenderable()) return reactQueue;
            reactQueue = reactQueue
                .catch(() => undefined)
                .then(() => Plotly.react(targetElement, newOptions.data, newOptions.layout, newOptions.config))
                .catch((error) => console.error('Plotly.react failed:', error));
            return reactQueue;
        }

        // Fast path: re-apply config without recomputing base options.
        // Debounced to batch rapid changes (e.g. multiple checkboxes).
        let configTimer = null;
        window.addEventListener('spinorama-config-change', () => {
            if (!cachedBaseOptions) return;
            if (configTimer) clearTimeout(configTimer);
            configTimer = setTimeout(() => {
                const newConfig = getConfig();
                const newOptions = applyConfigAndCompact(cachedBaseOptions, newConfig);
                reactWhenRenderable(newOptions);
            }, 16); // ~1 frame
        });

        // Set up resize handler — recompute base options since dimensions change
        let resizeTimer = null;
        const doResize = () => {
            if (resizeTimer) clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                cachedBaseOptions = computeBaseOptions();
                if (!cachedBaseOptions) return;
                const newConfig = getConfig();
                const newOptions = applyConfigAndCompact(cachedBaseOptions, newConfig);
                reactWhenRenderable(newOptions);
            }, 150);
        };
        window.addEventListener('resize', doResize);

        // Observe the target element so we re-render when a hidden tab becomes
        // visible (offsetWidth transitions from 0 → container width) or when the
        // user switches columns (cell width changes).
        if (typeof ResizeObserver !== 'undefined') {
            let lastKnownWidth = targetElement.offsetWidth || 0;
            const ro = new ResizeObserver((entries) => {
                const w = entries[0].contentRect.width;
                if (w > 0 && Math.abs(w - lastKnownWidth) > 4) {
                    lastKnownWidth = w;
                    doResize();
                }
            });
            ro.observe(targetElement);
        }
    }

    return run();
}
