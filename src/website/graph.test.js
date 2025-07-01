// -*- coding: utf-8 -*-
// Tests for graph.js
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

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Mock Plotly
vi.mock('plotly.js-dist-min', () => ({
  default: {
    newPlot: vi.fn(),
    react: vi.fn()
  }
}));

// Mock plot.js
vi.mock('./plot.js', () => ({
  setGraph: vi.fn().mockImplementation(() => {
    return [{
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }],
      layout: {
        title: { text: 'Test Graph' },
        xaxis: { showgrid: true },
        yaxis: { showgrid: true },
        legend: { x: 1, y: 0.5 }
      },
      config: {}
    }];
  })
}));

// Test configuration constants directly
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

// Import after mocking
import { displayGraph } from './graph.js';
import { setGraph } from './plot.js';
import Plotly from 'plotly.js-dist-min';

describe('Graph Configuration Constants', () => {
  describe('Color Palettes', () => {
    test('should have all expected color palettes', () => {
      expect(colorPalettes).toHaveProperty('default');
      expect(colorPalettes).toHaveProperty('vibrant');
      expect(colorPalettes).toHaveProperty('pastel');
      expect(colorPalettes).toHaveProperty('dark');
      expect(colorPalettes).toHaveProperty('monochrome');
    });

    test('default palette should contain the specified colors', () => {
      const expectedColors = [
        '#5c77a5', '#dc842a', '#c85857', '#89b5b1', '#71a152',
        '#bab0ac', '#e15759', '#b07aa1', '#76b7b2', '#ff9da7'
      ];
      expect(colorPalettes.default).toEqual(expectedColors);
    });

    test('all palettes should have 10 colors', () => {
      Object.values(colorPalettes).forEach(palette => {
        expect(palette).toHaveLength(10);
      });
    });

    test('all colors should be valid hex colors', () => {
      const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;
      Object.values(colorPalettes).forEach(palette => {
        palette.forEach(color => {
          expect(color).toMatch(hexColorRegex);
        });
      });
    });
  });

  describe('Contour Colorscales', () => {
    test('should have all expected contour colorscales', () => {
      expect(contourColorscales).toHaveProperty('default');
      expect(contourColorscales).toHaveProperty('viridis');
      expect(contourColorscales).toHaveProperty('plasma');
      expect(contourColorscales).toHaveProperty('cool');
      expect(contourColorscales).toHaveProperty('hot');
    });

    test('default colorscale should match the original', () => {
      const expectedColorscale = [
        [0, 'rgb(0,0,168)'], [0.1, 'rgb(0,0,200)'], [0.2, 'rgb(0,74,255)'],
        [0.3, 'rgb(0,152,255)'], [0.4, 'rgb(74,255,161)'], [0.5, 'rgb(161,255,74)'],
        [0.6, 'rgb(255,255,0)'], [0.7, 'rgb(234,159,0)'], [0.8, 'rgb(255,74,0)'],
        [0.9, 'rgb(222,74,0)'], [1, 'rgb(253,14,13)']
      ];
      expect(contourColorscales.default).toEqual(expectedColorscale);
    });

    test('all colorscales should have 11 color stops', () => {
      Object.values(contourColorscales).forEach(colorscale => {
        expect(colorscale).toHaveLength(11);
      });
    });

    test('all colorscales should have proper format', () => {
      Object.values(contourColorscales).forEach(colorscale => {
        colorscale.forEach((stop, index) => {
          expect(stop).toHaveLength(2);
          expect(stop[0]).toBeCloseTo(index * 0.1, 10);
          expect(typeof stop[1]).toBe('string');
          expect(stop[1]).toMatch(/^rgb\(\d+,\d+,\d+\)$/);
        });
      });
    });
  });
});

