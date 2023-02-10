// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

window.onload = () => {
    const navbarBurger = document.querySelector('#navbar-burger');
    const navbarMenu = document.querySelector('.navbar-menu');

    navbarBurger.addEventListener('click', (e) => {
        navbarBurger.classList.toggle('is-active');
        navbarMenu.classList.toggle('is-active');
    });

    const smallSearch = document.querySelector('#smallSearch');
    const searchBar = document.querySelector('#search-bar');

    if (smallSearch && searchBar) {
        smallSearch.addEventListener('click', (e) => {
            searchBar.classList.toggle('is-hidden-mobile');
        });
    }

    const banner = document.querySelector('.banner');
    if (banner) {
        banner.addEventListener('click', (e) => {
            banner.classList.toggle('hidden');
        });
    }
};
