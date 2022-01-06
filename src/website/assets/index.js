import { urlSite, getID, getPicture, getLoading, getDecoding, getScore, getReviews } from './misc.js'
import { sortMetadata2 } from './sort.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((dataJson) => {
  const metadata = Object.values(dataJson)

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
  const speakerContainer = document.querySelector('[data-num="0"')

  function printSpeaker (key, value) {
    const context = getContext(key, value)
    const html = template(context)
    const divSpeaker = document.createElement('div')
    divSpeaker.setAttribute('class', 'column is-2')
    divSpeaker.setAttribute('id', context.id)
    divSpeaker.innerHTML = html
    return divSpeaker
  }

  function display () {
    const fragment = new DocumentFragment()
    sortMetadata2(metadata, { by: 'date' }).forEach(function (value, key) {
      const speaker = metadata[value]
      console.log(speaker)
      fragment.appendChild(printSpeaker(key, speaker))
    })
    speakerContainer.appendChild(fragment)
  }

  display()
}).catch(
  err => console.log('index.js: ' + err.message)
)
