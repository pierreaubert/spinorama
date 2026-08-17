// -*- coding: utf-8 -*-
// Tests for theme.js — theme toggle, units, menu dropdown
//
// Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

const NAV_HTML = `
<!DOCTYPE html>
<html lang="en" data-theme="light">
<body>
  <nav class="navbar-bar mx-1 my-1">
    <div class="dropdown is-hoverable" id="menu-main">
      <div class="dropdown-trigger" id="menu-main-trigger">
        <button type="button" class="button" aria-label="menu-main">M</button>
      </div>
      <div class="dropdown-menu" id="menu-main-dropdown" role="menu">
        <div class="dropdown-content">
          <div class="dropdown-item">
            <div class="menu-row">
              <span>Theme</span>
              <div class="theme-toggle" role="radiogroup" aria-label="Theme">
                <button type="button" class="theme-toggle-btn" data-theme="light">L</button>
                <button type="button" class="theme-toggle-btn" data-theme="dark">D</button>
              </div>
            </div>
          </div>
          <div class="dropdown-item">
            <div class="menu-row">
              <span>Units</span>
              <div class="field has-addons mb-0">
                <p class="control"><button class="button is-small unit-btn is-active" data-units="metric">Metric</button></p>
                <p class="control"><button class="button is-small unit-btn" data-units="imperial">Imperial</button></p>
              </div>
            </div>
          </div>
          <a class="dropdown-item" href="/">Home</a>
          <a class="dropdown-item" href="/customization.html">Customization</a>
        </div>
      </div>
    </div>
    <a href="/" class="navbar-brand-link is-size-4"><b>SPIN</b>orama</a>
    <div class="field has-addons navbar-search-field">
      <div class="control has-icons-right is-expanded">
        <input id="searchInput" class="input is-info" type="text" placeholder="brand or model ...">
      </div>
      <div class="control">
        <div class="dropdown is-right" id="filters-dropdown">
          <div class="dropdown-trigger" id="filters-dropdown-trigger">
            <button type="button" class="button" aria-label="filter">F</button>
          </div>
        </div>
      </div>
      <div class="control">
        <div class="dropdown is-hoverable is-right" id="sorters-dropdown">
          <div class="dropdown-trigger" id="sorters-dropdown-trigger">
            <button type="button" class="button" aria-label="sort">S</button>
          </div>
        </div>
      </div>
    </div>
  </nav>
  <div class="content">
    <span class="unit-value" data-unit="mm" data-value="200">200</span><span class="unit-label" data-unit="mm">mm</span>
    <span class="unit-value" data-unit="kg" data-value="10.5">10.5</span><span class="unit-label" data-unit="kg">kg</span>
    <span class="unit-value" data-unit="m" data-value="1">1</span><span class="unit-label" data-unit="m">m</span>
  </div>
</body>
</html>`;

let dom;

function setupDOM() {
    dom = new JSDOM(NAV_HTML, { url: 'https://dev.spinorama.org/' });
    global.document = dom.window.document;
    global.window = dom.window;
    global.localStorage = dom.window.localStorage;
    global.CustomEvent = dom.window.CustomEvent;
    global.Event = dom.window.Event;
    global.HTMLElement = dom.window.HTMLElement;
    global.window.matchMedia = vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
    });
}

function teardownDOM() {
    delete global.document;
    delete global.window;
    delete global.localStorage;
    delete global.CustomEvent;
    delete global.Event;
    delete global.HTMLElement;
}

function loadThemeJS() {
    const fs = require('fs');
    const code = fs.readFileSync('src/website/theme.js', 'utf-8');
    const fn = new dom.window.Function(code);
    fn.call(dom.window);
}

// =========================================================================
// Navbar structure
// =========================================================================
describe('Navbar structure', () => {
    beforeEach(() => setupDOM());
    afterEach(() => teardownDOM());

    test('navbar is a single row with menu, brand, and search', () => {
        const bar = document.querySelector('.navbar-bar');
        expect(bar).not.toBeNull();
        expect(bar.querySelector('#menu-main')).not.toBeNull();
        expect(bar.querySelector('.navbar-brand-link')).not.toBeNull();
        expect(bar.querySelector('#searchInput')).not.toBeNull();
    });

    test('theme toggle is inside the hamburger menu', () => {
        const menu = document.querySelector('#menu-main .dropdown-content');
        expect(menu.querySelector('.theme-toggle')).not.toBeNull();
    });

    test('unit toggle is inside the hamburger menu', () => {
        const menu = document.querySelector('#menu-main .dropdown-content');
        expect(menu.querySelectorAll('.unit-btn').length).toBe(2);
    });

    test('menu contains customization link', () => {
        const menu = document.querySelector('#menu-main .dropdown-content');
        const links = Array.from(menu.querySelectorAll('a.dropdown-item'));
        const customLink = links.find((a) => a.href.includes('customization'));
        expect(customLink).not.toBeUndefined();
    });

    test('search bar has filter and sort controls', () => {
        expect(document.querySelector('#filters-dropdown')).not.toBeNull();
        expect(document.querySelector('#sorters-dropdown')).not.toBeNull();
    });
});

