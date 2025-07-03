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
import { setGraph } from './plot.js';

// Color palettes for graphs
const colorPalettes = {
    default: [
        '#5c77a5', '#dc842a', '#c85857', '#89b5b1', '#71a152',
        '#bab0ac', '#e15759', '#b07aa1', '#76b7b2', '#ff9da7'
    ],
    vibrant: [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
    ],
    pastel: [
        '#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF',
        '#E6E6FA', '#F0E68C', '#DDA0DD', '#98FB98', '#F5DEB3'
    ],
    dark: [
        '#2C3E50', '#E74C3C', '#3498DB', '#2ECC71', '#F39C12',
        '#9B59B6', '#1ABC9C', '#34495E', '#E67E22', '#95A5A6'
    ],
    monochrome: [
        '#2C3E50', '#34495E', '#5D6D7E', '#85929E', '#AEB6BF',
        '#D5DBDB', '#EAEDED', '#F8F9F9', '#BDC3C7', '#95A5A6'
    ]
};

// Contour colorscales
const contourColorscales = {
    default: [
        [0, 'rgb(0,0,168)'], [0.1, 'rgb(0,0,200)'], [0.2, 'rgb(0,74,255)'],
        [0.3, 'rgb(0,152,255)'], [0.4, 'rgb(74,255,161)'], [0.5, 'rgb(161,255,74)'],
        [0.6, 'rgb(255,255,0)'], [0.7, 'rgb(234,159,0)'], [0.8, 'rgb(255,74,0)'],
        [0.9, 'rgb(222,74,0)'], [1, 'rgb(253,14,13)']
    ],
    viridis: [
        [0, 'rgb(68,1,84)'], [0.1, 'rgb(72,40,120)'], [0.2, 'rgb(62,74,137)'],
        [0.3, 'rgb(49,104,142)'], [0.4, 'rgb(38,130,142)'], [0.5, 'rgb(31,158,137)'],
        [0.6, 'rgb(53,183,121)'], [0.7, 'rgb(109,205,89)'], [0.8, 'rgb(180,222,44)'],
        [0.9, 'rgb(253,231,37)'], [1, 'rgb(253,231,37)']
    ],
    plasma: [
        [0, 'rgb(13,8,135)'], [0.1, 'rgb(75,3,161)'], [0.2, 'rgb(125,3,168)'],
        [0.3, 'rgb(168,34,150)'], [0.4, 'rgb(203,70,121)'], [0.5, 'rgb(229,107,93)'],
        [0.6, 'rgb(248,148,65)'], [0.7, 'rgb(253,195,40)'], [0.8, 'rgb(239,248,33)'],
        [0.9, 'rgb(240,249,33)'], [1, 'rgb(240,249,33)']
    ],
    cool: [
        [0, 'rgb(0,255,255)'], [0.1, 'rgb(25,230,255)'], [0.2, 'rgb(51,204,255)'],
        [0.3, 'rgb(76,179,255)'], [0.4, 'rgb(102,153,255)'], [0.5, 'rgb(127,128,255)'],
        [0.6, 'rgb(153,102,255)'], [0.7, 'rgb(178,76,255)'], [0.8, 'rgb(204,51,255)'],
        [0.9, 'rgb(229,25,255)'], [1, 'rgb(255,0,255)']
    ],
    hot: [
        [0, 'rgb(0,0,0)'], [0.1, 'rgb(26,0,0)'], [0.2, 'rgb(51,0,0)'],
        [0.3, 'rgb(77,0,0)'], [0.4, 'rgb(102,0,0)'], [0.5, 'rgb(128,0,0)'],
        [0.6, 'rgb(153,51,0)'], [0.7, 'rgb(179,102,0)'], [0.8, 'rgb(204,153,0)'],
        [0.9, 'rgb(230,204,0)'], [1, 'rgb(255,255,255)']
    ]
};

