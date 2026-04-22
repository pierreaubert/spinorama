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

/*eslint no-undef: "error"*/

const flagCounters = false;

import { getMetadataHead, getMetadataTail } from './download.js';
import {
    getPrice,
    getID,
    getPicture,
    getLoading,
    getDecoding,
    getScore,
    getReviews,
    getSensitivity,
    getSPL,
    removeVendors,
    sanitizeFilename,
    validShape,
} from './misc.js';
import { process, urlParameters2Sort, setupEventListener } from './search.js';
import { pagination } from './pagination.js';

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

function getDefaultUrl(value) {
    const def = value.default_measurement;
    if (def && value.measurements[def]) {
        const origin = value.measurements[def].origin;
        return encodeURI(
            'speakers/' + sanitizeFilename(value.brand) + ' ' + sanitizeFilename(value.model) + '/' + removeVendors(origin) + '/index_' + def + '.html'
        );
    }
    return null;
}

function getContext(key, index, value) {
    // console.log(getReviews(value));
    const price = getPrice(value.price, value.amount);
    return {
        id: getID(value.brand, value.model),
        brand: value.brand,
        model: value.model,
        type: value.type,
        price: price,
        priceAsDollar: getDollar(price),
        shape: value.shape,
        sensitivity: getSensitivity(value),
        splinfo: getSPL(value),
        defaultUrl: getDefaultUrl(value),
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

function isShort(values) {
    const max_len = 29;
    let len = 0;
    for (const value of values) {
        if (value.origin) {
            len += [...value.origin].length + 4;
        } else {
            len += 10;
        }
    }
    return len < max_len;
}

function iconValue(value) {
    if (value === '***') {
        return '0';
    }
    const iValue = parseInt(value);
    if (iValue <= 30) {
        return '0';
    } else if (iValue <= 60) {
        return '1';
    } else if (iValue <= 90) {
        return '2';
    }
    return '3';
}

function footerHtml(id, reviews) {
    if (isShort(reviews)) {
        return reviews
            .flatMap(
                (review) => `
            <a class="card-footer-item" href="${review.url}">${review.originLong}</a>
        `
            )
            .join(' ');
    }
    const dropdown = reviews
        .flatMap(
            (review) =>
                `<div class="dropdown-item">
                <a href="${review.url}">${review.originLong}</a>
         </div>
        `
        )
        .join(' ');
    return `
        <div class="card-footer-item">
           <div class="dropdown is-hoverable">
             <div class="dropdown-trigger">
               <button class="button is-small" aria-haspopup="true" aria-controls="dropdown-menu-reviews-${id}">
                 <span>Measurements</span>
                   <span class="icon is-small"><svg width="16px" height="16px"><use href="#icon-angle-down"/></svg></span>
               </button>
             </div>
             <div class="dropdown-menu" id="dropdown-menu-reviews-${id}" role="menu" style="min-width: 300px; left: 50%; transform: translateX(-50%);">
                 <div class="dropdown-content" style="min-width: 300px;">
                   ${dropdown}
                 </div>
              </div>
           </div>
        </div>
    `;
}

function scoreHtml(shape, score) {
    const iconScore = '#icon-volume-danger-' + iconValue(score.scoreScaled);
    const help = `
               <span class="icon is-pulled-right">
                 <a href="/help.html#tonalityDefinition">
                   <svg width="20px" height="20px">
                     <use href="#icon-circle-question"/>
                   </svg>
                 </a>
               </span>
    `;
    if (validShape.has(shape)) {
        return `
               <span class="icon-text">
                 <span class="icon">
                   <svg width="20px" height="20px" aria-label="rating">
                     <use href="${iconScore}"/>
                   </svg>
                 </span>
                 <span>Tonality: <b>${score.score}</b></span>
               </span>
<!--
               ${help}
-->
    `;
    } else {
        return `
               <span class="icon-text">
                 <span class="icon">
                   <svg width="20px" height="20px" aria-label="rating">
                     <use href="${iconScore}"/>
                   </svg>
                 </span>
                 <span>Tonality: <b>***</b></span>
               </span>
<!--
               ${help}
-->
    `;
    }
}

function sensitivityHtml(stype, sensitivity) {
    if (stype === 'active') {
        return 'Active';
    }
    if (sensitivity !== '0') {
        return `Sensitivity: <b>${sensitivity}</b>&nbsp;dB</span>`;
    }
    return 'Sensitivity: <b>?</b>&nbsp;dB</span>';
}

function splHtml(splinfo, splvalue) {
    if (splinfo === '***' || splinfo === '0') {
        return 'SPL ? dB';
    }
    return `${splinfo} SPL: <b>${splvalue}</b>&nbsp;dB</span>`;
}

function contextHtml(context) {
    const brand = context.brand;
    const model = context.model;
    const stype = context.type;
    const img = context.img;
    const score = context.score;
    const price = context.price;
    const sensitivity = sensitivityHtml(stype, context.sensitivity);
    const [splinfo, splvalue] = [...context.splinfo];
    const spl = splHtml(splinfo, splvalue);
    const dollar = context.priceAsDollar;
    const iconLFX = '#icon-volume-info-' + iconValue(score.lfxScaled);
    const iconFlatness = '#icon-volume-success-' + iconValue(score.flatnessScaled);
    const footer = footerHtml(context.id, context.reviews.reviews);
    const html_score = scoreHtml(context.shape, score);
    const defaultUrl = context.defaultUrl;
    const imageHtml = defaultUrl
        ? `<a href="${defaultUrl}">
             <figure class="image is-2by3">
               <picture>
                 <source srcset="${img.webp}" type="image/webp" width="340" height="510">
                 <img src="${img.jpg}" loading="${img.loading}" decoding="${img.decoding}" alt="${brand} ${model}" width="340" height="510"/>
               </picture>
             </figure>
           </a>`
        : `<figure class="image is-2by3">
               <picture>
                 <source srcset="${img.webp}" type="image/webp" width="340" height="510">
                 <img src="${img.jpg}" loading="${img.loading}" decoding="${img.decoding}" alt="${brand} ${model}" width="340" height="510"/>
               </picture>
             </figure>`;
    const html = `
       <div class="card card-min has-background-white-bis">
           <div class="card-image">
             ${imageHtml}
           </div>
           <div class="card-content">
             <div class="content card-identity">
               <span class="card-brand">${brand}</span>
               <span class="card-model">${model}</span>
             </div>
             <div class="content card-metrics">
               <div class="card-metric-row">
                 <span class="icon-text">
                   <span class="icon">${dollar}</span>
                   <span>Price: <b>${price}</b></span>
                 </span>
               </div>
               <div class="card-metric-row card-metric-score">
                 ${html_score}
               </div>
               <div class="card-metric-row">
                 <span class="icon-text">
                   <span class="icon has-text-danger"><svg width="20px" height="20px" aria-label="rating"><use href="${iconLFX}"/></svg></span>
                   <span>Bass extension: <b>${score.lfx}</b>&nbsp;Hz</span>
                 </span>
               </div>
               <div class="card-metric-row">
                 <span class="icon-text">
                   <span class="icon has-text-success"><svg width="20px" height="20px" aria-label="flatness"><use href="${iconFlatness}"/></svg></span>
                   <span>Flatness: <b>&plusmn;${score.flatness}</b>&nbsp;dB</span>
                 </span>
               </div>
             </div>
             <div class="content card-secondary">
               <div class="card-metric-row">
                 <span class="icon-text">
                   <span class="icon has-text-success"><svg width="20px" height="20px" aria-label="sensitivity"><use href="#icon-circle"/></svg></span>
                   <span>${sensitivity}</span>
                 </span>
               </div>
               <div class="card-metric-row">
                 <span class="icon-text">
                   <span class="icon has-text-success">
                     <svg width="20px" height="20px" aria-label="spl">
                      <use href="#icon-circle-dot"/>
                     </svg>
                   </span>
                   <span>${spl}</span>
                 </span>
               </div>
             </div>
           </div>
           <footer class="card-footer">
             ${footer}
           </footer>
       </div>
    `;
    return html;
}

function printSpeaker(key, index, value) {
    const context = getContext(key, index, value);
    const html = contextHtml(context);
    const divSpeaker = document.createElement('div');
    divSpeaker.setAttribute('class', 'cell');
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
    const [maxResults, fragment] = process(data, params, speakerHtml);
    if (fragment) {
        parentDiv.appendChild(fragment);
    }
    return maxResults;
}

function clearContainer(container) {
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
}

getMetadataHead()
    .then((metadataHead) => {
        const url = new URL(window.location);
        const hasParams = url.search !== '';
        if (hasParams) {
            clearContainer(speakerContainer);
            display(metadataHead, printSpeaker, speakerContainer);
        }
        return metadataHead;
    })
    .then((metadataHead) => getMetadataTail(metadataHead))
    .then((metadata) => {
        setupEventListener(metadata, printSpeaker, speakerContainer);
        if (flagCounters) {
            const speakerCount = document.querySelector('#speakerCount p:nth-child(2)');
            const measurementCount = document.querySelector('#measurementCount p:nth-child(2)');
            const brandCount = document.querySelector('#brandCount p:nth-child(2)');
            const reviewCount = document.querySelector('#reviewCount p:nth-child(2)');
            speakerCount.innerHTML = metadata.size;
            measurementCount.innerHTML = getMeasurementCount(metadata);
            brandCount.innerHTML = getBrandCount(metadata);
            reviewCount.innerHTML = getReviewCount();
        }
        clearContainer(speakerContainer);
        const maxResults = display(metadata, printSpeaker, speakerContainer);
        pagination(maxResults);
    })
    .catch((error) => {
        console.log(error);
    });
