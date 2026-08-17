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

/*global Handlebars*/
/*eslint no-undef: "error"*/

import { urlSite } from './meta.js';
import { getID, getPeq } from './misc.js';
import { process, urlParameters2Sort, setupEventListener } from './search.js';
import { pagination } from './pagination.js';

function getHeadphoneEQData() {
    const metaUrl = urlSite + 'json/headphone_metadata.json';
    const eqUrl = urlSite + 'json/headphone_eqdata.json';

    const metaPromise = fetch(metaUrl).then((r) => r.json());
    const eqPromise = fetch(eqUrl)
        .then((r) => r.json())
        .catch(() => ({}));

    return Promise.all([metaPromise, eqPromise]).then(([metaData, eqData]) => {
        const merged = new Map();
        for (const [key, value] of Object.entries(metaData)) {
            const id = getID(value.brand, value.model);
            if (eqData[key] && eqData[key].eqs) {
                value.eqs = eqData[key].eqs;
                value.default_eq = eqData[key].default_eq;
            }
            if (value.eqs && Object.keys(value.eqs).length > 0) {
                merged.set(id, value);
            }
        }
        return merged;
    });
}

const source = document.querySelector('#templateEQ').innerHTML;
const template = Handlebars.compile(source);
const container = document.querySelector('[data-num="0"');

function getContext(pKey, pIndex, pValue) {
    const defaultEQ = pValue.default_eq;
    let otherEQ = {};
    for (const eqType in pValue.eqs) {
        if (eqType !== defaultEQ) {
            otherEQ[eqType] = {
                key: eqType,
                name: pValue.eqs[eqType].display_name,
                url:
                    'https://raw.githubusercontent.com/pierreaubert/spinorama/develop/' +
                    encodeURI(pValue.eqs[eqType].filename),
                preamp_gain: pValue.eqs[eqType].preamp_gain,
                peq: getPeq(pValue.eqs[eqType].peq),
            };
        }
    }
    const defaultEqData = pValue.eqs[defaultEQ];
    return {
        id: getID(pValue.brand, pValue.model),
        brand: pValue.brand,
        model: pValue.model,
        autoeq: {
            key: defaultEQ,
            name: defaultEqData.display_name,
            url: 'https://raw.githubusercontent.com/pierreaubert/spinorama/develop/' + encodeURI(defaultEqData.filename),
            preamp_gain: defaultEqData.preamp_gain,
            peq: getPeq(defaultEqData.peq),
        },
        othereq: otherEQ,
    };
}

function printEQ(key, index, value) {
    const context = getContext(key, index, value);
    const html = template(context);
    const div = document.createElement('div');
    div.className = 'cell';
    div.id = getID(value.brand, value.model);
    div.innerHTML = html;
    return div;
}

function clearContainer(c) {
    while (c.firstChild) {
        c.removeChild(c.firstChild);
    }
}

function display(data, parentDiv) {
    const url = new URL(window.location);
    const params = urlParameters2Sort(url);
    const [maxResults, fragment] = process(data, params, printEQ);
    if (fragment) {
        parentDiv.appendChild(fragment);
    }
    return maxResults;
}

getHeadphoneEQData()
    .then((metadata) => {
        setupEventListener(metadata, printEQ, container);
        clearContainer(container);
        const maxResults = display(metadata, container);
        pagination(maxResults);
    })
    .catch((error) => {
        console.error('Failed to load headphone EQ data:', error);
    });
