// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2026 Pierre Aubert pierre(at)spinorama(dot)org
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

import { urlSite } from './meta.js';
import { getID } from './misc.js';
import { process, urlParameters2Sort, setupEventListener } from './search.js';
import { pagination } from './pagination.js';

function getHeadphoneMetadata() {
    const url = urlSite + 'json/headphone_metadata.json';
    return fetch(url).then(r => r.json()).then((data) => {
        if (!data) return new Map();
        return new Map(Object.values(data).map((hp) => [getID(hp.brand, hp.model), hp]));
    });
}

function getReviewUrl(value) {
    const defaultMeasurement = value.default_measurement;
    const measurement = value.measurements[defaultMeasurement];
    if (measurement && measurement.origin) {
        const origin = measurement.origin.replace('Vendors-', '');
        return 'headphones/' + encodeURI(value.brand + ' ' + value.model) + '/' + encodeURI(origin) + '/index_' + defaultMeasurement + '.html';
    }
    return '#';
}

const container = document.querySelector('[data-num="0"');

// Print header
const header = document.createElement('div');
header.className = 'cell is-col-span-11';
header.innerHTML = `
    <div class="columns is-mobile is-vcentered m-0 p-0 has-background-info-light">
        <div class="column is-1 has-text-centered p-1"><b class="is-size-7">#</b></div>
        <div class="column is-4 p-1"><b class="is-size-7">Name</b></div>
        <div class="column is-2 p-1"><b class="is-size-7">Shape</b></div>
        <div class="column is-2 p-1"><b class="is-size-7">Type</b></div>
        <div class="column is-2 p-1"><b class="is-size-7">Price</b></div>
    </div>
`;
container.appendChild(header);

function printRow(key, index, value) {
    const reviewUrl = getReviewUrl(value);
    const row = document.createElement('div');
    row.className = 'cell is-col-span-11';
    row.id = getID(value.brand, value.model);
    row.innerHTML = `
        <div class="columns is-mobile is-vcentered m-0 p-0">
            <div class="column is-1 has-text-centered p-1">
                <span class="is-size-7">${index + 1}</span>
            </div>
            <div class="column is-4 p-1">
                <a href="${reviewUrl}" class="is-size-7">
                    <b>${value.brand}</b> ${value.model}
                </a>
            </div>
            <div class="column is-2 p-1">
                <span class="is-size-7">${value.shape || ''}</span>
            </div>
            <div class="column is-2 p-1">
                <span class="is-size-7">${value.type || ''}</span>
            </div>
            <div class="column is-2 p-1">
                <span class="is-size-7">${value.price && value.price !== '?' ? value.price + ' USD' : ''}</span>
            </div>
        </div>
    `;
    return row;
}

function clearContainer(c) {
    // Keep the header
    while (c.children.length > 1) {
        c.removeChild(c.lastChild);
    }
}

function display(data, parentDiv) {
    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const [maxResults, fragment] = process(data, params, printRow);
    if (fragment) {
        parentDiv.appendChild(fragment);
    }
    return maxResults;
}

getHeadphoneMetadata()
    .then((metadata) => {
        setupEventListener(metadata, printRow, container);
        clearContainer(container);
        const maxResults = display(metadata, container);
        pagination(maxResults);
    })
    .catch((error) => {
        console.error('Failed to load headphone metadata:', error);
    });
