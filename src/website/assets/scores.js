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
import { toggleId, getID, getPicture, getLoading, getDecoding, getField, getReviews } from './misc.js'
import { sortMetadata2 } from './sort.js'

getMetadata().then((metadata) => {
  function getSpider (brand, model) {
  // console.log(brand + model);
    return encodeURI('speakers/' + brand + ' ' + model + '/spider.jpg')
  }

  function getContext (key, value) {
  // console.log(getReviews(value));
    const scores = getField(value, 'pref_rating', value.default_measurement)
    scores.pref_score = parseFloat(scores.pref_score).toFixed(1)
    scores.pref_score_wsub = parseFloat(scores.pref_score_wsub).toFixed(1)
    const scoresEq = getField(value, 'pref_rating_eq', value.default_measurement)
    scoresEq.pref_score = parseFloat(scoresEq.pref_score).toFixed(1)
    scoresEq.pref_score_wsub = parseFloat(scoresEq.pref_score_wsub).toFixed(1)
    return {
      id: getID(value.brand, value.model),
      brand: value.brand,
      model: value.model,
      sensitivity: value.sensitivity,
      estimates: getField(value, 'estimates', value.default_measurement),
      estimatesEq: getField(value, 'estimates_eq', value.default_measurement),
      scores: scores,
      scoresEq: scoresEq,
      reviews: getReviews(value),
      img: {
      // avif: getPicture(value.brand, value.model, "avif"),
        webp: getPicture(value.brand, value.model, 'webp'),
        jpg: getPicture(value.brand, value.model, 'jpg'),
        loading: getLoading(key),
        decoding: getDecoding(key)
      },
      spider: getSpider(value.brand, value.model)
    }
  }

  Handlebars.registerHelper('isNaN', function (value) {
    return isNaN(value)
  })

  const source = document.querySelector('#scoresht').innerHTML
  const template = Handlebars.compile(source)

  function printScore (key, value) {
    const context = getContext(key, value)
    const html = template(context)
    const divScore = document.createElement('div')
    divScore.setAttribute('id', context.id)
    divScore.setAttribute('class', 'column py-0 is-12 is-vertical')
    divScore.innerHTML = html
    const button = divScore.querySelector('#' + context.id + '-button')
    button.addEventListener('click', e => toggleId('#' + context.id + '-details'))
    return divScore
  }

  function hasQuality (meta, quality) {
    let status = false

    for (const [key, measurement] of Object.entries(meta)) {
      const mFormat = measurement.format.toLowerCase()
      const mQuality = measurement.quality.toLowerCase()

      if (mQuality && mQuality === quality) {
        status = true
        break
      }

      if (mFormat === 'klippel' && quality === 'high') {
        status = true
        break
      }
    }
    return status
  }

  function display () {
    const speakerContainer = document.querySelector('[data-num="0"')
    const fragment1 = new DocumentFragment()
    const queryString = window.location.search
    const urlParams = new URLSearchParams(queryString)
    let quality

    if (urlParams.get('quality')) {
      quality = urlParams.get('quality')
    }

    // todo check filter

    console.log('Quality=' + quality)

    sortMetadata2(metadata, { by: 'score' }).forEach(function (value, key) {
      const speaker = metadata[value]
      if (!quality || hasQuality(speaker.measurements, quality.toLowerCase())) {
        fragment1.appendChild(printScore(value, speaker))
      }
    })
    speakerContainer.appendChild(fragment1)
  }

  display()
}).catch(err => console.log(err))
