// -*- coding: utf-8 -*-
// Configuration management for spinorama charts
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

import { labelShort, labelLong } from './plot.js';
import { getUrlParameter } from './misc.js';

// Color palettes for graphs
export const colorPalettes = {
    default: [
        'rgb(92, 119, 165)',
        'rgb(220, 132, 42)',
        'rgb(200, 88, 87)',
        'rgb(137, 181, 177)',
        'rgb(113, 161, 82)',
        'rgb(186, 176, 172)',
        'rgb(225, 87, 89)',
        'rgb(176, 122, 161)',
        'rgb(118, 183, 178)',
        'rgb(255, 157, 167)',
    ],
    vibrant: [
        'rgb(255, 107, 107)',
        'rgb(78, 205, 196)',
        'rgb(69, 183, 209)',
        'rgb(150, 206, 180)',
        'rgb(255, 234, 167)',
        'rgb(221, 160, 221)',
        'rgb(152, 216, 200)',
        'rgb(247, 220, 111)',
        'rgb(187, 143, 206)',
        'rgb(133, 193, 233)',
    ],
    pastel: [
        'rgb(255, 179, 186)',
        'rgb(255, 223, 186)',
        'rgb(255, 255, 186)',
        'rgb(186, 255, 201)',
        'rgb(186, 225, 255)',
        'rgb(230, 230, 250)',
        'rgb(240, 230, 140)',
        'rgb(221, 160, 221)',
        'rgb(152, 251, 152)',
        'rgb(245, 222, 179)',
    ],
    dark: [
        'rgb(185, 195, 255)',
        'rgb(255, 180, 171)',
        'rgb(80, 220, 160)',
        'rgb(255, 193, 70)',
        'rgb(226, 186, 217)',
        'rgb(193, 197, 221)',
        'rgb(255, 157, 120)',
        'rgb(133, 193, 233)',
        'rgb(255, 214, 102)',
        'rgb(174, 214, 181)',
    ],
    monochrome: [
        'rgb(44, 62, 80)',
        'rgb(52, 73, 94)',
        'rgb(93, 109, 126)',
        'rgb(133, 146, 158)',
        'rgb(174, 182, 191)',
        'rgb(213, 219, 219)',
        'rgb(234, 237, 237)',
        'rgb(248, 249, 249)',
        'rgb(189, 195, 199)',
        'rgb(149, 165, 166)',
    ],
};

// Contour colorscales
export const contourColorscales = {
    default: [
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
    ],
    viridis: [
        [0, 'rgb(68,1,84)'],
        [0.1, 'rgb(72,40,120)'],
        [0.2, 'rgb(62,74,137)'],
        [0.3, 'rgb(49,104,142)'],
        [0.4, 'rgb(38,130,142)'],
        [0.5, 'rgb(31,158,137)'],
        [0.6, 'rgb(53,183,121)'],
        [0.7, 'rgb(109,205,89)'],
        [0.8, 'rgb(180,222,44)'],
        [0.9, 'rgb(253,231,37)'],
        [1, 'rgb(253,231,37)'],
    ],
    plasma: [
        [0, 'rgb(13,8,135)'],
        [0.1, 'rgb(75,3,161)'],
        [0.2, 'rgb(125,3,168)'],
        [0.3, 'rgb(168,34,150)'],
        [0.4, 'rgb(203,70,121)'],
        [0.5, 'rgb(229,107,93)'],
        [0.6, 'rgb(248,148,65)'],
        [0.7, 'rgb(253,195,40)'],
        [0.8, 'rgb(239,248,33)'],
        [0.9, 'rgb(240,249,33)'],
        [1, 'rgb(240,249,33)'],
    ],
    cool: [
        [0, 'rgb(0,255,255)'],
        [0.1, 'rgb(25,230,255)'],
        [0.2, 'rgb(51,204,255)'],
        [0.3, 'rgb(76,179,255)'],
        [0.4, 'rgb(102,153,255)'],
        [0.5, 'rgb(127,128,255)'],
        [0.6, 'rgb(153,102,255)'],
        [0.7, 'rgb(178,76,255)'],
        [0.8, 'rgb(204,51,255)'],
        [0.9, 'rgb(229,25,255)'],
        [1, 'rgb(255,0,255)'],
    ],
    hot: [
        [0, 'rgb(0,0,0)'],
        [0.1, 'rgb(26,0,0)'],
        [0.2, 'rgb(51,0,0)'],
        [0.3, 'rgb(77,0,0)'],
        [0.4, 'rgb(102,0,0)'],
        [0.5, 'rgb(128,0,0)'],
        [0.6, 'rgb(153,51,0)'],
        [0.7, 'rgb(179,102,0)'],
        [0.8, 'rgb(204,153,0)'],
        [0.9, 'rgb(230,204,0)'],
        [1, 'rgb(255,255,255)'],
    ],
};