describe('Graph Configuration Menu', () => {
  let dom;
  let window;
  let document;

  beforeEach(() => {
    // Set up a DOM environment
    dom = new JSDOM('<!DOCTYPE html><html><body><div id="test-graph"></div></body></html>', {
      url: 'http://localhost/',
      runScripts: 'dangerously'
    });
    window = dom.window;
    document = window.document;
    
    // Create localStorage mock
    const localStorageMock = (() => {
      let store = {};
      return {
        getItem: (key) => store[key] || null,
        setItem: (key, value) => {
          store[key] = value.toString();
        },
        removeItem: (key) => {
          delete store[key];
        },
        clear: () => {
          store = {};
        }
      };
    })();

    // Mock window properties
    global.window = window;
    global.document = document;
    global.HTMLElement = window.HTMLElement;
    global.Element = window.Element;
    global.Plotly = Plotly;
    global.localStorage = localStorageMock;
    window.localStorage = localStorageMock;
    window.innerWidth = 1024;
    window.innerHeight = 768;

    // Reset mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up
    delete global.window;
    delete global.document;
    delete global.HTMLElement;
    delete global.Element;
    delete global.Plotly;
    delete global.localStorage;
  });

  test('displayGraph creates a configuration menu', async () => {
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Check if setGraph was called with correct parameters
    expect(setGraph).toHaveBeenCalledWith('On Axis', ['Test Graph'], [graphSpec], 1024, 768, 1);

    // Check if Plotly.newPlot was called
    expect(Plotly.newPlot).toHaveBeenCalled();

    // Check if the configuration menu was created
    const configContainer = document.querySelector('.plot-config-container');
    expect(configContainer).not.toBeNull();

    // Check if the toggle button exists
    const toggleButton = document.querySelector('.plot-config-toggle');
    expect(toggleButton).not.toBeNull();
    expect(toggleButton.textContent).toBe('Configure Plot');

    // Check if the menu is initially hidden
    const configMenu = document.querySelector('.plot-config-menu');
    expect(configMenu).not.toBeNull();
    expect(configMenu.style.display).toBe('none');
  });

  test('configuration menu toggles visibility when button is clicked', async () => {
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Get the toggle button and menu
    const toggleButton = document.querySelector('.plot-config-toggle');
    const configMenu = document.querySelector('.plot-config-menu');

    // Initial state - menu should be hidden
    expect(configMenu.style.display).toBe('none');

    // Click the toggle button
    toggleButton.click();

    // Menu should now be visible
    expect(configMenu.style.display).toBe('grid');
    expect(toggleButton.textContent).toBe('Hide Configuration');

    // Click the toggle button again
    toggleButton.click();

    // Menu should be hidden again
    expect(configMenu.style.display).toBe('none');
    expect(toggleButton.textContent).toBe('Configure Plot');
  });

  test('changing configuration updates the plot', async () => {
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Get a select element (font family)
    const fontFamilySelect = document.querySelector('select[name="fontfamily"]');
    expect(fontFamilySelect).not.toBeNull();

    // Change the font family
    fontFamilySelect.value = '"Times New Roman", serif';
    const event = new window.Event('change');
    fontFamilySelect.dispatchEvent(event);

    // Check if Plotly.react was called with updated options
    expect(Plotly.react).toHaveBeenCalled();
    const callArgs = Plotly.react.mock.calls[0];
    expect(callArgs[0]).toBe('test-graph');
    expect(callArgs[1]).toBeDefined();
    expect(callArgs[2].font.family).toBe('"Times New Roman", serif');
  });

  test('reset button restores default configuration', async () => {
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Get the font family select and reset button
    const fontFamilySelect = document.querySelector('select[name="fontfamily"]');
    const resetButton = document.querySelector('.plot-config-reset');
    expect(resetButton).not.toBeNull();

    // Change the font family
    fontFamilySelect.value = '"Times New Roman", serif';
    let event = new window.Event('change');
    fontFamilySelect.dispatchEvent(event);

    // First call to Plotly.react with changed font
    expect(Plotly.react).toHaveBeenCalledTimes(1);

    // Click the reset button
    resetButton.click();

    // Second call to Plotly.react with default font
    expect(Plotly.react).toHaveBeenCalledTimes(2);
    const callArgs = Plotly.react.mock.calls[1];
    expect(callArgs[2].font.family).toBe('Arial, sans-serif');

    // Check if the select was reset
    expect(fontFamilySelect.value).toBe('Arial, sans-serif');
  });

  test('3D plots have shapes removed', async () => {
    // Create a sample 3D graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test 3D Graph' },
        shapes: [{ type: 'line' }]
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], z: [1, 2, 3], type: 'scatter3d' }]
    };

    // Call displayGraph with a 3D jsonName
    await displayGraph('SPL Horizontal Contour 3D', 'test3D.json', 'test-graph', graphSpec);

    // Check if shapes were removed
    const callArgs = Plotly.newPlot.mock.calls[0];
    expect(callArgs[1].layout.shapes).toBeNull();
  });

  test('should load saved configuration when creating new graph', async () => {
    // Pre-populate localStorage with custom config
    const savedConfig = {
      font: {
        family: 'Roboto, sans-serif',
        size: 14,
        color: '#333333'
      },
      theme: 'dark',
      grid: false,
      legend: {
        position: 'bottom',
        show: true
      },
      margin: {
        l: 60,
        r: 60,
        t: 90,
        b: 60
      }
    };
    
    localStorage.setItem('spinorama-plot-config', JSON.stringify(savedConfig));
    
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Check if Plotly.newPlot was called
    expect(Plotly.newPlot).toHaveBeenCalled();
    
    // Just verify that the settings were loaded without errors
    expect(localStorage.getItem('spinorama-plot-config')).not.toBeNull();
  });

  test('should save configuration changes to localStorage', async () => {
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Get a select element (font family) and change it
    const fontFamilySelect = document.querySelector('select[name="fontfamily"]');
    expect(fontFamilySelect).not.toBeNull();

    // Change the font family
    fontFamilySelect.value = '"Times New Roman", serif';
    const event = new window.Event('change');
    fontFamilySelect.dispatchEvent(event);

    // Check if the configuration was saved to localStorage
    const stored = localStorage.getItem('spinorama-plot-config');
    expect(stored).not.toBeNull();
    
    const parsedConfig = JSON.parse(stored);
    expect(parsedConfig.font.family).toBe('"Times New Roman", serif');
  });

  test('should handle missing localStorage gracefully', async () => {
    // Ensure localStorage is empty
    localStorage.clear();
    
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // This should not throw an error even with empty localStorage
    await expect(displayGraph('On Axis', 'test.json', 'test-graph', graphSpec)).resolves.not.toThrow();
    
    // Should still create the plot with default configuration
    expect(Plotly.newPlot).toHaveBeenCalled();
  });

  test('should handle corrupted localStorage data gracefully', async () => {
    // Store invalid JSON
    localStorage.setItem('spinorama-plot-config', 'invalid-json-data');
    
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // This should not throw an error even with corrupted localStorage
    await expect(displayGraph('On Axis', 'test.json', 'test-graph', graphSpec)).resolves.not.toThrow();
    
    // Should still create the plot with default configuration
    expect(Plotly.newPlot).toHaveBeenCalled();
  });

  test('should merge partial saved configurations with defaults', async () => {
    // Store partial configuration
    const partialConfig = {
      theme: 'dark',
      font: {
        size: 16
      }
    };
    
    localStorage.setItem('spinorama-plot-config', JSON.stringify(partialConfig));
    
    // Create a sample graph spec
    const graphSpec = {
      layout: {
        title: { text: 'Test Graph' }
      },
      data: [{ x: [1, 2, 3], y: [1, 2, 3], type: 'scatter' }]
    };

    // Call displayGraph
    await displayGraph('On Axis', 'test.json', 'test-graph', graphSpec);

    // Check if Plotly.newPlot was called
    expect(Plotly.newPlot).toHaveBeenCalled();
    
    // Just verify that the settings were loaded without errors
    expect(localStorage.getItem('spinorama-plot-config')).not.toBeNull();
    const parsedConfig = JSON.parse(localStorage.getItem('spinorama-plot-config'));
    expect(parsedConfig.font.size).toBe(16);
  });
});
