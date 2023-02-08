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

import { getMetadata } from './common.js';
import { sortMetadata2 } from './sort.js';
import {
    openModal,
    closeModal,
    getPeq,
    getID
}
from './misc.js';

function getPictureEqCompare(brand, model, suffix) {
    return encodeURI('speakers/' + brand + ' ' + model + '/eq_compare.' + suffix);
}

getMetadata()
    .then((metadata) => {
        const source = document.querySelector('#templateEQ').innerHTML;
        const template = Handlebars.compile(source);

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
            return {
                id: getID(pValue.brand, pValue.model),
                brand: pValue.brand,
                model: pValue.model,
                name: pValue.eqs.autoeq.display_name,
                img_eq_compare: {
                    avif: getPictureEqCompare(pValue.brand, pValue.model, 'avif'),
                    webp: getPictureEqCompare(pValue.brand, pValue.model, 'webp'),
                    jpg: getPictureEqCompare(pValue.brand, pValue.model, 'jpg')
                },
                autoeq: {
                    key: 'autoeq',
                    name: pValue.eqs.autoeq.display_name,
                    url: 'https://raw.githubusercontent.com/pierreaubert/spinorama/develop/' +
                        encodeURI(pValue.eqs.autoeq.filename),
                    preamp_gain: pValue.eqs.autoeq.preamp_gain,
                    peq: getPeq(pValue.eqs.autoeq.peq)
                },
                othereq: otherEQ,
            };
        }

        function switchVisible(divEQ, context, current) {
            if ( current === 'autoeq' ) {
                let autoeq = divEQ.querySelector('#eq-'+context.id+'-autoeq');
                autoeq.classList.remove('hidden');
                for (const oeq in context.othereq) {
                    let eq = divEQ.querySelector('#eq-'+context.id+'-'+context.othereq[oeq].key);
                    eq.classList.add('hidden');
                }
            } else {
                let autoeq = divEQ.querySelector('#eq-'+context.id+'-autoeq');
                autoeq.classList.add('hidden');
                for (const oeq in context.othereq) {
                    if (oeq === current) {
                        let eq = divEQ.querySelector('#eq-'+context.id+'-'+context.othereq[oeq].key);
                        eq.classList.remove('hidden');
                    } else {
                        let eq = divEQ.querySelector('#eq-'+context.id+'-'+context.othereq[oeq].key);
                        eq.classList.add('hidden');
                    }
                }
            }
        }

        function addChangeEvents(divEQ, context) {
            const selectEQ = divEQ.querySelector('#eq-select-'+context.id);
            if (selectEQ !== null) {
                selectEQ.addEventListener('change', function () {
                    switchVisible(divEQ, context, this.value);
                });
            }
        }

        function addModalEvents(divEQ, context) {
            const click = divEQ.querySelector('#eq-button-compare-'+context.id);
            if (click !== null ) {
                const target = click.dataset.target;
                const modal = divEQ.querySelector('#'+target);
                if (modal !== null) {
                    click.addEventListener('click', () => {
                        return openModal(modal);
                    });
                    const childs = modal.querySelectorAll('.modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button');
                    childs.forEach( closeable => {
                        const target = closeable.closest('.modal');
                        closeable.addEventListener('click', () => closeModal(target));
                    });
                }
            }
        }

        function printEQ(key, index, pValue) {
            const context = getContext(key, index, pValue);
            const html = template(context);
            const divEQ = document.createElement('div');
            // populate
            divEQ.setAttribute('class', 'column is-narrow searchable');
            divEQ.setAttribute('id', context.id);
            divEQ.innerHTML = html;
            // add events
            addChangeEvents(divEQ, context);
            addModalEvents(divEQ, context);
            return divEQ;
        }

        function display() {
            const speakerContainer = document.querySelector('[data-num="0"');
            const fragment1 = new DocumentFragment();
            sortMetadata2(metadata, { by: 'date' }).forEach(function (key, index) {
                const speaker = metadata.get(key);
                if ('eqs' in speaker && 'default_eq' in speaker) {
                    fragment1.appendChild(printEQ(key, index, speaker));
                }
            });
            speakerContainer.appendChild(fragment1);
            speakerContainer.addEventListener('keydown', (event) => {
                const e = event || window.event;
                if (e.keyCode === 27) { // Escape key
                    document.querySelectorAll('.modal').forEach( modal => closeModal(modal));
                }
            });
        }

        display();
    })
    .catch((err) => console.log(err));
