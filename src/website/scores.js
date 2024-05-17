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

/*eslint no-undef: "error"*/

import { getID, getPicture, getLoading, getDecoding, getField, getReviews, getPrice } from './misc.js';
import { getMetadata } from './download.js';
import { process, urlParameters2Sort, setupEventListener } from './search.js';
import { pagination } from './pagination.js';

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
    };
}

const speakerContainer = document.querySelector('[data-num="0"');

function contextFragment(context, index) {
    const fragment = new DocumentFragment();
    let class1 = 'cell';
    let class2 = 'cell is-col-span-2';
    if (index % 2 == 0) {
        class1 += ' has-background-light';
        class2 += ' has-background-light';
    }

    const brand = context.brand;
    const model = context.model;
    const div0 = document.createElement('div');
    div0.setAttribute('class', class2);
    div0.innerHTML = brand + ' ' + model;
    fragment.append(div0);

    const price = context.price;
    const div1 = document.createElement('div');
    div1.setAttribute('class', class1);
    div1.innerHTML = price;
    fragment.append(div1);

    const reviews = context.reviews.reviews;
    const div2 = document.createElement('div');
    div2.setAttribute('class', class2);
    if (window.innerWidth < 860) {
        div2.innerHTML = reviews
            .flatMap((review) => '<a href="'+review.url+'">'+review.originShort+'</a>&nbsp;')
            .join('<br/>');
    } else {
        div2.innerHTML = reviews
            .flatMap((review) => '<a href="'+review.url+'">'+review.originLong+'</a>&nbsp;')
            .join('<br/>');
    }
    fragment.append(div2);

    const div3 = document.createElement('div');
    div3.setAttribute('class', class1);
    div3.innerHTML = context.estimates.ref_3dB + 'Hz';
    fragment.append(div3);

    const div4 = document.createElement('div');
    div4.setAttribute('class', class1);
    div4.innerHTML = context.estimates.ref_band + 'dB';
    fragment.append(div4);

    const pref_score = context.scores.pref_score;
    const div5 = document.createElement('div');
    div5.setAttribute('class', class1);
    div5.innerHTML = '';
    if (pref_score && !isNaN(pref_score)) {
        div5.innerHTML = '<b>' + pref_score + '</b>';
    }
    fragment.append(div5);

    const pref_score_wsub = context.scores.pref_score_wsub;
    const div6 = document.createElement('div');
    div6.setAttribute('class', class1);
    div6.innerHTML = '';
    if (pref_score_wsub && !isNaN(pref_score_wsub)) {
        div6.innerHTML = '<b>' + pref_score_wsub + '</b>';
    }
    fragment.append(div6);

    const eq_pref_score = context.scoresEq.pref_score;
    const div7 = document.createElement('div');
    div7.setAttribute('class', class1);
    div7.innerHTML = '';
    if (eq_pref_score && !isNaN(eq_pref_score)) {
        div7.innerHTML = '<b>' + eq_pref_score + '</b>';
    }
    fragment.append(div7);

    const eq_pref_score_wsub = context.scoresEq.pref_score_wsub;
    const div8 = document.createElement('div');
    div8.setAttribute('class', class1);
    div8.innerHTML = '';
    if (eq_pref_score_wsub && !isNaN(eq_pref_score_wsub)) {
        div8.innerHTML = '<b>' + eq_pref_score_wsub + '</b>';
    }
    fragment.append(div8);

    return fragment;
}

function printScore(key, index, value) {
    const context = getContext(key, index, value);
    const fragment = contextFragment(context, index);
    return fragment;
}

function display(data, speakerHtml, parentDiv) {
    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const [maxResults, fragment] = process(data, params, speakerHtml);
    parentDiv.appendChild(fragment);
    return maxResults;
}

getMetadata()
    .then((metadata) => {
        setupEventListener(metadata, printScore, speakerContainer);
        const maxResults = display(metadata, printScore, speakerContainer);
        pagination(maxResults);
    })
    .catch((err) => console.error(err));
