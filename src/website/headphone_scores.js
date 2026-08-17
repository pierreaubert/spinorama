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

const svgArrowUp =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512" width="10" height="10"><path d="M214.6 41.4c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192 109.3 329.4 246.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-160-160z"/></svg>';
const svgArrowDown =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512" width="10" height="10"><path d="M169.4 470.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 402.7 54.6 265.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"/></svg>';

const columnSortMap = [
    { label: '#', sortKey: null, width: 'is-1' },
    { label: 'Name', sortKey: 'brand', width: 'is-4' },
    { label: 'Shape', sortKey: null, width: 'is-2' },
    { label: 'Score', sortKey: 'score', width: 'is-1' },
    { label: 'w/EQ', sortKey: 'scoreEQ', width: 'is-1' },
    { label: 'Price', sortKey: 'price', width: 'is-2' },
];

let currentMetadata = null;
const container = document.querySelector('[data-num="0"');

function getHeadphoneMetadata() {
    const url = urlSite + 'json/headphone_metadata.json';
    return fetch(url)
        .then((r) => r.json())
        .then((data) => {
            if (!data) return new Map();
            return new Map(Object.values(data).map((hp) => [getID(hp.brand, hp.model), hp]));
        });
}

function getReviewUrl(value) {
    const defaultMeasurement = value.default_measurement;
    const measurement = value.measurements[defaultMeasurement];
    if (measurement && measurement.origin) {
        const origin = measurement.origin.replace('Vendors-', '');
        return (
            'headphones/' +
            encodeURI(value.brand + ' ' + value.model) +
            '/' +
            encodeURI(origin) +
            '/index_' +
            defaultMeasurement +
            '.html'
        );
    }
    return '#';
}

function triggerSort(sortKey) {
    const url = new URL(window.location);
    const currentSort = url.searchParams.get('sort') || 'date';
    const currentReverse = url.searchParams.get('reverse') === 'true';

    if (currentSort === sortKey) {
        url.searchParams.set('reverse', (!currentReverse).toString());
    } else {
        url.searchParams.set('sort', sortKey);
        url.searchParams.set('reverse', 'false');
    }
    url.searchParams.set('page', 1);
    window.history.pushState({}, '', url);

    // sync the sort dropdown and reverse checkbox
    const sortSelect = document.querySelector('#sortBy');
    if (sortSelect) {
        sortSelect.value = sortKey;
    }
    const reverseCheckbox = document.querySelector('#sortReverse');
    if (reverseCheckbox) {
        reverseCheckbox.checked = url.searchParams.get('reverse') === 'true';
    }

    const params = urlParameters2Sort(url);
    const [maxResults, fragment] = process(currentMetadata, params, printRow);
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    if (fragment) {
        container.appendChild(fragment);
        pagination(maxResults);
    }
}

function buildHeader() {
    const url = new URL(window.location);
    const currentSort = url.searchParams.get('sort') || 'date';
    const currentReverse = url.searchParams.get('reverse') === 'true';

    const header = document.createElement('div');
    header.className = 'cell is-col-span-11';

    const row = document.createElement('div');
    row.className = 'columns is-mobile is-vcentered m-0 p-0 has-background-info-light';

    for (const col of columnSortMap) {
        const colDiv = document.createElement('div');
        colDiv.className = 'column ' + col.width + ' p-1';
        if (col.width === 'is-1') {
            colDiv.classList.add('has-text-centered');
        }

        if (col.sortKey) {
            const isActive = currentSort === col.sortKey;
            const upStyle = isActive && !currentReverse ? 'opacity:1' : 'opacity:0.25';
            const downStyle = isActive && currentReverse ? 'opacity:1' : 'opacity:0.25';

            colDiv.style.cursor = 'pointer';
            colDiv.innerHTML =
                '<span style="user-select:none;display:inline-flex;align-items:center;gap:2px">' +
                '<b class="is-size-7">' +
                col.label +
                '</b>' +
                '<span style="display:inline-flex;flex-direction:column;line-height:0;gap:1px;margin-left:2px">' +
                '<span style="' +
                upStyle +
                '">' +
                svgArrowUp +
                '</span>' +
                '<span style="' +
                downStyle +
                '">' +
                svgArrowDown +
                '</span>' +
                '</span>' +
                '</span>';
            colDiv.addEventListener('click', () => triggerSort(col.sortKey));
        } else {
            colDiv.innerHTML = '<b class="is-size-7">' + col.label + '</b>';
        }

        row.appendChild(colDiv);
    }

    header.appendChild(row);
    return header;
}

function printRow(key, index, value) {
    const fragment = new DocumentFragment();

    // Render header on first row so it persists during sorts
    if (index === 0) {
        fragment.appendChild(buildHeader());
    }

    const reviewUrl = getReviewUrl(value);
    const row = document.createElement('div');
    row.className = 'cell is-col-span-11';
    row.id = getID(value.brand, value.model);
    const score = typeof value.score === 'number' ? value.score.toFixed(1) : '';
    const scoreEq = typeof value.score_eq === 'number' ? value.score_eq.toFixed(1) : '';
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
            <div class="column is-1 has-text-centered p-1">
                <span class="is-size-7">${score}</span>
            </div>
            <div class="column is-1 has-text-centered p-1">
                <span class="is-size-7">${scoreEq}</span>
            </div>
            <div class="column is-2 p-1">
                <span class="is-size-7">${value.price && value.price !== '?' ? value.price + ' USD' : ''}</span>
            </div>
        </div>
    `;
    fragment.appendChild(row);
    return fragment;
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
        currentMetadata = metadata;
        setupEventListener(metadata, printRow, container);
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        const maxResults = display(metadata, container);
        pagination(maxResults);
    })
    .catch((error) => {
        console.error('Failed to load headphone metadata:', error);
    });
