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

import {
    openModal,
    closeModal,
    urlSite,
    getID,
    getPicture,
    getLoading,
    getDecoding,
    getField,
    getReviews,
    getPrice
} from './misc.js';
import { getMetadata } from './common.js';
import { sortMetadata2 } from './sort.js';

getMetadata()
    .then((metadata) => {

        function getSpider(brand, model) {
            // console.log(brand + model);
            return encodeURI('speakers/' + brand + ' ' + model + '/spider.jpg');
        }

        function getContext(key, index, value) {
            // console.log(getReviews(value));
            const scores = getField(value, 'pref_rating', value.default_measurement);
            scores.pref_score = parseFloat(scores.pref_score).toFixed(1);
            scores.pref_score_wsub = parseFloat(scores.pref_score_wsub).toFixed(1);
            const scoresEq = getField(value, 'pref_rating_eq', value.default_measurement);
            scoresEq.pref_score = parseFloat(scoresEq.pref_score).toFixed(1);
            scoresEq.pref_score_wsub = parseFloat(scoresEq.pref_score_wsub).toFixed(1);
            return {
                brand: value.brand,
                estimates: getField(value, 'estimates', value.default_measurement),
                estimatesEq: getField(value, 'estimates_eq', value.default_measurement),
                model: value.model,
                id: getID(value.brand, value.model),
                img: {
                    // avif: getPicture(value.brand, value.model, "avif"),
                    webp: getPicture(value.brand, value.model, 'webp'),
                    jpg: getPicture(value.brand, value.model, 'jpg'),
                    loading: getLoading(key),
                    decoding: getDecoding(key),
                },
                price: getPrice(value.price, value.amount),
                reviews: getReviews(value),
                scores: scores,
                scoresEq: scoresEq,
                sensitivity: value.sensitivity,
                spider: getSpider(value.brand, value.model),
            };
        }

        Handlebars.registerHelper('isNaN', function (value) {
            return isNaN(value);
        });

        Handlebars.registerHelper('isDefined', function (value) {
            return value !== undefined;
        });
        Handlebars.registerHelper('roundFloat', function (value) {
            const f = parseFloat(value);
            // console.log('debug '+f)
            return Math.round(f);
        });
        Handlebars.registerHelper('floorFloat', function (value) {
            return Math.floor(parseFloat(value));
        });

        const queryString = window.location.search;
        const urlParams = new URLSearchParams(queryString);
        const urlScores = urlSite + 'scores.html?';

        const sourceSpeaker = document.querySelector('#templateScores').innerHTML;
        const templateSpeaker = Handlebars.compile(sourceSpeaker);
        const speakerContainer = document.querySelector('[data-num="0"');

        function printScore(key, index, value, isStripe) {
            const context = getContext(key, index, value);
            const htmlSpeaker = templateSpeaker(context);
            const divScore = document.createElement('div');
            divScore.setAttribute('id', context.id);
            let attributes = 'searchable column py-2 is-12 is-vertical py-0 my-0';
            if (isStripe) {
                attributes = attributes + ' has-background-light';
            }
            divScore.setAttribute('class', attributes);
            divScore.innerHTML = htmlSpeaker;
            const button = divScore.querySelector('#' + context.id + '-button');
            const target = button.dataset.target;
            const modal = divScore.querySelector('#'+target);
            button.addEventListener('click', () => {
                return openModal(modal);
            });
            const childs = modal.querySelectorAll('.modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button');
            childs.forEach( closeable => {
                const target = closeable.closest('.modal');
                closeable.addEventListener('click', () => closeModal(target));
            });
            return divScore;
        }

        function hasQuality(meta, quality) {
            let status = false;

            for (const [key, measurement] of Object.entries(meta)) {
                const mFormat = measurement.format.toLowerCase();
                const mQuality = measurement.quality.toLowerCase();

                if (mQuality && mQuality === quality) {
                   status = true;
                    break;
                }

                if (mFormat === 'klippel' && quality === 'high') {
                    status = true;
                    break;
                }
            }
            return status;
        }

        function display() {
            const fragment1 = new DocumentFragment();
            const queryString = window.location.search;
            const urlParams = new URLSearchParams(queryString);
            let by_key = 'score';
            let reverse = false;
            let quality;

            if (urlParams.get('quality')) {
                quality = urlParams.get('quality');
            }

            if (urlParams.get('sort')) {
                by_key = urlParams.get('sort');
            }

            if (urlParams.has('reverse')) {
                if (urlParams.get('reverse') === 'true') {
                    reverse = true;
                }
            }

            // todo check filter
            // console.log('Quality=' + quality + ' Key=' + by_key + ' Reverse=' + reverse);

            let count = 0;
            sortMetadata2(metadata, { by: by_key }, reverse).forEach(function (key, index) {
                const speaker = metadata.get(key);
                if (!quality || hasQuality(speaker.measurements, quality.toLowerCase())) {
                    fragment1.appendChild(printScore(key, index, speaker, count %2 == 0));
                    count += 1;
                }
            });
            speakerContainer.appendChild(fragment1);
        }

        display();

        document.addEventListener('keydown', (event) => {
            const e = event || window.event;
            if (e.keyCode === 27) { // Escape key
                document.querySelectorAll('.modal').forEach( modal => closeModal(modal));
            }
        });
    })
    .catch((err) => console.log(err));