// Default delta configuration options for plots
export const defaultConfig = {
    font: {
        family: 'default', // 'default' means keep original value
        size: 0, // 0 means no change to original size
        color: 'default', // 'default' means keep original color
    },
    colors: {
        palette: 'default', // 'default' means keep original palette
    },
    contour: {
        colorscale: 'default', // 'default' means keep original colorscale
    },
    grid: {
        show: true, // Boolean overrides original value
        color: 'default', // 'default' means keep original color
    },
    legend: {
        show: true, // Boolean overrides original value
        position: 'default', // 'default' means keep original position
        xanchor: 'default', // 'default' means keep original xanchor
        yanchor: 'default', // 'default' means keep original yanchor
        xoffset: 0, // 0 means no change to original offset (range: -1.0 to 1.0)
        yoffset: 0, // 0 means no change to original offset (range: -1.0 to 1.0)
        label: 'default', // 'default' means keep original label style
    },
    margins: {
        l: 0, // 0 means no change to original margin
        r: 0, // 0 means no change to original margin
        t: 0, // 0 means no change to original margin
        b: 0, // 0 means no change to original margin
        pad: 0, // 0 means no change to original padding
    },
    showAxisLabels: true, // Boolean overrides original value
    layout: {
        direction: 'default', // 'default' means keep original direction
    },
    colorbar: {
        thickness: 0, // 0 means no change to original thickness
        len: 0, // 0 means no change to original length
        show: true, // Boolean overrides original value
    },
    annotations: {
        show: true, // Boolean overrides original value
        showA: true, // Per-speaker A (compare mode)
        showB: true, // Per-speaker B (compare mode)
    },
    trendlines: {
        show: true, // Boolean overrides original value
        showA: true, // Per-speaker A (compare mode)
        showB: true, // Per-speaker B (compare mode)
    },
    zones: {
        show: true, // Boolean overrides original value
        showA: true, // Per-speaker A (compare mode)
        showB: true, // Per-speaker B (compare mode)
    },
};

// Local storage key for configuration
export const CONFIG_STORAGE_KEY = 'spinorama-plot-config';

// Save configuration to local storage
export function saveConfigToStorage(config) {
    try {
        localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
    } catch (error) {
        console.warn('Failed to save configuration to localStorage:', error);
    }
}

// Load configuration from local storage and apply to graph config
export function loadConfigFromStorage(graphConfig) {
    // If graphConfig is a primitive, start with defaultConfig as base
    let baseConfig =
        typeof graphConfig === 'object' && graphConfig !== null && !Array.isArray(graphConfig) ? graphConfig : defaultConfig;

    try {
        const storedConfig = localStorage.getItem(CONFIG_STORAGE_KEY);
        if (storedConfig) {
            const userConfig = JSON.parse(storedConfig);
            // First apply default deltas, then user deltas
            return mergeConfigs(mergeConfigs(baseConfig, defaultConfig), userConfig);
        }
    } catch (error) {
        console.warn('Error loading configuration from localStorage:', error);
    }

    // Apply just the default config as delta if storage access fails
    return mergeConfigs(baseConfig, defaultConfig);
}

// Apply delta configuration to a base configuration
export function mergeConfigs(baseConf, deltaConf) {
    if (!deltaConf) return baseConf;
    const result = JSON.parse(JSON.stringify(baseConf));
    applyDelta(result, deltaConf);
    return result;

    function applyDelta(target, delta) {
        // If target itself is a primitive (string, number, etc), we can't set properties on it
        if (typeof target !== 'object' || target === null || Array.isArray(target)) {
            return; // Can't apply delta to a primitive target
        }

        for (const key in delta) {
            if (delta[key] && typeof delta[key] === 'object' && !Array.isArray(delta[key])) {
                // Check if target[key] is a string or other primitive - if so, convert to object
                // Also handle the case where target[key] is null or undefined
                if (!target[key] || typeof target[key] !== 'object' || Array.isArray(target[key])) {
                    target[key] = {};
                }
                applyDelta(target[key], delta[key]);
            } else {
                // For strings, 'default' means keep the original value
                if (typeof delta[key] === 'string' && delta[key] === 'default') {
                    continue; // Skip this property, keep target value
                }
                // For numbers, apply as delta (addition)
                else if (typeof delta[key] === 'number' && typeof target[key] === 'number') {
                    target[key] += delta[key];
                }
                // For other cases (booleans, arrays, etc), replace as before
                else {
                    target[key] = delta[key];
                }
            }
        }
    }
}

