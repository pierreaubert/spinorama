import { urlSite, getID, getPicture, getLoading, getDecoding, getScore, getReviews } from './misc.js'
import { sortMetadata } from './sort.js'

fetch(urlSite + 'assets/metadata.json').then(
  function (response) {
    return response.json()
  }).then((datajs) => {
  const speakerContainer = document.querySelector('[data-num="0"')
  const speakerDatabase = Object.values(datajs)

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

  function display () {
    const fragment1 = new DocumentFragment()
    speakerDatabase.forEach(function (value, key) {
      fragment1.appendChild(printSpeaker(key, value))
    })
    sortMetadata(speakerDatabase, fragment1, { by: 'date' })
    speakerContainer.appendChild(fragment1)
  }

  display()
})
