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

import { getMetadata } from './common.js'
import { getPrice, getID, getPicture, getLoading, getDecoding, getScore, getReviews } from './misc.js'
import { sortMetadata2 } from './sort.js'

getMetadata().then((metadata) => {
  function getContext (key, value) {
    // console.log(getReviews(value));
    return {
      id: getID(value.brand, value.model),
      brand: value.brand,
      model: value.model,
      price: getPrice(value.price, value.amount),
      img: {
        avif: getPicture(value.brand, value.model, 'avif'),
        webp: getPicture(value.brand, value.model, 'webp'),
        jpg: getPicture(value.brand, value.model, 'jpg'),
        loading: getLoading(key),
        decoding: getDecoding(key)
      },
      score: getScore(value, value.default_measurement),
      reviews: getReviews(value)
    }
  }

  function printSpeaker (key, value) {
    const context = getContext(key, value)
    const html = template(context)
    const divSpeaker = document.createElement('div')
    divSpeaker.setAttribute('class', 'column is-2')
    divSpeaker.setAttribute('id', context.id)
    divSpeaker.innerHTML = html
    return divSpeaker
  }

  function display (data) {
    const fragment = new DocumentFragment()
    sortMetadata2(data, { by: 'date' }).forEach(function (value, key) {
      const speaker = metadata[value]
      fragment.appendChild(printSpeaker(key, speaker))
    })
    speakerContainer.appendChild(fragment)
  }

  const source = document.querySelector('#speaker').innerHTML
  const template = Handlebars.compile(source)
  const speakerContainer = document.querySelector('[data-num="0"')

  display(metadata)
}).catch((error) => {
  console.log(error)
})
