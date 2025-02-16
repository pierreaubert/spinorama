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

import { flags_Screen } from './meta.js';

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

    const filters = document.querySelector('#filters-dropdown');
    if (filters) {
        const trigger = filters.querySelector('#filters-dropdown-trigger');
        const menu = filters.querySelector('#filters-dropdown-menu');
        if (!trigger || !menu) {
            console.log('error dropdown trigger+menu not found!');
        }
        trigger.addEventListener('click', () => {
            menu.classList.toggle('hidden');
        });
    }

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
