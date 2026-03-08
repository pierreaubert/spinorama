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
        'rgb(44, 62, 80)',
        'rgb(231, 76, 60)',
        'rgb(52, 152, 219)',
        'rgb(46, 204, 113)',
        'rgb(243, 156, 18)',
        'rgb(155, 89, 182)',
        'rgb(26, 188, 156)',
        'rgb(52, 73, 94)',
        'rgb(230, 126, 34)',
        'rgb(149, 165, 166)',
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
    theme: 'default', // 'default' means keep original theme
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

        // Apply theme
        if (config.theme && config.theme !== 'default') {
            switch (config.theme) {
                case 'light':
                    layout.paper_bgcolor = '#ffffff';
                    layout.plot_bgcolor = '#ffffff';
                    if (!layout.font) layout.font = {};
                    layout.font.color = '#333333';
                    ['xaxis', 'yaxis', 'zaxis'].forEach((axis) => {
                        if (layout[axis]) {
                            layout[axis].gridcolor = '#e0e0e0';
                            layout[axis].linecolor = '#333333';
                            layout[axis].zerolinecolor = '#666666';
                        }
                    });
                    break;
                case 'dark':
                    layout.paper_bgcolor = '#1a1a2e';
                    layout.plot_bgcolor = '#16213e';
                    if (!layout.font) layout.font = {};
                    layout.font.color = '#e0e0e0';
                    ['xaxis', 'yaxis', 'zaxis'].forEach((axis) => {
                        if (layout[axis]) {
                            layout[axis].gridcolor = '#3a3a5c';
                            layout[axis].linecolor = '#e0e0e0';
                            layout[axis].zerolinecolor = '#5a5a7c';
                        }
                    });
                    break;
            }
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

            if (config.legend.show !== undefined) {
                layout.showlegend = config.legend.show;
            }

            // Apply legend position
            if (config.legend.position && config.legend.position !== 'default') {
                switch (config.legend.position) {
                    case 'top-left':
                        layout.legend.x = 0.01;
                        layout.legend.y = 0.99;
                        break;
                    case 'top':
                        layout.legend.x = 0.5;
                        layout.legend.y = 0.99;
                        break;
                    case 'top-right':
                        layout.legend.x = 0.99;
                        layout.legend.y = 0.99;
                        break;
                    case 'left':
                        layout.legend.x = 0.01;
                        layout.legend.y = 0.5;
                        break;
                    case 'center':
                        layout.legend.x = 0.5;
                        layout.legend.y = 0.5;
                        break;
                    case 'right':
                        layout.legend.x = 0.99;
                        layout.legend.y = 0.5;
                        break;
                    case 'bottom-left':
                        layout.legend.x = 0.01;
                        layout.legend.y = 0.01;
                        break;
                    case 'bottom':
                        layout.legend.x = 0.5;
                        layout.legend.y = 0.01;
                        break;
                    case 'bottom-right':
                        layout.legend.x = 0.99;
                        layout.legend.y = 0.01;
                        break;
                }
            }

            // Apply legend anchor
            if (config.legend.xanchor && config.legend.xanchor !== 'default') {
                layout.legend.xanchor = config.legend.xanchor;
            }

            if (config.legend.yanchor && config.legend.yanchor !== 'default') {
                layout.legend.yanchor = config.legend.yanchor;
            }

            // Apply legend offset as deltas
            if (config.legend.xoffset !== undefined) {
                if (!layout.legend.x) layout.legend.x = 0;
                layout.legend.x += config.legend.xoffset;
            }

            if (config.legend.yoffset !== undefined) {
                if (!layout.legend.y) layout.legend.y = 0;
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
                // Show/hide legend
                if (config.legend.show !== undefined) {
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

// Create plot configuration menu
export function createConfigMenu(divName, config, updateCallback) {
    // Don't create menu if in compact mode with ploty=1 flag
    const plotyFlag = getUrlParameter('ploty');
    const graphSmall = 550; // Same as plot.js
    const isCompact = window.innerWidth < graphSmall || window.innerHeight < graphSmall;

    if (plotyFlag === '1' && isCompact) {
        return;
    }

    // Get the container element
    const container = typeof divName === 'string' ? document.getElementById(divName) : divName;
    if (!container) {
        console.error('Cannot find container for configuration menu');
        return;
    }

    // Check if config menu already exists
    let configContainer = container.querySelector('.plot-config-container');
    if (configContainer) {
        return; // Menu already exists
    }

    // Create main config container with grid layout
    configContainer = document.createElement('div');
    configContainer.className = 'plot-config-container';
    configContainer.style.cssText = `
        width: 100%;
        margin-bottom: 20px;
        order: -1; /* Ensure it appears before other elements in flex contexts */
        display: flex;
        justify-content: center;
    `;

    // Create grid container
    const gridContainer = document.createElement('div');
    gridContainer.className = 'grid';
    gridContainer.style.cssText = `
        justify-content: center;
        text-align: center;
        width: 100%;
        display: flex;
        justify-content: center;
    `;
    configContainer.appendChild(gridContainer);

    // Create cell for the main config dropdown
    const cell = document.createElement('div');
    cell.className = 'cell';

    // Create dropdown structure
    const dropdown = document.createElement('div');
    dropdown.className = 'dropdown is-hoverable';

    // Create dropdown trigger
    const dropdownTrigger = document.createElement('div');
    dropdownTrigger.className = 'dropdown-trigger';

    // Create main button
    const mainButton = document.createElement('button');
    mainButton.className = 'button';
    mainButton.setAttribute('aria-haspopup', 'true');
    mainButton.setAttribute('aria-controls', 'dropdown-plotconfig-main');

    const buttonText = document.createElement('span');
    buttonText.textContent = 'Plot Configuration';

    const buttonIcon = document.createElement('span');
    buttonIcon.className = 'icon is-small';
    buttonIcon.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"/></svg>';

    mainButton.appendChild(buttonText);
    mainButton.appendChild(buttonIcon);
    dropdownTrigger.appendChild(mainButton);

    // Create dropdown menu
    const dropdownMenu = document.createElement('div');
    dropdownMenu.className = 'dropdown-menu';
    dropdownMenu.id = 'dropdown-plotconfig-main';
    dropdownMenu.setAttribute('role', 'menu');
    dropdownMenu.style.cssText = `
        left: 50%;
        transform: translateX(-50%);
        position: absolute;
    `;

    // Create dropdown content
    const dropdownContent = document.createElement('div');
    dropdownContent.className = 'dropdown-content';
    dropdownContent.style.cssText = `
        min-width: 400px;
        max-width: 600px;
    `;

    dropdownMenu.appendChild(dropdownContent);

    // Assemble dropdown structure
    dropdown.appendChild(dropdownTrigger);
    dropdown.appendChild(dropdownMenu);
    cell.appendChild(dropdown);
    gridContainer.appendChild(cell);

    // Create config panel container (inside dropdown content)
    const configPanel = document.createElement('div');
    configPanel.className = 'config-panel';
    configPanel.style.cssText = `
        padding: 15px;
    `;
    dropdownContent.appendChild(configPanel);

    // Array to keep track of all sections for accordion behavior
    const allSections = [];

    // Create group sections to organize controls
    function createGroupSection(title) {
        const section = document.createElement('div');
        section.className = 'config-section';
        section.style.cssText = `
            margin-bottom: 20px;
            padding: 0px;
        `;

        // Create collapsible section header
        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'section-header is-clickable';
        sectionHeader.style.cssText = `
            display: flex;
            align-items: center;
            padding: 10px;
            background-color: rgb(245, 245, 245);
            border-radius: 4px;
            cursor: pointer;
            border: 1px solid rgb(224, 224, 224);
        `;

        // Section title
        const heading = document.createElement('h4');
        heading.textContent = title;
        heading.style.cssText = `
            margin: 0px;
            font-size: 1rem;
            font-weight: bold;
            flex-grow: 1;
        `;

        // Toggle icon - start with closed state
        const toggleIcon = document.createElement('span');
        toggleIcon.innerHTML = '►';
        toggleIcon.style.cssText = `
            margin-left: 10px;
            font-size: 0.8rem;
            transition: transform 0.2s;
        `;

        sectionHeader.appendChild(heading);
        sectionHeader.appendChild(toggleIcon);
        section.appendChild(sectionHeader);

        // Create content area for form elements - start closed
        const contentArea = document.createElement('div');
        contentArea.className = 'section-content';
        contentArea.style.cssText = `
            display: none;
            padding: 10px;
            border-right: 1px solid rgb(224, 224, 224);
            border-bottom: 1px solid rgb(224, 224, 224);
            border-left: 1px solid rgb(224, 224, 224);
            border-image: initial;
            border-top: none;
            background: rgb(255, 255, 255);
            border-radius: 0px 0px 4px 4px;
        `;

        // Create a flex container for form elements
        const flexContainer = document.createElement('div');
        flexContainer.className = 'config-flex-container';
        flexContainer.style.cssText = `
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: flex-start;
        `;

        contentArea.appendChild(flexContainer);
        section.appendChild(contentArea);

        // Store section data for accordion behavior
        const sectionData = {
            sectionHeader,
            contentArea,
            toggleIcon,
            isContentVisible: false, // Start closed
        };

        // Add this section to the allSections array
        allSections.push(sectionData);

        // Store a reference to close all other sections function
        section._closeOthers = () => {
            allSections.forEach((otherSection) => {
                if (otherSection !== sectionData) {
                    otherSection.isContentVisible = false;
                    otherSection.contentArea.style.display = 'none';
                    otherSection.toggleIcon.innerHTML = '►';
                    otherSection.toggleIcon.style.transform = 'rotate(-90deg)';
                }
            });
        };

        // Add click handler for accordion behavior
        sectionHeader.addEventListener('click', () => {
            const wasVisible = sectionData.isContentVisible;

            // Close all other sections first
            section._closeOthers();

            // Toggle this section
            sectionData.isContentVisible = !wasVisible;
            contentArea.style.display = sectionData.isContentVisible ? 'block' : 'none';
            toggleIcon.innerHTML = sectionData.isContentVisible ? '▼' : '►';
            toggleIcon.style.transform = sectionData.isContentVisible ? 'rotate(0)' : 'rotate(-90deg)';
        });

        // Override the appendChild method to add items to the flex container
        const originalAppendChild = section.appendChild;
        section.appendChild = function (element) {
            if (element !== sectionHeader && element !== contentArea && element !== flexContainer) {
                // Ensure each form control has proper styling for the flex layout
                if (element.classList.contains('form-group')) {
                    element.style.cssText += `
                        width: 100%;
                        flex: 1 1 auto;
                        min-width: 180px;
                        max-width: 300px;
                    `;
                }
                return flexContainer.appendChild(element);
            }
            return originalAppendChild.call(this, element);
        };

        return section;
    }

    // Theme section
    const themeSection = createGroupSection('Theme & Appearance');

    // Custom theme selector with SVG icons
    const themeGroup = document.createElement('div');
    themeGroup.className = 'form-group field';
    // themeGroup.style.cssText = `
    //     width: 100%;
    // `;

    const themeLabel = document.createElement('label');
    themeLabel.className = 'label is-small';
    themeLabel.textContent = 'Theme';
    themeGroup.appendChild(themeLabel);

    const themeContainer = document.createElement('div');
    themeContainer.style.cssText = `
        display: flex;
        gap: 10px;
        padding: 5px 0;
    `;

    // Light theme option
    const lightTheme = document.createElement('div');
    lightTheme.className = `theme-option ${config.theme === 'light' ? 'active' : ''}`;
    lightTheme.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 7C14.7614 7 17 9.23858 17 12C17 14.7614 14.7614 17 12 17C9.23858 17 7 14.7614 7 12C7 9.23858 9.23858 7 12 7ZM12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9Z" fill="currentColor"/>
        <path d="M12 2L12 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M12 20L12 22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M22 12L20 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M4 12L2 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M19.0711 4.92893L17.6569 6.34315" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M6.34315 17.6569L4.92893 19.0711" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M19.0711 19.0711L17.6569 17.6569" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M6.34315 6.34315L4.92893 4.92893" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`;
    lightTheme.style.cssText = `
        padding: 10px;
        border-radius: 4px;
        cursor: pointer;
        border: 1px solid ${config.theme === 'light' ? '#4285f4' : '#ddd'};
        background-color: ${config.theme === 'light' ? '#e8f0fe' : 'transparent'};
    `;
    lightTheme.dataset.value = 'light';

    // Dark theme option
    const darkTheme = document.createElement('div');
    darkTheme.className = `theme-option ${config.theme === 'dark' ? 'active' : ''}`;
    darkTheme.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20V4C16.42 4 20 7.58 20 12C20 16.42 16.42 20 12 20Z" fill="currentColor"/>
    </svg>`;
    darkTheme.style.cssText = `
        padding: 10px;
        border-radius: 4px;
        cursor: pointer;
        border: 1px solid ${config.theme === 'dark' ? '#4285f4' : '#ddd'};
        background-color: ${config.theme === 'dark' ? '#e8f0fe' : 'transparent'};
    `;
    darkTheme.dataset.value = 'dark';

    // Theme option click handlers
    [lightTheme, darkTheme].forEach((option) => {
        option.addEventListener('click', () => {
            const themeValue = option.dataset.value;
            config.theme = themeValue;

            // Update UI
            document.querySelectorAll('.theme-option').forEach((opt) => {
                opt.style.border = opt === option ? '1px solid #4285f4' : '1px solid #ddd';
                opt.style.backgroundColor = opt === option ? '#e8f0fe' : 'transparent';
            });

            updateCallback(config);
        });
    });

    themeContainer.appendChild(lightTheme);
    themeContainer.appendChild(darkTheme);
    themeGroup.appendChild(themeContainer);

    themeSection.appendChild(themeGroup);

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
            ['right', 'bottom', 'top', 'left'],
            (e) => {
                config.legend.position = e.target.value;
                updateCallback(config);
            }
        )
    );

    // Add legend label format options
    legendSection.appendChild(
        createFormGroup('Label Format', 'select', config.legend.label, 'config-legend-label', ['short', 'long'], (e) => {
            config.legend.label = e.target.value;
            updateCallback(config);
        })
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
    const annotationsSection = createGroupSection('Annotations');

    // Add checkbox to show/hide annotations
    annotationsSection.appendChild(
        createFormGroup('Show Annotations', 'checkbox', config.annotations.show, 'config-annotations-show', null, (e) => {
            config.annotations.show = e.target.checked;
            updateCallback(config);
        })
    );

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

    // Make container a flex container to control the order properly
    container.style.display = 'flex';
    container.style.flexDirection = 'column';

    // Insert config container at start of target container
    container.insertBefore(configContainer, container.firstChild);

    // Find any plotly graph containers and ensure they display properly
    Array.from(container.querySelectorAll('.js-plotly-plot')).forEach((plotContainer) => {
        if (plotContainer !== configContainer) {
            // Ensure the plot container takes full width
            plotContainer.style.width = '100%';
        }
    });
}

// Helper function to create form groups
export function createFormGroup(label, type, value, name, options, onChange) {
    let input, group, flexContainer;

    group = document.createElement('div');
    group.className = 'form-group field';
    group.style.cssText = `
        width: 100%;
        flex: 1 1 auto;
        min-width: 180px;
        max-width: 300px;
    `;

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