// Default configuration options for plots
const defaultConfig = {
    font: {
        family: 'Arial, sans-serif',
        size: 12,
        color: '#333333'
    },
    theme: 'light', // 'light' or 'dark'
    grid: true,
    legend: {
        position: 'right', // 'right', 'bottom', 'top', 'left'
        show: true
    },
    margin: {
        l: 50,
        r: 50,
        t: 80,
        b: 50
    },
    colors: {
        palette: 'default' // 'default', 'vibrant', 'pastel', 'dark', 'monochrome'
    },
    layout: {
        direction: 'horizontal' // 'horizontal' (left/right) or 'vertical' (top/down) for multiple graphs
    },
    contour: {
        colorscale: 'default' // 'default', 'viridis', 'plasma', 'cool', 'hot'
    }
};

// Local storage key for configuration
const CONFIG_STORAGE_KEY = 'spinorama-plot-config';

// Save configuration to local storage
function saveConfigToStorage(config) {
    try {
        localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
    } catch (error) {
        console.warn('Failed to save configuration to local storage:', error);
    }
}

// Load configuration from local storage
function loadConfigFromStorage() {
    try {
        const stored = localStorage.getItem(CONFIG_STORAGE_KEY);
        if (stored) {
            const parsedConfig = JSON.parse(stored);
            // Merge with default config to ensure all properties exist
            return mergeConfigs(defaultConfig, parsedConfig);
        }
    } catch (error) {
        console.warn('Failed to load configuration from local storage:', error);
    }
    return JSON.parse(JSON.stringify(defaultConfig));
}

// Deep merge two configuration objects
function mergeConfigs(defaultConf, userConf) {
    const result = JSON.parse(JSON.stringify(defaultConf));

    function deepMerge(target, source) {
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                if (!target[key] || typeof target[key] !== 'object') {
                    target[key] = {};
                }
                deepMerge(target[key], source[key]);
            } else {
                target[key] = source[key];
            }
        }
    }

    deepMerge(result, userConf);
    return result;
}

