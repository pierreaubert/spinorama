// -*- coding: utf-8 -*-
// A library to display spinorama charts
//
// Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

// import Handlebars from './handlebars-${versions["HANDLEBARS"]}.min.js';
import { getMetadata, getMetadataHead, getMetadataTail } from './download-${versions["CACHE"]}${min}.js';
import {
    getPrice,
    getID,
    getPicture,
    getLoading,
    getDecoding,
    getScore,
    getReviews,
} from './misc-${versions["CACHE"]}${min}.js';
import { process, urlParameters2Sort, setupEventListener } from './search-${versions["CACHE"]}${min}.js';

function getMeasurementCount(metadata) {
    let count = 0;
    metadata.forEach((e) => {
        count += Object.values(e.measurements).length;
    });
    return count;
}

function getBrandCount(metadata) {
    const brands = new Set();
    metadata.forEach((e) => {
        brands.add(e.brand);
    });
    return brands.size;
}

function getDollar(price) {
    if (price === '?') {
        return price;
    }
    const iprice = parseInt(price);
    if (iprice <= 200) {
        return '$';
    } else if (iprice <= 500) {
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
        priceAsDollar: getDollar(price),
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

const templateSource = document.querySelector('#templateSpeaker').innerHTML;
const templateCompiled = Handlebars.compile(templateSource);

function printSpeaker(key, index, value) {
    const context = getContext(key, index, value);
    const html = templateCompiled(context);
    const divSpeaker = document.createElement('div');
    divSpeaker.setAttribute('class', 'column is-narrow searchable');
    divSpeaker.setAttribute('id', context.id);
    divSpeaker.innerHTML = html;
    return divSpeaker;
}

function getReviewCount() {
    return document.querySelectorAll('#selectReviewer')[0].options.length;
}

const speakerContainer = document.querySelector('[data-num="0"');

function display(data, speakerHtml, parentDiv) {
    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const fragment = process(data, params, speakerHtml);
    parentDiv.appendChild(fragment);
}

const navigationContainer = document.querySelector('#pagination');

function urlChangePage(url, newpage) {
    const newUrl = new URL(url);
    newUrl.searchParams.set('page', newpage);
    return newUrl.toString();
}

function navigation(numberSpeakers) {
    // the ${} for mako is replaced by ${"$"} because mako is ran twice on this file
    const navHeader = '<nav class="pagination" role="navigation" aria-label="pagination">';
    const navFooter = '</nav>';

    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const currentPage = params[3].page;
    const perPage = params[3].count;
    const maxPage = Math.floor(numberSpeakers / perPage);
    const prevPage = Math.max(currentPage - 1, 1);
    const nextPage = Math.min(currentPage + 1, maxPage);

    console.log('currentPage='+currentPage+' perPage='+perPage+' maxPage='+maxPage+' prevPage='+prevPage+' nextPage='+nextPage);

    let html = navHeader;
    if (currentPage <= 3) {
        let disabled = '';
        if (currentPage == 1) {
            disabled = 'is-disabled';
        }
        html += '<a href="' + urlChangePage(url, prevPage) + '" class="pagination-previous" ${"$"}{disabled}>Prev</a>';
        html += '<a href=' + urlChangePage(url, nextPage) + ' class="pagination-next">Next</a>';
        html += '<ul class="pagination-list">';
        for (let i = 1; i <= Math.min(3, maxPage); i++) {
            let current = '';
            if (i === currentPage) {
                current = 'is-current';
            }
            html +=
                '<li><a href="' +
                urlChangePage(url, i) +
                `" class="pagination-link ${'$'}{current}" aria-label="Goto page ${'$'}{i}">${'$'}{i}</a></li>`;
        }
        if (maxPage > 5) {
            html += '<li><span class="pagination-ellipsis">&hellip;</span></li>';
            html +=
                '<li><a href="' +
                urlChangePage(url, nextPage) +
                `" class="pagination-link" aria-label="Goto page ${'$'}{maxPage}">${'$'}{maxPage}</a></li>`;
        }
        html += '</ul>';
    } else if (maxPage - currentPage <= 3) {
        html += '<a href="' + urlChangePage(url, prevPage) + '" class="pagination-previous ${"$"}">Prev</a>';
        html += '<a href=' + urlChangePage(url, nextPage) + ' class="pagination-next">Next</a>';
        html += '<ul class="pagination-list">';
        for (let i = 1; i <= Math.min(3, maxPage); i++) {
            let current = '';
            if (i === currentPage) {
                current = 'is-current';
            }
            html +=
                '<li><a href="' +
                urlChangePage(url, i) +
                `" class="pagination-link ${'$'}{current}" aria-label="Goto page ${'$'}{i}">${'$'}{i}</a></li>`;
        }
        if (maxPage > 5) {
            html += '<li><span class="pagination-ellipsis">&hellip;</span></li>';
            html +=
                '<li><a href="' +
                urlChangePage(url, nextPage) +
                `" class="pagination-link" aria-label="Goto page ${'$'}{maxPage}">${'$'}{maxPage}</a></li>`;
        }
        html += '</ul>';
    } else {
    }
    html += navFooter;
    const divNavigation = document.createElement('div');
    while (divNavigation.firstChild) {
        divNavigation.removeChild(divNavigation.firstChild);
    }
    divNavigation.innerHTML = html;
    navigationContainer.appendChild(divNavigation);
}

getMetadataHead()
    .then((metadataHead) => {
        const url = new URL(window.location);
        if (url.pathname === '' || url.pathname === 'index.html') {
            display(metadataHead, printSpeaker, speakerContainer);
        }
        return metadataHead;
    })
    .then((metadataHead) => getMetadataTail(metadataHead))
    .then((metadata) => {
        // now that we have all the data
        setupEventListener(metadata, printSpeaker, speakerContainer);
        // moved after the main display of speakers to minimise reflow
        const speakerCount = document.querySelector('#speakerCount p:nth-child(2)');
        const measurementCount = document.querySelector('#measurementCount p:nth-child(2)');
        const brandCount = document.querySelector('#brandCount p:nth-child(2)');
        const reviewCount = document.querySelector('#reviewCount p:nth-child(2)');
        speakerCount.innerHTML = metadata.size;
        measurementCount.innerHTML = getMeasurementCount(metadata);
        brandCount.innerHTML = getBrandCount(metadata);
        reviewCount.innerHTML = getReviewCount();
        // display if not done above
        const url = new URL(window.location);
        if (url.pathname !== '' && url.pathname !== 'index.html') {
            display(metadata, printSpeaker, speakerContainer);
        }
        navigation(metadata.size);
    })
    .catch((error) => {
        console.log(error);
    });
