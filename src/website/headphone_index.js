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

function getContext(key, index, value) {
    const price = getPrice(value.price, 'each');
    return {
        id: getID(value.brand, value.model),
        brand: value.brand,
        model: value.model,
        type: value.type,
        price: price,
        shape: value.shape,
        img: {
            avif: getPicture(value.brand, value.model, 'avif'),
            webp: getPicture(value.brand, value.model, 'webp'),
            jpg: getPicture(value.brand, value.model, 'jpg'),
            loading: getLoading(index),
            decoding: getDecoding(index),
        },
        reviews: [],
    };
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

function printCard(container, key, index, value) {
    const context = getContext(key, index, value);
    const reviewUrl = getReviewUrl(value);

    const card = document.createElement('div');
    card.className = 'cell';
    card.innerHTML = `
        <div class="card m-1">
            <a href="${reviewUrl}">
                <div class="card-image">
                    <figure class="image is-4by3">
                        <picture>
                            <source type="image/webp" srcset="${context.img.webp}">
                            <img src="${context.img.jpg}" alt="${context.brand} ${context.model}"
                                 loading="${context.img.loading}" decoding="${context.img.decoding}"
                                 width="400" height="300">
                        </picture>
                    </figure>
                </div>
                <div class="card-content p-2">
                    <p class="title is-6">${context.brand} ${context.model}</p>
                    <p class="subtitle is-7">
                        ${getShapeLabel(context.shape)} &middot; ${getTypeLabel(context.type)}
                        ${context.price !== '?' ? ' &middot; ' + context.price + ' USD' : ''}
                    </p>
                </div>
            </a>
        </div>
    `;
    container.appendChild(card);
}

getHeadphoneMetadata()
    .then((metadata) => {
        const speakerContainer = document.querySelector('[data-num="0"');

        function printPage(metadata, params) {
            const results = process(metadata, params);
            speakerContainer.innerHTML = '';
            let index = 0;
            results.forEach((value, key) => {
                printCard(speakerContainer, key, index, value);
                index++;
            });
            pagination(speakerContainer, metadata.size, params);
        }

        const params = urlParameters2Sort();
        printPage(metadata, params);
        setupEventListener(metadata, printPage);
    })
    .catch((error) => {
        console.error('Failed to load headphone metadata:', error);
    });
