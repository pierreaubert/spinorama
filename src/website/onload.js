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

/*
import { flags_Screen } from './meta.js';
*/

window.onload = () => {
    const navbarBurger = document.querySelector('#navbar-burger');
    const navbarMenu = document.querySelector('.navbar-menu');

    if (navbarBurger && navbarMenu) {
        navbarBurger.addEventListener('click', () => {
            navbarBurger.classList.toggle('is-active');
            navbarMenu.classList.toggle('is-active');
        });
    }

    const smallSearch = document.querySelector('#smallSearch');
    const searchBar = document.querySelector('#search-bar');

    if (smallSearch && searchBar) {
        smallSearch.addEventListener('click', () => {
            searchBar.classList.toggle('is-hidden-mobile');
        });
    }

    const banner = document.querySelector('.banner');
    if (banner) {
        banner.addEventListener('click', () => {
            banner.classList.toggle('hidden');
        });
    }

    const tips = document.querySelectorAll('.speaker-tip');
    if (tips) {
        tips.forEach((tip) => {
            tip.addEventListener('click', () => {
                tip.classList.toggle('hidden');
            });
        });
    }

    // Filter dropdown toggle is handled by theme.js

    // Intercept pushState so we can detect URL changes made by search.js
    const origPushState = history.pushState.bind(history);
    history.pushState = function () {
        origPushState.apply(this, arguments);
        window.dispatchEvent(new Event('pushstate'));
    };

    // Active filter badge: count active filters from URL params (source of truth)
    const filterParams = [
        'reviewer', 'shape', 'power', 'brand', 'quality',
        'priceMin', 'priceMax', 'weightMin', 'weightMax',
        'heightMin', 'heightMax', 'widthMin', 'widthMax',
        'depthMin', 'depthMax', 'f3Min', 'f3Max',
        'f6Min', 'f6Max', 'sensitivityMin', 'sensitivityMax',
        'impedanceMin', 'impedanceMax', 'lfxMin', 'lfxMax',
        'splMin', 'splMax', 'bandwidthMin', 'bandwidthMax',
    ];

    function updateFilterBadge() {
        const triggerBtn = document.querySelector('#filters-dropdown-trigger .button');
        if (!triggerBtn) return;

        const existing = triggerBtn.querySelector('.filter-count');
        if (existing) existing.remove();

        const url = new URL(window.location);
        let count = 0;
        filterParams.forEach(function (param) {
            if (url.searchParams.has(param) && url.searchParams.get(param) !== '') count++;
        });

        if (count > 0) {
            const badge = document.createElement('span');
            badge.className = 'filter-count';
            badge.textContent = count;
            triggerBtn.appendChild(badge);
        }
    }

    // Update badge whenever URL changes
    window.addEventListener('popstate', updateFilterBadge);
    window.addEventListener('pushstate', updateFilterBadge);
    // Initial badge from current URL
    updateFilterBadge();

    const navtabs = document.querySelector('#navtab');
    if (navtabs) {
        const tabs = document.querySelectorAll('.tab-pane');
        tabs.forEach((tab) => {
            // console.info(tab.id);
            if (tab.id === 'pane-2') {
                tab.style.display = 'block';
            } else {
                tab.style.display = 'none';
            }
        });
    }

    document.addEventListener('keydown', (event) => {
        const e = event || window.event;
        if (e.keyCode === 27) {
            // Escape key
            document.querySelectorAll('.modal').forEach((modal) => modal.remove('is-active'));
        }
    });

    if (window.trustedTypes && window.trustedTypes.createPolicy && !window.trustedTypes.defaultPolicy) {
        window.trustedTypes.createPolicy('default', {
            createHTML: (string) => string,
            // Optional, only needed for script (url) tags
            //,createScriptURL: string => string
            //,createScript: string => string,
        });
    }

    /*
    if (flags_Screen) {
        switch (screen.orientation.type) {
            case 'landscape-primary':
            case 'landscape-secondary':
                console.log('Mmmh… you should rotate your device to portrait');
                break;
            case 'portrait-secondary':
            case 'portrait-primary':
                console.log('We are in portrait mode, all good');
                break;
            default:
                console.log("The orientation API isn't supported in this browser :(");
        }
    }
*/
};