// =========================================================================
// Theme toggle
// =========================================================================
describe('Theme toggle', () => {
    beforeEach(() => {
        setupDOM();
        localStorage.clear();
    });
    afterEach(() => teardownDOM());

    test('defaults to light theme', () => {
        loadThemeJS();
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });

    test('restores dark theme from localStorage', () => {
        localStorage.setItem('spinorama-theme', 'dark');
        loadThemeJS();
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    });

    test('clicking dark button sets dark theme and persists', () => {
        loadThemeJS();
        document.querySelector('.theme-toggle-btn[data-theme="dark"]').click();
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        expect(localStorage.getItem('spinorama-theme')).toBe('dark');
    });

    test('clicking dark then light restores light', () => {
        loadThemeJS();
        document.querySelector('.theme-toggle-btn[data-theme="dark"]').click();
        document.querySelector('.theme-toggle-btn[data-theme="light"]').click();
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });

    test('theme toggle dispatches spinorama-config-change event', () => {
        loadThemeJS();
        const spy = vi.fn();
        window.addEventListener('spinorama-config-change', spy);
        document.querySelector('.theme-toggle-btn[data-theme="dark"]').click();
        expect(spy).toHaveBeenCalledTimes(1);
    });
});

// =========================================================================
// Unit conversion
// =========================================================================
describe('Unit conversion', () => {
    beforeEach(() => {
        setupDOM();
        localStorage.clear();
    });
    afterEach(() => teardownDOM());

    test('defaults to metric', () => {
        loadThemeJS();
        expect(document.querySelector('.unit-value[data-unit="mm"]').textContent).toBe('200');
        expect(document.querySelector('.unit-label[data-unit="mm"]').textContent).toBe('mm');
    });

    test('clicking imperial converts mm to inches', () => {
        loadThemeJS();
        document.querySelector('.unit-btn[data-units="imperial"]').click();
        expect(parseFloat(document.querySelector('.unit-value[data-unit="mm"]').textContent)).toBeCloseTo(7.9, 1);
        expect(document.querySelector('.unit-label[data-unit="mm"]').textContent).toBe('in');
    });

    test('clicking imperial converts kg to lbs', () => {
        loadThemeJS();
        document.querySelector('.unit-btn[data-units="imperial"]').click();
        expect(parseFloat(document.querySelector('.unit-value[data-unit="kg"]').textContent)).toBeCloseTo(23.1, 0);
        expect(document.querySelector('.unit-label[data-unit="kg"]').textContent).toBe('lbs');
    });

    test('clicking imperial converts m to ft', () => {
        loadThemeJS();
        document.querySelector('.unit-btn[data-units="imperial"]').click();
        expect(parseFloat(document.querySelector('.unit-value[data-unit="m"]').textContent)).toBeCloseTo(3.3, 1);
        expect(document.querySelector('.unit-label[data-unit="m"]').textContent).toBe('ft');
    });

    test('switching back to metric restores original values', () => {
        loadThemeJS();
        document.querySelector('.unit-btn[data-units="imperial"]').click();
        document.querySelector('.unit-btn[data-units="metric"]').click();
        expect(document.querySelector('.unit-value[data-unit="mm"]').textContent).toBe('200');
        expect(document.querySelector('.unit-label[data-unit="mm"]').textContent).toBe('mm');
    });

    test('persists unit choice to localStorage', () => {
        loadThemeJS();
        document.querySelector('.unit-btn[data-units="imperial"]').click();
        expect(localStorage.getItem('spinorama-units')).toBe('imperial');
    });

    test('restores imperial from localStorage', () => {
        localStorage.setItem('spinorama-units', 'imperial');
        loadThemeJS();
        expect(parseFloat(document.querySelector('.unit-value[data-unit="mm"]').textContent)).toBeCloseTo(7.9, 1);
    });
});