// Create plot configuration menu
function createConfigMenu(divName, config, updateCallback) {
    // Handle both string IDs and DOM element objects
    const divId = typeof divName === 'string' ? divName : divName.id || 'plot-' + Math.random().toString(36).substr(2, 9);
    const menuId = `${divId}-config-menu`;
    const menuContainerId = `${divId}-config-container`;

    // Create container for the menu
    const container = document.createElement('div');
    container.id = menuContainerId;
    container.className = 'plot-config-container';
    container.style.cssText = 'margin-bottom: 10px; padding: 5px; border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9;';

    // Create toggle button
    const toggleBtn = document.createElement('button');
    toggleBtn.textContent = 'Configure Plot';
    toggleBtn.className = 'plot-config-toggle';
    toggleBtn.style.cssText = 'padding: 3px 8px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;';

    // Create menu div (initially hidden) - using flex layout for single-line
    const menu = document.createElement('div');
    menu.id = menuId;
    menu.className = 'plot-config-menu';
    menu.style.display = 'none';
    menu.style.cssText = 'display: none; flex-flow: row wrap; align-items: left; gap: 8px; overflow-x: auto; padding: 5px 0;';


    // Font family selection
    const fontFamilyGroup = createFormGroup('Family', 'select', config.font.family, 'fontfamily', [
        { value: 'Arial, sans-serif', text: 'Arial' },
        { value: '"Times New Roman", serif', text: 'Times New Roman' },
        { value: 'Roboto, sans-serif', text: 'Roboto' },
        { value: 'Courier, monospace', text: 'Courier' }
    ], (value) => {
        config.font.family = value;
        updateCallback(config);
    });

    // Font size selection
    const fontSizeGroup = createFormGroup('Size', 'select', config.font.size.toString(), 'fontsize', [
        { value: '10', text: '10px' },
        { value: '11', text: '11px' },
        { value: '12', text: '12px' },
        { value: '14', text: '14px' },
        { value: '16', text: '16px' },
        { value: '18', text: '18px' }
    ], (value) => {
        config.font.size = parseInt(value, 10);
        updateCallback(config);
    });

    // Theme selection
    const themeGroup = createFormGroup('Theme', 'select', config.theme, 'theme', [
        { value: 'light', text: 'Light' },
        { value: 'dark', text: 'Dark' }
    ], (value) => {
        config.theme = value;
        updateCallback(config);
    });

    // Grid toggle
    const gridGroup = createFormGroup('Grid', 'checkbox', config.grid, 'grid', null, (value) => {
        config.grid = value;
        updateCallback(config);
    });

    // Legend position
    const legendPosGroup = createFormGroup('Position', 'select', config.legend.position, 'legendposition', [
        { value: 'right', text: 'Right' },
        { value: 'bottom', text: 'Bottom' },
        { value: 'top', text: 'Top' },
        { value: 'left', text: 'Left' }
    ], (value) => {
        config.legend.position = value;
        updateCallback(config);
    });

    // Legend visibility
    const legendVisGroup = createFormGroup('Show', 'checkbox', config.legend.show, 'showLegend', null, (value) => {
        config.legend.show = value;
        updateCallback(config);
    });

    // Color palette selection
    const colorPaletteGroup = createFormGroup('Palette', 'select', config.colors.palette, 'colorpalette', [
        { value: 'default', text: 'Default' },
        { value: 'vibrant', text: 'Vibrant' },
        { value: 'pastel', text: 'Pastel' },
        { value: 'dark', text: 'Dark' },
        { value: 'monochrome', text: 'Monochrome' }
    ], (value) => {
        config.colors.palette = value;
        updateCallback(config);
    });

    // Layout direction for multiple graphs
    const layoutDirectionGroup = createFormGroup('Direction', 'select', config.layout.direction, 'layoutdirection', [
        { value: 'horizontal', text: 'Side by Side' },
        { value: 'vertical', text: 'Top to Bottom' }
    ], (value) => {
        config.layout.direction = value;
        updateCallback(config);
    });

    // Contour colorscale selection
    const contourColorscaleGroup = createFormGroup('Contour', 'select', config.contour.colorscale, 'contourcolorscale', [
        { value: 'default', text: 'Default (Blue-Red)' },
        { value: 'viridis', text: 'Viridis (Purple-Yellow)' },
        { value: 'plasma', text: 'Plasma (Purple-Pink)' },
        { value: 'cool', text: 'Cool (Cyan-Magenta)' },
        { value: 'hot', text: 'Hot (Black-White)' }
    ], (value) => {
        config.contour.colorscale = value;
        updateCallback(config);
    });

    // Margin controls
    const marginTopGroup = createFormGroup('Top', 'range', config.margin.t.toString(), 'marginTop', { min: 0, max: 150, step: 5 }, (value) => {
        config.margin.t = parseInt(value, 10);
        updateCallback(config);
    });

    const marginBottomGroup = createFormGroup('Bottom', 'range', config.margin.b.toString(), 'marginBottom', { min: 0, max: 150, step: 5 }, (value) => {
        config.margin.b = parseInt(value, 10);
        updateCallback(config);
    });

    const marginLeftGroup = createFormGroup('Left', 'range', config.margin.l.toString(), 'marginLeft', { min: 0, max: 150, step: 5 }, (value) => {
        config.margin.l = parseInt(value, 10);
        updateCallback(config);
    });

    const marginRightGroup = createFormGroup('Right', 'range', config.margin.r.toString(), 'marginRight', { min: 0, max: 150, step: 5 }, (value) => {
        config.margin.r = parseInt(value, 10);
        updateCallback(config);
    });

    // Create group sections to organize controls
    const createGroupSection = (title) => {
        const section = document.createElement('div');
        section.className = 'config-section';
        section.style.cssText = 'display: flex; flex-direction: column; border-right: 1px solid #ddd; padding-right: 8px; margin-right: 8px;';

        if (title) {
            const titleSpan = document.createElement('span');
            titleSpan.textContent = title;
            titleSpan.style.cssText = 'font-weight: bold; font-size: 12px; margin-right: 5px; text-align: center;';
            section.appendChild(titleSpan);

            // Add a controls container for the form groups
            const controlsContainer = document.createElement('div');
            controlsContainer.style.cssText = 'display: flex; flex-wrap: wrap; align-items: center; justify-content: center;';
            section.appendChild(controlsContainer);
            section.controlsContainer = controlsContainer; // Store reference for appending children
        }

        return section;
    };

    // Group 1: Font settings
    const fontSection = createGroupSection('Font');
    fontSection.controlsContainer.appendChild(fontFamilyGroup);
    fontSection.controlsContainer.appendChild(fontSizeGroup);
    menu.appendChild(fontSection);

    // Group 2: Theme & Grid
    const themeSection = createGroupSection('Display');
    themeSection.controlsContainer.appendChild(themeGroup);
    themeSection.controlsContainer.appendChild(gridGroup);
    menu.appendChild(themeSection);

    // Group 3: Legend settings
    const legendSection = createGroupSection('Legend');
    legendSection.controlsContainer.appendChild(legendPosGroup);
    legendSection.controlsContainer.appendChild(legendVisGroup);
    menu.appendChild(legendSection);

    // Group 4: Colors
    const colorSection = createGroupSection('Colors');
    colorSection.controlsContainer.appendChild(colorPaletteGroup);
    colorSection.controlsContainer.appendChild(contourColorscaleGroup);
    menu.appendChild(colorSection);

    // Group 5: Layout
    const layoutSection = createGroupSection('Layout');
    layoutSection.controlsContainer.appendChild(layoutDirectionGroup);
    menu.appendChild(layoutSection);

    // Group 6: Margins
    const marginSection = createGroupSection('Margins');
    marginSection.controlsContainer.appendChild(marginTopGroup);
    marginSection.controlsContainer.appendChild(marginBottomGroup);
    marginSection.controlsContainer.appendChild(marginLeftGroup);
    marginSection.controlsContainer.appendChild(marginRightGroup);
    menu.appendChild(marginSection);

    // Add reset button
    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Reset to Defaults';
    resetBtn.className = 'plot-config-reset';
    resetBtn.style.cssText = 'padding: 3px 8px; background-color: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: auto;';
    resetBtn.addEventListener('click', () => {
        Object.assign(config, JSON.parse(JSON.stringify(defaultConfig)));
        updateCallback(config);

        // Update all form controls to reflect default values
        const selects = menu.querySelectorAll('select');
        selects.forEach(select => {
            const name = select.name;
            if (name === 'fontfamily') select.value = config.font.family;
            if (name === 'fontsize') select.value = config.font.size.toString();
            if (name === 'theme') select.value = config.theme;
            if (name === 'legendposition') select.value = config.legend.position;
            if (name === 'colorpalette') select.value = config.colors.palette;
            if (name === 'layoutdirection') select.value = config.layout.direction;
            if (name === 'contourcolorscale') select.value = config.contour.colorscale;
        });

        const checkboxes = menu.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            const name = checkbox.name;
            if (name === 'grid') checkbox.checked = config.grid;
            if (name === 'showLegend') checkbox.checked = config.legend.show;
        });

        const ranges = menu.querySelectorAll('input[type="range"]');
        ranges.forEach(range => {
            const name = range.name;
            if (name === 'marginTop') {
                range.value = config.margin.t;
                range.nextElementSibling.textContent = config.margin.t;
            }
            if (name === 'marginBottom') {
                range.value = config.margin.b;
                range.nextElementSibling.textContent = config.margin.b;
            }
            if (name === 'marginLeft') {
                range.value = config.margin.l;
                range.nextElementSibling.textContent = config.margin.l;
            }
            if (name === 'marginRight') {
                range.value = config.margin.r;
                range.nextElementSibling.textContent = config.margin.r;
            }
        });
    });

    menu.appendChild(resetBtn);

    // Toggle menu visibility when button is clicked
    toggleBtn.addEventListener('click', () => {
        if (menu.style.display === 'none') {
            menu.style.display = 'flex';
            toggleBtn.textContent = 'Hide Configuration';
        } else {
            menu.style.display = 'none';
            toggleBtn.textContent = 'Configure Plot';
        }
    });

    // Add button and menu to container - using flex layout
    container.style.display = 'flex';
    container.style.flexDirection = 'column';

    const topRow = document.createElement('div');
    topRow.style.cssText = 'display: flex; align-items: center;';
    topRow.appendChild(toggleBtn);

    container.appendChild(topRow);
    container.appendChild(menu);

    // Insert the container before the plot div
    let plotDiv;
    if (typeof divName === 'string') {
        plotDiv = document.getElementById(divName);
        if (!plotDiv) {
            console.error(`Error: Element with ID "${divName}" not found. Cannot add configuration menu.`);
            return config;
        }
    } else if (divName instanceof HTMLElement) {
        plotDiv = divName;
    } else {
        console.error('Error: divName must be a string ID or HTMLElement');
        return config;
    }
    plotDiv.parentNode.insertBefore(container, plotDiv);

    return config;
}

