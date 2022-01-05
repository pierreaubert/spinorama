import { getID, getPicture, getLoading, getDecoding, getScore, getReviews } from './misc.js'
import metadata from './metadata.js'
import { sortMetadata2 } from './sort.js'

function getContext (key, value) {
  // console.log(getReviews(value));
  return {
    id: getID(value.brand, value.model),
    brand: value.brand,
    model: value.model,
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

const source = document.querySelector('#speaker').innerHTML
const template = Handlebars.compile(source)

function printSpeaker (key, value) {
  const context = getContext(key, value)
  const html = template(context)
  const divSpeaker = document.createElement('div')
  divSpeaker.setAttribute('class', 'column is-2')
  divSpeaker.setAttribute('id', context.id)
  divSpeaker.innerHTML = html
  return divSpeaker
}

export function display () {
  const speakerContainer = document.querySelector('[data-num="0"')
  const fragment = new DocumentFragment()
  sortMetadata2(metadata, { by: 'date' }).forEach(function (value, key) {
    const speaker = metadata[value]
    fragment.appendChild(printSpeaker(key, speaker))
  })
  speakerContainer.appendChild(fragment)
}
