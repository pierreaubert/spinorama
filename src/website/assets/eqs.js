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
import { getPeq, getID } from './misc.js';

getMetadata()
    .then((metadata) => {
        const source = document.querySelector('#templateEQ').innerHTML;
        const template = Handlebars.compile(source);

        function getContext(key, index, value) {
            // console.log(getReviews(value));
            return {
                id: getID(value.brand, value.model),
                brand: value.brand,
                model: value.model,
                autoeq:
                    'https://raw.githubusercontent.com/pierreaubert/spinorama/develop/datas/eq/' +
                    encodeURI(value.brand + ' ' + value.model) +
                    '/iir-autoeq.txt',
                preamp_gain: value.eq_autoeq.preamp_gain,
                peq: getPeq(value.eq_autoeq.peq),
            };
        }

        function printEQ(key, index, value) {
            const context = getContext(key, index, value);
            const html = template(context);
            const divEQ = document.createElement('div');
            divEQ.setAttribute('class', 'column is-narrow searchable');
            divEQ.setAttribute('id', context.id);
            divEQ.innerHTML = html;
            return divEQ;
        }

        function display() {
            const speakerContainer = document.querySelector('[data-num="0"');
            const fragment1 = new DocumentFragment();
            sortMetadata2(metadata, { by: 'date' }).forEach(function (key, index) {
                const speaker = metadata.get(key);
                if ('eq_autoeq' in speaker) {
                    fragment1.appendChild(printEQ(key, index, speaker));
                }
            });
            speakerContainer.appendChild(fragment1);
        }

        display();
    })
    .catch((err) => console.log(err));