// Helper function to create form groups
function createFormGroup(label, type, value, name, options, onChange) {
    const group = document.createElement('div');
    group.className = 'plot-config-group';
    group.style.cssText = 'margin: 0 4px; display: inline-block; vertical-align: top;';

    // Create label
    const labelElement = document.createElement('label');
    labelElement.textContent = label;
    labelElement.style.cssText = 'display: block; margin-bottom: 2px; font-size: 11px; color: #555;';
    group.appendChild(labelElement);

    let input;

    if (type === 'select') {
        input = document.createElement('select');
        input.name = name || label.toLowerCase().replace(/\s+/g, '');
        input.style.cssText = 'padding: 4px; border: 1px solid #ddd; border-radius: 4px; max-width: 70px';

        options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.text;
            if (opt.value === value) {
                option.selected = true;
            }
            input.appendChild(option);
        });

        input.addEventListener('change', (e) => {
            onChange(e.target.value);
        });
    } else if (type === 'checkbox') {
        input = document.createElement('input');
        input.type = 'checkbox';
        input.name = name || label.toLowerCase().replace(/\s+/g, '');
        input.checked = value;
        input.style.cssText = 'margin-left: 5px; margin-right: 5px;';

        const checkboxContainer = document.createElement('div');
        checkboxContainer.style.cssText = 'display: flex; align-items: center;';

        checkboxContainer.appendChild(input);
        group.appendChild(checkboxContainer);

        input.addEventListener('change', (e) => {
            onChange(e.target.checked);
        });
    } else if (type === 'range') {
        const rangeContainer = document.createElement('div');
        rangeContainer.style.cssText = 'display: flex; align-items: center;';

        input = document.createElement('input');
        input.type = 'range';
        input.name = name || label.toLowerCase().replace(/\s+/g, '');
        input.min = options.min;
        input.max = options.max;
        input.step = options.step || 1;
        input.value = value;
        input.style.cssText = 'flex-grow: 1; margin-right: 10px;';

        const valueDisplay = document.createElement('span');
        valueDisplay.textContent = value;
        valueDisplay.style.cssText = 'min-width: 30px; text-align: right;';

        input.addEventListener('input', (e) => {
            valueDisplay.textContent = e.target.value;
            onChange(e.target.value);
        });

        rangeContainer.appendChild(input);
        rangeContainer.appendChild(valueDisplay);
        group.appendChild(rangeContainer);
        return group;
    }

    if (type !== 'range') {
        group.appendChild(input);
    }

    return group;
}

