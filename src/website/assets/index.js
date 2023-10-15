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

/*global Handlebars*/
/*eslint no-undef: "error"*/

import { getMetadata } from './common.js';
import { getPrice, getID, getPicture, getLoading, getDecoding, getScore, getReviews } from './misc.js';
import { sortMetadata2 } from './sort.js';

getMetadata()
    .then((metadata) => {
        const source = document.querySelector('#templateSpeaker').innerHTML;
        const template = Handlebars.compile(source);
        const speakerContainer = document.querySelector('[data-num="0"');
	const speakerCount = document.querySelector('#speakerCount p:nth-child(2)');
	const measurementCount = document.querySelector('#measurementCount p:nth-child(2)');
	const brandCount = document.querySelector('#brandCount p:nth-child(2)');
	const reviewCount = document.querySelector('#reviewCount p:nth-child(2)');

	function getMeasurementCount() {
	    let count = 0;
	    metadata.forEach( (e) => {
		count += Object.values(e.measurements).length;
	    });
	    return count;
	}

	function getBrandCount() {
	    const brands = new Set();
	    metadata.forEach( (e) => {
		brands.add(e.brand);
	    });
	    return brands.size;
	}

	function getReviewCount() {
	    return document.querySelectorAll('#selectReviewer')[0].options.length;
	}

        function getDollar(price) {
            if (price === '?') {
                return price;
            }
            const iprice = parseInt(price);
            if (iprice<=200) {
                return '$';
            } else if (iprice <=500) {
                return '$$';
            }
            return '$$$';
        }

        function getContext(key, index, value) {
            // console.log(getReviews(value));
            const price = getPrice(value.price, value.amount);
            return {
                id: getID(value.brand, value.model),
                brand: value.brand,
                model: value.model,
                price: price,
                priceAsDollar : getDollar(price),
                img: {
                    avif: getPicture(value.brand, value.model, 'avif'),
                    webp: getPicture(value.brand, value.model, 'webp'),
                    jpg: getPicture(value.brand, value.model, 'jpg'),
                    loading: getLoading(index),
                    decoding: getDecoding(index),
                },
                score: getScore(value, value.default_measurement),
                reviews: getReviews(value),
            };
        }

        function printSpeaker(key, index, value) {
            const context = getContext(key, index, value);
            const html = template(context);
            const divSpeaker = document.createElement('div');
            divSpeaker.setAttribute('class', 'column is-narrow searchable');
            divSpeaker.setAttribute('id', context.id);
            divSpeaker.innerHTML = html;
            return divSpeaker;
        }

        function display(data) {
            const fragment = new DocumentFragment();
            sortMetadata2(data, { by: 'date', reverse: false }).forEach((key, index) => {
                const speaker = data.get(key);
                fragment.appendChild(printSpeaker(key, index, speaker));
            });
            return fragment;
        }

	speakerCount.innerHTML = metadata.size;
	measurementCount.innerHTML = getMeasurementCount();
	brandCount.innerHTML = getBrandCount();
	reviewCount.innerHTML = getReviewCount();

        speakerContainer.appendChild(display(metadata));
    })
    .catch((error) => {
        console.log(error);
    });
