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
import { getPrice, getID, getPicture, getLoading, getDecoding } from './misc.js';
import { process, urlParameters2Sort, setupEventListener } from './search.js';
import { pagination } from './pagination.js';

function getHeadphoneMetadata() {
    const url = urlSite + 'json/headphone_metadata.json';
    return fetch(url, { headers: { 'Accept-Encoding': 'bz2, gzip, deflate', 'Content-Type': 'application/json' } })
        .then((response) => {
            if (!response.ok) {
                console.log('ERROR fetching headphone metadata: ' + response.status);
                return null;
            }
            return response.json();
        })
        .then((data) => {
            if (!data) return new Map();
            return new Map(Object.values(data).map((hp) => [getID(hp.brand, hp.model), hp]));
        });
}

function getShapeLabel(shape) {
    const labels = {
        'over-ear': 'Over-Ear',
        'on-ear': 'On-Ear',
        'in-ear': 'IEM',
        'earbud': 'Earbud',
    };
    return labels[shape] || shape;
}

function getTypeLabel(type) {
    const labels = {
        'wired': 'Wired',
        'wireless': 'Wireless',
        'hybrid': 'Hybrid',
    };
    return labels[type] || type;
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

function printHeadphone(key, index, value) {
    const id = getID(value.brand, value.model);
    const price = getPrice(value.price, 'each');
    const img = {
        webp: getPicture(value.brand, value.model, 'webp'),
        jpg: getPicture(value.brand, value.model, 'jpg'),
        loading: getLoading(index),
        decoding: getDecoding(index),
    };
    const reviewUrl = getReviewUrl(value);

    const card = document.createElement('div');
    card.className = 'cell';
    card.id = id;
    card.innerHTML = `
        <div class="card m-1">
            <a href="${reviewUrl}">
                <div class="card-image">
                    <figure class="image is-4by3">
                        <picture>
                            <source type="image/webp" srcset="${img.webp}">
                            <img src="${img.jpg}" alt="${value.brand} ${value.model}"
                                 loading="${img.loading}" decoding="${img.decoding}"
                                 width="400" height="300">
                        </picture>
                    </figure>
                </div>
                <div class="card-content p-2">
                    <p class="title is-6">${value.brand} ${value.model}</p>
                    <p class="subtitle is-7">
                        ${getShapeLabel(value.shape)}
                        ${value.type ? ' &middot; ' + getTypeLabel(value.type) : ''}
                        ${price !== '?' ? ' &middot; ' + price + ' USD' : ''}
                    </p>
                </div>
            </a>
        </div>
    `;
    return card;
}

const headphoneContainer = document.querySelector('[data-num="0"');

function clearContainer(container) {
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
}

function display(data, parentDiv) {
    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const [maxResults, fragment] = process(data, params, printHeadphone);
    if (fragment) {
        parentDiv.appendChild(fragment);
    }
    return maxResults;
}

getHeadphoneMetadata()
    .then((metadata) => {
        setupEventListener(metadata, printHeadphone, headphoneContainer);
        clearContainer(headphoneContainer);
        const maxResults = display(metadata, headphoneContainer);
        pagination(maxResults);
    })
    .catch((error) => {
        console.error('Failed to load headphone metadata:', error);
    });