// Apply configuration to plot options, treating config values as deltas
export function applyConfig(options, config) {
    if (!options || !config) return options;

    // Build font configuration object from config
    const fontConfig = {};
    if (config.font) {
        if (config.font.family && config.font.family !== 'default') {
            fontConfig.family = config.font.family;
        }
        if (config.font.color && config.font.color !== 'default') {
            fontConfig.color = config.font.color;
        }
        if (config.font.size && typeof config.font.size === 'number' && config.font.size !== 0) {
            // Note: font size will be applied as deltas in the specific axis handling below
        }
    }

    // Apply options to layout if it exists
    if (options.layout) {
        const layout = options.layout;

        // Apply font to layout
        if (Object.keys(fontConfig).length > 0 || (config.font && config.font.size !== 0)) {
            [layout, layout.xaxis, layout.yaxis, layout.zaxis, layout.legend].forEach((axis) => {
                if (axis?.title?.font) {
                    if (config.font) {
                        if (config.font.size && typeof config.font.size === 'number') {
                            if (axis.title.font.size) {
                                axis.title.font.size += config.font.size;
                            }
                        }
                        if (config.font.family && config.font.family !== 'default') {
                            axis.title.font.family = config.font.family;
                        }
                        if (config.font.color && config.font.color !== 'default') {
                            axis.title.font.color = config.font.color;
                        }
                    }
                }
            });
        }

        // Apply theme (light/dark) to graph backgrounds and colors
        if (config.theme && config.theme !== 'default') {
            switch (config.theme) {
                case 'light':
                    layout.paper_bgcolor = '#faf8ff';
                    layout.plot_bgcolor = '#faf8ff';
                    if (!layout.font) layout.font = {};
                    layout.font.color = '#1b1b21';
                    ['xaxis', 'yaxis', 'yaxis2', 'zaxis'].forEach((axis) => {
                        if (layout[axis]) {
                            layout[axis].gridcolor = '#c6c5d0';
                            layout[axis].linecolor = '#45464f';
                            layout[axis].zerolinecolor = '#767680';
                            if (layout[axis].minor) {
                                layout[axis].minor.gridcolor = 'rgba(0,0,0,0.05)';
                            }
                        }
                    });
                    break;
                case 'dark':
                    layout.paper_bgcolor = '#131318';
                    layout.plot_bgcolor = '#1f1f25';
                    if (!layout.font) layout.font = {};
                    layout.font.color = '#e3e1e9';
                    ['xaxis', 'yaxis', 'yaxis2', 'zaxis'].forEach((axis) => {
                        if (layout[axis]) {
                            layout[axis].gridcolor = '#34343b';
                            layout[axis].linecolor = '#c6c5d0';
                            layout[axis].zerolinecolor = '#45464f';
                            if (layout[axis].minor) {
                                layout[axis].minor.gridcolor = 'rgba(255,255,255,0.05)';
                            }
                        }
                    });
                    break;
            }
        }

        // Enforce plot borders on SPL vs frequency graphs (not contour/radar/globe)
        var gt = options._graphType;
        var isSplGraph = !gt || (gt.isGraph && !gt.isSurface && !gt.isRadar && !gt.isGlobe);
        if (isSplGraph) {
            var borderColor = (config.theme === 'dark') ? '#c6c5d0' : '#45464f';
            ['xaxis', 'yaxis', 'yaxis2'].forEach(function(ax) {
                if (layout[ax]) {
                    layout[ax].showline = true;
                    layout[ax].linewidth = 1;
                    layout[ax].linecolor = borderColor;
                    layout[ax].mirror = 'ticks';
                }
            });
        }

        // Apply margins as deltas to existing margins
        if (config.margins) {
            if (!layout.margin) {
                layout.margin = {};
            }
            if (config.margins.l !== undefined) {
                layout.margin.l = (layout.margin.l || 0) + config.margins.l;
            }
            if (config.margins.r !== undefined) {
                layout.margin.r = (layout.margin.r || 0) + config.margins.r;
            }
            if (config.margins.t !== undefined) {
                layout.margin.t = (layout.margin.t || 0) + config.margins.t;
            }
            if (config.margins.b !== undefined) {
                layout.margin.b = (layout.margin.b || 0) + config.margins.b;
            }
            if (config.margins.pad !== undefined) {
                layout.margin.pad = (layout.margin.pad || 0) + config.margins.pad;
            }
        }

        // Apply legend configuration
        if (config.legend) {
            if (!layout.legend) {
                layout.legend = {};
            }

            // Only force legend on if the graph didn't explicitly disable it (e.g. contour plots)
            if (config.legend.show !== undefined && layout.showlegend !== false) {
                layout.showlegend = config.legend.show;
            }

            // Apply legend position
            if (config.legend.position && config.legend.position !== 'default') {
                switch (config.legend.position) {
                    case 'top':
                        layout.legend.x = 0.5;
                        layout.legend.y = 1.0;
                        layout.legend.xanchor = 'center';
                        layout.legend.yanchor = 'bottom';
                        layout.legend.orientation = 'h';
                        break;
                    case 'right':
                        layout.legend.x = 1.0;
                        layout.legend.y = 1.0;
                        layout.legend.xanchor = 'left';
                        layout.legend.yanchor = 'auto';
                        layout.legend.orientation = 'v';
                        break;
                    case 'bottom':
                        layout.legend.x = 0.5;
                        layout.legend.y = -0.1;
                        layout.legend.xanchor = 'center';
                        layout.legend.yanchor = 'top';
                        layout.legend.orientation = 'h';
                        break;
                    case 'left':
                        layout.legend.x = 0.0;
                        layout.legend.y = 1.0;
                        layout.legend.xanchor = 'right';
                        layout.legend.yanchor = 'auto';
                        layout.legend.orientation = 'v';
                        break;
                }
            }

            // Apply legend offset as deltas
            if (config.legend.xoffset !== undefined && config.legend.xoffset !== 0) {
                if (layout.legend.x === undefined) layout.legend.x = 0;
                layout.legend.x += config.legend.xoffset;
            }

            if (config.legend.yoffset !== undefined && config.legend.yoffset !== 0) {
                if (layout.legend.y === undefined) layout.legend.y = 0;
                layout.legend.y += config.legend.yoffset;
            }

            // Apply legend font
            if (Object.keys(fontConfig).length > 0) {
                if (!layout.legend.font) layout.legend.font = {};
                layout.legend.font = { ...layout.legend.font, ...fontConfig };
            }
        }

        // Apply grid configuration
        if (config.grid) {
            const axes = ['xaxis', 'yaxis', 'zaxis'];
            axes.forEach((axis) => {
                if (layout[axis]) {
                    if (config.grid.show !== undefined) {
                        layout[axis].showgrid = config.grid.show;
                    }
                    if (config.grid.color && config.grid.color !== 'default') {
                        layout[axis].gridcolor = config.grid.color;
                    }
                }
            });
        }

        // Apply axis labels
        if (config.showAxisLabels !== undefined) {
            ['xaxis', 'yaxis', 'zaxis'].forEach((axis) => {
                if (layout[axis]) {
                    layout[axis].showticklabels = config.showAxisLabels;
                }
            });
        }
    }

    // Apply annotation visibility
    if (config.annotations) {
        if (options.layout && options.layout.annotations) {
            for (const ann of options.layout.annotations) {
                // Per-speaker annotation visibility (annotations have no legendgroup,
                // so we use showA/showB as a combined toggle in compare mode)
                if (ann._speakerIndex === 1 && config.annotations.showB !== undefined) {
                    ann.visible = config.annotations.showB;
                } else if (ann._speakerIndex === 0 && config.annotations.showA !== undefined) {
                    ann.visible = config.annotations.showA;
                } else if (config.annotations.show !== undefined) {
                    ann.visible = config.annotations.show;
                }
            }
        }
    }

    // Apply to data traces if they exist
    if (options.data && Array.isArray(options.data)) {
        options.data.forEach((trace) => {
            if (trace.colorbar) {
                // Apply colorbar configuration if it exists
                if (config.colorbar) {
                    if (config.colorbar.thickness !== undefined) {
                        // Apply thickness as delta
                        trace.colorbar.thickness = (trace.colorbar.thickness || 0) + config.colorbar.thickness;
                    }
                    if (config.colorbar.len !== undefined) {
                        // Apply length as delta
                        trace.colorbar.len = (trace.colorbar.len || 0) + config.colorbar.len;
                    }
                    if (config.colorbar.show !== undefined) {
                        trace.colorbar.visible = config.colorbar.show;
                    }
                }
            }

            if (trace.marker && trace.marker.textfont && Object.keys(fontConfig).length > 0) {
                trace.marker.textfont = { ...trace.marker.textfont, ...fontConfig };
            }

            if (trace.hoverlabel && trace.hoverlabel.font && Object.keys(fontConfig).length > 0) {
                trace.hoverlabel.font = { ...trace.hoverlabel.font, ...fontConfig };
            }

            // Apply legend settings
            if (config.legend) {
                // Show/hide legend — respect per-trace override (e.g. contour grid lines)
                if (config.legend.show !== undefined && trace.showlegend !== false) {
                    trace.showlegend = config.legend.show;
                }

                // Apply label format (short or long)
                if (trace.name) {
                    trace._fullName = trace.name;
                    if (config.legend.label && config.legend.label !== 'default') {
                        if (config.legend.label === 'short') {
                            trace.name = labelShort[trace._fullName] || trace.name;
                        } else if (config.legend.label === 'long') {
                            trace.name = labelLong[trace._fullName] || trace.name;
                        }
                    }
                }
            }

            // Apply trend line visibility
            if (config.trendlines && trace.name) {
                const trendNames = [
                    'Band ±3dB',
                    'Band ±1.5dB',
                    'Midrange Band +3dB',
                    'Midrange Band -3dB',
                    'Midrange ±3dB',
                    'Linear interpolation',
                ];
                const isTrend = trendNames.includes(trace.name) || trace.name.endsWith(' slope');
                if (isTrend) {
                    if (trace.legendgroup === 'speaker1' && config.trendlines.showB !== undefined) {
                        trace.visible = config.trendlines.showB;
                    } else if (trace.legendgroup === 'speaker0' && config.trendlines.showA !== undefined) {
                        trace.visible = config.trendlines.showA;
                    } else if (config.trendlines.show !== undefined) {
                        trace.visible = config.trendlines.show;
                    }
                }
            }

            // Apply recommended zone visibility
            if (config.zones && trace.name && trace.name.startsWith('recommended ')) {
                if (trace.legendgroup === 'speaker1' && config.zones.showB !== undefined) {
                    trace.visible = config.zones.showB;
                } else if (trace.legendgroup === 'speaker0' && config.zones.showA !== undefined) {
                    trace.visible = config.zones.showA;
                } else if (config.zones.show !== undefined) {
                    trace.visible = config.zones.show;
                }
            }

            // Enforce legend group title font size >= legend item font size
            if (trace.legendgrouptitle && trace.legendgrouptitle.text) {
                const legendFontSize = options.layout?.legend?.font?.size;
                if (legendFontSize) {
                    if (!trace.legendgrouptitle.font) {
                        trace.legendgrouptitle.font = {};
                    }
                    if (!trace.legendgrouptitle.font.size || trace.legendgrouptitle.font.size < legendFontSize) {
                        trace.legendgrouptitle.font.size = legendFontSize;
                    }
                }
            }
        });

        // Auto-select dark palette when in dark theme and user hasn't chosen one
        if (config.theme === 'dark' && config.colors && (!config.colors.palette || config.colors.palette === 'default')) {
            config.colors.palette = 'dark';
        }

        // Only apply color palette if not set to 'default'
        if (config.colors && config.colors.palette && config.colors.palette !== 'default') {
            const selectedPalette = colorPalettes[config.colors.palette] || colorPalettes.default;
            options.data.forEach((trace, index) => {
                if (trace.type === 'scatter') {
                    const colorIndex = index % selectedPalette.length;
                    const color = selectedPalette[colorIndex];

                    if (trace.marker) {
                        trace.marker.color = color;
                    }
                    if (trace.line) {
                        trace.line.color = color;
                    }
                    if (!trace.marker && !trace.line) {
                        trace.marker = { color: color };
                        trace.line = { color: color };
                    }
                }
            });
        }

        // Only apply colorscale if not set to 'default'
        if (config.contour && config.contour.colorscale && config.contour.colorscale !== 'default') {
            const selectedColorscale = contourColorscales[config.contour.colorscale] || contourColorscales.default;
            options.data.forEach((trace) => {
                if (
                    trace.type === 'contour' ||
                    trace.type === 'heatmap' ||
                    trace.type === 'surface' ||
                    trace.type === 'contourgl'
                ) {
                    trace.colorscale = selectedColorscale;
                }
            });
        }
    }

    // Apply layout direction for multiple graphs only if not default
    if (config.layout && config.layout.direction && config.layout.direction !== 'default') {
        options._layoutDirection = config.layout.direction;
    }

    return options;
}