// Apply configuration to plot options
function applyConfig(options, config) {
    // Define font configuration for use throughout the function
    const bgColor = config.theme === 'dark' ? '#333333' : '#ffffff';
    const gridColor = config.theme === 'dark' ? '#555555' : '#e6e6e6';
    const titleFontConfig = {
        family: config.font.family,
        size: config.font.size+2,
        color: config.theme === 'dark' ? '#ffffff' : '#333333'
    };

    const fontConfig = {
        family: config.font.family,
        size: config.font.size,
        color: config.theme === 'dark' ? '#ffffff' : '#333333'
    };

    // Apply font settings
    if (options.layout) {

        // Apply global font settings
        options.layout.font = fontConfig;

        // Apply theme
        options.layout.paper_bgcolor = bgColor;
        options.layout.plot_bgcolor = bgColor;

        // Apply font and grid settings to x-axis
        if (options.layout.xaxis) {
            options.layout.xaxis.showgrid = config.grid;
            options.layout.xaxis.gridcolor = gridColor;
	    if (options.layout.xaxis.title && options.layout.xaxis.title.font) {
		options.layout.xaxis.title.font = fontConfig;
	    }
            options.layout.xaxis.tickfont = fontConfig;
        }
        if (options.layout.xaxis2) {
            options.layout.xaxis2.showgrid = config.grid;
            options.layout.xaxis2.gridcolor = gridColor;
	    if (options.layout.xaxis2.title && options.layout.xaxis2.title.font) {
		options.layout.xaxis2.title.font = fontConfig;
	    }
            options.layout.xaxis2.tickfont = fontConfig;
        }

        // Apply font and grid settings to y-axis
        if (options.layout.yaxis) {
            options.layout.yaxis.showgrid = config.grid;
            options.layout.yaxis.gridcolor = gridColor;
	    if (options.layout.yaxis.title && options.layout.yaxis.title.font) {
		options.layout.yaxis.title.font = fontConfig;
	    }
            options.layout.yaxis.tickfont = fontConfig;
        }
        if (options.layout.yaxis2) {
            options.layout.yaxis2.showgrid = config.grid;
            options.layout.yaxis2.gridcolor = gridColor;
	    if (options.layout.yaxis2.title && options.layout.yaxis2.title.font) {
		options.layout.yaxis2.title.font = fontConfig;
	    }
            options.layout.yaxis2.tickfont = fontConfig;
        }

        // Apply font settings to title
        if (options.layout.title) {
            if (typeof options.layout.title === 'string') {
                options.layout.title = {
                    text: options.layout.title,
                    font: titleFontConfig
                };
            } else {
                options.layout.title.font = titleFontConfig;
            }
        }

        // Apply font settings to annotations (if any)
        if (options.layout.annotations && Array.isArray(options.layout.annotations)) {
            options.layout.annotations.forEach(annotation => {
                annotation.font = fontConfig;
            });
        }

        // Apply font settings to colorbar (if any)
        if (options.layout.coloraxis && options.layout.coloraxis.colorbar) {
            options.layout.coloraxis.colorbar.titlefont = fontConfig;
            options.layout.coloraxis.colorbar.tickfont = fontConfig;
        }

	// Apply legend settings
	if (options.layout.legend) {
            options.layout.legend.font = fontConfig;

            options.layout.showlegend = config.legend.show;

            switch (config.legend.position) {
            case 'right':
		options.layout.legend.x = 1;
		options.layout.legend.y = 0.5;
		options.layout.legend.xanchor = 'left';
		options.layout.legend.yanchor = 'middle';
		break;
            case 'bottom':
		options.layout.legend.x = 0.5;
		options.layout.legend.y = -0.2;
		options.layout.legend.xanchor = 'center';
		options.layout.legend.yanchor = 'top';
		options.layout.legend.orientation = 'h';
		break;
            case 'top':
		options.layout.legend.x = 0.5;
		options.layout.legend.y = 1.1;
		options.layout.legend.xanchor = 'center';
		options.layout.legend.yanchor = 'bottom';
		options.layout.legend.orientation = 'h';
		break;
            case 'left':
		options.layout.legend.x = -0.1;
		options.layout.legend.y = 0.5;
		options.layout.legend.xanchor = 'right';
            options.layout.legend.yanchor = 'middle';
		break;
            }
	}

	// Apply margin settings
	if (options.layout.margin) {
	    options.layout.margin = {
		l: config.margin.l,
		r: config.margin.r,
		t: config.margin.t,
		b: config.margin.b
	    };
	}
    }

    // Apply font settings to data traces
    if (options.data && Array.isArray(options.data)) {

        options.data.forEach( trace => {

	    if (trace.colorbar) {
		if (trace.colorbar.tickfont) {
                    trace.tickfont = fontConfig;
		}
		if (trace.colorbar.title && trace.colorbar.title.text) {
		    if (typeof trace.colorbar.title === 'string') {
			trace.colorbar.title = {
			    text: trace.colorbar.title.text,
			    font: fontConfig,
			};
		    } else {
			trace.colorbar.title.font = fontConfig;
		    }
		}
	    }

            if (trace.marker && trace.marker.textfont) {
                trace.marker.textfont = { ...trace.marker.textfont, ...fontConfig };
            }

            if (trace.hoverlabel && trace.hoverlabel.font) {
                trace.hoverlabel.font = { ...trace.hoverlabel.font, ...fontConfig };
            }

	    trace.showlegend = config.legend.show;
        });

	if (config.colors && config.colors.palette) {
            const selectedPalette = colorPalettes[config.colors.palette] || colorPalettes.default;
            options.data.forEach((trace, index) => {
		if (trace.marker?.color && trace.type === 'scatter') {
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

	if (config.contour && config.contour.colorscale) {
            const selectedColorscale = contourColorscales[config.contour.colorscale] || contourColorscales.default;
            options.data.forEach(trace => {
		if (trace.type === 'contour' || trace.type === 'heatmap' ||
                    trace.type === 'surface' || trace.type === 'contourgl') {
                    trace.colorscale = selectedColorscale;
		}
            });
	}
    }

    // Apply layout direction for multiple graphs (this will be used by the calling code)
    if (config.layout && config.layout.direction) {
        options._layoutDirection = config.layout.direction;
    }

    return options;
}

export function displayGraph(measurementName, jsonName, divName, graphSpec) {
    // Ensure divName is either a string ID or an HTMLElement
    if (typeof divName !== 'string' && !(divName instanceof HTMLElement)) {
        console.error('Error: divName must be a string ID or HTMLElement', divName);
        return Promise.reject(new Error('Invalid divName parameter'));
    }
    // Create a config object for this graph, loading from storage if available
    const config = loadConfigFromStorage();

    async function run() {
        const w = window.innerWidth;
        const h = window.innerHeight;

        const title = graphSpec.layout.title.text;
        let graphOptions = setGraph(measurementName, [title], [graphSpec], w, h, 1);

        if (graphOptions?.length >= 1) {
            let options = graphOptions[0];
            if (jsonName.indexOf('3D') !== -1) {
                if (options.layout) {
                    options.layout.shapes = null;
                }
            }

            // Create configuration menu and get initial config
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

            // Apply initial configuration
            options = applyConfig(options, config);

            // Plot the graph
            // Get the actual element if divName is a string ID
            const targetElement = typeof divName === 'string' ? document.getElementById(divName) : divName;
            if (!targetElement) {
                console.error(`Error: Target element not found for plotting`);
                return;
            }
            Plotly.newPlot(targetElement, options);
        }
    }

    return run();
}

// Export the color palettes and contour colorscales for use in other modules
export { colorPalettes, contourColorscales };