// Legacy per-graph config menu — now a no-op (config lives in the global navbar panel)
export function createConfigMenu(divName, config, updateCallback, menuOptions) {
    return;
}

// Notify all listeners that global config changed
function dispatchConfigChange(config) {
    saveConfigToStorage(config);
    window.dispatchEvent(new CustomEvent('spinorama-config-change', { detail: config }));
}

// Initialize the global config panel inside #global-config-panel in the navbar
export function initGlobalConfigPanel(config) {
    const panel = document.getElementById('global-config-panel');
    if (!panel || panel.dataset.initialized) {
        return;
    }
    panel.dataset.initialized = 'true';

    const updateCallback = (updatedConfig) => dispatchConfigChange(updatedConfig);
    const menuOptions = {};

    // Build config UI directly inside the global panel
    const configPanel = document.createElement('div');
    configPanel.className = 'plot-config-inner';
    panel.appendChild(configPanel);

    // Create group sections — flat layout, no accordion
    function createGroupSection(title) {
        const section = document.createElement('div');
        section.className = 'plot-config-section';

        const heading = document.createElement('div');
        heading.className = 'config-label';
        heading.textContent = title;
        section.appendChild(heading);

        const contentArea = document.createElement('div');
        contentArea.className = 'section-content';

        const flexContainer = document.createElement('div');
        flexContainer.className = 'config-flex-container';
        contentArea.appendChild(flexContainer);
        section.appendChild(contentArea);

        // Override appendChild to route into flexContainer
        const originalAppendChild = section.appendChild.bind(section);
        section.appendChild = function (element) {
            if (element !== heading && element !== contentArea && element !== flexContainer) {
                return flexContainer.appendChild(element);
            }
            return originalAppendChild(element);
        };

        return section;
    }

    // Fonts section
    const themeSection = createGroupSection('Fonts');

    themeSection.appendChild(
        createFormGroup(
            'Font Family',
            'select',
            config.font.family,
            'config-font-family',
            [
                'Arial, sans-serif',
                'Helvetica, Arial, sans-serif',
                'Georgia, serif',
                'Times New Roman, serif',
                'Courier New, monospace',
            ],
            (e) => {
                config.font.family = e.target.value;
                updateCallback(config);
            }
        )
    );

    themeSection.appendChild(
        createFormGroup('Font Size', 'number', config.font.size, 'config-font-size', { min: -6, max: 6, step: 1 }, (e) => {
            config.font.size = parseInt(e.target.value);
            updateCallback(config);
        })
    );

    themeSection.appendChild(
        createFormGroup('Font Color', 'color', config.font.color, 'config-font-color', null, (e) => {
            config.font.color = e.target.value;
            updateCallback(config);
        })
    );

    // Layout section
    const layoutSection = createGroupSection('Layout & Grid');

    layoutSection.appendChild(
        createFormGroup('Show Grid', 'checkbox', config.grid.show, 'config-grid', null, (e) => {
            config.grid.show = e.target.checked;
            updateCallback(config);
        })
    );

    // Fix layout direction selector
    const layoutDirectionGroup = document.createElement('div');
    layoutDirectionGroup.className = 'form-group field';
    layoutDirectionGroup.style.cssText = `width: 100%;`;

    const layoutLabel = document.createElement('label');
    layoutLabel.className = 'label is-small';
    layoutLabel.textContent = 'Layout Direction';
    layoutDirectionGroup.appendChild(layoutLabel);

    const selectWrapper = document.createElement('div');
    selectWrapper.className = 'select is-small is-fullwidth';

    const layoutSelect = document.createElement('select');
    layoutSelect.id = 'config-layout-direction';
    layoutSelect.name = 'config-layout-direction';

    const options = [
        { value: 'horizontal', text: 'Horizontal (Side by Side)' },
        { value: 'vertical', text: 'Vertical (Top to Bottom)' },
    ];

    options.forEach((option) => {
        const optElement = document.createElement('option');
        optElement.value = option.value;
        optElement.textContent = option.text;
        optElement.selected = option.value === config.layout.direction;
        layoutSelect.appendChild(optElement);
    });

    layoutSelect.addEventListener('change', (e) => {
        config.layout.direction = e.target.value;
        updateCallback(config);
    });

    selectWrapper.appendChild(layoutSelect);

    const controlDiv = document.createElement('div');
    controlDiv.className = 'control';
    controlDiv.style.cssText = 'display: flex; align-items: center;';
    controlDiv.appendChild(selectWrapper);

    layoutDirectionGroup.appendChild(controlDiv);
    layoutSection.appendChild(layoutDirectionGroup);

    // Legend section
    const legendSection = createGroupSection('Legend');

    legendSection.appendChild(
        createFormGroup('Show Legend', 'checkbox', config.legend.show, 'config-legend-show', null, (e) => {
            config.legend.show = e.target.checked;
            updateCallback(config);
        })
    );

    legendSection.appendChild(
        createFormGroup(
            'Legend Position',
            'select',
            config.legend.position,
            'config-legend-position',
            ['default', 'top', 'right', 'bottom', 'left'],
            (e) => {
                config.legend.position = e.target.value;
                updateCallback(config);
            }
        )
    );

    // Add legend label format options
    legendSection.appendChild(
        createFormGroup(
            'Label Format',
            'select',
            config.legend.label,
            'config-legend-label',
            ['default', 'short', 'long'],
            (e) => {
                config.legend.label = e.target.value;
                updateCallback(config);
            }
        )
    );

    // Add legend position adjustment sliders
    const createLegendOffsetSlider = (axis, label) => {
        const sliderGroup = document.createElement('div');
        sliderGroup.className = 'form-group field';
        sliderGroup.style.cssText = `width: 100%;`;

        const sliderLabel = document.createElement('label');
        sliderLabel.className = 'label is-small';
        sliderLabel.textContent = `${label} Offset`;
        sliderGroup.appendChild(sliderLabel);

        const sliderContainer = document.createElement('div');
        sliderContainer.style.cssText = `
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        // Create slider input for incremental adjustments
        const sliderInput = document.createElement('input');
        sliderInput.type = 'range';
        sliderInput.min = '-100';
        sliderInput.max = '100';
        sliderInput.step = '1';
        sliderInput.value = Math.round(config.legend[axis + 'offset'] * 100); // Convert from -1.0...1.0 to -100...100
        sliderInput.id = `config-legend-offset-${axis}`;
        sliderInput.style.cssText = `
            flex-grow: 1;
            height: 8px;
        `;

        // Value display
        const valueDisplay = document.createElement('span');
        valueDisplay.textContent = config.legend[axis + 'offset'].toFixed(2);
        valueDisplay.style.cssText = `
            min-width: 40px;
            text-align: right;
            font-size: 0.8rem;
        `;

        // Update handler
        sliderInput.addEventListener('input', (e) => {
            const sliderValue = parseInt(e.target.value);
            const offsetValue = sliderValue / 100; // Convert slider value to offset (-1.0 to 1.0)
            config.legend[axis + 'offset'] = offsetValue;
            valueDisplay.textContent = offsetValue.toFixed(2);
            updateCallback(config);
        });

        sliderContainer.appendChild(sliderInput);
        sliderContainer.appendChild(valueDisplay);
        sliderGroup.appendChild(sliderContainer);

        return sliderGroup;
    };

    // Add X and Y offset sliders
    legendSection.appendChild(createLegendOffsetSlider('x', 'Horizontal'));
    legendSection.appendChild(createLegendOffsetSlider('y', 'Vertical'));

    // Margin section
    const marginSection = createGroupSection('Margins');

    // Replace margin number inputs with sliders
    ['l', 'r', 't', 'b'].forEach((side) => {
        const labels = { l: 'Left', r: 'Right', t: 'Top', b: 'Bottom' };

        const marginGroup = document.createElement('div');
        marginGroup.className = 'form-group field';
        marginGroup.style.cssText = `width: 100%;`;

        const marginLabel = document.createElement('label');
        marginLabel.className = 'label is-small';
        marginLabel.textContent = `${labels[side]} Margin`;
        marginGroup.appendChild(marginLabel);

        const sliderContainer = document.createElement('div');
        sliderContainer.style.cssText = `
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        // Create slider input
        const sliderInput = document.createElement('input');
        sliderInput.type = 'range';
        sliderInput.min = '0';
        sliderInput.max = '200';
        sliderInput.step = '5';
        sliderInput.value = config.margins[side] > 200 ? 200 : config.margins[side];
        sliderInput.id = `config-margin-${side}`;
        sliderInput.style.cssText = `
            flex-grow: 1;
            height: 8px;
        `;

        // Value display
        const valueDisplay = document.createElement('span');
        valueDisplay.textContent = config.margins[side];
        valueDisplay.style.cssText = `
            min-width: 30px;
            text-align: right;
            font-size: 0.8rem;
        `;

        // Update handler
        sliderInput.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            config.margins[side] = value;
            valueDisplay.textContent = value;
        });

        sliderInput.addEventListener('change', () => {
            updateCallback(config);
        });

        sliderContainer.appendChild(sliderInput);
        sliderContainer.appendChild(valueDisplay);
        marginGroup.appendChild(sliderContainer);
        marginSection.appendChild(marginGroup);
    });

    // Colors section
    const colorsSection = createGroupSection('Colors');

    // Create color palette selector with visual previews
    const paletteGroup = createFormGroup(
        'Color Palette',
        'div', // Special type for custom implementation
        config.colors.palette,
        'config-colors-palette',
        null,
        (palette) => {
            config.colors.palette = palette;
            if (updateCallback) updateCallback(config);
        }
    );

    // Create visual palette previews
    const paletteContainer = document.createElement('div');
    paletteContainer.className = 'palette-previews';
    paletteContainer.style.cssText = `
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
        margin-top: 5px;
    `;

    Object.keys(colorPalettes).forEach((paletteName) => {
        const paletteRow = document.createElement('div');
        paletteRow.className = `palette-preview ${paletteName === config.colors.palette ? 'selected' : ''}`;
        paletteRow.style.cssText = `
            display: flex;
            align-items: center;
            cursor: pointer;
            padding: 5px;
            border-radius: 4px;
            background-color: ${paletteName === config.colors.palette ? '#f0f0f0' : 'transparent'};
            border: 1px solid ${paletteName === config.colors.palette ? '#ccc' : 'transparent'};
        `;

        // Palette name
        const nameSpan = document.createElement('span');
        nameSpan.textContent = paletteName;
        nameSpan.style.cssText = `
            width: 80px;
            margin-right: 8px;
        `;
        paletteRow.appendChild(nameSpan);

        // Color swatches
        const swatchContainer = document.createElement('div');
        swatchContainer.style.cssText = `
            display: flex;
            flex-grow: 1;
        `;

        colorPalettes[paletteName].forEach((color) => {
            const swatch = document.createElement('div');
            swatch.style.cssText = `
                width: 16px;
                height: 16px;
                background-color: ${color};
                margin-right: 2px;
            `;
            swatchContainer.appendChild(swatch);
        });

        paletteRow.appendChild(swatchContainer);

        // Click handler
        paletteRow.addEventListener('click', () => {
            // Update selection
            document.querySelectorAll('.palette-preview').forEach((el) => {
                el.classList.remove('selected');
                el.style.backgroundColor = 'transparent';
                el.style.border = '1px solid transparent';
            });
            paletteRow.classList.add('selected');
            paletteRow.style.backgroundColor = '#f0f0f0';
            paletteRow.style.border = '1px solid #ccc';

            // Update config
            config.colors.palette = paletteName;
            updateCallback(config);
        });

        paletteContainer.appendChild(paletteRow);
    });

    paletteGroup.appendChild(paletteContainer);
    colorsSection.appendChild(paletteGroup);

    // Create enhanced colorscale selector with visual previews
    const colorscaleGroup = document.createElement('div');
    colorscaleGroup.className = 'form-group';
    colorscaleGroup.style.cssText = `
        padding: 8px;
        margin-bottom: 4px;
        border: 1px solid #eaeaea;
        border-radius: 4px;
        background: #ffffff;
    `;

    const colorscaleLabel = document.createElement('label');
    colorscaleLabel.textContent = 'Contour Colorscale';
    colorscaleLabel.style.cssText = `
        font-weight: bold;
        font-size: 0.9rem;
        color: #444;
        display: block;
        margin-bottom: 8px;
    `;
    colorscaleGroup.appendChild(colorscaleLabel);

    const colorscaleContainer = document.createElement('div');
    colorscaleContainer.style.cssText = `
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        justify-content: flex-start;
    `;
    colorscaleGroup.appendChild(colorscaleContainer);

    // Create a visual preview for each colorscale option
    Object.entries(contourColorscales).forEach(([name, scale]) => {
        const colorscaleOption = document.createElement('div');
        colorscaleOption.className = 'colorscale-option';
        colorscaleOption.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            padding: 5px;
            border: 2px solid ${name === config.contour.colorscale ? '#4285f4' : 'transparent'};
            border-radius: 4px;
            transition: all 0.2s ease;
        `;

        // Create the gradient preview
        const preview = document.createElement('div');
        preview.style.cssText = `
            width: 80px;
            height: 20px;
            margin-bottom: 5px;
            background: linear-gradient(to right,
                ${scale.map(([pos, color]) => `${color} ${pos * 100}%`).join(', ')}
            );
            border-radius: 3px;
        `;

        // Create the name label
        const nameLabel = document.createElement('span');
        nameLabel.textContent = name;
        nameLabel.style.cssText = `
            font-size: 0.8rem;
            color: #666;
        `;

        // Add elements to the option container
        colorscaleOption.appendChild(preview);
        colorscaleOption.appendChild(nameLabel);

        // Add click handler
        colorscaleOption.addEventListener('click', () => {
            // Update visual selection
            document.querySelectorAll('.colorscale-option').forEach((opt) => {
                opt.style.border = '2px solid transparent';
            });
            colorscaleOption.style.border = '2px solid #4285f4';

            // Update config
            config.contour.colorscale = name;
            updateCallback(config);
        });

        colorscaleContainer.appendChild(colorscaleOption);
    });

    colorsSection.appendChild(colorscaleGroup);

    // Create reset button with Bulma styling
    const resetButton = document.createElement('button');
    resetButton.textContent = 'Reset to Default';
    resetButton.className = 'button is-small is-danger is-light reset-config-button';
    resetButton.addEventListener('click', () => {
        Object.assign(config, JSON.parse(JSON.stringify(defaultConfig)));
        saveConfigToStorage(config); // Save the reset config
        if (updateCallback) updateCallback(config);
        // Refresh the page to apply the reset config
        window.location.reload();
    });

    // Add sections to the config panel
    // Colorbar section
    const colorbarSection = createGroupSection('Colorbar');

    colorbarSection.appendChild(
        createFormGroup('Show Colorbar', 'checkbox', config.colorbar.show, 'config-colorbar-show', null, (e) => {
            config.colorbar.show = e.target.checked;
            updateCallback(config);
        })
    );

    colorbarSection.appendChild(
        createFormGroup(
            'Thickness (px)',
            'number',
            config.colorbar.thickness,
            'config-colorbar-thickness',
            { min: 5, max: 100, step: 1 },
            (e) => {
                config.colorbar.thickness = parseInt(e.target.value);
                updateCallback(config);
            }
        )
    );

    colorbarSection.appendChild(
        createFormGroup(
            'Length',
            'number',
            config.colorbar.len,
            'config-colorbar-len',
            { min: 0.1, max: 1.0, step: 0.1 },
            (e) => {
                config.colorbar.len = parseFloat(e.target.value);
                updateCallback(config);
            }
        )
    );

    // Create annotations section
    const annotationsSection = createGroupSection('Annotations & Trend Lines');

    if (menuOptions && menuOptions.compareMode) {
        // Per-speaker controls for compare mode
        annotationsSection.appendChild(
            createFormGroup('Annotations (A)', 'checkbox', config.annotations.showA, 'config-annotations-showA', null, (e) => {
                config.annotations.showA = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Annotations (B)', 'checkbox', config.annotations.showB, 'config-annotations-showB', null, (e) => {
                config.annotations.showB = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Trend Lines (A)', 'checkbox', config.trendlines.showA, 'config-trendlines-showA', null, (e) => {
                config.trendlines.showA = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Trend Lines (B)', 'checkbox', config.trendlines.showB, 'config-trendlines-showB', null, (e) => {
                config.trendlines.showB = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Recommended Zones (A)', 'checkbox', config.zones.showA, 'config-zones-showA', null, (e) => {
                config.zones.showA = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Recommended Zones (B)', 'checkbox', config.zones.showB, 'config-zones-showB', null, (e) => {
                config.zones.showB = e.target.checked;
                updateCallback(config);
            })
        );
    } else {
        // Single speaker mode
        annotationsSection.appendChild(
            createFormGroup('Show Annotations', 'checkbox', config.annotations.show, 'config-annotations-show', null, (e) => {
                config.annotations.show = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Show Trend Lines', 'checkbox', config.trendlines.show, 'config-trendlines-show', null, (e) => {
                config.trendlines.show = e.target.checked;
                updateCallback(config);
            })
        );
        annotationsSection.appendChild(
            createFormGroup('Show Recommended Zones', 'checkbox', config.zones.show, 'config-zones-show', null, (e) => {
                config.zones.show = e.target.checked;
                updateCallback(config);
            })
        );
    }

    // Add all sections to the config panel
    configPanel.appendChild(themeSection);
    configPanel.appendChild(layoutSection);
    configPanel.appendChild(marginSection);
    configPanel.appendChild(legendSection);
    configPanel.appendChild(colorsSection);
    configPanel.appendChild(colorbarSection);
    configPanel.appendChild(annotationsSection);

    // Add reset button at the bottom
    const resetContainer = document.createElement('div');
    resetContainer.style.cssText = `
        display: flex;
        justify-content: flex-end;
        margin-top: 20px;
    `;

    resetContainer.appendChild(resetButton);
    configPanel.appendChild(resetContainer);
}

// Helper function to create form groups
export function createFormGroup(label, type, value, name, options, onChange) {
    let input, group, flexContainer;

    group = document.createElement('div');
    group.className = 'form-group field';

    // Label with Bulma styling
    if (label) {
        const labelElement = document.createElement('label');
        labelElement.className = 'label is-small';
        labelElement.textContent = label;
        group.appendChild(labelElement);
    }

    // Container for inputs with Bulma control class
    flexContainer = document.createElement('div');
    flexContainer.className = 'control';
    flexContainer.style.cssText = `
        display: flex;
        align-items: center;
    `;
    group.appendChild(flexContainer);

    if (type === 'select') {
        // Create a Bulma select wrapper
        const selectWrapper = document.createElement('div');
        selectWrapper.className = 'select is-small is-fullwidth';
        flexContainer.appendChild(selectWrapper);

        input = document.createElement('select');
        input.name = name || label.toLowerCase().replace(/\s+/g, '');

        // Add options
        options.forEach((option) => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option;
            optionElement.selected = option === value;
            input.appendChild(optionElement);
        });

        selectWrapper.appendChild(input);
    } else if (type === 'checkbox') {
        // Create a Bulma checkbox wrapper
        const checkWrapper = document.createElement('label');
        checkWrapper.className = 'checkbox';

        input = document.createElement('input');
        input.type = 'checkbox';
        input.name = name || label.toLowerCase().replace(/\s+/g, '');
        input.checked = value;
        input.style.cssText = 'margin-right: 8px;';

        checkWrapper.appendChild(input);
        checkWrapper.appendChild(document.createTextNode(label));

        // Replace the main label with an empty span since we've moved the label text
        const labelElement = group.querySelector('label');
        if (labelElement) labelElement.textContent = '';

        flexContainer.appendChild(checkWrapper);
    } else if (type === 'number') {
        input = document.createElement('input');
        input.type = 'number';
        input.name = name;
        input.id = name;
        input.value = value;
        input.style.cssText = `
            width: 100%;
            padding: 5px;
            border: 1px solid rgb(221, 221, 221);
            border-radius: 3px;
        `;

        if (options) {
            if (options.min !== undefined) input.min = options.min;
            if (options.max !== undefined) input.max = options.max;
            if (options.step !== undefined) input.step = options.step;
        }
    } else if (type === 'color') {
        // Create a Bulma color input with better styling
        const colorWrapper = document.createElement('div');
        colorWrapper.className = 'field has-addons';

        input = document.createElement('input');
        input.type = 'color';
        input.className = 'input is-small';
        input.name = name || label.toLowerCase().replace(/\s+/g, '');
        input.value = value;
        input.style.cssText = `
            width: 40px;
            height: 30px;
            padding: 0;
            cursor: pointer;
        `;

        const colorPreview = document.createElement('div');
        colorPreview.style.cssText = `
            display: inline-block;
            width: 20px;
            height: 20px;
            background-color: ${value};
            border: 1px solid #ddd;
            margin-left: 8px;
            vertical-align: middle;
        `;

        input.addEventListener('input', (e) => {
            colorPreview.style.backgroundColor = e.target.value;
        });

        flexContainer.appendChild(input);
        flexContainer.appendChild(colorPreview);
    } else {
        input = document.createElement('input');
        input.type = type;
        input.name = name;
        input.id = name;
        input.value = value;
        input.style.cssText = `
            width: 100%;
            padding: 5px;
            border: 1px solid rgb(221, 221, 221);
            border-radius: 3px;
        `;
    }

    if (onChange) {
        input.addEventListener('change', onChange);
    }

    // Only append input directly if it's not already wrapped (select elements are wrapped)
    if (type !== 'select' && type !== 'checkbox' && type !== 'color') {
        flexContainer.appendChild(input);
    }
    return group;
}
